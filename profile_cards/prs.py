"""FIG. 05: recently merged open source pull requests as one list card."""

from datetime import date
from html import escape

from .theme import PAD, WIDTH, arrow, frame, stylesheet, svg, text

ROW_HEIGHT = 68
FIRST_ROW_Y = 56
BOTTOM = 16
MAX_TITLE = 72
RIGHT = WIDTH - PAD - 28  # right edge of the number and date column, clear of the arrow


def _row(pr, y, index):
    owner, _, name = pr["repo"].partition("/")
    title = pr["title"]
    if len(title) > MAX_TITLE:
        title = title[: MAX_TITLE - 1] + "…"
    merged = date.fromisoformat(pr["date"][:10]).strftime("%d %b %Y")
    delay = 0.1 + index * 0.1
    repo = (
        f'<text x="{PAD}" y="{y + 30}" class="o" font-size="22" font-weight="600" '
        f'letter-spacing="-.4" fill="var(--fg)">{escape(name)}'
        f'<tspan class="m" font-size="11" font-weight="400" letter-spacing="1" '
        f'fill="var(--muted)" dx="10">{escape(owner)}</tspan></text>'
    )
    return (
        f'<g class="r" style="animation-delay:{delay:.2f}s">'
        f'<line x1="{PAD}" x2="{WIDTH - PAD}" y1="{y}" y2="{y}" stroke="var(--border)"/>'
        + repo
        + text(PAD, y + 52, title, font="o", size=15, fill="var(--muted)")
        + text(RIGHT, y + 30, f"#{pr['number']}", size=12, fill="var(--brand)", anchor="end")
        + text(RIGHT, y + 52, merged, fill="var(--muted)", anchor="end")
        + arrow(WIDTH - PAD - 8, y + ROW_HEIGHT / 2, "var(--fg)", reach=7)
        + "</g>"
    )


def render(prs):
    """`prs`: [{repo, number, title, date}] newest first."""
    height = FIRST_ROW_Y + len(prs) * ROW_HEIGHT + BOTTOM
    rows = "".join(_row(pr, FIRST_ROW_Y + i * ROW_HEIGHT, i) for i, pr in enumerate(prs))
    body = frame(WIDTH, height, "FIG. 05 · OPEN SOURCE · MERGED PRS") + rows
    return svg(WIDTH, height, "Recently merged open source pull requests", stylesheet(), body)
