"""FIG. 03: the portfolio's tumbling tech chips, settled into a pile."""

import json
import random

from .theme import ASSETS, BOTTOM_PAD, PAD, WIDTH, frame, stylesheet, svg, text

CHIP_HEIGHT = 36
ROW_HEIGHT = 42
GAP = 8
TOP = 72
MOTION = (
    ".k{transform-box:fill-box;transform-origin:center;transform:rotate(var(--r));"
    "animation:drop 1s cubic-bezier(.3,1.35,.5,1) both}"
    "@keyframes drop{from{opacity:0;transform:translateY(-320px) rotate(calc(var(--r) * 5))}"
    "20%{opacity:1}}"
)


def _rows(widths):
    rows, current, used = [], [], 0
    for index, width in enumerate(widths):
        if current and used + width > WIDTH - 2 * PAD:
            rows.append(current)
            current, used = [], 0
        current.append(index)
        used += width + GAP
    return [*rows, current]


def _chip(chip, x, y, width, rotation, delay):
    icon = ""
    if chip["icon"]:
        icon = (
            f'<svg x="9" y="9" width="18" height="18" viewBox="{chip["vb"]}">{chip["icon"]}</svg>'
        )
    tile = "#0d0d0d" if chip["dark"] else "#fafafa"
    return (
        f'<g transform="translate({x:.1f} {y:.1f})">'
        f'<g class="k" style="--r:{rotation:.1f}deg;animation-delay:{delay:.2f}s">'
        f'<rect width="{width}" height="{CHIP_HEIGHT}" rx="11" fill="{chip["bg"]}"/>'
        f'<rect x="4" y="4" width="28" height="28" rx="8" fill="{tile}"/>{icon}'
        + text(40, 24, chip["label"], font="o", size=15, weight=600, fill=chip["fg"])
        + "</g></g>"
    )


def render(seed=7):
    chips = json.loads((ASSETS / "chips.json").read_text(encoding="utf-8"))
    rng = random.Random(seed)
    rng.shuffle(chips)
    widths = [round(52 + 8.1 * len(chip["label"])) for chip in chips]

    body, count = "", 0
    rows = _rows(widths)
    for row_index, row in enumerate(rows):
        row_width = sum(widths[i] for i in row) + GAP * (len(row) - 1)
        x = PAD + (WIDTH - 2 * PAD - row_width) / 2
        for i in row:
            y = TOP + row_index * ROW_HEIGHT + rng.uniform(-3, 3)
            body += _chip(chips[i], x, y, widths[i], rng.uniform(-9, 9), 0.1 + count * 0.045)
            x += widths[i] + GAP
            count += 1

    height = TOP + (len(rows) - 1) * ROW_HEIGHT + CHIP_HEIGHT + BOTTOM_PAD
    return svg(
        WIDTH,
        height,
        "Tech stack",
        stylesheet(MOTION),
        frame(WIDTH, height, "FIG. 03 · STACK") + body,
    )
