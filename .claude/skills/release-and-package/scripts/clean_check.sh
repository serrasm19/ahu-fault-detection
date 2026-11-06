#!/usr/bin/env bash
# Build the ZIP from a git ref and test it in a clean folder with a new environment.
# Usage: clean_check.sh <git-ref> <zip-path>
set -euo pipefail

ref="${1:?give a git ref, for example origin/main}"
zip_path="${2:?give the path of the ZIP to write}"
root=$(git rev-parse --show-toplevel)
data="${AHU_DATA_DIR:-$root/assignment/data}"
validator="$root/assignment/starter/validate_submission.py"
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

echo "== build the ZIP from $ref"
git -C "$root" archive --format=zip -o "$work/delivery.zip" "$ref:submission"
unzip -q "$work/delivery.zip" -d "$work/unzipped"
cp "$work/unzipped/predictions.csv" "$work/predictions_shipped.csv"

echo "== nothing private inside"
if unzip -l "$work/delivery.zip" | grep -Ei '\.parquet|\.venv|__pycache__|context/|AGENTS\.md|CLAUDE\.md'; then
  echo "The ZIP holds files that must stay out."
  exit 1
fi

echo "== new environment"
python3.11 -m venv "$work/venv"
"$work/venv/bin/pip" install -q -r "$work/unzipped/code/requirements.txt"
"$work/venv/bin/pip" install -q -e "$work/unzipped/code"

cd "$work/unzipped/code"
echo "== tests"
"$work/venv/bin/python" -m pytest -q | tail -1
echo "== predict"
AHU_DATA_DIR="$data" "$work/venv/bin/python" -m ahu_fdd.predict
echo "== validator"
"$work/venv/bin/python" "$validator" ../predictions.csv
echo "== same predictions?"
new=$(shasum -a 256 ../predictions.csv | cut -d' ' -f1)
old=$(shasum -a 256 "$work/predictions_shipped.csv" | cut -d' ' -f1)
echo "rebuilt  $new"
echo "shipped  $old"
[ "$new" = "$old" ] || { echo "The rebuilt predictions differ from the ones in the ZIP."; exit 1; }

cd "$root"
cp "$work/delivery.zip" "$zip_path"
echo "== done: $zip_path ($(du -h "$zip_path" | cut -f1))"
