"""FIG. 05: the last 30 days as segmented bars, plus all-time activity stats."""

from datetime import date

from .theme import (
    BOTTOM_PAD,
    HEADLINE_Y,
    PAD,
    POP,
    WIDTH,
    big_number,
    caption,
    frame,
    stylesheet,
    svg,
    text,
)

BASELINE = 282
AXIS_Y = BASELINE + 28
HEIGHT = AXIS_Y + BOTTOM_PAD
BAR_GAP = 6
SEGMENT, SEGMENT_GAP, MAX_SEGMENTS = 6, 2, 14
STAT_SPACING = 130
MOTION = f".c{{transform-box:fill-box;transform-origin:bottom;animation:pop .4s {POP} both}}"


def all_time_stats(history):
    """`history`: [(iso_date, count)] oldest first. Returns active days, average contributions
    per day since the first contribution, current streak and longest streak."""
    counts = [count for _, count in history]
    first_active = next((i for i, count in enumerate(counts) if count), 0)
    average = sum(counts) / max(len(counts) - first_active, 1)

    longest = run = 0
    for count in counts:
        run = run + 1 if count else 0
        longest = max(longest, run)

    current = 0
    # Today may not have a contribution yet, so a streak is allowed to end yesterday.
    for count in reversed(counts if counts and counts[-1] else counts[:-1]):
        if not count:
            break
        current += 1
    return sum(1 for count in counts if count), average, current, longest


def _bars(days, slot, peak_index):
    top = max(count for _, count in days)
    width = slot - BAR_GAP
    out = ""
    for i, (_, count) in enumerate(days):
        x = PAD + i * slot
        if not count:
            out += (
                f'<rect x="{x:.1f}" y="{BASELINE - SEGMENT}" width="{width:.1f}" '
                f'height="{SEGMENT}" fill="var(--cell)"/>'
            )
            continue
        segments = max(1, round(count / max(top, 1) * MAX_SEGMENTS))
        for j in range(segments):
            if i == peak_index:
                fill = "var(--l4)"
            else:
                fill = "var(--l3)" if j == segments - 1 else "var(--l2)"
            y = BASELINE - (j + 1) * (SEGMENT + SEGMENT_GAP) + SEGMENT_GAP
            out += (
                f'<rect class="c" x="{x:.1f}" y="{y}" width="{width:.1f}" height="{SEGMENT}" '
                f'fill="{fill}" style="animation-delay:{0.2 + i * 0.035 + j * 0.025:.2f}s"/>'
            )
    return out


def _all_time_header(history):
    active, average, current, longest = all_time_stats(history)
    stats = (
        (f"{active:,}", "ACTIVE DAYS"),
        (f"{average:.1f}", "AVG PER DAY"),
        (f"{current}", "CURRENT STREAK"),
        (f"{longest}", "LONGEST STREAK"),
    )
    out = caption(WIDTH - PAD, HEADLINE_Y - 38, "ALL TIME", 0.25, "end", size=10)
    for i, (value, name) in enumerate(stats):
        x = WIDTH - PAD - (len(stats) - 1 - i) * STAT_SPACING
        out += big_number(x, HEADLINE_Y, value, 30, 0.3 + i * 0.1, "end")
        out += caption(x, HEADLINE_Y + 22, name, 0.35 + i * 0.1, "end", size=10)
    return out


def _short_date(day):
    return date.fromisoformat(day).strftime("%d %b")


def render(days, history=None):
    """`days`: the last 30 (iso_date, count) pairs. `history` (the full account history) feeds
    the all-time stats and defaults to `days`."""
    counts = [count for _, count in days]
    slot = (WIDTH - 2 * PAD + BAR_GAP) / max(len(days), 1)
    peak_index = counts.index(max(counts))
    total = f"{sum(counts):,}"

    bar_x = PAD + peak_index * slot + (slot - BAR_GAP) / 2
    label_top = BASELINE - MAX_SEGMENTS * (SEGMENT + SEGMENT_GAP) - 6
    peak_anchor = "end" if peak_index > len(days) * 0.8 else "middle"
    body = (
        frame(WIDTH, HEIGHT, "FIG. 05 · LAST 30 DAYS")
        + _all_time_header(history or days)
        + big_number(PAD, HEADLINE_Y, total, 56, 0.1)
        + caption(PAD + 22 + len(total) * 31, HEADLINE_Y, "CONTRIBUTIONS", 0.2)
        + text(
            f"{min(bar_x, WIDTH - PAD):.1f}",
            f"{label_top:.1f}",
            f"PEAK {max(counts)} · {_short_date(days[peak_index][0])}",
            size=11,
            fill="var(--brand)",
            spacing=1,
            anchor=peak_anchor,
            delay=1.6,
        )
        + _bars(days, slot, peak_index)
        + f'<line x1="{PAD}" x2="{WIDTH - PAD}" y1="{BASELINE + 6}" y2="{BASELINE + 6}" '
        f'stroke="var(--line)"/>'
        + caption(PAD, AXIS_Y, _short_date(days[0][0]))
        + caption(WIDTH - PAD, AXIS_Y, _short_date(days[-1][0]), anchor="end")
    )
    title = f"{total} contributions in the last 30 days"
    return svg(WIDTH, HEIGHT, title, stylesheet(MOTION), body)
