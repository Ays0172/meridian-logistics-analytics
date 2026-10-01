"use strict";
/* Topic 11 - Ranking & Top N. Stub: add challenges (see AUTHORING.md). */
registerTopic({
  id:'T11',title:'Ranking & Top N',order:11,
  concept:[
    '`RANKX(table, expression, [value], [ASC|DESC], [SKIP|DENSE])` ranks the current row among the rows of a table. The table decides who competes: `ALL(Customer[CustomerName])` ranks against every customer, `ALLSELECTED(Customer[CustomerName])` only against those the slicers leave. Ties share a rank; SKIP leaves a gap after a tie (1, 1, 3) and DENSE does not (1, 1, 2). `TOPN(n, table, expression)` returns the top n rows and keeps all rows tied at the cut-off. `CONCATENATEX` joins values into text.',
    '',
    '  Customer Rank = RANKX(ALL(Customer[CustomerName]), [Total Revenue], , DESC, DENSE)',
    '  Top 3 Revenue = CALCULATE([Total Revenue], TOPN(3, ALL(Customer[CustomerName]), [Total Revenue]))'
  ].join('\n'),
  challenges:[]
});
