"""Render the open source PR card and the README block under it.

The card is one image, so it links to the full merged-PR search. Each PR gets its own link tile
in a row beneath it.

Usage: python -m scripts.build_prs prs.json
(prs.json: `gh search prs --json repository,number,createdAt,title,url`)
"""

import glob
import json
import os
import re
import sys
from pathlib import Path

from profile_cards import links, prs

START, END = "<!-- START_LATEST_PRS -->", "<!-- END_LATEST_PRS -->"
LOGIN = os.environ.get("GH_USER", "Utkarsh-Singhal-26")
SEARCH_URL = f"https://github.com/pulls?q=is%3Apr+is%3Amerged+author%3A{LOGIN}+-user%3A{LOGIN}"


def readme_block(pull_requests):
    count = len(pull_requests)
    # Tiles must sit on one line with nothing between them, or the row breaks apart.
    tiles = "".join(
        f'<a href="{pr["url"]}"><img src="cards/pr-{i}.svg" width="{100 / count:.3f}%" '
        f'alt="{pr["repository"]["nameWithOwner"]} #{pr["number"]}"></a>'
        for i, pr in enumerate(pull_requests, 1)
    )
    return (
        f"{START}\n"
        f'<a href="{SEARCH_URL}"><img src="cards/prs.svg" '
        f'alt="Latest merged open source pull requests" width="100%"></a>\n\n'
        f"{tiles}\n"
        f"{END}"
    )


def main(path):
    pull_requests = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = [
        {
            "repo": pr["repository"]["nameWithOwner"],
            "number": pr["number"],
            "title": pr["title"],
            "date": pr["createdAt"],
        }
        for pr in pull_requests
    ]
    Path("cards/prs.svg").write_text(prs.render(rows) + "\n", encoding="utf-8")
    for stale in glob.glob("cards/pr-*.svg"):
        os.remove(stale)
    for i, pr in enumerate(pull_requests, 1):
        label = f"{pr['repository']['name']}#{pr['number']}"
        tile = links.render(
            label,
            f"{pr['repository']['nameWithOwner'].split('/')[0]} · MERGED",
            i - 1,
            len(pull_requests),
        )
        Path(f"cards/pr-{i}.svg").write_text(tile + "\n", encoding="utf-8")

    readme = Path("README.md")
    updated, count = re.subn(
        f"{re.escape(START)}.*?{re.escape(END)}",
        lambda _: readme_block(pull_requests),
        readme.read_text(encoding="utf-8"),
        flags=re.DOTALL,
    )
    if count != 1:
        raise SystemExit("README.md is missing the START_LATEST_PRS / END_LATEST_PRS markers")
    readme.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
