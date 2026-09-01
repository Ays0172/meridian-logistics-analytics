# Day 16: Ocean liner measures (22 KPIs)

> Time: 3.75 h · Spaced recall 10 min · Concept 15 min · Drill 190 min · Ship 30 min · Log 15 min

The heaviest single-domain day of the week, 22 KPIs, the domain the whole
curriculum has been circling since Week 1 Day 1. You already own the two hardest
mechanisms this domain needs: `CALCULATE` modifiers (Day 9) and the
naive-vs-correct discipline (Day 15). Today is mostly volume, applied with
discipline, not new concepts.

---

## Spaced recall (10 min, closed book)

1. State the `[KpiCode]` description convention from Day 15 and why the code
   matters more than the folder.
2. Why does `Revenue per FFE` deliberately exclude empty repositioning by
   construction, rather than filtering it out with a `CALCULATE` condition?
3. What is the fleet-mix reason `TEU Volume` and `FFE Volume` are not numerically
   comparable, even for the same containers?
4. Restate Day 9's four percentage-scope measures, which one would you use for
   "% of visual total that sums to 100% under a slicer"?
5. What did the naive/correct gap for `OCN.REL.SCHED` do across the full history
   versus inside the Jul–Sep 2025 congestion window, and why the difference?

---

## Concept

No new mechanism today: every measure below is `SUM`, `DIVIDE`, `AVERAGE`,
`AVERAGEX`, `MEDIANX`, `PERCENTILEX.INC`, or a `CALCULATE` filter, all from Weeks 1
and 2. The only new discipline is applying Day 15's method 22 times without letting
quality slip on KPI #19 the way it didn't on KPI #1. All 22 codes, DAX pulled
verbatim from `00_docs/KPI_DICTIONARY.md` §1, folder `05 Ocean Liner` for every
one, sub-foldered by function per Day 15's `Volume & Mix` / `Rate & Utilisation` /
`Revenue & Cost` / `Quality & Service` split - the code's own middle segment
(`VOL`, `REL`, `REV`, `QLT`...) tells you which.

**One naming note before you start:** `OCN.VOL.TEU` and `OCN.VOL.FFE` are already
shipped (Day 15). Do not rebuild them: confirm they're there, described, and move
on.

---

## Concept: the eight KPIs worked in full

### 1. Laden vs Empty Split: `OCN.MIX.LADEN`
```dax
Laden Share of TEU :=
VAR LadenTeu = CALCULATE ( SUM ( FactContainerMove[Teu] ), FactContainerMove[IsLaden] = 1 )
VAR TotalTeu = SUM ( FactContainerMove[Teu] )
RETURN DIVIDE ( LadenTeu, TotalTeu )
```
Validation gate (`SCHEMA_CONTRACT.md` §4): overall laden share 66–70%; backhaul
empty share 39–43%. Watch-out: `IsLaden`/`IsEmpty` are complementary on one row:
never sum both expecting 100% confirmation; `IsRepositioning` is a *subset* of
empty, not a synonym.

### 2. Headhaul / Backhaul Load Factor: `OCN.UTL.LF.HEAD` / `OCN.UTL.LF.BACK`
```dax
Headhaul Load Factor :=
VAR UsedTeu = CALCULATE ( SUM ( FactPortCall[SlotsUsedTeu] ), DimVoyage[Direction] = "Headhaul" )
VAR CapTeu  = CALCULATE ( SUM ( FactPortCall[SlotCapacityTeu] ), DimVoyage[Direction] = "Headhaul" )
RETURN DIVIDE ( UsedTeu, CapTeu )

Backhaul Load Factor :=
VAR UsedTeu = CALCULATE ( SUM ( FactPortCall[SlotsUsedTeu] ), DimVoyage[Direction] = "Backhaul" )
VAR CapTeu  = CALCULATE ( SUM ( FactPortCall[SlotCapacityTeu] ), DimVoyage[Direction] = "Backhaul" )
RETURN DIVIDE ( UsedTeu, CapTeu )
```
Gate: headhaul mean 0.88–0.96, backhaul 0.55–0.70. The dictionary's own naive
variant averages per-call ratios instead of pooling capacity-weighted sums, the
same shape of error as Day 9's `AVERAGEX` trap, wearing a load-factor costume. Ship
`[DO NOT USE] Headhaul Load Factor (naive)` beside it, same folder.
Watch-out: never blend headhaul and backhaul into one "average load factor." A
strong headhaul next to a weak backhaul is the *normal* state of a trade-imbalanced
network, not an anomaly to smooth over.

### 3. Slot Utilisation: `OCN.UTL.SLOT`
```dax
Slot Utilisation := DIVIDE ( SUM ( FactPortCall[SlotsUsedTeu] ), SUM ( FactPortCall[SlotCapacityTeu] ) )
```
Mathematically identical formula to load factor: the only difference is the
absence of a direction filter. Label the visual clearly: a reader who sees "slot
utilisation 91%" beside "backhaul load factor 61%" for the same service, with no
direction label on either, will think the numbers contradict each other.

### 4. Schedule Reliability: `OCN.REL.SCHED`, **the flagship trap**
Already shipped (Day 15), both variants. This is the KPI this whole project leads
with (`README` §6: network-wide **0.6598**), and it is worth restating *why* it's
the flagship: the naive/correct gap is small at the grand total and large inside
one nine-week window, which means a dashboard built and tested against
all-history data can pass every visual check and still be silently wrong the moment
someone filters to the exact period that matters most. If you only ship one naive
variant with real care this week, make it this one; every other naive trap in this
domain (load factor, moves-per-crane-hour, revenue per FFE) is a variation on the
same mechanism, but this is the one the project's own headline numbers depend on.

### 5. Rollover Ratio: `OCN.OPS.ROLL`
```dax
Rollover Ratio :=
VAR Rolled = CALCULATE ( COUNTROWS ( FactBooking ), FactBooking[IsRolled] = 1 )
VAR Base   = CALCULATE ( COUNTROWS ( FactBooking ), FactBooking[IsConfirmed] = 1 || FactBooking[IsRolled] = 1 )
RETURN DIVIDE ( Rolled, Base )
```
Baseline ~9%, rising to ~19% inside the congestion window. Watch-out: the
denominator is deliberately *confirmed-or-rolled* bookings, excluding cancellations
and no-shows; otherwise a cancellation spike would mechanically dilute rollover
and hide the real signal. Rollover ratio and cancellation rate get confused in
commentary constantly; keep them visibly separate.

### 6. Moves per Crane-Hour, Gross / Net: `OCN.OPS.MPCH.GROSS` / `.NET`
```dax
Moves per Crane-Hour Gross := DIVIDE ( SUM ( FactPortCall[TotalMoves] ), SUM ( FactPortCall[CraneHoursGross] ) )
Moves per Crane-Hour Net   := DIVIDE ( SUM ( FactPortCall[TotalMoves] ), SUM ( FactPortCall[CraneHoursNet] ) )
```
Second naive/correct pair this domain: `AVERAGE(FactPortCall[MovesPerCraneHourGross])`
is the naive shortcut: it averages a per-call ratio that was computed independently
per call, so a call with 2 crane-hours and one with 40 count equally. Ship
`[DO NOT USE] Moves per Crane-Hour Gross (naive)` too. Net compresses to ×0.72 of
baseline inside the congestion window even while gross can look flat; net is where
a terminal slowdown shows up first.

### 7. Container Port Dwell Hours: `OCN.OPS.DWELL`
```dax
Avg Container Dwell Hours :=
CALCULATE ( AVERAGE ( FactContainerMove[DwellHours] ), FactContainerMove[DwellHours] <> -1 )
```
Reuses Day 12's sentinel-filtering discipline directly: `-1` marks a container's
first-ever event (no prior dwell to measure), and omitting the `<> -1` filter
silently drags every average down, making yards look faster than they are: the
same shape of bug as `FactShipmentMilestone`'s `-1` milestone dates, now on a
different table.

### 8. Demurrage / Detention Revenue: `OCN.REV.DEM` / `OCN.REV.DET`
```dax
Demurrage Revenue := CALCULATE ( SUM ( FactFreightCharge[RevenueAmount_usd] ), FactFreightCharge[IsDemurrage] = 1 )
Detention Revenue  := CALCULATE ( SUM ( FactFreightCharge[RevenueAmount_usd] ), FactFreightCharge[IsDetention] = 1 )
```
Both fully additive, both rise sharply during the congestion window (charge-line
volume ×3.1) precisely *because* the operation is degrading: a rising number here
is a symptom, not a win. Never ship either on a "revenue" scorecard without the
operational context (`Avg Waiting for Berth Hours`, `Avg Container Dwell Hours`)
sitting next to it. Keep the two separate: they have different owners on the
customer side and different remediation levers; a blended "D&D revenue" line hides
that.

---

## Checklist: remaining 11 Ocean KPIs, same method

Complete these with the same six-step process from Day 15. DAX for every one
already exists verbatim in `KPI_DICTIONARY.md` §1, pull it, don't rederive it.

- [ ] `OCN.TRN.P50`, Transit Days P50: `MEDIANX(FactShipment, ActualTransitDays)`
- [ ] `OCN.TRN.P90`, Transit Days P90: `PERCENTILEX.INC(..., 0.9)`
- [ ] `OCN.TRN.VAR`, Mean Transit Variance Days + P90 Transit Variance Days (ship
      both together, per the dictionary's own "never one without the other" note)
- [ ] `OCN.OPS.TURN`, Avg Vessel Turnaround Hours: `AVERAGE(TurnaroundHours)`
- [ ] `OCN.OPS.WAIT`, Avg Waiting for Berth Hours (the congestion leading
      indicator, degrades before schedule reliability does)
- [ ] `OCN.REV.FFE`, already shipped Day 9/15, just confirm folder+description
- [ ] `OCN.REV.GP.FFE`, Gross Profit per FFE: `DIVIDE(SUM(GrossProfit_usd), SUM(Ffe))`
- [ ] `OCN.REV.BAF`, BAF Recovery Ratio (billed-vs-retained proxy; read the
      dictionary's watch-out on why this is *not* a bunker-cost-pass-through ratio
      before shipping the description)
- [ ] `OCN.OPS.FREETIME`, Free-Time Breach Rate + Avg Free-Time Consumption Ratio

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 16.1: the eight worked KPIs (75 min)
Build all measures from the eight worked sections above, including both naive
variants. Predict, before running, each pair's grand-total value and which will be
higher. For the two naive/correct pairs (load factor, moves per crane-hour),
predict the gap's rough size before checking, is it closer to the ~22% gap from
Day 9's `LPH Naive`, or closer to the near-zero gap from `Revenue per FFE Naive`?
Justify using the same correlation logic from Day 9: what is each ratio's
denominator, and is it a measure of effort/capacity or of demand?

### Exercise 16.2: the eleven checklist KPIs (75 min)
Build the remaining 11. For `OCN.TRN.P50`/`P90`, predict which is larger before
running, and roughly how far apart, given `SCHEMA_CONTRACT.md` §3.4's right-skewed
lognormal transit-variance distribution. For `OCN.OPS.FREETIME`, predict whether
`Avg Free-Time Consumption Ratio` should ever exceed 1.0 for a shipment that has
*not yet* breached free time, and check your model against that prediction.

### Exercise 16.3: the load-factor blend, proven wrong (20 min)
Build a deliberately bad `Overall Load Factor` measure by averaging your
`Headhaul Load Factor` and `Backhaul Load Factor` values with a simple `(x+y)/2` in
a card visual (not recomputed from pooled sums, literally average the two
already-computed ratios). Compare it against `Slot Utilisation` for the same
filter context. Predict, before checking, whether the two will match, and if not,
explain in one sentence which one is measuring the real network-wide slot fill and
which one is an artefact of blending two differently-sized populations.

### Exercise 16.4: congestion window stress test (20 min)
Filter every measure you built today to `14 Jul 2025 – 14 Sep 2025` at `NLRTM` and
`USLAX` only (`SCHEMA_CONTRACT.md` §3.3). Predict which three measures move the
*most* from their baseline (by relative %, not absolute units) before checking.
Confirm `Schedule Reliability Rolling 8wk` lands in the 0.28–0.34 band the contract
specifies for inside the window.

---

## Ship

`05 Ocean Liner` now holds all 22 KPIs (or a clean checklist of what's left, logged
in your notes if you ran short on time, do not ship a half-built domain silently),
each in its function subfolder. Every naive variant named `[DO NOT USE]`, every
measure described with its `[KpiCode]` prefix.

```
git add .
git commit -m "Day 16: Ocean liner measure library, 22 KPIs, naive/correct pairs marked"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] All 22 Ocean KPIs exist in `05 Ocean Liner`, each in its function subfolder
      per Day 15 and described with its `[KpiCode]`.
- [ ] Both naive/correct pairs (`OCN.REL.SCHED`, `OCN.UTL.LF.HEAD`,
      `OCN.OPS.MPCH.GROSS`) are shipped side by side, naive ones named
      `[DO NOT USE]`.
- [ ] You can state, from your own numbers, `Schedule Reliability Rolling 8wk`
      inside vs outside the congestion window, and explain why the naive version's
      error is worse specifically inside that window.
- [ ] `Overall Load Factor` (the deliberately bad blend) does not match
      `Slot Utilisation`, and you can explain why in one sentence.
- [ ] Predictions recorded, misses annotated.
