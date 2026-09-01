# Day 31 — Row-level security: two real roles, and where they quietly stop working

> Time: 3 h · Spaced recall 10 min · Concept 45 min · Drill 80 min · Ship 30 min · Log 15 min

Every measure you've built so far assumes one reader sees everything. Today
that assumption breaks on purpose. Row-level security (RLS) is a DAX filter
applied to a table before anything else runs — and the two roles you build
today will surface the same lesson twice: a security filter only reaches as
far as the relationships (and their active/inactive state) actually carry it.

---

## Spaced recall (10 min, closed book)

1. What does `TREATAS` do, and which of its arguments supplies the values
   versus which one gets filtered?
2. `DimLocation[TradeRegion]` and `DimLocation[Region]` both look like region
   columns. Which one bridges to `FactTarget`, and what happens if you use the
   wrong one?
3. What does `USERELATIONSHIP` do, and why does this model need it at all
   given that a physical relationship already exists between the two tables
   it's activating?
4. What is `DimCustomer`'s SCD type, and what does `IsCurrent` mean on it?
5. Name the Pro and PPU scheduled-refresh limits from Day 30.

---

## Concept

### What an RLS role actually is

A **security role** is a named set of **table filters** — one DAX boolean
expression per table, evaluated as if it were a permanent `CALCULATE` filter
argument wrapped around every query a member of that role runs. Unlike a
measure's filter, it cannot be turned off by the report, bypassed by a
different visual, or removed by `ALL()` — `REMOVEFILTERS` clears filters
built from visuals, slicers and `CALCULATE`, but a security role's filter is
applied at the storage-engine level, beneath all of that.

You define a role's filter on **one table at a time**, as a DAX expression
that must evaluate to `TRUE`/`FALSE` per row:

```dax
[SalesRegion] = "APAC"
```

That filter propagates outward through the model's relationships exactly the
way any other filter does — through **active** relationships, in whichever
direction cross-filtering is set. Everything you already know about filter
propagation from Week 2 applies here without exception; RLS is not a separate
mechanism, it is the same mechanism with the filter source moved from a
visual to a role membership.

### Role 1 — `Sales - APAC`, filtering `DimCustomer`

`DimCustomer[SalesRegion]` takes four values: `EMEA` (1,604), `APAC` (1,561),
`Americas` (705), `ANZ` (300). A role restricting a regional sales lead to
their own book of business filters `DimCustomer` directly:

```dax
[SalesRegion] = "APAC"
```

`CustomerKey` is a direct foreign key on almost every fact table in this model
— `FactBooking`, `FactShipment`, `FactShipmentMilestone` (via `ShipmentKey`),
`FactContainerMove`, `FactFreightCharge`, `FactTransportLeg`,
`FactWarehouseTask`, `FactInventorySnapshot` — so this one filter reaches
nearly the whole model in a single hop, no `TREATAS` required.

**The SCD2 trap — and it cuts the opposite way from what habit suggests.**
`DimCustomer` is SCD2 (Day 6/7): a real customer like `CUS0003` can have
**more than one row**, one per historical version, only one of which is
current (`IsCurrent = 1`), and — this is the part that matters —
`SCHEMA_CONTRACT.md` is explicit that `FactShipment[CustomerKey]` is
**"SCD2-resolved to the version valid at booking date,"** not to the current
version. A shipment booked two years ago, under a customer's *older* SCD2
version, still carries that older version's `CustomerKey` forever — the fact
row never gets re-pointed at the current version after the customer changes.

The instinct carried over from Week 1 measure-writing is "always add
`IsCurrent = TRUE()` to an SCD2 filter." For a role whose job is to gate
**historical fact data**, that instinct is backwards, and it is checkable:

```dax
-- WRONG for this purpose — silently drops real, in-scope revenue
[SalesRegion] = "APAC" && [IsCurrent] = TRUE ()

-- RIGHT — reaches every version's CustomerKey, current or not
[SalesRegion] = "APAC"
```

Measured on the frozen history: **368 of DimCustomer's 1,561 `APAC`
customer-versions are non-current**, and **19,318 `FactShipment` rows
(worth $81.79M in revenue) key to one of those non-current versions.** Adding
the `IsCurrent` guard does not make the role safer — it silently excludes
$81.79M of legitimately APAC-scoped revenue, because those rows' `CustomerKey`
values point at exactly the DimCustomer rows the guard just removed from
visibility. This works cleanly here specifically because `SalesRegion` itself
never changes across a given customer's SCD2 history (verified: zero
customers have it differ between versions) — so every version of an APAC
customer is safely APAC, and there is no reason to prefer the current one.

**The guard is still sometimes correct — just not by default.** If you filter
a role on an attribute that genuinely *does* vary between versions — `DimCustomer[AccountManagerEmail]`
is a real example (`CUS0003` alone moved from `carlos.al-farsi@…` to
`yuki.obrien@…` between its two versions) — then "all versions" and "current
only" give **different, both-defensible** answers to two different questions:
"show me everything this account manager has ever touched" versus "show me
only what belongs to the customers currently assigned to them." Which one is
correct is a business decision to make explicit in the role's documentation,
not a habit to apply uniformly. The lesson from `SalesRegion` is not "never
guard on `IsCurrent`" — it is "know which of your filtering columns actually
varies across versions before deciding, because guessing produces a role that
looks correct in every quick check and is silently wrong by a measurable
amount," the same "plausible-looking wrong number" shape you've now seen from
`TREATAS` reversed (Day 13) and the naive average (Day 9).

### Role 2 — `Region - Americas`, filtering `DimLocation`, and where it stops

`DimLocation[TradeRegion]` takes five values — the same ones you bridged
`FactTarget` through in Day 13: `Americas`, `Asia`, `Europe`, `MEA`,
`Oceania`. The role:

```dax
[TradeRegion] = "Americas"
```

Several fact tables carry **more than one** foreign key into `DimLocation` at
once — `FactShipment` alone has `LocationKeyOrigin`, `LocationKeyDestination`,
`LocationKeyPol`, `LocationKeyPod`; `FactTransportLeg` has
`LocationKeyOrigin`/`LocationKeyDestination`. Power BI allows only **one**
active relationship between any two tables at a time. That means for any fact
table with multiple location roles, at most one of those foreign keys has an
**active** relationship to `DimLocation` — the rest are necessarily inactive,
the same role-playing-dimension shape Day 9 introduced `USERELATIONSHIP` for.

**This is the sharp edge, and it is real, not hypothetical: an RLS filter on
`DimLocation` only propagates through whichever relationship is active.** If
`LocationKeyOrigin` is the active path, a member of `Region - Americas` sees
shipments correctly restricted by *origin* — and a measure that reports on
`LocationKeyPod` (destination port) through the *inactive* relationship is
**not restricted by this role at all**, unless that measure explicitly
reactivates the path with `USERELATIONSHIP` — and a measure written with
`USERELATIONSHIP` does not automatically inherit the role's filter along that
newly-activated path either. This is not a corner case you might hit; it is
the default behaviour of every multi-role-playing fact table in this model,
and it is exactly why Exercise 31.2 has you go find out, on the real model,
which of `FactShipment`'s four location roles the role actually restricts.

### Plugging the `FactTarget` gap with the Day 13 pattern

`FactTarget` has **no relationship at all** to `DimLocation` — Day 13 covered
exactly why (region/month grain versus daily/location grain). A `TradeRegion`-based
role therefore does not restrict `FactTarget` by default: an APAC sales lead
placed under `Region - Americas` (hypothetically, if regions overlapped a
customer's assignments) would see every row of budget/target data
unrestricted, regardless of region. The fix reuses Day 13's `TREATAS`
directly, but as a **role filter on `FactTarget` itself**, not as a measure:

```dax
-- Role filter on FactTarget
COUNTROWS (
    CALCULATETABLE (
        VALUES ( DimLocation[TradeRegion] ),
        TREATAS ( VALUES ( FactTarget[Region] ), DimLocation[TradeRegion] ),
        DimLocation[TradeRegion] = "Americas"
    )
) > 0
```

This says: "keep this `FactTarget` row only if its `Region` value, mapped
through the same bridge Day 13 built, is in the set the role is scoped to."
It is more machinery than the one-line `DimCustomer`/`DimLocation` filters
above, and that asymmetry is the lesson: **a table with no physical
relationship to your filtering dimension needs its own explicit role rule,
every time** — RLS does not "figure out" a virtual relationship on its own
any more than a measure does.

### Testing: View As, and what it does not catch

**View As Roles** (Modeling ribbon → *View as*) lets you preview the model as
a role member without logging in as anyone else. It is necessary but not
sufficient: View As applies the role's filters and shows you the *result*,
but it will not tell you *which relationship* carried (or failed to carry)
the filter to a given visual — that diagnosis is on you, using what you know
about active/inactive relationships from Day 9 and this lesson. A role that
"looks right" in a summary card can still be leaking an unrestricted number
through one specific measure that happens to touch an inactive path — the
only way to catch that is to deliberately build a visual against each
role-playing foreign key and check it under View As, not just eyeball the
first table you think of.

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 31.1 — build and test `Sales - APAC`, both ways (25 min)
Build the role twice: once as `[SalesRegion] = "APAC"` alone, once with
`&& [IsCurrent] = TRUE()` added. Put `Revenue` on a card, View As each version
in turn. Predict, before checking, which one returns the larger number and
roughly how much larger — you have everything you need to estimate it from
the Concept section's counts (368 non-current APAC customer-versions) without
running anything yet. Then verify against a normal measure written as your
own cross-check:
`CALCULATE([Revenue], DimCustomer[SalesRegion]="APAC")` versus the same with
`DimCustomer[IsCurrent]=TRUE()` added.

### Exercise 31.2 — find the leak (25 min)
Build `Region - Americas` on `DimLocation[TradeRegion]`. Put two measures side
by side: one that sums `FactShipment[Revenue_usd]` (reaching `DimLocation`
through whichever relationship is active), and one built to force the
*destination*-side location via `USERELATIONSHIP` if that's the inactive one
(or vice versa — check which is active first). Predict, before checking under
View As, whether both numbers shrink to Americas-only, or whether one stays
at the unrestricted total. Write two sentences on what this means for anyone
relying on this role to actually gate destination-side reporting.

### Exercise 31.3 — plug the `FactTarget` gap (20 min)
Build the `TREATAS`-based role rule on `FactTarget` from the Concept section.
Put `FactTarget[TargetValue]` on a card, View As `Region - Americas`, with
and without the `FactTarget` rule active. Predict both numbers before
checking, and confirm the rule is what closes the gap.

### Exercise 31.4 — a role where the guard genuinely matters (15 min)
Build a third, hypothetical role, `AM - Carlos`, filtering
`DimCustomer[AccountManagerEmail] = "carlos.al-farsi@meridiangl.com"`, once
with no `IsCurrent` guard and once with it. `CUS0003` is a confirmed real
customer whose `AccountManagerEmail` changed between its two SCD2 versions.
Predict, before checking: does the ungated version let through revenue this
customer generated *after* the account moved to a different manager? Explain
in 2–3 sentences why this case is genuinely different from `Sales - APAC` —
name the one empirical fact from the Concept section that makes the two roles
behave oppositely under the same guard.

---

## Ship

Add both roles to the model exactly as built (`Sales - APAC` on
`[SalesRegion] = "APAC"` with **no** `IsCurrent` guard, `Region - Americas`
with the `FactTarget` `TREATAS` rule), plus a short table in
`03_powerbi/rls_roles.md` recording, per role: which tables it restricts
directly, which fact tables it reaches only through an inactive relationship
(and therefore does **not** restrict), whether its filtering column varies
across a customer's SCD2 history (and therefore whether an `IsCurrent` guard
would help or hurt), and the `View As` numbers you verified each against.

```
git add .
git commit -m "Day 31: RLS roles Sales-APAC and Region-Americas built, TREATAS gap on FactTarget closed, tested with View As"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] Both roles exist, tested with `View As`, and match an independently
      written `CALCULATE` cross-check.
- [ ] You can state, without notes, why an RLS filter on `DimLocation` does
      not automatically restrict a fact table's inactive location roles, and
      you found a concrete example of this on the real model.
- [ ] You can explain why `Sales - APAC` is *more* correct without an
      `IsCurrent` guard than with one, using the measured $81.79M gap, and can
      state the one condition (whether the filtering attribute itself varies
      across SCD2 versions) that decides whether a given role needs the guard
      at all.
- [ ] The `TREATAS`-based `FactTarget` role rule exists and you verified,
      with numbers, that it closes the gap a plain `DimLocation` filter leaves
      open.
- [ ] Predictions recorded, misses annotated.
