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
  challenges:[]
});
