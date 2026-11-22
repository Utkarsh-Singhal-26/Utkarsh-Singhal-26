"""Shared look for every card: portfolio colour tokens, fonts, motion and SVG primitives."""

import base64
import colorsys
from html import escape
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "assets"

WIDTH = 900
PAD = 32

# (hue, saturation %, lightness %), taken from the portfolio's globals.css.
LIGHT = {
    "bg": (240, 7, 92),
    "card": (240, 8, 95),
    "border": (240, 7, 83),
    "line": (240, 7, 68),
    "fg": (240, 12, 8),
    "muted": (240, 6, 36),
    "brand": (172, 42, 32),
    "cell": (240, 7, 86),
}
DARK = {
    "bg": (240, 8, 6),
    "card": (240, 8, 8),
    "border": (240, 6, 16),
    "line": (240, 5, 26),
    "fg": (240, 8, 96),
    "muted": (240, 5, 64),
    "brand": (172, 40, 48),
    "cell": (240, 6, 14),
}
LEVEL_MIX = (0, 0.3, 0.55, 0.8, 1)  # empty cell -> brand, exposed as --l0..--l4

FONTS = (
    ("Outfit", 600, "outfit-latin-600-normal.woff"),
    ("Outfit", 400, "outfit-latin-400-normal.woff"),
    ("Geist Mono", 400, "geist-mono-latin-400-normal.woff"),
)

EASE = "cubic-bezier(.16,1,.3,1)"
POP = "cubic-bezier(.2,1.4,.4,1)"


def _hex(hsl):
    hue, sat, light = hsl
    r, g, b = colorsys.hls_to_rgb(hue / 360, light / 100, sat / 100)
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def _mix(start, end, amount):
    a = [int(start[i : i + 2], 16) for i in (1, 3, 5)]
    b = [int(end[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * amount):02x}" for x, y in zip(a, b, strict=True))


def _variables(palette):
    colours = "".join(f"--{name}:{_hex(hsl)};" for name, hsl in palette.items())
    cell, brand = _hex(palette["cell"]), _hex(palette["brand"])
    levels = "".join(f"--l{i}:{_mix(cell, brand, t)};" for i, t in enumerate(LEVEL_MIX))
    return colours + levels


def _font_face(family, weight, filename):
    data = base64.b64encode((ASSETS / "fonts" / filename).read_bytes()).decode()
    return (
        f"@font-face{{font-family:'{family}';font-weight:{weight};"
        f"src:url(data:font/woff;base64,{data}) format('woff')}}"
    )


def stylesheet(extra=""):
    """Fonts, light/dark tokens and the shared keyframes. SVGs shown through <img> cannot load
    web fonts, so they are embedded."""
    return (
        "".join(_font_face(*font) for font in FONTS)
        + f":root{{{_variables(LIGHT)}}}"
        + f"@media (prefers-color-scheme:dark){{:root{{{_variables(DARK)}}}}}"
        + ".o{font-family:Outfit,system-ui,sans-serif}"
        + ".m{font-family:'Geist Mono',ui-monospace,Menlo,monospace}"
        + "@keyframes rise{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:none}}"
        + "@keyframes pop{0%{opacity:0;transform:scale(.6)}70%{transform:scale(1.06)}"
        "100%{opacity:1;transform:none}}"
        + "@keyframes draw{from{transform:scaleX(0)}to{transform:none}}"
        + "@keyframes blink{50%{opacity:.25}}"
        + f".r{{animation:rise .7s {EASE} both}}"
        + ".bx{transform-box:fill-box;transform-origin:left center}"
        + extra
        + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
    )


def text(  # noqa: PLR0913
    x,
    y,
    content,
    *,
    font="m",
    size=12,
    fill="var(--fg)",
    anchor=None,
    weight=None,
    spacing=None,
    delay=None,
    rise=False,
    escape_content=True,
):
    """A <text> element. `delay` (seconds) fades it in with the shared rise animation."""
    classes = font + (" r" if rise or delay is not None else "")
    attrs = f'x="{x}" y="{y}" class="{classes}" font-size="{size}" fill="{fill}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if spacing is not None:
        attrs += f' letter-spacing="{spacing}"'
    if delay is not None:
        attrs += f' style="animation-delay:{delay:.2f}s"'
    body = escape(str(content)) if escape_content else content
    return f"<text {attrs}>{body}</text>"


def big_number(x, y, value, size=44, delay=0, anchor=None):
    return text(
        x, y, value, font="o", size=size, weight=600, spacing=-1, delay=delay, anchor=anchor
    )


def caption(x, y, value, delay=0, anchor=None, size=11):
    return text(
        x, y, value, size=size, fill="var(--muted)", spacing=1.2, delay=delay, anchor=anchor
    )


def _corner_marks(width, height, arm=6):
    path = "".join(
        f"M{x - arm} {y}H{x + arm}M{x} {y - arm}V{y + arm}" for x in (0, width) for y in (0, height)
    )
    return f'<path d="{path}" stroke="var(--fg)" stroke-opacity=".55" fill="none"/>'


def frame(width, height, figure):
    """Hairline border, corner marks and the FIG. label."""
    label = text(PAD, 34, figure, size=12, fill="var(--muted)", spacing=1.5, rise=True)
    return (
        f'<rect width="{width}" height="{height}" fill="var(--bg)" stroke="var(--border)"/>'
        f"{_corner_marks(width, height)}{label}"
    )


def svg(width, height, title, css, body):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="100%" viewBox="-8 -8 {width + 16} {height + 16}" role="img" '
        f'aria-label="{escape(title)}"><style>{css}</style>{body}</svg>'
    )
