"""Render the open source PR card and its README block.

GitHub strips CSS from READMEs, so a custom look is only possible as an image, and an image
carries one link. The card therefore links to the full merged-PR search.

Usage: python -m scripts.build_prs prs.json
(prs.json: `gh search prs --json repository,number,createdAt,title`)
"""

import glob
import json
import os
import re
import sys
from pathlib import Path

from profile_cards import prs

START, END = "<!-- START_LATEST_PRS -->", "<!-- END_LATEST_PRS -->"
LOGIN = os.environ.get("GH_USER", "Utkarsh-Singhal-26")
SEARCH_URL = f"https://github.com/pulls?q=is%3Apr+is%3Amerged+author%3A{LOGIN}+-user%3A{LOGIN}"
BLOCK = (
    f"{START}\n"
    f'<a href="{SEARCH_URL}"><img src="cards/prs.svg" '
    f'alt="Latest merged open source pull requests" width="100%"></a><br>\n'
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

    readme = Path("README.md")
    updated, count = re.subn(
        f"{re.escape(START)}.*?{re.escape(END)}",
        lambda _: BLOCK,
        readme.read_text(encoding="utf-8"),
        flags=re.DOTALL,
    )
    if count != 1:
        raise SystemExit("README.md is missing the START_LATEST_PRS / END_LATEST_PRS markers")
    readme.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
