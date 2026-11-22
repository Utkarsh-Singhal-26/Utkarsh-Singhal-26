"""Fetch GitHub data and write the hero, heatmap, stats, stack and activity cards.

Usage: ACCESS_TOKEN=... USER_NAME=... python -m scripts.build_cards
"""

import os
from datetime import UTC, datetime
from pathlib import Path

from profile_cards import activity, heatmap, hero, links, stack, stats
from profile_cards.github import GitHub

CARDS_DIR = Path("cards")
RECENT_DAYS = 30


def main():
    login = os.environ["USER_NAME"]
    github = GitHub(os.environ["ACCESS_TOKEN"], login)

    user_id, created_at, followers = github.profile()
    first_year, this_year = int(created_at[:4]), datetime.now(UTC).year

    print("Collecting repositories...")
    repos = {
        repo["name"]: repo
        for repo in github.affiliated_repos() + github.external_repos(first_year, this_year)
    }
    print(f"Counting lines of code across {len(repos)} repositories...")
    added, deleted = github.lines_of_code(list(repos.values()), user_id)

    owned_repos, stars = github.owned_stats()
    history = github.history(created_at)
    cards = {
        "hero": hero.render(),
        "heatmap": heatmap.render(github.calendar()),
        "stats": stats.render(
            commits=sum(count for _, count in history),
            stars=stars,
            repos=owned_repos,
            contributed=len(repos),
            followers=followers,
            added=added,
            deleted=deleted,
        ),
        "stack": stack.render(),
        "activity": activity.render(history[-RECENT_DAYS:], history),
    }
    for i, (label, sub, _) in enumerate(links.NAV):
        cards[f"link-{label.lower()}"] = links.render(label, sub, i, len(links.NAV))

    CARDS_DIR.mkdir(exist_ok=True)
    for name, svg in cards.items():
        (CARDS_DIR / f"{name}.svg").write_text(svg + "\n", encoding="utf-8")
    print(f"Wrote {', '.join(f'{name}.svg' for name in cards)}")


if __name__ == "__main__":
    main()
