#!/usr/bin/env bash
# Simulates the GitHub Action's injection step locally, without needing to
# push anything. Run this after `python3 github_stats.py` has produced
# stats.md. Writes the result to README.preview.md so your real README.md
# is untouched until you're happy with it.
set -euo pipefail

if [ ! -f stats.md ]; then
  echo "stats.md not found — run 'python3 github_stats.py' first." >&2
  exit 1
fi

awk '
  BEGIN {in_block=0}
  /<!--START_SECTION:stats-->/ {
    print
    system("cat stats.md")
    in_block=1
    next
  }
  /<!--END_SECTION:stats-->/ {
    in_block=0
  }
  !in_block {print}
' README.md > README.preview.md

echo "Wrote README.preview.md — diff against README.md to see exactly what would change:"
echo "  diff README.md README.preview.md"
echo "Or view it directly: cat README.preview.md"