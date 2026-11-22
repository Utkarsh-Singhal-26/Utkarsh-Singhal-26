"""Render one tile per open source PR and the README block that links them.

Usage: python -m scripts.build_prs prs.json
(prs.json: `gh search prs --json repository,number,createdAt,title,url`)
"""

import glob
import json
import os
import re
import sys
from pathlib import Path

from profile_cards import prs

START, END = "<!-- START_LATEST_PRS -->", "<!-- END_LATEST_PRS -->"
COLUMNS = 3


def readme_block(pull_requests):
    """Rows of up to COLUMNS tiles. Tiles must sit on one line with nothing between them, or the
    row breaks apart."""
    rows = []
    for start in range(0, len(pull_requests), COLUMNS):
        rows.append(
            "".join(
                f'<a href="{pr["url"]}"><img src="cards/pr-{i}.svg" width="{100 / COLUMNS:.3f}%" '
                f'alt="{pr["repository"]["nameWithOwner"]} #{pr["number"]}"></a>'
                for i, pr in enumerate(pull_requests[start : start + COLUMNS], start + 1)
            )
            + "<br>"
        )
    return "\n".join([START, *rows, END])


def main(path):
    pull_requests = json.loads(Path(path).read_text(encoding="utf-8"))
    for stale in glob.glob("cards/pr-*.svg"):
        os.remove(stale)
    for i, pr in enumerate(pull_requests, 1):
        row = {
            "repo": pr["repository"]["nameWithOwner"],
            "number": pr["number"],
            "title": pr["title"],
            "date": pr["createdAt"],
        }
        tile = prs.render(row, (i - 1) % COLUMNS, COLUMNS)
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
