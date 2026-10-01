"use strict";
/* Topic 11 - Ranking & Top N. Oracles work from per-customer revenue lists (H.byCustomer, sorted high to low). */
(function(){
  const REV=s=>s.Revenue;
  const NAME='Customer[CustomerName]';
  // revenue (or other value) per customer visible on the row, ignoring the row's own customer filter
  const perCust=(D,c,f)=>H.byCustomer(H.vis(D,c,{drop:[NAME]}),f||REV);
  const keyOf=(D,name)=>D.Customer.find(x=>x.CustomerName===name).CustomerKey;
  const nameOf=(D,key)=>D.Customer.find(x=>x.CustomerKey===key).CustomerName;
  const rank=(list,key,desc,dense)=>{
    const me=list.find(x=>x.key===key);if(!me)return null;
    const better=list.filter(x=>desc?x.val>me.val:x.val<me.val).map(x=>x.val);
    return (dense?new Set(better).size:better.length)+1;
  };
  // revenue of the top n customers of the row (no tie at the cut-off is guaranteed for the overall data and per year)
  const topSum=(D,c,n)=>{const l=perCust(D,c);return l.length?H.sum(l.slice(0,n),x=>x.val):null;};

registerTopic({
  id:'T11',title:'Ranking & Top N',order:11,
  concept:[
    '`RANKX(table, expression, [value], [ASC|DESC], [SKIP|DENSE])` ranks the current row among the rows of a table. The table decides who competes: `ALL(Customer[CustomerName])` ranks against every customer, `ALLSELECTED(Customer[CustomerName])` only against those the slicers leave. Ties share a rank; SKIP leaves a gap after a tie (1, 1, 3) and DENSE does not (1, 1, 2). `TOPN(n, table, expression)` returns the top n rows and keeps all rows tied at the cut-off. `CONCATENATEX` joins values into text.',
    '',
    '  Customer Rank = RANKX(ALL(Customer[CustomerName]), [Total Revenue], , DESC, DENSE)',
    '  Top 3 Revenue = CALCULATE([Total Revenue], TOPN(3, ALL(Customer[CustomerName]), [Total Revenue]))'
  ].join('\n'),
  challenges:[
    {id:'T11-01',level:'Beginner',title:'Customer revenue rank',by:['Customer[CustomerName]'],checks:['slash','unqual'],
     prompt:`Rank every customer by revenue: 1 = the customer with the highest revenue, ranked against ALL customers. The total row must stay BLANK (a grand total has no rank).`,
     hint:`RANKX(ALL(Customer[CustomerName]), [Total Revenue]) ranks highest first by default. Wrap it in IF(HASONEVALUE(Customer[CustomerName]), ...) so the total row stays empty.`,
     ref:`IF(
    HASONEVALUE(Customer[CustomerName]),
    RANKX(ALL(Customer[CustomerName]), [Total Revenue], , DESC, DENSE)
)`,
     alts:[{code:`IF(ISINSCOPE(Customer[CustomerName]), RANKX(ALL(Customer[CustomerName]), [Total Revenue]))`},
           {code:`IF(HASONEVALUE(Customer[CustomerName]), RANKX(ALL(Customer[CustomerName]), CALCULATE(SUM(Shipment[Revenue]))))`}],
     wrongs:[{code:`RANKX(ALL(Customer[CustomerName]), [Total Revenue], , DESC, DENSE)`},
             {code:`IF(HASONEVALUE(Customer[CustomerName]), RANKX(ALL(Customer[CustomerName]), SUM(Shipment[Revenue])))`},
             {code:`IF(HASONEVALUE(Customer[CustomerName]), RANKX(ALL(Customer[CustomerName]), [Total Revenue], , ASC))`}],
     why:`RANKX evaluates the expression once for every customer in the list and tells you where the current value falls. The list must be ALL(Customer[CustomerName]); with VALUES it would only hold the row's own customer. A bare SUM does not become a per-customer value inside RANKX (no context transition), so every customer ties at rank 1: use the measure. Without the HASONEVALUE guard the total row ranks the grand total (rank 1).`,
     oracle:(D,c)=>{const nm=c.sel[NAME];if(nm==null)return null;return rank(perCust(D,c),keyOf(D,nm),true,true);}},

    {id:'T11-02',level:'Intermediate',title:'Ties: DENSE vs SKIP',by:['Customer[CustomerName]'],checks:['slash','unqual'],
     prompt:P=>`Rank customers by the number of shipments, FEWEST first (rank 1 = the customer with the fewest shipments). Customers with the same count share a rank, and the next rank follows without a gap (1, 1, 2, not 1, 1, 3). Several customers have exactly ${P.tieN} shipments. The total row stays BLANK.`,
     hint:`RANKX(table, expression, value, order, ties): the order is ASC for "fewest first", and the ties argument DENSE closes the gaps. SKIP is the default.`,
     ref:`IF(
    HASONEVALUE(Customer[CustomerName]),
    RANKX(ALL(Customer[CustomerName]), [Shipments], , ASC, DENSE)
)`,
     alts:[{code:`IF(ISINSCOPE(Customer[CustomerName]), RANKX(ALL(Customer[CustomerName]), CALCULATE(COUNTROWS(Shipment)), , ASC, DENSE))`}],
     wrongs:[{code:`IF(HASONEVALUE(Customer[CustomerName]), RANKX(ALL(Customer[CustomerName]), [Shipments], , ASC, SKIP))`},
             {code:`IF(HASONEVALUE(Customer[CustomerName]), RANKX(ALL(Customer[CustomerName]), [Shipments], , DESC, DENSE))`}],
     why:`With SKIP (the default) two tied customers both get rank 3 and the next customer gets 5: the tie "uses up" two positions. DENSE gives the next customer 4. Use DENSE for "level" style rankings and SKIP when the rank means "how many are strictly ahead of me, plus one". A bare COUNTROWS(Shipment) inside RANKX would not give a value per customer; wrap it in CALCULATE or use the measure.`,
     oracle:(D,c)=>{const nm=c.sel[NAME];if(nm==null)return null;return rank(perCust(D,c,()=>1),keyOf(D,nm),false,true);}},

    {id:'T11-03',level:'Intermediate',title:'Rank among the selected customers (ALLSELECTED)',by:['Customer[CustomerName]'],checks:['slash','unqual'],
     slicer:[{col:'Customer[CustomerName]',vals:['Apex Retail','Cedar Textiles','Falcon Electronics','Harbor Toys','Juniper Paper','Maple Beverages']}],
     prompt:`A report slicer limits the report to six customers. Rank those customers by revenue among themselves: 1 = highest of the six, so the ranks run from 1 to 6. The total row stays BLANK.`,
     hint:`ALL(Customer[CustomerName]) always ranks against all 15 customers, whatever the slicer says. ALLSELECTED(Customer[CustomerName]) keeps the slicer's selection, so only the six selected customers compete.`,
     ref:`IF(
    HASONEVALUE(Customer[CustomerName]),
    RANKX(ALLSELECTED(Customer[CustomerName]), [Total Revenue], , DESC, DENSE)
)`,
     alts:[{code:`IF(ISINSCOPE(Customer[CustomerName]), RANKX(ALLSELECTED(Customer[CustomerName]), [Total Revenue]))`}],
     wrongs:[{code:`IF(HASONEVALUE(Customer[CustomerName]), RANKX(ALL(Customer[CustomerName]), [Total Revenue], , DESC, DENSE))`},
             {code:`RANKX(ALLSELECTED(Customer[CustomerName]), [Total Revenue], , DESC, DENSE)`}],
     why:`RANKX evaluates the expression once per customer in the list, and each customer in the list replaces the slicer's filter on that column. With ALL the list holds all 15 customers, so each of the six shows its rank among 15 (for example 9th). ALLSELECTED returns only the customers the slicer left, so the rank is 1 to 6. The guard keeps the total row (six customers selected) from showing a rank.`,
     oracle:(D,c)=>{const nm=c.sel[NAME];if(nm==null)return null;const l=H.byCustomer(H.vis(D,Object.assign({},c,{sel:{}})),REV);return rank(l,keyOf(D,nm),true,true);}},

    {id:'T11-04',level:'Intermediate',title:'Revenue of the top 3 customers (TOPN)',by:['Date[Year]'],checks:['slash','unqual','varRepeat'],
     prompt:P=>`For each year, the combined revenue of the ${P.topN} customers with the highest revenue IN THAT YEAR (the top ${P.topN} can be different people each year). The total row uses the top ${P.topN} over all years.`,
     hint:`TOPN(n, ALL(Customer[CustomerName]), [Total Revenue]) returns the n customers with the highest revenue in the row's period. Pass that table to CALCULATE as a filter.`,
     ref:P=>`CALCULATE([Total Revenue], TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]))`,
     alts:P=>[{code:`SUMX(TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]), [Total Revenue])`},
              {code:`VAR TopCustomers = TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue])
RETURN CALCULATE([Total Revenue], TopCustomers)`}],
     wrongs:P=>[{code:`CALCULATE([Total Revenue], TOPN(${P.topN}, ALL(Customer[CustomerName]), CALCULATE([Total Revenue], ALL(Date))))`},
                {code:`CALCULATE([Total Revenue], TOPN(${P.topN}, ALL(Customer[CustomerName]), [Shipments]))`}],
     why:`TOPN is evaluated in the filter context of the row (the year), so [Total Revenue] inside it is each customer's revenue in that year, and the table it returns holds that year's best customers. CALCULATE then uses that table as a filter. Ranking by all-time revenue (ALL(Date)) or by another measure picks the wrong customers.`,
     oracle:(D,c)=>topSum(D,c,c.P.topN)},

    {id:'T11-05',level:'Pro',title:'Rank within the customer\'s segment',by:['Customer[Segment]','Customer[CustomerName]'],checks:['slash','unqual'],
     prompt:`Show each customer's revenue rank INSIDE its own Segment: the best Key customer is 1, and the best Standard customer is also 1. The Segment subtotal rows and the grand total stay BLANK.`,
     hint:`With one column in the list, each iterated customer replaces only the CustomerName filter, so customers of the other Segment come out BLANK and are ignored: that gives a rank inside the Segment. ALL(Customer) (the whole table) would also replace the Segment filter and rank against everyone.`,
     ref:`IF(
    HASONEVALUE(Customer[CustomerName]),
    RANKX(ALL(Customer[CustomerName]), [Total Revenue], , DESC, DENSE)
)`,
     alts:[{code:`IF(ISINSCOPE(Customer[CustomerName]), RANKX(ALL(Customer[CustomerName]), [Total Revenue]))`}],
     wrongs:[{code:`IF(HASONEVALUE(Customer[CustomerName]), RANKX(ALL(Customer), [Total Revenue], , DESC, DENSE))`},
             {code:`RANKX(ALL(Customer[CustomerName]), [Total Revenue], , DESC, DENSE)`}],
     why:`The Segment filter of the row stays active while RANKX iterates, so a customer from the other Segment has no revenue in this row and is skipped: the rank is inside the Segment. ALL(Customer) lists whole customer rows; each one replaces Segment as well as the name, so every customer keeps its revenue and the rank is global. Without a guard the subtotal and total rows would show a rank of the subtotal itself.`,
     oracle:(D,c)=>{const nm=c.sel[NAME];if(c.level<2||nm==null)return null;return rank(perCust(D,c),keyOf(D,nm),true,true);}},

    {id:'T11-06',level:'Pro',title:'Top 3 share of revenue',by:['Date[Year]'],checks:['slash','unqual','varRepeat'],
     prompt:P=>`For each year: the % of that year's revenue that comes from its top ${P.topN} customers (best ${P.topN} in that same year). The total row is the share for all years together.`,
     hint:`Put the top-n revenue in a VAR (CALCULATE + TOPN, as before), then DIVIDE it by the revenue of the row.`,
     ref:P=>`VAR TopRev = CALCULATE([Total Revenue], TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]))
RETURN
    DIVIDE(TopRev, [Total Revenue])`,
     alts:P=>[{code:`DIVIDE(SUMX(TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]), [Total Revenue]), [Total Revenue])`}],
     wrongs:P=>[{code:`VAR TopRev = CALCULATE([Total Revenue], TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]))
RETURN DIVIDE(TopRev, CALCULATE([Total Revenue], ALL(Date)))`},
                {code:`VAR TopRev = CALCULATE([Total Revenue], TOPN(${P.topN}, ALL(Customer[CustomerName]), CALCULATE([Total Revenue], ALL(Date))))
RETURN DIVIDE(TopRev, [Total Revenue])`}],
     why:`Numerator and denominator must describe the same period. The numerator is the top customers' revenue for the year; the denominator is the revenue of the year, so use the plain measure. Dividing by all-time revenue turns it into "share of the whole history", and choosing the top customers by all-time revenue answers a different question.`,
     oracle:(D,c)=>H.div(topSum(D,c,c.P.topN),H.sumOrNull(H.vis(D,c),REV))},

    {id:'T11-07',level:'Pro',title:'"Others" revenue (total minus top 3)',by:['Date[Year]'],checks:['slash','unqual','varRepeat'],
     prompt:P=>`For each year, the revenue of all customers that are NOT in that year's top ${P.topN}: total revenue minus the top ${P.topN} customers' revenue. The total row is the same for all years together.`,
     hint:`Compute the top-n revenue in a VAR and subtract it from [Total Revenue]. Both numbers must be taken in the same period.`,
     ref:P=>`VAR TopRev = CALCULATE([Total Revenue], TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]))
RETURN
    [Total Revenue] - TopRev`,
     alts:P=>[{code:`[Total Revenue] - SUMX(TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]), [Total Revenue])`}],
     wrongs:P=>[{code:`CALCULATE([Total Revenue], TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]))`},
                {code:`VAR TopRev = CALCULATE([Total Revenue], TOPN(${P.topN}, ALL(Customer[CustomerName]), CALCULATE([Total Revenue], ALL(Date))))
RETURN [Total Revenue] - TopRev`}],
     why:`"Others" is the rest: everything minus the top group. The top group has to be chosen inside the period of the row (TOPN evaluates [Total Revenue] in that period). Choosing it by all-time revenue removes the wrong customers in some years, so the "others" no longer add up with the top n to the year's total.`,
     oracle:(D,c)=>{const tot=H.sumOrNull(H.vis(D,c),REV);if(tot==null)return null;return tot-topSum(D,c,c.P.topN);}},

    {id:'T11-08',level:'Pro',title:'Names of the top 3 customers as text',by:['Date[Year]'],checks:['unqual'],
     prompt:P=>`For each year, a text with the names of the top ${P.topN} customers by revenue IN THAT YEAR, best first, separated by a comma and a space (for example "Alpha, Beta, Gamma"). The total row lists the top ${P.topN} over all years.`,
     hint:`CONCATENATEX(table, expression, delimiter, orderBy, ASC|DESC) joins text. The table is TOPN(...). Give an order-by expression, otherwise the order is not guaranteed.`,
     ref:P=>`CONCATENATEX(
    TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]),
    Customer[CustomerName],
    ", ",
    [Total Revenue], DESC
)`,
     alts:P=>[{code:`CONCATENATEX(TOPN(${P.topN}, VALUES(Customer[CustomerName]), [Total Revenue]), Customer[CustomerName], ", ", [Total Revenue], DESC)`}],
     wrongs:P=>[{code:`CONCATENATEX(TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]), Customer[CustomerName], ", ", [Total Revenue], ASC)`},
                {code:`CONCATENATEX(TOPN(${P.topN}, ALL(Customer[CustomerName]), [Total Revenue]), Customer[CustomerName], ", ", Customer[CustomerName], ASC)`},
                {code:`CONCATENATEX(ALL(Customer[CustomerName]), Customer[CustomerName], ", ", [Total Revenue], DESC)`}],
     why:`TOPN picks the customers; CONCATENATEX turns them into one text. The order-by argument (a measure, evaluated per customer, DESC) makes the best customer come first. Ordering by name would give an alphabetical list, and leaving TOPN out would list all 15 customers.`,
     oracle:(D,c)=>{const l=perCust(D,c);if(!l.length)return null;return l.slice(0,c.P.topN).map(x=>nameOf(D,x.key)).join(', ');}}
  ]
});
})();
