"use strict";
/* Topic 7 - Context transition. */
registerTopic({
  id:'T07',title:'Context transition',order:7,
  concept:[
    'Inside an iterator you have a row context (the current row), but aggregations such as `SUM` only see the filter context. `CALCULATE` converts the current row into filters, which is called context transition. A reference to a measure does the same automatically: `[Total Revenue]` is really `CALCULATE([Total Revenue])`. That is why a measure works per customer inside `SUMX(Customer, ...)` while a bare `SUM` gives the grand total for every row.',
    '',
    '  Busy Customer Revenue =',
    '      SUMX(FILTER(VALUES(Shipment[CustomerKey]), CALCULATE(COUNTROWS(Shipment)) > 25),',
    '           CALCULATE(SUM(Shipment[Revenue])))',
    '',
    'If an iterator seems to return the same number on every row, check where the transition is missing.'
  ].join('\n'),
  challenges:[
    {id:'T07-01',v1:'p5',level:'Pro',title:'Revenue from Busy Customers',by:['Customer[Segment]'],checks:['slash','unqual'],
     prompt:P=>'Total revenue from customers with more than '+P.n+' shipments (in the current filter context). Shown by customer Segment.',
     hint:'Iterate the customers: SUMX(FILTER(VALUES(Shipment[CustomerKey]), <shipments of this customer> > n), <revenue of this customer>). Each inner measure needs CALCULATE to apply the current customer.',
     ref:P=>'SUMX(\n  FILTER(VALUES(Shipment[CustomerKey]), CALCULATE(COUNTROWS(Shipment)) > '+P.n+'),\n  CALCULATE(SUM(Shipment[Revenue]))\n)',
     alts:P=>[{code:'SUMX(FILTER(Customer, CALCULATE(COUNTROWS(Shipment)) > '+P.n+'), CALCULATE(SUM(Shipment[Revenue])))'},
              {code:'SUMX(FILTER(VALUES(Customer[CustomerKey]), CALCULATE(COUNTROWS(Shipment)) > '+P.n+'), CALCULATE(SUM(Shipment[Revenue])))'},
              {code:'SUMX(FILTER(Customer, [Shipments] > '+P.n+'), [Total Revenue])'}],
     wrongs:P=>[{code:'SUM(Shipment[Revenue])'},
                {code:'SUMX(FILTER(VALUES(Shipment[CustomerKey]), CALCULATE(COUNTROWS(Shipment)) >= '+P.n+'), CALCULATE(SUM(Shipment[Revenue])))'},
                {code:'SUMX(FILTER(VALUES(Shipment[CustomerKey]), COUNTROWS(Shipment) > '+P.n+'), SUM(Shipment[Revenue]))'}],
     why:'Inside an iterator, CALCULATE (or a measure reference) turns the current row (the current customer) into a filter - context transition. Without it, COUNTROWS and SUM ignore the current customer and see every shipment.',
     oracle:(D,c)=>{const rows=H.vis(D,c);const by=H.byCustomer(rows,()=>1);const cnt={};by.forEach(x=>cnt[x.key]=x.val);
       return H.sumOrNull(rows.filter(s=>cnt[s.CustomerKey]>c.P.n),s=>s.Revenue);}}
  ]
});
