"""FIG. 02: the last year of contributions as a teal grid with a peak-day callout."""

from datetime import date

from .theme import PAD, POP, WIDTH, frame, stylesheet, svg, text

HEIGHT = 268
TOP = 90
COLUMNS = 53
PEAK_DELAY = 2.4
MOTION = f".c{{transform-box:fill-box;transform-origin:center;animation:pop .45s {POP} both}}"


def _level_thresholds(weeks):
    counts = sorted(count for week in weeks for _, count in week if count)
    if not counts:
        return [1, 2, 3]
    return [counts[int(len(counts) * share)] for share in (0.25, 0.5, 0.75)]


def _month_labels(weeks, step):
    starts = []
    previous = None
    for index, week in enumerate(weeks):
        month = week[0][0][5:7]
        if month != previous:
            starts.append((index, week[0][0]))
            previous = month
    if len(starts) > 1 and starts[1][0] - starts[0][0] < 3:
        starts.pop(0)  # too short to label without crowding the next month
    return "".join(
        text(
            PAD + index * step,
            TOP - 12,
            date.fromisoformat(day).strftime("%b"),
            size=11,
            fill="var(--muted)",
            delay=0.1,
        )
        for index, day in starts
        if index < len(weeks) - 2
    )


def _peak_callout(peak, step, cell):
    count, day, column, row = peak
    x, y = PAD + column * step, TOP + row * step
    leader_x = x + cell + 2
    grid_bottom = TOP + 7 * step + 6
    label = f"{count} contributions / {date.fromisoformat(day).strftime('%d %b %Y')}"
    box_width = round(34 + 7.3 * (len("PEAK") + 2 + len(label)) + 12)
    box_x = max(PAD, min(leader_x - box_width, WIDTH - PAD - box_width))
    box_y = grid_bottom + 8
    return (
        f'<g style="animation:pop .5s {POP} {PEAK_DELAY}s both" '
        f'transform-origin="{x + cell / 2} {y + cell / 2}">'
        f'<rect x="{x - 3}" y="{y - 3}" width="{cell + 6}" height="{cell + 6}" fill="none" '
        f'stroke="var(--fg)"/></g>'
        f'<g class="r" style="animation-delay:{PEAK_DELAY + 0.2}s">'
        f'<path d="M{leader_x} {y + cell / 2}V{box_y}H{box_x + box_width}" '
        f'stroke="var(--fg)" stroke-opacity=".6" fill="none"/>'
        f'<rect x="{box_x}" y="{box_y}" width="{box_width}" height="26" fill="var(--card)" '
        f'stroke="var(--line)"/>'
        f'<path d="M{box_x + 6} {box_y + 20}L{box_x + 14} {box_y + 6}'
        f'M{box_x + 11} {box_y + 20}L{box_x + 19} {box_y + 6}" '
        f'stroke="var(--brand)" stroke-opacity=".6"/>'
        f'<text x="{box_x + 28}" y="{box_y + 17}" class="m" font-size="12" xml:space="preserve">'
        f'<tspan fill="var(--brand)" letter-spacing="1.5">PEAK</tspan>'
        f'<tspan fill="var(--fg)">  {count} contributions </tspan>'
        f'<tspan fill="var(--muted)">/ {date.fromisoformat(day).strftime("%d %b %Y")}</tspan>'
        f"</text></g>"
    )


def render(weeks):
    """`weeks`: oldest first, each a list of (iso_date, count) starting on Sunday. The first
    week may be short."""
    step = round((WIDTH - 2 * PAD + 4) / COLUMNS, 2)
    cell = round(step - 4, 2)
    thresholds = _level_thresholds(weeks)
    total = sum(count for week in weeks for _, count in week)

    cells = ""
    peak = None
    for column, week in enumerate(weeks):
        offset = 7 - len(week) if column == 0 else 0
        for index, (day, count) in enumerate(week):
            row = index + offset
            level = 0 if not count else 1 + sum(count > t for t in thresholds)
            delay = 0.2 + column * 0.018 + row * 0.02
            cells += (
                f'<rect class="c" x="{PAD + column * step}" y="{TOP + row * step}" '
                f'width="{cell}" height="{cell}" fill="var(--l{level})" '
                f'style="animation-delay:{delay:.2f}s"/>'
            )
            if peak is None or count > peak[0]:
                peak = (count, day, column, row)

    body = frame(WIDTH, HEIGHT, "FIG. 02 · CONTRIBUTIONS")
    body += _month_labels(weeks, step) + cells + _peak_callout(peak, step, cell)
    title = f"GitHub contribution graph, {total:,} contributions in the last year"
    return svg(WIDTH, HEIGHT, title, stylesheet(MOTION), body)
