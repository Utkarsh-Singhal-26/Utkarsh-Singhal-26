"""Render the WakaTime card from the all-time stats JSON.

Usage: python -m scripts.build_waka waka_raw.json
"""

import json
import sys
from pathlib import Path

from profile_cards import waka


def main(path):
    stats = json.loads(Path(path).read_text(encoding="utf-8"))["data"]
    Path("cards/waka.svg").write_text(waka.render(stats) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1])
