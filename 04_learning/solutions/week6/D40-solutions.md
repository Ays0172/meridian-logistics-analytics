# Day 40: solutions

A worked example of the case-study opening and README numbers block, at the
quality bar to aim for, not a template to copy verbatim, since a copied opening
reads as generic the moment an interviewer has seen it twice.

---

## Spaced recall answers

1. Ocean Liner / Landside / Warehouse & Inventory / Air & LCL / Executive
   summary: the Executive page (Day 27) is the CFO-facing one, drilling through
   into the four domain pages.
2. Schedule reliability **0.6598**; delivery on-time rate **0.9130**; perfect
   order rate **0.8574**; revenue per FFE headhaul/backhaul **$2,482.78 /
   $1,286.66**; total revenue **$2,040,774,144**; revenue CAGR 2022→2025
   **5.78%**.
3. A visible, diffable commit history of every model change: a reviewer (or an
   interviewer) can see the model evolve over six weeks the same way they'd
   review application code, which a single opaque `.pbix` binary cannot show.
4. Example (Story 3): "A naive sum of inventory value across all snapshot dates
   returned roughly $1.3 trillion, about 500× the company's real ~$2 billion
   inventory value, which I caught with an order-of-magnitude sanity check before
   it reached a report."
5. Because a screenshot only shows *that* something was built, not *why it
   matters*: a reader has to already know what to look for to extract the point
   themselves, which most readers skimming a portfolio will not do.

---

## Worked example, case study opening (Exercise 40.1)

> **Meridian Logistics Analytics: a self-built BI platform, with four real bugs
> found and fixed.**
>
> I built a 19-dimension, 11-fact logistics analytics model (7.5M rows, seeded and
> reproducible) covering ocean, landside, warehouse, and air/LCL freight, then ran
> a data-quality audit against the finished semantic model. I found and fixed four
> distinct issues: a relationship silently bound to the wrong surrogate key
> (returning zero rows on every date filter until fixed), a text placeholder
> masquerading as a true blank value across five columns (a filter-logic trap, not
> a cosmetic one), a semi-additive rollup that was overstating inventory value by
> roughly 500×, and an 8.5-point gap between a planning system's stored actuals
> and the underlying transactional truth, traced to a naive average baked into the
> comparison data itself.
>
> The project's five-dashboard report and ~150-measure DAX library are built to
> demonstrate the modelling and visualization skill; the four findings above are
> built to demonstrate that I can debug a model someone else (or past-me) built,
> which is closer to what a working analytics job actually looks like day to day.

**Why this works:** the headline number appears in the first sentence ("four real
bugs found and fixed", a specific, checkable count, not "learned a lot"). The
second paragraph explicitly names the *reason* the findings matter more than the
build, a stronger closing move than just listing skills.

---

## Worked example, README numbers block (Exercise 40.3)

```markdown
## The numbers

| Metric | Value |
|---|---|
| Schedule reliability (vessel vs published ETA) | 0.6598 |
| Delivery on-time rate | 0.9130 |
| Perfect order rate | 0.8574 |
| Revenue per FFE, headhaul / backhaul | $2,482.78 / $1,286.66 |
| Total revenue, full history | $2,040,774,144 |
| Revenue CAGR, 2022→2025 | 5.78% |
| Top-10 customer revenue share | 27.8% |

## What I found while building this

Four issues, each traced to root cause and fixed:

1. **A relationship bound to the wrong key:** `FactContainerMove` was joined to
   `DimDate` on its own surrogate key instead of the actual event-date foreign
   key, silently returning zero rows on any date filter.
2. **A text placeholder standing in for BLANK():** five columns used `"#NA"` on
   real, populated rows (not just the unknown-member row), breaking `<> BLANK()`
   filters silently.
3. **A ~500× semi-additive overstatement:** a naive sum of inventory value
   across ~581 repeated snapshot dates returned ~$1.3T against a true balance of
   ~$2B.
4. **An 8.5-point budget-vs-actual gap:** traced to a planning table's own
   "Actual" figures being independently random-generated, with no arithmetic
   relationship to the live transactional data at all.

Full write-ups, STAR-formatted: [`06_portfolio/star-stories.md`](06_portfolio/star-stories.md).
```

**Why this works, and one thing to watch for:** the numbers are copied verbatim
from README §6. Do not round them further or restate them with different
precision, since a portfolio README's numbers should match the project's own
canonical source exactly (a reader who checks and finds a rounding mismatch will
trust the rest of the document less). The "what I found" list uses the same four
findings as the case study and the STAR stories, worded slightly shorter for a
skim-reading context. Repetition of the same four findings across the README,
case study, and STAR file is intentional, not redundant, since different readers
will only ever see one of the three.
