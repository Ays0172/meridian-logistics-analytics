# Day 17: solutions

---

## Spaced recall answers

1. `SlotCapacityTeu` is a capacity/effort denominator that varies enormously
   call-to-call (a 2,000-TEU feeder next to a 20,000-TEU ULCV). That variance is
   what made the naive gap land closer to the LPH pattern than to Revenue-per-FFE's
   near-zero gap, where the denominator (FFE) does not correlate strongly with the
   per-unit rate.
2. `-1` marks a container's first-ever event, meaning there is no prior dwell to
   measure, averaging it in blends a sentinel with real hours and silently drags
   the average down. `FactShipmentMilestone` (Day 12) introduced the `-1`
   not-yet-happened convention.
3. `WaitingForBerthHours` ×3.4, demurrage charge-line volume ×3.1, container dwell
   at the affected ports ×2.6 (per `SCHEMA_CONTRACT.md` §3.3).
4. Deadhead % is kilometre-based (share of total distance run empty); Empty
   Repositioning Ratio is leg-count-based (share of legs that are dedicated
   repositioning moves). A fleet can have a low deadhead % (short empty tails on
   otherwise loaded legs) while still running a high count of short repositioning
   legs, the two answer different questions and one cannot substitute for the
   other.
5. Naive measures are named `[DO NOT USE] <Name> (naive)`. They sit in the same
   folder as their correct sibling so the next analyst opening that folder sees the
   trap in context, with a description explaining the mechanism, rather than a
   clean folder with no memory of the mistake anywhere.

---

## Exercise 17.1: the nine worked KPIs

```dax
Cost per km := DIVIDE ( SUM ( FactTransportLeg[TotalCostUsd] ), SUM ( FactTransportLeg[DistanceKm] ) )
[DO NOT USE] Cost per km (naive) := AVERAGEX ( FactTransportLeg, DIVIDE ( FactTransportLeg[TotalCostUsd], FactTransportLeg[DistanceKm] ) )

Deadhead % := DIVIDE ( SUM ( FactTransportLeg[EmptyKm] ), SUM ( FactTransportLeg[DistanceKm] ) )
[DO NOT USE] Deadhead % (naive) := AVERAGEX ( FactTransportLeg, DIVIDE ( FactTransportLeg[EmptyKm], FactTransportLeg[DistanceKm] ) )

CO2 per Tonne-km (g) :=
VAR TotalCo2Grams = SUM ( FactTransportLeg[Co2Kg] ) * 1000
VAR TotalTonneKm = SUMX ( FactTransportLeg, ( FactTransportLeg[WeightKg] / 1000 ) * FactTransportLeg[DistanceKm] )
RETURN DIVIDE ( TotalCo2Grams, TotalTonneKm )
[DO NOT USE] CO2 per Tonne-km (naive) :=
AVERAGEX ( FactTransportLeg, DIVIDE ( FactTransportLeg[Co2Kg] * 1000, ( FactTransportLeg[WeightKg] / 1000 ) * FactTransportLeg[DistanceKm] ) )
```

**Ranking, largest expected gap to smallest: `Cost per km` > `CO2 per Tonne-km` >
`Deadhead %`.** `Cost per km`'s denominator (`DistanceKm`) spans everything from a
12 km drayage move to a 1,200 km line-haul, a two-orders-of-magnitude range, the
widest of the three, so naive averaging is dominated by the sheer number of short
legs. `CO2 per Tonne-km`'s denominator is itself a product (weight × distance),
which compounds the same short-leg-noise problem across two dimensions rather than
one, but the weight component partially dampens it (a short leg is often also
lightly loaded, correlating the two factors somewhat). `Deadhead %`'s denominator
is still `DistanceKm`, but the ratio itself is bounded 0–1 and many legs cluster
near a fleet's typical deadhead rate, so the naive average, while still wrong,
tends to land closer to the pooled figure than the unbounded cost ratio does. Your
own build's exact ranking may vary slightly, the reasoning about denominator
range and boundedness is the transferable part, not the precise order.

---

## Exercise 17.2: DIFOT vs the product of marginals

```dax
DIFOT % :=
VAR CommercialLegs = FILTER ( FactTransportLeg, FactTransportLeg[ShipmentKey] <> -1 )
VAR DifotLegs =
    FILTER ( CommercialLegs, FactTransportLeg[IsOnTimeDelivery] = 1 && RELATED ( FactShipment[IsInFull] ) = 1 )
RETURN DIVIDE ( COUNTROWS ( DifotLegs ), COUNTROWS ( CommercialLegs ) )

On-Time Delivery % x In-Full % (illustrative, not shipped) :=
CALCULATE ( AVERAGE ( FactTransportLeg[IsOnTimeDelivery] ), FactTransportLeg[ShipmentKey] <> -1 )
* CALCULATE ( AVERAGE ( RELATED ( FactShipment[IsInFull] ) ), FactTransportLeg[ShipmentKey] <> -1 )
```

**The product of marginals is lower than the true joint `DIFOT %`.** On-time
delivery and in-full delivery are positively correlated in this dataset (a leg that
runs late is disproportionately also the one that had to split or partially
deliver), so the two events co-occur *more* often than independence would predict.
Multiplying two independent-looking probabilities systematically understates a
positively-correlated joint probability, the product treats "on time" and
"in full" as if learning one told you nothing about the other, when in practice a
late leg is a warning sign for an in-full failure too. This mirrors Day 9's
averaging-ratio mechanism in shape (a shortcut arithmetic operation standing in for
a proper joint computation) even though the specific operators involved, product
vs. average, are different. It is also the structural mirror of `WHS.QLT.OTIF`'s
trap (Day 18): OTIF's naive error is averaging three marginals that should be
multiplied; DIFOT's naive error is multiplying two marginals that should be counted
jointly. Both traps come from treating correlated failure modes as if they were
independent, one just goes the direction of the error is "too optimistic" (DIFOT)
and the other "too optimistic" as well (OTIF's naive arithmetic mean also
overstates versus the correct multiplicative figure), worth noting both traps push
the naive number in the same *direction* (looks better than reality), which is
precisely why they are dangerous: nobody double-checks a KPI that looks good.

---

## Exercise 17.3: remaining 7 KPIs

```dax
Cost per Container Move (TEU-normalised) := DIVIDE ( SUM ( FactTransportLeg[TotalCostUsd] ), SUM ( FactTransportLeg[Teu] ) )
Avg Drayage Turn Time (min) := AVERAGE ( FactTransportLeg[TurnTimeMinutes] )
Empty Repositioning Ratio := AVERAGE ( FactTransportLeg[IsEmptyRepositioning] )
First-Attempt Delivery Rate := AVERAGE ( FactTransportLeg[IsFirstAttemptSuccess] )
Accessorial Cost Ratio := DIVIDE ( SUM ( FactTransportLeg[AccessorialUsd] ), SUM ( FactTransportLeg[TotalCostUsd] ) )
Avg Detention at Site Hours := AVERAGE ( FactTransportLeg[DetentionAtSiteHours] )
Subcontracting Ratio := AVERAGE ( FactTransportLeg[IsSubcontracted] )
```

**`Empty Repositioning Ratio` is typically lower than `Deadhead %`** for the same
filter context. A short, wholly-empty repositioning leg counts as one leg out of
many in the leg-count-based ratio (diluted by every loaded leg with only a small
empty tail), but the *kilometres* it contributes are 100% empty by definition,
concentrating its full weight in the kilometre-based `Deadhead %` numerator. A
fleet running many short dedicated repositioning trips shows up more visibly in
`Deadhead %` (each trip is pure empty km) than in `Empty Repositioning Ratio`
(each trip is still just "one leg" among possibly many loaded ones), so the
kilometre-based measure tends to read higher when repositioning legs are
disproportionately short relative to loaded legs. Check this against your own
build's actual numbers rather than assuming the direction always holds; it depends
on the relative length distribution of the two leg populations.

---

## Exercise 17.4: Carrier Composite Score, re-scaled

Removing the single best-cost carrier (lowest `CostKm`) changes `MinCost` to the
*next*-lowest carrier's cost figure. Every remaining carrier's normalised cost
component, `1 - DIVIDE([CostKm] - MinCost, MaxCost - MinCost)`, is recomputed
against this new, narrower range, **every other carrier's cost-component score
shifts**, generally downward for carriers that were previously closer to the old
minimum (since they are now relatively less close to the new, higher minimum), even
though none of their own underlying cost data changed at all. This is min-max
normalisation's defining property: it is a *relative* scale, entirely a function of
the population currently in scope, so removing or adding one extreme member
re-scales everyone else's score without anyone else's raw numbers moving. This is
exactly the dictionary's own watch-out, proven directly rather than taken on faith:
never patch or compare one carrier's composite score in isolation across two
different carrier panels, the score is only meaningful within one fixed
comparison set.

---

## Reference values used above

| Quantity | Note |
|---|---|
| `FactTransportLeg` rows | 320,000 (contract) / ~437,125 (live build, README) |
| Pickup / delivery on-time windows | ±2h / ±4h |
| DIFOT correct vs product-of-marginals | joint > product; correlation between late and partial delivery is positive |
| Carrier score weights | 0.40 on-time / 0.25 first-attempt / 0.20 cost (inverted) / 0.15 subcon (inverted) |
