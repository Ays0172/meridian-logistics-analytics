"use strict";
/* Topic 3 - Iterators. Stub: add challenges (see AUTHORING.md). */
registerTopic({
  id:'T03',title:'Iterators',order:3,
  concept:[
    'An iterator (`SUMX`, `AVERAGEX`, `MAXX`, `MINX`, `COUNTX`) walks a table row by row, evaluates an expression in each row, and then aggregates the results. Inside the expression you can use the columns of the current row, and `RELATED(Customer[Segment])` fetches a column from the one-side of a relationship.',
    '',
    '  Gross Weight Revenue = SUMX(Shipment, Shipment[Revenue] * Shipment[Weight])',
    '  Key Revenue = SUMX(Shipment, IF(RELATED(Customer[Segment]) = "Key", Shipment[Revenue], 0))',
    '',
    'Use an iterator when the value needs more than one column per row. A weighted average is SUMX(...) divided by the total weight; an average of per-row ratios (AVERAGEX of a division) is usually not what you want.'
  ].join('\n'),
  challenges:[]
});
