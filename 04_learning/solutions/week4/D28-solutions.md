# Day 28: solutions

---

## Spaced recall answers

1. `Period` and `TradeRegion` sync everywhere. `Mode` is the unsafe one: it breaks
   on **Landside** (`FactTransportLeg` carries no `ModeKey`) and **Warehouse &
   Inventory** (`FactWarehouseTask`/`FactInventorySnapshot` carry no mode
   dimension either).
2. **8.7 percentage points** (95.4% naive vs. 86.7% correct). The cause is the
   operator: `(DIF + DOQ + DOT) / 3` (arithmetic mean) versus `DIF x DOQ x DOT`
   (the correct multiplicative decomposition) - the underlying DIF/DOQ/DOT figures
   are identical in both, only the combining operator differs.
3. A **Page navigation button** (jumps to the domain page, preserving whatever
   filters are currently active on the Executive page) and a **genuine
   drillthrough** on `TradeRegion`+`Period` (jumps to the domain page pre-filtered
   to a specific right-clicked region/period). The button answers "show me that
   domain"; the drillthrough answers "show me that domain, for that specific
   region."
4. The full callout (combo chart, shaded window, tooltip) lives on **Ocean
   Liner**. The Executive page carries only a one-line containment footnote on the
   SCOR Reliability row ("network held at 0.662 vs. 0.670 unaffected, because the
   affected 3.2% of volume was too small a share to move the network figure"),
   with a drillthrough into the full Ocean Liner callout.
5. Any of: DPO in `XCT.FIN.C2C` (not computable, no vendor payment-terms field or
   AP fact - reported as a documented gap, not fabricated); true top-of-funnel
   `ALC.SLS.CONV` (implemented as a booking-stage conversion proxy); or
   `WHS.UTL.CUBE` (implemented using a documented `StandardPalletCbm ~ 1.7 m^3`
   assumption in place of a true racking-height/volume field).

---

## Part A: reference nav shell inventory

Compare your written-from-memory list against your actual build using this
structure, not a numeric answer key:

- **Nav bar buttons (5)**: one per page (`0 Executive Summary` through
  `4 Air & LCL`), each Page navigation, target = its own page, present and
  identically positioned on all five pages, with exactly the current page's own
  button re-tinted to the selected state on each page's copy.
- **Bookmarks**: `Reset Filters` (Data only, default slicer state), the two
  `Filter Pane Show`/`Filter Pane Hide` bookmarks (Display only). No bookmark
  drives the nav bar's "selected" highlight - per Day 22's explicit design
  decision, that's static per-page button styling, not dynamic.
- **Drillthrough pages**: `Carrier Detail` (Day 24, filter field `CarrierCode`),
  each of the four domain pages as a drillthrough target from the Executive page
  (Day 27, filter fields `TradeRegion` + `Period`). Every drillthrough target
  carries a native `Back` action button, not a bookmark.
- **The deliberately-skipped mechanism**: the dynamic bookmark-driven "you are
  here" highlight. The right call to skip it holds as long as the nav bar truly
  never changes structure - if a future week adds a sixth page or a
  conditionally-hidden page (e.g. an RLS-gated page in Week 5), the static
  per-page-copy approach would need re-auditing across every copy, and a
  dynamic, single-source highlight would start earning its complexity back. Worth
  re-deciding then, not now.

Common honest mismatches worth logging: forgetting that the two Filter Pane
bookmarks need their own toggle button pair (easy to build one and assume the
other exists), or discovering a drillthrough page missing its Back button because
it was copy-pasted from a page that had one wired differently.

---

## Part B: reference paragraphs (compare, don't copy)

1. "One page = one decision" is sharper than "one page = one domain" because a
   domain split (Ocean, Landside, Warehouse, Air & LCL, cross-cutting) organises
   how the KPI dictionary and the measure library are built, not how a reader
   uses a finished report. A page that fails the decision test still displays
   correct numbers - every KPI on it can be individually right - while answering
   nothing a reader can act on; the Ocean Liner page carrying all 22 KPIs
   undifferentiated, with no clear "should we intervene" answer, was the concrete
   shape of that failure this week deliberately avoided by cutting to seven
   justified visuals.
2. Filter scope depends on which fact tables the pages sit on, not on how
   convenient a shared slicer would be, because a synced filter that looks active
   on a page whose fact table doesn't carry that column is worse than no filter
   at all: it either does nothing while appearing to do something (the Mode
   slicer on Landside) or, if wired carelessly through an invented relationship,
   silently filters a page to zero rows. The audit has to be done column-by-column
   against each fact table's actual grain, the same discipline as checking
   `DISTINCT` values before trusting a `TREATAS` bridge on Day 13.
3. A plain Page navigation button answers "take me to that domain," preserving
   whatever the reader already had selected. A genuine drillthrough answers "take
   me to that domain, for this specific thing I just right-clicked," landing
   pre-filtered regardless of what was previously selected. Building only the
   button means a reader can never jump straight to one region's detail without
   manually re-filtering after arriving; building only the drillthrough means a
   reader can never do the simple, common "just take me there" jump without first
   finding something clickable to right-click on.
4. A report/page tooltip responds to whatever's being hovered and can carry a
   measure-driven, filter-context-aware message, while a static annotation on the
   canvas says the same fixed thing regardless of what a reader is looking at or
   which date range is in view. Day 23's congestion tooltip is the concrete case:
   the shaded window annotation is only visible while that date range is on
   screen, but the tooltip attached to the demurrage series still surfaces the
   context even after a reader has filtered the chart to a different period.
5. Contrast: body text against its background should meet at least a 4.5:1 ratio,
   checked against the actual theme hex values, not assumed from how it looks on
   one monitor. Alt text: every visual needs a real, specific description in
   Format > General > Alt text, not the Power BI default auto-generated one,
   since a screen reader user gets only that text, never the chart itself. Colour-
   blind-safe encoding: any status shown by colour (the `good`/`neutral`/`bad`
   accents from Day 22's theme) needs a second channel, an icon or a text label,
   alongside the colour, because red/green alone is exactly the pairing a
   substantial share of colour-blind readers cannot distinguish.

---

Part C has no reference answer - it is a genuine audit of your own build, and the
value is in what it actually turns up, not in matching a checklist someone else
ran. Keep the fix notes; they are this week's version of a portfolio story.
