# Day 7 — Checkpoint 1
> Time: 2.5 h · Quiz 60 min · Recording 30 min · Review 45 min · Log 15 min

This day's time breakdown deliberately differs from the rest of the week's template — there's no new Concept to teach today, and no Ship artefact beyond the checkpoint itself. Today proves what you actually retained, out loud and under closed-book conditions, before Week 2 builds on top of it.

## Spaced recall (10 min, closed book)

Six questions pulled across the whole week, not just yesterday — this is your last warm-up before the quiz proper, and a rough guide to which of the 25 questions below you're already solid on.

1. State the entity chain from booking to bill of lading, with the cardinality of each hop.
2. What is the ISO 6346 check-digit rule for a remainder of 10?
3. State `FactContainerMove`'s grain in one sentence.
4. Why does Parquet survive a reordered-column partition and CSV would not?
5. What does `USERELATIONSHIP` change, and what does it not change?
6. Why is a blanket `IsCurrent = 1` filter dangerous on a page that also reports historical revenue totals?

## Concept — how today works

Twenty-five questions, closed book, one sitting, no notes: 8 domain, 7 dimensional modelling, 5 Power Query, 5 relationships. Most are multiple-choice; several are short-answer; **two require a written explanation** rather than a one-line fact, because "state the rule" and "explain why the rule matters" are different skills and this checkpoint tests both. **Pass mark is 18/25 (72%).**

After the quiz, you record a five-minute spoken narration of your own model — not a script read aloud, an actual explanation of what you built, as if a hiring manager had just asked "walk me through this." The rubric is fixed and known to you in advance (§ Ship, below): you're not being marked on production values, you're being marked on whether you can say, out loud, without notes, the same things you've been writing down all week. If you can't yet say it fluently, that's exactly what this exercise is for — better to discover the gap today than in an actual interview.

**If you score below 18/25:** don't retake the same quiz immediately. Identify which of the four sections (domain / modelling / Power Query / relationships) cost you the most marks, re-read that day's Concept section and your own Log entries for that day, redo that day's Drill exercises you got wrong, and only then attempt a fresh short requiz (ask your cohort lead or mentor for five new questions in the weak section, or write your own five and check them against the relevant day's Concept content). Moving into Week 2 with a genuine gap in modelling or relationships compounds badly, since both weeks 2 and 3 assume this week's model is both built and understood.

**Remediation map, by section:**

| Section missed | Go back to | What to specifically redo |
|---|---|---|
| Domain (Q1–8) | Day 1, Day 2 | The entity chain and cardinality table; the Incoterms decision table; the DCSA journey/EDIFACT tables |
| Dimensional modelling (Q9–15) | Day 3 | The additivity classification drill (all ten items, including the two "not a fact measure" traps); the three fact-type failure scenarios |
| Power Query (Q16–20) | Day 4 | The folder-combine pattern step order; both landmine walk-throughs (#5 and #7), redone from scratch rather than re-read |
| Relationships (Q21–25) | Day 5 | The two role-playing patterns and when each applies; the inactive-relationship diagnosis drill, rebuilt live rather than just re-read |

**Time-boxing the quiz itself**: 60 minutes for 25 questions is roughly 2.4 minutes each, but the four written-answer items (Q2, Q5, Q10, Q14, Q19, Q24, Q25 — seven in total, two of which are the full written-explanation questions Q5 and Q14) genuinely need more like 4–5 minutes apiece to answer properly, which means the multiple-choice items need to move fast, close to a minute each including a re-read of the option list. Don't let one written answer eat ten minutes at the expense of three multiple-choice questions later — a checkpoint under real time pressure is itself a reasonable simulation of the pace a technical screening interview actually runs at.

## Drill — the checkpoint quiz

Answer all 25 before checking anything against the solutions file. Write full sentences for the short-answer and written-explanation items — a checkpoint answer of "because null" is not gradeable.

### Domain (8)

**Q1 (MCQ).** What is the correct term for the document an NVOCC issues to the underlying cargo owner, as distinct from the document Meridian issues to that NVOCC?
A. Master bill of lading B. House bill of lading C. Sea waybill D. Manifest

**Q2 (short answer).** In one sentence, referencing the contract's target load-factor bands, state why backhaul load factor is structurally lower than headhaul rather than a sales failure.

**Q3 (MCQ).** Which of these is *not* one of the four sea/waterway-only Incoterms 2020 rules?
A. FAS B. FOB C. CIF D. CIP

**Q4 (MCQ).** Demurrage is charged for a container that is:
A. Sitting in the terminal (CY) beyond free time B. Sitting at the customer's premises beyond free time C. Damaged during handling D. Shipped without a VGM declaration

**Q5 (written explanation).** Explain why rising demurrage revenue can indicate the operation is *failing* rather than succeeding, referencing the specific magnitudes from the congestion event (§3.3 of the schema contract).

**Q6 (MCQ).** A customer books space across four different carriers in one quarter and shows thin margin-per-shipment alongside high volume. Which `CustomerSegment` is this most consistent with?
A. BCO B. NVOCC C. 3PL D. SME Direct

**Q7 (MCQ).** DCSA's three "journeys" are:
A. Origin, Transit, Destination B. Equipment, Transport, Shipment C. Planned, Actual, Estimated D. Booking, Shipment, Delivery

**Q8 (MCQ).** Which EDIFACT message type would you expect to be the source of a container gate-in event at a terminal?
A. IFTMIN B. IFTSTA C. CODECO D. BAPLIE

### Dimensional modelling (7)

**Q9 (MCQ).** `FactInventorySnapshot.OnHandUnits` is:
A. Additive B. Semi-additive over date C. Non-additive D. Not a fact measure

**Q10 (short answer).** State the grain of `FactShipmentMilestone` in one sentence, naming its fact type.

**Q11 (MCQ).** What is the correct VertiPaq-grounded reason to prefer a star schema over a snowflake in Power BI?
A. Snowflakes violate Kimball's rules B. Star schemas look tidier in a diagram C. Compression is per-column and doesn't improve from normalising a dimension, while every extra relationship hop is real formula-engine cost at query time D. Snowflakes cannot be refreshed incrementally

**Q12 (MCQ).** `FactShipmentMilestone` is best described as:
A. A transaction fact B. A periodic snapshot fact C. An accumulating snapshot fact D. A factless fact

**Q13 (MCQ).** A dimension's `-1` Unknown member exists mainly because:
A. It looks tidy in a data dictionary B. A null FK doesn't participate in any relationship, and `NULL ≠ NULL` in join semantics, so unresolved rows would silently vanish from totals C. Power BI requires every FK column to be non-null D. It's specifically required for SCD2 versioning and nothing else

**Q14 (written explanation).** A colleague summed `GrossMarginPct` across 10,000 shipments and reported the average as "our overall margin." Explain precisely what's wrong with this and what they should have calculated instead.

**Q15 (MCQ).** `FactBooking.QuoteKey` is best described as:
A. A surrogate key to a `DimQuote` table B. A degenerate dimension C. A role-playing dimension D. A conformed dimension

### Power Query (5)

**Q16 (MCQ).** "View Native Query" is expected to be unavailable for every query built against Meridian's Parquet folder sources because:
A. The Parquet files are corrupted B. Query folding in that sense is a relational/OData concept, and folder/file-based sources have no native query language to fold into C. Power BI does not support Parquet D. The query has too many steps

**Q17 (MCQ).** The correct fix for the credit-note landmine (contract landmine #5) is to:
A. Filter out every negative `Amount_usd` value B. Use `try … otherwise` to catch only genuine conversion errors, leaving valid negative values untouched C. Take the absolute value of `Amount_usd` D. Round negative values to zero

**Q18 (MCQ).** The correct fix for the `dd/MM/yyyy` locale landmine (contract landmine #7) is to:
A. Trust the default type conversion B. Explicitly convert using the `"en-GB"` culture C. Manually re-type every date by hand D. Leave it, since it "usually" parses correctly

**Q19 (short answer).** In the folder-combine pattern, at what step must `Year`/`Month` be recovered from the folder path, and why does that ordering matter?

**Q20 (MCQ).** Parquet survives a partition with a different physical column order because:
A. Power Query auto-sorts columns before combining B. Parquet embeds its own schema and matches columns by name, not position C. Parquet files are not permitted to have different column orders D. Power Query ignores column order for every file format

### Relationships (5)

**Q21 (MCQ).** `USERELATIONSHIP` changes:
A. Which relationship a slicer filters through B. Which relationship a specific measure's calculation uses, for that calculation only C. A relationship's cardinality D. Whether a relationship is active in the model, permanently

**Q22 (MCQ).** Simultaneous, independent slicing by both origin country and destination country on the same report page requires:
A. `USERELATIONSHIP` on one shared `DimLocation` table B. A single bidirectional relationship C. Importing `DimLocation` multiple times as separate, role-named tables D. A many-to-many bridge table

**Q23 (MCQ).** An inactive relationship, not invoked by any measure, propagates:
A. Filters in both directions B. Filters in one direction only C. No filter at all D. Filters only for numeric columns

**Q24 (short answer).** Describe the exact visual symptom of an inactive relationship on a report page — specifically, one that a plain "wrong DAX formula" bug would not produce.

**Q25 (short answer).** Using the `DimCustomer`/`FactBooking`/`FactShipment` triangle, explain why making one edge of it bidirectional is risky, and name a safer alternative for a "customers-with-bookings visual should respond to shipment-level filters" requirement.

## Ship

**Why a recording, not just a written summary:** every one of this week's written artefacts — the grain statements, the bus matrix, the landmine write-ups — was produced with time to think, edit, and rephrase. An interview is not that. The single most common gap between "I understand this on paper" and "I can defend this to a stakeholder" shows up exactly here: the first time you try to explain your own model out loud, unscripted, at normal conversational speed, with no chance to backspace. Doing that today, in a low-stakes setting, against a fixed rubric you already know, is considerably cheaper than discovering the gap for the first time in a real screening call. Aim for genuinely five minutes, not a rehearsed thirty-second summary padded with pauses — if you find yourself running out of things to say well before five minutes, that's a signal the model itself is thinner than this week's Ship artefacts suggested, and worth noting honestly in today's Log rather than papering over with filler.

**The recording rubric** (fixed, known in advance): record a five-minute, unscripted spoken narration of your own Week 1 model, covering:

1. **The grain of every fact table present in your model**, stated in one sentence each, without reading from notes.
2. **One relationship decision, justified** — pick either the date role-play or the location role-play from Day 5, and explain out loud *why* you chose `USERELATIONSHIP` for one and multiple imports for the other, in your own words.
3. **One landmine and its handling, described precisely** — pick any one of landmines #5, #7 or #9, state what the landmine actually is, and describe the specific mechanism of the correct fix (not just "I fixed it").

Save the recording (or, if audio/video isn't practical to commit, a full transcript of what you said, written *after* recording it once, not drafted first and read) as `notes/week1/day7-narration.md` or an audio file alongside it, plus your 25 quiz answers as `notes/week1/day7-checkpoint-answers.md`, and your score.

Commit with:

```
git add notes/week1/day7-checkpoint-answers.md notes/week1/day7-narration.md
git commit -m "day7: checkpoint 1 — score X/25, model narration recorded"
```

(Replace `X` with your actual score — recording it in the commit message is part of the exercise; there's no benefit to hiding a low score from your own repo history, and a real interviewer will ask you to explain a gap, not pretend one doesn't exist.)

## Log

- **What clicked**: looking back across the whole week, which single day's content is now load-bearing for how you think about the other five?
- **What did not**: which of the four quiz sections cost you the most marks, and is that the same section your Day 1–6 Logs already flagged as shaky — or a surprise?
- **What to re-ask tomorrow**: heading into Week 2, name one specific question about DAX or measures that this week's model-building has made you want answered.

## Exit criteria

- [ ] All 25 checkpoint questions answered in full sentences (not just letters/numbers) before checking solutions.
- [ ] Score recorded honestly; if below 18/25, the weak section identified and a remediation plan stated (not just "redo everything").
- [ ] Five-minute model narration recorded (or transcribed), covering all three rubric items: every fact table's grain, one justified relationship decision, one landmine's mechanism.
- [ ] `day7-checkpoint-answers.md` and the narration committed to your own repo, with your score in the commit message.
- [ ] You can, without notes, state your model's fact-table grains, your role-playing decisions, and one landmine's handling — out loud, in under five minutes.
- [ ] Log entry written, including an honest look back across the full week.
