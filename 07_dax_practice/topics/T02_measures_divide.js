"use strict";
/* Topic 2 - Measures & DIVIDE. Library measures ([Total Revenue], [Profit] ...) may be referenced from here on. */
registerTopic({
  id:'T02',title:'Measures & DIVIDE',order:2,
  concept:[
    'A measure can be built from other measures. The page has a small library you can reference by name: `[Total Revenue]`, `[Total Cost]`, `[Profit]`, `[Shipments]`, `[Total FFE]`, `[On-Time %]` (see "Measures you can use"). A ratio must be built from totals, and it must not divide with `/` when the denominator can be zero: `DIVIDE(numerator, denominator, [alternate])` returns BLANK (or the alternate result) instead of an error.',
    '',
    '  Profit = [Total Revenue] - [Total Cost]',
    '  Margin % = DIVIDE([Profit], [Total Revenue])',
    '',
    'BLANK is not 0: a visual hides rows where a measure is BLANK, but shows rows where it is 0.'
  ].join('\n'),
  challenges:[
    {id:'T02-01',v1:'b5',level:'Beginner',title:'Total Profit',by:['Shipment[Mode]'],checks:['slash','sumxRedundant'],
     prompt:'Write a measure for total profit: total Revenue minus total Cost.',
     hint:'You can subtract two aggregations: SUM(...) - SUM(...). A row-by-row SUMX also works, and so do the library measures.',
     ref:'SUM(Shipment[Revenue]) - SUM(Shipment[Cost])',
     alts:[{code:'SUMX(Shipment, Shipment[Revenue] - Shipment[Cost])'},{code:'[Total Revenue] - [Total Cost]'},{code:'[Profit]'}],
     wrongs:[{code:'SUM(Shipment[Revenue])'},{code:'AVERAGE(Shipment[Revenue]) - AVERAGE(Shipment[Cost])'}],
     why:'All forms give the same answer: the sum of per-row profits equals total revenue minus total cost.',
     oracle:(D,c)=>{const r=H.vis(D,c);return H.sumOrNull(r,s=>s.Revenue-s.Cost);}},
    {id:'T02-02',v1:'i2',level:'Intermediate',title:'Margin %',by:['Shipment[Mode]'],checks:['slash','avgRatio'],
     prompt:'Margin % = (Revenue - Cost) / Revenue, computed on totals. Return BLANK rather than an error when revenue is zero.',
     hint:'Use DIVIDE(numerator, denominator). Both parts are sums, not averages of per-shipment percentages.',
     ref:'DIVIDE(SUM(Shipment[Revenue]) - SUM(Shipment[Cost]), SUM(Shipment[Revenue]))',
     alts:[{code:'DIVIDE(SUMX(Shipment, Shipment[Revenue] - Shipment[Cost]), SUM(Shipment[Revenue]))'},
           {code:'DIVIDE([Profit], [Total Revenue])'},
           {code:'(SUM(Shipment[Revenue]) - SUM(Shipment[Cost])) / SUM(Shipment[Revenue])',warn:'slash'}],
     wrongs:[{code:'AVERAGEX(Shipment, DIVIDE(Shipment[Revenue] - Shipment[Cost], Shipment[Revenue]))',warn:'avgRatio'},
             {code:'SUM(Shipment[Revenue]) - SUM(Shipment[Cost])'}],
     why:'A ratio must be built from totals (ratio of sums). Averaging per-shipment percentages gives small shipments the same weight as large ones.',
     oracle:(D,c)=>{const r=H.vis(D,c);const rev=H.sum(r,s=>s.Revenue);return H.div(rev-H.sum(r,s=>s.Cost),rev);}},
    {id:'T02-03',v1:'i3',level:'Intermediate',title:'On-Time %',by:['Shipment[Mode]'],checks:['slash'],
     prompt:'Share of shipments that were on time, written from scratch (do not just reference [On-Time %]). IsOnTime is 1 when on time and 0 otherwise.',
     hint:'IsOnTime is 0/1, so its average is already the on-time rate. DIVIDE(on-time count, all shipments) works as well.',
     ref:'DIVIDE(SUM(Shipment[IsOnTime]), COUNTROWS(Shipment))',
     alts:[{code:'AVERAGE(Shipment[IsOnTime])'},{code:'DIVIDE(CALCULATE(COUNTROWS(Shipment), Shipment[IsOnTime] = 1), COUNTROWS(Shipment))'}],
     wrongs:[{code:'SUM(Shipment[IsOnTime])'},{code:'DIVIDE(COUNTROWS(Shipment), SUM(Shipment[IsOnTime]))'}],
     why:'A 0/1 flag averages into a rate: AVERAGE(IsOnTime) = SUM(IsOnTime) / COUNTROWS.',
     oracle:(D,c)=>{const r=H.vis(D,c);return H.div(H.sum(r,s=>s.IsOnTime),r.length);}}
  ]
});
