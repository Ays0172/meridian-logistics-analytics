# Day 4 — Power Query as an Engineering Discipline
> Time: 2.5 h · Concept 35 min · Drill 60 min · Ship 50 min · Log 15 min

## Spaced recall (10 min, closed book)

1. State the grain of `FactContainerMove` and `FactInventorySnapshot` in one sentence each.
2. Why does summing a semi-additive measure across the date dimension produce a wrong number, and what's the correct aggregation instead?
3. What breaks if you treat `FactShipmentMilestone` as an append-only transaction fact during a refresh?
4. Give the VertiPaq-grounded reason for preferring a star schema over a snowflaked one — without saying "simpler."
5. Why does every dimension carry a `-1` "Unknown" row instead of allowing a null foreign key?
6. Name one degenerate dimension from the contract and explain why it doesn't get its own dimension table.

## Concept

Today you open Power BI for the first time this programme, and today is where the schema and domain knowledge from the last three days stops being theory and starts being the thing that saves you from three specific, named landmines sitting in the raw data waiting for exactly the mistake a rushed analyst makes. Power Query is not "the cleaning step before the real work" — treated as an engineering discipline, with the same rigour you'd bring to a script, it *is* the real work, because every number your model ever produces is only as trustworthy as what happened in this layer.

### 1. Staging vs load queries — separate "getting it right" from "shaping it"

Two categories of query, one discipline:

- **Staging queries** connect to a raw source and do only correctness work: correct types, correct column names, nothing that reshapes the data's meaning. They have **Enable Load unchecked** — they never become a table in your model, they exist purely as a clean, typed, trustworthy input that other queries reference.
- **Load queries** reference a staging query and do the shaping work that actually produces a model table: renaming to the contract's exact column names, adding derived columns, filtering to what the model needs. These have **Enable Load checked**.

Why bother splitting these at all, rather than doing everything in one query per table? Two reasons that matter in practice, not just in style guides. First, **a staging query with load disabled costs you nothing in model size or refresh** — it's a pass-through, not a table sitting in memory, so you get to organise your correctness logic cleanly without paying for it twice. Second, and more important: **any transformation likely to break folding (see below) belongs as late as possible in the chain**, which means putting foldable, source-native operations (filtering, type conversion, column selection) in the staging layer and reserving custom M logic, complex conditionals, and merges for the load layer — because once folding breaks, everything downstream in that query is evaluated locally regardless of where you put it, so there's no benefit to being tidy about ordering *after* the break point, only before it.

### 2. Query folding — what it actually is, and where it doesn't apply

Query folding is Power Query translating your M steps into the data source's *own* native query language — SQL, for a relational database — so the source system does the filtering, sorting and aggregating, and Power Query only receives the already-reduced result. This is why folding matters so much for performance: a folded filter on a ten-million-row SQL table means the database does the work with its own indexes; an unfolded filter means Power Query pulls all ten million rows across the wire first and filters them in memory.

**What typically folds** (on a foldable, relational-style source): row filters (`Table.SelectRows`), column selection and removal, renames, straightforward type changes, sorting, and some joins.

**What breaks folding**: custom M expressions with no native-source equivalent, most `Table.AddColumn` steps using general M functions, index columns, and — critically for you specifically — **anything applied after you've combined multiple files into one in-memory table**, because at that point there is no longer a single "source" left to translate a query back to.

**Here is the correction that matters for this dataset specifically: none of this — including "View Native Query" as a verification method — applies to Meridian's Parquet folder sources the way it applies to a SQL database.** Query folding, in the traditional sense, is a relational/OData concept; flat-file and folder-based connectors (CSV, Parquet, and the Folder connector generally) have no native query language to fold into, so "View Native Query" will simply be unavailable for every query in this dataset — that's expected, not a sign you've done something wrong.

What you *do* get, and what you must verify instead, is **file-level filtering before combine**: when you connect to a folder, Power Query first shows you a navigation table listing every file with its `Folder Path`, `Name`, `Extension` and other metadata — and if you filter *that* table (for instance, to only the `year=2025` and `year=2026` partitions while developing) **before** you invoke the combine step, Power Query only parses the files that survive the filter. The verification technique here isn't a native-query dialog — it's checking your row counts and refresh time against what you'd expect from the number of files that should actually match your filter, and confirming (by temporarily widening or narrowing the filter) that the count moves the way file inclusion, not row-level filtering after the fact, would predict.

### 3. Parameters for the data path

Hard-coding `C:\Users\yourname\work\02_data\raw` into every query is the single most common reason a Power BI file that worked perfectly on one machine breaks the moment it's shared. Create a single text **parameter** — call it `DataRootPath` — pointing at `02_data/raw`, and have every staging query build its folder path by concatenating that parameter with the table-specific subfolder (`DataRootPath & "FactContainerMove"`). Switching machines, switching from `dev` scale to `prod` scale, or handing the file to a teammate becomes a one-parameter edit instead of a find-and-replace across every query — and because the parameter is itself a query, it's visible and editable in the Queries pane, not buried in a connection string.

### 4. Custom functions — write once, apply to every file

The folder-combine pattern (below) generates one automatically: when you use Power Query's "Combine Files" experience, it builds a **sample-file transform query** (the steps you define once, against one example file) and a **linked function query** that applies those exact steps to every other file in the folder. Editing the sample query's steps automatically updates the function — you never touch the function directly. Beyond that generated one, write your own custom functions for any logic you find yourself repeating across staging queries — a locale-safe date parser (§7 below) is the clearest candidate this week, because you'll need the same "parse this text as a `dd/MM/yyyy` date, explicitly, regardless of the machine's regional settings" logic wherever a similarly-formatted text date shows up.

A worked custom function, since you'll want exactly this reusable across every `dd/MM/yyyy`-style text date you meet, on this dataset or any other:

```
// fnParseUkDate
(dateText as nullable text) as nullable date =>
    if dateText = null or dateText = "" then null
    else try Date.FromText(dateText, "en-GB") otherwise null
```

Call it with `Table.TransformColumns(Source, {{"TargetMonthDateKey", fnParseUkDate}})` and you get the same explicit, locale-safe behaviour as §8 below, written once and reusable anywhere else a `dd/MM/yyyy` text column turns up — which, per the contract's landmine list, is a real risk on any mirror CSV you haven't specifically checked, not just this one.

### 5. The folder-combine pattern over Hive-partitioned Parquet

Meridian's fact tables are written as `02_data/raw/<TableName>/year=YYYY/month=MM/part-000.parquet` — a **Hive-partitioned** layout, meaning the partition values (`year`, `month`) live in the *folder names*, not as columns inside the Parquet files themselves. This is a deliberate storage convention (used because it lets tools prune whole folders without opening a single file), and it has one direct, unavoidable consequence for you: **the year and month have to be recovered from the folder path text, because Parquet's own schema-on-read will not surface them as columns.**

The pattern, step by step:
1. Connect to the folder `DataRootPath & "FactContainerMove"` (Folder connector, not a single-file connector).
2. **Filter the file-listing table on `[Folder Path]` before combining** — during development, restrict to one or two `year=/month=` partitions so your iteration cycle stays fast; widen the filter once your logic is proven.
3. Extract `Year` and `Month` by parsing the partition segments out of `[Folder Path]` (a straightforward text split on `year=` and `month=`) — do this *before* the combine step invokes the per-file transform function, so every row correctly carries the partition it actually came from, not a value inferred after the fact from something inside the file.
4. Combine, using the generated sample-file function, into one in-memory table.
5. From this point on, folding is irrelevant (there is no fold-back-to-source once files are combined) — every subsequent step runs locally, so keep post-combine logic lean.

### 6. Landmine #9 — proving Parquet handles a reordered schema and CSV would not

`FactContainerMove/year=2023/month=07` has its columns written in a different order from every other partition. This is not a mistake to fix before you load it — it's a deliberate test of whether you actually understand how each file format resolves columns. **Parquet is self-describing: every file carries its own schema, and columns are matched to your table by name, not by position.** Combine that reordered partition alongside every other one, and every value still lands in the correct column, because Power Query (via the Parquet connector) reads each file's embedded column names and aligns them regardless of physical order. **CSV has no such protection**: a CSV file has no embedded schema at all, only a header row (if you're lucky) and then raw positional values — if you combined CSV partitions this way and one file's columns were reordered, every downstream value would silently shift into the wrong column, with no error raised, because CSV combination is purely positional unless you go out of your way to re-map by header name yourself. This is the single cleanest, most concrete argument for why the contract mandates Parquet for facts and reserves CSV only for dimension mirrors (§0, "File layout") — it isn't a style preference, it's a structural guarantee that one format gives you for free and the other does not.

### 7. Landmine #5 — the credit notes, and telling a real error from a legitimate value

0.3% of `FactFreightCharge` rows have a **negative** `Amount_usd` with `IsCreditNote = 1`. These are legitimate: a credit note is a real, negative-value correction to a previous charge, and it must survive every cleaning step you write, all the way into the model. The landmine isn't the negative number — it's the instinct, drilled into people who've mostly worked with "clean" data, that a negative value in a money column *must* be an error. Write a step like `Table.SelectRows(Source, each [Amount_usd] >= 0)` "just to be safe," and you have silently deleted every credit note in the dataset — a monetary correction, gone, with no error, no warning, and a `SUM(Amount_usd)` that is now systematically too high by exactly the amount those credit notes were correcting.

The correct discipline is to separate **type-conversion failures** (genuine errors — a cell that couldn't become a number at all, which Power Query surfaces as an `[Error]` value in that cell) from **valid negative numbers** (not errors — numbers that converted perfectly correctly and simply happen to be negative). The `try … otherwise` pattern lets you catch the first without touching the second:

```
= Table.AddColumn(Source, "AmountUsdSafe", each try [Amount_usd] otherwise null)
```

A row where `Amount_usd` was genuinely unparseable produces `null` here (or, if you want to inspect rather than blindly null it out, `try [Amount_usd]` returns a record with `[HasError]` and `[Error]` fields you can filter and review before deciding what to do). A row where `Amount_usd` parsed fine as `-284.50` is untouched — `try` only intervenes when the underlying expression actually errors, and a correctly-typed negative number is not an error by any definition Power Query uses. **Never filter on a value's sign as a proxy for whether it's an error** — filter on whether the conversion itself failed, and treat those two questions as completely separate, because in this dataset they are.

### 8. Data type discipline and locale — landmine #7, the silent one (and an honest gap)

**A gap worth naming before the lesson:** `00_docs/LANDMINES.md` lists landmine #7 (a `dd/MM/yyyy`-format text date on `FactTarget.TargetMonthDateKey`) among the fact-side landmines, but its own "Fact-side landmines" section is marked *"(placeholder — to be completed by the agent building the fact layer)"* — it was never actually implemented. There is no `FactTarget` CSV mirror in this dataset at all (`02_data/reference/` holds only the 19 `Dim*.csv` files; fact tables ship as Parquet only, already correctly typed, from `write_dim`/`factio.py`). So you cannot walk into this one live, the way you can the nine landmines that were built. The mechanism itself is still real and still the single most dangerous class of Power Query bug, so this section teaches it with a synthetic example you build yourself, in **Enter Data**, rather than a file that doesn't exist in this repo.

Build a two-row table via Home → Enter Data: a column `TargetMonthDateKey` (text) with values `25/03/2025` and `03/07/2025`. This is what a `dd/MM/yyyy`-format text date column looks like: apply Power Query's default "Change Type → Date" to it on a machine whose regional settings assume `M/d/yyyy` (US-style), and for any day-of-month **12 or below**, the conversion succeeds — silently, with no error — and swaps day and month. `25/03/2025` fails loudly (there's no 25th month, so you get an `[Error]` you'd actually notice). `03/07/2025` succeeds *silently* as "March 7th" when the source data meant "3rd of July" — no error, no warning, a wrong date sitting in your model looking completely plausible, and every measure that filters or groups by that date would be quietly wrong for however many rows fall into the ambiguous zone, on any dataset where this pattern is real.

The fix is to be explicit about the locale used for the conversion, every time, rather than relying on whatever the refreshing machine happens to have set:

```
= Table.TransformColumnTypes(Source, {{"TargetMonthDateKey", type date}}, "en-GB")
```

`"en-GB"` reads day-before-month, matching a `dd/MM/yyyy` source's actual format, regardless of what locale the machine doing the refresh is set to — which matters enormously the moment a real file like this gets refreshed on a colleague's machine, a service account, or a cloud gateway with a different regional default than yours. **The only way to catch this landmine with confidence is to test it against a row where day and month are unambiguous** (day > 12, e.g. `25/03/2025`) *and* a row where they're ambiguous (day ≤ 12, e.g. `03/07/2025`) — if you only ever eyeball the unambiguous rows, the silent swap on the ambiguous ones will pass every casual check you do and fail the moment someone downstream asks why Q3 targets look like they belong to March.

### 9. The other landmines you'll meet this week, in passing

Landmines #5, #7 and #9 get the full treatment today because they're specifically Power-Query mechanics. Seven more are seeded into this dataset and you will run into some of them while building this week's queries even though they're not today's main event — know the correct handling now so you recognise them on sight rather than mistaking them for a modelling problem to solve on some later day:

| # | Landmine | Correct handling, briefly |
|---|---|---|
| 1 | 4.1% nulls in optional fields (`VolumeCbm`, `RequiredTempC`, `ShelfLifeDays`, `RevisedEtaDateKey`) | Leave them null. A null here is a true "not applicable/not yet known," not a gap to zero-fill — zero-filling `RequiredTempC` would claim every ambient shipment is refrigerated at 0°C. |
| 2 | 312 duplicated `BookingNo` values with differing detail in `FactBooking` | Dedupe deliberately on the latest `BookingDateKey`, and write down the rule you used — an undocumented dedupe is a landmine you've just re-buried for whoever inherits this query next. |
| 3 | Mixed casing and trailing whitespace in `DimLocation.LocationName` (8% of rows) | `Text.Trim` then `Text.Proper` — but apply it once, in the staging layer, not repeatedly wherever the column happens to get used. |
| 4 | Two spellings of the same country in `DimLocation.CountryName` ("Viet Nam"/"Vietnam", "Korea, Republic of"/"South Korea") | Conform through an explicit mapping table, not a one-off find-and-replace — a mapping table is auditable and extends cleanly if a third spelling ever shows up; a find-and-replace step silently stops working the moment it does. |
| 6 | 47 late-arriving `FactShipment.CustomerKey` references to customers whose `OnboardedDate` postdates the shipment | Route to the `-1` Unknown member and **report the count** — this is a data-quality fact worth surfacing, not quietly hiding. |
| 8 | Three implausible outliers in `DimVessel.NominalTeuCapacity` | Flag them (a calculated "plausibility" column, or a documented note), do not silently drop them — an analyst who deletes outliers without recording that they did so has made the dataset smaller for reasons nobody downstream can audit. |
| 10 | Leading-zero business keys in `DimSku.SkuCode`'s mirror CSV | Import explicitly as text. The model's own `SkuCode` carries a `SKU-`-prefixed alphanumeric string (safe under auto-detection, since a value containing letters is never read as a number), but the mirror CSV strips that prefix for every real row, leaving a bare zero-padded numeric string like `000001` — exactly the shape Power Query's automatic type detection will silently convert to a number, dropping the leading zeros. Watch for this pattern generally: it's the mirror-CSV column that's actually at risk here, not the model column of the same name. |

One closing point worth carrying into every future refresh you ever build, on this dataset or any other: **a query that runs without error is not the same claim as a query that is correct.** Every landmine above — the reordered partition, the credit notes, the locale date — produces a query that refreshes cleanly, shows no red warning triangles, and looks entirely reasonable in a preview pane. The only way any of them get caught is by someone who already knew to check for them, checking deliberately, against specific rows chosen because they'd expose the problem if it existed. That's the actual skill this day is teaching underneath the M syntax: designing your own checks before you trust a refresh, not after a stakeholder notices a number looks wrong three weeks later.

## Drill

**1. Staging/load separation (10 min).** Build a staging query for `DimDate` (Enable Load off) that does only type correctness against the raw file, and a load query referencing it (Enable Load on) that applies the contract's exact column names and marks it ready for the model. Done = two queries exist, only the load query is set to load, and the staging query's steps contain no reshaping logic, only type/name correctness.

**2. Parameterise the path and build the FactContainerMove folder-combine (15 min).** Create the `DataRootPath` parameter, connect to `FactContainerMove`'s folder, filter the file list to a single `year=`/`month=` partition for speed, recover `Year` and `Month` from `[Folder Path]` before combining, then widen the filter to at least three partitions including `year=2023/month=07`. Done = the combined table has correct `Year`/`Month` columns for every partition and does not error on the reordered one.

**3. Prove landmine #9 (10 min).** Using the table from Drill 2, pick one row known to come from `year=2023/month=07` and verify, column by column against the schema contract's `FactContainerMove` field list, that every value landed in the correct column despite that partition's different physical column order. Write one sentence stating what would have happened if this partition had been written as CSV instead. Done = a specific row checked field-by-field, and the CSV counterfactual stated correctly.

**4. Walk into landmine #5, then fix it (15 min).** First, write the naive cleaning step almost everyone writes on first contact with negative money values: filter `FactFreightCharge` to `Amount_usd >= 0`, "just to remove bad data." Refresh, and record how many rows you just removed and what `IsCreditNote` value they carried. Then remove that step, and instead implement the `try … otherwise` pattern that only catches genuine conversion errors, confirming the credit-note rows survive intact and still sum to a negative total. Done = the row count you destroyed with the naive filter is recorded, and the corrected query preserves every `IsCreditNote = 1` row.

**5. Demonstrate landmine #7's mechanism, then fix it (10 min).** Landmine #7 was never actually built into this dataset (§8 above explains why — it's a documented gap, not a live file), so build the two-row `TargetMonthDateKey` table from §8 yourself via Enter Data, and apply Power Query's default date type conversion (whatever your machine's locale gives you) to record the interpreted date for both rows. Then reload using the explicit `"en-GB"` locale conversion and record the same two dates again. Done = both interpretations recorded for both rows, and a one-sentence statement of which row would have silently given a wrong answer under the default conversion, on a real file shaped like this one.

## Ship

Today's artefact is your first real Power BI file. Create `pbix/meridian-week1.pbix` (or the equivalent `.pq`/Power Query template if you're working outside Desktop) in your own repository, containing:

1. The `DataRootPath` parameter.
2. Staging + load query pairs for `DimDate` and `FactContainerMove`.
3. The corrected (not naive) handling of landmines #5 and #7, wherever they apply in the queries you've built.

Commit with:

```
git add pbix/meridian-week1.pbix
git commit -m "day4: parameterised paths, folder-combine over FactContainerMove, landmines 5+7 handled"
```

## Log

- **What clicked**: which distinction — staging vs load, folding vs file-filtering, error vs valid-negative — finally has a concrete mechanism behind it rather than just a rule you were told to follow?
- **What did not**: which landmine (#5, #7, or #9) took you longest to actually see happen, rather than just read about?
- **What to re-ask tomorrow**: one question about how these queries turn into a model with actual relationships — what you're still unsure will "just work."

## Exit criteria

- [ ] Staging query for `DimDate` exists with Enable Load off; load query references it with Enable Load on.
- [ ] `DataRootPath` parameter created and used by at least the `FactContainerMove` folder-combine query.
- [ ] `FactContainerMove` folder-combine correctly recovers `Year`/`Month` from `[Folder Path]` and includes the `year=2023/month=07` partition without error.
- [ ] Landmine #5 walked into (naive filter's row count recorded) and then correctly fixed with `try … otherwise`.
- [ ] Landmine #7's mechanism demonstrated on the synthetic table (wrong date recorded for the ambiguous row under default locale) and then correctly fixed with an explicit `"en-GB"` conversion — and you can state why this landmine has no live file to walk into in this build.
- [ ] `meridian-week1.pbix` committed to your own repo.
- [ ] You can state, without looking, why "View Native Query" is expected to be unavailable for every query in this dataset.
- [ ] Log entry written.
