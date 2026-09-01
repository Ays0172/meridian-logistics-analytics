# Day 34 — Formalizing the landmine audit: a repeatable checklist, and the real gaps in `LANDMINES.md`

> Time: 3.5 h · Spaced recall 10 min · Concept 40 min · Drill 100 min · Ship 30 min · Log 15 min

Two different things happened earlier in this project's history, and today's
job is to turn both into a repeatable method instead of a one-time story.
First: a real bug — text `"#NA"` masquerading as blank — was found in Power
Query, using nothing but two View-ribbon checkboxes. Second: this model was
built with **10 deliberately seeded landmines**, catalogued in
`00_docs/LANDMINES.md`. Today you check that document against what's actually
in the data, and you will find it is not fully finished — which is itself
today's most useful discovery.

---

## Spaced recall (10 min, closed book)

1. What does a `.pbip`'s `.SemanticModel/` folder let a reviewer do that a
   `.pbix` diff cannot?
2. Why is `TaskStartTs` a better candidate for hiding on cardinality grounds
   than `BookingNo`, even though both are high-cardinality?
3. State the `DimWarehouse ↔ DimLocation` decision from Day 32 and the one
   sentence of reasoning behind it.
4. Why does an RLS role built on `DimCustomer[SalesRegion]` need **no**
   `IsCurrent` guard, while one built on `AccountManagerEmail` behaves
   differently under the same guard?
5. Name the four live-feed guarantees from Day 29 in one phrase each.

---

## Concept

### The methodology, formalized from what was actually found

`03_powerbi/data_quality_findings.md` documents a real bug found this
project: several dimension columns carried the literal text `"#NA"` instead
of a true blank, in two distinct flavours —

- **Category 1a — the `-1` Unknown-member row inherited `"#NA"` as a label**
  instead of a real word like `"Unknown"`. Affects 12 columns across 7
  dimension tables (`DimCarrier.ContractRateBasis`/`PreferredTier`,
  `DimChargeType.AppliesToMode`, `DimLocation.CustomsRegime`,
  `DimService.ServiceFrequency`, `DimVessel.FuelType`/`EexiRating`,
  `DimWarehouse.RackingType`/`ShiftPattern`/`WmsSystem`/`OperatingModel`,
  `DimCustomer.ParentCustomerName`) — cosmetic, one row per column, fixed to
  `"Unknown"`.
- **Category 1b — a genuinely "not applicable" attribute stored as text**
  `"#NA"` instead of `BLANK()`, scattered across many rows wherever the
  attribute doesn't apply (`DimCarrier.AllianceName`, 135 rows;
  `DimCommodity.ImdgClass`/`UnNumber`, 720 rows each; `DimLocation.IataCode`,
  350 rows; `DimMilestone.EdifactMessageType`, 3 rows) — structural, fixed to
  true `BLANK()`.

**Why this hides from an ordinary blank check.** `"#NA"` is a real,
non-null string. `COUNTBLANK` returns 0. `<> BLANK()` filters match every row.
The column is not empty by any test that looks for emptiness — which is
exactly the trap.

**The two-minute repeatable check, using nothing but Power Query's View
ribbon:**

1. **Column Distribution** — tick it. A column showing one bar dominating the
   frequency chart, or a distinct count suspiciously low for what the column
   claims to be, is either dead or has a placeholder eating a chunk of rows.
2. **Column Quality** — tick it. This is the one that **lies on purpose** in
   this exact scenario: a column full of `"#NA"` reports **100% Valid, 0%
   Empty**, because Power Query correctly sees a non-null string. **A
   column you independently suspect has gaps, reporting 0% Empty, is itself
   the signal** — not the absence of one.
3. Click the column header's filter dropdown — Power Query lists every
   distinct value with a checkbox. A short list of code-word-looking values
   (`"#NA"`, `"N/A"`, `"-"`, `"None"`, `999999`, `1900-01-01`) sitting beside
   hundreds of real ones is a placeholder, confirmed by eye in seconds.
4. Decide category **1a vs 1b** by checking *which* rows carry it: only the
   `-1`/Unknown row → cosmetic, replace with a real label. Scattered across
   many real rows, conditionally meaningful → structural, replace with `null`.
5. **Quantify it in DAX** once you suspect a column:
   `CALCULATE(COUNTROWS(Table), Table[Column] = "#NA")` returning nonzero
   while `COUNTBLANK(Table[Column])` returns 0 is the confirmed diagnosis.

**The companion finding — dead columns, same audit pass.**
`FactTransportLeg.ContainerNo` and `FactFreightCharge.ContainerNo` were found
to be **100% `"#NA"`, distinct count 1** — genuinely dead for those tables
(a container number only applies to FCL container moves; both tables also
carry non-container traffic). The fix was to **hide, not delete** — the
source column stays traceable if anyone ever needs to re-derive why it's
empty, but it never clutters the field list. A distinct count of 1 on Column
Distribution is the single fastest "is this column worth anyone's time" check
you have, and it costs nothing to run on every table before you build a
single measure against it.

### Cross-referencing `LANDMINES.md` against the real 10-item contract

`SCHEMA_CONTRACT.md` §3.5 lists **10 deliberately seeded landmines** — the
authoritative index. `LANDMINES.md` is where each one is supposed to be
written up in full: what was injected, where, the rate observed, and the
correct handling. **Check the two documents against each other rather than
trusting either one alone — that check is today's first real finding.**

| # | Landmine (from the contract) | Written up in `LANDMINES.md`? |
|---|---|---|
| 3 | Mixed casing + trailing whitespace, `DimLocation.LocationName` | ✅ full write-up, rate measured (8.11% of 419 rows) |
| 4 | Two spellings of one country, `DimLocation.CountryName` | ✅ full write-up (`VN`/`KR` split) |
| 8 | 3 implausible `DimVessel.NominalTeuCapacity` outliers | ✅ full write-up, exact `VesselKey`s named |
| 10 | Leading-zero `DimSku.SkuCode`, CSV mirror only | ✅ full write-up, `pandas.read_csv` failure demonstrated |
| 1 | 4.1% nulls: `VolumeCbm`, `RequiredTempC`, `ShelfLifeDays`, `RevisedEtaDateKey` | **Partial.** Dimension half done (`RequiredTempC`, `ShelfLifeDays`); fact half explicitly marked out of scope |
| 2, 5, 6, 7, 9 | duplicate `BookingNo`; negative charges; late-arriving customers; text-as-date CSV; shuffled column order | **Not written up at all** — the document's own "Fact-side landmines" section is a literal placeholder: *"to be completed by the agent building the fact layer... out of scope for the dimension-layer build documented above."* |

**The fact tables now exist** — 7.5M rows, built and verified, per the
README. **Nobody went back and filled in that section.** This is not a
hypothetical gap for you to imagine; it is the actual, current state of a
real document in this real repo, and today's Ship section is to finish it —
using rates you measure yourself, the same way the dimension-side entries
were measured, not by copying the one-line descriptions out of the contract
table.

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 34.1 — verify #2, #5, #9 directly (30 min)
For each, predict the rate/finding before checking, using only the contract
table's one-line description as your hint:
- **#2** — count `FactBooking[BookingNo]` values that appear more than once
  (`value_counts() > 1`), on the frozen history. Predict roughly how many
  before running.
- **#5** — compute the rate of `FactFreightCharge[Amount_usd] < 0`, and
  cross-tabulate against `IsCreditNote`. Predict whether the two align
  perfectly or only partially before checking.
- **#9** — compare `FactContainerMove`'s column order between
  `year=2023/month=07` and any adjacent month, using a Parquet schema reader
  (not a DataFrame — a `DataFrame` would silently realign columns by name and
  hide the very thing you're checking for). Predict which specific month is
  the shuffled one before opening it.

### Exercise 34.2 — #1 and #7, checking whether they were even built (25 min)
For **#1**: check `FactShipment[VolumeCbm]` and `FactPortCall[RevisedEtaDateKey]`
for true nulls (not the `-1` sentinel — check both separately and explain
why they're different things). Predict, given `LANDMINES.md`'s own
placeholder note, whether you'll find the documented 4.1% or something much
closer to 0%.

For **#7**: look for a `FactTarget` CSV mirror anywhere under
`02_data/reference/`, and search the generator source for any locale-date
text-formatting logic (`dd/MM/yyyy`, or equivalent). Predict, before
searching, whether this landmine is (a) present and you just haven't found
the right file, or (b) specified in the contract but never actually built.
State which one you found, and how you know for certain rather than just
"I didn't find it."

### Exercise 34.3 — #6, and a number that doesn't match the doc (25 min)
Join `FactShipment[CustomerKey]` against `DimCustomer[OnboardedDate]` and
find shipments where the customer's onboarding postdates the shipment. The
contract says "47." Predict whether your count will match exactly, and if
not, in which direction. Then search `01_generator/meridian/facts_core.py`
for the literal constant this landmine is built from, and read the ~15 lines
around it. Explain, using what that code actually does (not what the one-line
contract description implies), the most likely reason your measured count
and the generator's target constant disagree — name the specific mechanism
from `factio.py` (Day 30's Concept section covered it) that could shrink a
table's row count post-generation without touching which rows survive being
seeded any differently.

### Exercise 34.4 — build the checklist (20 min)
Write `03_powerbi/landmine_audit_checklist.md`: a numbered, repeatable
procedure combining the Column Distribution / Column Quality method from the
Concept section with the "check the contract table against the write-up
document" cross-reference method from Exercise 34.1–34.3. This is not a
restatement of today's lesson — it should be short enough that you'd
actually run it against a table you've never seen before, in under five
minutes, without re-reading this file.

---

## Ship

Fill in `LANDMINES.md`'s fact-side section for real, in the same format as
the dimension-side entries (what was injected / where / rate observed /
correct handling), for landmines #2, #5, #6, #9 using the numbers you
measured today, and for #1 and #7 stating plainly — with your evidence —
that they are not (yet) implemented on the fact side rather than guessing at
a rate that doesn't exist. This turns a real, currently-incomplete project
document into a finished one.

```
git add .
git commit -m "Day 34: landmine audit checklist written, LANDMINES.md fact-side section completed with measured rates"
```

---

## Log

What clicked / what did not / what to re-ask. Note specifically: which
landmine's real number surprised you most, and why.

---

## Exit criteria

- [ ] You can run the Column Distribution / Column Quality check from memory,
      including the specific "0% Empty is itself the signal" tell.
- [ ] `LANDMINES.md`'s fact-side section is filled in with real, measured
      numbers — not copied from the contract table.
- [ ] You can state which two of the ten landmines are not actually
      implemented in the current build, and how you confirmed that rather
      than assumed it.
- [ ] You found and can explain the discrepancy between landmine #6's
      documented count and what's observable in the shipped data.
- [ ] `landmine_audit_checklist.md` exists and is short enough to actually
      use.
- [ ] Predictions recorded, misses annotated.
