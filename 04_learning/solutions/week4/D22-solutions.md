# Day 22: solutions

This week's solutions are worked reference designs, not a numeric answer key.
Compare your reasoning against these; a different visual choice is fine if your
justification is as concrete as the one here. A justification that only restates
the visual's name ("a bar chart to show carrier scores") is not.

---

## Spaced recall answers

1. `Schedule Reliability Rolling 8wk` counts on-time port calls over rolling
   `COUNTROWS`s, not `AVERAGEX` over weeks: `DIVIDE(COUNTROWS(FILTER(CallsInWindow,
   IsOnTimeArrival=1)), COUNTROWS(CallsInWindow))` over a 56-day
   `DATESBETWEEN`. Averaging seven or eight weekly rates gives a quiet 40-call week
   and a busy 400-call week equal weight, the exact averaging-an-average error from
   Day 9, and it drifts worst precisely when call volume swings hardest, which is
   what happens inside the congestion window.
2. Ocean liner 22, Landside 16, Warehouse & inventory 18, Air & LCL 9,
   Cross-cutting 7. 72 total.
3. Calculation groups let one set of reshaping logic (MTD, QTD, FYTD, PY, YoY%)
   apply to every measure in the model without a duplicated measure per
   base-measure-per-period. `SELECTEDMEASURE()` is the placeholder for "whichever
   measure is currently in the visual."
4. `FactTarget[Region]` is plain text at monthly/region grain; `DimLocation` has no
   matching key at that grain. The bridge is `DimLocation[TradeRegion]` (five
   values: Americas, Asia, Europe, MEA, Oceania), not the finer-grained
   `DimLocation[Region]`, which uses a completely different value set.
5. Network-wide schedule reliability is **0.6598**. During the 14 Jul-14 Sep 2025
   window, Rotterdam and Los Angeles fall to **0.405** while unaffected ports hold
   **0.670** and the network figure barely moves (0.662 vs 0.670), because the 131
   affected calls are only 3.2% of the population.

---

## Exercise 22.1: page purpose statements, reference version

| Page | Decision | If nobody could answer it from the page alone |
|---|---|---|
| Ocean Liner | Where is reliability or utilisation slipping enough to need a response this month? | The page is a KPI wall, not a dashboard: correct numbers, no operational conclusion. |
| Landside | Which carriers earn more freight next quarter, which get put on notice? | A carrier scorecard exists but nobody can actually use it in the quarterly review it was built for. |
| Warehouse & Inventory | Is a site's problem people (labour/quality) or stock (inventory/obsolescence)? | Two structurally different fixes (training vs. purchasing) get conflated into one vague "warehouse is underperforming" conversation. |
| Air & LCL | Is this lane priced/routed on the right mode, is the desk converting quotes? | Yield numbers exist with no action a commercial manager can take from them. |
| Executive Summary | Where does the CFO/COO personally intervene this week? | The page becomes a status report read once and never acted on - the single worst outcome for an executive-facing page. |

## Exercise 22.2: theme file

What the theme JSON does **not** control: font/size/colour on a *specific instance*
of a visual once someone has manually overridden it in that visual's own Format
pane - manual formatting always wins over the theme for that one visual, silently,
with no visual indicator that it has drifted from the theme. This is exactly why
Format Painter (copy the finished, on-theme visual, not re-build from theme
defaults each time) matters once real content goes in from Day 23 onward: a
one-off manual tweak on page 2 will not automatically appear on page 4's matching
visual, and there is nothing in the UI that flags the drift for you later.

## Exercise 22.3: nav shell, reference wiring

- Nav bar: five rectangles, 44px tall (comfortably above the ~40px minimum
  practical touch target, ahead of Day 28's mobile pass), icon + label, positioned
  identically at y=0 on every page.
- Each button: Format > Action > On, Type = Page navigation, Destination = the
  target page. Test every button from every other page, not just from page 1 -
  a common miss is wiring all five buttons correctly on page 1 and then only
  copy-pasting the bar (which correctly carries the actions) without re-tinting
  the *new* page's own "you are here" button, leaving two buttons looking selected
  or none.
- Reset-filters bookmark: View > Bookmarks > Add, with the slicers in their default
  (cleared) state, "Data" checked, "Display"/"Current page" unchecked so it resets
  filters without also jumping the reader to a different page. Attach it to a
  button via Action > Type = Bookmark.

## Exercise 22.4: filter scope audit, reference table

See the Concept section's table verbatim - it is the reference answer. The one
"no" row: **Mode**. Concretely, syncing a `DimMode[ModeCode]` slicer onto the
Landside page would either (a) silently do nothing, because `FactTransportLeg`
carries no `ModeKey`, leaving the slicer visibly selected but functionally inert
and misleading a reader into thinking the Landside numbers are mode-filtered when
they are not, or (b) if someone later adds a naive relationship to force it to
"work," filter Landside to zero rows the moment a mode with no landside legs (Air)
is selected, with no error, just an empty page. A reader would notice first on the
Landside page itself, since that is where the slicer's apparent effect and its
actual (non-)effect diverge.
