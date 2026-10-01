"use strict";
/* =====================================================================
   selftest.js - run with  dax_trainer.html?selftest&seed=N
   Options:  &topic=T05   only check the challenges of that topic (engine unit tests are skipped)
             &engine=1    also run the engine unit tests together with &topic=
   Result:   window.__selftest = {ok, pass, total, lines}; console lines start with PASS / FAIL / SELFTEST.
   ===================================================================== */

/* A tiny hand-made dataset: every expected value in the engine unit tests was computed by hand from it. */
function tinyData(){
  const dk=(y,m,d)=>y*10000+m*100+d;
  const S=(id,c,mode,reg,rev,cost,ffe,wt,ot,d,dd)=>({ShipmentID:id,CustomerKey:c,Mode:mode,Region:reg,Revenue:rev,Cost:cost,Ffe:ffe,Weight:wt,IsOnTime:ot,DateKey:d,DeliveryDateKey:dd});
  const D={seed:0,
    Customer:[
      {CustomerKey:1,CustomerName:'Alpha',Segment:'Key',Country:'Germany',AccountManager:'Ana'},
      {CustomerKey:2,CustomerName:'Beta',Segment:'Standard',Country:'Germany',AccountManager:'Ana'},
      {CustomerKey:3,CustomerName:'Gamma',Segment:'Standard',Country:'USA',AccountManager:'Bob'},
      {CustomerKey:4,CustomerName:'Delta',Segment:'Key',Country:'USA',AccountManager:'Bob'}],
    Shipment:[
      S(1,1,'Ocean','Asia',100,60,2,10,1,dk(2024,2,29),dk(2024,3,10)),
      S(2,2,'Ocean','Asia',100,70,1,10,0,dk(2024,3,31),dk(2024,4,5)),
      S(3,3,'Air','Europe',50,30,0,10,1,dk(2024,9,30),dk(2024,10,2)),
      S(4,4,'Road','Europe',30,20,1,10,1,dk(2024,10,1),dk(2024,10,5)),
      S(5,1,'Ocean','Asia',40,25,1,10,0,dk(2025,2,28),dk(2025,3,2)),
      S(6,2,'Air','Americas',60,40,0,10,1,dk(2025,3,15),dk(2025,3,20)),
      S(7,3,'Ocean','Americas',70,50,3,10,1,dk(2025,10,1),dk(2025,10,9)),
      S(8,1,'Road','Europe',20,10,1,10,1,dk(2025,9,30),dk(2025,10,2))],
    Date:buildDateRows(epochDay(2023,1,1),LAST_N),
    Target:[{YearMonth:'2024-03',Region:'Asia',TargetRevenue:120},{YearMonth:'2024-03',Region:'Europe',TargetRevenue:10},{YearMonth:'2025-03',Region:'Americas',TargetRevenue:55}]};
  return finalizeData(D);
}

function runSelfTest(seed,opts){
  opts=opts||{};
  const lines=[];let pass=0,total=0;
  const log=(ok,msg)=>{total++;if(ok)pass++;const l=(ok?'PASS ':'FAIL ')+msg;lines.push(l);console.log(l);};
  const short=s=>String(s).replace(/\s+/g,' ').slice(0,90);

  /* ---- 1. registry validation ---- */
  REG_ERRORS.forEach(e=>log(false,'registry '+e));
  log(REG_ERRORS.length===0,'registry: '+TOPICS.length+' topics, '+allChallenges().length+' challenges registered, no validation errors');
  if(opts.topic&&!TOPICS.some(t=>t.id===opts.topic))log(false,'unknown topic '+opts.topic);

  /* ---- 2. every challenge against its oracle ---- */
  const D=generateData(seed);DB=D;const P=D.params;
  console.log('seed='+seed+' attempt='+D.attempt+' params='+JSON.stringify(P));
  const topics=TOPICS.filter(t=>!opts.topic||t.id===opts.topic);
  let nCh=0;
  const evalAll=(code,ctxs)=>ctxs.map(c=>{try{return {v:evalIn(code,c)};}catch(e){if(e instanceof DaxError)return {err:e};throw e;}});
  const fmtv=v=>v===undefined?'undefined':fmt(v);
  for(const t of topics){
    for(const ch of t.challenges){
      nCh++;
      let ctxs,orc;
      try{
        ctxs=contextsFor(ch);
        orc=ctxs.map(c=>ch.oracle(D,c.oracleCtx));
      }catch(e){log(false,'oracle '+ch.id+' threw '+e.message);continue;}
      const tol=ch.tolerance||1e-6;
      const cmp=(code)=>{
        const got=evalAll(code,ctxs);let err=null,bad=[],diff=[];
        got.forEach((g,i)=>{
          if(g.err){err=err||g.err;return;}
          if(orc[i]===undefined){bad.push(i);return;}
          if(!sameVal(g.v,orc[i],tol))diff.push(i);
        });
        return {err:err,diff:diff,undef:bad,got:got};
      };
      const why=(r)=>r.err?' -> error '+r.err.message:(r.undef.length?' -> oracle returned undefined for '+ctxs[r.undef[0]].label:(r.diff.length?' -> differs from oracle at ['+ctxs[r.diff[0]].label+'] got '+fmtv(r.got[r.diff[0]].v)+' oracle '+fmtv(orc[r.diff[0]]):''));
      // oracle sanity: not all blank
      log(orc.some(v=>v!=null),'oracle '+ch.id+' '+ch.title+' returns a value in at least one of '+ctxs.length+' contexts');
      log(orc.length<=60,'rows '+ch.id+' has '+ctxs.length+' contexts (keep a grid at <= 60 rows)');
      const ref=chRef(ch,P);
      let r=cmp(ref);
      log(!r.err&&!r.diff.length&&!r.undef.length,'ref   '+ch.id+' '+ch.title+why(r));
      const g=grade(ch,ref,P);
      log(g.status==='ok','grade '+ch.id+' accepts its own ref');
      const unqualRef=runChecks(ch,parseCached(ref)).filter(w=>w.kind==='warn'&&!(ch.refWarns||[]).includes(w.rule));
      log(unqualRef.length===0,'ref   '+ch.id+' triggers no warning rule'+(unqualRef.length?' ('+unqualRef.map(w=>w.rule).join(',')+')':''));
      for(const a of chAlts(ch,P)){
        r=cmp(a.code);let ok=!r.err&&!r.diff.length&&!r.undef.length;
        let wmsg='';
        if(ok&&a.warn){ok=runChecks(ch,parseCached(a.code)).some(w=>w.rule===a.warn);if(!ok)wmsg=' -> expected warning '+a.warn+' not raised';}
        log(ok,'alt   '+ch.id+' '+(a.warn?'[expects warn '+a.warn+'] ':'')+short(a.code)+(ok?'':why(r)+wmsg));
      }
      for(const w of chWrongs(ch,P)){
        r=cmp(w.code);
        let ok=!r.err&&r.diff.length>0;
        let wmsg='';
        if(ok&&w.warn){ok=runChecks(ch,parseCached(w.code)).some(x=>x.rule===w.warn);if(!ok)wmsg=' -> expected warning '+w.warn+' not raised';}
        log(ok,'wrong '+ch.id+' '+(w.warn?'[expects warn '+w.warn+'] ':'')+short(w.code)+(ok?'':(r.err?' -> error '+r.err.message:(r.diff.length?wmsg:' -> equals the oracle in every context'))));
      }
    }
  }
  log(true,'checked '+nCh+' challenges in '+topics.length+' topic(s)');

  if(!opts.topic||opts.engine){
    engineTests(D,log);
    tinyTests(log);
  }

  const out=(pass===total?'SELFTEST PASS ':'SELFTEST FAIL ')+pass+'/'+total+' (seed '+seed+(opts.topic?', topic '+opts.topic:'')+')';
  lines.push(out);console.log(out);
  window.__selftest={pass:pass,total:total,lines:lines,ok:pass===total};
  return lines;
}

/* ---- 3. engine tests on the seeded dataset (independent JS computations) ---- */
function engineTests(D,log){
  DB=D;
  const S=D.Shipment,C=D.Customer;
  const sum=(a,f)=>a.reduce((x,s)=>x+f(s),0);
  const eq=(a,b)=>a===b||(a==null&&b==null)||(typeof a==='number'&&typeof b==='number'&&Math.abs(a-b)<1e-9*Math.max(1,Math.abs(b)));
  const T=(name,code,expected,rc)=>{
    let got,ok;
    try{got=evalMeasure(code,rc);ok=eq(got,expected);}catch(e){got='ERR '+e.message;ok=false;}
    log(ok,'engine '+name+' got='+(typeof got==='number'?got:JSON.stringify(got))+' expected='+JSON.stringify(expected));
  };
  const TE=(name,code,frag)=>{
    let msg='(no error)';try{evalMeasure(code);}catch(e){msg=e.message;}
    log(msg.toLowerCase().includes(frag.toLowerCase()),'engine error: '+name+' -> '+msg.slice(0,90));
  };
  const rowF=(col,v)=>({rowFilters:[{col:col,vals:[v]}]});
  const totalRev=sum(S,s=>s.Revenue);
  T('date year filter propagates','CALCULATE(SUM(Shipment[Revenue]), Date[Year] = 2026)',sum(S.filter(s=>s._d.Year===2026),s=>s.Revenue));
  T('date year+month (two filters)','CALCULATE(COUNTROWS(Shipment), Date[Year] = 2025, Date[MonthNo] <= 6)',S.filter(s=>s._d.Year===2025&&s._d.MonthNo<=6).length);
  T('context transition over Customer rows','SUMX(Customer, CALCULATE(SUM(Shipment[Revenue])))',totalRev);
  T('no transition without CALCULATE','SUMX(Customer, SUM(Shipment[Revenue]))',totalRev*C.length);
  T('transition over VALUES(col)','SUMX(VALUES(Shipment[Mode]), CALCULATE(SUM(Shipment[Revenue])))',totalRev);
  T('transition per Shipment row','SUMX(Shipment, CALCULATE(COUNTROWS(Shipment)))',S.length);
  T('ALL(Shipment) under Mode filter','CALCULATE(SUM(Shipment[Revenue]), ALL(Shipment))',totalRev,[{col:'Shipment[Mode]',vals:['Ocean']}]);
  T('ALL(col) removes only that column','CALCULATE(SUM(Shipment[Revenue]), ALL(Shipment[Mode]))',sum(S.filter(s=>s.Region==='Asia'),s=>s.Revenue),[{col:'Shipment[Mode]',vals:['Ocean']},{col:'Shipment[Region]',vals:['Asia']}]);
  T('boolean filter replaces column filter','CALCULATE(SUM(Shipment[Revenue]), Shipment[Mode] = "Air")',sum(S.filter(s=>s.Mode==='Air'),s=>s.Revenue),[{col:'Shipment[Mode]',vals:['Ocean']}]);
  T('KEEPFILTERS intersects (disjoint -> blank)','CALCULATE(SUM(Shipment[Revenue]), KEEPFILTERS(Shipment[Mode] = "Air"))',null,[{col:'Shipment[Mode]',vals:['Ocean']}]);
  T('KEEPFILTERS intersects (overlap)','CALCULATE(COUNTROWS(Shipment), KEEPFILTERS(Shipment[Mode] IN {"Ocean","Air"}))',S.filter(s=>s.Mode==='Ocean').length,[{col:'Shipment[Mode]',vals:['Ocean']}]);
  T('two filters on one column intersect','CALCULATE(COUNTROWS(Shipment), Shipment[Revenue] > 2000, Shipment[Revenue] < 5000)',S.filter(s=>s.Revenue>2000&&s.Revenue<5000).length);
  T('&& splits into separate column filters','CALCULATE(COUNTROWS(Shipment), Shipment[Mode] = "Ocean" && Shipment[Region] = "Asia")',S.filter(s=>s.Mode==='Ocean'&&s.Region==='Asia').length);
  T('IN list filter','CALCULATE(COUNTROWS(Shipment), Shipment[Mode] IN {"Ocean","Road"})',S.filter(s=>s.Mode!=='Air').length);
  T('Customer filter propagates to Shipment','CALCULATE(COUNTROWS(Shipment), Customer[Segment] = "Key")',S.filter(s=>s._c.Segment==='Key').length);
  T('Shipment filter does not filter Customer','COUNTROWS(Customer)',C.length,[{col:'Shipment[Mode]',vals:['Air']}]);
  T('VALUES reflects Shipment filter',"COUNTROWS(VALUES(Shipment[CustomerKey]))",new Set(S.filter(s=>s.Mode==='Air').map(s=>s.CustomerKey)).size,[{col:'Shipment[Mode]',vals:['Air']}]);
  T('FILTER(ALL(col)) as CALCULATE filter','CALCULATE(COUNTROWS(Shipment), FILTER(ALL(Shipment[Mode]), Shipment[Mode] <> "Air"))',S.filter(s=>s.Mode!=='Air').length);
  T('RELATED in iterator','SUMX(Shipment, IF(RELATED(Customer[Segment]) = "Key", Shipment[Revenue], 0))',sum(S.filter(s=>s._c.Segment==='Key'),s=>s.Revenue));
  T('case-insensitive text compare','CALCULATE(COUNTROWS(Shipment), Shipment[Mode] = "oCeAn")',S.filter(s=>s.Mode==='Ocean').length);
  T('measure-name prefix is stripped','Total Revenue = SUM(Shipment[Revenue])',totalRev);
  T('measure-name prefix with % and -','On-Time % = SUM(Shipment[Revenue])',totalRev);
  T('VAR / RETURN','VAR a = SUM(Shipment[Revenue])\nVAR b = COUNTROWS(Shipment)\nRETURN DIVIDE(a, b)',totalRev/S.length);
  T('VAR is not re-evaluated by CALCULATE','VAR a = SUM(Shipment[Revenue]) RETURN CALCULATE(a, Shipment[Mode] = "Air")',totalRev);
  T('comments are ignored','// c1\nSUM(Shipment[Revenue]) -- c2\n/* c3 */',totalRev);
  T('DIVIDE by zero is blank','DIVIDE(1, 0)',null);
  T('DIVIDE alternate result','DIVIDE(1, 0, -1)',-1);
  T('/ by zero is Infinity','1 / 0',Infinity);
  T('MAXX / MINX over rows','MAXX(Shipment, Shipment[Revenue]) - MINX(Shipment, Shipment[Revenue])',Math.max(...S.map(s=>s.Revenue))-Math.min(...S.map(s=>s.Revenue)));
  T('SUM of no rows is blank','CALCULATE(SUM(Shipment[Revenue]), Shipment[Mode] = "Nope")',null);
  T('library measure ref','[Total Revenue]',totalRev);
  T('library measure chain ([Profit])','[Profit]',sum(S,s=>s.Revenue-s.Cost));
  T('measure ref transitions inside SUMX','SUMX(Customer, [Total Revenue])',totalRev);
  T('measure ref in CALCULATE filter context','CALCULATE([Total Revenue], Shipment[Mode] = "Air")',sum(S.filter(s=>s.Mode==='Air'),s=>s.Revenue));
  T('Weight column exists','SUM(Shipment[Weight])',sum(S,s=>s.Weight));
  T('Date[Date] MAX is a date','MAX(Date[Date]) = DATE(2026,12,31)',true);
  T('DeliveryDate relationship is inactive by default','CALCULATE(COUNTROWS(Shipment), Date[Year] = 2026)',S.filter(s=>s._d.Year===2026).length);
  T('scalar VAR in a True/False filter','VAR T = 5000 RETURN CALCULATE([Total Revenue], Shipment[Revenue] > T)',sum(S.filter(s=>s.Revenue>5000),s=>s.Revenue));
  T('scalar expression in a True/False filter','VAR T = 2500 RETURN CALCULATE(COUNTROWS(Shipment), Shipment[Revenue] > T * 2, Shipment[Revenue] <= IF(T > 0, 3 * T, 0))',S.filter(s=>s.Revenue>5000&&s.Revenue<=7500).length);
  T('VAR holding an aggregate in a filter','VAR A = AVERAGE(Shipment[Revenue]) RETURN CALCULATE(COUNTROWS(Shipment), Shipment[Revenue] > A)',S.filter(s=>s.Revenue>totalRev/S.length).length);
  T('row-context VAR in a filter','SUMX(Customer, VAR k = Customer[CustomerKey] RETURN CALCULATE(COUNTROWS(Shipment), Shipment[CustomerKey] = k))',S.length);
  T('NOT as a prefix operator','CALCULATE(COUNTROWS(Shipment), NOT Shipment[Mode] = "Air")',S.filter(s=>s.Mode!=='Air').length);
  T('NOT prefix binds looser than comparison','IF(NOT 1 > 2, "y", "n")','y');
  T('NOT prefix on a function call','IF(NOT ISBLANK(CALCULATE(SUM(Shipment[Revenue]), Shipment[Mode] = "Nope")), 1, 2)',2);
  T('NOT(x) call form still works','IF(NOT(1 > 2) && NOT(ISBLANK(1)), 1, 0)',1);
  T('COUNTROWS of an empty table is blank','CALCULATE(COUNTROWS(Shipment), Shipment[Mode] = "Nope")',null);
  T('COUNTROWS(FILTER) with no match is blank','COUNTROWS(FILTER(Shipment, Shipment[Revenue] < 0))',null);
  T('COUNT of no rows is blank','CALCULATE(COUNT(Shipment[Revenue]), Shipment[Mode] = "Nope")',null);
  T('DISTINCTCOUNT of no rows is blank','CALCULATE(DISTINCTCOUNT(Shipment[CustomerKey]), Shipment[Mode] = "Nope")',null);
  T('blank COUNTROWS + 0 stays numeric','CALCULATE(COUNTROWS(Shipment), Shipment[Mode] = "Nope") + 0',0);
  T('blank COUNTROWS equals 0','CALCULATE(COUNTROWS(Shipment), Shipment[Mode] = "Nope") = 0',true);
  TE('aggregation of another column in a filter stays rejected','CALCULATE(COUNTROWS(Shipment), Shipment[Revenue] > AVERAGE(Shipment[Cost]))','VAR');
  TE('naked column','Shipment[Revenue]','aggregation');
  TE('unknown function','SUMM(Shipment[Revenue])','Did you mean SUM');
  TE('unknown column','SUM(Shipment[Revenu])','Did you mean Shipment[Revenue]');
  TE('unknown table','SUM(Shipments[Revenue])','Did you mean Shipment');
  TE('unbalanced paren','SUM(Shipment[Revenue]',"Missing ')'");
  TE('extra paren','SUM(Shipment[Revenue]))','no matching');
  TE('unqualified column','SUM([Revenue])','Shipment[Revenue]');
  TE('SUM of a measure','SUM([Total Revenue])','SUMX');
  TE('RELATED outside row context','RELATED(Customer[Segment])','row context');
  TE('== is rejected','CALCULATE(SUM(Shipment[Revenue]), Shipment[Mode] == "Air")','single =');
  TE('function in boolean filter','CALCULATE(SUM(Shipment[Revenue]), Shipment[Revenue] > AVERAGE(Shipment[Revenue]))','FILTER');
  TE('measure in boolean filter','CALCULATE(SUM(Shipment[Revenue]), Shipment[Revenue] > [Total Cost])','VAR');
  TE('DateKey int vs Date value','COUNTROWS(FILTER(Shipment, Shipment[DateKey] <= DATE(2025,1,31)))','whole number');
  TE('DateKey int vs MAX(Date[Date])','COUNTROWS(FILTER(Shipment, Shipment[DateKey] <= MAX(Date[Date])))','whole number');
  TE('time intelligence on Shipment[DateKey]','CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Shipment[DateKey]))','need Date[Date]');
  TE('time intelligence on Date[DateKey]','CALCULATE([Total Revenue], DATESYTD(Date[DateKey]))','Date[Date]');
  TE('USERELATIONSHIP outside CALCULATE','USERELATIONSHIP(Shipment[DeliveryDateKey], Date[DateKey])','inside CALCULATE');
  TE('no such relationship','CALCULATE([Total Revenue], USERELATIONSHIP(Shipment[Mode], Date[DateKey]))','no relationship');
  TE('ALLEXCEPT outside CALCULATE','ALLEXCEPT(Customer, Customer[Country])','CALCULATE');
  {let msg='(no error)';try{evalMeasure('CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Date[Date]))',{rowFilters:[{col:'Date[Year]',vals:[2024,2026]}]});}catch(e){msg=e.message;}
   log(msg.includes('contiguous'),'engine error: SAMEPERIODLASTYEAR needs contiguous dates -> '+msg.slice(0,80));}
  T('SPLY of a 2024 month is outside the date table -> blank','CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Date[Date]))',null,[{col:'Date[YearMonth]',vals:['2024-03']}]);
}

/* ---- 4. engine unit tests with hand-computed values (tiny dataset) ---- */
function tinyTests(log){
  const keep=DB;
  const tiny=tinyData();DB=tiny;
  const T=(name,code,expected,rc)=>{
    let got,ok;
    try{got=evalMeasure(code,rc);ok=got===expected||(typeof got==='number'&&typeof expected==='number'&&Math.abs(got-expected)<1e-9)||(got==null&&expected==null);}
    catch(e){got='ERR '+e.message;ok=false;}
    log(ok,'unit '+name+' got='+(typeof got==='number'?got:JSON.stringify(got))+' expected='+JSON.stringify(expected));
  };
  const rf=(col,v)=>({rowFilters:[{col:col,vals:[v]}]});
  const NAME='Customer[CustomerName]',YM='Date[YearMonth]',DK='Date[DateKey]';
  const REV='[Total Revenue]';
  // hand-computed: revenue by customer Alpha 160, Beta 160, Gamma 120, Delta 30; total 470
  T('library total revenue',REV,470);
  // RANKX ties
  const rkV=(who,ties,order,exp)=>T('RANKX '+(ties||'SKIP')+' '+(order||'DESC')+' '+who,'RANKX(ALL(Customer[CustomerName]), [Total Revenue], , '+(order||'DESC')+(ties?', '+ties:'')+')',exp,rf(NAME,who));
  rkV('Alpha',null,null,1);rkV('Beta',null,null,1);rkV('Gamma',null,null,3);rkV('Delta',null,null,4);
  rkV('Alpha','DENSE',null,1);rkV('Gamma','DENSE',null,2);rkV('Delta','DENSE',null,3);
  rkV('Gamma',null,'ASC',2);rkV('Delta',null,'ASC',1);rkV('Alpha',null,'ASC',3);rkV('Alpha','DENSE','ASC',3);
  T('RANKX at the grand total (value larger than any row) = 1','RANKX(ALL(Customer[CustomerName]), [Total Revenue])',1);
  T('RANKX with SUM (no transition) ties everyone at 1','RANKX(ALL(Customer[CustomerName]), SUM(Shipment[Revenue]))',1,rf(NAME,'Gamma'));
  // TOPN
  T('TOPN keeps ties at the cut-off (n=1 -> 2 rows)','COUNTROWS(TOPN(1, ALL(Customer), [Total Revenue]))',2);
  T('TOPN n=2 -> exactly the two tied rows','COUNTROWS(TOPN(2, ALL(Customer), [Total Revenue]))',2);
  T('TOPN n=3 -> 3 rows, sum 440','SUMX(TOPN(3, ALL(Customer), [Total Revenue]), [Total Revenue])',440);
  T('TOPN ASC n=2 -> Delta + Gamma = 150','SUMX(TOPN(2, ALL(Customer), [Total Revenue], ASC), [Total Revenue])',150);
  T('TOPN as CALCULATE filter (one column)','CALCULATE([Total Revenue], TOPN(3, ALL(Customer[CustomerName]), [Total Revenue]))',440);
  T('TOPN n=0 is empty','COUNTROWS(TOPN(0, ALL(Customer), [Total Revenue]))',null);
  // DATEADD / month ends
  T('DATEADD -1 MONTH of Mar 2024 = Feb 2024 (29 days)','COUNTROWS(DATEADD(Date[Date], -1, MONTH))',29,rf(YM,'2024-03'));
  T('DATEADD -1 MONTH of Mar 2025 = Feb 2025 (28 days)','COUNTROWS(DATEADD(Date[Date], -1, MONTH))',28,rf(YM,'2025-03'));
  T('DATEADD +1 MONTH of Feb 2024 = whole of Mar (31 days)','COUNTROWS(DATEADD(Date[Date], 1, MONTH))',31,rf(YM,'2024-02'));
  T('DATEADD -1 MONTH of the single day 31 Mar 2024 = 29 Feb (ship 1, revenue 100)','CALCULATE([Total Revenue], DATEADD(Date[Date], -1, MONTH))',100,rf(DK,20240331));
  T('DATEADD +1 YEAR of 29 Feb 2024 = 28 Feb 2025 (ship 5, revenue 40)','CALCULATE([Total Revenue], DATEADD(Date[Date], 1, YEAR))',40,rf(DK,20240229));
  T('DATEADD -1 DAY of 1 Oct 2025 = 30 Sep 2025 (ship 8, revenue 20)','CALCULATE([Total Revenue], DATEADD(Date[Date], -1, DAY))',20,rf(DK,20251001));
  T('DATEADD -1 QUARTER of Q2 2024 (Apr-Jun) = Q1 (91 days)','COUNTROWS(DATEADD(Date[Date], -1, QUARTER))',91,{rowFilters:[{col:'Date[Year]',vals:[2024]},{col:'Date[Quarter]',vals:[2]}]});
  // fiscal YTD across 1 Oct
  const fy="CALCULATE([Total Revenue], DATESYTD(Date[Date], \"09-30\"))";
  T('fiscal YTD at 1 Oct 2025 starts a new year = 70',fy,70,rf(DK,20251001));
  T('fiscal YTD at 30 Sep 2025 = 1 Oct 2024..30 Sep 2025 = 150',fy,150,rf(DK,20250930));
  T('fiscal YTD at 1 Oct 2024 = 30',fy,30,rf(DK,20241001));
  T('fiscal YTD at 30 Sep 2024 = 250',fy,250,rf(DK,20240930));
  T('calendar YTD at 30 Sep 2025 = 120','CALCULATE([Total Revenue], DATESYTD(Date[Date]))',120,rf(DK,20250930));
  T('TOTALYTD with year end for Oct 2025 = 70','TOTALYTD([Total Revenue], Date[Date], "09-30")',70,rf(YM,'2025-10'));
  T('TOTALYTD calendar for Mar 2025 = 100','TOTALYTD([Total Revenue], Date[Date])',100,rf(YM,'2025-03'));
  T('DATESQTD at 15 Mar 2025 = ships 5,6 = 100','CALCULATE([Total Revenue], DATESQTD(Date[Date]))',100,rf(DK,20250315));
  T('DATESMTD at 15 Mar 2025 = 60','CALCULATE([Total Revenue], DATESMTD(Date[Date]))',60,rf(DK,20250315));
  T('TOTALQTD at 15 Mar 2025 = 100','TOTALQTD([Total Revenue], Date[Date])',100,rf(DK,20250315));
  // SAMEPERIODLASTYEAR incl. leap day
  T('SPLY of 29 Feb 2024 is one day: 28 Feb 2023','COUNTROWS(SAMEPERIODLASTYEAR(Date[Date]))',1,rf(DK,20240229));
  T('SPLY of 29 Feb 2024 is DATE(2023,2,28)','MINX(SAMEPERIODLASTYEAR(Date[Date]), Date[Date]) = DATE(2023,2,28)',true,rf(DK,20240229));
  T('SPLY of Feb 2024 (29 days) = Feb 2023 (28 days)','COUNTROWS(SAMEPERIODLASTYEAR(Date[Date]))',28,rf(YM,'2024-02'));
  T('SPLY of Feb 2025 (28 days) = whole Feb 2024 (29 days)','COUNTROWS(SAMEPERIODLASTYEAR(Date[Date]))',29,rf(YM,'2025-02'));
  T('SPLY revenue Feb 2025 -> Feb 2024 = ship 1 = 100','CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Date[Date]))',100,rf(YM,'2025-02'));
  T('SPLY revenue Mar 2025 -> Mar 2024 = ship 2 = 100','CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Date[Date]))',100,rf(YM,'2025-03'));
  T('SPLY of Mar 2024 -> Mar 2023 has no shipments -> blank','CALCULATE([Total Revenue], SAMEPERIODLASTYEAR(Date[Date]))',null,rf(YM,'2024-03'));
  T('PARALLELPERIOD -1 YEAR of Mar 2025 = all of 2024 = 280','CALCULATE([Total Revenue], PARALLELPERIOD(Date[Date], -1, YEAR))',280,rf(YM,'2025-03'));
  T('PREVIOUSYEAR of Mar 2025 = 280','CALCULATE([Total Revenue], PREVIOUSYEAR(Date[Date]))',280,rf(YM,'2025-03'));
  T('PREVIOUSMONTH of Mar 2024 = Feb 2024 = 100','CALCULATE([Total Revenue], PREVIOUSMONTH(Date[Date]))',100,rf(YM,'2024-03'));
  T('PREVIOUSMONTH of Oct 2024 = Sep 2024 = 50','CALCULATE([Total Revenue], PREVIOUSMONTH(Date[Date]))',50,rf(YM,'2024-10'));
  T('DATESINPERIOD -3 MONTH from 31 Mar 2025 = Jan-Mar 2025 = 100','CALCULATE([Total Revenue], DATESINPERIOD(Date[Date], MAX(Date[Date]), -3, MONTH))',100,rf(YM,'2025-03'));
  T('DATESINPERIOD -1 MONTH from 31 Mar 2024 = Mar only = 100','CALCULATE([Total Revenue], DATESINPERIOD(Date[Date], MAX(Date[Date]), -1, MONTH))',100,rf(YM,'2024-03'));
  T('DATESINPERIOD -3 MONTH from 31 Mar 2024 = ships 1,2 = 200','CALCULATE([Total Revenue], DATESINPERIOD(Date[Date], MAX(Date[Date]), -3, MONTH))',200,rf(YM,'2024-03'));
  T('DATESBETWEEN with EOMONTH start (rolling 3 months)','CALCULATE([Total Revenue], DATESBETWEEN(Date[Date], EOMONTH(MAX(Date[Date]), -3) + 1, MAX(Date[Date])))',100,rf(YM,'2025-03'));
  T('DATESBETWEEN with BLANK start = everything up to the date (running total)','CALCULATE([Total Revenue], DATESBETWEEN(Date[Date], BLANK(), MAX(Date[Date])))',200,rf(YM,'2024-03'));
  T('running total with FILTER(ALL(Date[Date]), ...)','CALCULATE([Total Revenue], FILTER(ALL(Date[Date]), Date[Date] <= MAX(Date[Date])))',200,rf(YM,'2024-03'));
  T('running total with FILTER(ALL(Date), ...)','CALCULATE([Total Revenue], FILTER(ALL(Date), Date[Date] <= MAX(Date[Date])))',200,rf(YM,'2024-03'));
  T('a Date[Date] filter removes the other Date filters (marked date table)','CALCULATE([Total Revenue], DATESYTD(Date[Date]))',120,{rowFilters:[{col:'Date[Year]',vals:[2025]},{col:'Date[MonthNo]',vals:[9]}]});
  T('LASTDATE filter','CALCULATE([Total Revenue], LASTDATE(Date[Date]))',20,rf(YM,'2025-09'));
  T('EOMONTH','EOMONTH(DATE(2024,2,10), 0) = DATE(2024,2,29)',true);
  T('date - date is days','DATE(2024,3,1) - DATE(2024,2,1)',29);
  T('date + days is a date','DATE(2024,2,28) + 2 = DATE(2024,3,1)',true);
  T('YEAR / MONTH / QUARTER','YEAR(DATE(2025,11,3)) * 100 + MONTH(DATE(2025,11,3)) + QUARTER(DATE(2025,11,3))',202515);
  // ALLSELECTED
  const pct='DIVIDE([Total Revenue], CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName])))';
  T('ALLSELECTED without a slicer = ALL: Gamma 120/470',pct,120/470,rf(NAME,'Gamma'));
  T('ALLSELECTED with a Segment slicer: Alpha 160/190',pct,160/190,{slicers:[{col:'Customer[Segment]',vals:['Key']}],rowFilters:[{col:NAME,vals:['Alpha']}]});
  T('ALL(Customer) ignores the slicer: 470','CALCULATE([Total Revenue], ALL(Customer))',470,{slicers:[{col:'Customer[Segment]',vals:['Key']}],rowFilters:[{col:NAME,vals:['Alpha']}]});
  T('ALLSELECTED(Customer) keeps the slicer: 190','CALCULATE([Total Revenue], ALLSELECTED(Customer))',190,{slicers:[{col:'Customer[Segment]',vals:['Key']}],rowFilters:[{col:NAME,vals:['Alpha']}]});
  T('ALLSELECTED() keeps the slicer: 190','CALCULATE([Total Revenue], ALLSELECTED())',190,{slicers:[{col:'Customer[Segment]',vals:['Key']}],rowFilters:[{col:NAME,vals:['Alpha']}]});
  T('slicer on the same column: ALLSELECTED = 280, ALL = 470','CALCULATE([Total Revenue], ALLSELECTED(Customer[CustomerName])) * 1000 + CALCULATE([Total Revenue], ALL(Customer[CustomerName]))',280*1000+470,{slicers:[{col:NAME,vals:['Alpha','Gamma']}],rowFilters:[{col:NAME,vals:['Alpha']}]});
  T('ALLSELECTED(col) as a table: COUNTROWS with slicer = 2','COUNTROWS(ALLSELECTED(Customer[CustomerName]))',2,{slicers:[{col:NAME,vals:['Alpha','Gamma']}],rowFilters:[{col:NAME,vals:['Alpha']}]});
  // ISINSCOPE
  const sc1='IF(ISINSCOPE(Customer[CustomerName]), "row", "total")';
  T('ISINSCOPE at the grand total is false',sc1,'total',{groupBy:[]});
  T('ISINSCOPE at a customer row is true',sc1,'row',{groupBy:[NAME],rowFilters:[{col:NAME,vals:['Alpha']}]});
  T('ISINSCOPE of the parent level at a subtotal row','IF(ISINSCOPE(Customer[Segment]), 1, 0) * 10 + IF(ISINSCOPE(Customer[CustomerName]), 1, 0)',10,{groupBy:['Customer[Segment]'],rowFilters:[{col:'Customer[Segment]',vals:['Key']}]});
  T('ISINSCOPE is dropped by ALL','CALCULATE(IF(ISINSCOPE(Customer[CustomerName]), 1, 0), ALL(Customer[CustomerName]))',0,{groupBy:[NAME],rowFilters:[{col:NAME,vals:['Alpha']}]});
  // SELECTEDVALUE / HASONEVALUE
  T('SELECTEDVALUE with no filter -> alternate','SELECTEDVALUE(Customer[Segment], "Mixed")','Mixed');
  T('SELECTEDVALUE with one customer -> value','SELECTEDVALUE(Customer[Segment], "Mixed")','Key',rf(NAME,'Alpha'));
  T('SELECTEDVALUE without alternate is blank','SELECTEDVALUE(Customer[Segment])',null);
  T('HASONEVALUE false with no filter','HASONEVALUE(Shipment[Mode])',false);
  T('HASONEVALUE true with Mode filter','HASONEVALUE(Shipment[Mode])',true,rf('Shipment[Mode]','Ocean'));
  T('HASONEVALUE true when a filter leaves one value (Country=USA, two customers, one country)','HASONEVALUE(Customer[Country])',true,rf('Customer[Country]','USA'));
  // SWITCH
  const sw='SWITCH(TRUE(), [Total Revenue] > 400, "big", [Total Revenue] > 150, "mid", "small")';
  T('SWITCH(TRUE()) total -> big',sw,'big');T('SWITCH(TRUE()) Alpha 160 -> mid',sw,'mid',rf(NAME,'Alpha'));T('SWITCH(TRUE()) Delta 30 -> small',sw,'small',rf(NAME,'Delta'));
  T('SWITCH value form hit','SWITCH(SELECTEDVALUE(Shipment[Mode]), "Ocean", 1, "Air", 2, 0)',2,rf('Shipment[Mode]','Air'));
  T('SWITCH value form else','SWITCH(SELECTEDVALUE(Shipment[Mode]), "Ocean", 1, "Air", 2, 0)',0);
  T('SWITCH without else is blank','SWITCH(5, 1, "a", 2, "b")',null);
  T('COALESCE','COALESCE(BLANK(), BLANK(), 5, 6)',5);
  T('INT floors negatives','INT(-1.5)',-2);T('MOD takes the sign of the divisor','MOD(-1, 3)',2);
  // ALLEXCEPT
  T('ALLEXCEPT keeps Country: Germany = Alpha+Beta = 320','CALCULATE([Total Revenue], ALLEXCEPT(Customer, Customer[Country]))',320,{rowFilters:[{col:NAME,vals:['Alpha']},{col:'Customer[Country]',vals:['Germany']}]});
  T('ALLEXCEPT with nothing kept left = 470','CALCULATE([Total Revenue], ALLEXCEPT(Customer, Customer[Country]))',470,rf(NAME,'Alpha'));
  T('ALLEXCEPT on Shipment keeps Mode = Ocean total 310','CALCULATE([Total Revenue], ALLEXCEPT(Shipment, Shipment[Mode]))',310,{rowFilters:[{col:'Shipment[Mode]',vals:['Ocean']},{col:'Shipment[Region]',vals:['Asia']}]});
  // USERELATIONSHIP
  const ur='CALCULATE([Total Revenue], USERELATIONSHIP(Shipment[DeliveryDateKey], Date[DateKey]))';
  T('by order date Apr 2024 = blank','[Total Revenue]',null,rf(YM,'2024-04'));
  T('USERELATIONSHIP delivered in Apr 2024 = ship 2 = 100',ur,100,rf(YM,'2024-04'));
  T('USERELATIONSHIP delivered in Oct 2025 = ships 7+8 = 90',ur,90,rf(YM,'2025-10'));
  T('order date Oct 2025 = ship 7 = 70','[Total Revenue]',70,rf(YM,'2025-10'));
  T('USERELATIONSHIP with the active pair is a no-op','CALCULATE([Total Revenue], USERELATIONSHIP(Shipment[DateKey], Date[DateKey]))',70,rf(YM,'2025-10'));
  T('time intelligence + USERELATIONSHIP (delivered Jan-Oct 2025: ships 5,6,7,8 = 190)','CALCULATE([Total Revenue], USERELATIONSHIP(Shipment[DeliveryDateKey], Date[DateKey]), DATESYTD(Date[Date]))',190,rf(YM,'2025-10'));
  // TREATAS
  T('TREATAS list onto Target[YearMonth] = 130','CALCULATE(SUM(Target[TargetRevenue]), TREATAS({"2024-03"}, Target[YearMonth]))',130);
  T('TREATAS VALUES(Shipment[Region]) onto Target[Region] (Asia) = 120','CALCULATE(SUM(Target[TargetRevenue]), TREATAS(VALUES(Shipment[Region]), Target[Region]))',120,rf('Shipment[Region]','Asia'));
  T('Target ignores Date/Region without TREATAS (no relationship)','SUM(Target[TargetRevenue])',185,rf('Shipment[Region]','Asia'));
  T('TREATAS month + region together; VALUES(Region) only sees March 2024 shipments (Asia) = 120','CALCULATE(SUM(Target[TargetRevenue]), TREATAS(VALUES(Date[YearMonth]), Target[YearMonth]), TREATAS(VALUES(Shipment[Region]), Target[Region]))',120,rf(YM,'2024-03'));
  T('TREATAS onto a dimension column','CALCULATE([Total Revenue], TREATAS({"Germany"}, Customer[Country]))',320);
  // iterators / tables
  T('measure ref transitions inside SUMX','SUMX(Customer, [Total Revenue])',470);
  T('plain SUM inside SUMX has no transition (4 customers)','SUMX(Customer, SUM(Shipment[Revenue]))',1880);
  T('ADDCOLUMNS + MAXX over the added column','MAXX(ADDCOLUMNS(VALUES(Customer[CustomerName]), "Rev", [Total Revenue]), [Rev])',160);
  T('SUMMARIZE group-by columns (Mode x Region combos)','COUNTROWS(SUMMARIZE(Shipment, Shipment[Mode], Shipment[Region]))',5);
  T('SUMMARIZE through a relationship (Customer[Segment])','COUNTROWS(SUMMARIZE(Shipment, Customer[Segment]))',2);
  T('CONCATENATEX with order','CONCATENATEX(TOPN(3, ALL(Customer), [Total Revenue]), Customer[CustomerName], ", ", Customer[CustomerName], ASC)','Alpha, Beta, Gamma');
  T('RELATEDTABLE counts shipments per customer','SUMX(FILTER(Customer, COUNTROWS(RELATEDTABLE(Shipment)) = 3), 1)',1);
  T('CALCULATETABLE + COUNTROWS','COUNTROWS(CALCULATETABLE(Shipment, Shipment[Mode] = "Air"))',2);
  T('DISTINCTCOUNT of a text column','DISTINCTCOUNT(Date[YearMonth])',12,rf('Date[Year]',2024));
  T('COUNTBLANK of a column without blanks','COUNTBLANK(Shipment[Revenue])',0);
  T('empty argument is allowed','COALESCE(, 4)',4);
  DB=keep;
}

/* page entry point: ?selftest&seed=N[&topic=T05][&engine=1] */
function bootSelfTest(q){
  document.body.classList.add('selftest');
  const seed=parseInt(q.get('seed'),10);
  let lines;
  try{lines=runSelfTest(Number.isFinite(seed)?seed:20260824,{topic:q.get('topic')||null,engine:q.has('engine')});}
  catch(e){lines=['SELFTEST FAIL exception: '+e.message+(e.stack?'\n'+e.stack:'')];console.log(lines[0]);window.__selftest={ok:false,pass:0,total:0,lines:lines};}
  document.getElementById('selftest-out').textContent=lines.join('\n');
}
