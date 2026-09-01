# Day 16: solutions

---

## Spaced recall answers

1. `[KpiCode] <definition>. <watch-out>.` The code is the join key back to
   `KPI_DICTIONARY.md`; the folder can be renamed or reorganised freely (it's a
   string), but the code is what makes the measure traceable to its authoritative
   source and its target band regardless of where it lives in the Fields pane.
2. Because empty repositioning moves have no `ShipmentKey`/`Revenue_usd` row at
   all, there is nothing to filter out, the population simply excludes them by
   the structure of the fact table. Filtering with `CALCULATE` would be redundant
   and would incorrectly imply an empty move *could* have appeared in the
   numerator or denominator if not excluded.
3. A 20' box is `1.0` TEU but only `0.5` FFE; a 40'/45' box is `2.0`/`2.25` TEU but
   `1.0`/`1.125` FFE. The two units use different conversion factors for the same
   physical container, so summing either one for a fleet with a mixed 20'/40' mix
   produces numbers that are not proportional to each other by any single constant.
4. `Pct of Grand Total` (ignores every filter, `REMOVEFILTERS`), `Pct of Visual
   Total` (`ALLSELECTED`, sums to 100% under a slicer: this is the one), `Pct of
   Trade Lane` and `Pct of Customer` (`ALLEXCEPT`, share-of-parent).
5. Across the full history the gap was small (both methods average roughly
   comparable weekly call volumes most of the time); inside the 9-week congestion
   window the gap widens sharply because call volume and on-time rate move together
   during exactly the period the naive method assumes is stable, the naive
   method's error grows precisely when the correlation between the per-week rate
   and that week's sample size stops being negligible.

---

## Exercise 16.1: the eight worked KPIs

```dax
Laden Share of TEU :=
VAR LadenTeu = CALCULATE ( SUM ( FactContainerMove[Teu] ), FactContainerMove[IsLaden] = 1 )
VAR TotalTeu = SUM ( FactContainerMove[Teu] )
RETURN DIVIDE ( LadenTeu, TotalTeu )
```
Expect this in the **66–70%** validation-gate band (`SCHEMA_CONTRACT.md` §4).

```dax
Headhaul Load Factor :=
VAR UsedTeu = CALCULATE ( SUM ( FactPortCall[SlotsUsedTeu] ), DimVoyage[Direction] = "Headhaul" )
VAR CapTeu  = CALCULATE ( SUM ( FactPortCall[SlotCapacityTeu] ), DimVoyage[Direction] = "Headhaul" )
RETURN DIVIDE ( UsedTeu, CapTeu )

Backhaul Load Factor :=
VAR UsedTeu = CALCULATE ( SUM ( FactPortCall[SlotsUsedTeu] ), DimVoyage[Direction] = "Backhaul" )
VAR CapTeu  = CALCULATE ( SUM ( FactPortCall[SlotCapacityTeu] ), DimVoyage[Direction] = "Backhaul" )
RETURN DIVIDE ( UsedTeu, CapTeu )

[DO NOT USE] Headhaul Load Factor (naive) :=
CALCULATE (
    AVERAGEX ( FactPortCall, DIVIDE ( FactPortCall[SlotsUsedTeu], FactPortCall[SlotCapacityTeu] ) ),
    RELATED ( DimVoyage[Direction] ) = "Headhaul"
)
```
Expect headhaul in **0.88–0.96**, backhaul in **0.55–0.70**. The naive/correct gap
here should sit **closer to the LPH pattern (~15–25%) than to Revenue-per-FFE's
near-zero gap**, the denominator, `SlotCapacityTeu`, is a measure of vessel
*capacity*, and capacity varies enormously call-to-call (a 2,000-TEU feeder next to
a 20,000-TEU ULCV on the same service). That is exactly the "effort/capacity
denominator" family Day 9 flagged as dangerous: small-ship calls get equal vote
with large-ship calls in the naive average, dragging the naive figure toward
whichever vessel class is more numerous rather than toward the capacity-weighted
truth.

```dax
Moves per Crane-Hour Gross := DIVIDE ( SUM ( FactPortCall[TotalMoves] ), SUM ( FactPortCall[CraneHoursGross] ) )
[DO NOT USE] Moves per Crane-Hour Gross (naive) := AVERAGE ( FactPortCall[MovesPerCraneHourGross] )
```
Same family as load factor, `CraneHoursGross` is an effort/duration denominator,
so expect a meaningful naive gap here too, though generally smaller than the load
factor gap since crane productivity is comparatively less variable across vessel
classes than raw slot capacity is.

```dax
Slot Utilisation := DIVIDE ( SUM ( FactPortCall[SlotsUsedTeu] ), SUM ( FactPortCall[SlotCapacityTeu] ) )
Avg Container Dwell Hours := CALCULATE ( AVERAGE ( FactContainerMove[DwellHours] ), FactContainerMove[DwellHours] <> -1 )
Demurrage Revenue := CALCULATE ( SUM ( FactFreightCharge[RevenueAmount_usd] ), FactFreightCharge[IsDemurrage] = 1 )
Detention Revenue  := CALCULATE ( SUM ( FactFreightCharge[RevenueAmount_usd] ), FactFreightCharge[IsDetention] = 1 )

Rollover Ratio :=
VAR Rolled = CALCULATE ( COUNTROWS ( FactBooking ), FactBooking[IsRolled] = 1 )
VAR Base   = CALCULATE ( COUNTROWS ( FactBooking ), FactBooking[IsConfirmed] = 1 || FactBooking[IsRolled] = 1 )
RETURN DIVIDE ( Rolled, Base )
```
Rollover baseline ≈**9%**, rising to ≈**19%** filtered to the congestion window.

---

## Exercise 16.2: the eleven checklist KPIs

```dax
Transit Days P50 := MEDIANX ( FactShipment, FactShipment[ActualTransitDays] )
Transit Days P90 := PERCENTILEX.INC ( FactShipment, FactShipment[ActualTransitDays], 0.9 )

Mean Transit Variance Days := AVERAGE ( FactShipment[TransitVarianceDays] )
P90 Transit Variance Days  := PERCENTILEX.INC ( FactShipment, FactShipment[TransitVarianceDays], 0.9 )

Avg Vessel Turnaround Hours   := AVERAGE ( FactPortCall[TurnaroundHours] )
Avg Waiting for Berth Hours   := AVERAGE ( FactPortCall[WaitingForBerthHours] )

Gross Profit per FFE := DIVIDE ( SUM ( FactShipment[GrossProfit_usd] ), SUM ( FactShipment[Ffe] ) )

BAF Recovery Ratio :=
VAR BilledBaf = CALCULATE ( SUM ( FactFreightCharge[RevenueAmount_usd] ), RELATED ( DimChargeType[ChargeCode] ) = "BAF" )
VAR RetainedBaf =
    CALCULATE (
        SUM ( FactFreightCharge[RevenueAmount_usd] ),
        RELATED ( DimChargeType[ChargeCode] ) = "BAF",
        FactFreightCharge[SettlementStatus] <> "Written Off"
    )
RETURN DIVIDE ( RetainedBaf, BilledBaf )

Free-Time Breach Rate :=
DIVIDE (
    CALCULATE ( COUNTROWS ( FactContainerMove ), FactContainerMove[IsPastFreeTime] = 1 ),
    COUNTROWS ( FactContainerMove )
)

Avg Free-Time Consumption Ratio :=
AVERAGEX (
    FactContainerMove,
    DIVIDE ( FactContainerMove[FreeTimeDaysUsed], RELATED ( DimEquipment[FreeDaysDemurrage] ) )
)
```

**P90 is larger than P50, and substantially so**, given the lognormal(μ=0.9,
σ=0.65) right-skew on transit variance (`SCHEMA_CONTRACT.md` §3.4), the gap between
P50 and P90 should be several days wide, wider than a symmetric distribution would
predict at the same variance. This is the KPI dictionary's own point: the P50–P90
spread is itself the planning-relevant number, not either percentile alone.

**`Avg Free-Time Consumption Ratio` can exceed 1.0** even for moves that have not
yet formally breached free time in the `IsPastFreeTime` flag sense, because
`FreeTimeDaysUsed` and the breach flag are computed independently, a move can be
mid-way through accumulating days at the moment of measurement without yet having
crossed the field's own breach threshold in this particular snapshot of the data,
or the ratio can slightly exceed 1.0 due to how `FreeTimeDaysUsed` is measured
relative to the exact free-day allowance. Values consistently sitting near or above
1.0 for a lane or customer are the early-warning signal the dictionary's
watch-out describes, a lane whose consumption ratio sits above ~0.8 on average is
already trending toward routine demurrage even before the breach rate itself moves.

---

## Exercise 16.3: the load-factor blend, proven wrong

`(Headhaul Load Factor + Backhaul Load Factor) / 2` does **not** match
`Slot Utilisation`, and should not be expected to. `Slot Utilisation` pools *all*
`SlotsUsedTeu` and `SlotCapacityTeu` across both directions before dividing, it is
weighted by each direction's actual capacity share of the network. The naive blend
gives headhaul and backhaul equal 50/50 weight regardless of how much of the fleet's
total slot capacity each direction actually represents. Since headhaul and backhaul
capacity are not equally sized in a typical trade-imbalanced network, the simple
average is systematically pulled away from the true pooled utilisation. This is
the averaging trap again, at the level of two pre-aggregated ratios instead of many
row-level ones, which is exactly why the correct `Slot Utilisation` measure is
built from pooled `SUM`s, not from combining `Headhaul Load Factor` and
`Backhaul Load Factor` after the fact.

---

## Exercise 16.4: congestion window stress test

Filtered to `14 Jul 2025 – 14 Sep 2025` at `NLRTM`/`USLAX` (`SCHEMA_CONTRACT.md`
§3.3), the three largest relative movers should be:

| Measure | Contract-specified shock |
|---|---|
| `Avg Waiting for Berth Hours` | **×3.4** |
| Demurrage charge-line volume (`Demurrage Revenue`'s underlying line count) | **×3.1** |
| Container `Avg Container Dwell Hours` at those ports | **×2.6** |

`Schedule Reliability Rolling 8wk`, filtered to the same window, should land in the
**0.28–0.34** band the contract specifies, a sharp drop from the network baseline
of 0.6598 (`README` §6), consistent with `IsOnTimeArrival` moving from 0.68 to 0.31
per the contract's own behavioural spec. `Avg Vessel Turnaround Hours` (×1.9) and
`Moves per Crane-Hour Net` (×0.72, i.e. a *fall*, not a rise) are the next-largest
movers, worth naming if your own top-three differs, since "which three moved most"
depends slightly on the exact filter scope and baseline period chosen for
comparison.

---

## Reference values used above

| Quantity | Value |
|---|---|
| Laden share (gate) | 66–70% |
| Headhaul / backhaul load factor (gate) | 0.88–0.96 / 0.55–0.70 |
| Rollover baseline / congestion-window | ~9% / ~19% |
| Schedule reliability, network / congestion-window | 0.6598 / 0.28–0.34 |
| `IsOnTimeArrival`, outside / inside congestion window | 0.68 / 0.31 |
| Waiting-for-berth / dwell / demurrage-volume shock | ×3.4 / ×2.6 / ×3.1 |
| Turnaround / moves-per-crane-hour-net shock | ×1.9 / ×0.72 |
