# Day 2 — Solutions

## Spaced recall

1. Booking → Shipment (1 → 0/1, occasionally 1 → many) → Container (1 → 1/many) → Equipment event (1 → many, sequential); separately, House B/L → Master B/L is many → 1.
2. Backhaul carries the structurally lighter direction of trade — the manufacturing/export volume simply doesn't exist in the reverse direction at the same scale, so lower load factor is geography, not a sales failure.
3. A rollover is booked cargo that does not make it onto the specific vessel voyage it was booked for and is carried forward to a later sailing — it is a capacity/space outcome, not necessarily anything being "late" in the sense of missing a deadline (the cargo may still arrive within an acceptable window, just on a different voyage than planned).
4. Location: demurrage is charged while the container is still inside the terminal (port-side); detention is charged once it has left the terminal and is out with the customer (street-side).
5. BCO (optimises landed cost and supply-chain reliability), NVOCC (optimises the margin spread between wholesale and retail ocean rates across volume), Freight Forwarder (optimises service breadth and reliability across multiple carriers/modes), 3PL (optimises operational KPIs inside the warehouse, not ocean freight rates), SME Direct (optimises price and cutoff flexibility, with low negotiating leverage on space).
6. Because demurrage/detention only accrue when a container is sitting still rather than moving — a spike in D&D revenue is frequently a symptom of network congestion or slow customer/customs turnaround, meaning the *operation* is degrading even as that one revenue line rises.

---

## Drill 1 — ISO 6346 check digit, implemented

```python
LETTER_VALUES = {}
_v = 10
for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    while _v % 11 == 0:
        _v += 1
    LETTER_VALUES[ch] = _v
    _v += 1

def iso6346_check_digit(ten_chars: str) -> int:
    total = 0
    for i, ch in enumerate(ten_chars.upper()):
        value = LETTER_VALUES[ch] if ch.isalpha() else int(ch)
        total += value * (2 ** i)
    remainder = total % 11
    return 0 if remainder == 10 else remainder
```

**(a) `CSQU305438`** → sum of weighted products = 6,185 → 6,185 mod 11 = 3 (562×11 = 6,182; 6,185 − 6,182 = 3). **Check digit = 3.** Matches the worked example in the Concept section and the real-world container number `CSQU3054383`. `iso6346_check_digit("CSQU305438")` returns `3`.

**(b) `MSCU6639871`** — first 10 characters: `MSCU663987`; stated check digit: `1`.

| Pos | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| Char | M | S | C | U | 6 | 6 | 3 | 9 | 8 | 7 |
| Value | 24 | 30 | 13 | 32 | 6 | 6 | 3 | 9 | 8 | 7 |
| ×2^pos | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256 | 512 |
| Product | 24 | 60 | 52 | 256 | 96 | 192 | 192 | 1,152 | 2,048 | 3,584 |

Sum = 24+60+52+256+96+192+192+1,152+2,048+3,584 = **7,656**. 7,656 ÷ 11 = 696 exactly, remainder **0**. Computed check digit = **0**.

**Verdict: INVALID.** The number as given carries check digit `1`, but the correct check digit for `MSCU663987` is `0`. This is exactly the scenario you'd hit with a mis-keyed or corrupted container number in a real EDI feed — the fix is not to "round" or assume it's close enough; a container number with a failing check digit should be flagged, not silently accepted, because you cannot be sure which digit is wrong without going back to source. If your function returned `0` for this case, you did it correctly — the point of including an invalid case in the drill is to prove your implementation doesn't just always agree with whatever digit it's handed.

**(c)** Any self-invented 10-character `<owner 3 letters><category 1 letter><serial 6 digits>` string will do — the marking criterion is that your by-hand tier-by-tier working (value → multiply by 2^position → sum → mod 11 → remainder-10 special case) matches what your function returns for the same input. If they disagree, the almost-always culprit is either (i) using the position starting from 1 instead of 0, which shifts every multiplier by a factor of 2 and produces a completely different sum, or (ii) forgetting the "remainder 10 → check digit 0" rule, which only bites roughly 1 in 11 times, so it's easy to miss until a drill or a real container forces it.

## Drill 2 — IMO check digit

IMO `9247398` — first six digits `924739`, check digit `8`.

| Digit | 9 | 2 | 4 | 7 | 3 | 9 |
|---|---|---|---|---|---|---|
| Weight | ×7 | ×6 | ×5 | ×4 | ×3 | ×2 |
| Product | 63 | 12 | 20 | 28 | 9 | 18 |

Sum = 63+12+20+28+9+18 = **150**. 150 mod 10 = **0**.

**Verdict: FAIL.** The computed check digit is `0`; the number as given ends in `8`. This is not a valid IMO number as stated. As with Drill 1(b), the correct response in a real data-quality context is to flag the record and trace it back to source, not to assume the vessel is fine because the number "looks" plausible (seven digits, sensible-looking) — plausible-looking and valid are different properties, and the check digit is specifically there to catch the difference.

## Drill 3 — HS code truncation

`HsCode6 = 851712` → `HsCode4 = 8517` → `HsCode2 = 85`.

Why the Indian (`85171210`) and US (`85176200`) extracts cannot be assumed to describe the same product: both share the internationally harmonised 6-digit subheading only up to the point where their digits actually match — and here they diverge already at the fifth/sixth digit (`85171` vs `85176`), meaning they aren't even the same 6-digit HS subheading, let alone the same 8-digit national line. Even where two countries' 8-digit codes *do* share the same leading six digits, the 7th digit onward is each country's own national tariff schedule, built independently by that country's customs authority for its own duty and statistical purposes — there is no guarantee, and often no truth, that the same 8th digit means the same thing in India's schedule as in the US's. The **only** level at which you can safely compare across these two national extracts is the 6-digit subheading — and in this specific case, since the two given codes don't even agree at 6 digits, you'd correctly conclude these are not the same product line at all, not merely "not comparable at 8 digits."

## Drill 4 — Incoterms applied

The facts given — Meridian arranges and pays ocean freight through to the destination port; risk passes to the buyer the moment the container is loaded on board at origin; the buyer's own broker arranges and pays insurance — match **CFR (Cost and Freight)** exactly: seller/carrier pays main carriage to destination, risk transfers on loading at the port of shipment, and insurance is left to the buyer's discretion (as it is for every Incoterm except CIF and CIP).

**The one fact that would change under CIF**: everything else stays identical (same risk-transfer point, same freight arrangement — CIF and CFR share both) — the only change is that **the seller, not the buyer's broker, would be contractually obliged to arrange insurance**, and specifically only to the *minimum* cover level (Institute Cargo Clauses C). A common wrong answer here is to say "risk would transfer later under CIF" — it does not; CIF and CFR transfer risk at exactly the same point (on board at origin). The entire difference between CFR and CIF is the insurance obligation, nothing about risk timing.

## Drill 5 — DCSA journey classification

| EventCode | Journey | Reason |
|---|---|---|
| `GTIN` (gate in) | **Equipment** | Happens to the physical box at a terminal/depot gate, independent of which commercial shipment (if any) it's carrying. |
| `ARRI` (vessel arrival) | **Transport** | Happens to the vessel/voyage as a whole — one arrival event is shared across every container aboard. |
| `CONF` (booking confirmed) | **Shipment** | A commercial-transaction milestone attached to the booking/house bill, not to any specific physical box. |
| `STRP` (stripping) | **Equipment** | A physical operation performed on the container itself (deconsolidating its contents at a CFS), independent of the commercial shipment record. |

If you classified `STRP` as Shipment because it "relates to LCL cargo owners," that's a defensible-sounding but incorrect instinct — the *event itself* is a thing that happens to the box at a facility, which is what makes it Equipment-journey; the commercial consequence for the shipper is a separate, correlated fact, not the event's own classification.
