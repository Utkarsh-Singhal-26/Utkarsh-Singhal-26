"""Open source pull request tiles, one image per PR so each can link to its PR."""

import textwrap
from datetime import date
from html import escape

from .links import INSET, edges, tile
from .theme import arrow, text

HEIGHT = 148
TITLE_CHARS = 36
TITLE_LINES = 2


def _title_lines(title):
    lines = textwrap.wrap(title, TITLE_CHARS)
    if len(lines) > TITLE_LINES:
        lines = lines[:TITLE_LINES]
        lines[-1] = lines[-1][: TITLE_CHARS - 1].rstrip() + "…"
    return lines


def render(pr, column, columns):
    """`pr`: {repo, number, title, date}. Tile `column` of a row of `columns`."""
    unit, left, right = edges(column, columns)
    owner, _, name = pr["repo"].partition("/")
    merged = date.fromisoformat(pr["date"][:10]).strftime("%d %b %Y")
    x, delay = left + 20, 0.1 + column * 0.08
    body = (
        f'<rect x="{left}" y="{INSET}" width="{right - left:.1f}" height="{HEIGHT - 2 * INSET}" '
        f'fill="var(--bg)" stroke="var(--border)"/>'
        + text(
            x,
            32,
            f"MERGED · #{pr['number']}",
            size=11,
            fill="var(--brand)",
            spacing=1.2,
            delay=delay,
        )
        + (
            f'<text x="{x}" y="62" class="o r" font-size="22" font-weight="600" letter-spacing="-.4" '
            f'fill="var(--fg)" style="animation-delay:{delay:.2f}s">{escape(name)}'
            f'<tspan class="m" font-size="11" font-weight="400" letter-spacing="1" '
            f'fill="var(--muted)" dx="8">{escape(owner)}</tspan></text>'
        )
        + "".join(
            text(x, 86 + i * 18, line, font="o", size=14, fill="var(--muted)", delay=delay + 0.05)
            for i, line in enumerate(_title_lines(pr["title"]))
        )
        + text(x, HEIGHT - 18, merged, fill="var(--muted)", delay=delay + 0.1)
        + arrow(right - 22, 30, "var(--brand)")
    )
    return tile(f"{pr['repo']} #{pr['number']}: {pr['title']}", HEIGHT, body, unit)
