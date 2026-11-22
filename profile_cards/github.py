"""GitHub GraphQL fetchers behind the stats cards, with a per-repo lines-of-code cache."""

import hashlib
import json
import time
from datetime import UTC, datetime
from pathlib import Path

import requests

API_URL = "https://api.github.com/graphql"
ERROR_LOG = Path("last_api_error.txt")
RETRYABLE = (502, 503, 504)

REPO_COMMITS = """
    nameWithOwner
    defaultBranchRef { target { ... on Commit { history { totalCount } } } }
"""


AFFILIATED_REPOS = (
    """
    query($login: String!, $cursor: String) {
      user(login: $login) {
        repositories(
          first: 60, after: $cursor,
          ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER]
        ) {
          nodes { isFork """
    + REPO_COMMITS
    + """ }
          pageInfo { endCursor hasNextPage }
        }
      }
    }"""
)


class GitHubError(Exception):
    """Any GitHub API failure."""


def _year_ranges(first_year, last_year, body):
    """One aliased `contributionsCollection` per year: GitHub caps each at a year."""
    return " ".join(
        f'y{year}: contributionsCollection(from: "{year}-01-01T00:00:00Z", '
        f'to: "{year}-12-31T23:59:59Z") {{ {body} }}'
        for year in range(first_year, last_year + 1)
    )


def _repo(node):
    branch = node["defaultBranchRef"]
    commits = branch["target"]["history"]["totalCount"] if branch else 0
    return {"name": node["nameWithOwner"], "commits": commits}


class GitHub:
    def __init__(self, token, login, cache_dir=Path("cache")):
        self.login = login
        self.headers = {"authorization": f"token {token}"}
        digest = hashlib.sha256(login.encode()).hexdigest()
        self.cache_path = cache_dir / f"{digest}.json"

    def query(self, query, retries=4, **variables):
        """POST a GraphQL query and return its data. Network errors and 502/503/504 are
        retried with backoff; anything else fails straight away."""
        for attempt in range(1, retries + 1):
            try:
                response = requests.post(
                    API_URL,
                    json={"query": query, "variables": self._variables(query, variables)},
                    headers=self.headers,
                    timeout=30,
                )
            except requests.RequestException as error:
                if attempt == retries:
                    raise GitHubError(f"Network error after {retries} attempts: {error}") from error
            else:
                if response.status_code == 200:
                    return response.json()["data"]
                if response.status_code not in RETRYABLE or attempt == retries:
                    self._fail(response)
            time.sleep(3 * 2 ** (attempt - 1))
        raise AssertionError("unreachable")

    def _variables(self, query, variables):
        return {"login": self.login, **variables} if "$login" in query else variables

    @staticmethod
    def _fail(response):
        # GitHub's error text can name private repos, so keep it in a local, ignored file.
        ERROR_LOG.write_text(f"Status: {response.status_code}\n\n{response.text}", encoding="utf-8")
        if response.status_code == 403:
            raise GitHubError("Hit GitHub's anti-abuse rate limit")
        raise GitHubError(f"GitHub API failed ({response.status_code}); see {ERROR_LOG}")

    def profile(self):
        """Returns (user id, account creation date, follower count)."""
        user = self.query(
            "query($login: String!) { user(login: $login) { id createdAt "
            "followers { totalCount } } }"
        )["user"]
        return user["id"], user["createdAt"], user["followers"]["totalCount"]

    def calendar(self):
        """The last year's contribution graph: weeks of (iso_date, count), oldest first."""
        weeks = self.query(
            "query($login: String!) { user(login: $login) { contributionsCollection { "
            "contributionCalendar { weeks { contributionDays { date contributionCount } } } } } }"
        )["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
        return [[(d["date"], d["contributionCount"]) for d in w["contributionDays"]] for w in weeks]

    def history(self, created_at):
        """Every (iso_date, count) since the account was created, up to today."""
        years = _year_ranges(
            int(created_at[:4]),
            datetime.now(UTC).year,
            "contributionCalendar { weeks { contributionDays { date contributionCount } } }",
        )
        user = self.query("query($login: String!) { user(login: $login) { " + years + " } }")[
            "user"
        ]
        days = {
            day["date"]: day["contributionCount"]
            for year in user.values()
            for week in year["contributionCalendar"]["weeks"]
            for day in week["contributionDays"]
        }
        today = datetime.now(UTC).date().isoformat()  # the current year's calendar runs to Dec 31
        return sorted((date, count) for date, count in days.items() if date <= today)

    def owned_stats(self):
        """Returns (repo count, star count) for non-fork repositories you own."""
        repos = stars = 0
        cursor = None
        while True:
            page = self.query(
                """
                query($login: String!, $cursor: String) {
                  user(login: $login) {
                    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
                      nodes { isFork stargazers { totalCount } }
                      pageInfo { endCursor hasNextPage }
                    }
                  }
                }""",
                cursor=cursor,
            )["user"]["repositories"]
            own = [node for node in page["nodes"] if not node["isFork"]]
            repos += len(own)
            stars += sum(node["stargazers"]["totalCount"] for node in own)
            if not page["pageInfo"]["hasNextPage"]:
                return repos, stars
            cursor = page["pageInfo"]["endCursor"]

    def affiliated_repos(self):
        """Non-fork repos you own, collaborate on or reach through an organisation."""
        repos = []
        cursor = None
        while True:
            page = self.query(
                AFFILIATED_REPOS,
                cursor=cursor,
            )["user"]["repositories"]
            repos += [_repo(node) for node in page["nodes"] if not node["isFork"]]
            if not page["pageInfo"]["hasNextPage"]:
                return repos
            cursor = page["pageInfo"]["endCursor"]

    def external_repos(self, first_year, last_year):
        """Repos you committed to without collaborator access, which is what captures open
        source work."""
        body = f"commitContributionsByRepository(maxRepositories: 100) {{ repository {{ {REPO_COMMITS} }} }}"
        years = _year_ranges(first_year, last_year, body)
        user = self.query("query($login: String!) { user(login: $login) { " + years + " } }")[
            "user"
        ]
        return [
            _repo(entry["repository"])
            for year in user.values()
            for entry in year["commitContributionsByRepository"]
            if entry["repository"]["defaultBranchRef"]  # skip empty repos
        ]

    def repo_loc(self, name, user_id):
        """Lines added and deleted by `user_id` on the default branch of `name`. The author
        filter runs server-side so large repos are not walked commit by commit."""
        owner, repo = name.split("/")
        added = deleted = 0
        cursor = None
        while True:
            data = self.query(
                """
                query($owner: String!, $repo: String!, $cursor: String, $author: ID!) {
                  repository(owner: $owner, name: $repo) {
                    defaultBranchRef { target { ... on Commit {
                      history(first: 100, after: $cursor, author: {id: $author}) {
                        nodes { additions deletions }
                        pageInfo { endCursor hasNextPage }
                      }
                    } } }
                  }
                }""",
                owner=owner,
                repo=repo,
                cursor=cursor,
                author=user_id,
            )["repository"]
            if data["defaultBranchRef"] is None:
                return 0, 0
            history = data["defaultBranchRef"]["target"]["history"]
            added += sum(commit["additions"] for commit in history["nodes"])
            deleted += sum(commit["deletions"] for commit in history["nodes"])
            if not history["pageInfo"]["hasNextPage"]:
                return added, deleted
            cursor = history["pageInfo"]["endCursor"]

    def lines_of_code(self, repos, user_id):
        """Total (added, deleted) across `repos`. Results are cached per repo and only rescanned
        when its commit count changes. Cache keys are hashed because the cache is committed to
        a public repo and a plain name would leak private repos."""
        cache = self._read_cache()
        fresh = {}
        for position, repo in enumerate(repos, 1):
            key = hashlib.sha256(repo["name"].encode()).hexdigest()
            entry = cache.get(key)
            if entry and entry["total_commits"] == repo["commits"]:
                fresh[key] = entry
                continue
            print(f"  [{position}/{len(repos)}] commit count changed, rescanning")
            added, deleted = self.repo_loc(repo["name"], user_id) if repo["commits"] else (0, 0)
            fresh[key] = {
                "total_commits": repo["commits"],
                "loc_add": added,
                "loc_del": deleted,
            }
            self._write_cache(fresh)  # after every repo, so a crash keeps its progress
        self._write_cache(fresh)
        return (
            sum(entry["loc_add"] for entry in fresh.values()),
            sum(entry["loc_del"] for entry in fresh.values()),
        )

    def _read_cache(self):
        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_cache(self, cache):
        self.cache_path.parent.mkdir(exist_ok=True)
        self.cache_path.write_text(json.dumps(cache, indent=2, sort_keys=True), encoding="utf-8")
