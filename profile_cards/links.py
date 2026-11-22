"""Link tiles: a row of bordered cells, each its own image so each can carry its own link."""

from .theme import WIDTH, arrow, stylesheet, svg, text

HEIGHT = 76
INSET = 4  # gap to the neighbouring tile; the outer edges line up with the full-width cards
NAV = (
    ("Portfolio", "utkarsh-singhal.is-a.dev", "https://utkarsh-singhal.is-a.dev/"),
    ("LinkedIn", "in/singhalutkarsh26", "https://www.linkedin.com/in/singhalutkarsh26"),
    (
        "Resume",
        "drive.google.com",
        "https://drive.google.com/file/d/1cIGjSvD9CLdq3WMwDn7WAjGpt0bq-Jhk/view",
    ),
    ("Email", "singhalutkarsh26@gmail.com", "mailto:singhalutkarsh26@gmail.com"),
)


def render(label, sub, index, count):
    """Tile `index` of a row of `count`. Tiles are drawn at the scale of a full-width card, so
    the outer edges line up with the cards above and below."""
    unit = (WIDTH + 16) / count
    left = 8 if index == 0 else INSET
    right = unit - (8 if index == count - 1 else INSET)
    body = (
        f'<rect x="{left}" y="{INSET}" width="{right - left:.1f}" height="{HEIGHT - 2 * INSET}" '
        f'fill="var(--bg)" stroke="var(--border)"/>'
        + text(
            left + 20,
            38,
            label,
            font="o",
            size=22,
            weight=600,
            delay=0.1 + index * 0.08,
        )
        + text(left + 20, 58, sub, size=11, fill="var(--muted)", delay=0.15 + index * 0.08)
        + arrow(right - 22, 30, "var(--brand)")
    )
    return svg(
        unit,
        HEIGHT,
        f"{label}: {sub}",
        stylesheet(),
        body,
        viewbox=f"0 0 {unit:.1f} {HEIGHT}",
    )
