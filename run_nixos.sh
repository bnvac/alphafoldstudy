#!/usr/bin/env bash
#
# run_nixos.sh -- run the study on NixOS, inside the FHS sandbox and venv.
#
#   bash run_nixos.sh                              the 250-protein default
#   bash run_nixos.sh --registry proteins_1000.csv the 1000-protein set
#   bash run_nixos.sh src/compare_metrics.py       any other script in src/
#
# With no arguments it runs src/af_study.py. A first argument ending in .py is
# treated as the script to run; anything else is passed to af_study.py.
#
# Run bash setup_nixos.sh first.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

VENV_DIR="${AFS_VENV:-$PROJECT_ROOT/.venv}"
NIXPKGS_FALLBACK="${AFS_NIXPKGS:-https://github.com/NixOS/nixpkgs/archive/nixos-26.05.tar.gz}"

die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

[ -d "$VENV_DIR" ] || die "No venv at $VENV_DIR. Run: bash setup_nixos.sh"
command -v nix-shell >/dev/null 2>&1 || die "nix-shell not found. See setup_nixos.sh."

# Decide what to run, then quote it so paths with spaces survive the --run string.
if [ "$#" -gt 0 ] && [ "${1%.py}" != "$1" ]; then
    SCRIPT="$1"; shift
else
    SCRIPT="src/af_study.py"
fi

CMD="source $(printf '%q' "$VENV_DIR")/bin/activate && python $(printf '%q' "$SCRIPT")"
for arg in "$@"; do
    CMD="$CMD $(printf '%q' "$arg")"
done

NIX_EXTRA=()
nix-instantiate --eval -E '<nixpkgs>' >/dev/null 2>&1 || \
    NIX_EXTRA=(-I "nixpkgs=$NIXPKGS_FALLBACK")

exec nix-shell "${NIX_EXTRA[@]}" nix/fhs.nix --run "$CMD"
