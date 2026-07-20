import requests
import os
import time
import json
import hashlib

# Fine-grained personal access token needed, scoped to All Repositories:
# Account permissions: read:Followers, read:Starring, read:Watching
# Repository permissions: read:Commit statuses, read:Contents, read:Issues,
# read:Metadata, read:Pull Requests
#
# NOTE: fine-grained PATs currently CANNOT access private repos you're only a
# collaborator on (owned by another individual, not an org/yourself) — this
# is a documented GitHub gap, not a bug here. If you contribute to such a
# repo and want it included, use a classic PAT with `repo` scope instead —
# this script doesn't care which type of token it gets, just the string.
HEADERS = {"authorization": "token " + os.environ["ACCESS_TOKEN"]}
USER_NAME = os.environ["USER_NAME"]
QUERY_COUNT = {
    "user_getter": 0,
    "follower_getter": 0,
    "graph_repos_stars": 0,
    "recursive_loc": 0,
    "fetch_owned_repo_edges": 0,
    "fetch_external_contribution_repos": 0,
    "contribution_weeks": 0,
}

# Set for real inside __main__, but must exist unconditionally at module scope
# or static analysis (and any future import of this module) can't prove
# loc_counter_one_repo() below has a valid value to read at call time.
OWNER_ID = None


class GitHubStatsError(Exception):
    """Raised for any GitHub API failure in this script — lets callers (and
    linters) distinguish our failures from generic Python exceptions."""


def post_graphql(query, variables, max_retries=4, base_delay=3):
    """
    Posts a GraphQL request with retry + exponential backoff for TRANSIENT
    failures only (network errors, 502/503/504 — GitHub's infrastructure
    having a momentary hiccup, unrelated to anything about our query). Does
    NOT retry 4xx errors like 403 (rate limit / auth problems) — those need
    a person to look at them, retrying blindly just burns more of the rate
    limit budget that's already the problem.
    """
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.post(
                "https://api.github.com/graphql",
                json={"query": query, "variables": variables},
                headers=HEADERS,
                timeout=30,
            )
        except requests.exceptions.RequestException as exc:
            if attempt == max_retries:
                raise GitHubStatsError(
                    f"Network error after {max_retries} attempts: {exc}"
                ) from exc
            wait = base_delay * (2 ** (attempt - 1))
            print(
                f"  !! Network error ({exc}) — retrying in {wait}s (attempt {attempt}/{max_retries})..."
            )
            time.sleep(wait)
            continue

        if response.status_code == 200:
            return response

        if response.status_code in (502, 503, 504) and attempt < max_retries:
            wait = base_delay * (2 ** (attempt - 1))
            print(
                f"  !! GitHub returned {response.status_code} (transient) — retrying in {wait}s (attempt {attempt}/{max_retries})..."
            )
            time.sleep(wait)
            continue

        return response  # non-retryable status, or retries exhausted — let the caller raise with context

    return response


def simple_request(func_name, query, variables):
    request = post_graphql(query, variables)
    if request.status_code == 200:
        return request
    raise GitHubStatsError(
        f"{func_name} failed with {request.status_code}: {request.text} (queries so far: {QUERY_COUNT})"
    )


def contribution_weeks(username):
    """
    Uses GitHub's GraphQL v4 API to fetch the contribution calendar for the
    past year, grouped by week — this is real activity data, not decoration.
    """
    print(f"  -> Fetching contribution calendar for {username}...")
    query_count("contribution_weeks")
    query = """
    query($login: String!) {
        user(login: $login) {
            contributionsCollection {
                contributionCalendar {
                    weeks {
                        contributionDays {
                            contributionCount
                        }
                    }
                }
            }
        }
    }"""
    request = simple_request(contribution_weeks.__name__, query, {"login": username})
    weeks = request.json()["data"]["user"]["contributionsCollection"][
        "contributionCalendar"
    ]["weeks"]
    return [
        sum(day["contributionCount"] for day in w["contributionDays"]) for w in weeks
    ]


def graph_repos_stars(count_type, owner_affiliation, cursor=None):
    """
    Uses GitHub's GraphQL v4 API to return total repository or star count.
    Forks are excluded from both — a forked repo isn't really "your" repo or
    "your" stars for display purposes here.
    """
    if cursor is None:
        print(f"  -> Fetching {count_type} count (affiliation: {owner_affiliation})...")
    query_count("graph_repos_stars")
    query = """
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 100, after: $cursor, ownerAffiliations: $owner_affiliation) {
                totalCount
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            isFork
                            stargazers {
                                totalCount
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }"""
    variables = {
        "owner_affiliation": owner_affiliation,
        "login": USER_NAME,
        "cursor": cursor,
    }
    request = simple_request(graph_repos_stars.__name__, query, variables)
    data = request.json()["data"]["user"]["repositories"]
    non_fork_edges = [e for e in data["edges"] if not e["node"]["isFork"]]
    if count_type == "repos":
        # Note: totalCount from the API includes forks and doesn't paginate,
        # so for accounts with 100+ owned repos this undercounts slightly —
        # good enough for a display number, not used for LOC math.
        return len(non_fork_edges)
    elif count_type == "stars":
        return stars_counter(non_fork_edges)


def recursive_loc(
    owner,
    repo_name,
    cache,
    addition_total=0,
    deletion_total=0,
    my_commits=0,
    cursor=None,
):
    """
    Uses GitHub's GraphQL v4 API and cursor pagination to fetch 100 commits from a repository at a time.

    Filters by author server-side (author: {id: ...}) — without this, a huge
    repo like a popular open-source project would force us to paginate
    through its ENTIRE commit history checking every commit's author
    client-side, burning API calls on thousands of commits that aren't yours.
    With the filter, GitHub only ever sends back commits you actually wrote.
    """
    if cursor is not None:
        print(
            f"     ...paginating {owner}/{repo_name} (fetched {my_commits} of your commits so far)"
        )
    query_count("recursive_loc")
    query = """
    query ($repo_name: String!, $owner: String!, $cursor: String, $author_id: ID!) {
        repository(name: $repo_name, owner: $owner) {
            defaultBranchRef {
                target {
                    ... on Commit {
                        history(first: 100, after: $cursor, author: {id: $author_id}) {
                            totalCount
                            edges {
                                node {
                                    ... on Commit {
                                        committedDate
                                    }
                                    deletions
                                    additions
                                }
                            }
                            pageInfo {
                                endCursor
                                hasNextPage
                            }
                        }
                    }
                }
            }
        }
    }"""
    variables = {
        "repo_name": repo_name,
        "owner": owner,
        "cursor": cursor,
        "author_id": OWNER_ID["id"],
    }
    request = post_graphql(query, variables)
    if request.status_code == 200:
        if request.json()["data"]["repository"]["defaultBranchRef"] is not None:
            return loc_counter_one_repo(
                owner,
                repo_name,
                cache,
                request.json()["data"]["repository"]["defaultBranchRef"]["target"][
                    "history"
                ],
                addition_total,
                deletion_total,
                my_commits,
            )
        else:
            return 0, 0, 0
    force_close_file(cache)
    if request.status_code == 403:
        raise GitHubStatsError(
            "Too many requests in a short amount of time — hit GitHub's non-documented anti-abuse rate limit"
        )
    raise GitHubStatsError(
        f"recursive_loc() failed with {request.status_code}: {request.text} (queries so far: {QUERY_COUNT})"
    )


def loc_counter_one_repo(
    owner, repo_name, cache, history, addition_total, deletion_total, my_commits
):
    """
    Recursively call recursive_loc (GraphQL can only search 100 commits at a time).
    Every edge here is already guaranteed to be authored by you — the
    author filter in the query does that server-side now, so no client-side
    author check is needed anymore.
    """
    for node in history["edges"]:
        my_commits += 1
        addition_total += node["node"]["additions"]
        deletion_total += node["node"]["deletions"]

    if history["edges"] == [] or not history["pageInfo"]["hasNextPage"]:
        return addition_total, deletion_total, my_commits
    else:
        return recursive_loc(
            owner,
            repo_name,
            cache,
            addition_total,
            deletion_total,
            my_commits,
            history["pageInfo"]["endCursor"],
        )


def fetch_owned_repo_edges(owner_affiliation, cursor=None, edges=None):
    """
    Fetches repos where you're OWNER/COLLABORATOR/ORGANIZATION_MEMBER — i.e.
    repos GitHub considers you formally affiliated with. This does NOT include
    open-source repos where you only have merged PRs with no collaborator
    access — see fetch_external_contribution_repos() for those.

    Forks are excluded: a forked repo's commit history is really the upstream
    repo's history, so counting it would double-count LOC that either belongs
    to someone else entirely, or gets counted a second time if the upstream
    repo also shows up via fetch_external_contribution_repos().
    """
    if edges is None:
        edges = []
    query_count("fetch_owned_repo_edges")
    query = """
    query ($owner_affiliation: [RepositoryAffiliation], $login: String!, $cursor: String) {
        user(login: $login) {
            repositories(first: 60, after: $cursor, ownerAffiliations: $owner_affiliation) {
                edges {
                    node {
                        ... on Repository {
                            nameWithOwner
                            isFork
                            defaultBranchRef {
                                target {
                                    ... on Commit {
                                        history {
                                            totalCount
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }"""
    variables = {
        "owner_affiliation": owner_affiliation,
        "login": USER_NAME,
        "cursor": cursor,
    }
    request = simple_request(fetch_owned_repo_edges.__name__, query, variables)
    repos = request.json()["data"]["user"]["repositories"]
    page_edges = [e for e in repos["edges"] if not e["node"]["isFork"]]
    skipped = len(repos["edges"]) - len(page_edges)
    if skipped:
        print(f"  -> Skipping {skipped} forked repo(s) on this page")
    if repos["pageInfo"]["hasNextPage"]:
        edges += page_edges
        return fetch_owned_repo_edges(
            owner_affiliation, repos["pageInfo"]["endCursor"], edges
        )
    return edges + page_edges


def fetch_external_contribution_repos(username, start_year, end_year):
    """
    Fetches repos you've committed to (via merged PRs, etc.) that you're NOT
    a collaborator/owner/org-member on — this is what actually captures
    open-source contributions. GitHub's API only gives one year per call, so
    this loops year-by-year from account creation to now and de-dupes.
    """
    repos_by_name = {}
    for year in range(start_year, end_year + 1):
        print(f"  -> Checking external contributions for {year}...")
        query_count("fetch_external_contribution_repos")
        query = """
        query($login: String!, $from: DateTime!, $to: DateTime!) {
            user(login: $login) {
                contributionsCollection(from: $from, to: $to) {
                    commitContributionsByRepository(maxRepositories: 100) {
                        repository {
                            nameWithOwner
                            defaultBranchRef {
                                target {
                                    ... on Commit {
                                        history {
                                            totalCount
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }"""
        variables = {
            "login": username,
            "from": f"{year}-01-01T00:00:00Z",
            "to": f"{year}-12-31T23:59:59Z",
        }
        request = simple_request(
            fetch_external_contribution_repos.__name__, query, variables
        )
        by_repo = request.json()["data"]["user"]["contributionsCollection"][
            "commitContributionsByRepository"
        ]
        for entry in by_repo:
            repo = entry["repository"]
            if repo["defaultBranchRef"] is not None:  # skip empty repos
                repos_by_name[repo["nameWithOwner"]] = {"node": repo}
    return list(repos_by_name.values())


def cache_filename():
    return "cache/" + hashlib.sha256(USER_NAME.encode("utf-8")).hexdigest() + ".json"


def repo_cache_key(repo_name):
    """
    Hashes the repo name before it's used as a cache key. This matters
    because cache/ gets committed to your public profile repo — a plain-text
    key like 'YourCompany/internal-project-codename' would sit in public git
    history forever, leaking the repo's existence and name even though the
    repo itself is private. Hashing ALL repos uniformly (not just private
    ones) is simpler than tracking visibility and gives the same protection:
    the aggregate numbers stay public, individual repo names don't.
    """
    return hashlib.sha256(repo_name.encode("utf-8")).hexdigest()


def load_cache():
    try:
        with open(cache_filename(), "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    os.makedirs("cache", exist_ok=True)
    with open(cache_filename(), "w") as f:
        json.dump(cache, f, indent=2, sort_keys=True)


def cache_builder(edges, force_cache=False, loc_add=0, loc_del=0):
    """
    Checks each repo to see if it's changed since it was last cached, by
    hashed name — not by position, so adding/removing a repo no longer
    invalidates everything else the way the old line-indexed txt format did.
    """
    print(f"  -> Checking cache for {len(edges)} repositories...")
    old_cache = {} if force_cache else load_cache()
    if not old_cache:
        print("  -> No cache found (or force_cache set) — starting fresh.")

    new_cache = {}
    rescanned = 0
    for index, edge in enumerate(edges):
        repo_name = edge["node"]["nameWithOwner"]
        cache_key = repo_cache_key(repo_name)
        branch_ref = edge["node"]["defaultBranchRef"]
        live_commit_count = (
            branch_ref["target"]["history"]["totalCount"] if branch_ref else 0
        )
        cached_entry = old_cache.get(cache_key)

        if (
            cached_entry is not None
            and cached_entry.get("total_commits") == live_commit_count
        ):
            new_cache[cache_key] = cached_entry
            continue

        rescanned += 1
        cached_count = cached_entry["total_commits"] if cached_entry else 0
        print(
            f"  -> [{index + 1}/{len(edges)}] {repo_name}: cached={cached_count}, live={live_commit_count} — rescanning..."
        )

        if branch_ref is None:  # empty repo
            new_cache[cache_key] = {
                "total_commits": 0,
                "my_commits": 0,
                "loc_add": 0,
                "loc_del": 0,
            }
        else:
            owner, repo_short = repo_name.split("/")
            add, delete, mine = recursive_loc(owner, repo_short, new_cache)
            new_cache[cache_key] = {
                "total_commits": live_commit_count,
                "my_commits": mine,
                "loc_add": add,
                "loc_del": delete,
            }
        save_cache(
            new_cache
        )  # persist after every repo so a crash mid-run doesn't lose progress

    if rescanned == 0:
        print("  -> All repos already up to date in cache, nothing to rescan.")
    else:
        print(f"  -> Rescanned {rescanned} repo(s) with new commits.")

    save_cache(new_cache)
    for entry in new_cache.values():
        loc_add += entry["loc_add"]
        loc_del += entry["loc_del"]
    return [loc_add, loc_del, loc_add - loc_del]


def force_close_file(cache):
    """
    Saves whatever partial data exists before the program crashes mid-run.
    """
    save_cache(cache)
    print("Error while writing cache. Partial data saved to", cache_filename())


def stars_counter(data):
    total_stars = 0
    for node in data:
        total_stars += node["node"]["stargazers"]["totalCount"]
    return total_stars


def commit_counter():
    """
    Sums total commits from the cache (built by cache_builder). This is the
    GraphQL-derived, author-filtered, commits-ONLY count — used as a fallback
    if fetch_total_contributions() (below) fails, and still the source of
    truth for per-repo commit counts even though it's no longer what's
    displayed as 'Commits' in the card.
    """
    cache = load_cache()
    return sum(entry["my_commits"] for entry in cache.values())


def fetch_total_contributions(username):
    """
    Fetches total contributions per year from an external, UNAUTHENTICATED
    API (github-contributions-api.jogruber.de) that mirrors GitHub's public
    contribution calendar.

    IMPORTANT: despite being displayed under the 'Commits' label per an
    explicit choice, this is NOT a commits-only count — it's the same total
    metric GitHub's contribution graph shows (commits + issues + PRs +
    reviews combined). Confirmed via diagnose_commit_gap.py: GitHub's own
    commit-only count was 1,829 vs this API's yearly total of 2,563 for the
    same account — a real, ~700-contribution difference from non-commit
    activity, not a bug in either number.

    Returns None on any failure so the caller can fall back to
    commit_counter() — this endpoint has no uptime guarantee, unlike
    GitHub's own API.
    """
    print(
        "  -> Fetching total contributions from github-contributions-api.jogruber.de..."
    )
    try:
        resp = requests.get(
            f"https://github-contributions-api.jogruber.de/v4/{username}", timeout=15
        )
        resp.raise_for_status()
        yearly_totals = resp.json()["total"]
        return sum(yearly_totals.values())
    except (
        requests.exceptions.RequestException,
        KeyError,
        ValueError,
        TypeError,
    ) as exc:
        print(
            f"  !! External contributions API failed ({exc}) — falling back to GraphQL-derived commit_counter()."
        )
        return None


def user_getter(username):
    query_count("user_getter")
    query = """
    query($login: String!){
        user(login: $login) {
            id
            createdAt
        }
    }"""
    request = simple_request(user_getter.__name__, query, {"login": username})
    user_data = request.json()["data"]["user"]
    return {"id": user_data["id"]}, user_data["createdAt"]


def follower_getter(username):
    query_count("follower_getter")
    query = """
    query($login: String!){
        user(login: $login) {
            followers {
                totalCount
            }
        }
    }"""
    request = simple_request(follower_getter.__name__, query, {"login": username})
    return int(request.json()["data"]["user"]["followers"]["totalCount"])


def query_count(funct_id):
    QUERY_COUNT[funct_id] += 1


if __name__ == "__main__":
    from datetime import datetime, timezone
    from card_layout import compose_card, compose_svg_card

    print(f"=== Building GitHub stats card for {USER_NAME} ===\n")

    print("[1/8] Fetching your GitHub user ID and account creation date...")
    OWNER_ID, created_at = user_getter(USER_NAME)
    start_year = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").year
    current_year = datetime.now(timezone.utc).year
    print(f"      -> OWNER_ID = {OWNER_ID}, account created {start_year}\n")

    print("[2/8] Fetching repos you own/collaborate on/belong to via org...")
    owned_edges = fetch_owned_repo_edges(
        ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"]
    )
    print(f"      -> {len(owned_edges)} repos\n")

    print(
        f"[3/8] Fetching open-source repos you've contributed to ({start_year}-{current_year})..."
    )
    external_edges = fetch_external_contribution_repos(
        USER_NAME, start_year, current_year
    )
    print(f"      -> {len(external_edges)} external repos found\n")

    print("[4/8] Merging and de-duplicating repo lists...")
    repos_by_name = {}
    for edge in owned_edges + external_edges:
        repos_by_name[edge["node"]["nameWithOwner"]] = edge
    all_edges = list(repos_by_name.values())
    print(
        f"      -> {len(all_edges)} unique repos total (was {len(owned_edges)} before adding open source)\n"
    )

    print("[5/8] Fetching lines-of-code data (this is the slow step on first run)...")
    total_loc = cache_builder(all_edges, force_cache=False)
    print(
        f"      -> total LOC: +{total_loc[0]:,} / -{total_loc[1]:,} (net {total_loc[2]:,})\n"
    )

    print("[6/8] Fetching total contributions (displayed as 'Commits')...")
    commit_data = fetch_total_contributions(USER_NAME)
    if commit_data is None:
        commit_data = commit_counter()
    print(f"      -> {commit_data:,}\n")

    print("[7/8] Fetching stars, followers, and weekly activity...")
    star_data = graph_repos_stars("stars", ["OWNER"])
    repo_data = graph_repos_stars("repos", ["OWNER"])
    contrib_data = len(
        all_edges
    )  # now genuinely reflects open-source contributions too
    follower_data = follower_getter(USER_NAME)
    weekly_totals = contribution_weeks(USER_NAME)
    print(
        f"      -> {star_data} stars, {repo_data} owned repos, contributed to {contrib_data}, {follower_data} followers\n"
    )

    print("[8/8] Assembling the card and writing stats.md...")
    card = compose_card(
        weekly_totals,
        commit_data,
        star_data,
        repo_data,
        contrib_data,
        follower_data,
        total_loc,
    )

    with open("stats.md", "w") as f:
        f.write(card + "\n")
    with open("stats.svg", "w") as f:
        f.write(compose_svg_card(card) + "\n")
    print("      -> stats.md and stats.svg written.\n")

    print("=== Done. Preview below (colors will only render in a real terminal): ===\n")
    print(card)
    print(f"\nTotal GitHub GraphQL API calls: {sum(QUERY_COUNT.values())}")
    print(f"Breakdown: {QUERY_COUNT}")
