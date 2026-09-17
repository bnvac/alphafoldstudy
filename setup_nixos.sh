#!/usr/bin/env bash
#
# setup_nixos.sh -- one-command setup for this project on NixOS.
#
#   bash setup_nixos.sh
#
# What it does: creates the working directories, builds an FHS sandbox with
# nix-shell, makes a Python venv inside it, installs every dependency, and
# checks that all of them import.
#
# Why the sandbox: NixOS has no /lib64/ld-linux-x86-64.so.2, so prebuilt wheels
# from PyPI (numpy, scipy, matplotlib, torch) cannot start. See nix/fhs.nix.
# Nothing is installed system-wide, nothing is written outside this folder, and
# no root access is needed. Your NixOS configuration is not touched.
#
# Afterwards, run the study with:  bash run_nixos.sh
#
# Options:
#   --download   also pre-download every structure once setup finishes
#   --recreate   delete an existing .venv and build it again
#
# Environment overrides:
#   AFS_VENV       where the venv goes           (default ./.venv)
#   AFS_NIXPKGS    nixpkgs to use if the channel is missing

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

VENV_DIR="${AFS_VENV:-$PROJECT_ROOT/.venv}"
NIXPKGS_FALLBACK="${AFS_NIXPKGS:-https://github.com/NixOS/nixpkgs/archive/nixos-26.05.tar.gz}"
TORCH_CPU_INDEX="https://download.pytorch.org/whl/cpu"

DO_DOWNLOAD=0
DO_RECREATE=0
for arg in "$@"; do
    case "$arg" in
        --download) DO_DOWNLOAD=1 ;;
        --recreate) DO_RECREATE=1 ;;
        -h|--help) sed -n '2,30p' "$0"; exit 0 ;;
        *) echo "Unknown option: $arg (try --help)" >&2; exit 1 ;;
    esac
done

die() { printf '\nERROR: %s\n' "$*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# Stage 2: inside the sandbox. Everything below the marker assumes an FHS
# layout, so it is equally valid on a normal distribution.
# ---------------------------------------------------------------------------
if [ "${AFS_IN_FHS:-0}" = "1" ]; then
    echo
    echo "[2/4] Python environment"
    if [ "$DO_RECREATE" = "1" ] && [ -d "$VENV_DIR" ]; then
        echo "  removing existing $VENV_DIR"
        rm -rf "$VENV_DIR"
    fi
    if [ -d "$VENV_DIR" ]; then
        echo "  reusing existing venv at $VENV_DIR"
    else
        echo "  creating venv at $VENV_DIR"
        python3 -m venv "$VENV_DIR"
    fi

    # shellcheck disable=SC1091
    source "$VENV_DIR/bin/activate"
    python -m pip install --quiet --upgrade pip wheel

    echo
    echo "[3/4] Dependencies"
    # CPU torch first and from PyTorch's own index. Installing it up front means
    # metapredict's dependency is already satisfied, so pip never pulls the
    # multi-gigabyte CUDA build from PyPI.
    echo "  installing CPU PyTorch (large, a few minutes)"
    python -m pip install --quiet --index-url "$TORCH_CPU_INDEX" torch
    echo "  installing everything else"
    python -m pip install --quiet -r requirements.txt

    echo
    echo "[4/4] Verifying"
    python - <<'PYEOF'
import importlib
import importlib.metadata
import sys

# (import name, pip name) -- several differ, which is why both are listed.
MODULES = [
    ("numpy", "numpy"), ("scipy", "scipy"), ("pandas", "pandas"),
    ("matplotlib", "matplotlib"), ("statsmodels", "statsmodels"),
    ("Bio", "biopython"), ("requests", "requests"), ("torch", "torch"),
    ("tmtools", "tmtools"), ("rcsbapi", "rcsb-api"),
    ("metapredict", "metapredict"),
]


def version_of(module, pip_name):
    """Version string, preferring the package metadata over __version__.

    Not every package exposes __version__ (rcsb-api does not), so falling back
    to the installed metadata avoids printing a bare "?" that reads like a
    failure when the import in fact succeeded.
    """
    try:
        return importlib.metadata.version(pip_name)
    except Exception:
        return getattr(module, "__version__", "installed")


failed = []
for name, pip_name in MODULES:
    try:
        loaded = importlib.import_module(name)
        print("  ok   {0:<14} {1}".format(pip_name, version_of(loaded, pip_name)))
    except Exception as exc:
        failed.append((pip_name, exc))
        print("  FAIL {0:<14} {1}".format(pip_name, exc))

if failed:
    print("\n{0} package(s) failed to import.".format(len(failed)))
    sys.exit(1)
print("\nAll {0} packages import cleanly.".format(len(MODULES)))
PYEOF

    if [ "$DO_DOWNLOAD" = "1" ]; then
        echo
        echo "Pre-downloading structures into ./data"
        python src/af_study.py
    fi

    echo
    echo "=============================================="
    echo " Done. Run the study with:"
    echo
    echo "   bash run_nixos.sh"
    echo
    echo " Or enter the environment yourself with:"
    echo
    echo "   nix-shell nix/fhs.nix"
    echo "   source $VENV_DIR/bin/activate"
    echo "=============================================="
    exit 0
fi

# ---------------------------------------------------------------------------
# Stage 1: outside the sandbox. Check the host, make the directories, re-enter.
# ---------------------------------------------------------------------------
echo "=============================================="
echo " AlphaFold study setup (NixOS)"
echo "=============================================="
echo
echo "[1/4] Host checks and directories"

command -v nix-shell >/dev/null 2>&1 || die \
"nix-shell not found.

This script is for NixOS, or any machine with the Nix package manager.
On a normal Linux distribution or a Mac, use the conda installer instead:

    bash setup_env.sh"

if [ -r /etc/os-release ] && grep -qi '^ID=nixos' /etc/os-release; then
    echo "  host: NixOS"
else
    echo "  host: not NixOS, but nix-shell is present, so continuing"
fi
echo "  nix:  $(nix-shell --version 2>&1 | head -1)"

[ -f requirements.txt ] || die "requirements.txt not found. Run this from the project folder."
[ -f nix/fhs.nix ] || die "nix/fhs.nix not found. Run this from the project folder."

mkdir -p data results logs
echo "  directories: data/ results/ logs/"

# Flake-based systems often have no <nixpkgs> on NIX_PATH. Pin one in that case
# rather than failing with a search-path error.
NIX_EXTRA=()
if nix-instantiate --eval -E '<nixpkgs>' >/dev/null 2>&1; then
    echo "  nixpkgs: from your channel"
else
    echo "  nixpkgs: channel not on NIX_PATH, pinning $NIXPKGS_FALLBACK"
    NIX_EXTRA=(-I "nixpkgs=$NIXPKGS_FALLBACK")
fi

echo
echo "  entering the FHS sandbox (first run builds it, which takes a while)"

# Re-enter this same script inside the sandbox. The flags are passed through so
# --download and --recreate keep working.
INNER="AFS_IN_FHS=1 AFS_VENV=$(printf '%q' "$VENV_DIR") bash $(printf '%q' "$0")"
for arg in "$@"; do
    INNER="$INNER $(printf '%q' "$arg")"
done

exec nix-shell "${NIX_EXTRA[@]}" nix/fhs.nix --run "$INNER"
