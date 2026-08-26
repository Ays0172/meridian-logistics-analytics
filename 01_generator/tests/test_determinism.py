"""The build must be a pure function of the seed — across processes, not just
within one.

See 00_docs/ADR/ADR-002-build-determinism.md. A set of strings iterates in an
order that depends on the per-process PYTHONHASHSEED, and any such order that
reaches an RNG makes the build irreproducible while leaving row counts and most
aggregates untouched. That is a bug that hides.

These tests force the failure mode by running the same code under deliberately
different hash seeds. A test that inherits the parent process's hash seed cannot
catch this.
"""

from __future__ import annotations

import ast
import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

GEN_DIR = Path(__file__).resolve().parents[1]
REPO = GEN_DIR.parent
RAW = REPO / "02_data" / "raw"

HASH_SEEDS = ("1", "424242")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_under_hash_seed(script: str, workdir: Path, seed: str) -> None:
    env = dict(os.environ, PYTHONHASHSEED=seed)
    result = subprocess.run(
        [sys.executable, script],
        cwd=workdir / "01_generator",
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"{script} failed under PYTHONHASHSEED={seed}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


@pytest.mark.skipif(
    not (RAW / "DimVoyage" / "part-000.parquet").exists(),
    reason="needs a built 02_data/raw; run build_dims.py first",
)
def test_revise_voyage_rotations_is_hash_seed_independent(tmp_path: Path) -> None:
    """The historical failure: a str set feeding rng.choice."""
    hashes = []
    for seed in HASH_SEEDS:
        work = tmp_path / f"seed{seed}"
        (work / "02_data" / "raw").mkdir(parents=True)
        shutil.copytree(GEN_DIR, work / "01_generator")
        for dim in ("DimVoyage", "DimLocation", "DimService"):
            shutil.copytree(RAW / dim, work / "02_data" / "raw" / dim)

        _run_under_hash_seed("revise_voyage_rotations.py", work, seed)
        hashes.append(_sha(work / "02_data" / "raw" / "DimVoyage" / "part-000.parquet"))

    assert hashes[0] == hashes[1], (
        "DimVoyage differs between PYTHONHASHSEED values. Something whose "
        "iteration order depends on string hashing is reaching the RNG. "
        "See ADR-002."
    )


def _unordered_iterations(path: Path) -> list[str]:
    """Find `list(<name>)` / `for x in <name>` where <name> was built by set()
    or dict() from a non-literal — the shape that caused ADR-002.

    Deliberately syntactic and deliberately noisy on the safe side: it reports
    candidates for a human to clear, it does not try to prove safety.
    """
    tree = ast.parse(path.read_text())
    set_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            fn = node.value.func
            name = getattr(fn, "id", None)
            if name == "set":
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        set_names.add(target.id)

    findings = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "id", None) in ("list", "tuple", "sorted")
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id in set_names
            and getattr(node.func, "id", None) != "sorted"
        ):
            findings.append(f"{path.name}:{node.lineno} list({node.args[0].id})")
        if (
            isinstance(node, ast.For)
            and isinstance(node.iter, ast.Name)
            and node.iter.id in set_names
        ):
            findings.append(f"{path.name}:{node.lineno} for ... in {node.iter.id}")
    return findings


def test_no_mutable_set_is_iterated_in_the_generator() -> None:
    """Static guard: iterating a `set()` built at runtime is how ADR-002 happened.

    Membership-only sets are fine and invisible to this check — it only fires on
    a set that is turned into a sequence or iterated, which is the shape that can
    reach the RNG. Any legitimate hit should be rewritten as `sorted(...)`.
    """
    targets = [
        GEN_DIR / "revise_voyage_rotations.py",
        GEN_DIR / "build_dims.py",
        GEN_DIR / "build_facts.py",
        *sorted((GEN_DIR / "meridian").glob("*.py")),
    ]
    findings: list[str] = []
    for path in targets:
        if path.exists():
            findings.extend(_unordered_iterations(path))

    assert not findings, (
        "A runtime-built set is being iterated or converted to a sequence in the "
        "generator. If its order can reach the RNG or the generated data, the "
        "build is not reproducible — use sorted(). See ADR-002.\n  "
        + "\n  ".join(findings)
    )
