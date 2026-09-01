# Day 31 — solutions

All figures computed from `02_data/raw` (frozen history, 491,400 `FactShipment`
rows) joined against `02_data/reference/DimCustomer.csv` and
`DimLocation.csv`, and against the full `FactTarget` table (51,900 rows, all
60 partitions). Total frozen `FactShipment` revenue: **$2,039,118,300** — this
lines up with README §6's all-history figure of $2,040,774,144 once the small
number of live-appended days on top of the frozen snapshot are added in,
which is itself a useful cross-check that nothing was mis-joined.

---

## Spaced recall answers

1. `TREATAS(<table>, <col1>, <col2>, …)` applies `<table>`'s current values
   **as if** they were a filter directly on the named columns. The first
   argument supplies the values; the columns after it are what gets filtered.
2. `DimLocation[TradeRegion]` bridges `FactTarget[Region]` — both take the
   same five values. `DimLocation[Region]` is a finer, non-matching grain; use
   it and you get a plausible-looking wrong join, not an error.
3. It activates an inactive relationship for the duration of one evaluation.
   This model needs it because several fact tables carry more than one
   foreign key into the same dimension (e.g. `FactShipment`'s four
   `LocationKey*` columns into `DimLocation`) — Power BI allows only one
   active relationship per table pair, so every additional role-playing path
   is necessarily inactive by default.
4. `DimCustomer` is SCD2. `IsCurrent = 1` marks the one row per `CustomerCode`
   that is the customer's present-day version; older versions carry
   `IsCurrent = 0` and a closed `ScdValidTo`.
5. 8 refreshes/day on Pro, 48/day on PPU or Fabric capacity.

---

## Exercise 31.1 — build and test `Sales - APAC`, both ways

**Prediction basis, worked from the Concept section alone:** 368 of 1,561
APAC customer-versions are non-current. Adding `IsCurrent = TRUE()` should
therefore make the number **smaller**, not larger — the guard removes rows,
it can't add revenue.

**Measured:**

| Role filter | `Revenue` under View As | vs. plain `SalesRegion = "APAC"` |
|---|---|---|
| `[SalesRegion] = "APAC"` (no guard) | **$965,503,550** | — |
| `[SalesRegion] = "APAC" && [IsCurrent] = TRUE()` | **$883,716,500** | **−$81,786,850 (−8.47%)** |

The guarded version is smaller by exactly the revenue tied to
`FactShipment` rows whose `CustomerKey` resolves to one of the 368
non-current APAC customer-versions (19,318 rows). The independent
cross-check measure (`CALCULATE([Revenue], DimCustomer[SalesRegion]="APAC")`,
with and without the `IsCurrent` clause) reproduces both numbers exactly,
confirming the role's behaviour matches ordinary `CALCULATE` filter
semantics — it is the same mechanism, just applied earlier.

**Which one ships:** the ungated version, `$965,503,550` — see the Concept
section for why.

---

## Exercise 31.2 — find the leak

`FactShipment` carries `LocationKeyOrigin`/`LocationKeyPol` as one matched
pair and `LocationKeyDestination`/`LocationKeyPod` as another (POL = origin
port, POD = destination port for an ocean move — the two pairs are
numerically identical in this data, confirming that's exactly what they
represent):

| Path | "Americas" revenue *if RLS could reach it* | Actual under `Region - Americas`, this path **inactive** |
|---|---|---|
| `LocationKeyOrigin` / `LocationKeyPol` | $423,986,200 (20.79%) | — |
| `LocationKeyDestination` / `LocationKeyPod` | $425,010,800 (20.84%) | — |

The two "natural" subsets are close in size (Meridian's trade is roughly
balanced inbound/outbound), which is a red herring — **that is not the
number the leak exercise is testing.** The actual failure mode: whichever of
the two paths is the **inactive** relationship shows the full,
**unrestricted total, $2,039,118,300** — not $425M, not some other
plausible-looking number, the entire book. A role member sees their own
region correctly on an origin-based visual and the whole company's revenue on
a destination-based one, on the same page, with no error, warning, or visual
cue that anything is different between the two.

**What this means in practice:** any visual built against the inactive
location role is invisible to a data-quality reviewer scanning for "does the
region filter look right" — the number just looks like a bigger number, not a
broken one. The only reliable check is to deliberately build a visual against
*every* role-playing foreign key on a fact table and View As each one, per
role, rather than trusting that one correct-looking card means the role is
safe everywhere.

---

## Exercise 31.3 — plug the `FactTarget` gap

`FactTarget` totals (all 4 scenarios, all 60 partitions): **$178,201,680**.
Region breakdown: Americas $35,776,624 (20.08%), MEA, Oceania, Europe, Asia
roughly even at the remaining ~80%.

| Rule state | `FactTarget[TargetValue]` under View As `Region - Americas` |
|---|---|
| Without the `TREATAS` rule on `FactTarget` | **$178,201,680** (unrestricted — the role has no path into this table at all) |
| With the `TREATAS` rule | **$35,776,624** |

The gap the rule closes is the full $142,425,056 difference — every dollar of
budget/target data belonging to the other four regions, which a `TradeRegion`
role with no explicit `FactTarget` rule would otherwise expose to every
region's readers regardless of scope. This is Day 13's finding wearing a
security hat: no physical relationship means no default protection, and the
same `TREATAS` bridge that made the measure work is what the role needs too.

---

## Exercise 31.4 — a role where the guard genuinely matters

`CUS0003` is the illustrative single case — version 1 (`ScdVersion=1`,
`IsCurrent=0`) carried `AccountManagerEmail = carlos.al-farsi@meridiangl.com`,
valid through `2021-02-12`; version 2 (`ScdVersion=2`, `IsCurrent=1`) carries
`yuki.obrien@meridiangl.com` from `2021-02-13` onward — but Carlos is not
`CUS0003`'s account manager alone. Checked against the shipped
`DimCustomer.csv`: `carlos.al-farsi@meridiangl.com` appears on **75 rows
across 70 distinct customers — 58 current versions and 17 non-current**.

An ungated `AM - Carlos` role (`[AccountManagerEmail] =
"carlos.al-farsi@meridiangl.com"`, no `IsCurrent` clause) matches **all 75**
of those `DimCustomer` rows, current and non-current alike, and therefore lets
through every `FactShipment` row keyed to any of their `CustomerKey`s —
including shipments booked while Carlos managed a customer he has since
handed off (like `CUS0003` before 2021-02-12). Adding `IsCurrent = TRUE()`
drops the 17 non-current rows, which means it drops every `FactShipment` row
keyed to one of those 17 `CustomerKey`s too. **The guard changes the answer
materially here** — this is the mirror image of `Sales - APAC`, not a repeat
of it: because `AccountManagerEmail` genuinely varies across a customer's
SCD2 versions (unlike `SalesRegion`, which never does), "all versions" and
"current only" are two different, both-defensible questions with two
different numbers, exactly as the Concept section predicted. Which one is
"correct" depends on what the role is for: ungated answers *"every shipment
Carlos was ever the account manager of record for, historically"* (the right
scope for a departing-AM handover audit); gated answers *"only the shipments
tied to customers currently on Carlos's book"* (the right scope for his live
commission or territory report). Shipping the wrong one for the business
question is the actual risk, not a `#NA`-style bug — pick deliberately, and
document which question the role answers in `03_powerbi/rls_roles.md`.

**The one fact that decides which way a given role behaves:** whether the
*filtered column itself* changes value across a customer's SCD2 versions.
`SalesRegion` never does (0 customers differ) — so restricting to
`IsCurrent` only ever removes legitimately-matching historical rows without
changing which *customers* are in scope, which is why that guard turned out
to be pure overhead for `Sales - APAC`. `AccountManagerEmail` does vary by
construction — so gating by `IsCurrent` here changes *which customers* (and
therefore which `FactShipment` rows) the role includes at all. Check which
kind of column you're filtering on before deciding whether the guard helps,
hurts, or does nothing — it is never safe to assume from habit.

---

## Reference values used above

| Quantity | Value |
|---|---|
| Total frozen `FactShipment` revenue | $2,039,118,300 |
| APAC revenue, all customer versions | $965,503,550 |
| APAC revenue, `IsCurrent` guarded | $883,716,500 |
| Revenue lost to the guard (APAC) | $81,787,050 (19,318 rows) |
| `FactShipment` rows keyed to a non-current `DimCustomer` version | 35,053 of 491,400 (7.13%) |
| Americas revenue via `LocationKeyOrigin`/`Pol` | $423,986,200 |
| Americas revenue via `LocationKeyDestination`/`Pod` | $425,010,800 |
| `FactTarget` total `TargetValue`, all scenarios | $178,201,680 |
| `FactTarget` Americas `TargetValue` | $35,776,624 |
