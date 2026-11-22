"""Render the open source PR card and the README links under it.

A card is a single image, so it can carry one link. It points at the full merged-PR search, and
each PR gets a text link below it.

Usage: python -m scripts.build_prs prs.json
(prs.json: `gh search prs --json repository,number,createdAt,title,url`)
"""

import json
import os
import re
import sys
from html import escape
from pathlib import Path

from profile_cards import prs

START, END = "<!-- START_LATEST_PRS -->", "<!-- END_LATEST_PRS -->"
LOGIN = os.environ.get("GH_USER", "Utkarsh-Singhal-26")
SEARCH_URL = f"https://github.com/pulls?q=is%3Apr+is%3Amerged+author%3A{LOGIN}+-user%3A{LOGIN}"


def readme_block(pull_requests):
    links = " &nbsp;/&nbsp; ".join(
        f'<a href="{pr["url"]}">{escape(pr["repository"]["name"])}#{pr["number"]}</a>'
        for pr in pull_requests
    )
    return (
        f"{START}\n"
        f'<a href="{SEARCH_URL}"><img src="cards/prs.svg" '
        f'alt="Latest merged open source pull requests" width="100%"></a>\n\n'
        f'<p align="center">{links}</p>\n'
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
