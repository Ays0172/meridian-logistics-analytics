"use strict";
/* Topic 12 - Capstone: long, multi-step measures. Stub: add challenges (see AUTHORING.md). */
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
  challenges:[]
});
