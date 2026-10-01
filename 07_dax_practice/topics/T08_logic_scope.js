"use strict";
/* Topic 8 - Logic & scope. Stub: add challenges (see AUTHORING.md). */
registerTopic({
  id:'T08',title:'Logic & scope',order:8,
  concept:[
    '`IF` and `SWITCH` choose a result. `SWITCH(TRUE(), cond1, result1, cond2, result2, ..., else)` is the readable way to write a ladder of conditions. `SELECTEDVALUE(col, alternate)` returns the one value left by the filters, or the alternate when there are zero or several. `HASONEVALUE(col)` tests exactly that. `ISINSCOPE(col)` is true only on the rows of a visual that are grouped by that column, so a measure can show a different value on the total row. `COALESCE` returns its first non-blank argument.',
    '',
    '  Band = SWITCH(TRUE(), [Total Revenue] > 100000, "High", [Total Revenue] > 50000, "Medium", "Low")',
    '  Label = IF(ISINSCOPE(Customer[CustomerName]), [Total Revenue], BLANK())'
  ].join('\n'),
  challenges:[]
});
