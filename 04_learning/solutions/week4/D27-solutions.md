# Day 27: solutions

---

## Spaced recall answers

1. `XCT.SCOR.MAP`, `XCT.QLT.PERFECT`, `XCT.FIN.C2C`, `XCT.FIN.FCR`, `XCT.FIN.CTS`,
   `XCT.CUS.CONC`, `XCT.FIN.MARGDISP`. DPO cannot be computed at all: `DimCarrier`
   carries no payment-terms field, and no fact table records a vendor-invoice or
   vendor-payment date, so there is no source for it under this schema contract.
2. `XCT.QLT.PERFECT` covers **every** shipment across every mode, with no
   `WarehouseKey` filter - the enterprise superset. `WHS.QLT.PERFECT` restricts to
   shipments that touched a Meridian warehouse. They can legitimately disagree
   because warehouse-touched shipments (often value-added-service shipments) can
   carry a different, more complex, more failure-prone risk profile than the book
   as a whole.
3. Because the "top 10" set itself is a ranking that depends on the current filter
   context (region, period, mode) - a top-10 list computed once at the company
   level does not carry over correctly to a filtered view, since the actual top 10
   customers by revenue can differ once you restrict to one region or one year.
4. Any correct pairing from the §5 mapping table is acceptable, e.g.
   `OCN.REL.SCHED` (Ocean) and `LND.SVC.DIFOT` (Landside) both map to
   **Reliability**; `WHS.OPS.D2S` (Warehouse) and `ALC.TRN.MODAL` (Air & LCL) both
   map to **Responsiveness**.
5. Network-wide schedule reliability is **0.6598**. It barely moved (0.662 vs.
   0.670 for unaffected ports) because the 131 affected calls at Rotterdam/LA were
   only 3.2% of the total call population - a 40% local failure at that small a
   share of volume shifts the network average by only about 0.8 points in
   absolute terms (README §6's "1.3%" is the same shift expressed relatively:
   0.008/0.670 ≈ 1.3% of the unaffected baseline, not 1.3 percentage points).

---

## Exercise 27.1: SCOR scorecard, expected spread

**Reliability** and **Cost** are the two attributes most likely to show the widest
spread across their underlying KPIs' target attainment in this dataset, because
Reliability directly includes `OCN.REL.SCHED`, which is the one KPI in the entire
library with a *known, deliberately modelled* extreme event (the congestion
window) sitting inside its trailing window at certain periods - a single KPI that
swings hard will widen its whole attribute's spread. Cost tends to run wide for a
structural reason rather than an event-driven one: it blends genuinely different
cost bases (BAF billing-integrity, per-km landside cost, labour cost per line,
direct-cost-only cost-to-serve), each with its own natural variance, into one
attribute bucket.

## Exercise 27.2: margin dispersion

Expect the P10-P90 spread to show **periods of widening** that do not track the
mean margin closely - the contract's own validation gate documents a mean gross
margin of 14-22% *with a documented loss-making left tail*, meaning the spread's
behaviour is partly structural (some shipments are always loss-making) rather than
purely cyclical. A widening spread with a flat mean means: the average is not
telling you the business is getting less healthy, because it isn't - but a growing
share of individual shipments are quietly sliding into or further into loss, which
a mean-only chart cannot show and a P10-P90 band can.

## Exercise 27.3: dual-mechanism links, expected behaviour

The Page navigation button, correctly wired, **should** preserve the Executive
page's current filter selection when it lands on the domain page, since Page
navigation only changes which page is displayed - it does not clear or alter
slicer state (unless a Reset-filters bookmark is separately, mistakenly, attached
to the same button). The drillthrough should land with the drillthrough filter
pane showing exactly the right-clicked `TradeRegion` and `Period`, visible and
editable in the pane on the target page. The Back button should restore the exact
page and filter state active immediately before the drillthrough was triggered - if
it instead resets to a default state, the target page's own Reset-filters
bookmark (Day 22) has likely been wired to the same button by mistake instead of
the native `Back` action type.

## Exercise 27.4: the containment footnote and its defense

Example footnote: *"Network schedule reliability held at 0.662 during the
Rotterdam/LA congestion event vs. 0.670 for unaffected ports - contained because
the affected 3.2% of call volume, despite collapsing locally to 0.405, was too
small a share to move the network figure."*

Defense for keeping the full callout on Ocean Liner: the CFO-facing finding
(containment, a positive-framed exec insight) and the ops-facing finding (the
operation itself failed badly at two specific ports, a negative-framed operational
alert) are both true and both important, but they argue for opposite emotional
reads of the same event. Merging them into one visual forces a choice between two
incompatible framings on one chart, or dilutes both into a muddier middle message.
Kept on separate pages, each page's reader gets the framing that matches the
decision they're actually making - and the footnote's drillthrough means nobody
who needs the operational detail is more than one click away from it.
