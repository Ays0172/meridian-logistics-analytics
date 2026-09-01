# Day 23: The Ocean Liner Dashboard

> Time: 3.5 h · Spaced recall 10 min · Concept 45 min · Drill 100 min · Ship 30 min · Log 15 min

Page 1 of 5. The shell exists; today it gets real content built from the 22
measures Week 3 Day 16 shipped against `00_docs/KPI_DICTIONARY.md` §1. This is also
the page carrying the single best "does the average hide the real problem" story
in the whole dataset, so today doubles as the day you learn to design a callout
that survives someone skimming past it in six seconds.

---

## Spaced recall (10 min, closed book)

1. What does `KEEPFILTERS` change about a `CALCULATE` boolean filter argument, and
   when do you need it (Day 9)?
2. State the pooled formula for `Revenue per FFE` from memory, and explain in one
   sentence why the naive `AVERAGEX` version over-weights small bookings.
3. Which page's filters (from Day 22) are safe to sync onto this page, and which
   are not?
4. Name the four candidate KPIs you would put in a fixed-height header card row on
   any page, per Day 22's grid discussion, and why fixed height matters there
   specifically.
5. What is the headhaul vs. backhaul revenue-per-FFE ratio, and what structural
   fact (not a sales failure) explains it (Day 1 §5)?

---

## Concept

### This page's one job

From Day 22: *where is network reliability or capacity utilisation slipping enough
to need a commercial or operational response this month.* Everything on this page
either answers that directly or supports the reader in deciding where to look next.
Nothing on it is here because it's "an Ocean KPI" - 22 KPIs exist in the
dictionary; this page uses roughly a third of them as visuals, because a page that
tries to surface all 22 stops being a decision page and becomes the reference sheet
Day 22 warned against. The rest stay one click away, in a drillthrough or a
tooltip, for the reader who wants depth.

### The visuals, and what each one is actually for

| # | Visual | Measure(s) | Chart type | Decision it supports |
|---|---|---|---|---|
| 1 | Header KPI cards | `Schedule Reliability Rolling 8wk`, `Headhaul Load Factor`, `Backhaul Load Factor`, `Revenue per FFE` | Cards, conditional icon | The five-second read: is the network healthy right now, at a glance, before anyone reads a chart. |
| 2 | Reliability trend | `Schedule Reliability Rolling 8wk` by week | Line, with a shaded region for 14 Jul-14 Sep 2025 | Is the current dip a blip or a trend, and does it line up with a known event. |
| 3 | Reliability vs. call volume | `Schedule Reliability Rolling 8wk` (y), port call count (x), TEU (size), by port | Scatter | Surfaces which ports are actually dragging the network, without the Day 1 sorting trap (see below). |
| 4 | Revenue per FFE, headhaul vs. backhaul | `Revenue per FFE` by `DimVoyage[Direction]` and `TradeLane` | Clustered bar | Is the structural imbalance from Day 1 §5 showing up as expected, or has a lane moved out of its normal band. |
| 5 | The congestion callout | `Demurrage Revenue`, `Detention Revenue`, `Avg Waiting for Berth Hours`, `Avg Container Dwell Hours` | Combo chart + annotation card | The page's single most important message: rising D&D revenue during the window is a symptom, not a win. |
| 6 | Terminal crane productivity | `Moves per Crane-Hour Net`, `Moves per Crane-Hour Gross` | Table, by terminal | Which terminals are the operational bottleneck, net vs. gross split so a "productive-looking" terminal with a bad gross number doesn't hide. |
| 7 | Rollover ratio trend | `Rollover Ratio` | Line, with reference line at contract baseline ~9% | Early warning: rollovers spike before schedule reliability visibly craters. |

Seven visuals, not twenty-two measures. `OCN.TRN.P50`/`P90` (transit time
percentiles), `OCN.MIX.LADEN`, `OCN.REV.BAF`, `OCN.OPS.FREETIME` and the rest stay
available via drillthrough to a "Ocean Detail" tooltip or a future Week 5
performance pass adds them to a secondary page if a specific stakeholder asks -
they did not clear the "does this move the page's one decision" bar today, and
resisting the urge to add them is itself the design decision worth remembering.

### Why the scatter, not a sorted bar, for visual #3

Day 1 named the trap directly: sorting ports ascending by reliability does **not**
surface the congestion crisis, because sparse ports with a handful of calls rank
below Rotterdam and Los Angeles on a pure reliability sort, and a reader's eye goes
to the top of the list. A scatter with call volume on the x-axis forces the
low-volume noise to the left, where it visually separates from the
high-volume-low-reliability outliers on the right - Rotterdam and LA should appear
as two clearly isolated points, low on the y-axis and far right on the x-axis,
distinguishable from a low-call-count port that happens to have a bad week by
chance. This is the same "denominator matters" lesson from Day 9's averaging trap,
now expressed as a chart-design choice instead of a DAX choice: a metric's
reliability as a signal depends on the size of the population behind it, and the
chart should show that population size, not hide it.

### The congestion callout, designed to survive a skim

The numbers, so you have them in one place before building anything: network
schedule reliability sits at **0.6598** overall. During 14 Jul-14 Sep 2025 at
Rotterdam and Los Angeles, that figure falls to **0.405** while unaffected ports
hold **0.670** - and because those 131 affected calls are only 3.2% of the total
population, the *network* headline barely moves (0.662 vs. 0.670 unaffected). In
the same window: demurrage charge-line volume roughly **triples (×3.1)**,
waiting-for-berth hours run **×3.4** baseline, dwell hours run **×2.6**, vessel
turnaround runs **×1.9**, net crane productivity falls to **×0.72**, and rollover
ratio roughly doubles from ~9% baseline to ~19%.

Design the callout to make one specific point unmissable: **demurrage revenue
rising is not good news here, it is the symptom of an operation that was already
failing.** Concretely:

- A combo chart with `Demurrage Revenue` as columns and `Avg Waiting for Berth
  Hours` as a line on a secondary axis, both trended weekly through the event
  window and shaded to mark it. The two series should visibly move together - the
  line leads, since waiting-for-berth is the earlier-degrading signal per the KPI
  dictionary's own watch-out for `OCN.OPS.WAIT`.
- A card, styled with the theme's `bad` accent color from Day 22, carrying a single
  sentence: *"Demurrage revenue rose ~3.1x during the Rotterdam/LA congestion
  event while schedule reliability at those ports collapsed to 0.405 - this is
  the operation failing, not commercial success."* Static text is fine here; the
  point is not to over-engineer a dynamic measure for a known, dated historical
  event, it is to make sure nobody reads the demurrage bar chart in isolation and
  congratulates finance on a good quarter.
- A page tooltip (Format > Tooltip, canvas 320x240) attached to the demurrage
  column series, so hovering any bar - not just the ones inside the shaded window -
  surfaces the same one-line context, in case a reader filters the date range and
  the shading disappears from view.

---

## Drill

Write your justification before building; check it against the reference design in
solutions.

### Exercise 23.1: header cards with conditional status (25 min)
Build the four header cards. For `Schedule Reliability Rolling 8wk`, write a status
measure using the Sea-Intelligence directional band from the KPI dictionary
(55-70% typical) and this project's own validation gate (0.62-0.70 outside the
congestion window). Predict which of the two bands you'll actually use for the
conditional-formatting thresholds, and why one is more defensible for *this*
dataset than the industry-wide one, before writing the `SWITCH`.

### Exercise 23.2: the scatter, verified against the Day 1 sorting trap (30 min)
Build visual #3. Before adding any interactivity, sort the underlying table by
reliability ascending and confirm for yourself that Rotterdam and Los Angeles do
**not** appear at the top - this is the exact failure Day 1 described, reproduced
on purpose. Then build the scatter and confirm the two ports separate visually as
predicted. Write one sentence on what a reader who only ever sees sorted tables,
never scatter plots, would miss about this dataset.

### Exercise 23.3: the congestion combo chart (30 min)
Build the demurrage/waiting-for-berth combo chart. Predict, before checking,
whether the waiting-for-berth line visibly leads the demurrage bars by more than a
few days inside the shaded window, or whether they move together with no lag.
Verify against the weekly series and note the actual lag in your predictions log.

### Exercise 23.4: visual justification pass (15 min)
For each of the seven visuals in the table above, write one sentence (not copied
from this file) stating what a reader would wrongly conclude, or fail to notice, if
that specific visual were removed from the page. A visual whose absence you cannot
write a concrete sentence for is a visual that has not earned its place - flag it
honestly, even if you already built it.

---

## Ship

Build page `1 Ocean Liner` in the report, all seven visuals wired, the congestion
callout styled with the theme's `bad` accent and its tooltip attached. Add the
status measure from Exercise 23.1 to `_Measures`, display folder `05 Report
Status`. Update `06_portfolio/notes-report-design.md` with the one sentence per
visual from Exercise 23.4 - that file is now becoming the design rationale
document a portfolio write-up in Week 6 will draw on directly.

```
git add .
git commit -m "Day 23: Ocean Liner dashboard, congestion callout wired"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] Page `1 Ocean Liner` exists with all seven visuals, on-theme, nav bar intact
      from Day 22.
- [ ] You can state, without notes, why the scatter (not a sorted bar) is the
      right chart for reliability-by-port, referencing the Day 1 sorting trap by
      name.
- [ ] The congestion callout exists, is visually distinct (theme `bad` accent),
      and its tooltip works when hovered outside the shaded date window.
- [ ] You wrote a genuine "what would a reader miss" sentence for all seven
      visuals, including any you judged weak.
- [ ] Status measure shipped to `_Measures` with a documented threshold choice.
