"use strict";
/* Topic 5 - Removing filters. */
registerTopic({
  id:'T05',title:'Removing filters',order:5,
  concept:[
    'To compare a row with a total you must remove filters inside CALCULATE. `ALL(Shipment[Mode])` (or `REMOVEFILTERS`) clears one column, `ALL(Shipment)` clears the whole table, `ALLEXCEPT(Customer, Customer[Country])` clears everything on the table except the listed columns. `ALLSELECTED` clears only the visual\'s own row filters but keeps the report slicers, so it gives "% of what the user selected".',
    '',
    '  % of All Modes = DIVIDE([Total Revenue], CALCULATE([Total Revenue], ALL(Shipment[Mode])))',
    '  % of Visible = DIVIDE([Total Revenue], CALCULATE([Total Revenue], ALLSELECTED(Shipment[Mode])))',
    '',
    'Remove only what the question needs: ALL(Shipment) is often more than you want.'
  ].join('\n'),
  challenges:[
    {id:'T05-01',v1:'i5',level:'Intermediate',title:'Revenue Share of All Modes',by:['Shipment[Mode]'],checks:['slash','unqual','allTable'],
     prompt:'Each Mode\'s revenue as a share of the revenue of ALL modes. In a Mode row the denominator must ignore the Mode filter.',
     hint:'The denominator needs CALCULATE(SUM(...), ALL(Shipment[Mode])) to remove only the Mode filter.',
     ref:'DIVIDE(SUM(Shipment[Revenue]), CALCULATE(SUM(Shipment[Revenue]), ALL(Shipment[Mode])))',
     alts:[{code:'DIVIDE(SUM(Shipment[Revenue]), CALCULATE(SUM(Shipment[Revenue]), REMOVEFILTERS(Shipment[Mode])))'},
           {code:'DIVIDE([Total Revenue], CALCULATE([Total Revenue], ALL(Shipment[Mode])))'},
           {code:'DIVIDE(SUM(Shipment[Revenue]), CALCULATE(SUM(Shipment[Revenue]), ALL(Shipment)))',warn:'allTable'},
           {code:'SUM(Shipment[Revenue]) / CALCULATE(SUM(Shipment[Revenue]), ALL(Shipment[Mode]))',warn:'slash'}],
     wrongs:[{code:'DIVIDE(SUM(Shipment[Revenue]), SUM(Shipment[Revenue]))'},
             {code:'DIVIDE(SUM(Shipment[Revenue]), CALCULATE(SUM(Shipment[Revenue]), Shipment[Mode] = "Ocean"))'}],
     why:'ALL(Shipment[Mode]) removes the Mode filter from the denominator only, so each row is divided by the grand total.',
     oracle:(D,c)=>{const num=H.sumOrNull(H.vis(D,c),s=>s.Revenue);const den=H.sumOrNull(H.vis(D,c,{drop:['Shipment[Mode]']}),s=>s.Revenue);return H.div(num,den);}},
    {id:'T05-02',v1:'p4',level:'Pro',title:'Revenue per Shipment vs Overall',by:['Shipment[Mode]'],checks:['slash','unqual'],
     prompt:'Average revenue per shipment in the current selection minus the average revenue per shipment across ALL shipments. Use VAR / RETURN.',
     hint:'VAR CurrentAvg = AVERAGE(...)  VAR OverallAvg = CALCULATE(AVERAGE(...), ALL(Shipment))  RETURN CurrentAvg - OverallAvg',
     ref:'VAR CurrentAvg = AVERAGE(Shipment[Revenue])\nVAR OverallAvg = CALCULATE(AVERAGE(Shipment[Revenue]), ALL(Shipment))\nRETURN CurrentAvg - OverallAvg',
     alts:[{code:'AVERAGE(Shipment[Revenue]) - CALCULATE(AVERAGE(Shipment[Revenue]), ALL(Shipment))'}],
     wrongs:[{code:'AVERAGE(Shipment[Revenue])'},
             {code:'VAR CurrentAvg = AVERAGE(Shipment[Revenue])\nVAR OverallAvg = AVERAGE(Shipment[Revenue])\nRETURN CurrentAvg - OverallAvg'}],
     why:'VAR values are fixed where they are defined. OverallAvg needs ALL(Shipment) to ignore the current Mode; without it both VARs are the same number and the difference is always 0.',
     oracle:(D,c)=>{const cur=H.vis(D,c),all=H.vis(D,c,{drop:['Shipment']});if(!cur.length||!all.length)return null;return H.sum(cur,s=>s.Revenue)/cur.length-H.sum(all,s=>s.Revenue)/all.length;}}
  ]
});
