# Meridian Semantic Model — Data Quality Audit & Fixes

**Model:** `yLogistics_Live.pbix`
**Scope:** Full model — 30 tables (19 dimensions, 11 facts)
**Status:** All items below are fixed and refresh-verified in the live model.

---

## 1. What was wrong

Two unrelated problems were hiding under one symptom ("this column looks messy"):

### 1a. The `-1` Unknown-member row inherited `"#NA"` instead of a real label

Every dimension has a `-1` surrogate-key row reserved for unmatched/unknown foreign keys (the standard "unknown member" pattern). On several dimensions, the *text attribute* columns on that one row were literally the string `"#NA"` — an artifact of how the row was seeded, not a real data value. Only that single row was affected on each column; every other row was populated normally. This is cosmetic, not structural: it shows up as an ugly label whenever `-1` rows surface in a visual (e.g. "Carrier: #NA" instead of "Carrier: Unknown"), and it invites confusion with the second problem below.

**Affected (fixed → `"Unknown"`):**
| Table | Column |
|---|---|
| DimCarrier | ContractRateBasis, PreferredTier |
| DimChargeType | AppliesToMode |
| DimLocation | CustomsRegime |
| DimService | ServiceFrequency |
| DimVessel | FuelType, EexiRating |
| DimWarehouse | RackingType, ShiftPattern, WmsSystem, OperatingModel |
| DimCustomer | ParentCustomerName |

### 1b. Genuine "not applicable" attributes stored as text `"#NA"` instead of `BLANK()`

These columns carry real data for the rows where the attribute applies, and `"#NA"` for the (many) rows where it genuinely doesn't apply — e.g. `ImdgClass` is only meaningful for dangerous-goods commodities; most commodities aren't DG, so most rows legitimately have nothing to say. The problem: Power BI's `BLANK()` and `COUNTBLANK()` treat blank/null specially in DAX and visuals, but a *text string* `"#NA"` is never blank — `DISTINCTCOUNT`, `<> BLANK()` filters, and "Show items with no data" all silently miss these rows or double-count a fake category called "#NA". A filter like `ImdgClass <> BLANK()` returns every row (nothing is ever truly blank), while the intended filter is `ImdgClass <> "#NA"`.

**Affected (fixed → true `BLANK()`, verified counts in parentheses):**
| Table | Column | Rows converted to BLANK() |
|---|---|---|
| DimCarrier | AllianceName | 135 |
| DimCommodity | ImdgClass | 720 |
| DimCommodity | UnNumber | 720 |
| DimLocation | IataCode | 350 |
| DimMilestone | EdifactMessageType | 3 |

These counts matched the pre-fix `"#NA"` occurrence counts exactly, confirming nothing else moved.

### Fix mechanism

Both categories were fixed in Power Query (M), not by touching the source CSVs, so the fix survives a refresh from `02_data/reference/*.csv`. A final step was appended to each affected table's query:

```
#"Replaced NA" = Table.TransformColumns(#"Changed column type", {
    {"ColumnA", each if _ = "#NA" then "Unknown" else _, type text},   // category 1a
    {"ColumnB", each if _ = "#NA" then null else _, type text}        // category 1b
})
in
    #"Replaced NA"
```

`null` in M becomes `BLANK()` in the DAX/report layer. All 9 affected tables were then given a Full refresh and re-verified with a DAX query counting remaining `"#NA"` occurrences (all zero) and resulting blanks (all matching expected counts).

---

## 2. How to find this yourself next time (no DAX required)

This class of bug hides from a plain "does this table have blanks" check because the placeholder text isn't blank — that's exactly the trap. Two Power Query Editor views catch it in under a minute per table, no formulas needed:

1. **Column Distribution** (Power Query Editor → View ribbon → tick "Column distribution"). Above each column it shows a small bar chart of value frequency plus distinct/unique counts. A column that's supposed to be free-text but shows one bar dominating the chart, or a distinct count suspiciously equal to 1, is either dead (only one value ever) or has a placeholder swallowing a chunk of rows.
2. **Column Quality** (same View ribbon → tick "Column quality"). This shows, per column, the % Valid / % Error / % Empty right under the header. This is the one that *lies* in this exact scenario: a column full of `"#NA"` text reports 100% Valid and 0% Empty, because Power Query correctly sees a non-null string — that mismatch (0% Empty on a column you *know* has gaps) is itself the signal.
3. Once a column looks suspicious, right-click the column header → **"Value Distribution"** or just eyeball the top of the column list — any value that looks like a code word rather than real data (`"#NA"`, `"N/A"`, `"-"`, `"None"`, `"Unknown"`, `999999`, `1900-01-01`) is a candidate placeholder. Click the filter dropdown on the column header — Power Query lists every distinct value with a checkbox; a short, suspicious-looking list (vs. hundreds of real values) confirms it fast.
4. Decide which of the two categories it is by checking *how many rows* carry the placeholder and *which rows*:
   - Only the `-1`/Unknown-member row → category 1a → replace with a real label like `"Unknown"`.
   - Many rows, scattered, and the attribute is conditionally meaningful (only applies to a subset, like DG-only or airport-only attributes) → category 1b → replace with `null` (true blank).
5. To fix: right-click the value in the column preview → **Replace Values...** (this is the UI-equivalent of the `Table.TransformColumns` step used here) — set "Value To Find" to `#NA` and "Replace With" to either `Unknown` or leave blank/delete for a true null, depending on category. Power Query records this as a step automatically; no manual M editing required.

The DAX-side tell (useful once you suspect a table, to quantify it precisely): `CALCULATE(COUNTROWS(Table), Table[Column] = "#NA")` — if this returns a number greater than zero while `COUNTBLANK(Table[Column])` returns 0, you've confirmed a placeholder-instead-of-blank problem on that column.

---

## 3. Everything else audited this pass (for reference)

- **Dead / degenerate columns** — `FactTransportLeg.ContainerNo` and `FactFreightCharge.ContainerNo` were 100% `"#NA"` (distinct count 1) — genuinely dead, no conditional meaning. Hidden from the model (not deleted, so the source column stays traceable).
- **True nulls / blanks** — every FK, date-key, and measure column across all 30 tables was checked; zero true nulls anywhere. All FK columns correctly use the `-1` sentinel rather than blank, which is why they were excluded from this fix (sentinel keys are a deliberate, correct pattern — leave them as `-1`, do not blank them).
- **Formatting** — currency (`$#,##0.00` / `#,##0.00` for non-USD "document currency" values), percentages (checked actual value ranges before formatting — `OnTimeTargetPct` is a true 0–1 fraction using `0.0%`, while a differently-scaled 0–100 percentage column needed the literal `0.0"%"` format instead of a true percentage format), FX rates (`#,##0.0000`), physical quantities, and date/timestamp columns were corrected across ~200+ columns model-wide.
- **`summarizeBy`** corrected from the default `Sum` to `None` on ~24 non-additive numeric columns (coordinates, rates, vessel specs, year columns, percentages) so they don't silently sum in visuals.
- **Relationships** — 108 total (was 81): fixed one mis-wired relationship (`FactContainerMove` was joined to `DimDate` on its own surrogate key instead of `EventDateKey`), and added 27 correctly-inactive role-playing-date relationships across 6 fact tables. A handful of dimension-to-dimension and fact-to-fact relationships are deliberately left inactive to avoid Power BI's single-active-path cycle rule — this is by design, not an oversight.
- **Hidden columns** — 166 surrogate keys, SCD audit columns, and sort-helper columns hidden model-wide to declutter the field list for report authors.

## 4. Still open / not part of this pass

- 3 fact-to-fact bridge relationships and the `DimWarehouse ↔ DimLocation` bidirectional relationship are flagged for a deliberate decision, not yet made.
- No DAX measures exist in the model yet (0 measures) — the measure library is a separate, upcoming step per the curriculum.
- Calculation groups, TMDL export of the finished model into this folder, and refresh-source verification against `02_data/raw` are still pending.
