"""
Renders the weekly contribution bar chart as a self-contained SVG using the
portfolio's design tokens (cool zinc surfaces, single pine-teal accent, light
and dark variants), so the profile README needs no third-party image host.
"""

import colorsys

# (h, s%, l%) copied from portfolio/src/app/globals.css
_LIGHT = {
    "card": (240, 10, 99),
    "border": (240, 8, 88),
    "fg": (240, 12, 8),
    "muted": (240, 6, 42),
    "brand": (172, 42, 32),
}
_DARK = {
    "card": (240, 8, 8),
    "border": (240, 6, 16),
    "fg": (240, 8, 96),
    "muted": (240, 5, 64),
    "brand": (172, 40, 48),
}

WIDTH, HEIGHT, PAD = 712, 220, 24
CHART_TOP, CHART_BOTTOM = 70, HEIGHT - 28


def _hex(hsl):
    h, s, l = hsl
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return f"#{round(r * 255):02x}{round(g * 255):02x}{round(b * 255):02x}"


def _vars(palette):
    return "".join(f"--{k}:{_hex(v)};" for k, v in palette.items())


def render_activity_svg(weekly_totals):
    weeks = weekly_totals or [0]
    peak = max(max(weeks), 1)
    slot = (WIDTH - 2 * PAD) / len(weeks)
    bar_w = slot * 0.62
    chart_h = CHART_BOTTOM - CHART_TOP

    bars = []
    for i, total in enumerate(weeks):
        h = max(total / peak * chart_h, 2)
        x = PAD + i * slot + (slot - bar_w) / 2
        bars.append(
            f'<rect x="{x:.1f}" y="{CHART_BOTTOM - h:.1f}" width="{bar_w:.1f}" '
            f'height="{h:.1f}" rx="2" fill="var(--brand)" '
            f'opacity="{0.35 + 0.65 * total / peak:.2f}"/>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="100%" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="Contributions per week over the last year">'
        f"<style>:root{{{_vars(_LIGHT)}}}"
        f"@media (prefers-color-scheme: dark){{:root{{{_vars(_DARK)}}}}}"
        f"text{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}</style>"
        f'<rect x=".5" y=".5" width="{WIDTH - 1}" height="{HEIGHT - 1}" rx="20" '
        f'fill="var(--card)" stroke="var(--border)"/>'
        f'<text x="{PAD}" y="38" font-size="15" font-weight="600" fill="var(--fg)">'
        f"Contribution activity</text>"
        f'<text x="{PAD}" y="56" font-size="11" fill="var(--muted)">'
        f"{sum(weeks):,} contributions in the last year, per week</text>"
        f'<line x1="{PAD}" x2="{WIDTH - PAD}" y1="{CHART_BOTTOM + .5}" '
        f'y2="{CHART_BOTTOM + .5}" stroke="var(--border)"/>'
        + "".join(bars)
        + f'<text x="{PAD}" y="{HEIGHT - 10}" font-size="10" fill="var(--muted)">'
        f"52 weeks ago</text>"
        f'<text x="{WIDTH - PAD}" y="{HEIGHT - 10}" font-size="10" '
        f'text-anchor="end" fill="var(--muted)">this week</text></svg>'
    )


if __name__ == "__main__":
    import random

    svg = render_activity_svg([random.randint(0, 40) for _ in range(53)])
    assert svg.startswith("<svg") and svg.count("<rect") == 54
    assert render_activity_svg([]).startswith("<svg")
    print("ok")
