# ADR-002 — The build must be reproducible across processes, not just within one

**Status:** accepted, 21 August 2026
**Supersedes:** nothing
**Related:** ADR-001 (voyage rotation length), `00_docs/LIVE_FEED.md`

---

## Context

The whole package rests on one claim: the dataset is a pure function of
`SEED = 20260824`, so anyone who runs the generator gets the dataset that was
verified, byte for byte. That claim is what lets the archive ship a 4 MB generator
instead of 503 MB of Parquet, and it is what makes `live_feed.py --redo` safe.

The claim was false, and I only found out by testing it properly.

### How it surfaced

Before shipping, I unpacked the archive into a clean directory and ran the full
pipeline end to end — a clean-room build, not a re-verification of the build I
already had. It failed:

```
[FAIL] 14. Congestion effects within +/-15% of contract:
       ... demurrage lines 4.23 (target 3.1)
```

against 3.48 in the build that had passed 14/14 an hour earlier. Other figures had
moved too: congested on-time arrival 0.322 against 0.275, total revenue 2,034.5M
against 2,043.1M.

Same seed. Same code. Same row counts. Different data.

### Diagnosis

Hashing every table in both builds isolated it immediately:

| Table | Verified build | Clean-room build |
|---|---|---|
| all 18 other dimensions | identical | identical |
| **DimVoyage** | `aacf7f80fc8b41e6` | `5bcf460d9a96b1ee` |
| every fact downstream of voyages | differs | differs |
| FactInventorySnapshot, FactTarget, FactExchangeRate | identical | identical |

One dimension diverged and dragged eight fact tables with it. Running
`revise_voyage_rotations.py` twice, in two processes, on identical input confirmed
it directly — two different output hashes.

The cause is three characters wide:

```python
valid_codes = set(locations[locations["LocationKey"] > 0]["LocationCode"].tolist())
...
load_pool = pool.get(o_reg[i]) or list(valid_codes)   # <-- order feeds the RNG
```

**CPython randomises the hash of `str` per process** (PEP 456, on by default since
3.3). So a `set` of strings iterates in an order that changes every run.
`list(valid_codes)` is a fallback sampling pool handed to `rng.choice`, which means
the *order of that list is an input to the random draw*. The RNG was perfectly
seeded; it was being asked to choose from a differently-ordered pool each time.

Note what made this hard to see: the pool has the same length every run, so
`rng.choice` consumes exactly the same number of random values. The RNG stream stays
in lockstep. Only the *selected port codes* differ. Row counts, table shapes and
most aggregate statistics are unchanged — which is why 13 of 14 gates still passed
and the build looked fine.

## Decision

**Any collection whose iteration order can reach the RNG, or reach generated data,
must have a defined order.** Sets and dicts keyed by strings are membership
structures only.

Concretely:

```python
# order-defining: this feeds rng.choice
valid_codes_list = sorted(
    locations[locations["LocationKey"] > 0]["LocationCode"].tolist()
)
# membership only: never iterated
valid_codes = frozenset(valid_codes_list)
```

The `frozenset` is kept deliberately. It documents intent at the point of use — a
`frozenset` cannot accidentally be handed to `rng.choice` and have the mistake go
unnoticed, because the reviewer's question becomes "why is this ordered?" rather
than "does this order matter?".

### Audit of every other candidate

I checked every `set(...)`, `.keys()` and `.values()` in the generator:

| Site | Verdict |
|---|---|
| `revise_voyage_rotations.py` `valid_codes` | **the bug.** Fixed. |
| `facts_ops.py` `tranship_ships`, `dem_ships`, `det_ships` | safe — sets of `int`, and used only in `np.isin` / `np.fromiter`, both order-independent. `hash(int) == int`, so int sets are not affected by hash randomisation anyway. |
| `dims.py` `used_codes`, `used_iata`, `used_imo`, `used_names`, `used_callsigns` | safe — membership-only deduplication guards, never iterated. |
| `dims.py` `known_codes` | safe — membership test inside a validation loop. |
| `BOOKING_MODE_MIX.keys()` / `.values()`, `TASK_TYPE_MIX`, `BOOKING_STATUS_MIX` | safe — `dict` preserves insertion order since 3.7, and these are module-level literals. |
| `validate.py`, `audit.py`, `crosscheck.py`, `live_feed.py` sets | safe — checkers, and all uses are order-independent. |

## Consequences

**Positive.** The build is now reproducible across processes and machines. Verified
by running the full pipeline twice in separate processes and comparing SHA-256 of
every partition. This is the property the archive's size and the live feed's
`--redo` both depend on.

**Cost.** Every calibrated constant had to be re-derived, because the fixed build
produces a different (correct, reproducible) dataset than the one those constants
were tuned against. Gate 14's congestion multipliers were the ones affected.

**Process change, and the real lesson.** Verifying the artefact you already have is
not the same as verifying the artefact you ship. I had run the three checkers many
times against my working build and got 14/14 every time. That told me the working
build was internally consistent; it said nothing about whether the generator
reproduces it. **A clean-room build from the shipped archive is now a mandatory
release step**, and `setup_all.py` exists partly so that step is one command.

A determinism test now lives in `01_generator/tests/test_determinism.py`: it runs
`revise_voyage_rotations.py` in two subprocesses with different `PYTHONHASHSEED`
values and asserts the outputs are byte-identical. Running it under an explicitly
*varied* hash seed is the point — a test that inherits one process's seed cannot
catch this class of bug.
