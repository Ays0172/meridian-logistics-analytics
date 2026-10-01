"use strict";
/* =====================================================================
   checks.js - topic registry + validation, pattern rules (AST predicates),
   grading contexts, sameVal and grade().
   Loaded after engine.js and before the topic files.
   ===================================================================== */

/* ---------------- Topic registry ---------------- */
const LEVELS=['Beginner','Intermediate','Pro'];
const TOPICS=[];            // registered topics, sorted by order
const REG_ERRORS=[];        // validation problems found while registering (the selftest fails if any)
const CH_BY_ID={};
const lst=(x,P)=>typeof x==='function'?x(P):(x||[]);
function chRef(ch,P){return typeof ch.ref==='function'?ch.ref(P):ch.ref;}
function chAlts(ch,P){return lst(ch.alts,P);}
function chWrongs(ch,P){return lst(ch.wrongs,P);}
function chPrompt(ch,P){return typeof ch.prompt==='function'?ch.prompt(P):ch.prompt;}
function normBy(ch){const b=ch.by;return Array.isArray(b)?b:(b?[b]:[]);}
function slicerOf(ch,P){const s=typeof ch.slicer==='function'?ch.slicer(P):ch.slicer;return s||[];}
function colIdOk(id){
  const m=/^([A-Za-z]+)\[([A-Za-z]+)\]$/.exec(id||'');
  return !!(m&&TABLES[m[1]]&&TABLES[m[1]].cols.includes(m[2]));
}
function registerTopic(t){
  const errs=[];const where='topic '+(t&&t.id);
  const bad=m=>errs.push(where+': '+m);
  if(!t||typeof t!=='object'){REG_ERRORS.push('registerTopic: argument is not an object');return;}
  if(!/^T\d\d$/.test(t.id||''))bad('id must look like "T05"');
  if(TOPICS.some(x=>x.id===t.id))bad('duplicate topic id');
  if(typeof t.title!=='string'||!t.title)bad('title is required');
  if(typeof t.order!=='number')bad('order (number) is required');
  else if(TOPICS.some(x=>x.order===t.order))bad('duplicate order '+t.order);
  if(typeof t.concept!=='string'||!t.concept.trim())bad('concept (text) is required');
  else if(t.concept.trim().split(/\s+/).length>150)bad('concept is longer than 150 words');
  if(!Array.isArray(t.challenges))bad('challenges must be an array (may be empty)');
  const good=[];
  (t.challenges||[]).forEach((ch,i)=>{
    const w='challenge '+(ch&&ch.id||('#'+(i+1)))+' of '+t.id;
    const cb=m=>errs.push(w+': '+m);
    if(!ch||typeof ch!=='object'){cb('not an object');return;}
    if(!ch.id||ch.id.indexOf(t.id+'-')!==0)cb('id must start with "'+t.id+'-"');
    if(CH_BY_ID[ch.id]||good.some(g=>g.id===ch.id))cb('duplicate id');
    if(!LEVELS.includes(ch.level))cb('level must be one of '+LEVELS.join('/'));
    if(!ch.title)cb('title is required');
    for(const k of ['prompt','ref'])if(typeof ch[k]!=='function'&&typeof ch[k]!=='string')cb(k+' must be a string or a function of P');
    if(typeof ch.hint!=='string'||!ch.hint)cb('hint is required');
    if(typeof ch.why!=='string'||!ch.why)cb('why is required');
    if(typeof ch.oracle!=='function')cb('oracle(D, ctx) is required');
    const by=normBy(ch);
    if(by.length<1||by.length>2||!by.every(colIdOk))cb('by must be one or two columns such as "Shipment[Mode]" (got '+JSON.stringify(ch.by)+')');
    else if(by.some(b=>b.startsWith('Target[')))cb('by cannot use the Target table');
    if(!Array.isArray(ch.checks))cb('checks must be an array of rule ids (may be empty)');
    else for(const c of ch.checks)if(!RULES[c])cb('unknown check rule "'+c+'"');
    for(const k of ['alts','wrongs']){
      if(ch[k]!==undefined&&typeof ch[k]!=='function'&&!Array.isArray(ch[k]))cb(k+' must be an array or a function of P');
      else if(Array.isArray(ch[k]))for(const a of ch[k])if(!a||typeof a.code!=='string')cb(k+' entries need a "code" string');
    }
    if(ch.noTotal!==undefined&&typeof ch.noTotal!=='boolean')cb('noTotal must be true/false');
    if(ch.slicer!==undefined&&typeof ch.slicer!=='function'){
      if(!Array.isArray(ch.slicer)||!ch.slicer.every(s=>s&&colIdOk(s.col)&&Array.isArray(s.vals)))cb('slicer must be [{col:"Table[Col]", vals:[...]}]');
    }
    if(!Array.isArray(ch.wrongs)&&typeof ch.wrongs!=='function')cb('wrongs is required (at least 2 wrong answers are expected)');
    good.push(ch);
  });
  if(errs.length){errs.forEach(e=>REG_ERRORS.push(e));}
  if(/^T\d\d$/.test(t.id||'')&&typeof t.order==='number'&&!TOPICS.some(x=>x.id===t.id||x.order===t.order)){
    t.challenges=good.filter(ch=>ch&&ch.id&&!CH_BY_ID[ch.id]);
    t.challenges.forEach(ch=>{CH_BY_ID[ch.id]=ch;ch.topic=t.id;});
    TOPICS.push(t);TOPICS.sort((a,b)=>a.order-b.order);
  }
}
function allChallenges(){const o=[];TOPICS.forEach(t=>t.challenges.forEach(c=>o.push(c)));return o;}

/* ---------------- Pattern checks (AST predicates) ---------------- */
function walk(n,fn){
  if(!n||typeof n!=='object')return;
  fn(n);
  if(n.l)walk(n.l,fn);if(n.r)walk(n.r,fn);if(n.e)walk(n.e,fn);
  if(n.args)n.args.forEach(a=>walk(a,fn));
  if(n.items)n.items.forEach(a=>walk(a,fn));
  if(n.vars)n.vars.forEach(v=>walk(v.e,fn));
  if(n.body)walk(n.body,fn);
}
function countCols(n){const s=new Set();let calls=0;walk(n,x=>{if(x.t==='col')s.add((x.table+'['+x.col+']').toLowerCase());if(x.t==='call')calls++;});return {cols:s.size,calls:calls};}
function astKey(n){   // structural fingerprint without positions
  if(!n||typeof n!=='object')return String(n);
  const o={};for(const k of Object.keys(n)){if(k==='pos'||k==='end'||k==='raw'||k==='_r'||k==='_pc')continue;o[k]=n[k];}
  return JSON.stringify(o,(k,v)=>(k==='pos'||k==='end'||k==='raw'||k==='_r'||k==='_pc')?undefined:v);
}
const RULES={
  slash:{level:'Intermediate',kind:'warn',test(ast){let hit=false;walk(ast,n=>{if(n.t==='bin'&&n.op==='/')hit=true;});return hit;},
    msg:'`/` returns Infinity (or an error) when the denominator is 0.',fix:'Use DIVIDE(numerator, denominator) - it returns BLANK instead.'},
  unqual:{level:'Beginner',kind:'warn',test(ast){
      const defined=new Set();
      walk(ast,n=>{if(n.t==='call'&&n.name==='ADDCOLUMNS')n.args.forEach((a,i)=>{if(i>0&&i%2===1&&a.t==='str')defined.add(a.v.toLowerCase());});});
      let hit=false;walk(ast,n=>{if(n.t==='mref'&&!MEASURE_LC[n.name.toLowerCase()]&&!defined.has(n.name.toLowerCase()))hit=true;});return hit;},
    msg:'A name in [brackets] with no table in front is read as a measure, not a column.',fix:'Write columns with their table: Shipment[Revenue].'},
  filterInCalc:{level:'Intermediate',kind:'info',test(ast){
      let hit=false;
      walk(ast,n=>{if(n.t==='call'&&n.name==='CALCULATE')n.args.slice(1).forEach(a=>{
        if(a.t==='call'&&a.name==='FILTER'&&a.args.length===2&&a.args[0].t==='id'){const c=countCols(a.args[1]);if(c.cols===1&&c.calls===0)hit=true;}});});
      return hit;},
    msg:'FILTER(table, simple condition) inside CALCULATE works, but it iterates the whole table and overrides more context than needed.',fix:'A plain column filter is shorter and faster: CALCULATE(..., Shipment[Mode] = "Ocean").'},
  avgRatio:{level:'Pro',kind:'warn',test(ast){let hit=false;walk(ast,n=>{if(n.t==='call'&&n.name==='AVERAGEX'&&n.args[1]){walk(n.args[1],m=>{if((m.t==='bin'&&m.op==='/')||(m.t==='call'&&m.name==='DIVIDE'))hit=true;});}});return hit;},
    msg:'AVERAGEX over a per-row ratio is an average of ratios; every shipment counts equally, whatever its size.',fix:'Build the ratio from totals: DIVIDE(SUM(numerator), SUM(denominator)).'},
  ffeScope:{level:'Pro',kind:'warn',test(ast){
      let scoped=false;
      walk(ast,n=>{if(n.t==='bin'&&['>','<>','>='].includes(n.op)&&n.l.t==='col'&&n.l.col.toLowerCase()==='ffe'&&n.r.t==='num')scoped=true;});
      return !scoped;},
    msg:'Nothing restricts the ratio to Ffe > 0. Air shipments have Revenue but Ffe = 0, so their revenue inflates the numerator while adding nothing to the denominator.',fix:'CALCULATE(DIVIDE(SUM(Shipment[Revenue]), SUM(Shipment[Ffe])), KEEPFILTERS(Shipment[Ffe] > 0)) - KEEPFILTERS intersects with any existing Ffe filter instead of replacing it.'},
  allTable:{level:'Intermediate',kind:'info',test(ast){let hit=false;walk(ast,n=>{if(n.t==='call'&&n.name==='ALL'&&n.args.length===1&&n.args[0].t==='id')hit=true;});return hit;},
    msg:'ALL(Shipment) clears every filter on Shipment, more than this question needs.',fix:'ALL(Shipment[Mode]) clears only the Mode filter, which is what a share-of-all-modes denominator wants.'},
  sumxRedundant:{level:'Beginner',kind:'info',test(ast){let hit=false;walk(ast,n=>{if(n.t==='call'&&n.name==='SUMX'&&n.args.length===2&&n.args[0].t==='id'&&n.args[1].t==='col'&&n.args[0].name.toLowerCase()===n.args[1].table.toLowerCase())hit=true;});return hit;},
    msg:'SUMX(Shipment, Shipment[Column]) works, but it is just a longer SUM(Shipment[Column]).',fix:'Use SUM(Shipment[Column]) when you only add up a single column; keep SUMX for row-by-row calculations.'},
  hardcodedPeriod:{level:'Intermediate',kind:'warn',test(ast){
      let hit=false;
      walk(ast,n=>{if(n.t==='bin'&&['=','<>','<','>','<=','>=','in'].includes(n.op)){
        const isDateCol=x=>x&&x.t==='col'&&x.table.toLowerCase()==='date'&&['year','monthno','yearmonth','fiscalyear','quarter','monthname'].includes(x.col.toLowerCase());
        const lit=x=>x&&(x.t==='num'||x.t==='str'||x.t==='list');
        if((isDateCol(n.l)&&lit(n.r))||(isDateCol(n.r)&&lit(n.l)))hit=true;}});
      return hit;},
    msg:'A fixed year/month is written into the formula, so it will not move with the report (every row would show the same period).',fix:'Derive the period from the current context instead: MAX(Date[Date]), SAMEPERIODLASTYEAR, DATEADD, DATESYTD ...'},
  varRepeat:{level:'Intermediate',kind:'info',test(ast){
      const seen={};let hit=false;
      walk(ast,n=>{if(n.t==='call'&&['CALCULATE','SUMX','AVERAGEX','DIVIDE','TOTALYTD','COUNTROWS'].includes(n.name)&&n.args.length>=2){const k=astKey(n);seen[k]=(seen[k]||0)+1;if(seen[k]>=2)hit=true;}});
      return hit;},
    msg:'The same calculation appears more than once in this formula.',fix:'Store it in a VAR once and reuse the variable: it is evaluated once and the formula is easier to read and debug.'}
};
function runChecks(ch,ast){
  const out=[];
  if(!ast)return out;
  for(const id of ch.checks){const r=RULES[id];if(r&&r.test(ast))out.push({rule:id,level:r.level,kind:r.kind,msg:r.msg,fix:r.fix});}
  return out;
}

/* ---------------- Grading ---------------- */
const colShort=id=>id.slice(id.indexOf('[')+1,-1);
// One entry per row of the result grid the learner's measure is tested on:
//   {label, slicers:[{col,vals}], rowFilters:[{col,vals}], groupBy:[ids], oracleCtx, subtotal}
function contextsFor(ch,D){
  D=D||DB;
  D.__ctxs=D.__ctxs||{};
  if(D.__ctxs[ch.id])return D.__ctxs[ch.id];
  const P=D.params,by=normBy(ch),slic=slicerOf(ch,P);
  const slicObj={};slic.forEach(s=>slicObj[s.col]=s.vals.slice());
  const out=[];
  const mk=(label,gb,sel,subtotal)=>({label:label,slicers:slic,rowFilters:gb.map(c=>({col:c,vals:[sel[c]]})),groupBy:gb,subtotal:!!subtotal,
    oracleCtx:{label:label,P:P,level:gb.length,groupBy:gb.slice(),sel:Object.assign({},sel),slicers:slicObj}});
  if(!ch.noTotal)out.push(mk('Grand total',[],{}));
  (function rec(level,sel){
    const col=by[level];
    const rows=H.vis(D,{slicers:slicObj,sel:sel});
    const seen=new Set(),vals=[];
    for(const s of rows){const v=H.colVal(s,col);if(!seen.has(v)){seen.add(v);vals.push(v);}}
    vals.sort((a,b)=>typeof a==='number'&&typeof b==='number'?a-b:String(a).localeCompare(String(b)));
    for(const v of vals){
      const sel2=Object.assign({},sel);sel2[col]=v;
      const gb=by.slice(0,level+1);
      const sub=level+1<by.length;
      out.push(mk(gb.map(c=>colShort(c)+' = '+sel2[c]).join(', ')+(sub?' (subtotal)':''),gb,sel2,sub));
      if(sub)rec(level+1,sel2);
    }
  })(0,{});
  return D.__ctxs[ch.id]=out;
}
function sameVal(a,b,tol){
  if(a==null&&b==null)return true;
  if(a==null)a=0;if(b==null)b=0;   // BLANK and 0 are treated as equal when grading
  if(typeof a==='number'&&typeof b==='number'){
    if(a===b)return true;
    if(!Number.isFinite(a)||!Number.isFinite(b))return false;
    return Math.abs(a-b)<=tol*Math.max(1,Math.abs(a),Math.abs(b));
  }
  return a===b;   // text (and dates) compare exactly: case, spaces and punctuation all count
}
function textMismatch(a,b){return typeof a==='string'&&typeof b==='string'&&a!==b;}
function normCode(s){return s.replace(/\/\/.*$/gm,'').replace(/--.*$/gm,'').replace(/^\s*[A-Za-z_][A-Za-z0-9_ %#.$\-]*=\s*(?!=)/,'').replace(/\s+/g,'').toLowerCase();}
function evalIn(code,c){return evalMeasure(code,{slicers:c.slicers,rowFilters:c.rowFilters,groupBy:c.groupBy});}
// returns {status:'parse'|'runtime'|'ok'|'wrong', error, rows, warnings}
function grade(ch,code,P){
  let ast=null;
  try{ast=parseCached(code);}
  catch(e){if(e instanceof DaxError)return {status:'parse',error:e,rows:[],warnings:[]};throw e;}
  const warnings=runChecks(ch,ast);
  const ref=chRef(ch,P),tol=ch.tolerance||1e-6;
  const rows=[];let err=null;
  for(const c of contextsFor(ch)){
    const exp=evalIn(ref,c);
    let got=null,bad=false;
    try{got=evalIn(code,c);}catch(e){if(e instanceof DaxError){err=err||e;bad=true;}else throw e;}
    const tm=!bad&&textMismatch(got,exp);
    rows.push({label:c.label,user:got,exp:exp,match:!bad&&sameVal(got,exp,tol),err:bad,textDiff:tm,
      textNote:tm?(got.toLowerCase()===exp.toLowerCase()?'differs only in upper/lower case':(got.trim()===exp.trim()?'differs only in leading/trailing spaces':'different text')):''});
  }
  if(err)return {status:'runtime',error:err,rows:rows,warnings:warnings};
  return {status:rows.every(r=>r.match)?'ok':'wrong',rows:rows,warnings:warnings};
}
