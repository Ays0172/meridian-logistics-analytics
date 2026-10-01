"use strict";
/* Topic 9 - Variables. Stub: add challenges (see AUTHORING.md). */
registerTopic({
  id:'T09',title:'Variables',order:9,
  concept:[
    '`VAR name = expression ... RETURN result` stores a value once and lets you reuse it. A variable is evaluated once, where it is defined, in the filter context of that place; a later CALCULATE cannot change it. Variables make long measures readable, avoid repeating the same calculation, and let you debug: temporarily `RETURN` an intermediate variable to see its value in every row.',
    '',
    '  Growth % =',
    '      VAR Current = [Total Revenue]',
    '      VAR Previous = CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Date[Date]))',
    '      RETURN DIVIDE(Current - Previous, Previous)',
    '',
    'Name variables for what they mean, and put the pieces of a ratio in separate variables.'
  ].join('\n'),
  challenges:[
    {id:'T09-01',level:'Beginner',title:'Profit margin with VARs',by:['Shipment[Mode]'],checks:['slash','unqual','avgRatio'],
     prompt:`Profit margin % = (revenue - cost) / revenue, shown by Mode. Put revenue and cost in their own VARs and finish with a RETURN. The total row is the margin of all shipments together.`,
     hint:`VAR Rev = SUM(Shipment[Revenue])  VAR Cost = SUM(Shipment[Cost])  RETURN DIVIDE(Rev - Cost, Rev)`,
     ref:`VAR Rev = SUM(Shipment[Revenue])
VAR Cost = SUM(Shipment[Cost])
RETURN
    DIVIDE(Rev - Cost, Rev)`,
     alts:[{code:`VAR Rev = [Total Revenue]
VAR Profit = [Profit]
RETURN DIVIDE(Profit, Rev)`},{code:`DIVIDE([Total Revenue] - [Total Cost], [Total Revenue])`}],
     wrongs:[{code:`VAR Rev = SUM(Shipment[Revenue])
VAR Cost = SUM(Shipment[Cost])
RETURN DIVIDE(Rev - Cost, Cost)`},
             {code:`AVERAGEX(Shipment, DIVIDE(Shipment[Revenue] - Shipment[Cost], Shipment[Revenue]))`,warn:'avgRatio'},
             {code:`VAR Rev = SUM(Shipment[Revenue])
VAR Cost = SUM(Shipment[Cost])
RETURN Rev - Cost`}],
     why:`Each VAR is calculated once and then reused by name, so the RETURN line reads like the formula on paper. The ratio is built from two totals; averaging the margin of each shipment would give a small shipment the same weight as a big one, and dividing by cost gives markup, not margin.`,
     oracle:(D,c)=>{const rows=H.vis(D,c);if(!rows.length)return null;const rv=H.sum(rows,s=>s.Revenue),cs=H.sum(rows,s=>s.Cost);return H.div(rv-cs,rv);}},

    {id:'T09-02',level:'Intermediate',title:'The trap: a VAR defined outside CALCULATE',by:['Shipment[Region]'],checks:['slash','unqual','varRepeat'],
     prompt:`For each Region show Ocean revenue minus Air revenue (Ocean first). Build it with one VAR per mode. The total row is the same difference over all regions.`,
     hint:`A VAR keeps the value it had where it was defined. If you write VAR Rev = [Total Revenue] and later CALCULATE(Rev, Shipment[Mode] = "Ocean"), the filter cannot reach inside Rev. Put the CALCULATE inside the VAR instead.`,
     ref:`VAR OceanRev = CALCULATE([Total Revenue], Shipment[Mode] = "Ocean")
VAR AirRev = CALCULATE([Total Revenue], Shipment[Mode] = "Air")
RETURN
    OceanRev - AirRev`,
     alts:[{code:`CALCULATE([Total Revenue], Shipment[Mode] = "Ocean") - CALCULATE([Total Revenue], Shipment[Mode] = "Air")`},
           {code:`VAR OceanRev = CALCULATE(SUM(Shipment[Revenue]), Shipment[Mode] = "Ocean")
VAR AirRev = CALCULATE(SUM(Shipment[Revenue]), Shipment[Mode] = "Air")
RETURN OceanRev - AirRev`}],
     wrongs:[{code:`VAR Rev = [Total Revenue]
VAR OceanRev = CALCULATE(Rev, Shipment[Mode] = "Ocean")
VAR AirRev = CALCULATE(Rev, Shipment[Mode] = "Air")
RETURN OceanRev - AirRev`},
             {code:`CALCULATE([Total Revenue], Shipment[Mode] = "Ocean") - [Total Revenue]`}],
     why:`A variable is evaluated once, at the place where it is defined, in the filter context of that place. Rev already holds the number for the whole row (all modes), so CALCULATE(Rev, Mode = "Ocean") returns that same number and the difference is always 0. The calculation that needs the Mode filter has to be written inside the VAR.`,
     oracle:(D,c)=>{const rows=H.vis(D,c,{drop:['Shipment[Mode]']});const o=H.sum(rows.filter(s=>s.Mode==='Ocean'),s=>s.Revenue),a=H.sum(rows.filter(s=>s.Mode==='Air'),s=>s.Revenue);return o-a;}},

    {id:'T09-03',level:'Intermediate',title:'Revenue relative to the best Mode',by:['Shipment[Mode]'],checks:['slash','unqual'],
     prompt:`Revenue of the row as a share of the revenue of the best Mode (the Mode with the highest revenue). The best Mode shows 100%, the others less. The total row shows total revenue divided by the best Mode's revenue.`,
     hint:`Store the best Mode's revenue in a VAR: MAXX(ALL(Shipment[Mode]), [Total Revenue]) looks at every Mode, not only the one in the row. Then DIVIDE the row's revenue by it.`,
     ref:`VAR BestModeRev = MAXX(ALL(Shipment[Mode]), [Total Revenue])
RETURN
    DIVIDE([Total Revenue], BestModeRev)`,
     alts:[{code:`DIVIDE([Total Revenue], MAXX(ALL(Shipment[Mode]), [Total Revenue]))`},
           {code:`VAR BestModeRev = MAXX(ALLSELECTED(Shipment[Mode]), [Total Revenue])
VAR RowRev = [Total Revenue]
RETURN DIVIDE(RowRev, BestModeRev)`}],
     wrongs:[{code:`VAR BestModeRev = MAXX(VALUES(Shipment[Mode]), [Total Revenue])
RETURN DIVIDE([Total Revenue], BestModeRev)`},
             {code:`DIVIDE([Total Revenue], MAXX(Shipment, Shipment[Revenue]))`},
             {code:`DIVIDE([Total Revenue], CALCULATE([Total Revenue], ALL(Shipment[Mode])))`}],
     why:`MAXX walks over the list of Modes and evaluates [Total Revenue] for each one. With ALL the list contains every Mode even in a Mode row, so the best one is found. VALUES only returns the Mode of the current row, so every row would be its own best (100%). The result is stored in a VAR so the final line stays short.`,
     oracle:(D,c)=>{const per={};H.vis(D,c,{drop:['Shipment[Mode]']}).forEach(s=>per[s.Mode]=(per[s.Mode]||0)+s.Revenue);const best=Math.max.apply(null,Object.values(per));return H.div(H.sumOrNull(H.vis(D,c),s=>s.Revenue),best);}},

    {id:'T09-04',level:'Intermediate',title:'Customer revenue index (1.0 = average customer)',by:['Customer[CustomerName]'],checks:['slash','unqual'],
     prompt:`Revenue index: the customer's revenue divided by the average revenue per customer, where the average is taken over ALL customers. A customer at 1.0 is average, 2.0 is twice the average. The total row shows total revenue divided by the same average.`,
     hint:`Two VARs: the revenue of the row, and AVERAGEX(ALL(Customer[CustomerName]), [Total Revenue]) for the average customer. Then DIVIDE.`,
     ref:`VAR CustRev = [Total Revenue]
VAR AvgCustRev = AVERAGEX(ALL(Customer[CustomerName]), [Total Revenue])
RETURN
    DIVIDE(CustRev, AvgCustRev)`,
     alts:[{code:`VAR CustRev = [Total Revenue]
VAR AvgCustRev = DIVIDE(CALCULATE([Total Revenue], ALL(Customer)), CALCULATE(DISTINCTCOUNT(Customer[CustomerKey]), ALL(Customer)))
RETURN DIVIDE(CustRev, AvgCustRev)`}],
     wrongs:[{code:`VAR CustRev = [Total Revenue]
VAR AvgCustRev = AVERAGEX(VALUES(Customer[CustomerName]), [Total Revenue])
RETURN DIVIDE(CustRev, AvgCustRev)`},
             {code:`DIVIDE([Total Revenue], AVERAGE(Shipment[Revenue]))`}],
     why:`The average has to be computed over all customers, so the iterated list must ignore the customer in the row: ALL(Customer[CustomerName]). With VALUES the list holds only the row's customer and the index is 1.0 everywhere. AVERAGE(Shipment[Revenue]) is the average shipment, not the average customer.`,
     oracle:(D,c)=>{const list=H.byCustomer(H.vis(D,c,{drop:['Customer[CustomerName]']}),s=>s.Revenue);if(!list.length)return null;const avg=H.sum(list,x=>x.val)/list.length;return H.div(H.sumOrNull(H.vis(D,c),s=>s.Revenue),avg);}},

    {id:'T09-05',level:'Intermediate',title:'Debug step: return only the threshold',by:['Shipment[Mode]'],checks:['slash','unqual'],
     prompt:`The next challenge needs a "large shipment" threshold: the average revenue per shipment across ALL shipments, ignoring the Mode of the row. Before building on it, write a measure that returns only this threshold, so you can check it shows the same number on every row, including the total.`,
     hint:`Define VAR Threshold = CALCULATE(AVERAGE(Shipment[Revenue]), ALL(Shipment)) and make the RETURN line return just Threshold. Debugging a long measure works the same way: RETURN one VAR at a time.`,
     ref:`VAR Threshold = CALCULATE(AVERAGE(Shipment[Revenue]), ALL(Shipment))
RETURN
    Threshold`,
     alts:[{code:`CALCULATE(AVERAGE(Shipment[Revenue]), ALL(Shipment[Mode]))`},
           {code:`CALCULATE(DIVIDE([Total Revenue], [Shipments]), REMOVEFILTERS(Shipment))`}],
     wrongs:[{code:`VAR Threshold = AVERAGE(Shipment[Revenue])
RETURN Threshold`},
             {code:`VAR Threshold = AVERAGEX(ALL(Shipment[Mode]), [Total Revenue])
RETURN Threshold`}],
     why:`Returning an intermediate VAR is the quickest debugger DAX has: the visual shows exactly what the variable holds in every row. A correct threshold is one number repeated down the whole column; if it changes by Mode, the filter was not removed. The second wrong answer is a different number altogether: the average revenue per Mode, not per shipment.`,
     oracle:(D,c)=>{const all=H.vis(D,c,{drop:['Shipment']});return all.length?H.sum(all,s=>s.Revenue)/all.length:null;}},

    {id:'T09-06',level:'Pro',title:'Share of revenue from large shipments',by:['Shipment[Mode]'],checks:['slash','unqual','varRepeat'],
     prompt:`Large-shipment share: of the row's revenue, the % that comes from shipments whose revenue is above the average revenue per shipment across ALL shipments (the threshold from the previous challenge). The total row uses the same threshold over all shipments. A Mode with no large shipment shows BLANK.`,
     hint:`Three steps in three VARs: Threshold (ALL), LargeRev = CALCULATE([Total Revenue], FILTER(Shipment, Shipment[Revenue] > Threshold)), and the row's revenue. Remember the VAR holding the threshold is fixed before FILTER runs.`,
     ref:`VAR Threshold = CALCULATE(AVERAGE(Shipment[Revenue]), ALL(Shipment))
VAR LargeRev = CALCULATE([Total Revenue], FILTER(Shipment, Shipment[Revenue] > Threshold))
RETURN
    DIVIDE(LargeRev, [Total Revenue])`,
     alts:[{code:`VAR Threshold = CALCULATE(AVERAGE(Shipment[Revenue]), ALL(Shipment))
VAR LargeRev = SUMX(FILTER(Shipment, Shipment[Revenue] > Threshold), Shipment[Revenue])
RETURN DIVIDE(LargeRev, SUM(Shipment[Revenue]))`}],
     wrongs:[{code:`VAR Threshold = AVERAGE(Shipment[Revenue])
VAR LargeRev = CALCULATE([Total Revenue], FILTER(Shipment, Shipment[Revenue] > Threshold))
RETURN DIVIDE(LargeRev, [Total Revenue])`},
             {code:`VAR Threshold = CALCULATE(AVERAGE(Shipment[Revenue]), ALL(Shipment))
VAR LargeRev = CALCULATE([Total Revenue], FILTER(Shipment, Shipment[Revenue] > Threshold))
RETURN DIVIDE(LargeRev, CALCULATE([Total Revenue], ALL(Shipment)))`}],
     why:`The threshold must be one company-wide number, so it is computed with ALL(Shipment) once, in a VAR, before the FILTER uses it. Without ALL each Mode compares its shipments with its own average (about half of them are "large" by definition). Dividing by the grand total instead of the row's revenue answers a different question: how much of the whole company's revenue is large shipments in this Mode.`,
     oracle:(D,c)=>{const all=H.vis(D,c,{drop:['Shipment']});if(!all.length)return null;const thr=H.sum(all,s=>s.Revenue)/all.length;const rows=H.vis(D,c);const tot=H.sumOrNull(rows,s=>s.Revenue);return H.div(H.sumOrNull(rows.filter(s=>s.Revenue>thr),s=>s.Revenue),tot);}},

    {id:'T09-07',level:'Pro',title:'Margin gap to the company, only for busy customers',by:['Customer[CustomerName]'],checks:['slash','unqual','varRepeat'],
     prompt:P=>`For each customer show the profit margin (profit / revenue) minus the margin of ALL customers together, in margin points (0.02 = 2 points). Show BLANK for customers with fewer than ${P.n} shipments. The total row follows the same rule (it passes the shipment test and equals 0).`,
     hint:`Steps: (1) the number of shipments, (2) the row's margin, (3) the company margin with ALL(Customer) so the customer filter is removed, (4) RETURN IF(shipments >= n, margin - company margin). Shipment is the fact table: ALL(Shipment) would leave the customer filter in place.`,
     ref:P=>`VAR ShipCount = [Shipments]
VAR RowMargin = DIVIDE([Profit], [Total Revenue])
VAR CompanyMargin = CALCULATE(DIVIDE([Profit], [Total Revenue]), ALL(Customer))
RETURN
    IF(ShipCount >= ${P.n}, RowMargin - CompanyMargin)`,
     alts:P=>[{code:`VAR RowMargin = DIVIDE([Profit], [Total Revenue])
VAR CompanyMargin = CALCULATE(DIVIDE([Profit], [Total Revenue]), ALL(Customer[CustomerName]))
RETURN IF([Shipments] >= ${P.n}, RowMargin - CompanyMargin)`}],
     wrongs:P=>[{code:`VAR ShipCount = [Shipments]
VAR RowMargin = DIVIDE([Profit], [Total Revenue])
VAR CompanyMargin = CALCULATE(DIVIDE([Profit], [Total Revenue]), ALL(Shipment))
RETURN IF(ShipCount >= ${P.n}, RowMargin - CompanyMargin)`},
                {code:`VAR ShipCount = [Shipments]
VAR RowMargin = DIVIDE([Profit], [Total Revenue])
VAR CompanyMargin = CALCULATE(DIVIDE([Profit], [Total Revenue]), ALL(Customer))
RETURN IF(ShipCount > ${P.n}, RowMargin - CompanyMargin)`},
                {code:`VAR RowMargin = DIVIDE([Profit], [Total Revenue])
VAR CompanyMargin = CALCULATE(DIVIDE([Profit], [Total Revenue]), ALL(Customer))
RETURN RowMargin - CompanyMargin`}],
     why:`Customer filters the Shipment table, but ALL(Shipment) does not remove a filter that sits on Customer, so the "company margin" would still be this customer's own margin and the gap is always 0. ALL(Customer) removes it. The boundary matters too: "fewer than n" blanks the rows below n, so a customer with exactly n shipments stays visible (>=, not >).`,
     oracle:(D,c)=>{const rows=H.vis(D,c);if(rows.length<c.P.n)return null;const rv=H.sum(rows,s=>s.Revenue);const m=H.div(rv-H.sum(rows,s=>s.Cost),rv);const all=H.vis(D,c,{drop:['Customer']});const ar=H.sum(all,s=>s.Revenue);const cm=H.div(ar-H.sum(all,s=>s.Cost),ar);return (m==null||cm==null)?null:m-cm;}}
  ]
});
