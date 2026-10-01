"use strict";
/* Topic 12 - Capstone: long, multi-step measures (all Pro). Each prompt numbers the steps the measure must perform. */
(function(){
  const REV=s=>s.Revenue;
  const NAME='Customer[CustomerName]';
  const range=(D,c)=>H.dateRange(D,c);
  const rev=(D,c,a,b)=>H.inRange(D,c,a,b,REV);
  const shifted=(r,k)=>({min:H.som(H.shiftMonths(r.min,k)),max:H.eom(H.shiftMonths(r.max,k))});
  const perCust=(D,c)=>H.byCustomer(H.vis(D,c,{drop:[NAME]}),REV);
  // cumulative share of revenue (highest customer first, the customer itself included) for the customer in the row, or null
  const cumShare=(D,c)=>{
    const nm=c.sel[NAME];if(nm==null)return null;
    const l=perCust(D,c);const me=l.find(x=>D.Customer.find(k=>k.CustomerKey===x.key).CustomerName===nm);
    if(!me)return null;
    const tot=H.sum(l,x=>x.val);
    return H.div(H.sum(l.filter(x=>x.val>=me.val),x=>x.val),tot);
  };

registerTopic({
  id:'T12',title:'Capstone: big DAX',order:12,
  concept:[
    'Real report measures combine everything: variables for each step, time intelligence for the comparison period, `ALL`/`ALLSELECTED` for totals, `RANKX`/`TOPN` for rankings, `SWITCH` for classification, and blank-safe checks so the first period or an empty row does not show nonsense. Write them top-down: name each step as a VAR, check each step by returning it, and only then combine them in the final RETURN.',
    '',
    '  Budget Variance % =',
    '      VAR Actual = [Total Revenue]',
    '      VAR Budget = CALCULATE(SUM(Target[TargetRevenue]), TREATAS(VALUES(Date[YearMonth]), Target[YearMonth]), TREATAS(VALUES(Shipment[Region]), Target[Region]))',
    '      RETURN IF(NOT(ISBLANK(Budget)), DIVIDE(Actual - Budget, Budget))',
    '',
    'Each prompt in this topic lists the steps; follow them in order.'
  ].join('\n'),
  challenges:[
    {id:'T12-01',level:'Pro',title:'YoY % growth, blank-safe',by:['Date[Year]','Date[MonthNo]'],checks:['slash','unqual','hardcodedPeriod','varRepeat'],
     slicer:[{col:'Shipment[Region]',vals:['Asia','Europe']}],
     prompt:`Year-over-year growth % of revenue, shown by year with the months below it (the slicer limits the report to Asia and Europe).\nSteps:\n1) Cur = revenue of the row\n2) PY = revenue of the same period one year earlier\n3) return BLANK when PY is blank or 0 (the whole first year, and any month without prior-year revenue)\n4) otherwise (Cur - PY) / PY. A year row compares with the whole previous year.`,
     hint:`VAR Cur = [Total Revenue]  VAR PY = CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Date[Date]))  RETURN IF(...PY is not blank..., DIVIDE(Cur - PY, PY))`,
     ref:`VAR Cur = [Total Revenue]
VAR PY = CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Date[Date]))
RETURN
    IF(NOT(ISBLANK(PY)) && PY <> 0, DIVIDE(Cur - PY, PY))`,
     alts:[{code:`VAR PY = CALCULATE([Total Revenue], DATEADD(Date[Date], -1, YEAR))
RETURN IF(ISBLANK(PY), BLANK(), DIVIDE([Total Revenue] - PY, PY))`}],
     wrongs:[{code:`VAR Cur = [Total Revenue]
VAR PY = CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Date[Date]))
RETURN DIVIDE(Cur, PY) - 1`},
             {code:`VAR Cur = [Total Revenue]
VAR PY = CALCULATE([Total Revenue], DATEADD(Date[Date], -1, MONTH))
RETURN IF(NOT(ISBLANK(PY)), DIVIDE(Cur - PY, PY))`},
             {code:`[Total Revenue] - CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Date[Date]))`}],
     why:`DIVIDE(Cur, PY) is BLANK when PY is BLANK, but BLANK - 1 is -1, so the "ratio minus one" shortcut shows -100% for every month of the first year. Computing the difference first and dividing by PY (inside a blank check) keeps those months empty. SAMEPERIODLASTYEAR shifts the whole selection of the row, so a year row compares with the full previous year and a month row with the same month.`,
     oracle:(D,c)=>{const r=range(D,c);if(!r)return null;const p=shifted(r,-12);const py=rev(D,c,p.min,p.max);if(py==null||py===0)return null;const cur=rev(D,c,r.min,r.max)||0;return (cur-py)/py;}},

    {id:'T12-02',level:'Pro',title:'Pareto: cumulative % of revenue by customer',by:['Customer[CustomerName]'],checks:['slash','unqual','varRepeat'],
     slicer:[{col:'Shipment[Mode]',vals:['Ocean','Road']}],
     prompt:`Pareto cumulative %: customers ranked by revenue (highest first); for each customer, the % of total revenue earned by that customer PLUS all customers with higher revenue. The slicer limits the report to Ocean and Road, and the percentages are of what the slicer leaves. The best customer shows its own share, the last one 100%. The total row stays BLANK.\nSteps:\n1) CustRev = revenue of the row (a VAR, because it must not change inside the filter)\n2) AllRev = revenue of all selected customers\n3) Running = sum of revenue of the customers whose revenue >= CustRev\n4) return Running / AllRev.`,
     hint:`VAR Running = SUMX(FILTER(ALLSELECTED(Customer[CustomerName]), [Total Revenue] >= CustRev), [Total Revenue]). The comparison must use the VAR: inside FILTER, [Total Revenue] is re-evaluated for each customer, so comparing it with itself is always true.`,
     ref:`VAR CustRev = [Total Revenue]
VAR AllRev = CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName]))
VAR Running = SUMX(
    FILTER(ALLSELECTED(Customer[CustomerName]), [Total Revenue] >= CustRev),
    [Total Revenue])
RETURN
    IF(HASONEVALUE(Customer[CustomerName]), DIVIDE(Running, AllRev))`,
     alts:[{code:`VAR CustRev = [Total Revenue]
VAR AllRev = CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName]))
VAR Running = CALCULATE([Total Revenue], FILTER(ALLSELECTED(Customer[CustomerName]), [Total Revenue] >= CustRev))
RETURN IF(ISINSCOPE(Customer[CustomerName]), DIVIDE(Running, AllRev))`}],
     wrongs:[{code:`VAR CustRev = [Total Revenue]
VAR AllRev = CALCULATE([Total Revenue], ALL(Shipment))
VAR Running = SUMX(FILTER(ALLSELECTED(Customer[CustomerName]), [Total Revenue] >= CustRev), [Total Revenue])
RETURN IF(HASONEVALUE(Customer[CustomerName]), DIVIDE(Running, AllRev))`},
             {code:`VAR CustRev = [Total Revenue]
VAR AllRev = CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName]))
VAR Running = SUMX(FILTER(ALLSELECTED(Customer[CustomerName]), [Total Revenue] > CustRev), [Total Revenue])
RETURN IF(HASONEVALUE(Customer[CustomerName]), DIVIDE(Running, AllRev))`},
             {code:`VAR AllRev = CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName]))
VAR Running = SUMX(FILTER(ALLSELECTED(Customer[CustomerName]), [Total Revenue] >= [Total Revenue]), [Total Revenue])
RETURN IF(HASONEVALUE(Customer[CustomerName]), DIVIDE(Running, AllRev))`}],
     why:`Running total over a ranking = sum of every customer whose revenue is at least this customer's. The row's revenue must be captured in a VAR before FILTER starts: inside FILTER the measure is evaluated for each iterated customer, so [Total Revenue] >= [Total Revenue] is true for everybody and every row shows 100%. ALLSELECTED keeps the slicer in the denominator; ALL(Shipment) would remove it (and leave the customer filter in place).`,
     oracle:(D,c)=>cumShare(D,c)},

    {id:'T12-03',level:'Pro',title:'ABC classification of customers',by:['Customer[CustomerName]'],checks:['slash','unqual','varRepeat'],
     slicer:[{col:'Shipment[Region]',vals:['Asia','Europe']}],
     prompt:`ABC class of each customer, as text. Customers are ranked by revenue (highest first) and the Pareto cumulative % (this customer plus all higher ones, as a share of the revenue the slicer leaves: Asia and Europe) decides the class: "A" when the cumulative % is 80% or less, "B" when it is 95% or less, otherwise "C". The total row stays BLANK.\nSteps:\n1) CustRev\n2) AllRev\n3) CumPct = revenue of customers with revenue >= CustRev, divided by AllRev\n4) SWITCH(TRUE(), ...) on CumPct.`,
     hint:`Same Pareto building blocks as the previous challenge, then RETURN IF(HASONEVALUE(...), SWITCH(TRUE(), CumPct <= 0.8, "A", CumPct <= 0.95, "B", "C")). SWITCH(TRUE(), ...) returns the first branch whose test is true, so test the smallest limit first.`,
     ref:`VAR CustRev = [Total Revenue]
VAR AllRev = CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName]))
VAR CumPct = DIVIDE(
    SUMX(FILTER(ALLSELECTED(Customer[CustomerName]), [Total Revenue] >= CustRev), [Total Revenue]),
    AllRev)
RETURN
    IF(
        HASONEVALUE(Customer[CustomerName]),
        SWITCH(TRUE(), CumPct <= 0.8, "A", CumPct <= 0.95, "B", "C")
    )`,
     alts:[{code:`VAR CustRev = [Total Revenue]
VAR AllRev = CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName]))
VAR CumRev = CALCULATE([Total Revenue], FILTER(ALLSELECTED(Customer[CustomerName]), [Total Revenue] >= CustRev))
VAR CumPct = DIVIDE(CumRev, AllRev)
RETURN IF(ISINSCOPE(Customer[CustomerName]), SWITCH(TRUE(), CumPct <= 0.8, "A", CumPct <= 0.95, "B", "C"))`}],
     wrongs:[{code:`VAR CustRev = [Total Revenue]
VAR AllRev = CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName]))
VAR CumPct = DIVIDE(SUMX(FILTER(ALLSELECTED(Customer[CustomerName]), [Total Revenue] > CustRev), [Total Revenue]), AllRev)
RETURN IF(HASONEVALUE(Customer[CustomerName]), SWITCH(TRUE(), CumPct <= 0.8, "A", CumPct <= 0.95, "B", "C"))`},
             {code:`VAR CustRev = [Total Revenue]
VAR AllRev = CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName]))
VAR OwnPct = DIVIDE(CustRev, AllRev)
RETURN IF(HASONEVALUE(Customer[CustomerName]), SWITCH(TRUE(), OwnPct <= 0.8, "A", OwnPct <= 0.95, "B", "C"))`},
             {code:`VAR CustRev = [Total Revenue]
VAR AllRev = CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName]))
VAR CumPct = DIVIDE(SUMX(FILTER(ALLSELECTED(Customer[CustomerName]), [Total Revenue] >= CustRev), [Total Revenue]), AllRev)
RETURN IF(HASONEVALUE(Customer[CustomerName]), SWITCH(TRUE(), CumPct <= 0.95, "B", CumPct <= 0.8, "A", "C"))`}],
     why:`The class depends on the CUMULATIVE share, not on the customer's own share (own shares are small, so everybody would be "A"). The cumulative figure includes the customer itself (>=); leaving it out lets the customer that crosses the 80% line stay in class A. SWITCH(TRUE(), ...) stops at the first true test, so the strictest limit (80%) must come first, otherwise "A" is never reached.`,
     oracle:(D,c)=>{const v=cumShare(D,c);if(v==null)return null;return v<=0.8?'A':(v<=0.95?'B':'C');}},

    {id:'T12-04',level:'Pro',title:'Budget vs actual with TREATAS',by:['Date[Year]','Shipment[Region]'],checks:['slash','unqual'],
     prompt:`Budget variance %: (actual revenue - budget) / budget, shown by year with the regions below it. The budget lives in the Target table (YearMonth, Region, TargetRevenue), which has no relationship, so TREATAS must carry the filters.\nSteps:\n1) Actual = revenue of the row\n2) Budget = SUM(Target[TargetRevenue]) for the months of the row (the row's Date[YearMonth] values) and the regions of the row (Shipment[Region] values)\n3) Variance = Actual - Budget\n4) return Variance / Budget, BLANK when there is no budget. The total row covers all months and regions.`,
     hint:`CALCULATE(SUM(Target[TargetRevenue]), TREATAS(VALUES(Date[YearMonth]), Target[YearMonth]), TREATAS(VALUES(Shipment[Region]), Target[Region])). The two TREATAS arguments narrow the Target table by month and by region.`,
     ref:`VAR Actual = [Total Revenue]
VAR Budget = CALCULATE(
    SUM(Target[TargetRevenue]),
    TREATAS(VALUES(Date[YearMonth]), Target[YearMonth]),
    TREATAS(VALUES(Shipment[Region]), Target[Region]))
VAR Variance = Actual - Budget
RETURN
    IF(NOT(ISBLANK(Budget)), DIVIDE(Variance, Budget))`,
     alts:[{code:`VAR Budget = CALCULATE(SUM(Target[TargetRevenue]), TREATAS(VALUES(Shipment[Region]), Target[Region]), TREATAS(VALUES(Date[YearMonth]), Target[YearMonth]))
RETURN IF(ISBLANK(Budget), BLANK(), DIVIDE([Total Revenue] - Budget, Budget))`}],
     wrongs:[{code:`VAR Actual = [Total Revenue]
VAR Budget = CALCULATE(SUM(Target[TargetRevenue]), TREATAS(VALUES(Date[YearMonth]), Target[YearMonth]))
RETURN IF(NOT(ISBLANK(Budget)), DIVIDE(Actual - Budget, Budget))`},
             {code:`VAR Actual = [Total Revenue]
VAR Budget = CALCULATE(SUM(Target[TargetRevenue]), TREATAS(VALUES(Date[YearMonth]), Target[YearMonth]), TREATAS(VALUES(Shipment[Region]), Target[Region]))
RETURN DIVIDE(Actual, Budget)`},
             {code:`VAR Actual = [Total Revenue]
VAR Budget = SUM(Target[TargetRevenue])
RETURN IF(NOT(ISBLANK(Budget)), DIVIDE(Actual - Budget, Budget))`}],
     why:`Target is not related to Date or Shipment, so a row's filters never reach it. TREATAS(VALUES(col), Target[col]) takes the values the row has on one side and applies them as a filter on the other, one column at a time. Leave out the Region TREATAS and every region row is compared with the budget of all regions; leave out both and the budget is the same all-time number everywhere. DIVIDE(Actual, Budget) is attainment (e.g. 1.05), not variance (0.05).`,
     oracle:(D,c)=>{
       const f=H.filters(c);
       const yms=new Set(D.Date.filter(d=>!f['Date[Year]']||f['Date[Year]'].includes(d.Year)).map(d=>d.YearMonth));
       const regs=new Set(H.vis(D,c).map(s=>s.Region));
       const bud=H.sumOrNull(D.Target.filter(t=>yms.has(t.YearMonth)&&regs.has(t.Region)),t=>t.TargetRevenue);
       if(bud==null)return null;
       const act=H.sum(H.vis(D,c),REV);
       return (act-bud)/bud;}},

    {id:'T12-05',level:'Pro',title:'New customers in the month',by:['Date[YearMonth]'],checks:['unqual'],
     prompt:`Number of NEW customers per month: customers whose very first shipment (over all time) falls inside the month of the row. The total row counts the customers whose first shipment is anywhere in the data (all of them).\nSteps:\n1) MonthFirst and MonthLast = first and last DateKey of the row\n2) for each customer, FirstShip = the earliest Shipment[DateKey] over all dates\n3) keep customers with FirstShip between MonthFirst and MonthLast\n4) count them.`,
     hint:`Inside FILTER(VALUES(Customer[CustomerName]), ...) use CALCULATE(MIN(Shipment[DateKey]), ALL(Date)): the customer comes from the row, ALL(Date) removes the month so MIN sees every shipment. Keep both sides int DateKeys (Date[DateKey]); do not compare an int with a Date.`,
     ref:`VAR MonthFirst = MIN(Date[DateKey])
VAR MonthLast = MAX(Date[DateKey])
VAR NewCustomers =
    FILTER(
        VALUES(Customer[CustomerName]),
        VAR FirstShip = CALCULATE(MIN(Shipment[DateKey]), ALL(Date))
        RETURN FirstShip >= MonthFirst && FirstShip <= MonthLast
    )
RETURN
    COUNTROWS(NewCustomers)`,
     alts:[{code:`VAR MonthFirst = MIN(Date[DateKey])
VAR MonthLast = MAX(Date[DateKey])
RETURN
    COUNTROWS(
        FILTER(
            VALUES(Customer[CustomerName]),
            CALCULATE(MIN(Shipment[DateKey]), REMOVEFILTERS(Date)) >= MonthFirst
                && CALCULATE(MIN(Shipment[DateKey]), REMOVEFILTERS(Date)) <= MonthLast
        )
    )`}],
     wrongs:[{code:`VAR MonthFirst = MIN(Date[DateKey])
VAR MonthLast = MAX(Date[DateKey])
RETURN COUNTROWS(FILTER(VALUES(Customer[CustomerName]), CALCULATE(MIN(Shipment[DateKey])) >= MonthFirst && CALCULATE(MIN(Shipment[DateKey])) <= MonthLast))`},
             {code:`VAR MonthFirst = MIN(Date[DateKey])
RETURN COUNTROWS(FILTER(VALUES(Customer[CustomerName]), CALCULATE(MIN(Shipment[DateKey]), ALL(Date)) >= MonthFirst))`},
             {code:`DISTINCTCOUNT(Shipment[CustomerKey])`}],
     why:`"New" means the customer's FIRST shipment ever is in this month. For each customer, ALL(Date) removes the month so MIN sees all of the customer's shipments. Without ALL(Date) the minimum is the first shipment inside the month, so every active customer looks new (that is "active customers"). Dropping the upper bound counts customers that start this month or ANY later month. The month bounds are stored in VARs first because inside the FILTER the month filter is removed again.`,
     oracle:(D,c)=>{const r=range(D,c);if(!r)return null;const first={};D.Shipment.forEach(s=>{if(first[s.CustomerKey]==null||s._n<first[s.CustomerKey])first[s.CustomerKey]=s._n;});return Object.values(first).filter(n=>n>=r.min&&n<=r.max).length;}},

    {id:'T12-06',level:'Pro',title:'3-month moving average, blank until 3 months exist',by:['Date[YearMonth]'],noTotal:true,checks:['slash','unqual','varRepeat'],
     prompt:`3-month moving average of monthly revenue: the revenue of the current month and the two months before it, divided by 3. The Date table starts in January 2024, so January and February 2024 do not have three months behind them and must show BLANK (not a smaller average). The grand total row is not graded.\nSteps:\n1) Last3M = the three-month window ending at the last date of the row\n2) MonthsInWindow = how many calendar months of the Date table fall in that window\n3) Revenue3M = revenue in the window\n4) BLANK unless MonthsInWindow = 3, otherwise Revenue3M / MonthsInWindow.`,
     hint:`DATESINPERIOD(Date[Date], MAX(Date[Date]), -3, MONTH) in a VAR; CALCULATE(DISTINCTCOUNT(Date[YearMonth]), Last3M) counts the months that really exist in it.`,
     ref:`VAR LastDate = MAX(Date[Date])
VAR Last3M = DATESINPERIOD(Date[Date], LastDate, -3, MONTH)
VAR MonthsInWindow = CALCULATE(DISTINCTCOUNT(Date[YearMonth]), Last3M)
VAR Revenue3M = CALCULATE([Total Revenue], Last3M)
RETURN
    IF(MonthsInWindow = 3, DIVIDE(Revenue3M, MonthsInWindow))`,
     alts:[{code:`VAR Last3M = DATESINPERIOD(Date[Date], MAX(Date[Date]), -3, MONTH)
VAR MonthsInWindow = CALCULATE(DISTINCTCOUNT(Date[YearMonth]), Last3M)
RETURN IF(MonthsInWindow = 3, CALCULATE(AVERAGEX(VALUES(Date[YearMonth]), [Total Revenue]), Last3M))`}],
     wrongs:[{code:`VAR Last3M = DATESINPERIOD(Date[Date], MAX(Date[Date]), -3, MONTH)
RETURN DIVIDE(CALCULATE([Total Revenue], Last3M), 3)`},
             {code:`VAR Last3M = DATESINPERIOD(Date[Date], MAX(Date[Date]), -3, MONTH)
VAR MonthsInWindow = CALCULATE(DISTINCTCOUNT(Date[YearMonth]), Last3M)
RETURN IF(MonthsInWindow = 3, CALCULATE(AVERAGE(Shipment[Revenue]), Last3M))`},
             {code:`VAR Last3M = DATESINPERIOD(Date[Date], MAX(Date[Date]), -3, MONTH)
RETURN CALCULATE([Total Revenue], Last3M)`}],
     why:`The window is the same DATESINPERIOD pattern as a rolling sum, but a moving average also needs to know whether the window is complete. Counting the calendar months inside the window tells you: in January 2024 the window runs before the start of the Date table, so only 1 month exists. Dividing by a fixed 3 would understate the first months, and AVERAGE(Shipment[Revenue]) averages shipments, not months.`,
     oracle:(D,c)=>{const r=range(D,c);if(!r)return null;const e=r.max;const lo=(e===H.eom(e)?H.eom(H.shiftMonths(e,-3)):H.shiftMonths(e,-3))+1;const months=new Set(D.Date.filter(d=>d._n>=lo&&d._n<=e).map(d=>d.YearMonth));if(months.size!==3)return null;const t=rev(D,c,lo,e);return t==null?null:t/3;}},

    {id:'T12-07',level:'Pro',title:'On-time % vs same month last year (points)',by:['Date[YearMonth]'],checks:['slash','unqual','hardcodedPeriod','varRepeat'],
     slicer:[{col:'Shipment[Mode]',vals:['Ocean','Road']}],
     prompt:`Change in on-time % versus the same period last year, in PERCENTAGE POINTS (a move from 70% to 75% shows 5, not 0.05 and not 7%). The slicer limits the report to Ocean and Road. Use the [On-Time %] measure.\nSteps:\n1) Now = on-time % of the row\n2) PY = on-time % of the same period one year earlier\n3) BLANK when either is blank (the whole first year)\n4) otherwise (Now - PY) * 100. The total row compares the whole period with the period a year earlier.`,
     hint:`VAR PY = CALCULATE([On-Time %], SAMEPERIODLASTYEAR(Date[Date])). Test both VARs with ISBLANK before subtracting, because BLANK - number is not BLANK in DAX.`,
     ref:`VAR Now = [On-Time %]
VAR PY = CALCULATE([On-Time %], SAMEPERIODLASTYEAR(Date[Date]))
RETURN
    IF(NOT(ISBLANK(Now)) && NOT(ISBLANK(PY)), (Now - PY) * 100)`,
     alts:[{code:`VAR Now = [On-Time %]
VAR PY = CALCULATE([On-Time %], DATEADD(Date[Date], -1, YEAR))
RETURN IF(ISBLANK(Now) || ISBLANK(PY), BLANK(), 100 * (Now - PY))`}],
     wrongs:[{code:`VAR Now = [On-Time %]
VAR PY = CALCULATE([On-Time %], SAMEPERIODLASTYEAR(Date[Date]))
RETURN (Now - PY) * 100`},
             {code:`VAR Now = [On-Time %]
VAR PY = CALCULATE([On-Time %], SAMEPERIODLASTYEAR(Date[Date]))
RETURN IF(NOT(ISBLANK(PY)), Now - PY)`},
             {code:`VAR Now = [On-Time %]
VAR PY = CALCULATE([On-Time %], SAMEPERIODLASTYEAR(Date[Date]))
RETURN IF(NOT(ISBLANK(PY)), DIVIDE(Now, PY) - 1)`}],
     why:`Two percentages are compared by subtracting them: the result is in percentage points (multiply the fraction by 100 to read it as points). A relative change DIVIDE(Now, PY) - 1 is a different statement (7% better, not 5 points better). In the first year PY is BLANK and BLANK counts as 0 in a subtraction, so without the check every month would show its own on-time % as the "change".`,
     oracle:(D,c)=>{const r=range(D,c);if(!r)return null;const p=shifted(r,-12);const ot=rows=>rows.length?H.sum(rows,s=>s.IsOnTime)/rows.length:null;const now=ot(H.vis(D,c));const py=ot(H.vis(D,c,{drop:['Date'],from:p.min,to:p.max}));if(now==null||py==null)return null;return (now-py)*100;}},

    {id:'T12-08',level:'Pro',title:'Revenue bridge: price effect vs last year',by:['Date[YearMonth]'],noTotal:true,checks:['slash','unqual','varRepeat'],
     prompt:`Revenue bridge, price effect: how much of the revenue change versus the same month last year comes from a different average revenue per shipment (price/mix), holding the number of shipments at this year's level. Price effect = (AvgNow - AvgPY) * ShipmentsNow, where Avg = revenue / shipments.\nSteps:\n1) RevNow and CntNow\n2) RevPY and CntPY for the same period one year earlier\n3) AvgNow and AvgPY\n4) BLANK when there is no prior-year shipment, otherwise the price effect. The grand total row is not graded.`,
     hint:`Compute the prior-year dates once: VAR PYDates = SAMEPERIODLASTYEAR(Date[Date]), then CALCULATE([Total Revenue], PYDates) and CALCULATE([Shipments], PYDates). Check your work by returning the volume effect (CntNow - CntPY) * AvgPY too: volume + price = RevNow - RevPY.`,
     ref:`VAR RevNow = [Total Revenue]
VAR CntNow = [Shipments]
VAR PYDates = SAMEPERIODLASTYEAR(Date[Date])
VAR RevPY = CALCULATE([Total Revenue], PYDates)
VAR CntPY = CALCULATE([Shipments], PYDates)
VAR AvgNow = DIVIDE(RevNow, CntNow)
VAR AvgPY = DIVIDE(RevPY, CntPY)
RETURN
    IF(NOT ISBLANK(CntPY), (AvgNow - AvgPY) * CntNow)`,
     alts:[{code:`VAR CntNow = [Shipments]
VAR AvgNow = DIVIDE([Total Revenue], CntNow)
VAR AvgPY = CALCULATE(DIVIDE([Total Revenue], [Shipments]), SAMEPERIODLASTYEAR(Date[Date]))
RETURN IF(NOT(ISBLANK(AvgPY)), (AvgNow - AvgPY) * CntNow)`}],
     wrongs:[{code:`VAR RevNow = [Total Revenue]
VAR CntNow = [Shipments]
VAR PYDates = SAMEPERIODLASTYEAR(Date[Date])
VAR RevPY = CALCULATE([Total Revenue], PYDates)
VAR CntPY = CALCULATE([Shipments], PYDates)
VAR AvgNow = DIVIDE(RevNow, CntNow)
VAR AvgPY = DIVIDE(RevPY, CntPY)
RETURN IF(CntPY > 0, (AvgNow - AvgPY) * CntPY)`},
             {code:`VAR RevNow = [Total Revenue]
VAR CntNow = [Shipments]
VAR PYDates = SAMEPERIODLASTYEAR(Date[Date])
VAR RevPY = CALCULATE([Total Revenue], PYDates)
VAR CntPY = CALCULATE([Shipments], PYDates)
VAR AvgNow = DIVIDE(RevNow, CntNow)
VAR AvgPY = DIVIDE(RevPY, CntPY)
RETURN (AvgNow - AvgPY) * CntNow`},
             {code:`VAR RevNow = [Total Revenue]
VAR CntNow = [Shipments]
VAR PYDates = SAMEPERIODLASTYEAR(Date[Date])
VAR RevPY = CALCULATE([Total Revenue], PYDates)
VAR CntPY = CALCULATE([Shipments], PYDates)
VAR AvgPY = DIVIDE(RevPY, CntPY)
RETURN IF(CntPY > 0, (CntNow - CntPY) * AvgPY)`}],
     why:`Revenue = shipments x average revenue per shipment, so the change splits exactly in two: volume effect (CntNow - CntPY) * AvgPY plus price effect (AvgNow - AvgPY) * CntNow add up to RevNow - RevPY. Multiplying the price difference by this year's count (not last year's) is what makes the two parts add up with no remainder. The prior-year date table is built once in a VAR and reused by both CALCULATEs. In the first year there is no prior year, so a BLANK check keeps the price effect from becoming the whole revenue.`,
     oracle:(D,c)=>{const r=range(D,c);if(!r)return null;const p=shifted(r,-12);const nowRows=H.vis(D,c);const pyRows=H.vis(D,c,{drop:['Date'],from:p.min,to:p.max});if(!pyRows.length)return null;if(!nowRows.length)return null;const an=H.sum(nowRows,REV)/nowRows.length,ap=H.sum(pyRows,REV)/pyRows.length;return (an-ap)*nowRows.length;}}
  ]
});
})();
