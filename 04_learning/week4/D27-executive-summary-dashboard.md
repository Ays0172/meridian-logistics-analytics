# Day 27: The Executive Summary Dashboard

> Time: 3.5 h · Spaced recall 10 min · Concept 45 min · Drill 100 min · Ship 30 min · Log 15 min

Page 0, built last on purpose: you cannot design what a CFO needs to see until
you've built the four pages it summarises and know what's actually worth pulling
up. This page has the highest bar of the whole report - every visual on it has to
justify itself against "would a CFO, seeing this for eight seconds before a
meeting, know where to intervene" - and it is the page where the cross-cutting KPIs
from `KPI_DICTIONARY.md` §5 finally get used.

---

## Spaced recall (10 min, closed book)

1. Name the seven cross-cutting KPIs and state which of `XCT.FIN.C2C`'s three
   components (DIO, DSO, DPO) cannot be computed at all against this schema, and
   why.
2. What is `XCT.QLT.PERFECT` (company-wide) measuring that `WHS.QLT.PERFECT`
   (warehouse-touched) is not, and why can the two legitimately disagree?
3. Why does `Top-10 Customer Share` need to be re-ranked inside whatever filter
   context the report is in, rather than computed once at the company level?
4. Name the SCOR Level-1 attribute a given KPI you built this week (any domain)
   maps to, and one KPI from a different domain that maps to the same attribute.
5. State, from memory, the network-wide schedule reliability figure and why it
   barely moved during the Rotterdam/LA congestion event even though two ports
   collapsed to 0.405.

---

## Concept

### This page's one job

*Where does the CFO or COO need to personally intervene this week.* Not "here is
everything," not "here is one number per domain" - a specific, ranked answer to
"where." That bar rules out most of what would be tempting to put here: a wall of
KPI cards from every domain reads as comprehensive and answers nothing.

### The visuals, and what each is for

| # | Visual | Measure(s) | Chart type | Decision it supports |
|---|---|---|---|---|
| 1 | Header cards | `Perfect Order Rate (Company-wide)`, `Freight Cost % of Revenue`, `Top-10 Customer Share`, `Cash-to-Cash Cycle Time (partial)` | Cards, the latter explicitly labelled "partial (DIO+DSO only)" | The CFO's five-second read. |
| 2 | Revenue & margin trend with dispersion band | `Revenue`, mean `GrossMarginPct`, `Gross Margin % P10-P90 Spread` | Dual-axis line + shaded band | Is average margin health hiding a widening loss-making tail - the exec-level instance of "never chart a mean alone." |
| 3 | SCOR Level-1 scorecard | `Target Attainment % by SCOR Attribute` (Reliability, Responsiveness, Agility, Cost, Asset Management) | Small matrix/heatmap, one row per attribute | Organises the whole KPI library the way an exec audience actually expects to see it - by outcome, not by data domain. |
| 4 | Top-10 customer concentration | `Top-10 Customer Share` | Donut or single stacked bar, always re-ranked live | Concentration risk, one number, no ambiguity about what "top 10" means right now. |
| 5 | Domain synthesis strip | one wrapper measure per domain page: `Exec Headline Ocean`, `Exec Headline Landside`, `Exec Headline Warehouse`, `Exec Headline Air` | Four small cards, each a drillthrough/navigation target | The bridge into the four domain pages - see below. |
| 6 | Cost to Serve, top and bottom customers | `Cost to Serve per Customer`, paired with revenue per customer | Scatter or paired bar, top 10 and bottom 10 by cost | Never let "expensive to serve" stand alone without revenue context, per the KPI dictionary's own watch-out. |

Six visuals for seven KPIs plus a synthesis strip: `XCT.SCOR.MAP` itself is a
classification, not a chart in its own right, so it becomes the *organising frame*
for visual #3 rather than its own visual.

### Where the congestion callout goes, and why

**It stays on Ocean Liner, not here**, with only a compact trace of it on this
page. The reasoning: the congestion event's full story (waiting-for-berth leading
demurrage, the Day 1 sorting trap, the specific ports) is operationally dense and
belongs where a reader can act on it - the Ocean Liner page, owned by Network Ops.
What belongs on the CFO's page is the *containment* finding, which is arguably the
more interesting exec-level fact: network-wide schedule reliability barely moved
(0.662 vs. 0.670 unaffected-port baseline) even while two ports collapsed to 0.405,
because the affected calls were only 3.2% of the population. That is a genuinely
different message for a CFO than for an ops manager - "this did not become a
network-wide financial problem, and here's the arithmetic proving it, but it easily
could have if it had touched a bigger share of volume" - and it belongs as a
one-line footnote on the SCOR Reliability row, with a drillthrough into Ocean
Liner's full callout for anyone who wants the underlying story. Putting the full
combo chart and shaded-window annotation here too would duplicate content across
two pages and dilute the CFO page's own headline finding (containment) behind the
Ocean page's headline finding (the operational failure itself) - two different,
both valid, points, that read worse merged into one visual than they do kept on
their own pages and cross-linked.

### The domain synthesis strip, and how it connects to the four pages

Each of the four mini cards wraps a domain page's own headline measure in a
thin, exec-facing pass-through measure:

```dax
Exec Headline Ocean     := [Schedule Reliability Rolling 8wk]
Exec Headline Landside  := [DIFOT %]
Exec Headline Warehouse := [OTIF %]
Exec Headline Air       := [Yield per kg]
```

This is a deliberate, small pattern, not laziness: if a domain team ever renames
or restructures its underlying measure, only the wrapper needs updating, and every
report object referencing `Exec Headline Ocean` keeps working - the same
insulation-by-indirection idea `_Measures` display folders already give you at the
model level, applied here at the report level.

Two mechanisms connect each card to its domain page, and they solve different
problems:

- **A Page navigation button** (Day 22's mechanism) on each card, for the reader
  who just wants to jump to that domain page with whatever filters are already on
  the Executive page still applied - simple, one click, no gesture to learn.
- **A genuine drillthrough**, wired on `TradeRegion` (a field every domain page's
  fact tables can filter on through `DimLocation`, per Day 22's sync-safe filter
  list) plus `Period`. Right-clicking a specific region's value anywhere on this
  page and choosing "Drill through > Ocean Liner" lands on that page with the
  drillthrough filter pane pre-set to that exact region and period - useful when
  the CFO's actual question is "show me *this* region's Ocean numbers," not "take
  me to Ocean Liner in general." Each domain page needs a `Back` button (Action >
  Type = Back) for this to feel native; Power BI's built-in Back type restores the
  exact page and filter state the drillthrough was launched from, no bookmark
  required.

Use the button for the general jump, the drillthrough for the filtered jump. Most
report builders only wire one; a CFO-facing page benefits from both, because the
two questions ("show me that domain" vs. "show me that domain, for that region")
are genuinely different asks that happen inside the same meeting.

### Filters on this page

`Period` and `TradeRegion` sync in, same as every page. No page-specific filter is
added here deliberately - an executive page that grows its own bespoke slicer set
starts drifting toward "yet another domain page," which contradicts its whole
purpose.

---

## Drill

### Exercise 27.1: the SCOR scorecard (30 min)
Build the SCOR Level-1 matrix using the full mapping table from
`KPI_DICTIONARY.md` §5 (`XCT.SCOR.MAP`), not the abbreviated eight-row illustration
in the DAX sample - you need the complete 65-KPI mapping (the profitability KPIs
excluded by design) for the attainment percentage to mean anything. Predict, before
building, which of the five attributes will show the widest spread across its
underlying KPIs' target attainment, and why.

### Exercise 27.2: margin dispersion band (25 min)
Build visual #2. Predict whether the P10-P90 spread is widening, narrowing, or
flat over the period your data covers, before checking, and write one sentence on
what a widening spread with a flat mean would mean for the business that a mean-only
chart would miss entirely.

### Exercise 27.3: dual-mechanism domain links (30 min)
Wire both the Page navigation button and the `TradeRegion`+`Period` drillthrough
for at least two of the four domain synthesis cards. Test: does the button
preserve the Executive page's current filter selection when it lands on the domain
page? Does the drillthrough correctly pre-filter to the specific region you
right-clicked, and does the Back button return you to the exact prior state,
filters included? Note any mismatch.

### Exercise 27.4: the congestion footnote (15 min)
Write the one-sentence containment footnote for the SCOR Reliability row, in your
own words, and wire its drillthrough into Ocean Liner. Then write two sentences
defending the decision to keep the full callout on Ocean Liner rather than
duplicating it here - or, if you disagree with that decision after building both
pages, argue the other way and say what changed your mind.

---

## Ship

Build page `0 Executive Summary` with all six visuals, the SCOR scorecard using
the complete mapping, both domain-link mechanisms wired for all four synthesis
cards, and the containment footnote with its drillthrough. Add the four
`Exec Headline *` wrapper measures to `_Measures`, display folder
`05 Executive Synthesis`.

```
git add .
git commit -m "Day 27: Executive Summary dashboard, SCOR scorecard, dual-mechanism domain links"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] Page `0 Executive Summary` exists with all six visuals, on-theme, nav bar
      intact.
- [ ] The SCOR scorecard uses the complete KPI mapping, not the abbreviated
      illustration, and you can state which attribute showed the widest spread in
      your own data.
- [ ] The margin dispersion band is built and you can state, from your own data,
      whether the spread is widening, narrowing, or flat.
- [ ] Both the Page navigation button and the `TradeRegion`+`Period` drillthrough
      work on at least two domain synthesis cards, Back button confirmed to
      restore prior state.
- [ ] You can state, in your own words, the containment finding (network figure
      barely moved despite two ports collapsing) and defend where the full
      congestion callout lives.
