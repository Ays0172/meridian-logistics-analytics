# Day 24: solutions

---

## Spaced recall answers

1. `Deadhead % := DIVIDE(SUM(FactTransportLeg[EmptyKm]), SUM(FactTransportLeg[DistanceKm]))`.
   The naive `AVERAGEX` version gives a 5 km empty repositioning leg (100%
   deadhead) and a 500 km loaded linehaul with a 20 km empty tail (4% deadhead)
   equal weight, so the fleet-level number ends up dominated by however many short
   legs exist, not by how many empty kilometres they actually represent.
2. It requires counting legs that are **both** on-time **and** in-full
   simultaneously (the joint condition), not multiplying two independently
   computed marginal rates - a late leg is often also a partial delivery, so the
   two conditions are not statistically independent and the product of marginals
   understates the true joint failure rate.
3. `Period` and `TradeRegion`. `Carrier` doesn't join them because no other page's
   fact tables carry a carrier key - it is meaningless outside Landside.
4. `Truck Utilisation % = 1 - Deadhead %` algebraically, but the KPI dictionary
   insists on computing it independently from `LoadedKm` (not derived as
   `1 - Deadhead %`) so that a data-quality break where
   `LoadedKm + EmptyKm != DistanceKm` stays visible instead of being silently
   forced to reconcile by construction.
5. Reusing the "chart type that makes a trap visible rather than requiring trust in
   an isolated number" idea from Day 23's reliability-vs-volume scatter, applied
   here as the stacked (**not** 100%-stacked — that variant renormalises and would
   hide the gap) reconciliation bar for Deadhead/Truck Utilisation.

---

## Exercise 24.1: composite score ranking, expected pattern

The carrier ranked #1 overall will **not** necessarily lead every individual
component. Because on-time delivery carries the heaviest weight (0.40), a carrier
with a strong on-time record and a merely middling cost index can out-rank a
cheaper but less reliable carrier - this is the weighting doing its job, not a
bug. The useful check is confirming this in your own data: pick the overall #1 and
verify it is *not* simultaneously the cheapest (lowest cost index) carrier in the
panel. If it is both #1 overall and cheapest, that's still plausible, just worth a
second look at whether the normalisation range is being dominated by one outlier
carrier at the expensive end.

## Exercise 24.2: reconciliation stacked bar

If every carrier's stack reaches 100% cleanly, that is a legitimate pass, not
evidence the check wasn't needed - `FactTransportLeg` may simply have clean
`LoadedKm`/`EmptyKm`/`DistanceKm` data for this build. To prove the check was
actually run rather than assumed: add a hidden helper measure,
`LND Reconciliation Gap := 1 - Deadhead % - Truck Utilisation %`, pin it to a
tooltip or a small table beneath the stacked bar, and note its max absolute value
across all carriers in your notes. A reviewer who sees "max gap 0.0%" knows the
check ran and passed; a reviewer who only sees a clean-looking chart has to take
your word for it.

## Exercise 24.3: Carrier Detail drillthrough

Reference measures for the drillthrough page (population-wide, so they must be
computed with `ALL(DimCarrier)` or the equivalent, not carrier-filtered):

```dax
Carrier Cost Index Min (Population) :=
CALCULATE ( MINX ( VALUES ( DimCarrier[CarrierKey] ), [Cost per km] ), ALL ( DimCarrier ) )

Carrier Cost Index Max (Population) :=
CALCULATE ( MAXX ( VALUES ( DimCarrier[CarrierKey] ), [Cost per km] ), ALL ( DimCarrier ) )
```

The correctness check in the exercise (min/max identical across two different
drilled-into carriers) is the actual test that these are population-wide and not
accidentally carrier-filtered - a common mistake is forgetting the `ALL()` and
getting a min/max that trivially equals the single selected carrier's own value on
every drillthrough, which silently defeats the whole point of showing where a
carrier sits in the population.

## Exercise 24.4: detention at site

Flag any warehouse whose `Avg Detention at Site Hours` crosses roughly 1 hour as a
candidate for an appointment-scheduling review - the exact count depends on your
own build's data.

Ocean detention (`OCN.REV.DET`) is measured in **dollars of revenue billed**;
landside detention at site (`LND.OPS.DET`) is measured in **hours of delay**. They
must never be combined into one "detention" card because they are different units
measuring different failure modes on different sides of the business (a customer
paying a demurrage-adjacent charge vs. a truck sitting idle at a dock) - adding
dollars to hours produces a number with no unit and no meaning, the same category
of error as summing `TEU` and `Revenue_usd` would be.
