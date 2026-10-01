"use strict";
/* Topic 1 - Aggregations. Add challenges to the `challenges` array (see AUTHORING.md). */
registerTopic({
  id:'T01',title:'Aggregations',order:1,
  concept:[
    'A measure is a formula that Power BI evaluates again for every cell of a visual, using the filters that apply to that cell. The simplest measures aggregate one column into one number: `SUM`, `AVERAGE`, `MIN`, `MAX`. `COUNT` counts the non-blank values of a column, `COUNTROWS` counts the rows of a table, and `DISTINCTCOUNT` counts different values. Columns are always written `Table[Column]`.',
    '',
    '  Total Revenue = SUM(Shipment[Revenue])',
    '  Shipments = COUNTROWS(Shipment)',
    '  Customers = DISTINCTCOUNT(Shipment[CustomerKey])',
    '',
    'An aggregation over no rows is BLANK, not 0. The functions respect whatever filters the visual applies, so the same formula gives a different answer in each row.'
  ].join('\n'),
  challenges:[
    {id:'T01-01',v1:'b1',level:'Beginner',title:'Total Revenue',by:['Shipment[Mode]'],checks:['slash','unqual','sumxRedundant'],
     prompt:'Write a measure that returns total revenue: the sum of the Revenue column of Shipment.',
     hint:'SUM adds up one column. Columns are written Table[Column], so here it is Shipment[Revenue].',
     ref:'SUM(Shipment[Revenue])',
     alts:[{code:'SUMX(Shipment, Shipment[Revenue])',warn:'sumxRedundant'}],
     wrongs:[{code:'SUM(Shipment[Cost])'},{code:'COUNTROWS(Shipment)'}],
     why:'SUM(Shipment[Revenue]) respects whatever filters are active (e.g. each Mode row in a visual) and adds up the column.',
     oracle:(D,c)=>H.sumOrNull(H.vis(D,c),s=>s.Revenue)},
    {id:'T01-02',v1:'b2',level:'Beginner',title:'Shipment Count',by:['Shipment[Mode]'],checks:['slash','unqual'],
     prompt:'Write a measure that counts the shipments (one row of Shipment = one shipment).',
     hint:'COUNTROWS counts the rows of a table. Give it the table itself, with no column.',
     ref:'COUNTROWS(Shipment)',
     alts:[{code:'COUNT(Shipment[ShipmentID])'},{code:'DISTINCTCOUNT(Shipment[ShipmentID])'}],
     wrongs:[{code:'DISTINCTCOUNT(Shipment[CustomerKey])'},{code:'SUM(Shipment[IsOnTime])'}],
     why:'COUNTROWS(Shipment) counts the shipment rows left visible by the current filters.',
     oracle:(D,c)=>H.vis(D,c).length},
    {id:'T01-03',v1:'b3',level:'Beginner',title:'Average Cost',by:['Shipment[Mode]'],checks:['slash','unqual'],
     prompt:'Write a measure for the average Cost per shipment.',
     hint:'AVERAGE takes a column and averages its values.',
     ref:'AVERAGE(Shipment[Cost])',
     alts:[{code:'DIVIDE(SUM(Shipment[Cost]), COUNTROWS(Shipment))'},{code:'AVERAGEX(Shipment, Shipment[Cost])'}],
     wrongs:[{code:'SUM(Shipment[Cost])'},{code:'AVERAGE(Shipment[Revenue])'}],
     why:'AVERAGE(Shipment[Cost]) is the sum of Cost divided by the number of shipments, in the current filter context.',
     oracle:(D,c)=>{const r=H.vis(D,c);return r.length?H.sum(r,s=>s.Cost)/r.length:null;}},
    {id:'T01-04',v1:'b4',level:'Beginner',title:'Distinct Customers',by:['Shipment[Mode]'],checks:['slash','unqual'],
     prompt:'How many different customers have shipped? Count each customer once, no matter how many shipments they have.',
     hint:'DISTINCTCOUNT counts unique values in a column. Which column identifies the customer on each shipment?',
     ref:'DISTINCTCOUNT(Shipment[CustomerKey])',
     alts:[{code:'COUNTROWS(VALUES(Shipment[CustomerKey]))'}],
     wrongs:[{code:'COUNTROWS(Shipment)'},{code:'DISTINCTCOUNT(Customer[CustomerKey])'}],
     why:'Use the key on the fact table. DISTINCTCOUNT(Customer[CustomerKey]) counts every customer in the dimension, even ones with no visible shipments, because filters on Shipment do not flow to Customer.',
     oracle:(D,c)=>new Set(H.vis(D,c).map(s=>s.CustomerKey)).size}
  ]
});
