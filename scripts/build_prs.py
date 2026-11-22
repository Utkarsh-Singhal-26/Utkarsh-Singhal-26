"""Rewrite the open source PR table in the README.

GitHub strips CSS from READMEs, so this is a plain HTML table: it picks up GitHub's own styling and
every repo and PR is a real link.

Usage: python -m scripts.build_prs prs.json
(prs.json: `gh search prs --json repository,number,createdAt,title,url`)
"""

import json
import re
import sys
from datetime import date
from html import escape
from pathlib import Path

START, END = "<!-- START_LATEST_PRS -->", "<!-- END_LATEST_PRS -->"


def readme_block(pull_requests):
    rows = "\n".join(
        "<tr>"
        f'<td><a href="https://github.com/{pr["repository"]["nameWithOwner"]}">'
        f"{escape(pr['repository']['nameWithOwner'])}</a></td>"
        f'<td><a href="{pr["url"]}">{escape(pr["title"])}</a> (#{pr["number"]})</td>'
        f"<td>{date.fromisoformat(pr['createdAt'][:10]).strftime('%d %b %Y')}</td>"
        "</tr>"
        for pr in pull_requests
    )
    header = "<tr><th>Repository</th><th>Merged pull request</th><th>Date</th></tr>"
    return f"{START}\n<table>\n{header}\n{rows}\n</table>\n{END}"


def main(path):
    pull_requests = json.loads(Path(path).read_text(encoding="utf-8"))
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
