# Data-quality landmines

This document explains every deliberate data-quality issue injected by the generator, per
`SCHEMA_CONTRACT.md` SS3.5. It is split into the dimension-layer landmines (built and verified by
this pass, `01_generator/meridian/dims.py`) and a placeholder for the fact-layer landmines, to be
filled in once `FactBooking`, `FactFreightCharge`, `FactContainerMove`, `FactPortCall`, etc. exist.

Row/rate figures below were measured on the `prod`-scale run (`python build_dims.py --scale prod`,
seed `20260824`) and will shift slightly at `dev`/`stress` scale or if the seed changes, but the
*mechanism* and *target rate* are identical across scales.

---

## Dimension-side landmines

### #3 -- Mixed casing + trailing whitespace (`DimLocation.LocationName`)

**What was injected.** 8% of `DimLocation`'s real rows (excluding the `-1` Unknown member) have
their `LocationName` mangled: the text is upper-cased, lower-cased, or case-swapped, and then
padded with two leading spaces, two trailing spaces, and a trailing tab (`"  MANGLED VALUE  \t"`).
Implemented in `meridian/dims.py::_clean_title_whitespace_landmine`, called from
`build_dim_location`.

**Where.** `DimLocation.LocationName`, in **both** the parquet (`02_data/raw/DimLocation/`) and the
CSV mirror (`02_data/reference/DimLocation.csv`) -- this one is a property of the data itself, not
an artefact of one file format, so both copies carry it.

**Rate observed.** 34 of 419 real rows = **8.11%** (target: 8%).

**Correct handling in Power Query.** `Text.Trim` then `Text.Proper` (or `Text.Trim` +
`Text.Lower`/manual title-casing if `Text.Proper` mis-cases known multi-word proper nouns like
"Ho Chi Minh City"). Do this **before** any grouping, joining, or de-duplication on `LocationName`
-- comparing un-trimmed/mis-cased text will silently create duplicate groups for the same real
location.

### #4 -- Two spellings of the same country (`DimLocation.CountryName`)

**What was injected.** Two `CountryCode`s carry two different spellings of the same country's
name across their rows, split roughly 50/50 by a seeded coin flip per row:

| `CountryCode` | Spelling A | Spelling B |
|---|---|---|
| `VN` | "Vietnam" | "Viet Nam" |
| `KR` | "South Korea" | "Korea, Republic of" |

Implemented via `_COUNTRY_NAME_ALT` in `meridian/dims.py::build_dim_location`.

**Where.** `DimLocation.CountryName`, both parquet and CSV (same reasoning as #3 -- it's a data
property, not a file-format quirk).

**Rate observed.** `VN`: 12 "Vietnam" / 3 "Viet Nam" (15 rows total). `KR`: 5 "South Korea" / 6
"Korea, Republic of" (11 rows total). Small-sample variance around the 50/50 target is expected
and fine -- the point is that *both* spellings exist for the *same* `CountryCode`.

**Correct handling in Power Query.** Never fix this with find-and-replace on `CountryName` alone
(it doesn't scale, and it's easy to miss a spelling or a future one). Build a small **country
name -> canonical name mapping table** (keyed by the stable `CountryCode`, which is never
ambiguous) and merge/join it in, replacing `CountryName` with the canonical value. This is the
general pattern for any "reference data drifted between source extracts" problem, not just this
one pair.

### #8 -- Implausible `NominalTeuCapacity` outliers (`DimVessel`)

**What was injected.** After generating all vessels with class-consistent capacity (a `Feeder`
only ever gets 1,100-2,999 TEU, a `ULCV` only 16,000-23,900 TEU, etc. -- see
`_VESSEL_CLASS_SPECS`), exactly 3 real rows are overwritten with capacity figures that contradict
their `VesselClass`, simulating data-entry errors:

| `VesselKey` | `VesselClass` | Injected `NominalTeuCapacity` | Why it's implausible |
|---|---|---|---|
| 110 | Handysize | 350 | Below even the smallest Feeder's minimum (1,100) |
| 201 | Neo-Panamax | 21,000 | ULCV-sized capacity on a mid-size hull |
| 213 | Neo-Panamax | 99,999 | Outside the contract's entire 1,100-23,900 range |

Implemented as the very last step of `build_dim_vessel`, after the coherent generation, so the
error reads as exactly what it's meant to simulate -- a fat-fingered override, not part of the
underlying distribution.

**Where.** `DimVessel.NominalTeuCapacity` only (parquet and CSV both carry it -- it's a genuine
attribute value, not a file-format artefact).

**Correct handling in Power Query / analysis.** **Flag, don't silently drop.** A reasonable rule:
flag any row where `NominalTeuCapacity` falls outside the plausible band for its `VesselClass` (or
outside 1,100-23,900 entirely), surface it in a data-quality report, and let a human decide whether
to correct, exclude, or leave the flagged measure out of capacity-utilization calculations for that
vessel. Silently deleting the row would also delete every voyage/booking/container-move fact that
legitimately references that vessel.

### #10 -- Leading-zero business key (`DimSku.SkuCode`, CSV mirror only)

**What was injected.** The canonical `SkuCode` (parquet, e.g. `SKU-000001`) always keeps its
`SKU-` prefix, so it can never be misread as a number. The **CSV mirror** (`02_data/reference/
DimSku.csv`) strips that prefix for every real row, leaving a bare zero-padded numeric string
(e.g. `000001`) -- exactly the shape of a business key that a naive CSV export or Excel
auto-detection will read as a *number*, silently discarding the leading zeros.

Implemented in `build_dim_sku`: the function returns `(df, csv_df)`, where `csv_df` is a copy with
`SkuCode` stripped of its prefix; `build_dims.py` passes `csv_df` to `write_dim(..., csv_df=csv_df)`
so only the reference CSV is affected.

**Where.** `DimSku.SkuCode`, **CSV mirror only** -- `02_data/raw/DimSku/part-000.parquet` keeps the
full `SKU-000001` form.

**Verified effect.** `pandas.read_csv` with default type inference reads the CSV's `SkuCode` column
as `float64` and turns `"000001"` into `1.0` -- a real, reproducible demonstration of the failure
mode, not just a description of it.

**Correct handling in Power Query.** Import `SkuCode` explicitly as **Text**, never let the query
editor auto-detect its type. In Power Query terms: set the column's data type to `Text` in the
first `Table.TransformColumnTypes` step, before any other transformation touches it. If the key
must be reconciled against the parquet copy's `SKU-000001` form, pad left with zeros to 6 digits
and prepend `SKU-` (`Text.PadStart([SkuCode], 6, "0")`) rather than assuming the two files already
agree on format.

---

## Fact-side landmines

*(placeholder -- to be completed by the agent building the fact layer)*

SCHEMA_CONTRACT.md SS3.5 items **#1** (partially -- see note below), **#2**, **#5**, **#6**, **#7**,
and **#9** are fact-table landmines (`FactBooking`, `FactFreightCharge`, `FactShipment`,
`FactPortCall`, `FactTarget`, `FactContainerMove`) and are out of scope for the dimension-layer
build documented above. They should be documented here, in this same format (what was injected /
where / at what rate / correct handling), once the fact tables exist.

**Note on landmine #1** ("4.1% nulls in optional fields"): its column list spans both layers --
`VolumeCbm` and `RevisedEtaDateKey` are fact-table columns (out of scope here), but `RequiredTempC`
(`DimCommodity`) and `ShelfLifeDays` (`DimSku`) are dimension columns already built in this pass.
Both dimension columns are null wherever the underlying business logic says they should be (e.g.
`RequiredTempC` is null for any commodity that isn't temperature-controlled), **and** an
additional, independent 4.1% of `DimSku.ShelfLifeDays` values are randomly nulled on top of that
business-logic null rate, matching the contract's stated rate. `DimCommodity.RequiredTempC` was left
at its business-logic-only null rate (roughly 80%, since only a handful of headings are
temperature-controlled) -- the fact-layer agent should decide whether to also layer the extra 4.1%
onto it, and should treat this whole landmine as "partially implemented, dimension side" until the
fact-side columns are done too.
