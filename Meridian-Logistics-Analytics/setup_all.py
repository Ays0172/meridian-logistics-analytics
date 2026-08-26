#!/usr/bin/env python
"""
Meridian — one-command setup.

Builds the entire dataset from the seed, verifies it three ways, and brings the
live feed up to today. Run this once after unpacking, from anywhere:

    python setup_all.py

Everything is seeded (SEED = 20260824), so the dataset this produces is
byte-identical to the one that was built and verified on 21 August 2026.

Expect roughly 25-35 minutes and about 550 MB of disk.

Flags:
    --skip-build     verify and feed only; assumes 02_data/raw already exists
    --skip-feed      build and verify, do not append live days
    --no-fail-fast   keep going after a step fails (for diagnosis only)
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GEN = ROOT / "01_generator"

BUILD_STEPS = [
    ("build_dims.py", "Build the 19 dimensions", []),
    ("revise_voyage_rotations.py", "Apply ADR-001 voyage rotation revision", []),
    ("build_facts.py", "Build the 11 fact tables (~7.5M rows) — the long one", []),
]

VERIFY_STEPS = [
    ("validate.py", "14 contract gates", []),
    ("audit.py", "67 adversarial checks", []),
    ("crosscheck.py", "45 cross-table checks", []),
]

FEED_STEPS = [
    ("live_feed.py", "Bring the live feed up to today", []),
    # Eight of crosscheck's checks compare the appended rows against the history
    # they extend, so they can only run once a live day exists. Running it before
    # the feed reports 35/37 with those eight skipped; running it again after
    # reports the full 44/45. Both are correct — this second pass is the one that
    # actually exercises live-vs-history continuity.
    ("crosscheck.py", "45 cross-table checks, now including live continuity", []),
]

BAR = "=" * 78


def preflight() -> list[str]:
    problems = []

    if sys.version_info < (3, 10):
        problems.append(
            f"Python {sys.version_info.major}.{sys.version_info.minor} found; 3.10+ required."
        )

    for mod in ("pandas", "numpy", "pyarrow", "yaml"):
        try:
            __import__(mod)
        except ImportError:
            problems.append(
                f"Missing package '{mod}'. Run:  pip install -r "
                f"{GEN / 'requirements.txt'}"
            )

    if not GEN.exists():
        problems.append(f"Cannot find {GEN}. Run this script from the package root.")

    free_gb = shutil.disk_usage(ROOT).free / 1e9
    if free_gb < 2.0:
        problems.append(f"Only {free_gb:.1f} GB free; need about 2 GB of headroom.")

    return problems


def run(script: str, label: str, extra: list[str]) -> bool:
    print(f"\n{BAR}\n  {label}\n  $ python {script} {' '.join(extra)}\n{BAR}", flush=True)
    started = time.time()
    result = subprocess.run([sys.executable, script, *extra], cwd=GEN)
    elapsed = time.time() - started
    ok = result.returncode == 0
    print(
        f"\n  --> {'OK' if ok else 'FAILED (exit %d)' % result.returncode}"
        f"  [{elapsed / 60:.1f} min]",
        flush=True,
    )
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--skip-feed", action="store_true")
    ap.add_argument("--no-fail-fast", action="store_true")
    args = ap.parse_args()

    print(f"{BAR}\n  MERIDIAN LOGISTICS ANALYTICS — full setup\n{BAR}")

    problems = preflight()
    if problems:
        print("\nPreflight failed:\n")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nPreflight OK.")

    steps: list[tuple[str, str, list[str]]] = []
    if not args.skip_build:
        steps += BUILD_STEPS
    steps += VERIFY_STEPS
    if not args.skip_feed:
        steps += FEED_STEPS

    results: list[tuple[str, bool]] = []
    for script, label, extra in steps:
        ok = run(script, label, extra)
        results.append((script, ok))
        if not ok and not args.no_fail_fast:
            print(f"\nStopping at {script}. Fix the error above and re-run.")
            break

    print(f"\n{BAR}\n  SUMMARY\n{BAR}")
    for script, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {script}")

    failed = [s for s, ok in results if not ok]
    if failed:
        print(f"\n{len(failed)} step(s) failed. Nothing downstream should be trusted.")
        return 1

    print(
        "\nAll steps passed. The dataset is built and verified.\n"
        "\nNext:\n"
        "  1. Open 00_docs/start-here.html\n"
        "  2. Point Power BI at 02_data/raw (Parquet, folder combine)\n"
        "  3. Begin 04_learning/week1/D01-domain-foundations.md\n"
        "  4. Run  python 01_generator/live_feed.py  each morning\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
