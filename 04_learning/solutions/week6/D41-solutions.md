# Day 41: solutions, model answers, scored at a 4

Ten model answers, each written to the length and shape that would score a 4 on
Day 41's rubric: correct, specific, quantified, and anticipating the obvious
follow-up. Read these after you've scored your own, not before, the point of the
mock is your own answer under time pressure, not a memorized script.

---

## Q1, CALCULATE's filter behavior

"A `CALCULATE` filter argument **replaces** any existing filter on the same
column rather than intersecting with it: `DimMode[ModeCode] = "FCL"` inside
`CALCULATE` expands to `FILTER(ALL(DimMode[ModeCode]), ModeCode = "FCL")`, and the
`ALL` in there wipes out whatever the visual was already filtering on that column
first. So in a matrix with mode on rows, an `LCL` row would show the **FCL**
number, not blank, which surprises people the first time they see it. If you want
it to intersect instead (so the `LCL` row goes blank when you filter to FCL),
wrap the filter in `KEEPFILTERS`, which suppresses that implicit `ALL`. The
practical rule I use: any time I'm filtering a column the visual is already
filtering, I reach for `KEEPFILTERS` by default and only drop it if I deliberately
want the override behavior."

**Follow-up to anticipate:** "When would you *want* the replace behavior?"
Building an explicit override measure, like a "show FCL rate regardless of what's
selected" comparison column sitting next to the normal one.

---

## Q2, periodic vs accumulating snapshot

"A periodic snapshot records a state at a point in time, repeated on a cadence
(in my project, inventory on-hand value at SKU-warehouse-customer grain, weekly
then daily). The trap is that a snapshot row isn't additive across the date
dimension the way a transaction row is: summing on-hand value across every
snapshot date I have double-, triple-, and up to 500-times overcounts the same
physical stock, because the same inventory gets recorded again at every sample
date. An accumulating snapshot is different again: one row per entity, updated
in place as it progresses through stages, rather than a new row per event. My
shipment-milestone table is that shape: 14 milestone date columns on one row per
shipment, updated as the shipment moves through booking, loading, customs, and
delivery, rather than 14 separate event rows."

**Follow-up to anticipate:** "How do you fix the semi-additive problem?" Filter
to the single most recent snapshot date on or before the as-of date, never sum
across a range; `LASTNONBLANK` is the built-in version of that pattern.

---

## Q3, TREATAS, virtual relationships

"I reach for a virtual relationship when two tables genuinely can't share a
physical one, usually a grain mismatch, like a planning table set at region-month
grain being compared against transactional facts at location-day grain.
`TREATAS` takes the values currently in one table's column and applies them as a
filter on another column with no relationship, for the duration of one
`CALCULATE`. The real risk isn't the function itself: it's picking the wrong
bridge column, my model has two columns on the same location dimension encoding
region at two different granularities, and only one of them actually matches the
planning table's values. I always verify the match with a `DISTINCT` comparison
before building the measure, because getting the direction or the column wrong
doesn't error: it just silently filters the wrong table and returns a
plausible-looking wrong number."

**Follow-up to anticipate:** "How would you catch it if you didn't check first?" Compare the recomputed figure against a known reference value; a number that's
noticeably off from what you expect, with no error thrown, is the tell that the
bridge or the direction is wrong.

---

## Q4, rolling windows

"A single period's average is noisy: one bad week, or one week with unusually low
volume, swings the number around without telling you anything real changed. The
shipping industry reports schedule reliability on a trailing 8-week window
specifically because a vessel's schedule runs on a weekly cycle, so eight cycles
is enough observations to smooth weekly noise without averaging away a genuine
shift in performance. I'd implement it as a fixed-length trailing window with
explicit start and end dates, recomputed pooled over all the calls in the window, not as an average of eight separately-computed weekly rates, because that reopens
the same naive-averaging trap as any other unweighted mean of a ratio."

**Follow-up to anticipate:** "What if the underlying event calendar has gaps?" Use a calendar-time window (`RANGE`/`DATESBETWEEN`), not a row-count window
(`ROWS`), or a sparse population's window silently stretches further back in time
than the label claims.

---

## Q5, customer DIFOT case

"First, I'd pull their perfect-order rate by quarter and check the sample size
before drawing any conclusion: a rate built off a handful of shipments can swing
dramatically without anything real changing, and I want to know that before I say
anything to the customer. Then I'd decompose the composite rate into its
components, on-time, in-full, not-damaged, documentation-clean, because 'DIFOT
dropped' could mean four completely different operational problems, and the fix
and the message back to the customer are different for each. Then I'd check
whether their shipments cluster on a lane or port that had a known network-wide
event, if their volume runs through a location that had an operational
disruption, that's a materially different, more reassuring message than 'this is
specific to your account.' I'd close with the specific driving component and
whether it's systemic or account-specific, not just the headline percentage."

**Follow-up to anticipate:** "What if the sample size is too small to be
confident?" Say so directly to the customer rather than presenting a noisy
number as certain; widen the window or aggregate at a coarser grain if the
account's volume doesn't support a quarterly cut.

---

## Q6, the reconciliation case

"First step is to actually reproduce both numbers rather than guessing at the
cause, pull the stored figure from the planning table and recompute the same KPI
live from the transactional source. In my project this exact situation happened:
a stored 'actual' read 74.71%, the recomputed figure read 66.22%, an 8.5-point
gap. I traced it in two steps. First I verified the join between the two data
sources was actually bridging on the right column: there were two columns
encoding the same concept at different granularities, and it's easy to join on the
wrong one and get a plausible-but-wrong number with no error. Once I confirmed the
join was correct, the remaining gap traced to the stored figure itself. My first
guess was the same averaging error you'd catch in any DAX measure, an unweighted
mean baked into a static table nothing had validated — but checking it against
the code that actually built the table ruled that out: the stored 'actual' had
been drawn from an independent random distribution with no read of the
transactional source at all, so it carried no arithmetic relationship to the live
number to begin with. I'd recommend the recomputed, call-weighted figure for the
board deck, and flag the upstream fix, how that planning table's actuals get
produced, as a separate follow-up, not something to patch by just picking
whichever number looks better this month."

**Follow-up to anticipate:** "How do you know which number to trust when both look
plausible?" Trust the one whose construction method you've actually verified,
not the one that's more convenient or more familiar.

---

## Q7, auditing an inherited model

"I don't trust the relationship diagram at a glance, a one-to-many line between
two integer columns looks correct regardless of which columns it's actually bound
to. What I actually do is run a known, simple filtered query against the fact
table, something like 'rows in March 2025', and check the row count is
plausible for a table I know is populated. A real bug I found this way: a fact
table's relationship to the date dimension had been wired to the fact table's own
surrogate key instead of its actual date foreign key. It didn't error: it just
returned zero rows for any date filter, which was the tell, a populated table
returning nothing for an ordinary filter almost always means the join, not the
data. I fixed it by checking the value domains of both candidate columns, one
was a plain row-number sequence, the other matched the date dimension's key
domain exactly, then rebuilding the relationship on the correct column."

**Follow-up to anticipate:** "What if the failure isn't total, just subtly wrong?" That's harder and needs a reference value to check against; a total failure
(zero rows) is actually the easy case because it's unmissable once you look.

---

## Q8, the SQL averaging trap

"The naive way is `AVG` of a per-row ratio you compute in the `SELECT`, average
of `numerator/denominator` per row. That gives every row equal weight regardless
of how large its own denominator is, which overstates the average whenever small
denominators tend to come with inflated ratios, a five-minute task that's
unusually efficient per hour gets the same vote as a two-hour task that isn't. The
correct pooled version sums the numerator and denominator separately across the
whole group first, then divides once, `SUM(numerator)/SUM(denominator)`, which
weights each row by its own denominator automatically. I measured this exact gap
on a real dataset: one ratio came out about 22% too high under the naive method
because its denominator correlated strongly and negatively with the ratio itself;
a different ratio with near-zero correlation to its denominator came out barely
different between the two methods. The lesson isn't 'never average,' it's that the
size of the error is predictable from that correlation, and I check it rather than
assume."

**Follow-up to anticipate:** "Is this DAX-specific?" No, it's arithmetic;
it
shows up identically in `pandas`, Excel, or plain SQL; the only thing that changes
across tools is the syntax for writing the pooled version correctly.

---

## Q9, the embarrassing bug

"During a data-quality pass on a finished model, I sanity-checked a total
inventory-value figure against the company's known scale and it was off by
roughly 500 times, a naive sum across every historical snapshot date returned
about $1.3 trillion against a real balance closer to $2 billion. The cause was
that the inventory table records a state resampled repeatedly over time, not one
independent event per row, so summing across dates adds the same physical stock to
itself once per sample. It compiled, it ran, it looked like a number. Which is
exactly why it's the dangerous kind of bug: nothing about it announces itself as
wrong unless you stop and ask whether the magnitude actually makes sense. The fix
was a point-in-time filter to the most recent snapshot on or before the reporting
date, never a raw sum across a range."

**Follow-up to anticipate:** "How do you build the habit of catching this kind of
thing?" Treat every new aggregate as needing one plausibility check against a
number you already independently know, before it ships anywhere.

---

## Q10, limitations and next steps

"The most honest limitation is that this project uses Import mode over static
Parquet files the whole way through, I have no hands-on experience with
DirectQuery performance tuning, composite models, or query-folding behavior
against a live database, which is a real gap against a job that runs on a
multi-terabyte DirectQuery source. If I had another month, that's specifically
what I'd build next: point a DirectQuery model at the same schema in an actual
database and work through the aggregation-table and query-folding story, since
that's the part of a real production Power BI job this project's file-based setup
never had to face."

**Follow-up to anticipate:** "Why didn't you build that from the start?" Import
mode over Parquet was the right choice for learning the modelling and DAX
semantics fastest and cheapest, without needing a database server running, the
gap is real, but it's the right gap to have taken given what six weeks needed to
prioritize.
