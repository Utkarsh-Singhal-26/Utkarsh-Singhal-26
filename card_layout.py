"""
Shared card layout: skills/contact are edited HERE (not in the README anymore),
since the whole card is now assembled as one piece each day so the bar chart
can run down the full left-hand side next to everything else.
"""

import re
import textwrap

RESET = "\x1b[0m"
CYAN = "\x1b[36m"
GRAY = "\x1b[90m"
WHITE = "\x1b[97m"
YELLOW = "\x1b[33m"
GREEN = "\x1b[32m"
RED = "\x1b[31m"
BOLD = "\x1b[1m"

VALUE_WRAP_WIDTH = 44
ART_WIDTH = 20  # columns reserved for the bar chart on the left

SKILL_CATEGORIES = [
    ("Languages", "HTML, CSS, JavaScript, TypeScript, Python"),
    ("Frontend Frameworks", "React, Next.js, Vue, Astro"),
    (
        "UI & Styling",
        "Tailwind CSS, ShadCN UI, Material Tailwind, Ant Design",
    ),
    (
        "Backend & APIs",
        "Node.js, Express.js, Django, DRF, Adonis, tRPC, GraphQL, React Query",
    ),
    (
        "Data, Auth & CMS",
        "MongoDB, Redis, Firebase, Prisma, Clerk, Auth.js, JWT, Contentful",
    ),
    ("Mobile & Desktop", "React Native, Expo, Electron, PWA"),
    ("Cloud & DevOps", "AWS, GCP, Nginx, Vercel, Docker, PM2"),
    (
        "Dev Tools",
        "Git, GitHub, Prettier, Vite, Storybook, Sentry",
    ),
]

CONTACT = [
    ("Email", "singhalutkarsh26@gmail.com"),
    ("LinkedIn", "singhalutkarsh26"),
    ("Discord", "singhalutkarsh26"),
]


def dotted_prefix(label, min_dots=2):
    """The 'label: ....' part only — value is appended later once we know
    how many dots are needed to push it flush to the right edge."""
    return f". {CYAN}{label}{RESET}: {GRAY}{'.' * min_dots}{RESET} "


def dotted_wrapped(label, value, wrap_width=VALUE_WRAP_WIDTH):
    """Returns a list of ('primary', prefix, value_colored, value_plainlen)
    for the first line, and ('continuation', '', value_colored, value_plainlen)
    for any wrapped overflow lines — both kinds get right-justified in
    compose_card by stretching filler BEFORE the value, not after it."""
    wrapped = textwrap.wrap(value, width=wrap_width, break_long_words=False) or [""]
    result = [
        (
            "primary",
            dotted_prefix(label),
            f"{WHITE}{wrapped[0]}{RESET}",
            len(wrapped[0]),
        )
    ]
    for cont in wrapped[1:]:
        result.append(("continuation", "", f"{WHITE}{cont}{RESET}", len(cont)))
    return result


def section_header(title, width=52):
    plain = f"- {title} "
    dashes = max(width - len(plain), 2)
    return f"{YELLOW}- {title} {'-' * dashes}{RESET}"


def justify_dots(value_str, target_len):
    """Used only by field() below, for the two-column stat lines — pads with
    flanking spaces around the dots to match that function's own spacing
    convention. NOT a general-purpose "give me N characters" helper; see
    right_fill() for that."""
    just_len = max(0, target_len - len(value_str))
    if just_len == 0:
        return ""
    elif just_len == 1:
        return " "
    elif just_len == 2:
        return ". "
    else:
        return " " + ("." * just_len) + " "


def right_fill(gap, char="."):
    """Returns a filler string of EXACTLY `gap` visible characters — dots (or
    spaces for continuation lines) ending in a single space before the value,
    so 'label: ....... value' reads cleanly. Unlike justify_dots() above,
    this has no flanking-space padding baked in — the caller already knows
    exactly how many characters of space are available and wants exactly
    that many back, not that-many-plus-2."""
    if gap <= 0:
        return ""
    if gap == 1:
        return " "
    return char * (gap - 1) + " "


def field(label, value, label_width, value_target):
    """Total width = label_width + 1 + value_target, ALWAYS — padding for
    both label-length AND value-length differences keeps '|' aligned.
    Used only for the two-column Repos|Stars / Commits|Followers stat lines,
    which have their own fixed-width pairing logic that doesn't fit the
    single-value right-justify used for skills/contact/LOC lines below."""
    value_str = str(value)
    effective_target = (label_width - len(label)) + value_target
    dots = justify_dots(value_str, effective_target)
    return f"{CYAN}{label}{RESET}:{GRAY}{dots}{RESET}{WHITE}{value_str}{RESET}"


LABEL1_WIDTH = max(len("Repos"), len("Commits"))
LABEL2_WIDTH = max(len("Stars"), len("Followers"))
VALUE1_TARGET = 16
VALUE2_TARGET = 8


def build_bar_chart(weekly_totals, num_weeks=20, bar_width=12):
    """One row per week, most recent at the bottom (reads top-to-bottom as a
    timeline). Bar length is relative to this window's own max so it stays
    meaningful regardless of how active a given stretch was.

    Uses plain ASCII '#' rather than the Unicode full-block character (█) —
    that glyph is known to render with different line-height/baseline metrics
    than regular text in many monospace fonts, which compounds row after row
    and causes the whole chart to visibly drift out of alignment with the
    text next to it by the bottom of a tall chart. ASCII has no such issue.
    """
    recent = weekly_totals[-num_weeks:]
    recent = [0] * (num_weeks - len(recent)) + recent  # pad if fewer weeks exist
    peak = max(recent) if recent and max(recent) > 0 else 1
    rows = []
    for total in recent:
        filled = round((total / peak) * bar_width) if total > 0 else 0
        bar = "#" * filled + " " * (bar_width - filled)
        rows.append(f"{GREEN}{bar}{RESET}")
    return rows


def build_info_lines(
    commit_data, star_data, repo_data, contrib_data, follower_data, loc_data
):
    """
    Returns a list of tuples, one of:
      ('header', text)                              - top 'utkarsh@github ---' line
      ('divider', text)                              - section header lines
      ('blank', '')                                  - spacer rows
      ('pair', text)                                 - two-column stat lines (Repos|Stars etc), self-contained, fixed width
      ('primary', prefix, value_colored, value_len)   - 'label: ...value' lines, right-justified by stretching dots before value
      ('continuation', '', value_colored, value_len)  - wrapped overflow lines, right-justified the same way (spaces instead of dots)
    compose_card uses these tags to decide exactly how each line gets
    stretched to the final card width.
    """
    lines = [("header", f"{BOLD}utkarsh@github{RESET} {GRAY}{'-' * 34}{RESET}")]

    for label, value in SKILL_CATEGORIES:
        lines.extend(dotted_wrapped(label, value))

    lines.append(("blank", ""))
    lines.append(("divider", section_header("Contact")))
    for label, value in CONTACT:
        lines.append(
            ("primary", dotted_prefix(label), f"{WHITE}{value}{RESET}", len(value))
        )

    lines.append(("blank", ""))
    lines.append(("divider", section_header("GitHub Stats")))
    repo_val = f"{repo_data:,} {{Contributed: {contrib_data:,}}}"
    lines.append(
        (
            "pair",
            ("Repos", repo_val),
            ("Stars", f"{star_data:,}"),
        )
    )
    lines.append(
        (
            "pair",
            ("Commits", f"{commit_data:,}"),
            ("Followers", f"{follower_data:,}"),
        )
    )

    loc_value = f"{loc_data[2]:,} ( {GREEN}+{loc_data[0]:,}{RESET} / {RED}-{loc_data[1]:,}{RESET} )"
    loc_value_plainlen = len(f"{loc_data[2]:,} ( +{loc_data[0]:,} / -{loc_data[1]:,} )")
    lines.append(
        (
            "primary",
            dotted_prefix("Lines of Code on GitHub", min_dots=1),
            f"{WHITE}{loc_value}",
            loc_value_plainlen,
        )
    )
    return lines


PAIR_LEFT_WIDTH = 42
PAIR_RIGHT_WIDTH = 22


def render_pair_field(label, value, width):
    value = str(value)

    prefix = f". {CYAN}{label}{RESET}: "
    visible_prefix = len(f". {label}: ")

    gap = width - visible_prefix - len(value)
    filler = f"{GRAY}{right_fill(gap)}{RESET}" if gap > 0 else ""

    return f"{prefix}{filler}{WHITE}{value}{RESET}"


ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def visible_len(line):
    """Length ignoring ANSI escape codes — for measuring actual displayed width."""
    return len(ANSI_RE.sub("", line))


def compose_card(
    weekly_totals,
    commit_data,
    star_data,
    repo_data,
    contrib_data,
    follower_data,
    loc_data,
):
    info_lines = build_info_lines(
        commit_data, star_data, repo_data, contrib_data, follower_data, loc_data
    )
    art_lines = build_bar_chart(
        weekly_totals, num_weeks=len(info_lines), bar_width=ART_WIDTH - 2
    )

    art_gap = "  "
    max_lines = max(len(art_lines), len(info_lines))
    art_padded = art_lines + [" " * (ART_WIDTH - 2)] * (max_lines - len(art_lines))
    info_padded = info_lines + [("blank", "")] * (max_lines - len(info_lines))

    # Pass 1: compute the visible length of each row AS IF it had zero extra
    # filler, so we know the true minimum width of every line before deciding
    # the shared target width they should all stretch to.
    base_lengths = []
    for art_row, entry in zip(art_padded, info_padded):
        prefix_len = len(art_row) + len(art_gap)
        if entry[0] in ("header", "divider"):
            base_lengths.append(prefix_len + visible_len(entry[1]))
        elif entry[0] == "pair":
            _, left, right = entry
            rendered = (
                render_pair_field(*left, PAIR_LEFT_WIDTH)
                + " | "
                + render_pair_field(*right, PAIR_RIGHT_WIDTH)
            )
            base_lengths.append(prefix_len + visible_len(rendered))
        elif entry[0] == "blank":
            base_lengths.append(prefix_len)
        else:  # primary or continuation
            _, prefix, _, value_len = entry
            base_lengths.append(prefix_len + visible_len(prefix) + value_len)

    content_width = max(base_lengths)

    # Pass 2: build each row for real, stretching filler to hit content_width
    # — dots BEFORE the value for primary/continuation lines (so the value's
    # last character lands exactly on the right edge, true right-justify),
    # dashes for header/divider, plain padding after for the two-column pair
    # lines (no single value to justify against there).
    rows = []
    for art_row, entry in zip(art_padded, info_padded):
        kind = entry[0]
        base = len(art_row) + len(art_gap)

        if kind == "blank":
            rows.append(f"{art_row}{art_gap}" + " " * (content_width - base))
            continue

        if kind in ("header", "divider"):
            text = entry[1]
            gap = content_width - base - visible_len(text)

            if gap <= 0:
                rows.append(f"{art_row}{art_gap}{text}")
            else:
                color = YELLOW if kind == "divider" else GRAY
                rows.append(f"{art_row}{art_gap}{text}{color}{'-' * gap}{RESET}")

            continue

        if kind == "pair":
            _, left, right = entry

            text = (
                render_pair_field(*left, PAIR_LEFT_WIDTH)
                + " | "
                + render_pair_field(*right, PAIR_RIGHT_WIDTH)
            )

            gap = content_width - base - visible_len(text)
            rows.append(f"{art_row}{art_gap}{text}" + " " * max(gap, 0))
            continue

        # primary / continuation: right-justify the value
        _, prefix, value_colored, value_len = entry
        gap = content_width - base - visible_len(prefix) - value_len
        if kind == "continuation":
            filler = " " * max(gap, 0)  # plain indentation, not a dot-leader
        else:
            filler = f"{GRAY}{right_fill(gap)}{RESET}" if gap > 0 else ""
        rows.append(f"{art_row}{art_gap}{prefix}{filler}{value_colored}")

    return "\n".join(rows)


_SVG_BG = "#0d1117"
_SVG_DEFAULT_FG = "#c9d1d9"
_SVG_FONT_SIZE = 13
_SVG_LINE_HEIGHT = 18
_SVG_CHAR_WIDTH = 7.82
_SVG_PADDING = 16

_SVG_COLOR_MAP = {
    "31": "#ff7b72",
    "32": "#56d364",
    "33": "#e3b341",
    "36": "#79c0ff",
    "90": "#8b949e",
    "97": "#f0f6fc",
}


def _parse_ansi_line(line):
    current = _SVG_DEFAULT_FG
    result = []
    for seg in re.split(r"(\x1b\[[0-9;]*m)", line):
        m = re.fullmatch(r"\x1b\[([0-9;]*)m", seg)
        if m:
            code = m.group(1)
            if code in ("0", ""):
                current = _SVG_DEFAULT_FG
            elif code in _SVG_COLOR_MAP:
                current = _SVG_COLOR_MAP[code]
            # bold (1) → ignore
        elif seg:
            result.append((current, seg))
    return result


def compose_svg_card(card_ansi):
    lines = card_ansi.split("\n")
    max_vis = max((visible_len(l) for l in lines), default=0)
    width = int(max_vis * _SVG_CHAR_WIDTH) + _SVG_PADDING * 2
    height = len(lines) * _SVG_LINE_HEIGHT + _SVG_PADDING * 2

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">',
        f'<rect width="100%" height="100%" fill="{_SVG_BG}" rx="6"/>',
        f'<text xml:space="preserve" font-family="\'Courier New\', Courier, monospace"'
        f' font-size="{_SVG_FONT_SIZE}" fill="{_SVG_DEFAULT_FG}">',
    ]

    for i, line in enumerate(lines):
        y = _SVG_PADDING + (i + 1) * _SVG_LINE_HEIGHT
        x = _SVG_PADDING
        spans = _parse_ansi_line(line)
        if not spans:
            out.append(f'<tspan x="{x}" y="{y}"> </tspan>')
            continue
        tspans = []
        for j, (color, text) in enumerate(spans):
            e = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            parts = []
            if j == 0:
                parts.append(f'x="{x}" y="{y}"')
            if color != _SVG_DEFAULT_FG:
                parts.append(f'fill="{color}"')
            attrs = " ".join(parts)
            tspans.append(f"<tspan {attrs}>{e}</tspan>" if attrs else f"<tspan>{e}</tspan>")
        out.append("".join(tspans))

    out += ["</text>", "</svg>"]
    return "\n".join(out)
