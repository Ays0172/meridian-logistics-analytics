# Day 37: solutions

These are model answers, not a single graded number the way Weeks 1–2's solutions
were: a case drill's answer depends on the exact population and window you build,
so grade your own memo against the **shape** of each answer below and against the
handful of figures that are already fixed and checkable from earlier days. Where a
number here is one you have to compute fresh for your own build (not previously
established in this course), it's marked **[your figure]** rather than invented.

---

## Case 37.1, CFO, margin dispersion

**Define.** Standard deviation of `FactShipment[GrossMarginPct]` is the cleanest
single dispersion metric for a slide, easy to compute pooled, easy to explain.
Pair it with the loss-making share (`% of shipments with GrossMarginPct < 0`) as a
second, more visceral number for the same idea.

**Locate.**
```dax
Crisis Population :=
FILTER (
    FactShipment,
    LOOKUPVALUE ( DimLocation[LocationCode], DimLocation[LocationKey], FactShipment[LocationKeyPol] ) IN { "NLRTM", "USLAX" }
        || LOOKUPVALUE ( DimLocation[LocationCode], DimLocation[LocationKey], FactShipment[LocationKeyPod] ) IN { "NLRTM", "USLAX" }
)
```
`LOOKUPVALUE`, not `RELATED`, on purpose: `FactShipment` carries multiple
location-role foreign keys (`LocationKeyOrigin`/`Destination`/`Pol`/`Pod`) to the
same `DimLocation`, so per Day 5's role-playing-dimension rule only one of those
relationships can be active at a time — `RELATED(DimLocation[LocationCode])`
alone would resolve through whichever one that is, not necessarily Pol or Pod.
`LOOKUPVALUE` looks the code up directly by key, independent of which
relationship happens to be active. (In practice, build this as two
`CALCULATE`s, one filtered on POL and one on POD, unioned, since a shipment can
touch either leg. Restrict `DimDate[Date]` to 14 Jul-14 Sep for 2025 and again
for 2024.)

**Compute.**
```dax
Margin StdDev := STDEVX.P ( FactShipment, FactShipment[GrossMarginPct] )
Loss-Making Share := DIVIDE ( CALCULATE ( COUNTROWS ( FactShipment ), FactShipment[GrossMarginPct] < 0 ), COUNTROWS ( FactShipment ) )
```
Network-wide baseline: mean margin **0.1802**, loss-making share **2.26%** (README
§6). Your crisis-window, crisis-port figure should show a wider spread and a
higher loss-making share than baseline (**[your figure]** for the exact numbers),
but if your 2025-crisis figure comes back *narrower* than the 2024 same-window
baseline, that is a signal to re-check your port/date filter before trusting it.

**Caveat.** Demurrage is booked on `FactFreightCharge`, not netted into
`FactShipment[GrossMarginPct]` unless your model explicitly rolls charge lines up
to the shipment. Per `SCHEMA_CONTRACT.md` §3.3, demurrage charge-line *volume* rose
**×3.1** in the crisis window, so a margin-dispersion story told purely from
`FactShipment` may understate how much the crisis actually cost, or overstate it
if demurrage revenue is separately inflating a different P&L line the CFO is also
watching. Say this explicitly rather than letting the slide imply completeness.

**Recommend.** If dispersion widened materially: propose a demurrage-inclusive
margin view as the next iteration, and flag the crisis window as the reason Q3
average margin should not be extrapolated forward without adjustment.

---

## Case 37.2, key account, DIFOT drop

**Define.** Quarterly `IsPerfectOrder` rate for the one `CustomerKey`, decomposed
into its four components.

**Locate/Compute.**
```dax
Cust Perfect Order Rate := CALCULATE ( AVERAGE ( FactShipment[IsPerfectOrder] ), DimCustomer[CustomerCode] = "CUS-XXXX" )
Cust On-Time            := CALCULATE ( AVERAGE ( FactShipment[IsOnTime] ), DimCustomer[CustomerCode] = "CUS-XXXX" )
Cust In-Full            := CALCULATE ( AVERAGE ( FactShipment[IsInFull] ), DimCustomer[CustomerCode] = "CUS-XXXX" )
Cust Not-Damaged        := CALCULATE ( 1 - AVERAGE ( FactShipment[IsDamaged] ), DimCustomer[CustomerCode] = "CUS-XXXX" )
Cust Doc Clean          := CALCULATE ( AVERAGE ( FactShipment[IsDocumentationClean] ), DimCustomer[CustomerCode] = "CUS-XXXX" )
Cust Shipment Count     := CALCULATE ( COUNTROWS ( FactShipment ), DimCustomer[CustomerCode] = "CUS-XXXX" )
```
Break out by `DimDate[Quarter]` on rows. **[your figure]** for the actual
customer and quarter you pick, but the decomposition itself is the deliverable:
you are looking for which of the four component rates dropped the most
quarter-over-quarter.

**Sample-size check.** A Global Key Account typically ships enough volume that a
quarter is a meaningful sample; an SME-tier account might not. Report
`Cust Shipment Count` for the quarter alongside the rate: if it is under roughly
30–50 shipments, say explicitly that the quarterly rate carries real sampling
noise, the same caution Day 11 applied to sparse ports before ranking them.

**Congestion overlap check.** Cross-reference the customer's shipment lanes/ports
against `NLRTM`/`USLAX` and the 14 Jul–14 Sep 2025 window. If their volume
concentrates there, the honest message is "you were caught in a network-wide
event, and the network figures (schedule reliability 0.662 vs 0.670 baseline,
Day 11) show it wasn't specific to your account." If it doesn't overlap, the
degradation is customer- or lane-specific and needs a different explanation.

**Recommend.** Name the worst-performing component explicitly in the reply to the
customer: "on-time performance" reads very differently from "documentation
turnaround," and the account manager needs to know which conversation to have.

---

## Case 37.3, ops, reefer free-time

**Locate/Compute.**
```dax
Reefer Move Share := DIVIDE ( CALCULATE ( COUNTROWS ( FactContainerMove ), RELATED ( DimEquipment[IsReefer] ) = 1 ), COUNTROWS ( FactContainerMove ) )
-- ≈ 8.7%

Reefer D&D Share := DIVIDE ( CALCULATE ( SUM ( FactFreightCharge[Amount_usd] ), FactFreightCharge[IsDemurrage] = 1 || FactFreightCharge[IsDetention] = 1, RELATED ( DimEquipment[IsReefer] ) = 1 ), CALCULATE ( SUM ( FactFreightCharge[Amount_usd] ), FactFreightCharge[IsDemurrage] = 1 || FactFreightCharge[IsDetention] = 1 ) )
-- ≈ 20%
```
Both figures are already established (Day 9 spaced recall Q5): reefers are **8.7%**
of container moves but roughly **20%** of D&D charge value: more than double their
share, which is exactly the disproportion ops is asking about.

**Estimating the ask (+1 free day).** The honest approach: filter
`FactContainerMove` to reefer moves with `IsPastFreeTime = 1` and
`FreeTimeDaysUsed` in the range that a 4th free day would newly cover (i.e.
currently in tier 1, days 1–3 past the current 3-day free window). Sum the
demurrage charged specifically for that first tier-1 day across those moves: that
sum is your estimate of revenue/cost exposure a +1-day change would remove. State
plainly that this is an estimate bounded by the current tier structure in
`DimEquipment`, not a re-run of the generator with a genuinely different policy.
**[your figure]** for the actual dollar estimate on your build.

**Recommend.** Present both shares (8.7% vs ~20%) as the headline disproportion,
the tier-1 estimate as a bounded first-order cost, and recommend a carrier
conversation informed by, but not overclaiming precision from, the estimate.

---

## Case 37.4, finance, budget reconciliation

This one has a fixed, checkable answer already built in Days 13 and 36: grade
yourself directly against it:

| | Value |
|---|---|
| `FactTarget` stored `ACT`, Americas, June 2025 | **74.71%** |
| Recomputed via `TREATAS`/`DimLocation[TradeRegion]` join | **66.22%** |
| Gap | **8.5 points** |

**Mechanism, in one paragraph (this is the graded part):** `FactTarget`'s stored
`ACT` figure for this KPI was itself built as an unweighted mean across trade
lanes rather than a call-weighted pooled figure: the same shape of error Day 9
measured for lines-per-labour-hour, except this time baked into a static planning
table rather than a live DAX measure, which is why nobody caught it in Week 2. The
recomputed, call-weighted figure (66.22%) is the more defensible number.

If your write-up did not name the mechanism, just said "they use different
definitions" without saying *which* averaging error causes it: that is the
specific gap to close before Day 39, because this exact finding is one of the four
STAR stories.

**Recommend.** Board deck should carry the recomputed figure with a one-line note
on the discrepancy; the upstream fix (how `FactTarget.ACT` rows get produced)
should be logged as a follow-up, not patched by silently overwriting the stored
value.

---

## Case 37.5, board, lane recovery slide

**Compute (pooled, indexed to each direction's own baseline).**
```dax
Revenue per FFE := DIVIDE ( SUM ( FactShipment[Revenue_usd] ), SUM ( FactShipment[Ffe] ) )
-- computed per Direction, per period (pre / during / post 14 Jul–14 Sep 2025)
```
Headhaul pre-crisis baseline sits near the full-period figure of **2,482.78**;
backhaul near **1,286.66** (README §6, full-period pooled figures: your
period-bucketed figures will differ somewhat from these full-period numbers, which
is expected). Index each period to its own direction's pre-crisis value rather
than comparing the two directions' absolute dollars. **[your figure]** for the
actual indexed recovery percentages.

**Structural caveat, stated on the slide:** backhaul runs at roughly **0.52×**
headhaul revenue per FFE structurally (`SCHEMA_CONTRACT.md` §3.2): this is a
standing feature of trade imbalance, not something the congestion event changed,
and a slide that shows two absolute bars side by side invites the board to read
"backhaul is worse" when the real question is "did *either* direction recover
toward its own normal."

**Concentration footnote:** top-10 customers carry 27.8% of total revenue
(README §6), worth one footnote line if the board is likely to ask whether the
recovery number is being carried by a handful of large accounts.

**Recommend.** State plainly which direction recovered faster in your indexed
view and by how much, and whether "recovering" or "still depressed" is the
one-word verdict as of the latest data in your build.
