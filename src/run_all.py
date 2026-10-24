#!/usr/bin/env python3
"""run_all.py

Run the whole experiment with one command, in the right order:

  1. af_study.py         download structures, score AlphaFold2, statistics
  2. compare_metrics.py  three-panel comparison figure and tests
  3. extra_stats.py      robustness tests, appended to stats.txt
  4. esmfold_compare.py  the ESMFold mechanism test

Each stage is a separate script that can still be run on its own; this only
sequences them and stops at the first one that fails, saying which. Every stage
reuses cached downloads, so an interrupted run can simply be started again.

Run with:  python src/run_all.py
           python src/run_all.py --registry proteins_1000.csv
           python src/run_all.py --skip-esmfold

On NixOS:  bash run_nixos.sh src/run_all.py
"""

import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def stage(label, script, args):
    """Run one stage with this interpreter. Return True when it succeeds."""
    print("\n" + "=" * 64)
    print(" {0}".format(label))
    print("=" * 64, flush=True)
    start = time.time()
    code = subprocess.call([sys.executable, os.path.join(HERE, script)] + args)
    minutes = (time.time() - start) / 60.0
    if code != 0:
        print("\nSTOPPED: {0} exited with code {1} after {2:.1f} min.".format(
            script, code, minutes))
        print("Fix the error above and run this command again; finished work is")
        print("cached and will not be repeated.")
        return False
    print("\n  done in {0:.1f} min".format(minutes))
    return True


def main():
    parser = argparse.ArgumentParser(description="Run the whole experiment.")
    parser.add_argument("--registry", default="proteins.csv",
                        help="protein list to analyse (default proteins.csv, the 250)")
    parser.add_argument("--results-dir", default="results")
    parser.add_argument("--skip-esmfold", action="store_true",
                        help="stop after the AlphaFold2 analysis")
    args = parser.parse_args()

    if not os.path.exists(args.registry):
        print("No protein list at {0}. Run this from the project folder.".format(
            args.registry))
        sys.exit(1)

    metrics = os.path.join(args.results_dir, "metrics.csv")
    stages = [
        ("1/4  AlphaFold2 analysis", "af_study.py",
         ["--registry", args.registry, "--results-dir", args.results_dir]),
        ("2/4  Comparison figure", "compare_metrics.py",
         ["--metrics", metrics]),
        ("3/4  Robustness tests", "extra_stats.py",
         ["--metrics", metrics]),
    ]
    if not args.skip_esmfold:
        stages.append(("4/4  ESMFold mechanism test", "esmfold_compare.py",
                       ["--metrics", metrics]))

    overall = time.time()
    for label, script, stage_args in stages:
        if not stage(label, script, stage_args):
            sys.exit(1)

    print("\n" + "=" * 64)
    print(" Experiment complete in {0:.1f} min. Results are in {1}/".format(
        (time.time() - overall) / 60.0, args.results_dir))
    print("=" * 64)
    print("  stats.txt            AlphaFold2 statistics and robustness tests")
    print("  regression.txt       viral origin against disorder")
    print("  compare_metrics.png  viral against cellular, three measures")
    if not args.skip_esmfold:
        print("  esmfold_stats.txt    the mechanism test")
        print("  esmfold_compare.png  AlphaFold2 against ESMFold")


if __name__ == "__main__":
    main()
