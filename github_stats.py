"""
Generates a GitHub statistics card for a user.

This module fetches repository, contribution, follower, star, and
lines-of-code statistics using the GitHub GraphQL API. It caches
repository analysis to avoid repeated expensive requests, then
renders the collected statistics as both Markdown and SVG output.
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone

import requests

from card_layout import compose_card, compose_svg_card

# Fine-grained PAT scoped to All Repositories:
#   Account: read:Followers, read:Starring, read:Watching
#   Repository: read:Commit statuses, read:Contents, read:Issues,
#               read:Metadata, read:Pull Requests
#
# Fine-grained PATs can't access private repos you're only a collaborator on
# (owned by another individual, not an org/yourself) — a documented GitHub
# gap. Use a classic PAT with `repo` scope for that case; this script
# doesn't care which token type it gets, just the string.
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


class GitHubStatsError(Exception):
    """
    Raised for any GitHub API failure in this script.
    """


def post_graphql(query, variables, max_retries=4, base_delay=3):
    """
    POST with retry + exponential backoff for transient failures only
    (network errors, 502/503/504). Does not retry 4xx errors — those need a
    person to look at them, not another automatic attempt.
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
                f"  !! Network error, retrying in {wait}s ({attempt}/{max_retries})..."
            )
            time.sleep(wait)
            continue

        if response.status_code == 200:
            return response

        if response.status_code in (502, 503, 504) and attempt < max_retries:
            wait = base_delay * (2 ** (attempt - 1))
            print(
                f"  !! HTTP {response.status_code}, retrying in {wait}s ({attempt}/{max_retries})..."
            )
            time.sleep(wait)
            continue

        return response  # non-retryable, or retries exhausted — caller raises

    return response


def save_error_detail(context, request):
    """
    Writes the full raw error response to a LOCAL-ONLY file (never
    committed) instead of the exception message. GitHub's error text can
    embed repo names, and exception messages tend to get pasted around when
    debugging — this keeps that detail local by default.
    """
    with open("last_api_error.txt", "w", encoding="utf-8") as f:
        f.write(f"Context: {context}\nStatus: {request.status_code}\n\n{request.text}")


def simple_request(func_name, query, variables):
    request = post_graphql(query, variables)
    if request.status_code == 200:
        return request
    save_error_detail(func_name, request)
    raise GitHubStatsError(
        f"{func_name} failed with {request.status_code} "
        f"(queries so far: {QUERY_COUNT}). Details in last_api_error.txt."
    )


def contribution_weeks(username):
    """
    Fetches the past year's contribution calendar, grouped by week.
    """
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
    calendar = request.json()["data"]["user"]["contributionsCollection"][
        "contributionCalendar"
    ]
    return [
        sum(d["contributionCount"] for d in w["contributionDays"])
        for w in calendar["weeks"]
    ]


def graph_repos_stars(count_type, owner_affiliation, cursor=None):
    """
    Returns repo or star count, excluding forks (a fork isn't really
    "your" repo or "your" stars for display purposes here).
    """
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
        # totalCount includes forks and doesn't paginate, so 100+ owned repos
        # would slightly undercount here — fine for display, unused in LOC math.
        return len(non_fork_edges)
    elif count_type == "stars":
        return stars_counter(non_fork_edges)


def recursive_loc(
    owner,
    repo_name,
    owner_id,
    cache,
    addition_total=0,
    deletion_total=0,
    my_commits=0,
    cursor=None,
):
    """
    Paginates a repo's commit history 100 at a time, filtered by author
    server-side (author: {id: ...}) so a huge repo doesn't force us to walk
    its entire history checking every commit's author client-side.
    """
    if cursor is not None:
        print(f"     ...paginating (fetched {my_commits} of your commits so far)")
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
        "author_id": owner_id["id"],
    }
    request = post_graphql(query, variables)
    if request.status_code == 200:
        repo_data = request.json()["data"]["repository"]
        if repo_data["defaultBranchRef"] is not None:
            history = repo_data["defaultBranchRef"]["target"]["history"]
            return loc_counter_one_repo(
                owner,
                repo_name,
                owner_id,
                cache,
                history,
                addition_total,
                deletion_total,
                my_commits,
            )
        return 0, 0, 0
    force_close_file(cache)
    if request.status_code == 403:
        raise GitHubStatsError("Hit GitHub's non-documented anti-abuse rate limit")
    save_error_detail("recursive_loc", request)
    raise GitHubStatsError(
        f"recursive_loc() failed with {request.status_code} "
        f"(queries so far: {QUERY_COUNT}). Details in last_api_error.txt."
    )


def loc_counter_one_repo(
    owner,
    repo_name,
    owner_id,
    cache,
    history,
    addition_total,
    deletion_total,
    my_commits,
):
    """
    Sums additions/deletions across pages. Every edge here is already
    guaranteed to be authored by you — the query filters server-side.
    """
    for node in history["edges"]:
        my_commits += 1
        addition_total += node["node"]["additions"]
        deletion_total += node["node"]["deletions"]

    if history["edges"] == [] or not history["pageInfo"]["hasNextPage"]:
        return addition_total, deletion_total, my_commits
    return recursive_loc(
        owner,
        repo_name,
        owner_id,
        cache,
        addition_total,
        deletion_total,
        my_commits,
        history["pageInfo"]["endCursor"],
    )


def fetch_owned_repo_edges(owner_affiliation, cursor=None, edges=None):
    """
    Fetches repos where you're OWNER/COLLABORATOR/ORGANIZATION_MEMBER —
    repos GitHub considers you formally affiliated with. Does NOT include
    open-source repos with no collaborator access; see
    fetch_external_contribution_repos() for those. Forks are excluded, since
    a fork's commit history really belongs to the upstream repo.
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
    Fetches repos you've committed to without collaborator access — this
    is what captures open-source contributions. GitHub only gives one year
    per call, so this loops year-by-year and de-dupes by repo name.
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
    Hashes the repo name before using it as a cache key — cache/ gets
    committed to a public repo, and a plain-text key would leak a private
    repo's existence/name into public git history forever.
    """
    return hashlib.sha256(repo_name.encode("utf-8")).hexdigest()


def load_cache():
    try:
        with open(cache_filename(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_cache(cache):
    os.makedirs("cache", exist_ok=True)
    with open(cache_filename(), "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, sort_keys=True)


def cache_builder(edges, owner_id, force_cache=False, loc_add=0, loc_del=0):
    """
    Checks each repo by hashed name (not position) for changes since last
    cached, and rescans only what changed.
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
            f"  -> [{index + 1}/{len(edges)}] cached={cached_count}, live={live_commit_count} — rescanning..."
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
            add, delete, mine = recursive_loc(
                owner,
                repo_short,
                owner_id,
                new_cache,
            )
            new_cache[cache_key] = {
                "total_commits": live_commit_count,
                "my_commits": mine,
                "loc_add": add,
                "loc_del": delete,
            }
        save_cache(
            new_cache
        )  # after every repo, so a crash mid-run doesn't lose progress

    if rescanned == 0:
        print("  -> All repos already up to date, nothing to rescan.")
    else:
        print(f"  -> Rescanned {rescanned} repo(s) with new commits.")

    save_cache(new_cache)
    for entry in new_cache.values():
        loc_add += entry["loc_add"]
        loc_del += entry["loc_del"]
    return [loc_add, loc_del, loc_add - loc_del]


def force_close_file(cache):
    """
    Saves partial progress before the program crashes mid-run.
    """
    save_cache(cache)
    print("Error while writing cache. Partial data saved to", cache_filename())


def stars_counter(data):
    return sum(node["node"]["stargazers"]["totalCount"] for node in data)


def commit_counter():
    """
    Sums commits from cache — the author-filtered, commits-only count.
    Used as a fallback if fetch_total_contributions() fails, and still the
    source of truth for per-repo commit counts even though it's no longer
    what's displayed as 'Commits' in the card.
    """
    cache = load_cache()
    return sum(entry["my_commits"] for entry in cache.values())


def fetch_total_contributions(username):
    """
    Fetches total contributions per year from an external, unauthenticated
    API mirroring GitHub's public contribution calendar.

    NOT commits-only, despite being shown under the 'Commits' label by
    choice — it's commits + issues + PRs + reviews combined. Verified via
    diagnose_commit_gap.py: GitHub's own commit-only count was 1,829 vs this
    API's 2,563 for the same account, a real ~700 gap from non-commit
    activity, not a bug in either number.

    Returns None on failure so the caller can fall back to commit_counter()
    — this endpoint has no uptime guarantee, unlike GitHub's own API.
    """
    print("  -> Fetching total contributions (external API)...")
    try:
        resp = requests.get(
            f"https://github-contributions-api.jogruber.de/v4/{username}", timeout=15
        )
        resp.raise_for_status()
        return sum(resp.json()["total"].values())
    except (
        requests.exceptions.RequestException,
        KeyError,
        ValueError,
        TypeError,
    ) as exc:
        print(
            f"  !! External contributions API failed ({exc}) — falling back to commit_counter()."
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


def main():
    # Local imports: datetime is only needed here, and card_layout must be
    # importable relative to this script's own location, not at module load.
    print(f"=== Building GitHub stats card for {USER_NAME} ===\n")

    print("[1/8] Fetching user ID and account creation date...")
    owner_id, created_at = user_getter(USER_NAME)
    start_year = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").year
    current_year = datetime.now(timezone.utc).year
    print(f"      -> account created {start_year}\n")

    print("[2/8] Fetching repos you own/collaborate on/belong to via org...")
    owned_edges = fetch_owned_repo_edges(
        ["OWNER", "COLLABORATOR", "ORGANIZATION_MEMBER"]
    )
    print(f"      -> {len(owned_edges)} repos\n")

    print(
        f"[3/8] Fetching open-source repos contributed to ({start_year}-{current_year})..."
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
        f"      -> {len(all_edges)} unique repos total (was {len(owned_edges)} before open source)\n"
    )

    print("[5/8] Fetching lines-of-code data (slow on first run)...")
    total_loc = cache_builder(all_edges, owner_id, force_cache=False)
    print(
        f"      -> LOC: +{total_loc[0]:,} / -{total_loc[1]:,} (net {total_loc[2]:,})\n"
    )

    print("[6/8] Fetching total contributions (displayed as 'Commits')...")
    commit_data = fetch_total_contributions(USER_NAME)
    if commit_data is None:
        commit_data = commit_counter()
    print(f"      -> {commit_data:,}\n")

    print("[7/8] Fetching stars, followers, and weekly activity...")
    star_data = graph_repos_stars("stars", ["OWNER"])
    repo_data = graph_repos_stars("repos", ["OWNER"])
    contrib_data = len(all_edges)
    follower_data = follower_getter(USER_NAME)
    weekly_totals = contribution_weeks(USER_NAME)
    print(f"      -> {star_data} stars, {repo_data} repos, {follower_data} followers\n")

    print("[8/8] Assembling the card...")
    card = compose_card(
        weekly_totals,
        commit_data,
        star_data,
        repo_data,
        contrib_data,
        follower_data,
        total_loc,
    )

    with open("stats.md", "w", encoding="utf-8") as f:
        f.write(card + "\n")
    with open("stats.svg", "w", encoding="utf-8") as f:
        f.write(compose_svg_card(card) + "\n")
    print("      -> stats.md and stats.svg written.\n")

    print("=== Done ===\n")
    print(card)
    print(f"\nTotal GraphQL calls: {sum(QUERY_COUNT.values())} — {QUERY_COUNT}")


if __name__ == "__main__":
    main()
