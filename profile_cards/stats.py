"""FIG. 04: headline GitHub numbers and the lines-of-code split."""

from .theme import EASE, PAD, WIDTH, big_number, caption, frame, stylesheet, svg, text

HEIGHT = 270
BAR_X = 400
MOTION = f".f{{animation:draw 1s {EASE} both}}"


def render(*, commits, stars, repos, contributed, followers, added, deleted):
    tiles = (
        ("COMMITS", commits),
        ("STARS", stars),
        ("REPOS", repos),
        ("CONTRIBUTED TO", contributed),
        ("FOLLOWERS", followers),
    )
    tile_width = (WIDTH - 2 * PAD) / len(tiles)
    body = frame(WIDTH, HEIGHT, "FIG. 04 · GITHUB")
    for i, (name, value) in enumerate(tiles):
        x = PAD + i * tile_width
        if i:
            body += (
                f'<line x1="{x - 12:.1f}" x2="{x - 12:.1f}" y1="64" y2="134" '
                f'stroke="var(--border)"/>'
            )
        body += big_number(f"{x:.1f}", 108, f"{value:,}", delay=0.1 + i * 0.08)
        body += caption(f"{x:.1f}", 134, name, 0.2 + i * 0.08)

    bar_width = WIDTH - PAD - BAR_X
    added_share = added / max(added + deleted, 1)
    body += (
        f'<line x1="{PAD}" x2="{WIDTH - PAD}" y1="164" y2="164" stroke="var(--border)"/>'
        + caption(PAD, 192, "LINES OF CODE · NET", 0.7)
        + big_number(PAD, 232, f"{added - deleted:,}", 36, 0.8)
        + caption(BAR_X, 192, "ADDED / REMOVED", 0.9)
        + f'<rect x="{BAR_X}" y="206" width="{bar_width}" height="10" fill="var(--line)"/>'
        + f'<rect class="bx f" x="{BAR_X}" y="206" width="{bar_width * added_share:.1f}" '
        f'height="10" fill="var(--brand)" style="animation-delay:1s"/>'
        + text(BAR_X, 240, f"+{added:,}", fill="var(--brand)", delay=1.1)
        + text(WIDTH - PAD, 240, f"−{deleted:,}", fill="var(--muted)", anchor="end", delay=1.1)
    )
    title = f"GitHub stats: {commits:,} commits, {stars:,} stars, {followers:,} followers"
    return svg(WIDTH, HEIGHT, title, stylesheet(MOTION), body)
