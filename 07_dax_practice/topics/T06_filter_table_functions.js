"use strict";
/* Topic 6 - FILTER & table functions. */
registerTopic({
  id:'T06',title:'FILTER & table functions',order:6,
  concept:[
    '`FILTER(table, condition)` returns the rows of a table for which a condition holds; the condition may use several columns or calculated values, which a plain True/False argument of CALCULATE cannot. Table functions return tables, so wrap them in an aggregation: `COUNTROWS(FILTER(...))`, `SUMX(FILTER(...), ...)`. `VALUES(col)` and `DISTINCT(col)` list the distinct values visible in the current context; `ADDCOLUMNS`, `SUMMARIZE` and `CALCULATETABLE` build and reshape tables.',
    '',
    '  High Profit Shipments = COUNTROWS(FILTER(Shipment, Shipment[Revenue] - Shipment[Cost] > 1000))',
    '  Active Customers = COUNTROWS(VALUES(Shipment[CustomerKey]))',
    '',
    'Prefer a simple column filter in CALCULATE when one column is enough; FILTER iterates the whole table.'
  ].join('\n'),
  challenges:[
    {id:'T06-01',v1:'p3',level:'Pro',title:'High-Profit Shipments',by:['Shipment[Mode]'],checks:['slash','unqual','filterInCalc'],
     prompt:P=>'Count shipments whose profit (Revenue - Cost) is greater than '+P.T+'.',
     hint:'The condition uses two columns, so a simple CALCULATE true/false filter will not do. Count the rows of FILTER(Shipment, ...), or sum an IF.',
     ref:P=>'COUNTROWS(FILTER(Shipment, Shipment[Revenue] - Shipment[Cost] > '+P.T+'))',
     alts:P=>[{code:'SUMX(Shipment, IF(Shipment[Revenue] - Shipment[Cost] > '+P.T+', 1, 0))'},
              {code:'COUNTX(FILTER(Shipment, Shipment[Revenue] - Shipment[Cost] > '+P.T+'), Shipment[ShipmentID])'}],
     wrongs:P=>[{code:'COUNTROWS(FILTER(Shipment, Shipment[Revenue] - Shipment[Cost] >= '+P.T+'))'},
                {code:'CALCULATE(COUNTROWS(Shipment), Shipment[Revenue] > '+P.T+')'}],
     why:'The test is on a calculated value (Revenue - Cost), so evaluate it row by row with FILTER over the table. The condition is strictly greater than, not greater-or-equal.',
     oracle:(D,c)=>H.vis(D,c).filter(s=>s.Revenue-s.Cost>c.P.T).length}
  ]
});
