# Day 11 — solutions

All figures computed from the built dataset. Reference values in
`04_learning/week2/_reference_answers.json`.

---

## Spaced recall answers

1. The **correlation between the per-row ratio and its own denominator**.
2. Because the numerator included **air freight revenue** (39,096 shipments,
   161.9M USD, 7.9% of total) while the denominator had no air FFE to match it —
   air consignments are not containers. Numerator and denominator described
   different populations.
3. **Where it is written**, in the filter context prevailing at that point.
4. Every row the same large total → missing context transition. Every row the same
   non-total number → filter replaced instead of intersected. Every row 1 or 0 or
   blank → variable evaluated in the wrong context.
5. `AVERAGEX` **skips blanks** rather than treating them as zero. So the naive
   revenue-per-FFE measure silently excluded the air rows and accidentally landed on
   the correct scope — 1,889.40 against a correct 1,889.30. Had blanks counted as
   zero it would have read 1,739.19.

---

## Exercise 11.1 — the comparison set

**`Revenue LY` is blank for 2021**, the first year in the data. There is no 2020 to
compare against. This matters more than it looks: a YoY column with a blank first
row is correct, and the instinct to "fix" it by coalescing to zero produces a
−100% growth figure that is pure fiction.

Revenue by year:

| Year | Revenue (USD) | YoY |
|---|---|---|
| 2021 | 148,018,896 (partial — from 21 Aug) | blank |
| 2022 | 374,844,416 | — (2021 partial) |
| 2023 | 401,643,584 | +7.15% |
| 2024 | 420,435,936 | **+4.68%** |
| 2025 | 443,628,992 | **+5.52%** |
| 2026 | 252,202,304 (partial — to 21 Aug) | — |

Note 2021 and 2026 are partial years. Any YoY involving them is meaningless, and a
report that shows it anyway will be quoted at you. The fix is a `DimDate` flag for
complete periods, or an explicit note on the visual.

**`Revenue YTD` and `Revenue Fiscal YTD` do not agree for calendar 2024**, because
the fiscal year starts 1 October. At 31 December 2024, calendar YTD holds twelve
months of 2024 while fiscal YTD holds only October to December — the first quarter
of FY25.

---

## Exercise 11.2 — the fiscal year offset

`DimDate` uses the convention that **the fiscal year is named for the year it ends
in**: October 2025 through September 2026 is **FY26**. You can verify it directly:

| Date | FiscalYear | FiscalYearLabel | FiscalQuarter |
|---|---|---|---|
| 2025-09-30 | 2025 | FY25 | 4 |
| 2025-10-01 | 2026 | FY26 | 1 |
| 2026-08-31 | 2026 | FY26 | 4 |

The 1 October boundary is visible as the point where `FiscalYear` increments and
`FiscalQuarter` resets to 1.

**Handing calendar 2025 when asked for FY25** means giving Jan–Dec 2025 instead of
Oct 2024–Sep 2025. The two windows overlap by nine months and differ by six: you
would be including Oct–Dec 2025 that belongs to FY26, and excluding Oct–Dec 2024
that belongs to FY25. Compute both in your model — the gap is in the tens of
millions, which is the kind of discrepancy that ends with finance not trusting the
BI team.

---

## Exercise 11.3 — the rolling 8-week window

At **31 August 2025**, `Schedule Reliability Rolling 8wk` = **0.6616** over
**4,049** port calls.

The naive weekly average gives **0.6591** against a pooled **0.6598** across the
whole dataset — a gap of about 0.1%.

**Why so close?** Two conditions have to hold for the naive average to be safe, and
here both do: port-call volume per week is fairly stable (no week carries wildly
more calls than another), and the on-time rate is not correlated with weekly volume.
Yesterday's rule applied to a coarser grain — the error scales with the correlation
between the rate and the weight.

**What would make it far off:** any week with unusually low volume and an unusual
rate. A blank-sailing week during Lunar New Year has few calls; if those few
happened to be badly delayed, the naive average would give that sparse week the same
weight as a full one. Meridian has ~1.5% blank sailings concentrated in the LNY
windows, which is not enough to bite — but a carrier with heavy seasonal
service suspensions would see a real gap.

**Ship the pooled version anyway.** The gap being small in this data is a fact about
this data, not a property of the method.

---

## Exercise 11.4 — find the crisis the headline is hiding

### The numbers, rolling 8 weeks at 31 August 2025

| Population | Reliability | Calls | Berth wait (h) |
|---|---|---|---|
| Network-wide | **0.6616** | 4,049 | — |
| NLRTM + USLAX | **0.4046** | 131 | **23.6** |
| All other ports | **0.6702** | 3,918 | **7.6** |

The crisis ports are **39.6% worse** than the rest of the network. The network-wide
figure sits **1.28% below** the unaffected ports.

Note that the 8-week window ending 31 August starts on 7 July, a week before the
congestion event opens on 14 July. So this reading already understates the crisis
twice over: once by pooling, and once because an eighth of the window predates the
problem. Measured over the congestion window alone the crisis ports run at **0.333**
against a network baseline of **0.660** — and that is the figure `validate.py`
gate 5 checks.

### Why a 40% local failure barely moves the headline

The crisis ports account for **131 of 4,049 calls — 3.2%** of the population. A
pooled average is a weighted mean, so the effect on the total is roughly
`3.2% × 39.6% ≈ 1.28%`, which is exactly what we observe. The arithmetic is working
correctly; the metric is simply answering a question that is not the one you need
answered.

Put differently: to move a network reliability KPI by 5 points you would need either
a catastrophe across a third of the network, or the entire network to degrade
slightly. A severe, localised, expensive failure is invisible by construction.

### What would have surfaced it on day one — and the trap inside the obvious answer

The obvious answer is "break the measure out by port and sort ascending". Do that
and you get this, restricted to ports with at least 10 calls in the window:

| Port | Reliability | Calls |
|---|---|---|
| KRULS | 0.273 | 11 |
| **USLAX** | **0.353** | **68** |
| HKKCG | 0.364 | 11 |
| HKHKG | 0.364 | 11 |
| MAAGA | 0.364 | 11 |
| … | | |
| **NLRTM** | **0.460** | **63** |

**The two crisis ports are not at the bottom of that list.** Fourteen ports sit
below 0.50, and most of them are there because eleven port calls is not enough to
estimate a rate. A sorted-ascending table hands you small-sample noise first and
buries the real event in the middle of it.

That is worth more than the tidy answer. A naive exception list ranked by *rate*
surfaces whichever member has the fewest observations, which is why threshold alerts
on sparse dimensions get switched off within a fortnight of being built.

What actually works, in rough order of cost:

1. **Rate with a minimum-volume filter.** `IF(COUNTROWS(FactPortCall) >= 25, [rate])`
   turns the same table into a usable one. Pick the threshold from the data, and put
   the call count on the visual so the reader can see what is behind each rate.
2. **Rank by impact, not by rate.** `calls × (network rate − port rate)` — the number
   of late calls this port contributed above baseline. USLAX and NLRTM go to the top
   immediately, because impact is what you can act on and a rate is not.
3. **Spread alongside the average** — the standard deviation, or the gap between best
   and worst volume-weighted decile. An average that holds steady while the spread
   widens is the signature of localised failure.
4. **An exception queue with a volume floor and a persistence rule** — flag a port
   only when it breaches for two consecutive weeks. Noise does not persist; a
   congestion event does.

### If you kept only one number

Put a **volume-weighted count of exceptions** next to it — late calls above
baseline, not ports below threshold. An average tells you the state of the whole; a
count of breaches tells you whether anything is broken; weighting by volume is what
stops the count from being dominated by the ports you have barely measured.

Neither alone is enough, and of the two, the one that fails silently is the average.

**This is the answer to give when an interviewer asks what you would put on a
one-page executive dashboard.** Most candidates list KPIs. The stronger answer is
that a page of averages cannot detect localised failure, and describes what you would
put alongside them — with the arithmetic to back it up.

---

## Exercise 11.5 — Lunar New Year and the comparability trap

### The trough is real and present every year

FFE volume, January against February:

| Year | LNY falls in | January | February | Feb ÷ Jan |
|---|---|---|---|---|
| 2023 | January (22nd) | 15,056.5 | 12,019.0 | **0.798** |
| 2024 | February (10th) | 15,833.3 | 13,035.0 | **0.823** |
| 2025 | January (29th) | 17,104.1 | 13,290.9 | **0.777** |
| 2026 | February (17th) | 18,124.0 | 15,826.4 | **0.873** |

February runs at 78–87% of January in every year. The seasonal effect is
unambiguous.

### But the February YoY comparison is *not* badly distorted — and that is the honest answer

**February 2025 versus February 2024: +1.96%.** Against an underlying growth trend of
about 5–6%, that is a mild understatement, not the collapse you might have predicted.

**Why the trap does not bite here.** The trough is modelled as a two-week collapse
followed by a two-week rebound, and Lunar New Year falls between 22 January and 17
February across these years. In every case the four-week disturbance **straddles the
January/February boundary**, so both months absorb part of it. Monthly aggregation
smooths the shift.

If you predicted a large distortion, you were reasoning correctly from a real
phenomenon and the data simply did not cooperate. That is worth more than a
confident guess: **you now know to check rather than assume**, which is the actual
transferable skill.

### Where the moving date *would* do real damage

**ISO-week comparisons.** Week 5 of 2025 contains the LNY trough; week 5 of 2024 does
not. A week-on-week-last-year comparison at that grain would show a swing of tens of
percent that is purely calendar. This is why carriers and retailers with Asian supply
chains either compare on a **lunar-aligned offset** (shift the prior year by the
number of days between the two new years) or aggregate to quarters.

**Quarterly aggregation** is the safest: Q1 contains the whole disturbance in every
year, so the comparison is clean. The general principle — **choose the aggregation
grain so that a moving event falls entirely inside one bucket in every period you
compare** — applies to Easter, Ramadan, Diwali and every other lunar or lunisolar
event, and is worth knowing by name.

---

## Exercise 11.6 — containers in transit

At **1 April 2026**: **6,089** containers loaded but not yet discharged.

**With the `= -1` branch removed**, the reading at 1 April 2026 changes only
slightly, but the reading near the end of the data **collapses**.

**The asymmetry.** On a historical date like 1 April 2026, almost every container
that was at sea has since been discharged, so it has a real discharge date and the
comparison `VesselDischargeDateKey > AsOf` catches it. The `-1` branch is nearly
redundant.

Near the end of the data, the containers actually at sea have **no discharge date
yet** — that event has not happened, so the column holds `-1`. Since
`-1 > 20260820` is false, every genuinely in-flight container is excluded and the
count falls towards zero.

**This is the worst possible failure mode for an operational dashboard:** the
measure validates perfectly against history and under-reports the present. Anyone
testing it on last quarter's data would sign it off. The people who find the bug are
the operations team wondering why the board is empty.

The general rule: **whenever an open interval is encoded as a sentinel rather than a
null, every comparison against it needs an explicit branch.** A `-1` is not a large
date and it is not a small one; it is not a date at all, and arithmetic on it is
meaningless.

---

## Reference values used above

| Quantity | Value |
|---|---|
| Rolling 8wk reliability, network, 2025-08-31 | 0.66164 (n=4,049) |
| Rolling 8wk reliability, NLRTM+USLAX | 0.40458 (n=131) |
| Rolling 8wk reliability, other ports | 0.67024 (n=3,918) |
| Berth wait, crisis vs other | 23.6 h vs 7.6 h |
| Pooled reliability, whole dataset | 0.65984 |
| Naive weekly-average reliability | 0.65911 |
| Revenue 2023 / 2024 / 2025 | 401.6M / 420.4M / 443.6M |
| YoY 2024 vs 2023 | +4.68% |
| YoY 2025 vs 2024 | +5.52% |
| FFE Jan/Feb 2025 | 17,104.1 / 13,290.9 |
| Feb 2025 vs Feb 2024 YoY | +1.96% |
| Containers in transit, 2026-04-01 | 6,089 |
| Fiscal year convention | named for the year it ends in; starts 1 Oct |
