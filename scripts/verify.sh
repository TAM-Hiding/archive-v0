#!/usr/bin/env bash
# Run from a source-only temporary copy, never the user's notes directory.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${PYTHON_BIN:-python3}
python_bin=$(command -v "$python_bin")
reports=${1:?Usage: bash scripts/verify.sh ABSOLUTE_REPORT_DIRECTORY}
[[ "$reports" = /* ]] || { echo 'Report directory must be absolute' >&2; exit 2; }
mkdir -p "$reports"
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT
# Only tracked source is copied. Pending tracked edits are included; untracked data is not.
git -C "$repo" ls-files -z | tar -C "$repo" --null -T - -cf - | tar -C "$work" -xf -
cd "$work"
export PYTHONDONTWRITEBYTECODE=1
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export XDG_DATA_HOME="$work/.data" XDG_CONFIG_HOME="$work/.config"
"$python_bin" --version > "$reports/python.txt" 2>&1
"$python_bin" -m pip freeze > "$reports/dependencies.txt"
"$python_bin" -m pip check 2>&1 | tee "$reports/pip-check.txt"
"$python_bin" -m pytest -q -p no:cacheprovider --basetemp="$work/.pytest-tmp" --junitxml="$reports/junit.xml" 2>&1 | tee "$reports/pytest.txt"
