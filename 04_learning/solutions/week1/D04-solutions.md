# Day 4 — Solutions

## Spaced recall

1. `FactContainerMove`: one row per equipment event — one physical container, one thing that happened to it, once. `FactInventorySnapshot`: one row per SKU × site × day, present whether or not anything moved that day.
2. Because a semi-additive measure (e.g. `OnHandUnits`) represents a *position*, not a flow — the same physical stock is read again on every snapshot day, so summing across days adds it to itself repeatedly. The correct aggregation is the value at the last date in the period (a closing balance), not `SUM()`.
3. Treating it as append-only means either duplicating a row for a shipment that already exists (instead of updating its date-key columns in place as new milestones occur) or failing to reflect the shipment's progress at all — the table is meant to be UPSERTed, not appended to.
4. Compression in VertiPaq is per-column and doesn't improve from normalising a dimension into sub-tables, but every relationship hop a filter has to cross at query time is real formula-engine cost — snowflaking adds hops for no compression benefit.
5. Because a null foreign key doesn't participate in any relationship at all (it falls outside every filter built on that dimension, silently understating totals) and because `NULL <> NULL` in join semantics means nulls can never even be grouped together as "the same unknown" — pointing at a real `-1` row keeps the row inside every relationship and visibly labelled "Unknown."
6. E.g. `FactBooking.QuoteKey` — it's an identifier used for grouping/drill-through, with no descriptive attributes worth building a separate dimension table and surrogate key around, so it stays directly on the fact table as a degenerate dimension.

---

## Drill 1 — Staging/load separation

A correct build looks like:

- **`stg_DimDate`** (Enable Load: off) — connects to the raw `DimDate` file, sets each column to its contracted type (`DateKey` → whole number, `Date` → date, `Year`/`Quarter`/`Month`/`Day` → whole number, `IsWeekend`/`IsMonthEnd`/etc. → whole number, not true/false, matching the contract's `int8` 0/1 convention), and does nothing else — no renames beyond fixing an obviously wrong header, no derived columns, no filtering.
- **`DimDate`** (Enable Load: on) — `= stg_DimDate` as its source step, then applies any renaming needed to match the contract's exact column names precisely, sets sort-by-column relationships if you're doing that in M rather than in the model view, and is the query actually wired into the report.

The most common mistake here is putting type-correctness and renaming in the *same* query and calling it "staging" — the discipline only pays off if staging is strictly narrower than load: staging answers "is this cell the right data type," load answers "is this table shaped and named the way the model needs." If your staging query has a step that drops or renames a column for the model's benefit rather than for correctness, that step belongs in load, not staging.

## Drill 2 — Parameter and folder-combine

`DataRootPath` should be a **text** parameter with current value pointing at your local `02_data/raw/` (or its equivalent path on your machine), referenced by every folder-source staging query as `DataRootPath & "FactContainerMove"` rather than a hard-coded absolute path.

When you filter the folder's file-listing table to `year=2023` and `year=2026` (say) before combining, and then recover `Year`/`Month` via a text split on `[Folder Path]` (something like extracting the text between `"year="` and the next `\`, and between `"month="` and the next `\`, then converting to whole numbers) **before** invoking the per-file combine function, every row in the resulting table should carry a `Year`/`Month` pair that matches the folder it actually came from — including the `year=2023/month=07` partition, which should combine without error despite its different column order (see Drill 3). If your `Year`/`Month` columns instead show values inferred from a date column *inside* the file, re-check your step order: you've derived the partition value from file content rather than recovering it from the path, which happens to work here only because the file content and the folder both agree — it will not generalise to a partition where the two ever legitimately disagree (e.g., a late-arriving row processed in a different month than its own event date).

## Drill 3 — Proving landmine #9

Pick any row where `[Folder Path]` contains `year=2023\month=07` (or `year=2023/month=07`, depending on your OS's path separator) and check its `Teu`, `Ffe`, `GrossWeightKg`, `IsLaden`, `IsEmpty` and `MilestoneKey` values against what you'd expect for a genuine equipment-move record — a laden move should show `IsLaden = 1` and `IsEmpty = 0` together with a plausible `Teu`/`GrossWeightKg` pair, not a `MilestoneKey` value sitting in a numeric weight column or a weight value sitting in a boolean column. Because Parquet embeds its schema (column names) in every file, Power Query's Parquet connector matches this reordered partition's columns to your table by name, so every value should land correctly — if you find a value in the wrong column, the bug is in your own combine logic (likely a positional assumption you introduced after the combine, such as `Table.RenameColumns` by position rather than by name), not in the source file.

**CSV counterfactual, one sentence:** if this partition had been written as CSV instead of Parquet, combining it positionally alongside every other correctly-ordered partition would silently shift every value in that one partition's rows into the wrong column, because CSV carries no embedded column identity and Power Query's combine (absent an explicit re-map by header) aligns CSV files purely by column position.

## Drill 4 — Landmine #5, walked into and fixed

The naive step — `Table.SelectRows(Source, each [Amount_usd] >= 0)` — removes **every credit-note row**: per the contract, credit notes are 0.3% of `FactFreightCharge` lines, all with negative `Amount_usd` and `IsCreditNote = 1`. On the built fact volume of 1,611,807 charge lines (README §1), 0.3% is roughly **4,835 rows** removed — every single one of them a legitimate monetary correction, not an error. If your own count came out in that neighbourhood (order of a few thousand, all `IsCreditNote = 1`), you've correctly reproduced the landmine.

The corrected version replaces the sign-based filter entirely:

```
= Table.AddColumn(Source, "Amount_usd_checked", each try [Amount_usd] otherwise null)
```

followed by inspecting (not blindly discarding) any row where the checked column is `null` while the source cell was non-blank — that's your genuine conversion-failure population, almost certainly a small, different set of rows from the credit notes, and the only population you have grounds to treat as a data-quality problem. After the fix, `COUNTROWS` filtered to `IsCreditNote = 1` should return the same count as a query with no cleaning applied at all, and `SUM(Amount_usd)` over just those rows should still be negative.

## Drill 5 — Landmine #7, walked into and fixed

Under Power Query's default type conversion (locale inherited from your machine — commonly `en-US`, month-before-day), a source row of `25/03/2025` fails loudly (there's no 25th month) and you'll see it as an error or a null, which is annoying but harmless — you'd catch it immediately. A source row of `03/07/2025` (meaning 3rd July under the file's actual `dd/MM/yyyy` format) converts **silently and wrongly** to 7th March under an `en-US` default read, because both `03` and `07` are valid month numbers and the engine has no way to know it guessed wrong.

Reloading with the explicit locale conversion —

```
= Table.TransformColumnTypes(Source, {{"TargetMonthDateKey", type date}}, "en-GB")
```

— correctly reads `25/03/2025` as 25 March 2025 (same answer as before, since it was unambiguous either way) and, critically, correctly reads `03/07/2025` as **3 July 2025**, not 7 March.

**The row that silently gave a wrong answer under the default conversion is the day ≤ 12 row** — `03/07/2025`, misread as 7 March instead of 3 July. This is exactly why the landmine is dangerous: the unambiguous row (`25/03/2025`) would have passed every spot-check you might have run, giving false confidence that "the date column looks fine," while the ambiguous row sat there wrong the entire time.
