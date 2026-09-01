# Day 6 — The Date Dimension as Infrastructure, and SCD Type 2 for Real
> Time: 2.5 h · Concept 35 min · Drill 60 min · Ship 50 min · Log 15 min

## Spaced recall (10 min, closed book)

1. State the difference between what `USERELATIONSHIP` fixes and what importing a dimension multiple times fixes.
2. Draw (in words) the `DimCustomer`/`FactBooking`/`FactShipment` triangle and state what makes it dangerous only once a relationship in it is bidirectional.
3. What exactly does a dashed line in Model view tell you, and what does it not tell you about a relationship's cardinality?
4. Why does `FactShipment`'s in-transit `AtaDateKey` resolving to `DimDate`'s `-1` row matter, mechanically, compared to leaving it null?
5. State the decision rule for choosing `USERELATIONSHIP` versus importing a dimension multiple times.
6. Name the one setting that makes an inner-join-style relationship faster, and the one condition that must be true before you switch it on safely.

## Concept

Two subjects today, and they share a theme you'll meet constantly for the rest of this programme: **a value that changes over time needs infrastructure specifically built to represent "as of when," or your model will quietly average two different truths into one wrong one.** A date dimension has to represent time consistently across fiscal calendars, ISO weeks and "today," or your time-intelligence measures lie. A customer dimension has to represent "who owned this account when the transaction happened" separately from "who owns it now," or your account-manager reporting silently rewrites history every time an account gets reassigned.

### 1. Mark as date table — what it actually buys you, and what fails silently without it

`DimDate` needs to be explicitly marked as a date table (right-click the table → "Mark as date table," pointing at the `Date` column) for one structural reason: Power BI's time-intelligence functions — `SAMEPERIODLASTYEAR`, `TOTALYTD`, `DATESYTD`, `PARALLELPERIOD`, and the rest — need to know, unambiguously, which table and which column represent a genuine, contiguous, one-row-per-calendar-day sequence, so they can correctly walk backward and forward across it. `DimDate` qualifies (2021-01-01 through 2026-12-31, no gaps, one row per day) — but qualifying isn't the same as being *declared*, and the declaration is what the engine actually checks.

**Here is the specific, silent failure mode if you skip it, and it's worse than "time intelligence might not work":** Power BI Desktop ships with **Auto Date/Time** switched on by default. If it's still on and you haven't marked your own `DimDate`, Power BI silently generates a **separate, hidden date table for every date-typed column in your model** — one hidden calendar behind `FactShipment[ShipmentDateKey]`'s date equivalent, another behind `FactBooking[BookingDateKey]`'s, and so on, each with its own auto-generated year/quarter/month hierarchy, entirely independent of your carefully built `DimDate` with its fiscal calendar and ISO weeks. A visual built by dragging a date field directly from a fact table (rather than from `DimDate`) can end up filtering through one of these invisible auto-generated calendars instead of your real one — and because the auto-generated hierarchy uses the standard calendar year, not Meridian's fiscal year starting 1 October, a fiscal-year total built this way will be **quietly wrong**, off by exactly the three-month fiscal offset, with no error and no visual difference in the field list beyond a small calendar icon most people never notice. The fix is two actions, not one: mark `DimDate` as the date table, **and** turn off Auto Date/Time in Options (File → Options and Settings → Options → Data Load), so there's exactly one calendar in the model, not one real one and several accidental ones.

Two more prerequisites Power BI actually checks before it will let you mark a table as the date table, worth knowing precisely rather than discovering by trial and error: the marked column must contain **unique values** (one row per distinct date, never two rows claiming the same date) and **no nulls or blanks**. `DimDate.DateKey` and `Date` satisfy this by construction — 2,191 rows, 2021-01-01 to 2026-12-31, exactly one row per calendar day — but if you ever build a date table by hand for a different project and it has a gap or a duplicate, the mark-as-date-table step will refuse, which is the engine doing you a favour before a time-intelligence function fails quietly instead.

### 2. Fiscal calendar starting 1 October

`DimDate.FiscalYear`, `FiscalQuarter`, `FiscalMonth` and `FiscalYearLabel` (`"FY26"`) exist because Meridian's fiscal year runs 1 October to 30 September, not the calendar year — and every fiscal calculation is a simple, mechanical shift once you see it that way: **fiscal month = ((calendar month − 10) mod 12) + 1**, which maps October to fiscal month 1, and continues through September as fiscal month 12. Fiscal quarter follows directly (fiscal months 1–3 → FQ1, 4–6 → FQ2, and so on). The one genuinely ambiguous design decision — and worth stating out loud rather than assuming — is which calendar year a fiscal year is *named after*: does "FY26" mean the fiscal year that **starts** in October 2025, or the one that **ends** in September 2026? Both conventions exist in real organisations (the ends-in convention, matching the US federal fiscal year, is the more common one internationally). This is exactly the kind of ambiguity you should never guess silently past — confirm which convention a fiscal-year label actually uses against the generated data or the team that owns the calendar, document it in one sentence next to the column, and move on; guessing wrong here means every fiscal-year total in a board deck is a year off from what everyone else in the business means by that label.

A worked check of the formula, so you can verify your own drill answers against it: fiscal month = ((calendar month − 10) mod 12) + 1, using a mod that always returns a non-negative result. October: ((10−10) mod 12)+1 = 0+1 = **1**. January: ((1−10) mod 12)+1 = (−9 mod 12)+1 = 3+1 = **4**. March: ((3−10) mod 12)+1 = (−7 mod 12)+1 = 5+1 = **6**. September: ((9−10) mod 12)+1 = (−1 mod 12)+1 = 11+1 = **12**, correctly closing out the fiscal year immediately before it rolls to October again. Fiscal quarter is then a straightforward `CEILING(FiscalMonth / 3)`.

### 3. ISO weeks — a different year boundary than you'd assume

`ISOWeek` and `ISOYear` follow ISO 8601, and the rule that catches people who haven't hit it before is this: **a week belongs to whichever calendar year contains that week's Thursday** — equivalently, week 1 of an ISO year is the week containing that year's first Thursday. This means the last few days of December and the first few days of January can belong to an ISO year that **doesn't match their calendar year at all**. Concretely: 31 December 2023 was a Sunday — the ISO week containing it also contains the preceding Monday, 25 December, and its Thursday is 28 December 2023, so that week (and 31 December along with it) is **ISO week 52 of ISO year 2023**, matching the calendar year in that particular case. But shift the alignment by even a day or two in a different year and you can get an early-January date landing in the *previous* ISO year's final week, or a late-December date landing in *next* year's ISO week 1 — the exact pattern depends on which weekday 1 January falls on that year, which is precisely why you compute it properly rather than assume `ISOYear = Year`. This is also exactly why `ISOWeekSort` exists as a separate `int32` column: `ISOWeekLabel` text like `"2026-W01"` sorts correctly alphabetically in most cases, but relying on text sort for anything date-like is fragile — `ISOWeekSort` (built as `ISOYear × 100 + ISOWeek` or equivalent) gives you an unambiguous numeric sort key that a slicer or axis can order by without any text-parsing risk.

### 4. Relative offsets, and a baked-in "today"

`YearOffset`, `MonthOffset`, `WeekOffset` and `DayOffset` let you write "current year," "last month," "trailing 4 weeks" as simple filters (`YearOffset = 0`, `MonthOffset = -1`) instead of live date-arithmetic DAX — genuinely useful, and much cheaper at query time than recomputing relative position from `TODAY()` on every render. But notice precisely what they're relative *to*: the generator fixes `IsCurrentYear`/`IsCurrentMonth` and the offset columns against **`CURRENT_ANCHOR_DATE = 2026-08-20`** (`01_generator/meridian/config.py`), a date baked in at generation time — not a live, ever-moving `TODAY()`. This is a deliberate, sensible choice for a static teaching dataset (a snapshot has to freeze "now" somewhere), but it has a real consequence you need to reason about explicitly: **once real time moves past that generation anchor, a live report mixing `DimDate.IsCurrentYear = 1` with a measure that uses `TODAY()` directly will disagree with itself** — the stored column says "current" relative to 20 August 2026 forever, while `TODAY()` keeps moving. The professional habit this teaches, beyond this one dataset: know whether "current" in any model you inherit is a live, recalculated concept or a frozen one, and never assume — a frozen "current" flag inherited from a monthly refresh cycle, still being read as if it were live, is a genuinely common real-world reporting bug.

### 5. SCD Type 2 on `DimCustomer` — the mechanism, precisely

`DimCustomer` holds 3,200 *current* customers but 4,171 *rows*, because roughly 30% of customers have had 1–2 changes tracked over the period across four triggering attributes: `AccountManager`, `CreditTier`, `SizeTier`, `ContractType`. Every change creates a **new row with a new surrogate `CustomerKey`**, while the durable business key `CustomerCode` stays the same across every version. Each version carries `ScdValidFrom`, `ScdValidTo` (`9999-12-31` for whichever version is current), `IsCurrent` (1 for exactly one version per `CustomerCode`, 0 for every earlier one), and `ScdVersion` (1, 2, 3…).

The single most important mechanical fact about this design: **every fact table's `CustomerKey` FK is assigned to whichever `DimCustomer` version was valid at the time the transaction happened** — this is what the contract means when it notes `FactBooking.CustomerKey` is "SCD2-resolved to the version valid at booking date." A shipment posted while a customer's account was managed by Priya Sharma carries the `CustomerKey` for the *Priya Sharma version* of that customer, even after the account gets reassigned to someone else next quarter. This single fact is what makes SCD2 actually work end to end — the history isn't reconstructed after the fact from a changelog, it's baked directly into which specific dimension row each transaction points to at load time.

Mechanically, this is exactly what an "as-of" lookup does at load time, whether that load logic lives in the generator, an ETL pipeline, or a manual join: for a given transaction date, find the `DimCustomer` row for that `CustomerCode` where `ScdValidFrom ≤ TransactionDate < ScdValidTo`. Because exactly one version satisfies that condition for any valid date (versions are contiguous and non-overlapping by construction, with the current version's `ScdValidTo` set to the far-future `9999-12-31` sentinel rather than left open-ended), the lookup is always unambiguous — which is precisely why `9999-12-31` is used instead of a null "no end date": a null would need special-case handling in every comparison, while `9999-12-31` behaves correctly in a plain `<` comparison without any extra logic.

### 6. Two honest questions, two different answers, built side by side

"Revenue by the account manager who owned the account at the time" and "revenue by whoever owns the account now" are **both legitimate business questions**, and they can genuinely disagree — that disagreement is not a bug in either measure, it's the entire point of tracking history. Building both, on the same table visual, makes the divergence visible rather than asserted:

- **"At the time" is the default your model already gives you for free.** Group any revenue measure by `DimCustomer[AccountManager]`, and because `FactShipment.CustomerKey` already points at the historically-correct version, you get "revenue attributed to whichever AM actually owned the account when the shipment happened" with no extra work.
- **"As of now" requires a deliberate lookup across versions**, because the fact's `CustomerKey` does not point at the current version — it points at whichever version was valid *then*. The clean way to build it is a calculated column directly on `DimCustomer` that, for every row (current or historical), finds the `AccountManager` of the *current* row sharing the same `CustomerCode`:

```
CurrentAccountManager =
LOOKUPVALUE(
    DimCustomer[AccountManager],
    DimCustomer[CustomerCode], DimCustomer[CustomerCode],
    DimCustomer[IsCurrent], 1
)
```

Every `DimCustomer` row — including old, non-current versions — now carries two account-manager columns side by side: `AccountManager` (that version's own value, i.e. "at the time") and `CurrentAccountManager` (looked up from whichever row for that `CustomerCode` currently has `IsCurrent = 1`). Because `FactShipment` joins to whichever historical `DimCustomer` row was valid at shipment time, **both columns are available on that exact join, for every fact row, with no second relationship, no bidirectional toggle, and no ambiguity** — group a table visual by `AccountManager` for one view, group the same measure by `CurrentAccountManager` for the other, and the two totals per manager will genuinely differ wherever an account changed hands during the period. This is a considerably cleaner solution than trying to build two separate models or a bidirectional relationship back to a "current-only" customer table, and it's the pattern to reach for by default whenever you need both a historical and a current attribution from the same SCD2 dimension.

**A concrete illustration, with numbers, before you meet it live in Drill 4.** Suppose customer `CUS0842` has two versions: version 1 (`ScdVersion = 1`, `IsCurrent = 0`) valid from the start of the dataset until a credit-tier change on 2025-04-01, and version 2 (`IsCurrent = 1`) valid from 2025-04-01 onward. Every shipment that customer made before April 2025 carries the `CustomerKey` for version 1. Filter `DimCustomer` to `IsCurrent = 1` and every one of those pre-April shipments — real revenue, already invoiced, already in the general ledger — vanishes from any total on that filtered page, because version 1's `CustomerKey` no longer has a matching dimension row under the filter. Multiply this by the roughly 30% of the customer base that has gone through at least one change, and a page-level `IsCurrent = 1` filter isn't a rare edge case shaving a rounding error off a total — it's a structural, silent understatement of historical revenue, sized by exactly how much business those customers did before their most recent change.

### 7. The `IsCurrent` trap, stated precisely so you can avoid it once you've seen it

`IsCurrent = 1` correctly answers "how many customers do we have right now" (filter `DimCustomer` to `IsCurrent = 1`, then count — giving you 3,200, not 4,171). But **`IsCurrent = 1` is not a safe blanket filter to leave on a report page whenever `DimCustomer` is involved**, and here is the exact mechanism of the mistake: if you filter `DimCustomer` to `IsCurrent = 1` and then look at total revenue, the single-direction relationship correctly restricts `FactShipment` to only the rows whose `CustomerKey` matches a dimension row that survived the filter. **Every fact row whose `CustomerKey` points at a non-current, historical version of a customer who has since had an SCD2 change gets silently excluded** — not because that revenue didn't happen, but because the specific dimension row it's joined to no longer appears in the filtered dimension. With roughly 30% of customers having gone through at least one change, this isn't a rare edge case; it's a real, measurable understatement of total revenue the moment `IsCurrent = 1` is applied anywhere upstream of a total that's supposed to reflect *all* transactions regardless of which version they happened to post against. The correct discipline: use `IsCurrent = 1` only for questions specifically about the *current state of the customer master* (a live customer list, a current segmentation count) — never as a general-purpose "clean up the dimension" filter sitting on a page that also needs to report historical transaction totals.

Both halves of today share one underlying discipline worth naming directly: **a dimension that represents something changing over time — a calendar's relationship to "now," a customer's relationship to whoever manages their account — needs an explicit mechanism for "as of when," or the model will quietly collapse multiple truths into one.** `DimDate` without a marked date table and without a stated fiscal convention silently answers "which year" using whichever calendar happens to be active behind the scenes. `DimCustomer` without SCD2 silently answers "who manages this account" using only whoever manages it today, erasing the fact that someone else legitimately earned that revenue under their own management at the time. Both failures share the same shape: not a crash, not a visible error, just a report that's confidently, plausibly, and silently answering a slightly different question than the one it was asked.

## Drill

**1. Fiscal year and ISO week, by hand (15 min).** For each of these three dates, state the `FiscalYear`/`FiscalQuarter` (using the "names the year it ends" convention) and the `ISOYear`/`ISOWeek`: (a) 15 November 2025, (b) 3 October 2026, (c) 31 December 2023 (a Sunday). Done = six values stated with the mechanism shown, not just the answer, for at least the ISO week calculation on (c).

**2. Diagnose the Auto Date/Time trap (10 min).** With Auto Date/Time left on and `DimDate` not yet marked as a date table, build a card visual using `TOTALYTD` against a date field dragged directly from a fact table rather than from `DimDate`. Record what you observe about which calendar it's actually using (calendar-year boundaries vs fiscal). Then mark `DimDate` properly, disable Auto Date/Time, rebuild the relationship-based version, and compare. Done = the discrepancy recorded with a specific number or date boundary that changed.

**3. Build both account-manager measures (20 min).** Implement the `CurrentAccountManager` calculated column from §6, build two measures (`Revenue by AM at Time` grouped by `AccountManager`, `Revenue by Current AM` grouped by `CurrentAccountManager`), and find at least one real account manager pairing in your data where the two totals genuinely differ. Done = a specific AM name (or two) shown with two different totals, and one sentence on why they differ.

**4. Walk into the `IsCurrent` trap, then fix it (10 min).** Build a total revenue card with no filter, note the number. Add a page-level filter `DimCustomer[IsCurrent] = 1`. Note the new (lower) number. Explain, in one sentence naming the actual mechanism (not just "it went down"), why it dropped. Remove the filter and confirm the total returns. Done = both numbers recorded and the mechanism correctly named.

**5. The frozen "today" question (5 min).** In two sentences: why will a live measure using `TODAY()` eventually disagree with `DimDate.IsCurrentYear`, and what's the one-line fix if you need them to agree indefinitely?

## Ship

Update your model file with:
1. `DimDate` marked as a date table, Auto Date/Time disabled.
2. The `CurrentAccountManager` calculated column and both account-manager measures from Drill 3, with the divergent example visible in a table visual.
3. A note in `notes/week1/day6-dates-scd2.md` recording: your fiscal-year naming decision from §2 (which convention you're using and why), the Drill 2 discrepancy you observed, and the specific AM divergence from Drill 3.

Commit with:

```
git add notes/week1/day6-dates-scd2.md
git commit -m "day6: date table marked, fiscal/ISO verified by hand, SCD2 dual AM attribution built"
```

## Log

- **What clicked**: which mechanism — Auto Date/Time's hidden calendars, the ISO Thursday rule, or the SCD2 dual-attribution pattern — finally has a concrete "I saw the number change" behind it?
- **What did not**: are you still unsure exactly when `IsCurrent = 1` is safe to apply versus when it silently drops revenue?
- **What to re-ask tomorrow**: one question to carry into tomorrow's checkpoint about anything from the whole week you'd want to see phrased as an exam question before you're actually asked it.

## Exit criteria

- [ ] `DimDate` marked as a date table; Auto Date/Time disabled; the Drill 2 discrepancy observed and explained.
- [ ] Fiscal year and ISO week computed by hand for all three Drill 1 dates, with the ISO Thursday-rule mechanism shown for (c).
- [ ] `CurrentAccountManager` column built and both account-manager measures constructed, with at least one real divergent example found.
- [ ] The `IsCurrent` trap walked into, the revenue drop recorded, and the mechanism correctly named (not just observed).
- [ ] The frozen-"today" question answered with a stated fix.
- [ ] `day6-dates-scd2.md` committed with your fiscal-year convention decision documented.
- [ ] Log entry written.
