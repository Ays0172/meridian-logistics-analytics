# Day 28: Checkpoint 4: the UX pass

> Time: 3.5 h · Spaced recall 10 min · Part A 30 min · Part B 40 min · Part C 90 min · Log 15 min

No new concept. Five pages exist, each individually justified against its own
one-line decision. Today is the review: rebuild the shell from memory, explain the
week's design principles without notes, then run a genuine audit against your own
built report - the same "no new mechanism, just verify what you actually built"
shape as Week 2's Checkpoint 2 (Day 14), applied to design judgment instead of
DAX.

---

## Spaced recall (10 min, closed book)

1. Name the two filters that sync across all five pages, and the one filter Day
   22's audit specifically flagged as unsafe to sync, naming the two pages where it
   breaks.
2. State the OTIF naive-vs-correct gap in percentage points, and which operator
   choice (not which data) causes it.
3. What two mechanisms connect the Executive page's domain synthesis cards to
   their target pages, and what different question does each one answer?
4. Where does the full Rotterdam/LA congestion callout live, and what compact
   trace of it appears on the Executive page instead of the full version?
5. Name one KPI dictionary "Gap" (a KPI this schema cannot fully support as
   specified) that showed up in this week's build, and what proxy was used instead.

---

## Part A: rebuild the nav shell from memory (30 min)

Closed book except your own predictions log. Without opening the report, write
down:

1. Every button in the nav bar, its label, and its Page navigation destination.
2. Every bookmark that exists in the report, what each one captures (Data only,
   Display only, or both), and what it's attached to.
3. Every drillthrough page, its drillthrough filter field(s), and where its Back
   button returns to.
4. One thing from Day 22's Concept section you deliberately chose **not** to build
   (the dynamic bookmark-driven "you are here" highlight was named explicitly as
   unnecessary machinery for five static buttons) - and why skipping it was the
   right call, or, if you built it anyway, what made you change your mind.

Then open the report and check yourself. Every mismatch goes in today's Log: was
it a detail you genuinely forgot, or a piece you thought you'd built and hadn't?

---

## Part B: explain the week in five short paragraphs (40 min)

No DAX, no screenshots. One paragraph each:

1. **Page purpose.** Why "one page = one decision it supports" is a sharper design
   test than "one page = one KPI domain," and what a page that fails the test
   looks like in practice.
2. **Filter scope strategy.** How you decide whether a filter syncs across pages,
   is page-specific, or is excluded, and why the answer depends on which fact
   tables the pages sit on rather than on convenience.
3. **Drillthrough design.** When you reach for a genuine drillthrough versus a
   plain Page navigation button, and what breaks if you only build one of the two
   on a page that needed both.
4. **Tooltip design.** What a report/page tooltip is for that a static annotation
   on the canvas is not, and one place this week you used one (or should have).
5. **Accessibility basics.** Contrast, alt text, and colour-blind-safe encoding -
   name the specific rule for each and one place in your own report where it
   currently does or doesn't hold up.

---

## Part C: full UX audit (90 min)

Run this checklist against your own five-page report, not against this document.
Every unchecked box needs a one-line note on what you'll fix and when (now, or a
named future day) - an unchecked box with no note is the thing this checkpoint
exists to catch.

### Consistency
- [ ] All five pages use the same theme (`meridian-theme.json`), no manually
      overridden colours or fonts surviving from an earlier draft.
- [ ] Header band height and position identical across all five pages.
- [ ] Card visuals use the same corner radius, padding, and number-format
      convention (set on the measure, not per-visual) everywhere they appear.
- [ ] Nav bar identical in position and size on every page, with exactly one
      button per page shown in its selected state.

### Mobile layout
- [ ] Each page has a Mobile layout defined (Power BI Desktop: View > Mobile
      Layout), not left to auto-generate from the desktop canvas.
- [ ] Header KPI cards appear first in the mobile stack on every page - the
      five-second read still works on a phone.
- [ ] No visual in the mobile layout requires horizontal scrolling to read its
      title or its single most important number.
- [ ] Interactive elements (buttons, slicers) meet a touch target of roughly
      44x44px or larger in the mobile layout, not just the desktop one.

### Tooltip coverage
- [ ] Every measure that carries a documented "watch-out" in
      `KPI_DICTIONARY.md` (naive-average traps, sentinel values, proxy labels,
      grain warnings) has that caveat reachable from a tooltip on every visual
      that uses it, not only on the one visual where you happened to build it
      first.
- [ ] The congestion callout's tooltip (Day 23) is reachable from the demurrage
      series even when the shaded event window has scrolled out of the visible
      date range.
- [ ] No page relies on a caveat living only in this course's lesson files -
      every caveat a reader needs is reproduced inside the report itself.

### Drillthrough wiring
- [ ] Every drillthrough page's Back button restores the exact prior page and
      filter state (Exercise 27.3's test, re-run here across all wired
      drillthroughs, not just the two you tested that day).
- [ ] Every drillthrough filter field is one that is genuinely safe to sync
      per Day 22's audit (`TradeRegion`, `Period`) - no drillthrough silently
      depends on a page-specific filter (`Mode`, `Carrier`, `Warehouse`) that the
      source page doesn't actually expose.
- [ ] The Carrier Detail drillthrough's population-wide min/max measures
      (Exercise 24.3) are confirmed identical regardless of which carrier was
      drilled into - re-verify, don't just trust the earlier test.

### Accessibility
- [ ] Every visual has meaningful alt text (Format pane > General > Alt text),
      not the default auto-generated description.
- [ ] Text-on-background contrast meets at least 4.5:1 for body text, checked
      against the actual theme colours, not eyeballed.
- [ ] No status encoding (the `good`/`neutral`/`bad` conditional formatting from
      Day 23) relies on colour alone - icons or text labels accompany every
      colour-coded status, so a colour-blind reader isn't locked out of the
      Ocean Liner header cards specifically.
- [ ] Tab order (Selection pane > "Tab order" view) follows a sensible reading
      sequence on every page: header cards, then primary chart, then supporting
      visuals - not the order visuals happened to get added in.

---

## Ship

Commit the fixes Part C's audit turned up that you addressed same-day, plus a new
`06_portfolio/notes-ux-audit.md` holding Part B's five paragraphs and Part C's full
checklist with its fix notes attached - this is the document Week 6's portfolio
write-up will draw its "here is how I designed and then audited a five-page report"
section from directly, so write it for that future reader, not just for today.

```
git add .
git commit -m "Day 28: Checkpoint 4 - UX audit run, fixes applied, Week 4 complete"
```

---

## Log

What clicked / what did not / what to re-ask. For this checkpoint specifically:
which single checklist item, once you actually ran it against your own report
rather than assumed it was fine, turned up the most surprising gap?

---

## Exit criteria

- [ ] Part A rebuilt from memory, checked against the actual report, mismatches
      logged with a reason for each.
- [ ] Part B's five paragraphs written, no DAX, each one specific to this
      project's data rather than generic Power BI advice.
- [ ] Part C run in full against your own five-page report; every unchecked box
      carries a fix note.
- [ ] You can state, without notes, why the nav bar's "you are here" state uses
      static per-page styling rather than a dynamic bookmark, and can defend or
      revise that choice from your own build experience.
- [ ] Week 4 committed in full: four domain pages, the Executive Summary, the
      nav shell, and this checkpoint's audit notes.
