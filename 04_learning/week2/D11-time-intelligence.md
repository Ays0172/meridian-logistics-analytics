# Day 11 — Time intelligence, rolling windows, and what an average hides

> Time: 3 h · Spaced recall 10 min · Concept 45 min · Drill 70 min · Ship 40 min · Log 15 min

Time intelligence is the part of DAX with the most built-in functions and the most
ways to be quietly wrong. Today covers the functions, the rolling-window pattern
the shipping industry actually uses, and one demonstration that matters more than
any of the syntax: how completely a network-level metric can hide a local disaster.

---

## Spaced recall (10 min, closed book)

1. What quantity predicts how badly an unweighted average of a ratio will err?
2. Why did revenue per FFE come out 8.6% too high when computed the obvious way?
3. Where is a `VAR` evaluated — where it is written, or where it is used?
4. What are the three diagnostic symptoms, and what does each one mean?
5. `DIVIDE` returns blank on a zero denominator. What does `AVERAGEX` do with those
   blanks, and why does that matter for revenue per FFE?

---

## Concept

### Mark as date table, or nothing below works

Before any time-intelligence function will behave, `DimDate` must be marked as a
date table on its `Date` column. Without it, `DATESYTD` and friends fall back on
auto date/time tables that Power BI generates per date column — invisible, bloated,
and inconsistent with your fiscal calendar.

Two requirements: the date column must be contiguous with no gaps, and it must
cover full years. `DimDate` runs 2021-01-01 to 2026-12-31 for exactly this reason,
even though the facts only start in August 2021 — a date table that stops mid-year
makes `DATESYTD` wrong in the final year.

### The standard comparison set

```dax
Revenue := SUM ( FactShipment[Revenue_usd] )

Revenue LY :=
CALCULATE ( [Revenue], SAMEPERIODLASTYEAR ( DimDate[Date] ) )

Revenue YoY % :=
VAR Cur = [Revenue]
VAR Prior = [Revenue LY]
RETURN
    DIVIDE ( Cur - Prior, Prior )

Revenue YTD :=
CALCULATE ( [Revenue], DATESYTD ( DimDate[Date] ) )

Revenue Fiscal YTD :=
CALCULATE ( [Revenue], DATESYTD ( DimDate[Date], "09-30" ) )
```

Note the fiscal variant: Meridian's year starts 1 October, so the year-end marker
is `"09-30"`. Getting this wrong is the single most common time-intelligence bug in
a company with a non-calendar year, and it is invisible until someone reconciles
against the finance system.

`SAMEPERIODLASTYEAR` shifts the whole current selection back one year.
`DATEADD(DimDate[Date], -1, YEAR)` does the same thing and is more flexible when you
need other offsets. `PARALLELPERIOD` shifts and expands to the full period, which is
occasionally what you want and usually not.

### Rolling windows, and why the industry uses them

A single week of schedule reliability is noise. The whole industry — Sea-Intelligence,
Xeneta, carriers' own reporting — quotes reliability on a **trailing 8-week window**,
because a vessel's schedule is a weekly cycle and eight of them is enough to see
through the noise without smoothing away the signal.

```dax
Schedule Reliability Rolling 8wk :=
VAR LastDate = MAX ( DimDate[Date] )
VAR WindowStart = LastDate - 55            -- 56 days inclusive
VAR Calls =
    CALCULATETABLE (
        FactPortCall,
        DATESBETWEEN ( DimDate[Date], WindowStart, LastDate )
    )
RETURN
    DIVIDE (
        COUNTROWS ( FILTER ( Calls, FactPortCall[IsOnTimeArrival] = 1 ) ),
        COUNTROWS ( Calls )
    )
```

Two things to notice. `DATESBETWEEN` takes explicit endpoints, which is what you
want for a fixed-length trailing window — `DATESINPERIOD` is the alternative and
takes an anchor plus a count. And the ratio is **recomputed over the pooled window**,
not averaged from weekly rates: yesterday's lesson, applied.

### The demonstration: what a network average hides

Meridian's data contains a nine-week port congestion crisis at Rotterdam and Los
Angeles in July–September 2025. At its height, measured on the industry-standard
rolling 8-week window:

| Population | Rolling 8-week reliability | Port calls in window |
|---|---|---|
| Network-wide | **0.662** | 4,049 |
| The two crisis ports | **0.405** | 131 |
| Every other port | **0.670** | 3,918 |

The crisis ports are performing **40% worse** than the rest of the network. And the
network-wide number — the one that would be on the executive dashboard — sits
**1.3% below** the unaffected ports. Essentially unmoved.

This is not a flaw in the data or in the metric. It is arithmetic: 131 calls out of
4,049 is 3.2% of the population, so even a severe local failure moves the pooled
average by almost nothing — and note that 3.2% x 40% = 1.3%, which is exactly the
shift observed. Berth waiting time tells the same story — 23.6 hours at the crisis
ports against 7.6 hours everywhere else, and a network average that barely
registers it.

**The lesson is about dashboard design, not about DAX.** A single headline KPI, no
matter how correctly computed, cannot detect a localised failure. What detects it
is one of:

- the same measure **broken out by port**, with the call count beside it
- **ranking by impact** — calls × shortfall against baseline — rather than by rate
- a **variance** or spread measure alongside the average
- an **exception list** with a volume floor, so sparse members cannot dominate it

Exercise 11.4 makes you discover why that second point is not the same as "sort
ascending by reliability". Breaking out by port is necessary; breaking out *and
ranking by rate* surfaces whichever port has the fewest observations. That is the
failure mode that gets exception reports switched off.

This is why the Week 5 Executive Cockpit is built around a volume-weighted exception
queue rather than a wall of averages, and it is a good answer to "what would you put
on a one-page executive dashboard?" — because it explains *why*, not just *what*.

### The event-in-progress pattern

The signature logistics DAX problem: how many containers were in transit on a given
date? A container is in transit if it has been loaded but not yet discharged. There
is no row that says "in transit on 14 March" — the state has to be inferred from
two events straddling the date.

```dax
Containers In Transit :=
VAR AsOf = MAX ( DimDate[DateKey] )
RETURN
    CALCULATE (
        DISTINCTCOUNT ( FactContainerMove[ContainerNo] ),
        FILTER (
            ALL ( FactShipmentMilestone ),
            FactShipmentMilestone[VesselLoadDateKey] <= AsOf
                && ( FactShipmentMilestone[VesselDischargeDateKey] > AsOf
                     || FactShipmentMilestone[VesselDischargeDateKey] = -1 )
        )
    )
```

`AsOf` is pulled from `DimDate[DateKey]`, not `DimDate[Date]` — both `VesselLoadDateKey`
and `VesselDischargeDateKey` are `int32 yyyymmdd` integers (per the schema contract),
not dates, so comparing them against a `Date` value (or a `FORMAT(...)`-produced text
string) either compares the wrong types or fails outright; `DateKey` already carries
the matching `yyyymmdd` integer, no conversion needed.

The `= -1` branch is the part people forget: a container that has loaded and has no
discharge date yet is still at sea. Omit it and every genuinely in-flight box
disappears from the count — the measure will look fine on historical dates and
under-report the present, which is the worst possible failure mode for an
operational dashboard.

**Semi-additive reminder.** This pattern produces a number that is valid at a point
in time and meaningless summed across dates. The same is true of
`FactInventorySnapshot`. Any measure of a *state* rather than an *event* needs
`LASTNONBLANKVALUE` or an explicit as-of date, never a `SUM` over a range.

---

## Drill

Predictions first.

### Exercise 11.1 — build the comparison set (15 min)
Build `Revenue LY`, `Revenue YoY %`, `Revenue YTD` and `Revenue Fiscal YTD`. Put
`DimDate[Year]` on rows.

Predict: **which year shows a blank `Revenue LY`, and why?** Then predict whether
`Revenue YTD` and `Revenue Fiscal YTD` agree for calendar 2024, and explain.

### Exercise 11.2 — the fiscal year offset (15 min)
With `DimDate[FiscalYearLabel]` on rows, compare `Revenue YTD` against
`Revenue Fiscal YTD`. Work out from the data which convention `DimDate` uses:
does FY26 mean the year *starting* 1 Oct 2026 or *ending* 30 Sep 2026?

Then answer this: if a finance colleague asks for "FY25 revenue" and you hand them
a calendar-2025 number, how far out are you? Compute it.

### Exercise 11.3 — the rolling 8-week window (20 min)
Build `Schedule Reliability Rolling 8wk`. Put `DimDate[Date]` on rows filtered to
August 2025 and read the value at 31 August.

Then build the naive version and compare:
```dax
[DO NOT USE] Reliability Naive Weekly Avg :=
AVERAGEX ( VALUES ( DimDate[ISOWeekLabel] ), CALCULATE ( AVERAGE ( FactPortCall[IsOnTimeArrival] ) ) )
```
Predict the gap before you look. This is a case where the naive answer is close —
work out why, and say what would have to change about the data for it to be far off.

### Exercise 11.4 — find the crisis the headline is hiding (25 min)
This is the exercise that matters today.

With your rolling 8-week measure set to 31 August 2025:
1. Read the network-wide number. Write it down.
2. Now put `DimLocation[LocationCode]` on rows, sorted ascending by the measure.
   **Predict first: will NLRTM and USLAX be at the bottom?** Then look. Add the
   port-call count as a second column before you interpret anything.
3. Compute the measure for NLRTM + USLAX together, and for everything except them.
4. Quantify: how much worse are the crisis ports, and how much does the network
   number move because of them?
5. Now fix the visual from step 2 so that it *does* put the crisis ports at the top.
   There is more than one defensible way; pick one and say why.

Then answer, in writing, in `06_portfolio/notes-averages-hide.md`:
- Why does a 40% local failure barely move the headline?
- Why does sorting ascending by reliability *not* surface the crisis, and what
  ranking does?
- If you had to keep only one number on an executive page, what would you put next
  to it so the crisis could not hide?

That written answer is an interview answer. Keep it.

### Exercise 11.5 — Lunar New Year and the comparability trap (20 min)
Lunar New Year moves between January and February each year, and Asian export
volume collapses around it. Put `DimDate[MonthYear]` on rows with FFE volume, for
January and February of 2023 to 2026.

Predict, then check:
- Is the February trough visible in every year?
- Is the **February year-on-year comparison** badly distorted by the date moving?

Be careful here — the honest answer may not be the dramatic one. Compute it and
report what you actually find, including if the effect is milder than you expected.
Then work out at which grain (monthly, ISO-week, quarterly) the moving date would do
the most damage to a comparison, and why.

### Exercise 11.6 — containers in transit (20 min)
Build `Containers In Transit`. Read it at 1 April 2026.

Then break it: remove the `= -1` branch and read it again at 1 April 2026, and at
a date near the end of the data. Predict which of the two readings changes more
before you run it, and explain the asymmetry.

---

## Ship

Add to `_Measures` in display folder `04 Time`: `Revenue LY`, `Revenue YoY %`,
`Revenue YTD`, `Revenue Fiscal YTD`, `Schedule Reliability Rolling 8wk`,
`Containers In Transit`.

Write `06_portfolio/notes-averages-hide.md` with your Exercise 11.4 answer.

```
git add .
git commit -m "Day 11: time intelligence, rolling windows, event-in-progress, masking demo"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] `DimDate` is marked as a date table and you can say what breaks without it.
- [ ] You know which fiscal-year convention this model uses, and you verified it
      from the data rather than assuming.
- [ ] Your rolling 8-week measure matches the reference value at 31 August 2025.
- [ ] You can explain, with the actual numbers, why a 40% local failure moves the
      network average by under 1.5% — and name the visual that would have caught it.
- [ ] `Containers In Transit` handles the not-yet-discharged case, and you have
      proved what breaks when it does not.
- [ ] `notes-averages-hide.md` written. Predictions recorded, misses annotated.
