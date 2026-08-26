# Meridian Global Logistics — KPI Dictionary v1.0

**Status:** companion artefact to `00_docs/SCHEMA_CONTRACT.md` (frozen). Every KPI below is computable
from that contract's exact table and column names. `FactTarget.KpiCode` must draw from the `Code`
column of the summary table — do not invent codes elsewhere.

Conventions used throughout: money in `_usd`; `DIVIDE()` used for every ratio so a zero denominator
returns blank, not an error; "Grain" states the lowest level at which the number is *meaningful*, and
whether summing/averaging across a higher grain is safe (**additive**), safe only along the time axis
(**semi-additive**), or actively wrong (**non-additive** — must always be *recomputed* from its
numerator and denominator at the new grain, never averaged).

---

## 0. Summary table — the interview flashcard sheet

| Code | Name | Domain | Grain | Additive? | Owner |
|---|---|---|---|---|---|
| OCN.VOL.TEU | TEU Volume | Ocean | Voyage leg / port call / period | Additive | Network Ops |
| OCN.VOL.FFE | FFE Volume | Ocean | Voyage leg / period | Additive | Network Ops |
| OCN.MIX.LADEN | Laden vs Empty Split | Ocean | Move / leg / period | Non-additive (ratio) | Network Ops |
| OCN.UTL.LF.HEAD | Headhaul Load Factor | Ocean | Voyage leg / service / period | Non-additive (ratio) | Network Ops |
| OCN.UTL.LF.BACK | Backhaul Load Factor | Ocean | Voyage leg / service / period | Non-additive (ratio) | Network Ops |
| OCN.UTL.SLOT | Slot Utilisation | Ocean | Port call / period | Non-additive (ratio) | Network Ops |
| OCN.REL.SCHED | Schedule Reliability (rolling 8-week) | Ocean | Service / port pair, trailing 56 days | Non-additive (ratio) | Network Ops |
| OCN.TRN.P50 | Port-to-Port Transit P50 | Ocean | Trade lane / period | Non-additive (statistic) | Trade Management |
| OCN.TRN.P90 | Port-to-Port Transit P90 | Ocean | Trade lane / period | Non-additive (statistic) | Trade Management |
| OCN.TRN.VAR | Transit Variance vs Promise | Ocean | Shipment / lane / period | Non-additive (ratio) | Trade Management |
| OCN.OPS.TURN | Vessel Turnaround Hours | Ocean | Port call | Non-additive (average) | Network Ops |
| OCN.OPS.WAIT | Waiting-for-Berth Hours | Ocean | Port call | Non-additive (average) | Network Ops |
| OCN.OPS.MPCH.GROSS | Moves per Crane-Hour (Gross) | Ocean | Port call / terminal / period | Non-additive (ratio) | Network Ops |
| OCN.OPS.MPCH.NET | Moves per Crane-Hour (Net) | Ocean | Port call / terminal / period | Non-additive (ratio) | Network Ops |
| OCN.OPS.DWELL | Container Port Dwell Hours | Ocean | Container move / location | Non-additive (average) | Network Ops |
| OCN.OPS.ROLL | Rollover Ratio | Ocean | Booking / service / period | Non-additive (ratio) | Trade Management |
| OCN.REV.FFE | Revenue per FFE | Ocean | Shipment / lane / period | Non-additive (weighted ratio) | Commercial |
| OCN.REV.GP.FFE | Gross Profit per FFE | Ocean | Shipment / lane / period | Non-additive (weighted ratio) | Commercial |
| OCN.REV.BAF | BAF Recovery Ratio | Ocean | Shipment / lane / period | Non-additive (ratio) | Finance |
| OCN.REV.DEM | Demurrage Revenue | Ocean | Charge line / period | Additive | Finance |
| OCN.REV.DET | Detention Revenue | Ocean | Charge line / period | Additive | Finance |
| OCN.OPS.FREETIME | Free-Time Consumption Rate | Ocean | Container move / equipment type | Non-additive (ratio) | Network Ops |
| LND.CST.KM | Cost per km | Landside | Leg / lane / period | Non-additive (weighted ratio) | Inland Ops |
| LND.CST.MOVE | Cost per Container Move | Landside | Leg / period | Non-additive (weighted ratio) | Inland Ops |
| LND.OPS.TURN | Drayage Turn Time | Landside | Leg / site | Non-additive (average) | Inland Ops |
| LND.SVC.OTP | On-Time Pickup | Landside | Leg / carrier / period | Non-additive (ratio) | Inland Ops |
| LND.SVC.OTD | On-Time Delivery | Landside | Leg / carrier / period | Non-additive (ratio) | Inland Ops |
| LND.SVC.DIFOT | DIFOT | Landside | Leg / customer / period | Non-additive (ratio) | Inland Ops |
| LND.UTL.DEADHEAD | Deadhead Percentage | Landside | Leg / carrier / period | Non-additive (weighted ratio) | Inland Ops |
| LND.UTL.EMPTYREPO | Empty Repositioning Ratio | Landside | Leg / carrier / period | Non-additive (ratio) | Inland Ops |
| LND.UTL.TRUCK | Truck Utilisation | Landside | Carrier / fleet / period | Non-additive (ratio) | Inland Ops |
| LND.SVC.FAD | First-Attempt Delivery Rate | Landside | Leg / carrier / period | Non-additive (ratio) | Inland Ops |
| LND.REV.FSC | Fuel Surcharge Recovery | Landside | Leg / period | Non-additive (ratio) | Finance |
| LND.CST.ACC | Accessorial Cost Ratio | Landside | Leg / period | Non-additive (ratio) | Finance |
| LND.CAR.SCORE | Carrier Composite Score | Landside | Carrier / period | Non-additive (weighted index) | Inland Ops |
| LND.OPS.DET | Detention at Site Hours | Landside | Leg / site | Non-additive (average) | Inland Ops |
| LND.SUS.CO2 | CO2 per Tonne-km | Landside | Leg / period | Non-additive (weighted ratio) | Inland Ops |
| LND.OPS.SUBCON | Subcontracting Ratio | Landside | Leg / carrier / period | Non-additive (ratio) | Inland Ops |
| WHS.OPS.D2S | Dock-to-Stock Minutes | Warehouse | Task / warehouse | Non-additive (average) | Site Ops |
| WHS.QLT.INVACC | Inventory Accuracy | Warehouse | Snapshot / SKU / warehouse | Non-additive (ratio) | Site Ops |
| WHS.QLT.PICKACC | Pick Accuracy | Warehouse | Task / warehouse / period | Non-additive (ratio) | Site Ops |
| WHS.OPS.OCT | Order Cycle Time | Warehouse | Order / warehouse | Non-additive (average) | Site Ops |
| WHS.PRD.LPH | Lines per Labour Hour | Warehouse | Task / employee / shift | Non-additive (weighted ratio) | Site Ops |
| WHS.PRD.UPH | Units per Labour Hour | Warehouse | Task / employee / shift | Non-additive (weighted ratio) | Site Ops |
| WHS.CST.LCPL | Labour Cost per Line | Warehouse | Task / warehouse / period | Non-additive (weighted ratio) | Finance |
| WHS.UTL.PALLET | Pallet Position Utilisation | Warehouse | Snapshot / warehouse / day | Semi-additive (over date) | Site Ops |
| WHS.UTL.CUBE | Cube Utilisation | Warehouse | Snapshot / warehouse / day | Semi-additive (over date) | Site Ops |
| WHS.QLT.PERFECT | Perfect Order Rate (warehouse-touched) | Warehouse | Shipment / warehouse / period | Non-additive (ratio) | Site Ops |
| WHS.QLT.OTIF | OTIF (DIF × DOQ × DOT) | Warehouse | Shipment / customer / period | Non-additive (multiplicative ratio) | Site Ops |
| WHS.INV.TURNS | Inventory Turns | Warehouse | SKU / warehouse / period (annualised) | Non-additive (ratio) | Site Ops |
| WHS.INV.DOH | Days on Hand | Warehouse | SKU / warehouse / period | Non-additive (inverse ratio) | Site Ops |
| WHS.INV.ABC | ABC Class Mix | Warehouse | SKU / warehouse / period | Non-additive (distribution) | Site Ops |
| WHS.QLT.SHRINK | Shrinkage Rate | Warehouse | Snapshot / SKU / period | Semi-additive numerator / non-additive ratio | Site Ops |
| WHS.INV.OBS | Obsolete Stock Ratio | Warehouse | Snapshot / SKU / warehouse | Semi-additive numerator / non-additive ratio | Site Ops |
| WHS.QLT.STOCKOUT | Stockout Rate | Warehouse | Snapshot / SKU / warehouse | Non-additive (ratio) | Site Ops |
| WHS.QLT.REWORK | Rework Rate | Warehouse | Task / warehouse / period | Non-additive (ratio) | Site Ops |
| ALC.WT.CHG6000 | Chargeable Weight — Air 1:6000 | Air & LCL | Shipment | Additive (as precomputed kg) | Trade Management |
| ALC.WT.CHG5000 | Chargeable Weight — Air 1:5000 variant | Air & LCL | Shipment | Additive (as precomputed kg) | Trade Management |
| ALC.WT.RT1000 | Ocean LCL Revenue Tons — 1:1000 | Air & LCL | Shipment | Additive (as precomputed RT) | Trade Management |
| ALC.REV.YIELDKG | Yield per kg | Air & LCL | Shipment / lane / period | Non-additive (weighted ratio) | Commercial |
| ALC.SLS.CONV | Quote-to-Book Conversion | Air & LCL | Quote / period | Non-additive (ratio) | Commercial |
| ALC.REV.GPHBL | Gross Profit per House Bill | Air & LCL | Shipment / period | Non-additive (weighted ratio) | Commercial |
| ALC.CST.MODAL | Air vs Ocean Modal Cost Comparison | Air & LCL | Lane / period | Non-additive (index) | Commercial |
| ALC.TRN.MODAL | Modal Transit-Time Comparison | Air & LCL | Lane / period | Non-additive (statistic) | Commercial |
| ALC.WT.VOLMIX | Volumetric-vs-Actual Weight Mix | Air & LCL | Shipment / period | Non-additive (ratio) | Trade Management |
| XCT.SCOR.MAP | SCOR Level-1 Attribute Map | Cross-cutting | KPI catalogue (framework) | N/A (classification) | Commercial |
| XCT.QLT.PERFECT | Perfect Order Rate (company-wide) | Cross-cutting | Shipment / period | Non-additive (ratio) | Commercial |
| XCT.FIN.C2C | Cash-to-Cash Cycle Time | Cross-cutting | Company / period | Non-additive (sum of non-additive components) | Finance |
| XCT.FIN.FCR | Freight Cost as % of Revenue | Cross-cutting | Company / customer / period | Non-additive (ratio) | Finance |
| XCT.FIN.CTS | Cost to Serve per Customer | Cross-cutting | Customer / period | Additive (numerator), non-additive per-customer average | Finance |
| XCT.CUS.CONC | Revenue Concentration (Top-10 Share) | Cross-cutting | Company / period | Non-additive (ratio) | Commercial |
| XCT.FIN.MARGDISP | Margin Dispersion | Cross-cutting | Shipment / period | Non-additive (statistic) | Finance |

<!-- SECTION:OCEAN -->

---

## 1. Ocean liner (22)

### OCN.VOL.TEU — TEU Volume
**Definition.** Total container throughput expressed in twenty-foot equivalent units.
**Formula.** `Σ Teu`. Convention: **includes** empty repositioning by default (gross box-flow), because vessel/terminal capacity planning must account for every slot occupied, not only revenue cargo. Use `OCN.MIX.LADEN` to isolate the laden-only cut.
**Grain.** Any grain (move, port, voyage, day) — **additive**. A round trip legitimately contributes twice (laden outbound + empty/laden return are separate `ContainerMoveKey` rows) — that is correct, not double-counting, but do not mistake "TEU moved" for "unique containers handled."
**Source.** `FactContainerMove.Teu`, `EventDateKey`, `LocationKey`, `VoyageKey`, `ModeKey`.
**DAX.**
```dax
TEU Volume := SUM ( FactContainerMove[Teu] )

Laden TEU Volume :=
CALCULATE ( SUM ( FactContainerMove[Teu] ), FactContainerMove[IsLaden] = 1 )
```
**Target/benchmark.** Directional only — compare to `FactTarget` budget (`TargetUnit = "TEU"`); no universal industry band exists for absolute volume.
**Owner.** Network Ops.
**Watch-out.** Never build a *rate* by dividing two TEU sums pulled from different grains (e.g., a per-voyage TEU/day figure averaged across voyages of different loop length) — recompute the ratio at the grain you need, every time.

### OCN.VOL.FFE — FFE Volume
**Definition.** Total container throughput in forty-foot equivalent units — the billing-oriented sibling of TEU.
**Formula.** `Σ Ffe`. Same laden+empty convention as TEU.
**Grain.** Any grain — **additive**, subject to the same round-trip note as TEU.
**Source.** `FactContainerMove.Ffe`.
**DAX.**
```dax
FFE Volume := SUM ( FactContainerMove[Ffe] )
```
**Target/benchmark.** Directional, vs `FactTarget` budget.
**Owner.** Network Ops.
**Watch-out.** A 20' box is `0.5` FFE but `1.0` TEU — TEU and FFE totals for the *same* fleet are never numerically comparable; report them side by side, never as a combined figure.

### OCN.MIX.LADEN — Laden vs Empty Split
**Definition.** Share of container moves carrying revenue cargo versus moving empty.
**Formula.** `Σ Teu [IsLaden=1] ÷ Σ Teu [all]`.
**Grain.** Move / leg / period — **non-additive**; recompute at every grain, never average a pre-computed daily laden-share across days.
**Source.** `FactContainerMove.Teu`, `IsLaden`, `IsEmpty`, `IsRepositioning`.
**DAX.**
```dax
Laden Share of TEU :=
VAR LadenTeu = CALCULATE ( SUM ( FactContainerMove[Teu] ), FactContainerMove[IsLaden] = 1 )
VAR TotalTeu = SUM ( FactContainerMove[Teu] )
RETURN DIVIDE ( LadenTeu, TotalTeu )
```
**Target/benchmark.** Contract validation gate: overall laden share 66–70%; backhaul empty share 39–43% (`SCHEMA_CONTRACT.md` §4).
**Owner.** Network Ops.
**Watch-out.** `IsLaden`/`IsEmpty` are complementary on one row — never sum both expecting confirmation of 100%. `IsRepositioning` is a *subset* of empty moves (empties being actively repositioned to a deficit port), not a synonym for `IsEmpty`.

### OCN.UTL.LF.HEAD — Headhaul Load Factor
**Definition.** Share of headhaul vessel slot capacity actually filled with containers.
**Formula.** `Σ SlotsUsedTeu ÷ Σ SlotCapacityTeu`, filtered to `DimVoyage.Direction = "Headhaul"`.
**Grain.** Voyage leg / service / period — **non-additive**; must be capacity-weighted, never averaged.
**Source.** `FactPortCall.SlotsUsedTeu`, `SlotCapacityTeu`, `VoyageKey` → `DimVoyage.Direction`.
**DAX.**
```dax
-- NAÏVE (wrong)
Headhaul Load Factor (naive) :=
CALCULATE (
    AVERAGEX ( FactPortCall, DIVIDE ( FactPortCall[SlotsUsedTeu], FactPortCall[SlotCapacityTeu] ) ),
    RELATED ( DimVoyage[Direction] ) = "Headhaul"
)
-- WRONG: averages one ratio per port call, so a 2,000-TEU feeder call and a 20,000-TEU
-- ULCV call get equal weight — small-ship noise dominates the headline number.

-- CORRECT
Headhaul Load Factor :=
VAR UsedTeu = CALCULATE ( SUM ( FactPortCall[SlotsUsedTeu] ), DimVoyage[Direction] = "Headhaul" )
VAR CapTeu  = CALCULATE ( SUM ( FactPortCall[SlotCapacityTeu] ), DimVoyage[Direction] = "Headhaul" )
RETURN DIVIDE ( UsedTeu, CapTeu )
```
**Target/benchmark.** Contract validation gate: mean 0.88–0.96 (`SCHEMA_CONTRACT.md` §3.2, §4).
**Owner.** Network Ops.
**Watch-out.** Averaging per-call ratios instead of pooling capacity-weighted sums is the single most common load-factor error — it silently overweights small tonnage.

### OCN.UTL.LF.BACK — Backhaul Load Factor
**Definition.** Same construct as headhaul, filtered to the return leg of the trade.
**Formula.** `Σ SlotsUsedTeu ÷ Σ SlotCapacityTeu` where `DimVoyage.Direction = "Backhaul"`.
**Grain.** Voyage leg / service / period — **non-additive**, capacity-weighted only.
**Source.** Same as OCN.UTL.LF.HEAD.
**DAX.**
```dax
Backhaul Load Factor :=
VAR UsedTeu = CALCULATE ( SUM ( FactPortCall[SlotsUsedTeu] ), DimVoyage[Direction] = "Backhaul" )
VAR CapTeu  = CALCULATE ( SUM ( FactPortCall[SlotCapacityTeu] ), DimVoyage[Direction] = "Backhaul" )
RETURN DIVIDE ( UsedTeu, CapTeu )
```
**Target/benchmark.** Contract validation gate: mean 0.55–0.70; backhaul empty share ~41% (§3.2, §4).
**Owner.** Network Ops.
**Watch-out.** A healthy headhaul number next to a weak backhaul number is the *normal* state of a trade-imbalanced network, not an anomaly — never blend the two into one "average load factor" for the service, it destroys the commercial signal.

### OCN.UTL.SLOT — Slot Utilisation
**Definition.** Network-wide slot fill rate, without splitting by trade direction — the terminal/vessel-productivity lens rather than the commercial trade-balance lens.
**Formula.** `Σ SlotsUsedTeu ÷ Σ SlotCapacityTeu` across all port calls in scope.
**Grain.** Port call / period — **non-additive**.
**Source.** `FactPortCall.SlotsUsedTeu`, `SlotCapacityTeu`.
**DAX.**
```dax
Slot Utilisation := DIVIDE ( SUM ( FactPortCall[SlotsUsedTeu] ), SUM ( FactPortCall[SlotCapacityTeu] ) )
```
**Target/benchmark.** Directional, typically tracked in the high-80s to mid-90s for well-scheduled services.
**Owner.** Network Ops.
**Watch-out.** Mathematically identical formula to load factor — the only difference is the filter context (direction-split vs not). Label the visual clearly; a reader who sees "slot utilisation 91%" next to "backhaul load factor 61%" for the same service without a direction label will think the numbers contradict each other.

### OCN.REL.SCHED — Schedule Reliability (±1-day rule, rolling 8-week)
**Definition.** Share of vessel port calls that arrived within one calendar day of the *originally published* ETA, measured over a trailing 8-week (56-day) window — the industry-standard construct used by Sea-Intelligence and reported by carriers/analysts such as Xeneta.
**Formula.** `COUNT(port calls WHERE IsOnTimeArrival=1, in trailing 56 days) ÷ COUNT(port calls, in trailing 56 days)`, where `IsOnTimeArrival` already encodes `abs(ATA − PromisedETA) ≤ 24h` against the **never-revised** `PromisedEtaDateKey`/`PromisedEtaTs` — never the `RevisedEtaDateKey`. Source: "A vessel is considered on time if it arrives within one calendar day before or after its scheduled ETA" — [Xeneta, Schedule reliability documentation](https://help.xeneta.com/docs/schedule-reliability).
**Grain.** Service / port pair, trailing 56-day window — **non-additive**; the ratio must be recomputed for every window and every filter combination, never averaged from sub-windows.
**Source.** `FactPortCall.IsOnTimeArrival`, `PromisedEtaDateKey` (active relationship to `DimDate`), `AtaTs`, `PromisedEtaTs`.
**DAX.**
```dax
-- NAÏVE (wrong)
Schedule Reliability Rolling 8wk (naive) :=
AVERAGEX (
    VALUES ( DimDate[ISOWeekLabel] ),
    CALCULATE ( AVERAGE ( FactPortCall[IsOnTimeArrival] ) )
)
-- WRONG: averages 8 already-aggregated weekly rates with equal weight. A quiet week with
-- 40 calls and a busy week with 400 calls count the same — this is averaging an average,
-- the classic error, and it drifts further from the true pooled rate as call volume varies
-- week to week (exactly what happens inside the congestion window, §3.3).

-- CORRECT
Schedule Reliability Rolling 8wk :=
VAR LastDate = MAX ( DimDate[Date] )
VAR WindowStart = LastDate - 55                        -- 56 days inclusive = 8 weeks
VAR CallsInWindow =
    CALCULATETABLE (
        FactPortCall,
        DATESBETWEEN ( DimDate[Date], WindowStart, LastDate )
    )
RETURN
    DIVIDE (
        COUNTROWS ( FILTER ( CallsInWindow, FactPortCall[IsOnTimeArrival] = 1 ) ),
        COUNTROWS ( CallsInWindow )
    )
```
**Target/benchmark.** Global carrier average has run 55–70% through 2025–2026 per Sea-Intelligence's Global Liner Performance series (directional, not a fixed target) — [Sea-Intelligence press room](https://www.sea-intelligence.com/press-room/348-global-schedule-reliability-stable-at-65-68-since-may-2025). This project's own validation gate: 0.62–0.70 outside the congestion window, 0.28–0.34 inside it (14 Jul–14 Sep 2025 at `NLRTM`/`USLAX`, `SCHEMA_CONTRACT.md` §3.3–§4).
**Owner.** Network Ops.
**Watch-out.** Two traps stack here: (1) using `RevisedEtaDateKey` instead of the frozen `PromisedEtaDateKey` flatters the number — a carrier that quietly re-publishes its ETA the day before arrival "achieves" reliability it didn't earn; (2) treating the rolling window as calendar-month buckets instead of a true trailing 56 days misaligns the number every time the reporting date crosses a month boundary.

### OCN.TRN.P50 — Port-to-Port Transit P50
**Definition.** Median actual transit time on a trade lane — the typical experience, robust to the outliers that a mean would chase.
**Formula.** `MEDIAN(ActualTransitDays)` per lane / period.
**Grain.** Lane / period — **non-additive statistic**; never average lane-level medians across lanes to get a "network median."
**Source.** `FactShipment.ActualTransitDays`, `LocationKeyPol`, `LocationKeyPod`, `ServiceKey`.
**DAX.**
```dax
Transit Days P50 := MEDIANX ( FactShipment, FactShipment[ActualTransitDays] )
```
**Target/benchmark.** Directional; compare to `DimService.NominalTransitDays` for the same service.
**Owner.** Trade Management.
**Watch-out.** Because transit-time is right-skewed (lognormal add-on per `SCHEMA_CONTRACT.md` §3.4), P50 sits noticeably below the mean — quoting the mean as "typical transit" overstates what most shipments experience.

### OCN.TRN.P90 — Port-to-Port Transit P90
**Definition.** The transit time that 90% of shipments beat — the number a planner should build safety stock against, not the median.
**Formula.** `PERCENTILE.INC(ActualTransitDays, 0.90)` per lane / period.
**Grain.** Lane / period — **non-additive statistic**.
**Source.** `FactShipment.ActualTransitDays`.
**DAX.**
```dax
Transit Days P90 := PERCENTILEX.INC ( FactShipment, FactShipment[ActualTransitDays], 0.9 )
```
**Target/benchmark.** Directional; the gap between P50 and P90 is itself the KPI planners care about (tail risk), typically several days wide on congested lanes.
**Owner.** Trade Management.
**Watch-out.** Right-skew (§3.4) means P90 sits *far* right of P50 — a lane with a "good" median can still have a dangerous P90. Never substitute mean+1 standard deviation for a true percentile on this distribution; the normal approximation understates the tail.

### OCN.TRN.VAR — Transit Variance vs Promise
**Definition.** How far actual transit deviated from the planned/promised transit days, on average and in the tail.
**Formula.** `AVERAGE(TransitVarianceDays)` where `TransitVarianceDays = ActualTransitDays − PlannedTransitDays` (pre-computed).
**Grain.** Shipment / lane / period — **non-additive**; report mean *and* P90 together, they tell different stories on a skewed distribution.
**Source.** `FactShipment.TransitVarianceDays`, `PlannedTransitDays`, `ActualTransitDays`.
**DAX.**
```dax
Mean Transit Variance Days := AVERAGE ( FactShipment[TransitVarianceDays] )
P90 Transit Variance Days  := PERCENTILEX.INC ( FactShipment, FactShipment[TransitVarianceDays], 0.9 )
```
**Target/benchmark.** Directional; contract behavioural spec adds a mean +6.4-day shift on affected services during the congestion window (§3.3) — a useful sanity check when validating a model build.
**Owner.** Trade Management.
**Watch-out.** Mean ≠ median on this distribution — a lane can show "mean variance +1.2 days" while more than half its shipments arrive exactly on time and a few arrive very late. Always pair the mean with a percentile.

### OCN.OPS.TURN — Vessel Turnaround Hours
**Definition.** Total time a vessel occupies a port call, from arrival to departure.
**Formula.** `AVERAGE(TurnaroundHours)`.
**Grain.** Port call — **non-additive average**; do not sum turnaround hours across calls and present it as a duration.
**Source.** `FactPortCall.TurnaroundHours`, `AtaTs`, `AtdTs`.
**DAX.**
```dax
Avg Vessel Turnaround Hours := AVERAGE ( FactPortCall[TurnaroundHours] )
```
**Target/benchmark.** Directional; varies hugely by terminal and vessel class — track trend and congestion sensitivity, not an absolute band.
**Owner.** Network Ops.
**Watch-out.** Congestion multiplies this ×1.9 (§3.3) — a rising turnaround trend at a specific terminal is an early-warning signal, not noise; investigate before it shows up in schedule reliability.

### OCN.OPS.WAIT — Waiting-for-Berth Hours
**Definition.** Time a vessel spends at anchor or in the fairway before a berth becomes available.
**Formula.** `AVERAGE(WaitingForBerthHours)`.
**Grain.** Port call — **non-additive average**.
**Source.** `FactPortCall.WaitingForBerthHours`.
**DAX.**
```dax
Avg Waiting for Berth Hours := AVERAGE ( FactPortCall[WaitingForBerthHours] )
```
**Target/benchmark.** Directional; near zero at an uncongested terminal, can run into days during a congestion event.
**Owner.** Network Ops.
**Watch-out.** This is the leading indicator inside the congestion set-piece (×3.4, §3.3) — it degrades *before* schedule reliability and demurrage revenue move, so it is the earliest trigger for an operational alert, not a lagging report metric.

### OCN.OPS.MPCH.GROSS — Moves per Crane-Hour (Gross)
**Definition.** Terminal crane productivity measured against total crane-hours deployed, including idle/delay time within the call window.
**Formula.** `Σ TotalMoves ÷ Σ CraneHoursGross`, pooled — **not** an average of the pre-computed per-call `MovesPerCraneHourGross` column.
**Grain.** Port call / terminal / period — **non-additive**; must be recomputed by pooling numerator and denominator at whatever grain is displayed.
**Source.** `FactPortCall.TotalMoves`, `CraneHoursGross`, `MovesPerCraneHourGross` (stored per-call convenience column).
**DAX.**
```dax
-- NAÏVE (wrong)
Moves per Crane-Hour Gross (naive) := AVERAGE ( FactPortCall[MovesPerCraneHourGross] )
-- WRONG: this averages a ratio that was computed independently for every call — a call with
-- 2 crane-hours and a call with 40 crane-hours count equally, so a handful of short, lucky
-- calls can drag the terminal-level KPI in either direction regardless of actual volume.

-- CORRECT
Moves per Crane-Hour Gross :=
DIVIDE ( SUM ( FactPortCall[TotalMoves] ), SUM ( FactPortCall[CraneHoursGross] ) )
```
**Target/benchmark.** Directional; large modern terminals target 25–35+ gross moves/crane-hour, smaller/older terminals considerably less.
**Owner.** Network Ops.
**Watch-out.** "Gross" includes idle and delay time inside the crane-hour window — a terminal can post a healthy net productivity number while its gross number (the one that actually predicts vessel turnaround) is mediocre. Report both, never one without the other.

### OCN.OPS.MPCH.NET — Moves per Crane-Hour (Net)
**Definition.** Terminal crane productivity against *productive* crane-hours only (idle and delay time excluded) — the number terminal operators are actually benchmarked on.
**Formula.** `Σ TotalMoves ÷ Σ CraneHoursNet`, pooled.
**Grain.** Port call / terminal / period — **non-additive**.
**Source.** `FactPortCall.TotalMoves`, `CraneHoursNet`.
**DAX.**
```dax
Moves per Crane-Hour Net :=
DIVIDE ( SUM ( FactPortCall[TotalMoves] ), SUM ( FactPortCall[CraneHoursNet] ) )
```
**Target/benchmark.** Directional; top-quartile automated terminals exceed 35 net moves/crane-hour, global average considerably lower.
**Owner.** Network Ops.
**Watch-out.** Congestion compresses this to ×0.72 of baseline (§3.3) even while gross moves might look flat — net productivity is where a terminal slowdown shows up first, before turnaround hours visibly blow out.

### OCN.OPS.DWELL — Container Port Dwell Hours
**Definition.** How long a container sits at a location between consecutive events — the yard-congestion signal.
**Formula.** `AVERAGE(DwellHours)`, excluding the sentinel `-1` used for a container's first-ever event.
**Grain.** Container move / location — **non-additive average**; summing dwell hours across moves produces a meaningless total, not a duration.
**Source.** `FactContainerMove.DwellHours`, `LocationKey`, `EventDateKey`.
**DAX.**
```dax
Avg Container Dwell Hours :=
CALCULATE (
    AVERAGE ( FactContainerMove[DwellHours] ),
    FactContainerMove[DwellHours] <> -1
)
```
**Target/benchmark.** Directional; gamma(k=2.2, θ=18) baseline per §3.4 implies a mean around ~40 hours with a long right tail — compare trend, not an absolute target.
**Owner.** Network Ops.
**Watch-out.** The `-1` sentinel for "first event, no prior dwell to measure" must be filtered out explicitly — leaving it in silently drags every average down and makes yards look faster than they are. Congestion pushes real dwell at affected ports ×2.6 (§3.3).

### OCN.OPS.ROLL — Rollover Ratio
**Definition.** Share of accepted bookings that missed their intended sailing and were pushed ("rolled") to a later one.
**Formula.** `Σ IsRolled ÷ (Σ IsConfirmed + Σ IsRolled)` — the denominator is bookings that were accepted for carriage (confirmed or rolled); cancellations and no-shows are a *different* failure mode and are deliberately excluded, otherwise a spike in cancellations would mechanically dilute the rollover number and hide the real signal.
**Grain.** Booking / service / period — **non-additive**.
**Source.** `FactBooking.IsRolled`, `IsConfirmed`, `RolloverCount`, `BookingStatus`.
**DAX.**
```dax
Rollover Ratio :=
VAR Rolled = CALCULATE ( COUNTROWS ( FactBooking ), FactBooking[IsRolled] = 1 )
VAR Base   = CALCULATE ( COUNTROWS ( FactBooking ), FactBooking[IsConfirmed] = 1 || FactBooking[IsRolled] = 1 )
RETURN DIVIDE ( Rolled, Base )
```
**Target/benchmark.** Contract baseline ~9%, target distribution 8% cancelled/3% no-show separately; rises to ~19% inside the peak congestion window (§2.1, §3.3).
**Owner.** Trade Management.
**Watch-out.** Rollover ratio and cancellation rate are frequently confused in commentary — a carrier can simultaneously improve rollover (by not rolling anyone) and get there by cancelling more bookings outright, which is not an improvement from the customer's perspective.

### OCN.REV.FFE — Revenue per FFE
**Definition.** Average commercial yield per forty-foot-equivalent unit carried.
**Formula.** `Σ Revenue_usd ÷ Σ Ffe`, computed over `FactShipment` only. Convention: this **excludes empty repositioning by construction** — empty moves have no `ShipmentKey`/`Revenue_usd` row at all, so the denominator never includes non-revenue FFE. This is deliberate: revenue-per-FFE is a *commercial yield* metric, and blending in cost-driven empty-repositioning volume would understate true laden yield and conflate two different management questions (yield vs. empty-container logistics cost).
**Grain.** Shipment / lane / period — **non-additive**; a weighted rate, never averaged.
**Source.** `FactShipment.Revenue_usd`, `Ffe`.
**DAX.**
```dax
-- NAÏVE (wrong)
Revenue per FFE (naive) := AVERAGEX ( FactShipment, DIVIDE ( FactShipment[Revenue_usd], FactShipment[Ffe] ) )
-- WRONG: averages one rate per shipment, so a 0.1-FFE LCL shipment and a 500-FFE FCL
-- contract shipment carry equal weight in the "average rate" — nonsensical for a metric
-- meant to represent dollars earned per unit of capacity actually sold.

-- CORRECT
Revenue per FFE := DIVIDE ( SUM ( FactShipment[Revenue_usd] ), SUM ( FactShipment[Ffe] ) )
```
**Target/benchmark.** Directional and highly lane-dependent; contract behavioural spec: backhaul revenue/FFE runs ~0.52× headhaul (§3.2) — a useful internal cross-check rather than an external benchmark.
**Owner.** Commercial.
**Watch-out.** Never average this measure across lanes without re-pooling — a "network average revenue per FFE" computed as the mean of lane-level rates hides exactly the headhaul/backhaul imbalance the business needs to see.

### OCN.REV.GP.FFE — Gross Profit per FFE
**Definition.** Average margin dollars earned per FFE carried, after direct cost.
**Formula.** `Σ GrossProfit_usd ÷ Σ Ffe`, same laden-only convention as OCN.REV.FFE (empty moves carry no shipment-level P&L).
**Grain.** Shipment / lane / period — **non-additive weighted ratio**.
**Source.** `FactShipment.GrossProfit_usd`, `Ffe`, `GrossMarginPct`.
**DAX.**
```dax
Gross Profit per FFE := DIVIDE ( SUM ( FactShipment[GrossProfit_usd] ), SUM ( FactShipment[Ffe] ) )
```
**Target/benchmark.** Directional; contract validation gate on the related margin percentage is 14–22% mean gross margin, with a loss-making left tail (§4) — expect a wide spread in profit/FFE across the book, not a tight band.
**Owner.** Commercial.
**Watch-out.** A lane can grow revenue/FFE while gross profit/FFE falls (cost inflation outrunning rate increases) — always show the two together; neither one alone tells the profitability story.

### OCN.REV.BAF — BAF Recovery Ratio
**Definition.** Share of billed Bunker Adjustment Factor (fuel surcharge) revenue that is actually retained as invoiced revenue rather than waived or written off.
**Formula.** `Σ RevenueAmount_usd [ChargeCode="BAF", SettlementStatus ≠ "Written Off"] ÷ Σ RevenueAmount_usd [ChargeCode="BAF", gross billed]`. Convention and why: the more familiar industry definition of "BAF recovery" is *fuel surcharge revenue ÷ incremental bunker cost* (how much of a bunker price spike was passed through), but this contract carries bunker consumption (`FactPortCall.BunkerConsumedTonnes`) at the **vessel/port-call** grain, not allocated to individual shipments — there is no column to build a shipment-level bunker-cost denominator. This KPI therefore adopts the computable proxy above (billed-vs-retained), which still answers a real commercial question (surcharge leakage through waivers/write-offs) but is **not** the cost-pass-through ratio; see §Gaps.
**Grain.** Shipment / lane / period — **non-additive**.
**Source.** `FactFreightCharge.RevenueAmount_usd`, `IsWaived`, `SettlementStatus`, `ChargeTypeKey` → `DimChargeType.ChargeCode = "BAF"`.
**DAX.**
```dax
BAF Recovery Ratio :=
VAR BilledBaf =
    CALCULATE (
        SUM ( FactFreightCharge[RevenueAmount_usd] ),
        RELATED ( DimChargeType[ChargeCode] ) = "BAF"
    )
VAR RetainedBaf =
    CALCULATE (
        SUM ( FactFreightCharge[RevenueAmount_usd] ),
        RELATED ( DimChargeType[ChargeCode] ) = "BAF",
        FactFreightCharge[SettlementStatus] <> "Written Off"
    )
RETURN DIVIDE ( RetainedBaf, BilledBaf )
```
**Target/benchmark.** Directional; healthy books retain >95% of billed surcharge.
**Owner.** Finance.
**Watch-out.** Do not present this as "fuel cost pass-through" in front of a trade manager — it answers a billing-integrity question, not a bunker-cost-recovery question; conflating the two is a common and costly misstatement in rate reviews.

### OCN.REV.DEM — Demurrage Revenue
**Definition.** Revenue billed for containers held past free time inside the terminal (before gate-out).
**Formula.** `Σ RevenueAmount_usd [IsDemurrage=1]`.
**Grain.** Charge line / period — **additive** across customer, lane, and time.
**Source.** `FactFreightCharge.RevenueAmount_usd`, `IsDemurrage`.
**DAX.**
```dax
Demurrage Revenue := CALCULATE ( SUM ( FactFreightCharge[RevenueAmount_usd] ), FactFreightCharge[IsDemurrage] = 1 )
```
**Target/benchmark.** Directional; the analytical set-piece of this dataset is that demurrage revenue **rises** sharply during the Jul–Sep 2025 congestion window (charge-line volume ×3.1, §3.3) precisely because the operation is degrading — a rising number here is *not* good news, it is a symptom.
**Owner.** Finance.
**Watch-out.** Never present demurrage revenue on a "revenue" scorecard without the operational context (dwell hours, waiting-for-berth) alongside it — read alone, it looks like commercial success.

### OCN.REV.DET — Detention Revenue
**Definition.** Revenue billed for equipment held by the customer beyond free time outside the terminal (gate-out to empty return).
**Formula.** `Σ RevenueAmount_usd [IsDetention=1]`.
**Grain.** Charge line / period — **additive**.
**Source.** `FactFreightCharge.RevenueAmount_usd`, `IsDetention`.
**DAX.**
```dax
Detention Revenue := CALCULATE ( SUM ( FactFreightCharge[RevenueAmount_usd] ), FactFreightCharge[IsDetention] = 1 )
```
**Target/benchmark.** Directional; same "rising isn't winning" caveat as demurrage.
**Owner.** Finance.
**Watch-out.** Demurrage and detention are frequently reported as one blended "D&D revenue" line — keep them separate; they have different owners on the customer side (terminal congestion vs. customer's own inland cycle) and different remediation levers.

### OCN.OPS.FREETIME — Free-Time Consumption Rate
**Definition.** How much of the contractual free-time allowance is being used up before demurrage/detention charges start, and what share of moves breach it.
**Formula.** Two companion cuts: (a) breach rate `Σ IsPastFreeTime ÷ COUNT(moves)`; (b) average consumption `AVERAGE(FreeTimeDaysUsed ÷ applicable FreeDays)`, where applicable free days come from `DimEquipment.FreeDaysDemurrage`/`FreeDaysDetention` by equipment type (dry: 5 days, reefer: 3, special: 4, per contract §1.9).
**Grain.** Container move / equipment type — **non-additive**.
**Source.** `FactContainerMove.FreeTimeDaysUsed`, `IsPastFreeTime`, `DemurrageDays`, `DetentionDays`; `DimEquipment.FreeDaysDemurrage`, `FreeDaysDetention`.
**DAX.**
```dax
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
**Target/benchmark.** Directional; a consumption ratio consistently above ~0.8 is an early warning that a lane or customer is about to tip into demurrage even before the breach rate rises.
**Owner.** Network Ops.
**Watch-out.** `FreeTimeDaysUsed` is a days-elapsed measure, not a monetary one — do not average it together with `DemurrageDays`/`DetentionDays` (which only populate once free time is *already* breached); mixing the two produces a ratio with no clean interpretation.

---

## 2. Landside (16)

### LND.CST.KM — Cost per km
**Definition.** Average total trucking/rail cost incurred per kilometre driven.
**Formula.** `Σ TotalCostUsd ÷ Σ DistanceKm`.
**Grain.** Leg / lane / period — **non-additive weighted ratio**; must be recomputed at every grain.
**Source.** `FactTransportLeg.TotalCostUsd`, `DistanceKm`.
**DAX.**
```dax
-- NAÏVE (wrong)
Cost per km (naive) := AVERAGEX ( FactTransportLeg, DIVIDE ( FactTransportLeg[TotalCostUsd], FactTransportLeg[DistanceKm] ) )
-- WRONG: averages one cost-per-km figure per leg, so a 12 km drayage move and a 1,200 km
-- line-haul move get equal weight — the headline number is dominated by short-haul noise.

-- CORRECT
Cost per km := DIVIDE ( SUM ( FactTransportLeg[TotalCostUsd] ), SUM ( FactTransportLeg[DistanceKm] ) )
```
**Target/benchmark.** Directional; varies by mode, lane, and equipment — track trend and lane mix, not one absolute figure.
**Owner.** Inland Ops.
**Watch-out.** `TotalCostUsd` already includes `FreightCostUsd + FuelSurchargeUsd + TollsUsd + AccessorialUsd` — do not add any of those components again on top of it when building a cost bridge.

### LND.CST.MOVE — Cost per Container Move
**Definition.** Average total cost per unit of container capacity moved by road/rail, normalised to TEU so 20' and 40' equipment are comparable.
**Formula.** `Σ TotalCostUsd ÷ Σ Teu`.
**Grain.** Leg / period — **non-additive weighted ratio**.
**Source.** `FactTransportLeg.TotalCostUsd`, `Teu`.
**DAX.**
```dax
Cost per Container Move (TEU-normalised) :=
DIVIDE ( SUM ( FactTransportLeg[TotalCostUsd] ), SUM ( FactTransportLeg[Teu] ) )
```
**Target/benchmark.** Directional; track by equipment type and lane.
**Owner.** Inland Ops.
**Watch-out.** A simple `Σ TotalCostUsd ÷ COUNT(legs)` (cost per trip, not per TEU) is a different and equally valid KPI, but the two are not interchangeable — a fleet mix shift toward more 40' moves lowers cost-per-trip while cost-per-TEU stays flat; label the denominator explicitly on every chart.

### LND.OPS.TURN — Drayage Turn Time
**Definition.** Time a truck spends inside a terminal or site gate, from gate-in to gate-out.
**Formula.** `AVERAGE(TurnTimeMinutes)`.
**Grain.** Leg / site — **non-additive average**.
**Source.** `FactTransportLeg.TurnTimeMinutes`, `GateInWaitMinutes`, `LocationKeyOrigin`/`LocationKeyDestination`.
**DAX.**
```dax
Avg Drayage Turn Time (min) := AVERAGE ( FactTransportLeg[TurnTimeMinutes] )
```
**Target/benchmark.** Directional; well-run terminals target under 60 minutes gate-to-gate, congested sites regularly exceed 90–120. Congestion-window contract effect: landside `TurnTimeMinutes` ×1.7 (§3.3) — a ripple from port congestion into inland yards.
**Owner.** Inland Ops.
**Watch-out.** `GateInWaitMinutes` is a component of turn time, not an alternative to it — reporting the two side by side without noting the overlap double-counts the queue in a narrative.

### LND.SVC.OTP — On-Time Pickup
**Definition.** Share of legs picked up within the agreed appointment window (±2 hours per contract convention).
**Formula.** `Σ IsOnTimePickup ÷ COUNT(legs)`.
**Grain.** Leg / carrier / period — **non-additive**.
**Source.** `FactTransportLeg.IsOnTimePickup`, `PlannedPickupDateKey`, `ActualPickupDateKey`.
**DAX.**
```dax
On-Time Pickup % := AVERAGE ( FactTransportLeg[IsOnTimePickup] )
```
**Target/benchmark.** Directional; 90%+ is a common contractual SLA threshold for scheduled drayage.
**Owner.** Inland Ops.
**Watch-out.** `AVERAGE()` on a 0/1 flag is safe here only because every row is one leg of equal "weight" in the population being measured — if the report ever pivots to a grain where one leg can appear more than once (e.g., a many-to-many bridge), switch to the explicit `DIVIDE(COUNT WHERE=1, COUNT ALL)` form to avoid silent double-counting.

### LND.SVC.OTD — On-Time Delivery
**Definition.** Share of legs delivered within the agreed appointment window (±4 hours per contract convention).
**Formula.** `Σ IsOnTimeDelivery ÷ COUNT(legs)`.
**Grain.** Leg / carrier / period — **non-additive**.
**Source.** `FactTransportLeg.IsOnTimeDelivery`, `PlannedDeliveryDateKey`, `ActualDeliveryDateKey`.
**DAX.**
```dax
On-Time Delivery % := AVERAGE ( FactTransportLeg[IsOnTimeDelivery] )
```
**Target/benchmark.** Directional; 92–97% is typical for a mature dedicated fleet, lower for spot/subcontracted capacity.
**Owner.** Inland Ops.
**Watch-out.** The pickup window (±2h) is tighter than the delivery window (±4h) by contract convention — do not average the two "on-time" rates together into one number; they are not measuring the same tolerance.

### LND.SVC.DIFOT — DIFOT (Delivery In Full, On Time)
**Definition.** Share of legs that were both on time **and** in full — the landside analogue of OTIF, at leg grain.
**Formula.** `Σ (IsOnTimeDelivery=1 AND RELATED FactShipment.IsInFull=1) ÷ COUNT(legs WHERE ShipmentKey ≠ -1)`. "In full" is a shipment-level concept (`FactShipment.IsInFull`) reached via the leg's `ShipmentKey`; legs with `ShipmentKey = -1` (empty repositioning) carry no commercial delivery and are excluded from the denominator by construction.
**Grain.** Leg / customer / period — **non-additive**.
**Source.** `FactTransportLeg.IsOnTimeDelivery`, `ShipmentKey`; `FactShipment.IsInFull` (via relationship).
**DAX.**
```dax
DIFOT % :=
VAR CommercialLegs = FILTER ( FactTransportLeg, FactTransportLeg[ShipmentKey] <> -1 )
VAR DifotLegs =
    FILTER (
        CommercialLegs,
        FactTransportLeg[IsOnTimeDelivery] = 1 && RELATED ( FactShipment[IsInFull] ) = 1
    )
RETURN DIVIDE ( COUNTROWS ( DifotLegs ), COUNTROWS ( CommercialLegs ) )
```
**Target/benchmark.** Directional; 85–92% is a common target band for contract logistics DIFOT.
**Owner.** Inland Ops.
**Watch-out.** Multiplying `On-Time Delivery %` × `In-Full %` computed independently is **not** the same number as counting legs that satisfy both conditions simultaneously, unless on-time and in-full are statistically independent — they usually are not (a late leg is often also a split/partial delivery). Always count the joint condition directly, as above, rather than the product of two marginals.

### LND.UTL.DEADHEAD — Deadhead Percentage
**Definition.** Share of total distance driven with no load aboard.
**Formula.** `Σ EmptyKm ÷ Σ DistanceKm` — a DAX measure only, per the contract note; there is no stored `DeadheadPct` column.
**Grain.** Leg / carrier / period — **non-additive weighted ratio**.
**Source.** `FactTransportLeg.EmptyKm`, `DistanceKm`.
**DAX.**
```dax
-- NAÏVE (wrong)
Deadhead % (naive) := AVERAGEX ( FactTransportLeg, DIVIDE ( FactTransportLeg[EmptyKm], FactTransportLeg[DistanceKm] ) )
-- WRONG: a 5 km empty repositioning leg (100% deadhead) and a 500 km loaded linehaul with
-- a 20 km empty tail (4% deadhead) count equally in the average — the fleet-level number
-- becomes dominated by short legs regardless of how many empty kilometres they represent.

-- CORRECT
Deadhead % := DIVIDE ( SUM ( FactTransportLeg[EmptyKm] ), SUM ( FactTransportLeg[DistanceKm] ) )
```
**Target/benchmark.** Directional; well-optimised dedicated fleets run 10–20% deadhead, general drayage often 25–35%.
**Owner.** Inland Ops.
**Watch-out.** Deadhead % (kilometre-based) and Empty Repositioning Ratio (leg-count-based, next entry) answer different questions — a fleet can have a low deadhead % (short empty tails) but a high repositioning-leg count (many short repositioning trips); do not use one as a proxy for the other.

### LND.UTL.EMPTYREPO — Empty Repositioning Ratio
**Definition.** Share of legs that are dedicated empty-repositioning movements (equipment relocation with no commercial shipment), rather than legs incidentally running empty on a return tail.
**Formula.** `Σ IsEmptyRepositioning ÷ COUNT(legs)`.
**Grain.** Leg / carrier / period — **non-additive**.
**Source.** `FactTransportLeg.IsEmptyRepositioning`, `ShipmentKey` (`-1` for these legs).
**DAX.**
```dax
Empty Repositioning Ratio := AVERAGE ( FactTransportLeg[IsEmptyRepositioning] )
```
**Target/benchmark.** Directional; rises with trade imbalance and equipment-availability mismatches by region.
**Owner.** Inland Ops.
**Watch-out.** See LND.UTL.DEADHEAD — the two measures are related but not substitutable.

### LND.UTL.TRUCK — Truck Utilisation
**Definition.** Share of total distance driven with a load aboard — the productive-use complement of deadhead percentage.
**Formula.** `Σ LoadedKm ÷ Σ DistanceKm` (algebraically `= 1 − Deadhead %`, but compute it independently from `LoadedKm` rather than as `1 −` the other measure, so a data-quality break between `LoadedKm + EmptyKm ≠ DistanceKm` is visible instead of silently hidden).
**Grain.** Carrier / fleet / period — **non-additive weighted ratio**.
**Source.** `FactTransportLeg.LoadedKm`, `DistanceKm`.
**DAX.**
```dax
Truck Utilisation % := DIVIDE ( SUM ( FactTransportLeg[LoadedKm] ), SUM ( FactTransportLeg[DistanceKm] ) )
```
**Target/benchmark.** Directional; 65–85% is a common range for dedicated fleets.
**Owner.** Inland Ops.
**Watch-out.** If `Truck Utilisation % + Deadhead % ≠ 100%` for the same filter context, that is a genuine data-quality signal (unaccounted distance), not a rounding artefact — investigate rather than force-reconcile.

### LND.SVC.FAD — First-Attempt Delivery Rate
**Definition.** Share of legs delivered successfully on the first attempt, with no re-delivery required.
**Formula.** `Σ IsFirstAttemptSuccess ÷ COUNT(legs)`.
**Grain.** Leg / carrier / period — **non-additive**.
**Source.** `FactTransportLeg.IsFirstAttemptSuccess`, `DeliveryAttempts`.
**DAX.**
```dax
First-Attempt Delivery Rate := AVERAGE ( FactTransportLeg[IsFirstAttemptSuccess] )
```
**Target/benchmark.** Directional; 90%+ is typical for B2B distribution, lower for residential/last-mile.
**Owner.** Inland Ops.
**Watch-out.** `DeliveryAttempts` and `IsFirstAttemptSuccess` should always agree (`DeliveryAttempts = 1` implies success flag `= 1`); a reconciliation check between the two is a cheap and effective data-quality gate.

### LND.REV.FSC — Fuel Surcharge Recovery
**Definition.** Share of the fuel surcharge cost paid to hauliers that is recovered as billed customer revenue.
**Formula.** `Σ RevenueAmount_usd [ChargeCategory="Fuel Surcharge", AppliesToMode="Road"] ÷ Σ FuelSurchargeUsd`. This deliberately compares two different fact tables (`FactFreightCharge` revenue lines and `FactTransportLeg` cost lines) at a shared dimensional grain (customer × lane × month) rather than via a row-level join — that is the normal and correct way to build a cross-fact ratio in a star schema; there is no `TransportLegKey` on `FactFreightCharge` to join row-by-row, and none is needed.
**Grain.** Leg / period — **non-additive**; only meaningful at a grain both facts share (customer, mode, period — not `ContainerNo`, which `FactFreightCharge` does not reliably carry for road legs).
**Source.** `FactFreightCharge.RevenueAmount_usd`, `ChargeTypeKey` → `DimChargeType.ChargeCategory`, `AppliesToMode`; `FactTransportLeg.FuelSurchargeUsd`.
**DAX.**
```dax
Fuel Surcharge Recovery :=
VAR FscRevenue =
    CALCULATE (
        SUM ( FactFreightCharge[RevenueAmount_usd] ),
        RELATED ( DimChargeType[ChargeCategory] ) = "Fuel Surcharge",
        RELATED ( DimChargeType[AppliesToMode] ) = "Road"
    )
VAR FscCost = SUM ( FactTransportLeg[FuelSurchargeUsd] )
RETURN DIVIDE ( FscRevenue, FscCost )
```
**Target/benchmark.** Directional; healthy contracts recover 90–100% of fuel cost movement.
**Owner.** Finance.
**Watch-out.** Because this ratio spans two fact tables, it only behaves correctly when both tables are filtered by the *same* shared dimension members — slicing by a `FactTransportLeg`-only attribute (e.g. `TripNo`) with no equivalent on the charge side will silently return a blank or a meaningless number rather than an error.

### LND.CST.ACC — Accessorial Cost Ratio
**Definition.** Share of total landside cost that comes from accessorial charges (detention, extra stops, waiting time, re-delivery) rather than base freight.
**Formula.** `Σ AccessorialUsd ÷ Σ TotalCostUsd`.
**Grain.** Leg / period — **non-additive**.
**Source.** `FactTransportLeg.AccessorialUsd`, `TotalCostUsd`.
**DAX.**
```dax
Accessorial Cost Ratio := DIVIDE ( SUM ( FactTransportLeg[AccessorialUsd] ), SUM ( FactTransportLeg[TotalCostUsd] ) )
```
**Target/benchmark.** Directional; a rising ratio at flat volume is an efficiency red flag — well-run operations keep this under ~10%.
**Owner.** Finance.
**Watch-out.** This ratio can rise simply because base `FreightCostUsd` fell (rate renegotiation) even if accessorial dollars are flat — always check the absolute accessorial trend alongside the ratio, not the ratio alone.

### LND.CAR.SCORE — Carrier Composite Score
**Definition.** A single blended scorecard number ranking road/rail carriers, built from four normalised components.
**Formula.** `0.40 × NormOnTime + 0.25 × NormFirstAttempt + 0.20 × NormCostIndex + 0.15 × NormSubcontractDiscipline`, where each component is min-max normalised to 0–1 across carriers in scope before weighting, and `NormCostIndex`/`NormSubcontractDiscipline` are inverted so that lower cost and lower subcontracting share score higher. **Weighting rationale:** on-time delivery is weighted highest because it is the single largest driver of downstream DIFOT/OTIF failures and customer escalations (mirrors the SCOR "Reliability" attribute being the most heavily monitored in carrier QBRs); first-attempt success is weighted second because re-delivery cost and customer friction scale directly with it; cost index carries real but secondary weight since Meridian's own margin depends on it but a cheap, unreliable carrier is a false economy; subcontracting discipline is included as a visibility/control proxy — a carrier who subcontracts heavily is harder to hold accountable for the other three metrics. **A true claims/damage component could not be included — see §Gaps.**
**Grain.** Carrier / period — **non-additive weighted index**; never average carrier scores across a hierarchy (e.g., alliance level) without recomputing each normalised component at that hierarchy's own population.
**Source.** `FactTransportLeg.IsOnTimeDelivery`, `IsFirstAttemptSuccess`, `TotalCostUsd`, `DistanceKm`, `IsSubcontracted`, `CarrierKey`.
**DAX.**
```dax
-- NAÏVE (wrong)
Carrier Score (naive) :=
AVERAGE ( FactTransportLeg[IsOnTimeDelivery] ) + AVERAGE ( FactTransportLeg[IsFirstAttemptSuccess] )
-- WRONG on two counts: (1) it silently drops cost and subcontracting entirely rather than
-- weighting them, so a cheap, unreliable carrier and an expensive, reliable one are scored
-- on the same two dimensions only; (2) it adds two percentages with no normalisation against
-- the carrier population, so the result isn't comparable across review periods with
-- different carrier mixes.

-- CORRECT (illustrative — carrier-level table computed once per period, then ranked)
VAR CarrierStats =
    ADDCOLUMNS (
        VALUES ( DimCarrier[CarrierKey] ),
        "OnTime",  CALCULATE ( AVERAGE ( FactTransportLeg[IsOnTimeDelivery] ) ),
        "FirstAtt", CALCULATE ( AVERAGE ( FactTransportLeg[IsFirstAttemptSuccess] ) ),
        "CostKm",  CALCULATE ( DIVIDE ( SUM ( FactTransportLeg[TotalCostUsd] ), SUM ( FactTransportLeg[DistanceKm] ) ) ),
        "SubRate", CALCULATE ( AVERAGE ( FactTransportLeg[IsSubcontracted] ) )
    )
VAR MinCost = MINX ( CarrierStats, [CostKm] )
VAR MaxCost = MAXX ( CarrierStats, [CostKm] )
VAR MinSub  = MINX ( CarrierStats, [SubRate] )
VAR MaxSub  = MAXX ( CarrierStats, [SubRate] )
RETURN
    ADDCOLUMNS (
        CarrierStats,
        "CompositeScore",
            0.40 * [OnTime]
          + 0.25 * [FirstAtt]
          + 0.20 * ( 1 - DIVIDE ( [CostKm] - MinCost, MaxCost - MinCost ) )
          + 0.15 * ( 1 - DIVIDE ( [SubRate] - MinSub, MaxSub - MinSub ) )
    )
```
**Target/benchmark.** Directional; used for relative ranking within a review period, not an absolute pass/fail threshold. `DimCarrier.OnTimeTargetPct` and `PreferredTier` provide an independent cross-check.
**Owner.** Inland Ops.
**Watch-out.** Min-max normalisation is sensitive to the carrier population in scope — adding or removing one extreme carrier from the comparison set re-scales everyone else's score. Re-run the full ranking whenever the carrier panel changes; never patch one carrier's score in isolation.

### LND.OPS.DET — Detention at Site Hours
**Definition.** Hours a truck/trailer is held at a customer or warehouse site beyond the agreed free time.
**Formula.** `AVERAGE(DetentionAtSiteHours)`.
**Grain.** Leg / site — **non-additive average**.
**Source.** `FactTransportLeg.DetentionAtSiteHours`, `WarehouseKey`, `LocationKeyOrigin`/`LocationKeyDestination`.
**DAX.**
```dax
Avg Detention at Site Hours := AVERAGE ( FactTransportLeg[DetentionAtSiteHours] )
```
**Target/benchmark.** Directional; sites averaging over ~1 hour routinely should trigger an appointment-scheduling review.
**Owner.** Inland Ops.
**Watch-out.** This is the landside mirror of ocean detention (`OCN.REV.DET`) but measured in **hours of delay**, not **dollars of revenue** — the two must never be added together in a combined "detention" KPI card.

### LND.SUS.CO2 — CO2 per Tonne-km
**Definition.** Carbon intensity of landside transport — grams of CO2 emitted per tonne of cargo moved one kilometre.
**Formula.** `Σ Co2Kg × 1000 ÷ Σ (WeightKg ÷ 1000 × DistanceKm)` — numerator and denominator both pooled across legs before dividing.
**Grain.** Leg / period — **non-additive weighted ratio**.
**Source.** `FactTransportLeg.Co2Kg`, `WeightKg`, `DistanceKm`; reference only: `DimMode.Co2GramsPerTonneKm` (the mode-level design factor used to *generate* Co2Kg, useful as a sense-check, not as a substitute for the actual measure).
**DAX.**
```dax
-- NAÏVE (wrong)
CO2 per Tonne-km (naive) :=
AVERAGEX (
    FactTransportLeg,
    DIVIDE ( FactTransportLeg[Co2Kg] * 1000, ( FactTransportLeg[WeightKg] / 1000 ) * FactTransportLeg[DistanceKm] )
)
-- WRONG: averages a per-leg intensity figure, so a short, lightly loaded leg with a noisy
-- ratio carries the same weight as a fully-loaded, long-haul leg — the fleet-level carbon
-- intensity figure becomes dominated by small, unrepresentative legs.

-- CORRECT
CO2 per Tonne-km (g) :=
VAR TotalCo2Grams = SUM ( FactTransportLeg[Co2Kg] ) * 1000
VAR TotalTonneKm = SUMX ( FactTransportLeg, ( FactTransportLeg[WeightKg] / 1000 ) * FactTransportLeg[DistanceKm] )
RETURN DIVIDE ( TotalCo2Grams, TotalTonneKm )
```
**Target/benchmark.** Directional; `DimMode.Co2GramsPerTonneKm` carries the mode-level design baseline (rail and barge well below road) — use it as the reference line on the chart, not as the reported actual.
**Owner.** Inland Ops.
**Watch-out.** `SUMX` is required for the tonne-km denominator because tonne-km is itself a product of two row-level columns — a plain `SUM(WeightKg) × SUM(DistanceKm)` at the total level is mathematically wrong (it cross-multiplies unrelated legs' weight and distance) and will not match the correct figure except by coincidence.

### LND.OPS.SUBCON — Subcontracting Ratio
**Definition.** Share of landside legs executed by subcontracted capacity rather than Meridian's own contracted fleet.
**Formula.** `Σ IsSubcontracted ÷ COUNT(legs)`.
**Grain.** Leg / carrier / period — **non-additive**.
**Source.** `FactTransportLeg.IsSubcontracted`, `CarrierKey` → `DimCarrier.IsOwnFleet`.
**DAX.**
```dax
Subcontracting Ratio := AVERAGE ( FactTransportLeg[IsSubcontracted] )
```
**Target/benchmark.** Directional; a rising ratio during peak season is expected capacity flexing, not automatically a problem — evaluate alongside on-time delivery for the same population.
**Owner.** Inland Ops.
**Watch-out.** `IsSubcontracted` (a leg-level flag reflecting a specific booking decision) and `DimCarrier.IsOwnFleet` (a static carrier attribute) can disagree when Meridian's own carrier code is used to book a subcontracted trip under a partner agreement — reconcile the two rather than assuming they are always redundant.

---

## 3. Warehouse & inventory (18)

### WHS.OPS.D2S — Dock-to-Stock Minutes
**Definition.** Time from a container/pallet arriving at the dock to the SKU being put away and available for pick.
**Formula.** `AVERAGE(DockToStockMinutes)`, filtered to `TaskType IN {Receive, Putaway}` and `DockToStockMinutes ≠ -1` (the sentinel used for task types where the measure does not apply).
**Grain.** Task / warehouse — **non-additive average**.
**Source.** `FactWarehouseTask.DockToStockMinutes`, `TaskType`, `WarehouseKey`.
**DAX.**
```dax
Avg Dock-to-Stock Minutes :=
CALCULATE (
    AVERAGE ( FactWarehouseTask[DockToStockMinutes] ),
    FactWarehouseTask[TaskType] IN { "Receive", "Putaway" },
    FactWarehouseTask[DockToStockMinutes] <> -1
)
```
**Target/benchmark.** Directional; 60–120 minutes is a common target band for a manual DC, automated sites push well under that.
**Owner.** Site Ops.
**Watch-out.** Forgetting the `<> -1` filter is the most common mistake here — the sentinel is a large negative outlier disguised as a valid number and will drag any unfiltered average sharply (and misleadingly) downward.

### WHS.QLT.INVACC — Inventory Accuracy
**Definition.** How closely the WMS's system-of-record count matches a physical cycle count.
**Formula.** `1 − (Σ |SystemCountUnits − PhysicalCountUnits| ÷ Σ SystemCountUnits)`, computed only over snapshot rows where a physical count actually occurred (`PhysicalCountUnits ≠ -1`).
**Grain.** Snapshot / SKU / warehouse, cycle-count days only — **non-additive**.
**Source.** `FactInventorySnapshot.SystemCountUnits`, `PhysicalCountUnits`.
**DAX.**
```dax
Inventory Accuracy % :=
VAR CountedRows = FILTER ( FactInventorySnapshot, FactInventorySnapshot[PhysicalCountUnits] <> -1 )
VAR AbsVariance = SUMX ( CountedRows, ABS ( FactInventorySnapshot[SystemCountUnits] - FactInventorySnapshot[PhysicalCountUnits] ) )
VAR SystemTotal = SUMX ( CountedRows, FactInventorySnapshot[SystemCountUnits] )
RETURN 1 - DIVIDE ( AbsVariance, SystemTotal )
```
**Target/benchmark.** Directional; 98–99.5%+ is typical for a mature WMS with regular cycle counting.
**Owner.** Site Ops.
**Watch-out.** Summing signed variance instead of absolute variance lets over-counts and under-counts cancel out and hides real inaccuracy — always use `ABS()`.

### WHS.QLT.PICKACC — Pick Accuracy
**Definition.** Share of pick tasks completed with no error.
**Formula.** `Σ IsAccurate [TaskType="Pick"] ÷ COUNT(pick tasks)`.
**Grain.** Task / warehouse / period — **non-additive**.
**Source.** `FactWarehouseTask.IsAccurate`, `ErrorCount`, `TaskType`, `ShiftKey`, `EmployeeKey`.
**DAX.**
```dax
-- NAÏVE (wrong)
Pick Accuracy % (naive) :=
AVERAGEX (
    VALUES ( FactWarehouseTask[TaskDateKey] ),
    CALCULATE ( AVERAGE ( FactWarehouseTask[IsAccurate] ), FactWarehouseTask[TaskType] = "Pick" )
)
-- WRONG: averages one daily accuracy % per day with equal weight, so a slow Sunday with 40
-- picks and a peak Wednesday with 4,000 picks count the same — exactly the trap the contract's
-- own weekday-effect seasonality (§3.1) is designed to expose.

-- CORRECT
Pick Accuracy % :=
DIVIDE (
    CALCULATE ( COUNTROWS ( FactWarehouseTask ), FactWarehouseTask[TaskType] = "Pick", FactWarehouseTask[IsAccurate] = 1 ),
    CALCULATE ( COUNTROWS ( FactWarehouseTask ), FactWarehouseTask[TaskType] = "Pick" )
)
```
**Target/benchmark.** Contract behavioural baseline: 99.1% overall, dropping to 97.4% on night shift and 98.2% for agency staff in their first six months (§3.4) — a useful internal cross-check when validating a model build. World-class is often quoted around 99.5%+.
**Owner.** Site Ops.
**Watch-out.** Night-shift and new-agency-staff cuts will *always* look worse than the topline by design in this dataset — do not treat that as a data bug when validating.

### WHS.OPS.OCT — Order Cycle Time
**Definition.** Elapsed time from the first warehouse task on an order to the last, i.e. from work starting on the order to it being loaded/ready to ship.
**Formula.** For each `OrderNo`: `MAX(TaskEndTs) − MIN(TaskStartTs)`, in hours; the KPI is the average of that duration across orders in scope.
**Grain.** Order / warehouse — **non-additive average**; an order-level duration can never be summed across orders.
**Source.** `FactWarehouseTask.OrderNo`, `TaskStartTs`, `TaskEndTs`.
**DAX.**
```dax
Avg Order Cycle Time (hrs) :=
VAR OrderSpans =
    ADDCOLUMNS (
        SUMMARIZE ( FactWarehouseTask, FactWarehouseTask[OrderNo] ),
        "SpanHours",
            DATEDIFF (
                CALCULATE ( MIN ( FactWarehouseTask[TaskStartTs] ) ),
                CALCULATE ( MAX ( FactWarehouseTask[TaskEndTs] ) ),
                MINUTE
            ) / 60
    )
RETURN AVERAGEX ( OrderSpans, [SpanHours] )
```
**Target/benchmark.** Directional; B2B replenishment orders often target same-day to 24 hours, DTC/e-commerce targets a few hours.
**Owner.** Site Ops.
**Watch-out.** `OrderNo` is a degenerate dimension living only on the fact table — grouping by it inside a measure (as above) is correct, but it is easy to instead group by `WarehouseTaskKey` by mistake and get a duration of zero for every row; always sanity-check the grain of `SUMMARIZE` before trusting the output.

### WHS.PRD.LPH — Lines per Labour Hour
**Definition.** Order lines processed per hour of direct labour — the primary warehouse productivity KPI.
**Formula.** `Σ LinesProcessed ÷ Σ LabourHours`.
**Grain.** Task / employee / shift — **non-additive weighted ratio**.
**Source.** `FactWarehouseTask.LinesProcessed`, `LabourHours`.
**DAX.**
```dax
-- NAÏVE (wrong)
Lines per Labour Hour (naive) := AVERAGEX ( FactWarehouseTask, DIVIDE ( FactWarehouseTask[LinesProcessed], FactWarehouseTask[LabourHours] ) )
-- WRONG: a 6-minute task and a 6-hour task contribute an equally-weighted rate to the average,
-- so a handful of short high-rate tasks can make the whole shift look more productive than it was.

-- CORRECT
Lines per Labour Hour := DIVIDE ( SUM ( FactWarehouseTask[LinesProcessed] ), SUM ( FactWarehouseTask[LabourHours] ) )
```
**Target/benchmark.** Directional; contract behavioural spec ties this to role and tenure via a truncated normal distribution (§3.4) — compare by `RoleName`/`TenureBand`, not as one site-wide number.
**Owner.** Site Ops.
**Watch-out.** Comparing raw LPH across `TaskType` (Pick vs Putaway vs Pack) without segmenting is meaningless — the tasks have structurally different line-handling rates.

### WHS.PRD.UPH — Units per Labour Hour
**Definition.** Units processed per hour of direct labour — the volume-weighted sibling of LPH, better suited to comparing tasks with very different units-per-line (e.g., full-pallet putaway vs. each-picking).
**Formula.** `Σ UnitsProcessed ÷ Σ LabourHours`.
**Grain.** Task / employee / shift — **non-additive weighted ratio**.
**Source.** `FactWarehouseTask.UnitsProcessed`, `LabourHours`.
**DAX.**
```dax
Units per Labour Hour := DIVIDE ( SUM ( FactWarehouseTask[UnitsProcessed] ), SUM ( FactWarehouseTask[LabourHours] ) )
```
**Target/benchmark.** Directional; varies enormously with unit size/weight — track trend per role, not an absolute number.
**Owner.** Site Ops.
**Watch-out.** LPH and UPH can move in opposite directions in the same period (e.g., a shift toward full-case picking raises UPH while lowering LPH) — report both, and know which one the business actually wants to optimise for before drawing a conclusion.

### WHS.CST.LCPL — Labour Cost per Line
**Definition.** Direct labour dollars spent per order line processed.
**Formula.** `Σ LabourCostUsd ÷ Σ LinesProcessed`.
**Grain.** Task / warehouse / period — **non-additive weighted ratio**.
**Source.** `FactWarehouseTask.LabourCostUsd`, `LinesProcessed`.
**DAX.**
```dax
Labour Cost per Line := DIVIDE ( SUM ( FactWarehouseTask[LabourCostUsd] ), SUM ( FactWarehouseTask[LinesProcessed] ) )
```
**Target/benchmark.** Directional; falls as LPH rises for a given wage rate — the two KPIs should be reviewed together, not independently.
**Owner.** Finance.
**Watch-out.** A falling cost-per-line can come from genuine productivity gains **or** from a shift toward lower-wage agency/seasonal staff (`DimEmployee.EmploymentType`) — check the labour mix before crediting a productivity programme.

### WHS.UTL.PALLET — Pallet Position Utilisation
**Definition.** Share of available pallet storage positions occupied.
**Formula.** `Σ PalletPositionsUsed ÷ Σ PalletPositionsAvailable`, pooled across the SKUs/day in scope; when trending over multiple days, **average the daily ratio**, never sum positions across days.
**Grain.** Snapshot / warehouse / day — **semi-additive over date** (each day's value is a valid point-in-time occupancy figure; summing across days produces a meaningless "positions used" total).
**Source.** `FactInventorySnapshot.PalletPositionsUsed`, `PalletPositionsAvailable`, `WarehouseKey`; cross-check against `DimWarehouse.PalletPositions`.
**DAX.**
```dax
Pallet Position Utilisation % :=
DIVIDE ( SUM ( FactInventorySnapshot[PalletPositionsUsed] ), SUM ( FactInventorySnapshot[PalletPositionsAvailable] ) )
```
**Target/benchmark.** Directional; 80–90% is a commonly cited efficient range — much above that risks congestion and blocked put-away, much below signals under-utilised (costly) space.
**Owner.** Site Ops.
**Watch-out.** When aggregating this measure over a date range with the `SUM` form above, the result is still a same-day-style ratio (numerator and denominator both accumulate proportionally) — but if the report instead needs "average daily occupancy," switch explicitly to `AVERAGEX` over `VALUES(DimDate[Date])`, and never mix the two forms in the same workbook without labelling which is which.

### WHS.UTL.CUBE — Cube Utilisation
**Definition.** Share of available storage *volume* occupied by inventory — the cubic-space counterpart to pallet-position utilisation.
**Formula.** `Σ OnHandCbm ÷ Σ (PalletPositionsAvailable × StandardPalletCbm)`, where `StandardPalletCbm` (≈1.7 m³, a standard 1.0 m × 1.2 m footprint at ~1.4 m usable stack height) is a **documented assumption, not a contract column** — `DimWarehouse` carries `PalletPositions`/`StorageAreaSqm` but no racking height or total cubic-capacity field, so true cube utilisation cannot be computed exactly against this contract (see §Gaps).
**Grain.** Snapshot / warehouse / day — **semi-additive over date**, same caution as pallet utilisation.
**Source.** `FactInventorySnapshot.OnHandCbm`, `PalletPositionsAvailable`.
**DAX.**
```dax
Cube Utilisation % ( proxy ) :=
VAR StandardPalletCbm = 1.7   -- documented assumption, see KPI definition
RETURN
    DIVIDE (
        SUM ( FactInventorySnapshot[OnHandCbm] ),
        SUM ( FactInventorySnapshot[PalletPositionsAvailable] ) * StandardPalletCbm
    )
```
**Target/benchmark.** Directional only, given the proxy denominator; treat trend, not absolute level, as the signal.
**Owner.** Site Ops.
**Watch-out.** This number is only as good as the `StandardPalletCbm` assumption — it should never be presented next to `WHS.UTL.PALLET` as if the two were measuring the same thing with equal precision; one is exact (position count), the other is a modelled estimate.

### WHS.QLT.PERFECT — Perfect Order Rate (warehouse-touched)
**Definition.** Share of shipments that touched a Meridian warehouse and were delivered on time, in full, undamaged, and with clean documentation — all four conditions simultaneously.
**Formula.** `Σ IsPerfectOrder [WarehouseKey ≠ -1] ÷ COUNT(shipments WHERE WarehouseKey ≠ -1)`, where `IsPerfectOrder = IsOnTime AND IsInFull AND NOT IsDamaged AND IsDocumentationClean` (pre-computed per contract §2.2).
**Grain.** Shipment / warehouse / period — **non-additive**.
**Source.** `FactShipment.IsPerfectOrder`, `WarehouseKey`.
**DAX.**
```dax
Perfect Order Rate (Warehouse-touched) :=
CALCULATE ( AVERAGE ( FactShipment[IsPerfectOrder] ), FactShipment[WarehouseKey] <> -1 )
```
**Target/benchmark.** Contract validation gate: 0.84–0.89 company-wide (§4) — use as the sanity band for the warehouse-touched cut too, though it can legitimately differ from the enterprise number (`XCT.QLT.PERFECT`).
**Owner.** Site Ops.
**Watch-out.** This is a **superset** of OTIF (`WHS.QLT.OTIF`, next entry) — it adds the documentation-clean condition on top of the classic three-factor OTIF. Never quote the two numbers interchangeably in the same sentence.

### WHS.QLT.OTIF — OTIF (On-Time, In-Full) and its DIF × DOQ × DOT decomposition
**Definition.** The classic three-factor logistics quality KPI: did the order arrive complete, in good condition, and on time — decomposed into Delivered-In-Full (DIF), Delivered-On-Quality (DOQ), and Delivered-On-Time (DOT), each a marginal rate, multiplied together.
**Formula.** `OTIF = DIF × DOQ × DOT`, where `DIF = AVERAGE(IsInFull)`, `DOQ = AVERAGE(1 − IsDamaged)`, `DOT = AVERAGE(IsOnTime)` — all from `FactShipment`. This project's convention: `IsDocumentationClean` is deliberately **excluded** from OTIF (it belongs to the stricter, four-factor Perfect Order Rate above) because OTIF, as an industry standard, concerns physical delivery performance only.
**Grain.** Shipment / customer / period — **non-additive multiplicative ratio**; each of the three marginals must be computed independently at the grain in view, then multiplied — never multiply marginals computed at one grain to represent a different grain.
**Source.** `FactShipment.IsInFull`, `IsDamaged`, `IsOnTime`.
**DAX.**
```dax
-- NAÏVE (wrong) — arithmetic mean instead of product
OTIF % (naive) :=
VAR Dif = AVERAGE ( FactShipment[IsInFull] )
VAR Doq = CALCULATE ( AVERAGE ( 1 - FactShipment[IsDamaged] ) )
VAR Dot = AVERAGE ( FactShipment[IsOnTime] )
RETURN ( Dif + Doq + Dot ) / 3
-- WRONG: this is the single most common OTIF mistake. Averaging three healthy-looking rates
-- (~96%, ~99%, ~91%) gives ~95.4% — a great-looking number that hides how badly the three
-- failure modes compound. OTIF is a joint requirement, not a menu of three chances to pass.

-- CORRECT — multiplicative decomposition
VAR Dif = AVERAGE ( FactShipment[IsInFull] )                     -- ≈ 0.962
VAR Doq = CALCULATE ( AVERAGE ( 1 - FactShipment[IsDamaged] ) )  -- ≈ 0.987
VAR Dot = AVERAGE ( FactShipment[IsOnTime] )                     -- ≈ 0.913
RETURN Dif * Doq * Dot                                            -- ≈ 0.867
```
**Target/benchmark.** Contract behavioural spec: DIF ≈ 0.962, DOQ ≈ 0.987, DOT ≈ 0.913 → headline OTIF ≈ 0.867 (§3.4); validation gate 0.85–0.88 (§4). Worked contrast: arithmetic mean of the three components ≈ **95.4%**, correct multiplicative headline ≈ **86.7%** — an 8.7-point gap between the naive and correct number, entirely from the arithmetic operator chosen.
**Owner.** Site Ops.
**Watch-out.** The compounding effect gets worse, not better, as more factors are added (this is why the four-factor Perfect Order Rate is always lower than three-factor OTIF for the same population) — a stakeholder who has only ever seen the arithmetic-mean version will find the correct number "suspiciously low" and push back; have the worked example above ready.

### WHS.INV.TURNS — Inventory Turns
**Definition.** How many times inventory notionally cycles through the warehouse in a year — the standard inventory-efficiency KPI.
**Formula.** Because this is a 3PL/warehousing dataset rather than a retail P&L, there is no `COGS` measure — the convention adopted is a **throughput-based** turns figure: `(Σ UnitsProcessed for TaskType="Pick", annualised) ÷ AVERAGE(OnHandUnits over the same period)`, annualised by `365 ÷ (days in the selected period)`. State this convention on every chart that uses it.
**Grain.** SKU / warehouse / period (result is an annualised rate) — **non-additive**; never average period-level turns figures across periods, recompute from pooled sums.
**Source.** `FactWarehouseTask.UnitsProcessed`, `TaskType`; `FactInventorySnapshot.OnHandUnits`.
**DAX.**
```dax
-- NAÏVE (wrong)
Inventory Turns (naive) :=
VAR UnitsOut = CALCULATE ( SUM ( FactWarehouseTask[UnitsProcessed] ), FactWarehouseTask[TaskType] = "Pick" )
VAR EndingOnHand = CALCULATE ( SUM ( FactInventorySnapshot[OnHandUnits] ), LASTDATE ( DimDate[Date] ) )
RETURN DIVIDE ( UnitsOut, EndingOnHand )
-- WRONG on two counts: (1) not annualised, so a one-month view and a one-year view of the
-- same steady-state warehouse produce wildly different "turns" numbers; (2) uses the single
-- ending snapshot instead of an average, so a stock-build right before period-end (e.g. peak
-- season inbound) makes the warehouse look far less efficient than it is.

-- CORRECT
Inventory Turns :=
VAR PeriodDays = COUNTROWS ( DATESBETWEEN ( DimDate[Date], MIN ( DimDate[Date] ), MAX ( DimDate[Date] ) ) )
VAR AnnualiseFactor = DIVIDE ( 365, PeriodDays )
VAR UnitsOutAnnualised =
    CALCULATE ( SUM ( FactWarehouseTask[UnitsProcessed] ), FactWarehouseTask[TaskType] = "Pick" ) * AnnualiseFactor
VAR AvgOnHand = AVERAGE ( FactInventorySnapshot[OnHandUnits] )
RETURN DIVIDE ( UnitsOutAnnualised, AvgOnHand )
```
**Target/benchmark.** Directional and industry-dependent — fast-moving consumer goods commonly run 8–12+ turns/year, industrial/project cargo 2–4. Treat as trend, not a fixed pass/fail band.
**Owner.** Site Ops.
**Watch-out.** Because `FactInventorySnapshot` is weekly for the older 18 months of history and daily for the latest 12 (§2.9), a naive `AVERAGE(OnHandUnits)` mixes sparse and dense sampling across a long trend line — weight-check or restrict the comparison window before trusting a long-run turns trend.

### WHS.INV.DOH — Days on Hand
**Definition.** How many days of throughput the current inventory represents — the inverse framing of inventory turns.
**Formula.** `365 ÷ Inventory Turns` (recomputed from the same pooled sums as `WHS.INV.TURNS`, not derived by re-deriving turns from a different aggregation path).
**Grain.** SKU / warehouse / period — **non-additive inverse ratio**.
**Source.** Same as `WHS.INV.TURNS`; also cross-referenced against the pre-computed `FactInventorySnapshot.DaysOfSupply` (a row-level, SKU-specific figure — useful for allocation but **not** a substitute for the pooled enterprise DOH, since naively averaging `DaysOfSupply` across SKUs weights a slow-moving SKU with huge stock the same as a fast mover with almost none).
**DAX.**
```dax
Days on Hand := DIVIDE ( 365, [Inventory Turns] )
```
**Target/benchmark.** Directional; inverse of the turns band above (e.g., 8 turns/year ≈ 46 days on hand).
**Owner.** Site Ops.
**Watch-out.** Do not reach for `AVERAGE(FactInventorySnapshot[DaysOfSupply])` as a shortcut enterprise DOH — it is exactly the "averaging a ratio" trap again, this time hidden behind a column that looks pre-aggregated.

### WHS.INV.ABC — ABC Class Mix
**Definition.** Distribution of on-hand inventory value across the A/B/C classification — where the value concentration actually sits.
**Formula.** For each class `c`: `Σ OnHandValueUsd [AbcClassStatic = c] ÷ Σ OnHandValueUsd [all]`.
**Grain.** SKU / warehouse / period — **non-additive distribution** (the three class shares always sum to 100% within a filter context, but that total is not itself a meaningful "sum across classes" for any other purpose).
**Source.** `FactInventorySnapshot.OnHandValueUsd`, `SkuKey` → `DimSku.AbcClassStatic`.
**DAX.**
```dax
Value Share by ABC Class :=
DIVIDE ( SUM ( FactInventorySnapshot[OnHandValueUsd] ), CALCULATE ( SUM ( FactInventorySnapshot[OnHandValueUsd] ), ALL ( DimSku[AbcClassStatic] ) ) )
```
**Target/benchmark.** Directional; classic Pareto expectation is roughly 70–80% of value in Class A, which typically comprises 15–20% of SKUs.
**Owner.** Site Ops.
**Watch-out.** `DimSku.AbcClassStatic` is the **seeded** class from data generation; a DAX-derived reclassification (ranking SKUs by trailing usage/value and re-bucketing) will legitimately disagree with it for some SKUs — that divergence is deliberate curriculum content (a Week-4 exercise per `SCHEMA_CONTRACT.md` §1.16), not a data error to be reconciled away.

### WHS.QLT.SHRINK — Shrinkage Rate
**Definition.** Units lost to theft, damage, or unexplained write-off, relative to units counted.
**Formula.** `Σ ShrinkageUnits ÷ Σ SystemCountUnits`, computed over cycle-count snapshot rows (`PhysicalCountUnits ≠ -1`), consistent with `WHS.QLT.INVACC`.
**Grain.** Snapshot / SKU / period — numerator/count are **semi-additive over date** (snapshot facts), but the **ratio itself is non-additive** and must be recomputed at every grain.
**Source.** `FactInventorySnapshot.ShrinkageUnits`, `SystemCountUnits`, `PhysicalCountUnits`.
**DAX.**
```dax
Shrinkage Rate :=
VAR CountedRows = FILTER ( FactInventorySnapshot, FactInventorySnapshot[PhysicalCountUnits] <> -1 )
RETURN DIVIDE ( SUMX ( CountedRows, FactInventorySnapshot[ShrinkageUnits] ), SUMX ( CountedRows, FactInventorySnapshot[SystemCountUnits] ) )
```
**Target/benchmark.** Directional; well-controlled contract warehousing typically runs well under 0.5% of units; high-value or high-theft-risk categories run higher.
**Owner.** Site Ops.
**Watch-out.** Shrinkage and inventory inaccuracy are related but distinct — inaccuracy captures *any* system-vs-physical mismatch (including honest counting/data-entry error), while shrinkage specifically attributes the loss; do not report one as a subset check of the other without checking the generator's/business's own attribution rule.

### WHS.INV.OBS — Obsolete Stock Ratio
**Definition.** Share of on-hand units that are obsolete (unsellable/unusable, typically past shelf life or superseded).
**Formula.** `Σ ObsoleteUnits ÷ Σ OnHandUnits`.
**Grain.** Snapshot / SKU / warehouse — semi-additive numerator over date, **non-additive ratio**.
**Source.** `FactInventorySnapshot.ObsoleteUnits`, `OnHandUnits`.
**DAX.**
```dax
Obsolete Stock Ratio := DIVIDE ( SUM ( FactInventorySnapshot[ObsoleteUnits] ), SUM ( FactInventorySnapshot[OnHandUnits] ) )
```
**Target/benchmark.** Directional; under 2–5% of units is generally considered healthy, though it is highly category-dependent (perishables and fashion run structurally higher).
**Owner.** Site Ops.
**Watch-out.** This ratio is snapshot-grain — comparing "obsolete ratio last Monday" to "obsolete ratio this Monday" is valid, but summing `ObsoleteUnits` across a quarter of daily snapshots and dividing by the *quarter's* on-hand sum overstates the true picture because the same obsolete units are being counted on every snapshot day they remained on the shelf.

### WHS.QLT.STOCKOUT — Stockout Rate
**Definition.** Share of SKU-location-days where available stock was zero against demand.
**Formula.** `Σ IsStockout ÷ COUNTROWS(snapshot rows)` for the SKU/warehouse/period in scope.
**Grain.** Snapshot / SKU / warehouse — **non-additive ratio** over a semi-additive flag.
**Source.** `FactInventorySnapshot.IsStockout`, `SkuKey`, `WarehouseKey`.
**DAX.**
```dax
Stockout Rate := AVERAGE ( FactInventorySnapshot[IsStockout] )
```
**Target/benchmark.** Directional; high-service operations target under 1–2% of SKU-days out of stock.
**Owner.** Site Ops.
**Watch-out.** This measures SKU-*days* out of stock, not lost sales or order lines affected — a single high-velocity SKU stocking out for a week contributes far more real business impact than the "% of SKU-days" figure alone conveys; pair it with `WHS.QLT.PERFECT`/OTIF impact where possible.

### WHS.QLT.REWORK — Rework Rate
**Definition.** Share of warehouse tasks that had to be redone due to an error.
**Formula.** `Σ IsRework ÷ COUNT(tasks)`.
**Grain.** Task / warehouse / period — **non-additive**.
**Source.** `FactWarehouseTask.IsRework`, `IsDamagedOnHandling`, `ErrorCount`, `TaskType`.
**DAX.**
```dax
Rework Rate := AVERAGE ( FactWarehouseTask[IsRework] )
```
**Target/benchmark.** Directional; well-run sites target under 1–2% of tasks.
**Owner.** Site Ops.
**Watch-out.** `IsRework` and `IsDamagedOnHandling` overlap but are not the same population (a task can be reworked for reasons other than handling damage, e.g. a picking error) — report them as two bars, not one combined "quality failure" number, or the remediation owner becomes ambiguous.

---

## 4. Air & LCL (9)

### ALC.WT.CHG6000 — Chargeable Weight, Air 1:6000
**Definition.** The billing weight for most air cargo: the greater of actual gross weight and volumetric weight, where volumetric weight uses the IATA-standard divisor of 6,000 cm³ per kg.
**Formula.** Reference formula (industry documentation): `Volumetric Weight (kg) = Volume_cbm × 1,000,000 ÷ 6,000 = Volume_cbm × 166.67`; `Chargeable Weight = MAX(GrossWeightKg, Volumetric Weight)`. This project reports the **already-resolved** `FactShipment.ChargeableWeightKg` rather than recomputing from raw dimensions, because the contract carries only aggregate `VolumeCbm`/`GrossWeightKg` — no per-piece length/width/height — so the MAX() logic has already been applied upstream by the generator per `DimMode.ChargeableWeightRule`. Source for the divisor: "Volumetric Weight (kg) = (Length × Width × Height) ÷ 6000 ... an industry standard set by IATA" — [Maersk, Air Cargo Chargeable Weight](https://www.maersk.com/logistics-explained/transportation-and-freight/2025/03/10/air-cargo-chargeable-weight).
**Grain.** Shipment — **additive** (it is a resolved physical weight per shipment, safely summable across shipments that all use the same rule).
**Source.** `FactShipment.ChargeableWeightKg`, `GrossWeightKg`, `VolumeCbm`, `ModeKey` → `DimMode.ChargeableWeightRule = "Air 1:6000"`.
**DAX.**
```dax
Chargeable Weight kg (Air 1:6000) :=
CALCULATE (
    SUM ( FactShipment[ChargeableWeightKg] ),
    RELATED ( DimMode[ChargeableWeightRule] ) = "Air 1:6000"
)
```
**Target/benchmark.** N/A — a physical measure, not a ratio with a benchmark band.
**Owner.** Trade Management.
**Watch-out.** Never sum `ChargeableWeightKg` across shipments that mix the 1:6000 rule, the 1:5000 rule, and the ocean 1:1000 rule without first segmenting by `DimMode.ChargeableWeightRule` — the three are not the same unit of "chargeable weight" even though the column name is identical.

### ALC.WT.CHG5000 — Chargeable Weight, Air 1:5000 variant
**Definition.** The billing weight under the alternative 1:5,000 cm³-per-kg volumetric divisor used by some carriers and, historically, some express/small-parcel networks instead of the IATA 6,000 standard.
**Formula.** Reference formula: `Volumetric Weight (kg) = Volume_cbm × 1,000,000 ÷ 5,000 = Volume_cbm × 200`; `Chargeable Weight = MAX(GrossWeightKg, Volumetric Weight)`. Because `5,000 < 6,000`, the same cubic volume produces a **higher** volumetric weight under this rule — bulky, low-density cargo is charged more under 1:5000 than under 1:6000. Source: "Some carriers use a divisor of 5,000 instead of 6,000 ... which results in bulkier shipments being charged at a higher rate" — [Maersk, Air Cargo Chargeable Weight](https://www.maersk.com/logistics-explained/transportation-and-freight/2025/03/10/air-cargo-chargeable-weight). **When it applies:** carrier- and trade-lane-specific, never assumed — always look up `DimMode.ChargeableWeightRule` per shipment rather than hardcoding a divisor.
**Grain.** Shipment — **additive** within the 1:5000-tagged population.
**Source.** `FactShipment.ChargeableWeightKg`, `GrossWeightKg`, `VolumeCbm`; `DimMode.ChargeableWeightRule = "Air 1:5000"`.
**DAX.**
```dax
Chargeable Weight kg (Air 1:5000) :=
CALCULATE (
    SUM ( FactShipment[ChargeableWeightKg] ),
    RELATED ( DimMode[ChargeableWeightRule] ) = "Air 1:5000"
)
```
**Target/benchmark.** N/A — physical measure.
**Owner.** Trade Management.
**Watch-out.** A shipment can be volumetric-weight-driven under the 1:5000 rule while the *identical* cubic dimensions would be actual-weight-driven under 1:6000 — never compare `ChargeableWeightKg` figures, or yields computed from them, across the two rule populations without segmenting first.

### ALC.WT.RT1000 — Ocean LCL Revenue Tons, 1:1000
**Definition.** The billing unit for ocean LCL freight: Revenue Tons (RT), the greater of weight tons and volume in cubic metres, using the ocean convention that 1 m³ is treated as equivalent to 1 metric tonne (1,000 kg) — the "weight-or-measure" (W/M) rule.
**Formula.** `RT = MAX(WeightKg ÷ 1000, VolumeCbm)`. Source: "A Revenue Ton (RT) is the billing unit for LCL ocean freight, determined by whichever measurement is greater: cargo volume or cargo weight ... the industry standard is 1 CBM = 1,000 kg" — [LogisticsCalc, LCL Revenue Ton Calculator](https://logisticscalc.com/ocean-freight/lcl-revenue-ton-calculator). **Explicit contrast with air:** ocean LCL uses a flat **1:1,000 kg/cbm density crossover** with no divide-by-6000/5000 step — it is a direct tonne-for-cbm equivalence, not a volumetric-weight formula. Confusing the two — e.g. dividing ocean cbm by 6000 the way air is divided, or applying the 1,000 kg/cbm ocean rule to an air shipment — is a classic and expensive rating error; the two conventions differ by a factor of five to six.
**Grain.** Shipment — **additive** (a resolved per-shipment RT figure, already computed as `FactShipment.RevenueTons`).
**Source.** `FactShipment.RevenueTons`, `GrossWeightKg`, `VolumeCbm`, `ModeKey` → `DimMode.ModeCode = "LCL"`, `ChargeableWeightRule = "Ocean 1:1000"`.
**DAX.**
```dax
Revenue Tons (LCL) :=
CALCULATE ( SUM ( FactShipment[RevenueTons] ), DimMode[ModeCode] = "LCL" )
```
**Target/benchmark.** N/A — physical/billing measure.
**Owner.** Trade Management.
**Watch-out.** This is the single most common cross-mode confusion in an entry-level rating desk: air's chargeable-weight divisors (6000 / 5000) and ocean LCL's revenue-ton rule (1000) look superficially similar ("a number you divide volume by") but encode very different densities and must never be swapped.

### ALC.REV.YIELDKG — Yield per kg
**Definition.** Average revenue earned per chargeable kilogram — the air-freight analogue of ocean's revenue-per-FFE.
**Formula.** `Σ Revenue_usd ÷ Σ ChargeableWeightKg`, for `ModeGroup = "Air"` shipments.
**Grain.** Shipment / lane / period — **non-additive weighted ratio**.
**Source.** `FactShipment.Revenue_usd`, `ChargeableWeightKg`, `ModeKey` → `DimMode.ModeGroup`.
**DAX.**
```dax
-- NAÏVE (wrong)
Yield per kg (naive) :=
CALCULATE (
    AVERAGEX ( FactShipment, DIVIDE ( FactShipment[Revenue_usd], FactShipment[ChargeableWeightKg] ) ),
    DimMode[ModeGroup] = "Air"
)
-- WRONG: a 40 kg document courier shipment and a 12,000 kg charter consolidation contribute
-- equally to the "average yield," so a portfolio of many small shipments and a few large ones
-- gets a headline yield dominated by the small-shipment count, not by revenue-weighted reality.

-- CORRECT
Yield per kg :=
CALCULATE (
    DIVIDE ( SUM ( FactShipment[Revenue_usd] ), SUM ( FactShipment[ChargeableWeightKg] ) ),
    DimMode[ModeGroup] = "Air"
)
```
**Target/benchmark.** Directional; highly lane- and season-dependent (peak season index 1.35× baseline per §3.1).
**Owner.** Commercial.
**Watch-out.** Comparing yield per kg across shipments on different chargeable-weight rules (1:6000 vs 1:5000) without segmenting mixes two different denominators' economics into one number.

### ALC.SLS.CONV — Quote-to-Book Conversion
**Definition.** Share of quoted business that converts into an actual carried shipment.
**Formula.** `Σ (IsConfirmed=1 OR IsRolled=1) ÷ COUNT(DISTINCT QuoteKey)` on `FactBooking`. Convention and limitation: `FactBooking` is the only table carrying `QuoteKey`, and every row in it already represents a quote that reached the booking stage — there is no `FactQuote` capturing quotes that were requested and never became any booking record at all. This KPI is therefore a **booking-stage conversion proxy** (of quotes that got as far as a booking attempt, how many actually shipped), not true top-of-funnel win rate; see §Gaps.
**Grain.** Quote / period — **non-additive**.
**Source.** `FactBooking.QuoteKey`, `IsConfirmed`, `IsRolled`, `IsCancelled`, `IsNoShow`, `BookingStatus`.
**DAX.**
```dax
Quote-to-Book Conversion (booking-stage proxy) :=
VAR Converted =
    CALCULATE ( COUNTROWS ( FactBooking ), FactBooking[IsConfirmed] = 1 || FactBooking[IsRolled] = 1 )
VAR AllQuotes = DISTINCTCOUNT ( FactBooking[QuoteKey] )
RETURN DIVIDE ( Converted, AllQuotes )
```
**Target/benchmark.** Directional; freight-forwarding desks commonly track 30–50% quote-to-book depending on trade lane and account type — treat as a rough band given the proxy nature of this measure.
**Owner.** Commercial.
**Watch-out.** Never present this number as "sales conversion rate" to a commercial audience without the caveat above — a genuinely lost quote (customer never came back at all) is invisible to this measure by construction, so the real conversion rate is lower than what this KPI can show.

### ALC.REV.GPHBL — Gross Profit per House Bill
**Definition.** Average margin dollars earned per house bill of lading (one shipment) — the standard forwarding-desk profitability KPI.
**Formula.** `Σ GrossProfit_usd ÷ COUNT(DISTINCT HouseBlNo)`, for `ModeGroup IN {"Air", "Ocean"}` with `IsConsolidated = 1` (LCL/consol business) as the primary Air & LCL cut.
**Grain.** Shipment / period — **non-additive weighted ratio** (one house bill = one `FactShipment` row in this contract, so this collapses to gross profit per shipment for that population).
**Source.** `FactShipment.GrossProfit_usd`, `HouseBlNo`, `ModeKey` → `DimMode.IsConsolidated`.
**DAX.**
```dax
Gross Profit per House Bill :=
DIVIDE ( SUM ( FactShipment[GrossProfit_usd] ), DISTINCTCOUNT ( FactShipment[HouseBlNo] ) )
```
**Target/benchmark.** Directional; small house bills often carry disproportionately high per-file handling cost relative to margin — watch for a long left tail of loss-making small files.
**Owner.** Commercial.
**Watch-out.** `DISTINCTCOUNT(HouseBlNo)` is required, not `COUNTROWS(FactShipment)` — although the contract states one row per house bill, defensive modelling should never assume a table has no duplicates without checking (see `SCHEMA_CONTRACT.md` §3.5, landmine #2, for a documented example of exactly this kind of duplication risk elsewhere in the model).

### ALC.CST.MODAL — Air vs Ocean Modal Cost Comparison
**Definition.** How much more (or less) it costs to move a kilogram of cargo by air versus by ocean on a comparable lane.
**Formula.** `(Σ DirectCost_usd ÷ Σ ChargeableWeightKg) [ModeGroup="Air"] ÷ (Σ DirectCost_usd ÷ Σ ChargeableWeightKg) [ModeGroup="Ocean"]` — expressed as an index (e.g., "Air costs 6.2× Ocean per kg on this lane").
**Grain.** Lane / period — **non-additive index**; never average lane-level indices across lanes.
**Source.** `FactShipment.DirectCost_usd`, `ChargeableWeightKg`, `ModeKey` → `DimMode.ModeGroup`, `LocationKeyPol`/`LocationKeyPod`.
**DAX.**
```dax
Air vs Ocean Cost Index (per kg) :=
VAR AirCostPerKg   = CALCULATE ( DIVIDE ( SUM ( FactShipment[DirectCost_usd] ), SUM ( FactShipment[ChargeableWeightKg] ) ), DimMode[ModeGroup] = "Air" )
VAR OceanCostPerKg = CALCULATE ( DIVIDE ( SUM ( FactShipment[DirectCost_usd] ), SUM ( FactShipment[ChargeableWeightKg] ) ), DimMode[ModeGroup] = "Ocean" )
RETURN DIVIDE ( AirCostPerKg, OceanCostPerKg )
```
**Target/benchmark.** Directional; air-vs-ocean cost multiples of 4–8× per kg are typical, narrowing for very light, low-density, or time-critical cargo.
**Owner.** Commercial.
**Watch-out.** Ocean's `ChargeableWeightKg` for FCL cargo is not meaningfully comparable to an LCL or air kg figure (FCL is priced per container, not per kg) — restrict this comparison to LCL and air, or to a per-shipment revenue basis instead, when FCL is in scope.

### ALC.TRN.MODAL — Modal Transit-Time Comparison
**Definition.** How much faster air is than ocean on a comparable lane.
**Formula.** `MEDIAN(ActualTransitDays) [ModeGroup="Ocean"] ÷ MEDIAN(ActualTransitDays) [ModeGroup="Air"]`, expressed as an index; median is used rather than mean given the right-skewed transit distribution (§3.4).
**Grain.** Lane / period — **non-additive statistic**.
**Source.** `FactShipment.ActualTransitDays`, `ModeKey` → `DimMode.ModeGroup`, `TypicalTransitDaysBand`.
**DAX.**
```dax
Ocean vs Air Transit Index :=
VAR OceanMedian = CALCULATE ( MEDIANX ( FactShipment, FactShipment[ActualTransitDays] ), DimMode[ModeGroup] = "Ocean" )
VAR AirMedian   = CALCULATE ( MEDIANX ( FactShipment, FactShipment[ActualTransitDays] ), DimMode[ModeGroup] = "Air" )
RETURN DIVIDE ( OceanMedian, AirMedian )
```
**Target/benchmark.** Directional; ocean typically runs 4–10× longer than air on the same lane, before factoring in door-to-door drayage on both ends.
**Owner.** Commercial.
**Watch-out.** `ActualTransitDays` on `FactShipment` reflects the mode-specific leg being measured — confirm both cuts are measuring door-to-door (or both port/airport-to-port/airport) before dividing one by the other, or the index silently compares two different journeys.

### ALC.WT.VOLMIX — Volumetric-vs-Actual Weight Mix
**Definition.** Share of shipments (or volume) whose billing is driven by volumetric weight rather than actual gross weight — i.e., how much of the book is "space-constrained" cargo versus "weight-constrained" cargo.
**Formula.** `COUNT(shipments WHERE ChargeableWeightKg > GrossWeightKg) ÷ COUNT(shipments)`, per mode.
**Grain.** Shipment / period — **non-additive**.
**Source.** `FactShipment.ChargeableWeightKg`, `GrossWeightKg`, `ModeKey`.
**DAX.**
```dax
Volumetric-Driven Shipment Share :=
DIVIDE (
    COUNTROWS ( FILTER ( FactShipment, FactShipment[ChargeableWeightKg] > FactShipment[GrossWeightKg] ) ),
    COUNTROWS ( FactShipment )
)
```
**Target/benchmark.** Directional; consumer electronics and apparel commonly skew 40–60% volumetric-driven, dense industrial cargo much lower.
**Owner.** Trade Management.
**Watch-out.** A rising volumetric-driven share on a lane is a strong hint that pricing strategy should shift toward cbm-based rating rather than per-kg rating — but only within one chargeable-weight-rule population; mixing 1:6000, 1:5000, and 1:1000 shipments in one "volumetric share" figure produces an uninterpretable blend.

---

## 5. Cross-cutting (7)

### XCT.SCOR.MAP — SCOR Level-1 Attribute Map
**Definition.** A classification overlay mapping every KPI in this dictionary to the SCOR (Supply Chain Operations Reference) model's five Level-1 performance attributes — Reliability, Responsiveness, Agility, Cost, and Asset Management — so a scorecard can be organised the way a supply-chain executive audience expects to see it, rather than by data domain.
**Formula.** Not a computed ratio — a fixed classification. Mapping adopted by this project:

| SCOR Attribute | KPI codes |
|---|---|
| **Reliability** (did it happen as promised?) | `OCN.REL.SCHED`, `OCN.OPS.ROLL`, `OCN.TRN.VAR`, `LND.SVC.OTP`, `LND.SVC.OTD`, `LND.SVC.DIFOT`, `LND.SVC.FAD`, `WHS.QLT.INVACC`, `WHS.QLT.PICKACC`, `WHS.QLT.PERFECT`, `WHS.QLT.OTIF`, `WHS.QLT.REWORK`, `XCT.QLT.PERFECT` |
| **Responsiveness** (how fast?) | `OCN.TRN.P50`, `OCN.TRN.P90`, `OCN.OPS.TURN`, `OCN.OPS.WAIT`, `OCN.OPS.DWELL`, `LND.OPS.TURN`, `WHS.OPS.D2S`, `WHS.OPS.OCT`, `ALC.TRN.MODAL` |
| **Agility** (how well does it flex?) | `OCN.OPS.FREETIME`, `LND.OPS.SUBCON`, `LND.UTL.EMPTYREPO`, `ALC.SLS.CONV`, `ALC.WT.VOLMIX` |
| **Cost** (what does it cost?) | `OCN.REV.BAF`, `LND.CST.KM`, `LND.CST.MOVE`, `LND.CST.ACC`, `LND.REV.FSC`, `WHS.CST.LCPL`, `ALC.CST.MODAL`, `XCT.FIN.FCR`, `XCT.FIN.CTS` |
| **Asset Management** (how well are assets used?) | `OCN.UTL.LF.HEAD`, `OCN.UTL.LF.BACK`, `OCN.UTL.SLOT`, `OCN.OPS.MPCH.GROSS`, `OCN.OPS.MPCH.NET`, `LND.UTL.TRUCK`, `LND.UTL.DEADHEAD`, `WHS.UTL.PALLET`, `WHS.UTL.CUBE`, `WHS.INV.TURNS`, `WHS.INV.DOH`, `WHS.INV.OBS`, `XCT.FIN.C2C` |

Commercial/profitability KPIs (`OCN.REV.FFE`, `OCN.REV.GP.FFE`, `OCN.REV.DEM`, `OCN.REV.DET`, `ALC.REV.YIELDKG`, `ALC.REV.GPHBL`, `XCT.CUS.CONC`, `XCT.FIN.MARGDISP`, `LND.CAR.SCORE`, `WHS.INV.ABC`, `WHS.QLT.STOCKOUT`, `WHS.QLT.SHRINK`, `OCN.VOL.TEU`, `OCN.VOL.FFE`, `OCN.MIX.LADEN`, `ALC.WT.CHG6000`, `ALC.WT.CHG5000`, `ALC.WT.RT1000`) sit deliberately **outside** the classic five SCOR attributes — SCOR is an operations reference model, not a P&L framework, and forcing profitability metrics into it would misrepresent the standard.
**Grain.** KPI catalogue (a classification, not a fact-table measure) — **not applicable** for additivity.
**Source.** A small maintained mapping table, `SCORMap[KpiCode, ScorAttribute]`, joined to `FactTarget.KpiCode` for scorecard slicing.
**DAX.**
```dax
DEFINE
    TABLE SCORMap =
        DATATABLE (
            "KpiCode", STRING, "ScorAttribute", STRING,
            {
                { "OCN.REL.SCHED", "Reliability" }, { "LND.SVC.DIFOT", "Reliability" },
                { "WHS.QLT.OTIF", "Reliability" },  { "OCN.TRN.P90", "Responsiveness" },
                { "WHS.OPS.D2S", "Responsiveness" },{ "LND.OPS.SUBCON", "Agility" },
                { "LND.CST.KM", "Cost" },           { "OCN.UTL.LF.HEAD", "Asset Management" }
                -- (full table carries all 72 codes; abbreviated here for illustration)
            }
        )

Target Attainment % by SCOR Attribute :=
VAR TargetsInAttribute =
    TREATAS ( FILTER ( SCORMap, SCORMap[ScorAttribute] = SELECTEDVALUE ( SCORMap[ScorAttribute] ) )[KpiCode], FactTarget[KpiCode] )
RETURN
    CALCULATE (
        DIVIDE ( SUM ( FactTarget[TargetValue] ), SUM ( FactTarget[StretchValue] ) ),
        TargetsInAttribute
    )
```
**Target/benchmark.** N/A — a classification framework, not a measured value.
**Owner.** Commercial (framework governance); each underlying KPI keeps its own domain owner.
**Watch-out.** SCOR mappings are a matter of house convention, not a universal standard — a different organisation could reasonably place `LND.OPS.SUBCON` under Cost instead of Agility. Document the choice once, in this table, and do not let individual analysts re-classify KPIs ad hoc on different dashboards.

### XCT.QLT.PERFECT — Perfect Order Rate (company-wide)
**Definition.** Share of all shipments — across every mode, not just those touching a Meridian warehouse — delivered on time, in full, undamaged, and with clean documentation.
**Formula.** `AVERAGE(IsPerfectOrder)` across all of `FactShipment`, with **no** `WarehouseKey` filter (the enterprise superset of `WHS.QLT.PERFECT`).
**Grain.** Shipment / period — **non-additive**.
**Source.** `FactShipment.IsPerfectOrder`.
**DAX.**
```dax
Perfect Order Rate (Company-wide) := AVERAGE ( FactShipment[IsPerfectOrder] )
```
**Target/benchmark.** Contract validation gate: 0.84–0.89 (`SCHEMA_CONTRACT.md` §4).
**Owner.** Commercial.
**Watch-out.** This number and `WHS.QLT.PERFECT` will differ, sometimes substantially, whenever warehouse-touched shipments have a different risk profile than the book as a whole (e.g., value-added-service shipments often run more complex, more failure-prone journeys) — always label which population is being shown.

### XCT.FIN.C2C — Cash-to-Cash Cycle Time
**Definition.** How many days elapse, net, between paying for inputs and collecting cash from customers — `Days Inventory Outstanding + Days Sales Outstanding − Days Payable Outstanding`. Source for the standard formula: "Cash Conversion Cycle = DIO + DSO − DPO" — [Corporate Finance Institute, Cash Conversion Cycle](https://corporatefinanceinstitute.com/resources/accounting/cash-conversion-cycle/).
**Formula and what is actually computable against this contract:**
- **DIO** (Days Inventory Outstanding) — computable as a warehousing-throughput proxy: `365 ÷ Inventory Turns` — identical construction to `WHS.INV.DOH`.
- **DSO** (Days Sales Outstanding) — this contract has **no cash-receipt or payment-application date** anywhere (`FactFreightCharge.SettlementStatus` records a status, not a date), so *true* actual-collections DSO cannot be computed. This project instead reports a **contractual-terms proxy**: `Σ(Revenue_usd × DimCustomer.PaymentTermsDays) ÷ Σ Revenue_usd` — a revenue-weighted average of agreed payment terms, which is directional and *not* the same as real collection speed. See §Gaps.
- **DPO** (Days Payable Outstanding) — **not computable at all** against this contract: `DimCarrier` carries no payment-terms field, and no fact table carries a vendor-invoice or vendor-payment date. This component is reported as a documented gap, not fabricated; see §Gaps.
**Grain.** Company / period — **non-additive**; each component is itself a non-additive ratio/average, and the formula sums three non-additive figures — never average a cash-to-cash figure across periods, always recompute all three components from pooled sums first.
**Source.** `FactWarehouseTask.UnitsProcessed`, `FactInventorySnapshot.OnHandUnits` (for DIO); `FactShipment.Revenue_usd`, `DimCustomer.PaymentTermsDays` (for the DSO proxy); **no source exists for true DPO** (see §Gaps).
**DAX.**
```dax
Days Inventory Outstanding (proxy) := [Days on Hand]   -- = WHS.INV.DOH

Days Sales Outstanding (contractual-terms proxy) :=
DIVIDE (
    SUMX ( FactShipment, FactShipment[Revenue_usd] * RELATED ( DimCustomer[PaymentTermsDays] ) ),
    SUM ( FactShipment[Revenue_usd] )
)

-- Days Payable Outstanding: NOT COMPUTABLE under Schema Contract v1.0 — see §Gaps.
-- No DAX is provided for this component; do not substitute an invented column.

Cash-to-Cash Cycle Time (partial) :=
[Days Inventory Outstanding (proxy)] + [Days Sales Outstanding (contractual-terms proxy)]
-- NOTE: this is DIO + DSO only. The true C2C figure would subtract DPO, which is unavailable;
-- report this explicitly as a partial/directional figure, never as "the" cash-to-cash cycle.
```
**Target/benchmark.** Directional only, and explicitly partial (missing DPO). Asset-heavy logistics groups commonly target a full C2C cycle in the 20–45 day range; do not apply that band to the partial DIO+DSO figure above without the caveat.
**Owner.** Finance.
**Watch-out.** Never let this partial figure be relabelled "cash-to-cash cycle time" without the DIO+DSO-only caveat attached — dropping DPO from the formula always makes the number look **worse** (longer cycle) than the true cycle would be, because DPO is subtracted in the real formula.

### XCT.FIN.FCR — Freight Cost as % of Revenue
**Definition.** Direct transportation cost as a share of freight revenue — a standard top-line efficiency ratio for a carrier/forwarder's own book.
**Formula.** `Σ DirectCost_usd ÷ Σ Revenue_usd`.
**Grain.** Company / customer / period — **non-additive weighted ratio**.
**Source.** `FactShipment.DirectCost_usd`, `Revenue_usd`.
**DAX.**
```dax
Freight Cost % of Revenue := DIVIDE ( SUM ( FactShipment[DirectCost_usd] ), SUM ( FactShipment[Revenue_usd] ) )
```
**Target/benchmark.** Directional; consistent with the contract's gross-margin validation gate (14–22% mean gross margin, §4), this ratio should sit roughly in the 78–86% range at the corresponding grain — the two are complements (`Freight Cost % + Gross Margin % ≈ 100%` before other P&L lines).
**Owner.** Finance.
**Watch-out.** `DirectCost_usd` on `FactShipment` is **direct** cost only — it excludes SG&A and other overhead, so this ratio is not the same as an all-in operating-cost ratio; do not present it as full P&L cost coverage.

### XCT.FIN.CTS — Cost to Serve per Customer
**Definition.** Average direct cost incurred to serve one active customer over a period.
**Formula.** `Σ CostAmount_usd [IsCost=1] ÷ DISTINCTCOUNT(CustomerKey)`. Convention: this is **direct cost only** — there is no overhead-allocation table in the contract to build a full absorption-costing view, so indirect costs (account management time, systems, shared facility overhead) are out of scope by construction; state this on every chart.
**Grain.** Customer / period — the numerator is **additive** across customers and time; the per-customer average itself is **non-additive** and must be recomputed, not averaged, whenever the customer population changes.
**Source.** `FactFreightCharge.CostAmount_usd`, `IsCost`, `CustomerKey`.
**DAX.**
```dax
Cost to Serve per Customer :=
DIVIDE (
    CALCULATE ( SUM ( FactFreightCharge[CostAmount_usd] ), FactFreightCharge[IsCost] = 1 ),
    DISTINCTCOUNT ( FactFreightCharge[CustomerKey] )
)
```
**Target/benchmark.** Directional; varies enormously by `CustomerSegment`/`SizeTier` — a Global Key Account with dedicated capacity naturally costs more to serve in absolute terms than an SME Direct account, so compare within segment.
**Owner.** Finance.
**Watch-out.** Ranking customers by this measure alone rewards serving *fewer* customers at *lower* total cost, which is not the same as serving each customer *efficiently* — always pair it with revenue or margin per customer before drawing a "this customer is expensive" conclusion.

### XCT.CUS.CONC — Revenue Concentration (Top-10 Customer Share)
**Definition.** Share of total revenue coming from the ten largest customers by revenue — a concentration-risk KPI.
**Formula.** `Σ Revenue_usd [top 10 customers by revenue in the current filter context] ÷ Σ Revenue_usd [all customers, same filter context]`.
**Grain.** Company / period — **non-additive ratio**; the "top 10" set itself must be re-ranked inside whatever filter context (region, period, mode) is on the report — a top-10 list computed once at the company level does not carry over correctly to a filtered view.
**Source.** `FactShipment.Revenue_usd`, `CustomerKey` → `DimCustomer.CustomerCode`/`CustomerName` (SCD2-resolved).
**DAX.**
```dax
-- NAÏVE (wrong)
Top-10 Customer Share (naive) :=
VAR Top10Static = { "CUS0001", "CUS0002", "CUS0003", "CUS0004", "CUS0005", "CUS0006", "CUS0007", "CUS0008", "CUS0009", "CUS0010" }
RETURN
    DIVIDE (
        CALCULATE ( SUM ( FactShipment[Revenue_usd] ), DimCustomer[CustomerCode] IN Top10Static ),
        CALCULATE ( SUM ( FactShipment[Revenue_usd] ), ALL ( DimCustomer ) )
    )
-- WRONG: hardcodes a customer list computed once (e.g. for last year) — as the book changes,
-- this silently stops being "the top 10" and becomes "ten specific accounts," which is a
-- different and far less useful KPI, with no error raised to say so.

-- CORRECT
Top-10 Customer Share :=
VAR CustomerRevenue =
    ADDCOLUMNS (
        VALUES ( DimCustomer[CustomerCode] ),
        "CustRev", CALCULATE ( SUM ( FactShipment[Revenue_usd] ) )
    )
VAR Top10Revenue =
    SUMX ( TOPN ( 10, CustomerRevenue, [CustRev], DESC ), [CustRev] )
VAR TotalRevenue = SUMX ( CustomerRevenue, [CustRev] )
RETURN DIVIDE ( Top10Revenue, TotalRevenue )
```
**Target/benchmark.** Directional; under ~30–40% top-10 share is generally considered a diversified book, above ~50% signals meaningful concentration risk.
**Owner.** Commercial.
**Watch-out.** `DimCustomer` is SCD2 (multiple `CustomerKey` versions per durable customer, §1.4) — rank by `CustomerCode` (the durable business key) or a customer-level `SUMMARIZE`, never by `CustomerKey` directly, or one customer's revenue can split across several "top 10" slots under different key versions and understate true concentration.

### XCT.FIN.MARGDISP — Margin Dispersion
**Definition.** How widely gross margin varies across the shipment book — a stable, healthy-looking average margin can still hide a large loss-making tail.
**Formula.** Spread statistic on shipment-level `GrossMarginPct`: report both the standard deviation (`STDEV`) and the P10–P90 spread, since the distribution has a documented loss-making left tail (§4) that a symmetric standard deviation alone under-communicates.
**Grain.** Shipment / period — **non-additive statistic**.
**Source.** `FactShipment.GrossMarginPct`, `GrossProfit_usd`, `Revenue_usd`.
**DAX.**
```dax
Gross Margin % Std Dev := STDEVX.P ( FactShipment, FactShipment[GrossMarginPct] )

Gross Margin % P10–P90 Spread :=
VAR P90 = PERCENTILEX.INC ( FactShipment, FactShipment[GrossMarginPct], 0.9 )
VAR P10 = PERCENTILEX.INC ( FactShipment, FactShipment[GrossMarginPct], 0.1 )
RETURN P90 - P10
```
**Target/benchmark.** Directional; contract validation gate: mean gross margin 14–22%, with a documented left tail below zero (§4) — a healthy book keeps the P10 comfortably above zero even while the mean sits in-band.
**Owner.** Finance.
**Watch-out.** A flat or improving mean margin alongside a *widening* P10–P90 spread is a genuine warning sign (more shipments losing money even as the average holds) — always chart dispersion next to the mean, never the mean alone, when reporting margin health.

---

## 6. The eleven formulas you must be able to state cold

Interview-ready shortlist — code, name, formula only. If asked in a room with no laptop, these are the ones to have memorised.

1. **`OCN.REL.SCHED`** — Schedule Reliability: `COUNT(calls, |ATA − PromisedETA| ≤ 24h) ÷ COUNT(calls)`, trailing 56 days, always vs the never-revised promised ETA.
2. **`OCN.UTL.LF.HEAD`** — Headhaul Load Factor: `Σ SlotsUsedTeu ÷ Σ SlotCapacityTeu`, capacity-weighted, never averaged per call.
3. **`OCN.REV.FFE`** — Revenue per FFE: `Σ Revenue_usd ÷ Σ Ffe`, laden shipments only (empties excluded by construction).
4. **`OCN.OPS.MPCH.NET`** — Moves per Crane-Hour (Net): `Σ TotalMoves ÷ Σ CraneHoursNet`, pooled, not the average of per-call ratios.
5. **`LND.SVC.DIFOT`** — DIFOT: `COUNT(legs, on-time AND in-full) ÷ COUNT(legs)` — the joint condition, not the product of two independently-computed marginals.
6. **`WHS.QLT.OTIF`** — OTIF: `DIF × DOQ × DOT` (multiplicative, not averaged) — three ~90%+ marginals compound to a headline in the mid-80s.
7. **`WHS.INV.TURNS`** — Inventory Turns: `Annualised units shipped ÷ Average on-hand units`, never ending-balance-over-period-units.
8. **`ALC.WT.CHG6000`** — Air Chargeable Weight: `MAX(GrossWeightKg, VolumeCbm × 1,000,000 ÷ 6,000)`.
9. **`ALC.WT.RT1000`** — Ocean LCL Revenue Ton: `MAX(WeightKg ÷ 1,000, VolumeCbm)` — a flat 1,000 kg/cbm equivalence, structurally different from air's divide-by-6000/5000 approach.
10. **`XCT.FIN.C2C`** — Cash-to-Cash Cycle Time: `DIO + DSO − DPO`.
11. **`XCT.QLT.PERFECT`** — Perfect Order Rate: `AVERAGE(OnTime AND InFull AND NOT Damaged AND DocumentationClean)` — the four-condition joint AND, always stricter than three-factor OTIF for the same population.

---

## 7. Gaps — KPIs the contract cannot fully support as specified

Every KPI above has a working formula and DAX measure against `SCHEMA_CONTRACT.md` v1.0. The items below are the specific places where a fully faithful, non-proxy implementation is **not** possible with the columns that exist, and exactly what would need to be added. Nothing below has been patched with an invented column.

| # | KPI(s) affected | What's missing | Exact column/table needed | What was done instead |
|---|---|---|---|---|
| 1 | `XCT.FIN.C2C` (DPO component) | No vendor payment-terms attribute anywhere, and no accounts-payable fact with a payment date. `DimCarrier` has no `PaymentTermsDays`-equivalent field (unlike `DimCustomer`, which has one). | `DimCarrier.PaymentTermsDays` **or** a new `FactAccountsPayable` table with `VendorInvoiceDateKey`/`PaymentDateKey`. | DPO is reported as **not computable** — no DAX measure is provided for it, and the cash-to-cash figure is explicitly labelled "partial (DIO + DSO only)." |
| 2 | `XCT.FIN.C2C` (true DSO) | No cash-receipt or payment-application date on any revenue fact — `FactFreightCharge.SettlementStatus` records a status (`Invoiced`/`Paid`/`Disputed`/`Written Off`/`Credited`), not a date. | `FactFreightCharge.PaymentReceivedDateKey`, or a `FactCashApplication` table keyed to `InvoiceNo`. | DSO is reported as a **contractual-terms-weighted proxy** using `DimCustomer.PaymentTermsDays`, clearly labelled as directional, not actual collection speed. |
| 3 | `ALC.SLS.CONV` | No record of a quote that was requested and never became any booking row — `FactBooking` (the only table with `QuoteKey`) only contains quotes that reached the booking stage. | A `FactQuote` table (or a `QuoteStatus` on the quote itself) capturing quotes independent of `BookingKey`, including ones that never converted at all. | Implemented as a **booking-stage conversion proxy** (of quotes that reached a booking attempt, how many shipped), explicitly labelled as not true top-of-funnel win rate. |
| 4 | `LND.CAR.SCORE` (claims/damage component) | `FactShipment.IsDamaged` exists but is not attributable to the road/rail carrier responsible for a specific leg — `FactTransportLeg` carries no `IsDamaged`/claims flag of its own, and a shipment can involve several legs from several carriers. | `FactTransportLeg.IsDamaged` (or a `FactClaim` table keyed to `TransportLegKey`/`CarrierKey`). | The composite score's four components (on-time delivery, first-attempt success, cost index, subcontracting discipline) deliberately **exclude** a claims/damage weighting; the weighting rationale documents this omission rather than silently normalising around it. |
| 5 | `WHS.UTL.CUBE` | No total storage-volume or racking-height field on `DimWarehouse` — only `PalletPositions`, `StorageAreaSqm`, `GrossAreaSqm` (footprint, not volume). | `DimWarehouse.TotalStorageCbm` or `RackClearHeightMetres` (to derive volume from footprint). | Implemented as a **proxy** using an explicitly documented standard-pallet-volume assumption (`StandardPalletCbm ≈ 1.7 m³`), clearly labelled as an assumption rather than a contract column, and never presented with the same precision claim as `WHS.UTL.PALLET`. |
| 6 | `OCN.REV.BAF` | No bunker/fuel cost allocated at shipment grain — `FactPortCall.BunkerConsumedTonnes` exists only at the vessel/port-call grain, so a true "surcharge revenue ÷ incremental bunker cost" pass-through ratio cannot be built per shipment or per customer. | A shipment-level (or at least voyage-leg-level) allocated bunker-cost column, e.g. `FactShipment.AllocatedBunkerCostUsd`. | Implemented as a **billing-integrity proxy** (billed BAF revenue retained vs. billed BAF revenue gross, i.e. net of waivers/write-offs) — a real and useful KPI, but explicitly not the cost-pass-through ratio the name might suggest to a trade manager. |
| 7 | `XCT.FIN.CTS` | No overhead-allocation table — account management, shared systems, and facility overhead are not apportioned to individual customers anywhere in the contract. | A cost-allocation or activity-based-costing fact table apportioning indirect cost by `CustomerKey`. | Implemented as a **direct-cost-only** measure, explicitly labelled as such; full absorption cost-to-serve is out of scope for this dataset by design. |

No KPI in the required domain counts (Ocean 22, Landside 16, Warehouse 18, Air & LCL 9, Cross-cutting 7 — 72 total) was dropped or replaced with a fabricated column; every gap above is disclosed inline in its KPI's own **Formula**/**Watch-out** fields as well as here.

<!-- END -->
