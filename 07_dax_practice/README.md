# 07_dax_practice - DAX Practice Trainer

A single self-contained page, `dax_trainer.html`, for practising DAX on small random logistics data. Open it by double-click in any modern browser: no build, no server, no libraries.

- Three levels (Beginner / Intermediate / Pro), five challenges each. Each round generates fresh seeded data (`Shipment`, `Customer`, `Date`); the seed is shown and editable, "New data" rolls a new one.
- Your measure is run by a built-in mini DAX interpreter and compared with a reference measure on the grand total and on every row of a breakdown. Common mistakes (`/` instead of `DIVIDE`, unqualified columns, averaging ratios, the Air/`Ffe = 0` FFE trap) get a tagged warning.
- Supported DAX subset: `SUM AVERAGE MIN MAX COUNT COUNTA COUNTROWS DISTINCTCOUNT`, `SUMX AVERAGEX MINX MAXX COUNTX`, `FILTER ALL VALUES DISTINCT`, `CALCULATE` (with context transition, column filters, `KEEPFILTERS`, `ALL`/`REMOVEFILTERS`), `RELATED`, `DIVIDE IF AND OR NOT BLANK ISBLANK ABS ROUND`, `VAR`/`RETURN`, `IN {...}`.
- Limits: a True/False filter inside `CALCULATE` may reference one column (use `&&` or `FILTER` for more); no time intelligence, `ALLEXCEPT`, `SUMMARIZE`, `TOPN`, or user-defined measures; BLANK and 0 compare as equal when grading.
- Self-test: open `dax_trainer.html?selftest&seed=N` and read the browser console (`SELFTEST PASS n/n`).

This is independent of the seeded Meridian dataset in `02_data/`; nothing here reads or changes it.
