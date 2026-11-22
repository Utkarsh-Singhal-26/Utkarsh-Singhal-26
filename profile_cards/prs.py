"""FIG. 06: one card per merged open source PR, each its own image so each links to its PR."""

from datetime import date
from html import escape

from .theme import PAD, WIDTH, arrow, frame, stylesheet, svg, text

HEIGHT = 100
MAX_TITLE = 84


def render(pr, index):
    """`pr`: {repo, number, title, date}. `index`: 1-based position in the list."""
    owner, _, name = pr["repo"].partition("/")
    title = pr["title"]
    if len(title) > MAX_TITLE:
        title = title[: MAX_TITLE - 1] + "…"
    merged = date.fromisoformat(pr["date"][:10]).strftime("%d %b %Y")
    delay = 0.1 + index * 0.05
    repo = (
        f'<text x="{PAD}" y="66" class="o r" font-size="26" font-weight="600" letter-spacing="-.5" '
        f'fill="var(--fg)" style="animation-delay:{delay:.2f}s">{escape(name)}'
        f'<tspan class="m" font-size="11" font-weight="400" letter-spacing="1" '
        f'fill="var(--muted)" dx="10">{escape(owner)}</tspan></text>'
    )
    right = WIDTH - PAD - 30
    body = (
        frame(WIDTH, HEIGHT, f"FIG. 06.{index} · OPEN SOURCE · MERGED")
        + repo
        + text(PAD, 88, title, font="o", size=15, fill="var(--muted)", delay=delay + 0.05)
        + text(
            right,
            66,
            f"#{pr['number']}",
            size=13,
            fill="var(--brand)",
            spacing=1.2,
            anchor="end",
            delay=delay,
        )
        + text(right, 88, merged, fill="var(--muted)", anchor="end", delay=delay + 0.05)
        + arrow(WIDTH - PAD - 8, 52, "var(--fg)", reach=7)
    )
    return svg(WIDTH, HEIGHT, f"{pr['repo']} #{pr['number']}: {pr['title']}", stylesheet(), body)
