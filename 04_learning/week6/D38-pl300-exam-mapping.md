# Day 38: Mapping six weeks onto PL-300, and being honest about the gaps

> Time: 2.5 h · Spaced recall 10 min · Concept 40 min · Drill 60 min · Ship 20 min · Log 15 min

PL-300 (Microsoft Certified: Power BI Data Analyst Associate) is the exam a
hiring manager will assume you could pass if your resume says "Power BI." Today
maps what Days 1-37 actually built against the exam's published skill areas, and
(this is the part worth more than the mapping itself) names exactly what this
project did **not** cover, so you walk into that exam, or that interview, knowing
your gaps instead of discovering them live.

A caveat up front: Microsoft revises PL-300's exact skill weightings and item list
periodically (it has moved in step with the Fabric-era Power BI changes). What
follows is the skill-area structure as it has been stable for several cycles.
**Check the live "Skills measured" page on Microsoft Learn before you sit the
exam**, not this document, for the exact current weighting.

---

## Spaced recall (10 min, closed book)

1. Name the five report pages this project's dashboards were organised around
   (Week 4), and which KPI domain each one covers.
2. What refresh limits does Power BI Service Pro vs PPU licensing carry (Day 30 /
   README §4), and why does that matter for a daily-refresh model like this one?
3. What does `.pbip`/TMDL source control buy you that a `.pbix` file does not
   (Day 33)?
4. Name one row-level security pattern you built (Day 31) and the DAX filter
   pattern behind it.
5. What is a calculation group, and which exam-domain topic ("model the data" vs
   "visualize the data") does it belong to?

---

## Concept

### The four PL-300 skill areas, and where this course sits in each

| PL-300 domain | Roughly | Where this project covered it |
|---|---|---|
| **Prepare the data** | connect to sources, profile, clean, transform, load | Week 1 (D01–D07): dimensional modelling, Power Query cleaning steps, the 10 seeded landmines; Week 5 D34's formalised landmine audit |
| **Model the data** | relationships, DAX measures/columns, hierarchies, optimisation | Week 2 (D08–D14) and Week 3 (D15–D21): the ~150-measure library, calculation groups, TREATAS, semi-additive patterns; Week 5 D32's performance tuning |
| **Visualize and analyze the data** | report/dashboard design, accessibility, patterns, advanced analytics | Week 4 (D22–D28): the five dashboards, drillthrough, bookmarks, accessibility pass |
| **Deploy and maintain assets** | workspaces, RLS, refresh, apps, gateways, dataflows | Week 5 (D29–D35): scheduled refresh, RLS, `.pbip` source control, the GitHub Actions live feed |

That is a genuinely strong map: this project deliberately followed the shape of
the exam's own domains even before today made it explicit, because the two are
both organised around "how does a real BI project actually get built," not around
an arbitrary syllabus.

### Where the coverage is real depth, not just a checkbox

Three places this project goes noticeably deeper than a typical PL-300
crash-course, worth naming explicitly in an interview:

- **The averaging trap (Day 9) and semi-additive measures (Day 12)** are DAX
  correctness issues that PL-300 tests only lightly (a question or two on
  `SUMX`/`AVERAGEX` semantics), but that matter far more in a real job than the
  exam weighting suggests. You can speak to *why* these traps happen, not just
  that they exist.
- **`TREATAS` and virtual relationships (Day 13)** go past what most PL-300 prep
  material covers: many candidates pass the exam having only used physical
  relationships and basic `RELATED`/`RELATEDTABLE`.
- **Source-controlled `.pbip`/TMDL (Day 33)** and a scheduled, self-healing live
  data feed (Day 29's GitHub Actions work, per the Week 5 roadmap) are closer to
  how a Power BI project is actually operated in a team with CI/CD than what
  PL-300's "deploy and maintain" objectives ask you to demonstrate: that domain's
  exam content mostly stops at workspace/app management inside the Service UI.

### What this project genuinely did not cover

Do not paper over these. An interviewer who asks "have you worked with X" wants a
direct "no, but here's what I have done that's adjacent" -- not a vague answer that
implies coverage that isn't there.

| PL-300 topic | Covered here? | Notes |
|---|---|---|
| **Dataflows (Gen1/Gen2)** | **No** | This project reads Parquet directly via Power BI's Parquet connector; nothing was built with Power Query Online or a dataflow entity. If asked, say so plainly and note you understand the concept (reusable, centrally-refreshed ETL logic shared across models) even without hands-on time. |
| **Paginated reports (Power BI Report Builder)** | **No** | A genuinely different tool (RDL-based, pixel-perfect, built for invoices/statements) from anything this course touched. |
| **Power Automate / Power Apps integration** | **No** | No embedded Power Apps visual, no data-driven alert wired to a Power Automate flow. This project's "automation" (Day 29) is a GitHub Actions data pipeline, not a Power Platform automation: a related but distinct skill. |
| **DirectQuery / composite models / aggregations** | **No** | Every day of this course used Import mode over local/blob Parquet. The whole DirectQuery performance story (query folding, aggregation tables for a DirectQuery fact, dual storage mode) is untouched. |
| **Power BI Service governance** (sensitivity labels, certified/promoted datasets, deployment pipelines, capacity/Premium concepts) | **Partially** | Scheduled refresh and RLS were built (Day 30–31); workspace apps, deployment pipelines (Dev/Test/Prod), and sensitivity labelling were not. |
| **AI visuals** (Key Influencers, Decomposition Tree, Q&A, the Analytics pane's forecasting/clustering) | **No** | The five dashboards use standard visuals plus DAX-driven KPIs; none of the model's out-of-the-box analytics visuals were built into a page. |
| **Gateways for on-premises sources** | **No** | Nothing in this project connects to an on-prem source: every table is a file. |
| **Q&A / linguistic schema tuning** | **No** | Not touched. |

### How to talk about a gap, honestly, in an interview

The wrong answer to "have you built a paginated report" is pretending. The right
shape of answer: name what you *have* done that's structurally related, state the
gap plainly, and say what you'd need to close it. For paginated reports, that's
"no hands-on time, but I understand the tool is for pixel-perfect, print-shaped
outputs like invoices rather than interactive analysis, which is a different job
from the five dashboards I built: I'd expect to be productive with it inside a
day or two given the RDL concepts carry over from SSRS." That is a stronger answer
than a confident-sounding fabrication, and an experienced interviewer can tell the
difference immediately.

---

## Drill

### Exercise 38.1, self-audit against the domain table (25 min)
Before reading further, predict, from memory, roughly what percentage of each
PL-300 domain (Prepare / Model / Visualize / Deploy) you personally feel confident
demonstrating live, unscripted, in an interview (not "did the day file exist" but
"could you build it again from a blank model right now"). Write four percentages.
Then go back through Weeks 1–5's exit-criteria checklists (skim the actual `.md`
files) and count how many boxes you can genuinely still check without re-reading
the day. Compare your gut percentages to the checklist count: where they disagree
is worth a note.

### Exercise 38.2, pick your two weakest topics and name a concrete next step (20 min)
From the "did not cover" table, pick the two gaps most likely to come up given the
kind of role you're targeting (a heavy Power Automate shop cares about that gap
more than a pure-analytics team would). For each, write two sentences: what you'd
study or build to close it, and how long you'd estimate it taking given how this
course's other topics went. Be specific: "read the docs" is not a plan,
"build one dataflow that centralises the DimDate/DimLocation cleaning logic
Weeks 1 and 5 already did in Power Query, so I've done it both ways" is.

### Exercise 38.3, rewrite one gap as an honest interview answer (15 min)
Pick one row from the "did not cover" table and write out, verbatim, what you
would say if asked about it live. Use the three-part shape from the Concept
section: adjacent experience, honest gap, concrete plan to close it. Read it back:
does it sound confident or does it sound like an excuse? If the latter, tighten it.

---

## Ship

Write `06_portfolio/pl300-gap-analysis.md`: the domain table, your honest coverage
self-assessment from 38.1, and the two written gap-answers from 38.2/38.3. This
becomes both exam-prep material and, lightly edited, a legitimate line in an
interview prep doc.

```
git add .
git commit -m "Day 38: PL-300 domain mapping and honest gap analysis written"
```

---

## Log

What clicked / what did not / what to re-ask. Note specifically whether your gut
self-assessment in 38.1 over- or under-estimated your real coverage, and in which
direction: that bias is worth knowing about yourself going into Day 41's mock.

---

## Exit criteria

- [ ] You can state, without notes, which Week of this course maps to each of the
      four PL-300 domains, and one specific deliverable per domain as evidence.
- [ ] You can name, without notes, at least five topics PL-300 tests that this
      project did not cover.
- [ ] `06_portfolio/pl300-gap-analysis.md` exists with two fully written,
      honestly-worded gap answers.
- [ ] You checked the live Microsoft Learn "Skills measured" page (or noted that
      you did not have internet access to do so, and flagged it as a follow-up)
      rather than treating this file as the current authoritative weighting.
- [ ] Predictions recorded, misses annotated.
