"""FIG. 06: all-time coding time from WakaTime, as a strip of cells split by language."""

from .theme import BOTTOM_PAD, HEADLINE_Y, PAD, WIDTH, caption, frame, stylesheet, svg, text

LEGEND_Y = 206  # top of the legend swatches
DURATION_Y = LEGEND_Y + 68
HEIGHT = DURATION_Y + BOTTOM_PAD
CELLS = 60
MAX_LANGUAGES = 5
STRIP_Y, STRIP_HEIGHT = HEADLINE_Y + 28, 30
MOTION = ".c{animation:fade .4s ease-out both}@keyframes fade{from{opacity:0}to{opacity:1}}"


def _allocate_cells(percents):
    """Split CELLS between languages by share using largest remainders, so the strip is as long
    as the combined share. Anything left over is "other" and stays empty."""
    exact = [percent / 100 * CELLS for percent in percents]
    cells = [int(share) for share in exact]
    spare = round(sum(exact)) - sum(cells)
    for i in sorted(range(len(exact)), key=lambda i: exact[i] - cells[i], reverse=True)[:spare]:
        cells[i] += 1
    return cells


def _strip(fills, allocation):
    step = (WIDTH - 2 * PAD + 3) / CELLS
    colours = [fill for fill, count in zip(fills, allocation, strict=True) for _ in range(count)]
    colours += ["var(--cell)"] * (CELLS - len(colours))
    return "".join(
        f'<rect class="c" x="{PAD + i * step:.1f}" y="{STRIP_Y}" width="{step - 3:.1f}" '
        f'height="{STRIP_HEIGHT}" fill="{fill}" style="animation-delay:{0.2 + i * 0.018:.2f}s"/>'
        for i, fill in enumerate(colours)
    )


def _legend(languages, fills):
    column = (WIDTH - 2 * PAD) / len(languages)
    out = ""
    for i, language in enumerate(languages):
        x = PAD + i * column
        hours, minutes = language.get("hours", 0), language.get("minutes", 0)
        duration = f"{hours:,} hrs {minutes} mins" if hours else f"{minutes} mins"
        percent = (
            f'<text x="{x:.1f}" y="{LEGEND_Y + 44}" class="o" font-size="30" font-weight="600" '
            f'letter-spacing="-.5" fill="var(--fg)">{language["percent"]:.1f}'
            f'<tspan font-size="16" fill="var(--muted)">%</tspan></text>'
        )
        out += (
            f'<g class="r" style="animation-delay:{1.2 + i * 0.08:.2f}s">'
            f'<rect x="{x:.1f}" y="{LEGEND_Y}" width="10" height="10" fill="{fills[i]}"/>'
            + text(f"{x + 18:.1f}", LEGEND_Y + 10, language["name"], font="o", size=18, weight=600)
            + percent
            + text(f"{x:.1f}", DURATION_Y, duration, fill="var(--muted)")
            + "</g>"
        )
    return out


def render(stats):
    """`stats`: the `data` object of WakaTime's all_time stats endpoint."""
    languages = stats["languages"][:MAX_LANGUAGES]
    total = stats["human_readable_total"]
    hours, _, rest = total.partition(" hrs")
    fills = [f"var(--l{4 - i})" if i < 4 else "var(--line)" for i in range(len(languages))]
    allocation = _allocate_cells([language["percent"] for language in languages])

    headline = (
        f'<text x="{PAD}" y="{HEADLINE_Y}" class="o r" font-size="56" font-weight="600" letter-spacing="-1.5" '
        f'fill="var(--fg)">{hours}<tspan font-size="24" font-weight="400" letter-spacing="0" '
        f'fill="var(--muted)"> hrs{rest}</tspan></text>'
    )
    body = (
        frame(WIDTH, HEIGHT, "FIG. 06 · CODING TIME")
        + headline
        + caption(WIDTH - PAD, HEADLINE_Y, "WAKATIME · ALL TIME", 0.2, "end")
        + _strip(fills, allocation)
        + _legend(languages, fills)
    )
    return svg(WIDTH, HEIGHT, f"Coding time: {total}", stylesheet(MOTION), body)
