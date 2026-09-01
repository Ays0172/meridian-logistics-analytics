# Day 39: solutions

Day 39's day-file already contains the four stories fully worked out: that is the
"answer key." This file is the self-grading rubric for **your own delivery** of
them, plus notes on adapting them to a specific interview.

---

## Spaced recall answers

1. `FactTarget`'s stored "Actual" was itself built as an unweighted mean across
   trade lanes rather than a call-weighted pooled figure: the identical
   arithmetic error Day 9 measured for lines-per-labour-hour, just sitting inside
   a static planning table instead of a live DAX measure.
2. `-1` is the fixed sentinel for numeric surrogate keys and not-yet-happened
   dates, and its own row's text attributes carry the label `"Unknown"`
   (README §7 — originally `"#NA"`, itself one of Story 2's twelve cosmetic
   fixes). That's a *different* case from a real, non-unknown-member row whose
   attribute genuinely doesn't apply: there, the column should hold a true
   `BLANK()`/`null`, not a placeholder string — the Story 2 bug is exactly a
   case of `"#NA"` wrongly standing in for that, on real rows rather than the
   sentinel row.
3. Because `OnHandValueUsd` is additive across SKU/warehouse/customer at one
   snapshot date but not across dates, a date-unfiltered `SUM` adds the same
   physical stock to itself once per one of the roughly 581 snapshot dates.
4. `EventDateKey` is the real foreign key identifying which calendar date a
   container-move event happened on; `ContainerMoveKey` is the table's own
   transaction-grain surrogate key (a row identifier, not a date). Wiring a
   relationship to the wrong one of the two fails **totally** (zero rows on any
   date filter) rather than subtly, because the two columns don't share a value
   domain at all.
5. "Find one number in this model that would mislead a reader without context,
   and write three sentences: what it is, what the correct number is, and what
   you'd tell someone about to ship the wrong one." Day 14 flagged that exact
   kind of write-up as the seed of a Week 6 portfolio story, which today made
   literal.

---

## Self-grading rubric

Read each of your four written stories against this checklist. Be honest: this
is the same "check against the real answer" discipline every earlier week's
solutions file asked of you, just applied to prose instead of DAX.

**Situation**
- [ ] States a concrete fact table or component, not "a dashboard" or "the data."
- [ ] One or two sentences: resist the urge to over-set-the-scene.

**Task**
- [ ] States what was actually at stake if the bug went unfixed (a wrong number
      on a report, a filter that silently includes rows it shouldn't), not just
      "I needed to investigate."

**Action**
- [ ] Names the specific technical mechanism (a relationship bound to the wrong
      column, a text placeholder instead of `BLANK()`, a semi-additive column
      summed across a range, a virtual-relationship bridge column): vague
      "I debugged it" language is the single most common way these stories fall
      flat under a follow-up question.
- [ ] Shows the diagnostic step, not just the fix: *how* you knew, not only
      *what* you changed. ("Zero rows on an ordinary filter" and "the number
      failed a plausibility check against known company scale" are both
      diagnostic tells worth keeping in your telling.)

**Result**
- [ ] Contains an actual number or magnitude (500×, 8.5 points, zero rows → real
      rows): a Result with no quantity in it is the weakest, most common failure
      mode of a STAR answer.
- [ ] States what changed for a downstream user (a report, a decision, a
      dashboard), not just "the model was now correct."

**Delivery**
- [ ] You can say the full version in 60–90 seconds without reading it.
- [ ] You can say the headline version in under 15 seconds.
- [ ] You can answer at least one plausible follow-up without visibly pausing to
      recall a fact.

If a story is missing more than one checkbox, rewrite that section specifically:
don't rewrite the whole story from scratch, since the parts that pass are worth
keeping as-is.

---

## Adapting these stories to a real interview

**Trim the DAX/M jargon to the audience.** A data-team interviewer wants the exact
mechanism (`TREATAS`, `Table.TransformColumns`, semi-additive vs fully additive).
A hiring manager who isn't hands-on wants the business consequence first and the
mechanism only if they ask a follow-up: lead with "a board-facing number was off
by 8.5 points and here's why" rather than opening with the DAX function name.

**Pick the story to the question, not the other way around.** "Tell me about a
data quality issue" fits Story 2 or 3 best. "Tell me about reconciling conflicting
numbers" fits Story 4. "Tell me about debugging something that looked fine but
wasn't" fits any of the four. Memorize which prompt-shapes map to which story so
you're not searching under pressure.

**Never claim a story is more recent or more dramatic than it was.** All four of
these are genuinely real and genuinely yours from building and auditing this
project: that is already a strong position. Inflating the stakes ("this almost
cost the company millions") when the honest framing is "this would have shipped a
wrong number on an internal dashboard" is a risk with no upside: a good
interviewer's follow-up questions will find the seam.

---

## A fifth story, if you want one in reserve

Interviewers sometimes ask for a second example after the first lands well. If you
want a fifth in your back pocket, Day 37 Case 37.4 (the finance budget-reconciliation
case drill) *is* Story 4 told from the stakeholder's side rather than the
debugger's. Practice both framings of the same underlying finding; they are not
the same story told twice, they're two different useful shapes for two different
questions ("tell me about a bug you found" versus "tell me about handling a
disagreement with a stakeholder over which number is right").
