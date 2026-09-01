# Day 41: Full mock interview, 10 questions, timed, self-scored

> Time: 3 h · Spaced recall 10 min · Concept 25 min · Drill 90 min · Ship 20 min · Log 15 min

Everything else this week produced material. Today is the dress rehearsal: ten
questions, increasing in difficulty, run in one sitting with a clock running, no
looking anything up mid-answer. Score yourself honestly afterward against the
rubric: the value of a mock interview you grade generously is close to zero.

---

## Spaced recall (10 min, closed book)

1. Name one thing this project's curriculum genuinely did not cover (Day 38), and
   have your honest three-sentence answer for it ready before you start today.
2. What are the four STAR stories, in one sentence each (Day 39)?
3. What is the five-part case-answer skeleton from Day 37 (Define/Locate/Compute/
   Caveat/Recommend)?
4. What is your 60-second elevator pitch's opening line (Day 40)?
5. Which single number would you lead with if asked "what's the most interesting
   thing you found in this project"?

---

## Concept

### How a real technical interview is actually scored

An interviewer is rarely scoring "did you get the exactly right answer." They're
scoring three things simultaneously: **correctness** (is the mechanism right),
**specificity** (do you have a real number or example, or are you speaking in
generalities), and **communication** (can you explain it to the level of technical
depth the question implied, without over- or under-explaining). A technically
perfect answer delivered as an unstructured wall of jargon scores worse than a
slightly-less-complete answer that's clearly organized. This is not unfair: it's
literally testing whether you'd be useful to explain things to a stakeholder later.

Today's rubric scores all three, per question, on a 0–4 scale:

| Score | Meaning |
|---|---|
| 0 | Blank, or actively wrong mechanism |
| 1 | Right direction, no specifics, "it's about weighting things differently" |
| 2 | Correct mechanism, stated clearly, but no number and no real example |
| 3 | Correct, with a real number or example from this project, reasonably concise |
| 4 | A 3-level answer that also anticipates the obvious follow-up unprompted |

### Running the mock

Set a timer per question (times given below). Answer **out loud**, not by typing:
a spoken answer under time pressure is a genuinely different skill from a written
one, and it's the one that actually gets tested. Do not pause the clock to think
silently for more than a few seconds; if you freeze, note it and move on, same as
you would in a real interview. Record your answer (voice memo) if you can, so you
can listen back before scoring: most people are worse judges of their own rambling
in the moment than on replay.

---

## Drill

### Exercise 41.1, the ten-question mock (85 min)

Run straight through. Do not read ahead to the next question before finishing the
current one's time.

**Q1 (5 min, conceptual).** *"Explain `CALCULATE`'s filter behavior, what does it
mean for a filter argument to replace rather than intersect an existing filter,
and when do you need `KEEPFILTERS`?"*

**Q2 (5 min, conceptual).** *"What's the difference between a periodic snapshot and
an accumulating snapshot fact table? Give a real example."*

**Q3 (7 min, conceptual, harder).** *"When would you reach for a virtual
relationship like `TREATAS` instead of a physical one, and what's the risk if you
get the bridge column wrong?"*

**Q4 (8 min, conceptual, harder).** *"Walk me through why you'd report schedule
reliability on a rolling window instead of a plain period average, and what length
window you'd pick and why."*

**Q5 (12 min, case-style).** *"A customer says their on-time-in-full rate dropped
this quarter. How do you investigate, live, right now?"*

**Q6 (12 min, case-style, hardest).** *"Finance says the board deck's reliability
number doesn't match your dashboard's number. Walk me through reconciling that,
out loud, as if I'm the finance director waiting for an answer."*

**Q7 (10 min, technical).** *"You inherit a model you didn't build. How do you
find out whether a relationship is wired correctly, before you trust any measure
built on it?"*

**Q8 (10 min, SQL crossover).** *"If I asked you to compute an average ratio in
plain SQL, no DAX, what's the naive way people get wrong, and how do you avoid
it?"*

**Q9 (8 min, behavioral).** *"Tell me about a bug you found that would have been
embarrassing if it had shipped to a dashboard."*

**Q10 (8 min, closing/behavioral).** *"What's a real limitation of this project,
and what would you do next if you had another month?"*

### Exercise 41.2, self-score, immediately, honestly (15 min)

Score all ten answers 0–4 using the rubric above, right after finishing, not the
next day, when memory of exactly what you said (versus what you meant to say) has
already softened. If you recorded audio, listen back to at least your three
weakest-feeling answers before scoring them; people are reliably worse at judging
their own rambling from memory than on replay.

---

## Scoring guide

| Total (out of 40) | Read as |
|---|---|
| 32–40 | Ready to schedule real interviews. Polish, don't overhaul. |
| 20–31 | Solid foundation, specific weak spots to close before scheduling anything real (see the mapping below). |
| Under 20 | Not ready yet. Go back to the mapped days, rebuild the specific weak measures/stories, and re-run this mock in a few days rather than pushing forward. |

| Question | If you scored ≤2, go back to |
|---|---|
| Q1 | Day 9 (`CALCULATE`, `KEEPFILTERS`) |
| Q2 | Day 12 (snapshot patterns) |
| Q3 | Day 13 / Day 36 (TREATAS, and the SQL-join framing of the same idea) |
| Q4 | Day 11 (rolling windows, the masking demonstration) |
| Q5 | Day 37 Case 37.2 |
| Q6 | Day 37 Case 37.4 / Day 39 Story 4 |
| Q7 | Day 39 Story 1 |
| Q8 | Day 9 / Day 36 |
| Q9 | Day 39 Stories 2 or 3 |
| Q10 | Day 38 (honest gaps) / Day 42 (tomorrow) |

A single weak question is normal and fine: everyone has a rusty spot. A cluster
of weak scores in one area (all four conceptual questions, say, or both case-style
questions) tells you where to actually spend the time before Day 42's retrospective
closes the course out, rather than re-reviewing everything evenly.

---

## Ship

Write `06_portfolio/mock-interview-results.md`: your ten scores, one honest
sentence per question on what would need to improve, and your total. This is not
for anyone else to read: it's the single most useful diagnostic this whole week
produces, so don't sand it down to look better than it was.

```
git add .
git commit -m "Day 41: full mock interview run and self-scored"
```

---

## Log

Which question you'd most want to re-run right now if you had another 10 minutes,
and specifically what you'd change about the answer.

---

## Exit criteria

- [ ] All ten questions answered out loud, timed, in one sitting.
- [ ] All ten scored honestly against the 0–4 rubric, immediately after answering.
- [ ] `06_portfolio/mock-interview-results.md` written with real scores and real
      notes, not retroactively polished answers.
- [ ] You know your total and, more importantly, your weakest one or two specific
      questions, mapped back to the day that would fix them.
- [ ] You have decided, honestly, whether you are ready to schedule a real
      interview or need another pass first.
