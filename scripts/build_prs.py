"""Render one card per merged open source PR and the README block that links them.

GitHub strips CSS from READMEs, so a custom look is only possible as an image, and an image
carries one link. Each PR is therefore its own card, stacked inside the README's centred block.

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


def readme_block(pull_requests):
    cards = [
        f'<a href="{pr["url"]}"><img src="cards/pr-{i}.svg" width="100%" '
        f'alt="{pr["repository"]["nameWithOwner"]} #{pr["number"]}"></a><br>'
        for i, pr in enumerate(pull_requests, 1)
    ]
    return "\n".join([START, *cards, END])


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
        Path(f"cards/pr-{i}.svg").write_text(prs.render(row, i) + "\n", encoding="utf-8")

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
