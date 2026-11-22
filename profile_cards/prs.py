"""FIG. 06: recently merged open source pull requests as one list card."""

from datetime import date
from html import escape

from .theme import PAD, WIDTH, frame, stylesheet, svg, text

ROW_HEIGHT = 72
TOP = 56
MAX_TITLE = 70


def _row(pr, y, index):
    owner, _, name = pr["repo"].partition("/")
    title = pr["title"]
    if len(title) > MAX_TITLE:
        title = title[: MAX_TITLE - 1] + "…"
    merged = date.fromisoformat(pr["date"][:10]).strftime("%d %b %Y")
    arrow_x, arrow_y = WIDTH - PAD - 8, y + 34
    repo = (
        f'<text x="{PAD}" y="{y + 28}" class="o" font-size="22" font-weight="600" '
        f'letter-spacing="-.4" fill="var(--fg)">{escape(name)}'
        f'<tspan class="m" font-size="11" font-weight="400" letter-spacing="1" '
        f'fill="var(--muted)" dx="10">{escape(owner)}</tspan></text>'
    )
    return (
        f'<g class="r" style="animation-delay:{0.1 + index * 0.1:.2f}s">'
        f'<line x1="{PAD}" x2="{WIDTH - PAD}" y1="{y}" y2="{y}" stroke="var(--border)"/>'
        + repo
        + text(PAD, y + 52, title, font="o", size=15, fill="var(--muted)")
        + text(
            WIDTH - PAD - 30,
            y + 28,
            f"MERGED · #{pr['number']}",
            size=11,
            fill="var(--brand)",
            spacing=1.2,
            anchor="end",
        )
        + text(WIDTH - PAD - 30, y + 52, merged, fill="var(--muted)", anchor="end")
        + f'<path d="M{arrow_x - 7} {arrow_y + 7}L{arrow_x + 7} {arrow_y - 7}'
        f'M{arrow_x - 2} {arrow_y - 7}H{arrow_x + 7}V{arrow_y + 2}" '
        f'stroke="var(--fg)" fill="none" stroke-width="1.5"/></g>'
    )


def render(prs):
    """`prs`: [{repo, number, title, date}] newest first."""
    height = TOP + max(len(prs), 1) * ROW_HEIGHT + 8
    rows = "".join(_row(pr, TOP + i * ROW_HEIGHT, i) for i, pr in enumerate(prs))
    body = frame(WIDTH, height, "FIG. 06 · OPEN SOURCE · LATEST MERGED PRS") + rows
    return svg(WIDTH, height, "Recently merged open source pull requests", stylesheet(), body)
