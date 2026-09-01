# Day 34 — solutions

All figures measured directly against `02_data/raw` and
`01_generator/meridian/facts_core.py`, not copied from the contract table.

---

## Spaced recall answers

1. A reviewer can read the actual diff — which columns/measures/relationships
   changed and how — as text, the same way a code review works. A `.pbix`
   diff reports only "binary files differ."
2. `FactWarehouseTask.TaskDateKey` already exists as a sibling column that
   carries everything a report needs from `TaskStartTs` at date grain, so
   `TaskStartTs` can be hidden with nothing lost; `BookingNo` is a real
   business key with no substitute, needed for lookup and traceability
   despite its cardinality.
3. Single-direction (`DimLocation` filters `DimWarehouse`), because the
   model already has enough role-playing relationship paths through
   `DimLocation` that a second, bidirectional path risks the same
   ambiguous-filter-context problem Day 9's `ALL`/`ALLSELECTED` distinction
   warned about, one hop further from the visual.
4. `SalesRegion` never varies across a customer's SCD2 versions (measured: 0
   of however many multi-version customers differ); `AccountManagerEmail`
   does (confirmed real example: `CUS0003`). A guard only matters when the
   filtered attribute itself changes between versions.
5. History is immutable; days are reproducible (seeded per date + reserved
   key blocks); gaps self-heal (set-difference work list); every append is
   verified before the watermark moves.

---

## Exercise 34.1 — verify #2, #5, #9 directly

**#2 — duplicate `BookingNo`.** Frozen history, 573,300 rows:
**312 distinct `BookingNo` values appear more than once** (624 rows total
involved). This matches the generator's own constant exactly —
`DUPLICATE_BOOKING_REFS = 312` in `facts_core.py` — the cleanest possible
confirmation that both the measurement and the seed agree.

**#5 — negative charge amounts.** Frozen `FactFreightCharge`, 1,610,600 rows:
**4,815 rows carry `Amount_usd < 0` (0.299% ≈ 0.3%, matching the contract
exactly)**, and **every single one of those 4,815 rows also has
`IsCreditNote = 1`** — a perfect, 1:1 overlap, not a partial correlation.
The "correct handling" column's instruction ("these are credit notes — must
be retained") is not a heuristic here; it is a structurally guaranteed fact
of how the column was generated.

**#9 — shuffled column order.** Confirmed directly via `pyarrow.parquet`
schema inspection (not `pandas.read_parquet`, which would silently realign
columns by name and hide the exact thing being tested):

```
year=2023/month=07: ['GrossWeightKg', 'DwellHours', 'MoveCostUsd', 'CraneMoves', 'IsLaden', 'IsEmpty', ...]
year=2023/month=06: ['ContainerMoveKey', 'ContainerNo', 'ShipmentKey', 'EventDateKey', 'EventTs', 'TimeKey', ...]
```

Exactly the month the contract names, and exactly the mechanism `factio.py`
documents (a `shuffle_columns_for` parameter that reorders one specific
partition's columns on write, to prove Parquet resolves by name where a CSV
union would silently misalign).

---

## Exercise 34.2 — #1 and #7, checking whether they were even built

**#1, fact side.** `FactShipment[VolumeCbm]`: **0.0% true nulls** across
493,608 rows. `FactPortCall[RevisedEtaDateKey]`: **0.0% true nulls**, but
**55.76% hold the `-1` sentinel** — a different thing entirely, and the
project's own documented convention (README §7: not-yet-happened dates hold
`-1`, never `BLANK()`) for a column that simply hasn't been revised yet, not
an injected data-quality defect. **Neither column shows the documented 4.1%
null rate.** This confirms, rather than merely repeats, `LANDMINES.md`'s own
placeholder note: landmine #1 is genuinely dimension-side only in the
current build (`RequiredTempC`, `ShelfLifeDays` — already done), and the
fact-side half (`VolumeCbm`, `RevisedEtaDateKey`) was never implemented.

**#7.** `02_data/reference/` contains **exactly 19 files, all
`Dim*.csv`, zero fact-table mirrors** — no `FactTarget.csv` exists at all.
A search of every `.py` file under `01_generator/meridian/` for
`dd/MM`-style locale date formatting or any fact-table CSV writer returns
**nothing**. **This landmine is specified in the contract and was never
built.** The honest answer, and the one worth stating plainly rather than
hedging: it is not findable in Power Query because there is nothing there to
find — confirmed by the *absence* of both the file it should live in and the
code that would have produced it, not by a failed search alone.

---

## Exercise 34.3 — #6, and a number that doesn't match the doc

**Measured:** joining `FactShipment[CustomerKey]` against
`DimCustomer[OnboardedDate]` and filtering to `OnboardedDate > ShipmentDate`
finds **38 rows, across 33 distinct customers** — not the documented 47.

**The generator's actual target,** found in `facts_core.py` line 776 and
used at line ~1003–1010:

```python
LATE_ARRIVING_CUSTOMER_ROWS = 47
...
# Landmine #6: exactly LATE_ARRIVING_CUSTOMER_ROWS shipments are pointed at a
# customer version whose validity begins after the shipment date.
```

**47 is confirmed as the generation-time target**, injected by overwriting
exactly 47 `FactShipment` rows' `CustomerKey` with one drawn from the 200
most-recently-onboarded current customers. The gap between 47 (seeded) and
38 (observed in the shipped data) is real, not a measurement error on either
side — and it has a specific, nameable cause: **`clip_and_trim`**
(`factio.py`, covered in Day 30's Concept section), which drops rows *at
random* to bring a table down to its exact target row count after
generation. Nothing in `clip_and_trim`'s logic protects a deliberately
injected landmine row from being one of the ones trimmed away — it has no
knowledge that some rows are special. **9 of the 47 originally-injected
landmine rows were most likely removed by this same random trimming step**,
which is the same mechanism, applied incidentally, that Day 30 flagged as a
reason not to assume "oldest partition" is always safe to treat uniformly —
here it's "seeded-landmine row" that isn't safe to assume survives, either.

---

## Exercise 34.4 — the checklist

See `03_powerbi/landmine_audit_checklist.md` (Ship section) for the numbered
procedure actually shipped. Its two halves, in one line each:

1. **Per-column check:** Column Distribution + Column Quality, both ticked,
   before trusting any column's "looks fine" — 0% Empty is not proof of
   emptiness, it's exactly what a text placeholder produces.
2. **Per-document check:** never trust a data-quality write-up's absence of a
   number as evidence the underlying issue doesn't exist — check whether the
   write-up itself says it's incomplete (as `LANDMINES.md`'s fact-side
   section literally does) before concluding the data is clean.

---

## Reference values used above

| Quantity | Value |
|---|---|
| Duplicate `BookingNo` values (frozen) | 312, matches `DUPLICATE_BOOKING_REFS` exactly |
| Negative `FactFreightCharge.Amount_usd` rate | 0.299% (4,815 / 1,610,600) |
| Negative-amount / `IsCreditNote` overlap | 100% (4,815 / 4,815) |
| `FactContainerMove` shuffled partition | `year=2023/month=07`, confirmed |
| `FactShipment.VolumeCbm` true-null rate | 0.0% (landmine #1 fact-side: not built) |
| `FactPortCall.RevisedEtaDateKey` true-null / `-1`-sentinel rate | 0.0% / 55.76% |
| `FactTarget` CSV mirror | does not exist (landmine #7: not built) |
| Landmine #6 seeded target vs. observed | 47 (generator constant) vs. 38 (shipped data) |
