# Day 15: The KPI-to-DAX translation method

> Time: 3 h · Spaced recall 10 min · Concept 45 min · Drill 75 min · Ship 30 min · Log 15 min

Week 2 gave you the mechanisms: `CALCULATE` modifiers, iterators, semi-additive
patterns, `TREATAS`, calculation groups. Starting today you spend them: `00_docs/KPI_DICTIONARY.md`'s 72 KPIs, turned into a real measure library. Before
you touch KPI #1, you need a method, or you will end up with 150 measures with 150
different naming conventions, no display folders, and no way for the next person
(including future you) to find anything. Today builds that method once, so the
next six days are execution, not invention.

---

## Spaced recall (10 min, closed book)

1. State the calculation-group edge from Day 14: what does it apply to by default,
   and what is the fix?
2. What is the fiscal year convention in this project (README §7), and how do you
   express it in `TOTALYTD`/`DATESYTD`?
3. Why did `Actual Schedule Reliability (via TREATAS)` (Day 13) disagree with
   `FactTarget`'s stored `ACT` row by 8.5 points, and what were the two reasons?
4. Name the three fact table shapes from Day 12 and one column from this model that
   is an example of each.
5. What display folder did you create on Day 8, and what has been added to it since?

---

## Concept

### Why a dedicated measure table, still

Day 8 already made the call: one blank table, `_Measures`, holds every measure in
this model, nothing lives on `FactShipment` or `FactPortCall` directly. Restate
why, because the KPI dictionary is about to make the payoff concrete: `_Measures`
has no relationships, so it can never accidentally filter anything; a measure
written against `FactPortCall` and one written against `FactShipment` sit in the
same browsable list instead of two different tables' field lists; and a calculation
group (Day 14) reshapes every measure in the model regardless of which physical
table "owns" it, so storage location and business meaning are already decoupled;
`_Measures` just makes that decoupling visible instead of accidental.

### The folder taxonomy: mechanism-based (Week 2) vs domain-based (Week 3)

Look at what actually exists in `_Measures` today:

| Folder | Added | Organised by |
|---|---|---|
| `01 Core` | Day 8 | base additive measures (`Revenue`, `TEU Volume`) |
| `02 Ratios` | Day 9 | the four percentage scopes, averaging-trap pairs |
| `03 Iterators` | Day 10 | `RANKX`/`SUMX`-built measures |
| `03 Inventory (semi-additive)` | Day 12 | point-in-time snapshot measures |
| `04 Time` | Day 11 | time-intelligence built by hand, pre-calc-group |
| `04 Targets & Segmentation` | Day 13 | `TREATAS`, ABC |

Two folders share `03`, two share `04`. That is not a bug to fix retroactively:
Power BI's Display Folder is a string, not a unique key, and each week's folder was
named after the *DAX mechanism* being learned that day, which is a fine organising
principle for a curriculum but a bad one for the finished model: nobody opening the
Fields pane six months from now thinks "I need the semi-additive measure," they
think "I need a warehouse inventory number." **From today, the organising axis
changes from mechanism to KPI domain**, because domain is how Week 4's five
dashboards will actually be built, and domain is how `00_docs/KPI_DICTIONARY.md`
itself is already split (§1–§5). Five new folders, numbered to continue past the
highest number already in use rather than colliding with it:

| Folder | Domain | KPI count |
|---|---|---|
| `05 Ocean Liner` | KPI_DICTIONARY §1 | 22 |
| `06 Landside` | §2 | 16 |
| `07 Warehouse & Inventory` | §3 | 18 |
| `08 Air & LCL` | §4 | 9 |
| `09 Cross-Cutting` | §5 | 7 |

A measure keeps whichever folder it already has if a mechanism folder is still the
more useful lens (the four percentage-scope measures from Day 9 are genuinely
about `CALCULATE` modifiers, not about one KPI domain), but any measure that *is*
one of the 72 dictionary KPIs gets re-foldered into its domain home as you touch it
this week, starting with three you already shipped: `Revenue per FFE` (Day 9) is
`OCN.REV.FFE`, `Lines Per Labour Hour` (Day 9) is `WHS.PRD.LPH`, and `Actual
Schedule Reliability (via TREATAS)` (Day 13) is a variant of `OCN.REL.SCHED`. You
re-folder the first two today; the rest of Ocean and Warehouse pick up the pattern
on Days 16 and 18.

### Naming and description convention

**Name:** Title Case, business language, matching the name a stakeholder would say
out loud, not the dictionary's dotted code. Where the dictionary's own DAX block
already names the measure (most of them do), use that name verbatim; consistency
with a document other people can also open beats inventing a "better" name.

**Description property, every measure, no exceptions:** one line, this shape:

```
[<KpiCode>] <what it measures, in the grain that matters>. <one clause on additivity
or the sharpest watch-out, if the measure has one>.
```

Concrete example, the one you are about to ship:

```
[OCN.VOL.TEU] Total container throughput in TEU, including empty repositioning by
convention. Additive at any grain; use OCN.MIX.LADEN to isolate laden-only.
```

The `[KpiCode]` prefix is not decoration: it is the join key back to
`00_docs/KPI_DICTIONARY.md`. Six weeks from now, "what does this measure actually
mean and what's its target band" is one search away instead of a guess. This is
also exactly what Checkpoint 3 (Day 21) will script against: every one of the 72
codes must appear in exactly one shipped measure's description, or be logged as a
deliberate gap.

**Format string:** set it from the KPI's `TargetUnit` where `FactTarget` states one
(`Pct`, `USD`, `Days`, `Hours`, `Count`), a ratio measure with no `%` format is a
silent trap for the next report author, who will format it as a whole number and
publish "0.87" instead of "87%."

### The naive/correct convention, formalised

Day 9 shipped one pair this way: `[DO NOT USE] LPH Naive`. `KPI_DICTIONARY.md`
turns out to be full of these, nine of the pairs you will build this week come
with a NAIVE block and a CORRECT block already written side by side in the
dictionary itself (you saw the first one, `OCN.REL.SCHED`, in this week's reading).
**The rule, made explicit today:** every time the dictionary shows a naive variant,
you ship *both*: the correct one under its plain business name, the naive one
named `[DO NOT USE] <Business Name> (naive)`, in the **same domain folder**, next
to each other, not filed away in some separate "deprecated" folder. The reason for
same-folder placement is deliberate: the entire teaching value of shipping the
naive version at all is that the next analyst who opens `05 Ocean Liner` looking
for schedule reliability sees the trap sitting right beside the correct measure,
with a description that says why it's wrong, not a clean folder with one measure
in it and no memory of the mistake anywhere. A trap nobody can see is a trap that
gets rebuilt from scratch by the next person who didn't do Week 2.

The naive measure's own description states the error mechanism in one line, e.g.:

```
[DO NOT USE, OCN.REL.SCHED naive] Averages 8 pre-aggregated weekly rates with equal
weight regardless of call volume. See "Schedule Reliability Rolling 8wk" for the
pooled, correct version.
```

### Worked walkthrough, end to end: OCN.VOL.TEU

Follow the dictionary entry through every step, because this exact sequence is what
you repeat 72 times.

**1. Read the dictionary entry.** Definition: total container throughput in TEU.
Formula: `Σ Teu`, includes empty repositioning by convention. Grain: any grain,
additive. Source: `FactContainerMove.Teu`. DAX is given verbatim.

**2. Copy the DAX, don't rederive it.**
```dax
TEU Volume := SUM ( FactContainerMove[Teu] )

Laden TEU Volume :=
CALCULATE ( SUM ( FactContainerMove[Teu] ), FactContainerMove[IsLaden] = 1 )
```

**3. Place it.** New measure, in `_Measures`, display folder `05 Ocean Liner`.

**4. Format.** Whole number, thousands separator, `TargetUnit = "TEU"` per
`FactTarget`, not a currency and not a percentage.

**5. Describe it**, using the template above:
```
[OCN.VOL.TEU] Total container throughput in TEU, including empty repositioning by
convention. Additive at any grain; use OCN.MIX.LADEN to isolate laden-only.
```

**6. Sanity-check against the dictionary's own watch-out before moving on.** The
dictionary flags that a round trip legitimately contributes twice (laden outbound +
empty/laden return are separate `ContainerMoveKey` rows); that's a fact about the
*grain*, not a bug to fix in the DAX, so nothing here changes; you just now know why
`TEU Volume` will not equal "unique containers handled" and can say so if asked.

That is the whole method. Six days, 72 KPIs, same six steps every time.

---

## Drill

Predictions first, in `predictions.md`, every time.

### Exercise 15.1: build the scaffolding (20 min)
Confirm `_Measures` exists (Day 8) and add the five domain folders from the table
above. An empty measure with a `-- placeholder` comment in each is enough to prove
the folder exists in the model, since Power BI does not let a folder exist with
zero measures in it. Predict, before you build them, whether Power BI's Fields pane
will let two folders share the same leading number (`03 Iterators` and
`03 Inventory (semi-additive)` already do), then go look at your own model and
confirm what you predicted.

### Exercise 15.2: ship OCN.VOL.TEU and OCN.VOL.FFE (15 min)
Build both exactly as shown in the walkthrough, plus `FFE Volume` (same pattern,
`FactContainerMove[Ffe]`). Predict, before checking, which of the two, TEU or FFE,
will be the larger number at the grand total, and by roughly what factor. (Hint:
what is a 20' box in each unit, per `00_docs/SCHEMA_CONTRACT.md` §1.9's
`TeuFactor`/`FfeFactor`?)

### Exercise 15.3: re-folder two Week 2 measures into their domain home (15 min)
Move `Revenue per FFE` (Day 9) into `05 Ocean Liner` and `Lines Per Labour Hour`
(Day 9) into `07 Warehouse & Inventory`. Add the `[KpiCode]`-prefixed description
to each, using `OCN.REV.FFE` and `WHS.PRD.LPH` respectively, pulling the one-line
summary straight from the dictionary. This is not busywork: it is the first proof
that the taxonomy from the Concept section actually organises measures you already
trust, not just new ones.

### Exercise 15.4: the naive/correct pair, formalised (20 min)
`00_docs/KPI_DICTIONARY.md`'s `OCN.REL.SCHED` entry gives you both DAX blocks
already written. Ship both, named per this day's convention:
`Schedule Reliability Rolling 8wk` (correct) and
`[DO NOT USE] Schedule Reliability Rolling 8wk (naive)`, both in `05 Ocean Liner`.
Predict, before building, roughly how far apart the two will land at the grand
total across the full history (not just one congestion-affected window), will the
gap be as dramatic as Day 9's Lines-per-Labour-Hour gap, smaller, or about the
same? Then build both and compare. Write one sentence on why a gap that is small at
the grand total does not mean the naive version is safe to ship (hint: what does
the dictionary's own commentary say happens to this specific gap *inside* the
congestion window, and why would a grand-total comparison hide that entirely?).

### Exercise 15.5: audit for missing descriptions (5 min)
Open Model view, list every measure in `_Measures`, and confirm each of the eight
measures you have shipped across Weeks 2–3 so far has a non-empty `description`
property. If any don't, this is the moment to fix it: Day 21's checkpoint will
script exactly this check across all ~150 measures, and it is much cheaper to keep
the habit now than to retrofit it in Week 6.

---

## Ship

`_Measures` now has all nine folders (`01`–`04` from Weeks 1–2, `05`–`09` new
today), `TEU Volume`, `FFE Volume`, both `OCN.REL.SCHED` variants, and two
re-foldered Week 2 measures with descriptions added. This is the seed the rest of
the week builds on.

```
git add .
git commit -m "Day 15: KPI-to-DAX translation method, domain folder taxonomy, naive/correct convention formalised"
```

---

## Log

What clicked / what did not / what to re-ask.

---

## Exit criteria

- [ ] `_Measures` has all five domain folders (`05`–`09`), each containing at least
      one measure.
- [ ] `TEU Volume` and `FFE Volume` exist, formatted correctly, described with the
      `[KpiCode]` convention.
- [ ] Both `OCN.REL.SCHED` variants exist, named per the `[DO NOT USE]` convention,
      sitting in the same folder, and you can state from your own numbers how far
      apart they land.
- [ ] `Revenue per FFE` and `Lines Per Labour Hour` are re-foldered and described.
- [ ] You can state, without notes, why the naming/description/folder convention
      exists, not "because the instructions said so," but what it prevents.
- [ ] Predictions recorded, misses annotated.
