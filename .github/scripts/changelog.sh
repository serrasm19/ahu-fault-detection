#!/usr/bin/env bash
# Read the first release section of CHANGELOG.md.
# Usage: changelog.sh version|date|notes
set -euo pipefail

file="${CHANGELOG_FILE:-CHANGELOG.md}"
heading=$(grep -m 1 -E '^## \[[0-9]+\.[0-9]+\.[0-9]+\] - ' "$file" || true)
if [ -z "$heading" ]; then
  echo "No release heading like '## [1.2.3] - YYYY-MM-DD' found in $file" >&2
  exit 1
fi

case "${1:-}" in
  version) sed -E 's/^## \[([0-9.]+)\].*$/\1/' <<<"$heading" ;;
  date) sed -E 's/^## \[[0-9.]+\] - (.*)$/\1/' <<<"$heading" ;;
  # Lines between the first release heading and the next one
  notes) awk 'f && /^## \[/ {exit} f {print} /^## \[/ {f=1}' "$file" ;;
  *) echo "Usage: $0 version|date|notes" >&2; exit 2 ;;
esac
