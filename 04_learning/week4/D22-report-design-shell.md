# Day 22: Report Design Principles and the Navigation Shell

> Time: 3 h · Spaced recall 10 min · Concept 45 min · Drill 80 min · Ship 30 min · Log 15 min

Week 3 gave you ~150 measures sitting in `_Measures`, organised into display folders,
each one correct and checkable against the KPI dictionary. A measure library is not
a report. Today you decide the shape the report takes before you build a single
domain page: how many pages, what each one is *for*, which filters travel between
them, and how a reader gets from one to another without hunting through a pages
list. Get this wrong and Days 23-27 become five disconnected screens that happen to
share a data model. Get it right and they become one report a stakeholder can
actually navigate under pressure, in a live meeting, without you narrating.

---

## Spaced recall (10 min, closed book)

1. State, from memory, the pooled DAX for `Schedule Reliability Rolling 8wk` you
   built in Week 3 Day 16, and explain in one sentence why it cannot be built as an
   average of seven or eight weekly rates (this is Day 9's averaging trap, back
   again in a new context).
2. Name the five KPI domains this project's 72 KPIs split into, and how many KPIs
   sit in each.
3. What problem do calculation groups solve, and what is `SELECTEDMEASURE()`
   standing in for (Day 14)?
4. Why does `FactTarget` need `TREATAS` rather than a physical relationship to
   `DimLocation`, and which column is the actual bridge (Day 13)?
5. Give the two numbers that make the Rotterdam/Los Angeles congestion event worth
   putting on a dashboard: the network-wide schedule reliability figure, and the gap
   between congested and unaffected ports during the event window.

---

## Concept

### "One page = one decision," not "one page = one domain"

The KPI dictionary's five-way split (Ocean 22, Landside 16, Warehouse 18, Air & LCL
9, Cross-cutting 7) is a convenient organising principle for *building* measures. It
is not, by itself, a report design. A page organised around a domain can still fail
the only test that matters: **does a reader do something differently after looking
at it?** A page that answers "is our schedule performance healthy enough that
commercial can keep quoting current transit promises" is a decision page. A page
that is just "here are 22 numbers about ships" is a reference sheet, and reference
sheets belong in an appendix, not in the five pages a VP opens first.

So before drawing anything, write the decision each page exists to support:

| Page | One-line decision it supports |
|---|---|
| Ocean Liner | Where is network reliability or capacity utilisation slipping enough to need a commercial or operational response this month? |
| Landside | Which carriers earn more freight next quarter, and which get put on notice? |
| Warehouse & Inventory | Where is a site losing service (OTIF) or money (labour, shrinkage, obsolescence), and is it a people problem or a stock problem? |
| Air & LCL | Is this lane's cargo priced and routed on the right mode, and is the desk converting quotes into bookings? |
| Executive Summary | Where, across the whole network, does the CFO or COO need to personally intervene this week? |

Every visual you add from Day 23 onward has to earn its place against its page's
one-line decision. If you cannot say which decision a visual moves, it is
decoration, and decoration is exactly what turns a five-page report into
twenty-two unjustified charts nobody reads past the first meeting.

### Filter scope: page-level, page-specific, or excluded entirely

Power BI lets a slicer's selection **sync** across pages (Format > Edit
interactions > Sync slicers pane). The tempting default is "sync everything, keep
it simple." That default breaks the moment two pages disagree about what a filter
column even means, because the five domain pages sit on fact tables at genuinely
different grains: `FactPortCall`/`FactContainerMove` for Ocean, `FactTransportLeg`
for Landside, `FactWarehouseTask`/`FactInventorySnapshot` for Warehouse,
`FactShipment` cut by mode for Air & LCL. A filter that is meaningful everywhere on
one page can be meaningless, or silently wrong, on another.

Work through the candidate filters explicitly, the same way you worked through
`ALL` vs `ALLSELECTED` on Day 9, rather than guessing:

| Filter | Backing column | Pages it belongs on | Sync across pages? |
|---|---|---|---|
| Period (Year / rolling window) | `DimDate[Date]`, driven by the `Time Intelligence` calc group | All five | Yes, always. Every fact table relates to `DimDate`. |
| Trade region | `DimLocation[TradeRegion]` | All five | Yes, with care: this is the same bridge column Day 13 used for `FactTarget`, and it is common to `DimLocation`, which every fact table reaches. |
| Mode | `DimMode[ModeCode]`/`ModeGroup` | Ocean, Air & LCL | **No.** `FactTransportLeg` (Landside) and `FactWarehouseTask`/`FactInventorySnapshot` (Warehouse) carry no mode dimension at all. Syncing a Mode slicer onto those pages either does nothing (confusing: the slicer looks live but has no effect) or, worse, filters an unrelated table down to zero rows if someone wires it in carelessly. |
| Customer segment | `DimCustomer[CustomerSegment]` | Ocean, Air & LCL, Executive | Page-specific. Landside and Warehouse legs/tasks are not always cleanly attributable to one customer segment at the grain those pages report at. |
| Carrier | `DimCarrier[CarrierCode]` | Landside only | Page-specific; no other page's fact tables carry a carrier key. |
| Warehouse | `DimWarehouse[WarehouseCode]` | Warehouse only | Page-specific. |

The rule that falls out of the table: **sync a filter only when every page it
touches shares both the column and a sensible interpretation of it.** `Period` and
`TradeRegion` clear that bar for all five pages. Nothing else does by default.
Anything narrower stays a page-level slicer, visible only on the pages where it
means something, so a reader is never staring at a slicer that looks active but is
quietly inert.

### One theme file, not five sets of manual formatting

Power BI reads report-wide formatting from a JSON theme (View > Themes > Browse for
themes). Building one theme file and applying it once is the visual equivalent of
the `_Measures` table: a single source of truth instead of five pages that drift
apart the moment someone changes a font size on page 3 and forgets pages 1, 2, 4
and 5. It is also git-diffable text, which matters on a project that is already
under version control end to end (`03_powerbi` is `.pbip`/TMDL, per the README) - a
theme change shows up as a readable diff, not an opaque binary change buried inside
a `.pbix`.

A minimal starting theme, keyed to a maritime palette with one warning accent
reserved for exactly the kind of "this number looks good but the operation is
failing" callouts Day 23 needs:

```json
{
  "name": "Meridian",
  "dataColors": [
    "#1B4965", "#5FA8D3", "#BEE9E8", "#62929E", "#264653", "#E9C46A"
  ],
  "background": "#FFFFFF",
  "foreground": "#1B1B1B",
  "tableAccent": "#1B4965",
  "good": "#2A9D8F",
  "neutral": "#E9C46A",
  "bad": "#E76F51",
  "textClasses": {
    "callout": { "fontSize": 28, "fontFace": "Segoe UI Semibold" },
    "title": { "fontSize": 14, "fontFace": "Segoe UI Semibold" },
    "label": { "fontSize": 10, "fontFace": "Segoe UI" }
  }
}
```

`good`/`neutral`/`bad` are used with conditional formatting rules on KPI cards
(Day 23 wires the first one), not as generic data colours; keep them out of the
`dataColors` array so they never get auto-assigned to an unrelated category series.

### The navigation shell

**The "you are here" state does not need a bookmark.** Each report page carries its
own independent copy of the nav bar, so the simplest correct pattern is: build the
five-button nav bar once, copy it onto every page, and on each page re-tint that
page's own button to the "selected" colour from the theme. Five pages, five static
variants of one nav bar, kept in sync by copy-paste, not by dynamic DAX or a
bookmark. This is deliberately the boring option - a bookmark-driven highlight
(swap visuals on click, or toggle visibility by group) is real and some tutorials
reach for it by default, but it is unnecessary machinery for five buttons that
never change, and it is one more thing to keep synchronised across pages. Save the
bookmark budget for problems a static button cannot solve.

Where bookmarks *do* earn their place today:

- **Reset filters.** A bookmark captured with only "Data" checked, all slicers in
  their default state, attached to a button labelled "Reset." One click undoes
  whatever filter combination a reader wandered into.
- **Filter pane show/hide.** Two bookmarks capturing "Display" (object visibility)
  only, toggling a slicer panel open and closed, so the report can default to a
  clean view and still let a power user expose the filters.

Each button's actual page-to-page travel uses the **Page navigation** action type
(Format pane > Action > Type = Page navigation > target page) - not a bookmark at
all. Reserve `Back` buttons (Action > Type = Back) for drillthrough targets, which
Day 27 wires; Power BI's built-in Back type already knows how to return to
wherever the drillthrough was launched from, including the filter state, so
nothing custom is needed there either.

### A grid, so five pages look like one report

Fix these once and apply them everywhere:

- **Canvas size**: 16:9, 1280x720, set on page 1 and copied via Page Information
  format, not re-typed per page.
- **A fixed header band** (page title + KPI card row) at the same height on every
  page, so a reader's eye lands in the same place switching pages.
- **An 8px snap grid** (View > Gridlines > Snap to grid) and the Selection pane's
  Align/Distribute tools, used instead of eyeballing pixel positions.
- **Format Painter** to copy a finished visual's formatting onto its sibling on
  another page rather than re-setting fonts, borders and padding by hand each time.
- **Number formatting set on the measure**, not the visual. A format string on
  `[Schedule Reliability Rolling 8wk]` itself (percentage, 1 decimal) renders
  identically on every card, table and tooltip that uses it, on every page, with no
  per-visual formatting to keep in sync.

---

## Drill

Design-judgment days do not have a numeric answer to predict, so replace "predict,
then verify" with: **write your decision and its justification down first, then
compare it against the reference design in solutions.** A justification you had to
invent after seeing the answer is worth much less than one you committed to first.

### Exercise 22.1: page purpose statements (15 min)
Write the one-line decision each of the five pages supports, in your own words, not
copied from the Concept table above. For each one, write a second sentence: what
would you conclude was true about the report if this page existed but nobody could
answer its decision question from it alone?

### Exercise 22.2: the theme file (25 min)
Build `03_powerbi/themes/meridian-theme.json` (start from the JSON above, adjust to
taste) and apply it via View > Themes > Browse for themes on a fresh blank report.
Confirm a default bar chart and a default card pick up the palette without manual
formatting. Note one thing the theme JSON schema does *not* control that you
expected it to (there is at least one - find it by trying).

### Exercise 22.3: build the nav shell (40 min)
Create five blank pages, numbered so they sort in report order regardless of any
later alphabetical resort: `0 Executive Summary`, `1 Ocean Liner`,
`2 Landside`, `3 Warehouse & Inventory`, `4 Air & LCL`. Build the five-button nav
bar once, copy it to all five pages, wire each button's Page navigation action, and
re-tint each page's own button to the selected state. Add the Reset-filters
bookmark and button on one page first, confirm it works, then copy it everywhere.

### Exercise 22.4: filter scope audit (20 min)
Before building any domain-specific slicer in Days 23-27, decide and write down,
for each of the six filters in the Concept table, which pages it belongs on and
whether it syncs. Then, for the one filter in the table marked "no" for syncing,
write two sentences: what would go wrong, concretely, if you synced it anyway, and
on which page would a reader notice first.

---

## Ship

Commit the shell, not yet the domain content: `03_powerbi/themes/meridian-theme.json`,
the five numbered blank pages with the nav bar and Reset-filters button wired, and
a short `06_portfolio/notes-report-design.md` capturing your five page-purpose
statements from Exercise 22.1 and your filter-scope decisions from Exercise 22.4.
Both of those documents are the actual design rationale you will need again in
Week 6 when you write this project up as a portfolio piece - capture them now,
while the reasoning is fresh, not retroactively.

```
git add .
git commit -m "Day 22: report shell, theme, nav bar and filter scope decisions"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] You can state, without notes, the one-line decision each of the five pages
      supports.
- [ ] `meridian-theme.json` exists, is applied, and you can name one thing it does
      not control.
- [ ] The nav bar exists on all five pages, each page's own button correctly
      tinted as selected, Page navigation actions wired and tested.
- [ ] The Reset-filters bookmark and button exist and work on at least one page.
- [ ] You can explain, in one sentence naming the specific pages, why the Mode
      filter does not sync across all five pages.
- [ ] Filter-scope decisions and page-purpose statements committed to
      `06_portfolio/notes-report-design.md`.
