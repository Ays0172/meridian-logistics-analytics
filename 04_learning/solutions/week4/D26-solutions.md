# Day 26: solutions

---

## Spaced recall answers

1. `Yield per kg := CALCULATE(DIVIDE(SUM(FactShipment[Revenue_usd]),
   SUM(FactShipment[ChargeableWeightKg])), DimMode[ModeGroup]="Air")`. The naive
   `AVERAGEX` version gives a 40 kg courier shipment and a 12,000 kg charter
   consolidation equal weight, so a portfolio of many small shipments dominates the
   "average yield" regardless of revenue-weighted reality.
2. Air 1:6000 (IATA standard, `VolumeCbm x 166.67`), Air 1:5000 (carrier variant,
   `VolumeCbm x 200`), Ocean LCL 1:1000 (flat tonne-for-cbm, `MAX(WeightKg/1000,
   VolumeCbm)`, no divide-by-thousands step). Air 1:6000 and 1:5000 are the most
   commonly confused pair operationally (same mode, same-looking divisor pattern),
   but the dictionary flags ocean's 1:1000 rule against either air rule as the
   single most expensive entry-level mistake, since the two conventions differ by
   a factor of five to six.
3. It measures a **booking-stage conversion proxy**: of quotes that reached a
   booking attempt, how many actually shipped. It structurally understates true
   top-of-funnel win rate, because a quote that was requested and never came back
   as any booking row at all is invisible to the measure - `FactBooking` is the
   only table carrying `QuoteKey`, and it only contains quotes that got that far.
4. Landside used a stacked (not 100%-stacked, which would renormalise and hide the
   gap) reconciliation bar (Deadhead % / Truck Utilisation %) so a data-quality gap
   shows up visually rather than requiring trust in an
   isolated number. The analogous opportunity here is the chargeable-weight donut:
   segmenting by rule (rather than blending into one total) makes the "these three
   conventions are not interchangeable" fact visible in the chart itself.
5. FCL cargo is priced per container, not per kg, so its `ChargeableWeightKg`
   figure isn't meaningfully comparable to an LCL or air per-kg figure - including
   FCL would compare two different pricing logics as if they were the same unit.

---

## Exercise 26.1: paired modal comparison

The lane with the widest cost-index/transit-index rank gap is typically a
mid-distance, moderate-value lane where air's speed premium is large in relative
terms but the absolute cost gap is smaller than on a long-haul lane (short-haul
routes tend to have the smallest absolute air/ocean cost multiple, since bunker
and vessel-days scale with distance more than air freight does). The shippers on
that lane are trading a meaningfully long, well-worn transit-time gap for a
relatively affordable air premium - exactly the profile a lane where "should this
go air or ocean" is a live, non-obvious commercial question, rather than one mode
dominating outright.

## Exercise 26.2: chargeable weight blending distortion

Blending all three rules into one chargeable-weight total and computing yield on
top of it produces a **distorted** figure, typically pulled in whichever direction
the largest-volume rule's typical shipment size and rate level differ from air's:
since ocean LCL's 1:1000 rule and air's 1:5000/1:6000 rules represent different
underlying densities and rate levels, blending them mixes two economically
different populations into one number that represents neither cleanly. The
predicting line is the `ALC.REV.YIELDKG` watch-out itself: "comparing yield per kg
across shipments on different chargeable-weight rules without segmenting mixes two
different denominators' economics into one number."

## Exercise 26.3: volumetric share trend

A rising volumetric-driven share (shipments where `ChargeableWeightKg >
GrossWeightKg`, i.e. billing is driven by space rather than actual weight) implies
pricing strategy should shift toward **cbm-based rating** rather than pure per-kg
rating on that mode - the KPI dictionary states this directly as "a strong hint,"
not a certainty, since the shift could also reflect a genuine change in commodity
mix (more bulky, low-density cargo like apparel or consumer electronics) rather
than a pricing-policy gap. Either way, the visual is the trigger for the
conversation, not the final answer.

## Exercise 26.4: the honest one-sentence answer

"No - this is booking-stage conversion, meaning of the quotes that made it as far
as an actual booking attempt, roughly [X]% shipped; it can't see the quotes that
were requested and never came back to us at all, so our true top-of-funnel win
rate is lower than this number, and we don't currently have the data to measure
that gap directly." The point of the exercise is being able to say this cleanly,
in one breath, without either overstating the number's meaning or burying the
caveat in qualifiers nobody in the room retains.
