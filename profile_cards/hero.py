"""FIG. 01: the name set in the portfolio's type with guide lines and a dimension callout."""

from datetime import date

from .theme import EASE, POP, WIDTH, frame, stylesheet, svg, text

NAME = "Utkarsh Singhal"
TAGLINE = "I like shipping things people can actually use."
BIRTH_DATE = date(2004, 10, 26)

HEIGHT = 380
LEFT = 32
BASELINE = 196
CAP_HEIGHT, X_HEIGHT, DESCENDER = 84, 59, 24

# Glyph x-offsets of NAME in Outfit 600 at 120px with -0.04em tracking, measured in a browser.
# The callout box is drawn around the final "h" (index 12).
GLYPH_X = [0, 78.7, 120.5, 176.4, 242.1, 286.1, 334.5, 397.1, 415.7, 479.2, 504.1, 566.7]
GLYPH_X += [631.4, 694, 759.7]
NAME_WIDTH = 784.5
CALLOUT_GLYPH = 12

FACTS = (("ROLE", "FULL-STACK DEV"), ("BASE", "INDIA"), ("FOCUS", "OPEN SOURCE + TOOLS"))
FACTS_BOX = (560, 292, 308)  # x, y, width
FACTS_ROW = 22

MOTION = (
    f".w{{animation:wipe 1s {EASE} .5s both}}"
    f"@keyframes wipe{{from{{width:0}}to{{width:{NAME_WIDTH + 8}px}}}}"
    f".hb{{animation:pop .5s {POP} 1.5s both,blink 2.4s ease-in-out 2.4s infinite}}"
)


def age(today):
    return (
        today.year
        - BIRTH_DATE.year
        - ((today.month, today.day) < (BIRTH_DATE.month, BIRTH_DATE.day))
    )


def _guides(cap, x_height, descender):
    lines = (
        (cap, "cap height"),
        (x_height, "x-height"),
        (BASELINE, "baseline"),
        (descender, "descender"),
    )
    out = ""
    for i, (y, label) in enumerate(lines):
        out += (
            f'<g><line class="bx" x1="20" x2="{WIDTH - 20}" y1="{y}" y2="{y}" '
            f'stroke="var(--brand)" stroke-opacity=".55" '
            f'style="animation:draw .8s {EASE} {0.15 + i * 0.1:.2f}s both"/>'
            + text(
                WIDTH - 20,
                y - 4,
                label,
                size=10,
                fill="var(--brand)",
                anchor="end",
                delay=1.2 + i * 0.08,
            )
            + "</g>"
        )
    return out


def _facts():
    x, y, width = FACTS_BOX
    out = (
        f'<g class="r" style="animation-delay:1.7s">'
        f'<rect x="{x}" y="{y}" width="{width}" height="{FACTS_ROW * 3}" fill="none" '
        f'stroke="var(--line)"/>'
    )
    for i, (key, value) in enumerate(FACTS):
        row_bottom = y + FACTS_ROW * (i + 1)
        if i < len(FACTS) - 1:
            out += (
                f'<line x1="{x}" x2="{x + width}" y1="{row_bottom}" y2="{row_bottom}" '
                f'stroke="var(--line)"/>'
            )
        out += text(x + 12, row_bottom - 7, key, size=11, fill="var(--muted)")
        out += text(x + 84, row_bottom - 7, value)
    return out + "</g>"


def render(today=None):
    today = today or date.today()
    cap = BASELINE - CAP_HEIGHT
    h_x = LEFT + GLYPH_X[CALLOUT_GLYPH]
    h_width = GLYPH_X[CALLOUT_GLYPH + 1] - GLYPH_X[CALLOUT_GLYPH] - 4

    name = (
        f'<g clip-path="url(#c)"><text x="{LEFT}" y="{BASELINE}" class="o" font-size="120" '
        f'font-weight="600" letter-spacing="-4.8" fill="var(--fg)">{NAME}</text></g>'
    )
    callout = (
        '<g class="hb" style="transform-box:fill-box;transform-origin:center">'
        f'<rect x="{h_x}" y="{cap - 4}" width="{h_width}" height="{BASELINE - cap + 4}" '
        f'fill="none" stroke="var(--brand)" stroke-dasharray="4 3"/>'
        + text(
            h_x, cap - 10, f"h {round(h_width)} × {BASELINE - cap}", size=11, fill="var(--brand)"
        )
        + "</g>"
    )
    body = (
        frame(WIDTH, HEIGHT, "FIG. 01 · HEADER")
        + text(
            LEFT,
            66,
            f"{age(today)}, he/him · 28.7172°N, 77.1579°E · IST",
            size=13,
            fill="var(--muted)",
            delay=0.1,
        )
        + f'<defs><clipPath id="c"><rect class="w" x="{LEFT}" y="40" height="200" '
        f'width="{NAME_WIDTH + 8}"/></clipPath></defs>'
        + _guides(cap, BASELINE - X_HEIGHT, BASELINE + DESCENDER)
        + name
        + callout
        + text(LEFT, 262, TAGLINE, font="o", size=26, fill="var(--muted)", delay=1.1)
        + text(LEFT, 346, "utkarsh-singhal.is-a.dev ↗", size=13, fill="var(--brand)", delay=1.5)
        + _facts()
    )
    title = f"{NAME}. Full-stack software developer from India. {TAGLINE}"
    return svg(WIDTH, HEIGHT, title, stylesheet(MOTION), body)
