"use strict";
/* =====================================================================
   engine.js - tokenizer, parser and evaluator for the DAX subset.
   Evaluation context: { f: Map('Table[Col]' -> Set of norm()ed values),
                         slicers: Map (outer/report filters, used by ALLSELECTED),
                         groupBy: ['Table[Col]'] (columns in scope of the visual row, used by ISINSCOPE),
                         rel: null | 'DeliveryDateKey' (active Shipment-Date relationship), cache }
   ===================================================================== */

/* ---------------- Tokenizer ---------------- */
class DaxError extends Error{constructor(msg,pos,len){super(msg);this.pos=(pos==null?-1:pos);this.len=len||1;}}
function tokenize(src){
  const toks=[];let i=0;const n=src.length;
  while(i<n){
    const c=src[i];
    if(/\s/.test(c)){i++;continue;}
    if((c==='/'&&src[i+1]==='/')||(c==='-'&&src[i+1]==='-')){while(i<n&&src[i]!=='\n')i++;continue;}
    if(c==='/'&&src[i+1]==='*'){const e=src.indexOf('*/',i+2);if(e<0)throw new DaxError("This comment started with /* but is never closed with */",i,2);i=e+2;continue;}
    if(/[0-9]/.test(c)||(c==='.'&&/[0-9]/.test(src[i+1]||''))){
      let j=i;while(j<n&&/[0-9]/.test(src[j]))j++;
      if(src[j]==='.'){j++;while(j<n&&/[0-9]/.test(src[j]))j++;}
      toks.push({type:'num',v:parseFloat(src.slice(i,j)),pos:i,end:j});i=j;continue;
    }
    if(c==='"'){
      let j=i+1,s='';
      for(;;){
        if(j>=n)throw new DaxError('This text string is missing its closing double quote (")',i,1);
        if(src[j]==='"'){if(src[j+1]==='"'){s+='"';j+=2;continue;}break;}
        s+=src[j++];
      }
      toks.push({type:'str',v:s,pos:i,end:j+1});i=j+1;continue;
    }
    if(c==="'"){
      const e=src.indexOf("'",i+1);if(e<0)throw new DaxError("This quoted table name is missing its closing apostrophe (')",i,1);
      toks.push({type:'qid',v:src.slice(i+1,e),pos:i,end:e+1});i=e+1;continue;
    }
    if(c==='['){
      const e=src.indexOf(']',i+1);if(e<0)throw new DaxError("This column/measure name is missing its closing bracket ]",i,1);
      toks.push({type:'br',v:src.slice(i+1,e),pos:i,end:e+1});i=e+1;continue;
    }
    if(/[A-Za-z_]/.test(c)){
      let j=i;while(j<n&&/[A-Za-z0-9_]/.test(src[j]))j++;
      toks.push({type:'id',v:src.slice(i,j),pos:i,end:j});i=j;continue;
    }
    const two=src.slice(i,i+2);
    if(two==='=='||two==='!='||two==='=>')throw new DaxError(two==='!='?"DAX does not use != ; write <> for 'not equal'":"DAX compares with a single = (not "+two+")",i,2);
    if(['<=','>=','<>','&&','||'].includes(two)){toks.push({type:'op',v:two,pos:i,end:i+2});i+=2;continue;}
    if('+-*/=<>&(),{}'.includes(c)){toks.push({type:'op',v:c,pos:i,end:i+1});i++;continue;}
    if(c===';')throw new DaxError('Separate arguments with a comma (,) - semicolons are not accepted here',i,1);
    if(c===':')throw new DaxError("Use = to define a measure (Name = expression), not :=",i,1);
    throw new DaxError("Unexpected character '"+c+"'",i,1);
  }
  toks.push({type:'eof',v:'',pos:n,end:n});
  return toks;
}

/* ---------------- Parser (recursive descent) -> AST ---------------- */
// Blank out an optional "Measure Name =" prefix, keeping all positions unchanged.
function stripMeasureName(src){
  let i=0;
  for(;;){
    const m=/^\s+/.exec(src.slice(i));if(m)i+=m[0].length;
    if(src.startsWith('//',i)||src.startsWith('--',i)){const e=src.indexOf('\n',i);if(e<0)return src;i=e+1;continue;}
    if(src.startsWith('/*',i)){const e=src.indexOf('*/',i+2);if(e<0)return src;i=e+2;continue;}
    break;
  }
  const rest=src.slice(i);
  if(/^(VAR|RETURN)\b/i.test(rest))return src;
  const m=/^('[^'\n]+'|[A-Za-z_][A-Za-z0-9_ %#.$\-]*?)\s*=(?![=>])/.exec(rest);
  if(!m)return src;
  const nameOnly=m[1];
  if(/^(VAR|RETURN)\b/i.test(nameOnly))return src;
  return src.slice(0,i)+' '.repeat(m[0].length)+rest.slice(m[0].length);
}
function parseFormula(src0){
  const src=stripMeasureName(src0);
  const toks=tokenize(src);
  if(toks.length===1)throw new DaxError('The formula is empty. Write an expression such as SUM(Shipment[Revenue])',0,1);
  let p=0;
  const peek=()=>toks[p], next=()=>toks[p++];
  const isOp=v=>toks[p].type==='op'&&toks[p].v===v;
  const isKw=k=>toks[p].type==='id'&&toks[p].v.toUpperCase()===k;
  const show=t=>t.type==='eof'?'the end of the formula':"'"+src.slice(t.pos,t.end)+"'";
  const fail=(msg,t)=>{t=t||peek();throw new DaxError(msg,t.pos,Math.max(1,t.end-t.pos));};

  function parseExpr(){
    if(isKw('VAR')){
      const vars=[];
      while(isKw('VAR')){
        next();const nt=next();
        if(nt.type!=='id')fail('Expected a variable name after VAR but found '+show(nt),nt);
        if(!isOp('='))fail("Expected '=' after the variable name '"+nt.v+"' but found "+show(peek()));
        next();
        vars.push({name:nt.v,e:parseExpr(),pos:nt.pos});
      }
      if(!isKw('RETURN'))fail('Expected RETURN after the VAR definitions but found '+show(peek()));
      next();
      return {t:'let',vars:vars,body:parseExpr()};
    }
    return parseOr();
  }
  function parseOr(){let l=parseAnd();while(isOp('||')){const o=next();l={t:'bin',op:'||',l:l,r:parseAnd(),pos:o.pos};}return l;}
  function parseAnd(){let l=parseNot();while(isOp('&&')){const o=next();l={t:'bin',op:'&&',l:l,r:parseNot(),pos:o.pos};}return l;}
  // NOT as a prefix operator (NOT ISBLANK(x), NOT [Flag]): lower precedence than comparisons. NOT(x) stays an ordinary call.
  function parseNot(){
    const t=peek();
    if(t.type==='id'&&t.v.toUpperCase()==='NOT'&&!(toks[p+1]&&toks[p+1].type==='op'&&toks[p+1].v==='(')){next();return {t:'un',op:'NOT',e:parseNot(),pos:t.pos};}
    return parseCmp();
  }
  function parseCmp(){
    let l=parseConcat();
    for(;;){
      const t=peek();
      if(t.type==='op'&&['=','<>','<','>','<=','>='].includes(t.v)){next();l={t:'bin',op:t.v,l:l,r:parseConcat(),pos:t.pos};}
      else if(isKw('IN')){next();l={t:'bin',op:'in',l:l,r:parseConcat(),pos:t.pos};}
      else return l;
    }
  }
  function parseConcat(){let l=parseAdd();while(isOp('&')){const o=next();l={t:'bin',op:'&',l:l,r:parseAdd(),pos:o.pos};}return l;}
  function parseAdd(){let l=parseMul();while(isOp('+')||isOp('-')){const o=next();l={t:'bin',op:o.v,l:l,r:parseMul(),pos:o.pos};}return l;}
  function parseMul(){let l=parseUnary();while(isOp('*')||isOp('/')){const o=next();l={t:'bin',op:o.v,l:l,r:parseUnary(),pos:o.pos};}return l;}
  function parseUnary(){
    if(isOp('-')){const o=next();return {t:'un',op:'-',e:parseUnary(),pos:o.pos};}
    if(isOp('+')){next();return parseUnary();}
    return parsePrimary();
  }
  function parsePrimary(){
    const t=next();
    if(t.type==='num')return {t:'num',v:t.v,pos:t.pos};
    if(t.type==='str')return {t:'str',v:t.v,pos:t.pos};
    if(t.type==='op'&&t.v==='('){
      const e=parseExpr();
      if(!isOp(')')){
        if(peek().type==='eof')fail("Missing ')' - the '(' at position "+(t.pos+1)+" is never closed",peek());
        fail("Expected ')' but found "+show(peek()));
      }
      next();return e;
    }
    if(t.type==='op'&&t.v==='{'){
      const items=[];
      if(!isOp('}')){for(;;){items.push(parseExpr());if(isOp(',')){next();continue;}break;}}
      if(!isOp('}'))fail("Expected '}' to close the list but found "+show(peek()));
      next();return {t:'list',items:items,pos:t.pos};
    }
    if(t.type==='br')return {t:'mref',name:t.v,pos:t.pos,end:t.end};
    if(t.type==='qid'||t.type==='id'){
      if(t.type==='id'&&isOp('(')){
        const open=next();const args=[];
        if(!isOp(')')){
          for(;;){
            if(isOp(',')||isOp(')'))args.push({t:'empty',pos:peek().pos});   // omitted optional argument: f(a, , c)
            else args.push(parseExpr());
            if(isOp(',')){next();continue;}
            break;
          }
        }
        if(!isOp(')')){
          if(peek().type==='eof')fail("Missing ')' - the '(' after "+t.v+" at position "+(open.pos+1)+" is never closed",peek());
          fail("Expected ',' or ')' in the arguments of "+t.v+" but found "+show(peek()));
        }
        next();
        return {t:'call',name:t.v.toUpperCase(),raw:t.v,args:args,pos:t.pos,end:t.end};
      }
      if(peek().type==='br'){const b=next();return {t:'col',table:t.v,col:b.v,pos:t.pos,end:b.end};}
      if(t.type==='qid')return {t:'id',name:t.v,pos:t.pos,end:t.end};
      const u=t.v.toUpperCase();
      if(u==='TRUE')return {t:'bool',v:true,pos:t.pos};
      if(u==='FALSE')return {t:'bool',v:false,pos:t.pos};
      if(u==='RETURN'||u==='VAR')fail("'"+t.v+"' is not expected here",t);
      return {t:'id',name:t.v,pos:t.pos,end:t.end};
    }
    if(t.type==='eof')fail('The formula ends too early - an expression is missing here',t);
    fail('Unexpected '+show(t)+' - an expression (a number, column or function) was expected',t);
  }
  const ast=parseExpr();
  if(peek().type!=='eof'){
    const t=peek();
    if(t.type==='op'&&t.v===')')fail("Unexpected ')' - there is no matching '(' for it",t);
    fail('Unexpected '+show(t)+" - did you forget an operator or a comma before it?",t);
  }
  return ast;
}
const parseCache=new Map();
function parseCached(src){
  if(parseCache.has(src)){const c=parseCache.get(src);if(c.err)throw c.err;return c.ast;}
  try{const ast=parseFormula(src);parseCache.set(src,{ast:ast});return ast;}
  catch(e){if(e instanceof DaxError)parseCache.set(src,{err:e});throw e;}
}

/* ---------------- Evaluator: helpers ---------------- */
let DB=null; // current dataset
const TABLE_LC={}; Object.keys(TABLES).forEach(t=>TABLE_LC[t.toLowerCase()]=t);
function lev(a,b){const m=a.length,n=b.length,d=[];for(let i=0;i<=m;i++){d[i]=[i];}for(let j=1;j<=n;j++)d[0][j]=j;
  for(let i=1;i<=m;i++)for(let j=1;j<=n;j++)d[i][j]=Math.min(d[i-1][j]+1,d[i][j-1]+1,d[i-1][j-1]+(a[i-1]===b[j-1]?0:1));return d[m][n];}
function nearest(name,list){let best=null,bd=99;for(const x of list){const d=lev(name.toLowerCase(),x.toLowerCase());if(d<bd){bd=d;best=x;}}return bd<=Math.max(2,Math.floor(name.length/3))?best:null;}
function norm(v){if(v==null)return '\u0000null';if(typeof v==='string')return v.toLowerCase();if(typeof v==='object'&&v.isDate)return '\u0001'+v.n;return v;}
function inter(a,b){const o=new Set();for(const x of a)if(b.has(x))o.add(x);return o;}
const colId=(T,c)=>T+'['+c+']';
function resolveTable(name,node){
  const t=TABLE_LC[name.toLowerCase()];
  if(!t){const s=nearest(name,Object.keys(TABLES));
    throw new DaxError("Unknown table '"+name+"'."+(s?" Did you mean "+s+"?":" Tables are: "+Object.keys(TABLES).join(', ')+"."),node&&node.pos,name.length);}
  return t;
}
function resolveCol(n){
  if(n._r)return n._r;
  const T=resolveTable(n.table,n);
  const c=TABLES[T].cols.find(x=>x.toLowerCase()===n.col.toLowerCase());
  if(!c){const s=nearest(n.col,TABLES[T].cols);
    throw new DaxError("Table "+T+" has no column '"+n.col+"'."+(s?" Did you mean "+T+"["+s+"]?":" Columns: "+TABLES[T].cols.join(', ')+"."),n.pos,(n.end||n.pos)-n.pos);}
  return n._r={T:T,col:c};
}
function baseCtx(rc){
  rc=rc||{};
  const f=new Map(),slicers=new Map();
  for(const s of (rc.slicers||[])){const set=new Set(s.vals.map(norm));slicers.set(s.col,set);f.set(s.col,new Set(set));}
  for(const x of (rc.rowFilters||[])){const set=new Set(x.vals.map(norm));f.set(x.col,f.has(x.col)?inter(f.get(x.col),set):set);}
  return {f:f,slicers:slicers,groupBy:(rc.groupBy||[]).slice(),rel:null,cache:{}};
}
function mkCtx(f,base,o){return {f:f,slicers:base.slicers,groupBy:(o&&o.groupBy)||base.groupBy,rel:(o&&('rel' in o))?o.rel:base.rel,cache:{}};}
function ctxEntries(ctx,T){
  const c=ctx.cache;c.ent=c.ent||{};
  if(c.ent[T])return c.ent[T];
  const out=[],pre=T+'[';
  for(const [k,s] of ctx.f)if(k.startsWith(pre))out.push([k.slice(pre.length,-1),s]);
  return c.ent[T]=out;
}
function getIndex(T,col){
  DB.__idx=DB.__idx||{};const k=T+'.'+col;let m=DB.__idx[k];
  if(!m){m=new Map();for(const r of DB[T]){const x=norm(r[col]);let l=m.get(x);if(!l)m.set(x,l=[]);l.push(r);}DB.__idx[k]=m;}
  return m;
}
function visibleRows(T,ctx){
  const c=ctx.cache;c.rows=c.rows||{};
  if(c.rows[T])return c.rows[T];
  let rows=DB[T];
  const ent=ctxEntries(ctx,T);
  if(ent.length){
    let best=ent[0];for(const e of ent)if(e[1].size<best[1].size)best=e;
    let cand=rows;
    if(best[1].size*4<rows.length){
      const idx=getIndex(T,best[0]);cand=[];
      for(const k of best[1]){const l=idx.get(k);if(l)for(const r of l)cand.push(r);}
      if(best[1].size>1)cand.sort((a,b)=>a._i-b._i);
    }
    rows=cand.filter(r=>ent.every(([col,s])=>s.has(norm(r[col]))));
  }
  if(T==='Shipment'){
    for(const [P,fk] of [['Customer','CustomerKey'],['Date',ctx.rel||'DateKey']]){
      if(ctxEntries(ctx,P).length){
        const keys=new Set(visibleRows(P,ctx).map(r=>r[P==='Date'?'DateKey':'CustomerKey']));
        rows=rows.filter(r=>keys.has(r[fk]));
      }
    }
  }
  return c.rows[T]=rows;
}
function allValues(T,col){DB.__av=DB.__av||{};const k=T+'.'+col;if(DB.__av[k])return DB.__av[k];const seen=new Set(),out=[];for(const r of DB[T]){const x=norm(r[col]);if(!seen.has(x)){seen.add(x);out.push(r[col]);}}return DB.__av[k]=out;}
function colVals(T,col,ctx){
  const c=ctx.cache;c.cv=c.cv||{};const k=T+'.'+col;
  return c.cv[k]||(c.cv[k]=visibleRows(T,ctx).map(r=>r[col]));
}
function distinctVals(T,col,ctx){
  const seen=new Set(),out=[];
  for(const v of colVals(T,col,ctx)){const k=norm(v);if(!seen.has(k)){seen.add(k);out.push(v);}}
  return out;
}
// table values: full = the rows are real rows of table T; otherwise a virtual table with column ids "T[col]" or "[name]"
function ft(T,rows){return {isTable:true,full:true,T:T,cols:TABLES[T].cols.map(c=>colId(T,c)),rows:rows};}
function vt(cols,rows){return {isTable:true,full:false,T:null,cols:cols,rows:rows};}
const truthy=v=>v===true;
function sc(v,node){
  if(v&&v.isTable)throw new DaxError('A table was used where a single value is needed. Wrap it in an aggregation such as COUNTROWS(...) or SUMX(...).',node&&node.pos);
  if(v&&v.isList)throw new DaxError('A list {...} can only be used on the right side of IN (or as the first argument of TREATAS).',node&&node.pos);
  return v;
}
function numOf(v,node){
  if(v==null)return null;
  if(typeof v==='number')return v;
  if(typeof v==='boolean')return v?1:0;
  if(typeof v==='object'&&v.isDate)return v.n;
  const x=Number(v);if(v!==''&&Number.isFinite(x))return x;
  throw new DaxError("Cannot use the text '"+v+"' as a number.",node&&node.pos);
}
const DATE_INT_MSG='You are comparing a Date with a whole number (for example an int DateKey such as 20250131). DAX rejects that comparison: compare Date[Date] with a date (DATE(2025,1,31), MAX(Date[Date])), or compare a DateKey with another DateKey (MAX(Date[DateKey])). Stay in the same type on both sides.';
function cmpVals(a,b,node){
  const ad=a!=null&&typeof a==='object'&&a.isDate, bd=b!=null&&typeof b==='object'&&b.isDate;
  if(ad||bd){
    if(ad&&bd)return a.n<b.n?-1:(a.n>b.n?1:0);
    const o=ad?b:a;
    if(o==null)return ad?1:-1;
    if(typeof o==='number')throw new DaxError(DATE_INT_MSG,node&&node.pos,2);
    throw new DaxError("Cannot compare a Date with the text '"+o+"'. Build a date with DATE(year, month, day).",node&&node.pos,2);
  }
  if(a==null&&b==null)return 0;
  if(a==null)a=(typeof b==='string')?'':(typeof b==='boolean'?false:0);
  if(b==null)b=(typeof a==='string')?'':(typeof a==='boolean'?false:0);
  if(typeof a==='string'||typeof b==='string'){a=String(a).toLowerCase();b=String(b).toLowerCase();}
  return a<b?-1:(a>b?1:0);
}
function arity(n,min,max){
  const k=n.args.length;
  if(k<min||k>max)throw new DaxError(n.name+' expects '+(min===max?min:min+(max===Infinity?' or more':' to '+max))+' argument'+(max===1&&min===1?'':'s')+' but got '+k+'.',n.pos,n.name.length);
}
function needCol(a,fname){
  if(a.t==='mref'){
    if(MEASURE_LC[a.name.toLowerCase()])throw new DaxError(fname+' needs a column such as Shipment[Revenue], but ['+a.name+'] is a measure. To aggregate a measure over rows use SUMX(table, ['+a.name+']).',a.pos,(a.end||a.pos)-a.pos);
    ev(a,{ctx:null,rows:[],vars:{}});
  }
  if(a.t!=='col')throw new DaxError(fname+' needs a single column such as Shipment[Revenue] - not an expression. To aggregate an expression use '+(fname==='SUM'?'SUMX':fname==='AVERAGE'?'AVERAGEX':fname==='MIN'?'MINX':fname==='MAX'?'MAXX':'an iterator')+'(table, expression).',a.pos);
  return resolveCol(a);
}
function lookupRow(env,node){
  const {T,col}=resolveCol(node);
  const id=colId(T,col);
  for(let i=env.rows.length-1;i>=0;i--){
    const e=env.rows[i];
    if(e.row){if(e.table===T)return e.row[col];}
    else if(Object.prototype.hasOwnProperty.call(e.vrow,id))return e.vrow[id];
  }
  const hasShipRow=env.rows.some(e=>e.row&&e.table==='Shipment');
  const vr=env.rows.filter(e=>e.vrow);
  let msg=T+'['+col+'] is a whole column, so it needs a row context or an aggregation like SUM('+T+'['+col+']).';
  if(hasShipRow&&(T==='Customer'||T==='Date'))msg=T+'['+col+'] belongs to another table. Inside a row context on Shipment, fetch it with RELATED('+T+'['+col+']).';
  else if(vr.length)msg=T+'['+col+'] is not a column of the table being iterated (it has: '+Object.keys(vr[vr.length-1].vrow).join(', ')+'). Iterate a table that contains it, or wrap the measure in CALCULATE.';
  throw new DaxError(msg,node.pos,(node.end||node.pos)-node.pos);
}
function tableArg(a,env){
  const v=ev(a,env);
  if(!v||!v.isTable)throw new DaxError('A table is needed here (for example Shipment, FILTER(...), VALUES(...)).',a.pos);
  return v;
}
function withRow(env,tv,row){
  return {ctx:env.ctx,vars:env.vars,rows:env.rows.concat([tv.full?{table:tv.T,row:row}:{vrow:row}])};
}
function numVals(vals,node){return vals.filter(v=>v!=null).map(v=>numOf(v,node));}
function extremum(vals,isMax,node){
  const v=vals.filter(x=>x!=null);if(!v.length)return null;
  if(v.every(x=>typeof x==='object'&&x.isDate)){let b=v[0];for(const x of v)if(isMax?x.n>b.n:x.n<b.n)b=x;return b;}
  const nums=v.map(x=>numOf(x,node));return isMax?Math.max(...nums):Math.min(...nums);
}

/* ---------------- Filter arguments of CALCULATE ---------------- */
function isPredicate(n){return (n.t==='bin'&&['=','<>','<','>','<=','>=','&&','||','in'].includes(n.op))||(n.t==='un'&&n.op==='NOT')||(n.t==='call'&&['NOT','AND','OR'].includes(n.name));}
function splitAnd(n){return (n.t==='bin'&&n.op==='&&')?splitAnd(n.l).concat(splitAnd(n.r)):[n];}
const PRED_OK=new Set(['BLANK','TRUE','FALSE','NOT','AND','OR','DATE','YEAR','MONTH','DAY','EOMONTH','INT','MOD','ABS','ROUND']);
// a scalar sub-expression with no column, measure or table references (constants, VARs, arithmetic, IF/COALESCE/...) is fine inside a True/False filter
function scalarOnly(n){let ok=true;(function w(x){if(!x||typeof x!=='object'||!ok)return;if(x.t==='col'||x.t==='mref'||x.t==='let'||(x.t==='id'&&TABLE_LC[x.name.toLowerCase()])){ok=false;return;}for(const k of ['l','r','e'])if(x[k])w(x[k]);for(const k of ['args','items'])if(x[k])x[k].forEach(w);})(n);return ok;}
function predCols(n,out){
  switch(n.t){
    case 'col':{const r=resolveCol(n);out.set(r.T+'['+r.col+']',r);break;}
    case 'call':
      if(!PRED_OK.has(n.name)&&!scalarOnly(n))throw new DaxError("A True/False filter inside CALCULATE can't call "+n.name+"(). Use FILTER(table, condition) instead, or compute the value in a VAR first.",n.pos,n.name.length);
      n.args.forEach(a=>predCols(a,out));break;
    case 'mref':throw new DaxError("A True/False filter inside CALCULATE can't use the measure ["+n.name+"]. Store it in a VAR first, or use FILTER(table, condition).",n.pos,(n.end||n.pos)-n.pos);
    case 'bin':predCols(n.l,out);predCols(n.r,out);break;
    case 'un':predCols(n.e,out);break;
    case 'list':n.items.forEach(a=>predCols(a,out));break;
    case 'let':throw new DaxError('VAR cannot be used inside a True/False filter.',n.pos);
  }
}
function hasIdNode(n){let hit=false;(function w(x){if(!x||typeof x!=='object'||hit)return;if(x.t==='id'){hit=true;return;}for(const k of ['l','r','e','body'])if(x[k])w(x[k]);for(const k of ['args','items'])if(x[k])x[k].forEach(w);})(n);return hit;}
function predToSet(p,env){
  const cols=new Map();predCols(p,cols);
  if(cols.size===0)throw new DaxError('This True/False filter does not reference a column (for example Shipment[Mode] = "Ocean").',p.pos);
  if(cols.size>1)throw new DaxError('A True/False filter can only use one column (this one uses '+[...cols.keys()].join(' and ')+'). Split it into separate filter arguments, or use FILTER(table, condition).',p.pos);
  const {T,col}=[...cols.values()][0];
  const cacheable=!hasIdNode(p);
  if(cacheable&&p._pc&&p._pc.db===DB)return p._pc.res;
  const out=new Set();
  for(const v of allValues(T,col)){
    const e={vrow:{[colId(T,col)]:v}};
    const r=ev(p,{ctx:env.ctx,vars:env.vars,rows:env.rows.concat([e])});
    if(truthy(r))out.add(norm(v));
  }
  const res={key:T+'['+col+']',set:out};
  if(cacheable)p._pc={db:DB,res:res};
  return res;
}
function valuesOfSource(a,env){   // list or one-column table -> array of values
  const v=ev(a,env);
  if(v&&v.isList)return v.items;
  if(v&&v.isTable){
    if(v.cols.length!==1)throw new DaxError('TREATAS needs a one-column source (a list such as {"2025-01"} or VALUES(...) of one column).',a.pos);
    return v.rows.map(r=>r[v.cols[0]]);
  }
  throw new DaxError('TREATAS needs a list {...} or a one-column table as its first argument.',a.pos);
}
// collect the effect of one filter argument into mods
function collectFilter(a,env,mods,keep){
  if(a.t==='call'){
    const nm=a.name;
    if(nm==='KEEPFILTERS'){arity(a,1,1);return collectFilter(a.args[0],env,mods,true);}
    if(nm==='ALL'||nm==='REMOVEFILTERS'){
      if(a.args.length===0){Object.keys(TABLES).forEach(T=>mods.removes.push({T:T}));return;}
      for(const x of a.args){
        if(x.t==='col'){const r=resolveCol(x);mods.removes.push({T:r.T,col:r.col});}
        else if(x.t==='id'&&!(x.name.toLowerCase() in env.vars)){mods.removes.push({T:resolveTable(x.name,x)});}
        else throw new DaxError(nm+' takes a table ('+nm+'(Shipment)) or columns ('+nm+'(Shipment[Mode])).',a.pos);
      }
      return;
    }
    if(nm==='ALLEXCEPT'){
      if(a.args.length<1||a.args[0].t!=='id')throw new DaxError('ALLEXCEPT(table, column, ...) needs a table first, for example ALLEXCEPT(Customer, Customer[Country]).',a.pos);
      const T=resolveTable(a.args[0].name,a.args[0]);const keepCols=[];
      for(const x of a.args.slice(1)){
        if(x.t!=='col')throw new DaxError('ALLEXCEPT keeps columns of the table: write them as Table[Column].',x.pos);
        const r=resolveCol(x);if(r.T!==T)throw new DaxError('ALLEXCEPT('+T+', ...) can only keep columns of '+T+', but '+r.T+'['+r.col+'] belongs to '+r.T+'.',x.pos);
        keepCols.push(r.col);
      }
      mods.removes.push({T:T,except:keepCols});return;
    }
    if(nm==='ALLSELECTED'){
      if(a.args.length===0){mods.restores.push({all:true});return;}
      for(const x of a.args){
        if(x.t==='col'){const r=resolveCol(x);mods.restores.push({T:r.T,col:r.col});}
        else if(x.t==='id'&&!(x.name.toLowerCase() in env.vars)){mods.restores.push({T:resolveTable(x.name,x)});}
        else throw new DaxError('ALLSELECTED takes a table or columns.',a.pos);
      }
      return;
    }
    if(nm==='USERELATIONSHIP'){mods.rel=relFromArgs(a);return;}
    if(nm==='TREATAS'){
      if(a.args.length<2)throw new DaxError('TREATAS(source, Table[Column]) needs a source and a target column.',a.pos);
      if(a.args.length>2)throw new DaxError('TREATAS with several target columns is not supported by this trainer - use one TREATAS per column.',a.pos);
      const tc=a.args[1];if(tc.t!=='col')throw new DaxError('The second argument of TREATAS must be a column such as Date[YearMonth].',tc.pos);
      const r=resolveCol(tc);
      const set=new Set(valuesOfSource(a.args[0],env).map(norm));
      (keep?mods.keeps:mods.sets).push({key:colId(r.T,r.col),set:set});
      return;
    }
  }
  if(isPredicate(a)){
    for(const part of splitAnd(a)){const s=predToSet(part,env);(keep?mods.keeps:mods.sets).push(s);}
    return;
  }
  const v=ev(a,env);
  if(!v||!v.isTable)throw new DaxError('CALCULATE filter arguments must be a True/False test like Shipment[Mode] = "Ocean", or a table such as FILTER(...) / ALL(...) / VALUES(...) / DATESYTD(...).',a.pos);
  if(v.full){
    const key=TABLES[v.T].key;
    if(!keep)mods.removes.push({T:v.T});
    (keep?mods.keeps:mods.sets).push({key:colId(v.T,key),set:new Set(v.rows.map(r=>norm(r[key])))});
  }else{
    const real=v.cols.filter(c=>/^[A-Za-z]+\[/.test(c));
    if(real.length!==1||v.cols.length!==1)throw new DaxError('This table has '+v.cols.length+' columns ('+v.cols.join(', ')+'). The trainer can only use a one-column table (for example VALUES(Customer[Country]) or a date table) as a CALCULATE filter - filter one column at a time.',a.pos);
    (keep?mods.keeps:mods.sets).push({key:real[0],set:new Set(v.rows.map(r=>norm(r[real[0]])))});
  }
}
function relFromArgs(a){
  if(a.args.length!==2||a.args[0].t!=='col'||a.args[1].t!=='col')throw new DaxError('USERELATIONSHIP(Shipment[DeliveryDateKey], Date[DateKey]) takes the two columns of a relationship.',a.pos);
  let x=resolveCol(a.args[0]),y=resolveCol(a.args[1]);
  if(x.T==='Date'){const t=x;x=y;y=t;}
  if(x.T==='Shipment'&&y.T==='Date'&&y.col==='DateKey'){
    if(x.col==='DeliveryDateKey')return 'DeliveryDateKey';
    if(x.col==='DateKey')return null;
  }
  if(x.T==='Shipment'&&y.T==='Customer'&&x.col==='CustomerKey'&&y.col==='CustomerKey')return undefined;
  throw new DaxError('There is no relationship between '+x.T+'['+x.col+'] and '+y.T+'['+y.col+']. The model has an inactive one: Shipment[DeliveryDateKey] -> Date[DateKey].',a.pos);
}
function transitionInto(f,env){
  for(const e of env.rows){
    if(e.row){for(const c of TABLES[e.table].cols)f.set(colId(e.table,c),new Set([norm(e.row[c])]));}
    else{for(const k of Object.keys(e.vrow))if(k[0]!=='[')f.set(k,new Set([norm(e.vrow[k])]));}
  }
}
function calcContext(n,env,from){
  const base=env.ctx;
  const f=new Map(base.f);
  transitionInto(f,env);
  const mods={removes:[],sets:[],keeps:[],restores:[],rel:undefined};
  for(const a of n.args.slice(from))collectFilter(a,env,mods,false);
  let groupBy=base.groupBy;
  // Date is a marked date table: a filter on Date[Date] removes the other filters on the Date table
  if(mods.sets.some(s=>s.key==='Date[Date]'))mods.removes.push({T:'Date'});
  const drop=k=>{groupBy=groupBy.filter(g=>g!==k);};
  for(const r of mods.removes){
    for(const k of [...f.keys()]){
      let hit;
      if(r.col)hit=k===colId(r.T,r.col);
      else if(r.except)hit=k.startsWith(r.T+'[')&&!r.except.some(c=>k===colId(r.T,c));
      else hit=k.startsWith(r.T+'[');
      if(hit){f.delete(k);drop(k);}
    }
    if(!r.col&&!r.except)groupBy=groupBy.filter(g=>!g.startsWith(r.T+'['));
  }
  for(const r of mods.restores){
    const keys=new Set([...f.keys()]);
    for(const k of base.slicers.keys())keys.add(k);
    for(const k of keys){
      let hit;
      if(r.all)hit=true;else if(r.col)hit=k===colId(r.T,r.col);else hit=k.startsWith(r.T+'[');
      if(!hit)continue;
      if(base.slicers.has(k))f.set(k,new Set(base.slicers.get(k)));else f.delete(k);
      if(r.col||r.all)drop(k);
    }
    if(r.col)drop(colId(r.T,r.col));
    else if(r.all)groupBy=[];
    else groupBy=groupBy.filter(g=>!g.startsWith(r.T+'['));
  }
  const rep=new Map();
  for(const s of mods.sets)rep.set(s.key,rep.has(s.key)?inter(rep.get(s.key),s.set):s.set);
  for(const [k,s] of rep)f.set(k,s);
  for(const s of mods.keeps)f.set(s.key,f.has(s.key)?inter(f.get(s.key),s.set):s.set);
  const o={groupBy:groupBy};
  if(mods.rel!==undefined)o.rel=mods.rel;
  return mkCtx(f,base,o);
}
function fnCalculate(n,env){
  if(n.args.length<1)throw new DaxError('CALCULATE needs an expression as its first argument.',n.pos,9);
  const ctx2=calcContext(n,env,1);
  return ev(n.args[0],{ctx:ctx2,rows:[],vars:env.vars});
}
function iterate(n,env,fn){
  arity(n,2,2);
  const tv=tableArg(n.args[0],env);
  const out=[];
  for(const row of tv.rows)out.push(fn(ev(n.args[1],withRow(env,tv,row))));
  return out;
}
function iterVals(n,env){return iterate(n,env,x=>sc(x,n)).filter(x=>x!=null);}
function sumNums(v){return v.length?v.reduce((a,b)=>a+b,0):null;}

/* ---------------- Table helpers: sorting, ranking ---------------- */
function orderSpec(node,env){   // ASC / DESC / 0 / 1 -> true when descending
  if(!node||node.t==='empty')return true;
  if(node.t==='id'){const u=node.name.toUpperCase();if(u==='DESC')return true;if(u==='ASC')return false;}
  if(node.t==='num')return node.v===0;
  throw new DaxError('The order argument must be ASC or DESC.',node.pos);
}
function cmpKey(a,b){   // blank sorts lowest
  if(a==null&&b==null)return 0;if(a==null)return -1;if(b==null)return 1;
  return cmpVals(a,b);
}
function rowValues(tv,env,exprNode){return tv.rows.map(row=>sc(ev(exprNode,withRow(env,tv,row)),exprNode));}
function dimRowVal(row,T0,T,c,ctx){   // value of column T[c] for a row of table T0 (via relationships)
  if(T===T0)return row[c];
  if(T0==='Shipment'&&T==='Customer')return row._c[c];
  if(T0==='Shipment'&&T==='Date')return (ctx.rel==='DeliveryDateKey'?row._dd:row._d)[c];
  throw null;
}

/* ---------------- Date helpers ---------------- */
function dateNs(a,env,fname){
  if(a.t==='col'){
    const r=resolveCol(a);
    if(r.T==='Date'&&r.col==='Date'){const rows=visibleRows('Date',env.ctx);return rows.map(x=>x._n);}
    if(r.T==='Date'&&r.col==='DateKey')throw new DaxError(fname+' needs the Date column Date[Date], not the integer key Date[DateKey].',a.pos);
    throw new DaxError('Time-intelligence functions need Date[Date], not '+r.T+'['+r.col+']. Use the marked date table\'s Date column ('+fname+'(Date[Date], ...)).',a.pos,(a.end||a.pos)-a.pos);
  }
  const v=ev(a,env);
  if(v&&v.isTable&&v.cols.length===1&&v.cols[0]==='Date[Date]')return v.rows.map(r=>r['Date[Date]'].n).sort((x,y)=>x-y);
  throw new DaxError(fname+' needs Date[Date] or a table of dates (for example DATESYTD(Date[Date])).',a.pos);
}
function dateTable(ns){
  const lo=DB.Date[0]._n,hi=DB.Date[DB.Date.length-1]._n;
  const seen=new Set(),out=[];
  for(const n of ns){if(n>=lo&&n<=hi&&!seen.has(n)){seen.add(n);out.push(n);}}
  out.sort((x,y)=>x-y);
  return vt(['Date[Date]'],out.map(n=>({'Date[Date]':mkDate(n)})));
}
function rangeNs(a,b){const out=[];for(let n=a;n<=b;n++)out.push(n);return out;}
function intervalOf(node,fname){
  if(node&&node.t==='id'){const u=node.name.toUpperCase();if(['DAY','MONTH','QUARTER','YEAR'].includes(u))return u;}
  throw new DaxError(fname+' needs an interval: DAY, MONTH, QUARTER or YEAR.',node&&node.pos);
}
const IVMONTHS={MONTH:1,QUARTER:3,YEAR:12};
function shiftDates(ns,k,iv,node){
  if(!ns.length)return [];
  if(iv==='DAY')return ns.map(n=>n+k);
  const months=k*IVMONTHS[iv],lo=ns[0],hi=ns[ns.length-1];
  if(ns.length!==hi-lo+1)throw new DaxError('DATEADD / SAMEPERIODLASTYEAR need a contiguous range of dates (the filter on the Date table has gaps).',node&&node.pos);
  if(lo===somN(lo)&&hi===eomN(hi))return rangeNs(somN(shiftMonths(lo,months)),eomN(shiftMonths(hi,months)));   // whole months stay whole months
  return ns.map(n=>shiftMonths(n,months));
}
function scalarDate(a,env,fname,allowBlank){
  const v=sc(ev(a,env),a);
  if(v==null&&allowBlank)return null;
  if(v&&typeof v==='object'&&v.isDate)return v.n;
  throw new DaxError(fname+' needs a date here (for example DATE(2025,1,1) or MAX(Date[Date])).',a.pos);
}
function yearEndArg(a,env){
  if(!a||a.t==='empty')return null;
  const s=sc(ev(a,env),a);
  if(typeof s!=='string'||!/^\d\d-\d\d$/.test(s))throw new DaxError('The year-end argument must be text such as "09-30" (month-day).',a.pos);
  return s;
}
function tiYTD(n,env,fname,kind){
  const ns=dateNs(n.args[0],env,fname);
  if(!ns.length)return dateTable([]);
  const last=ns[ns.length-1];
  let start;
  if(kind==='Y')start=yearStartN(last,yearEndArg(n.args[1],env));
  else if(kind==='Q')start=sqN(last);else start=somN(last);
  return dateTable(rangeNs(start,last));
}

/* ---------------- Functions ---------------- */
const FN={
  SUM(n,env){arity(n,1,1);const {T,col}=needCol(n.args[0],'SUM');return sumNums(numVals(colVals(T,col,env.ctx),n));},
  AVERAGE(n,env){arity(n,1,1);const {T,col}=needCol(n.args[0],'AVERAGE');const v=numVals(colVals(T,col,env.ctx),n);return v.length?v.reduce((a,b)=>a+b,0)/v.length:null;},
  MIN(n,env){if(n.args.length===2){const a=sc(ev(n.args[0],env)),b=sc(ev(n.args[1],env));return a==null?b:(b==null?a:Math.min(a,b));}
    arity(n,1,1);const {T,col}=needCol(n.args[0],'MIN');return extremum(colVals(T,col,env.ctx),false,n);},
  MAX(n,env){if(n.args.length===2){const a=sc(ev(n.args[0],env)),b=sc(ev(n.args[1],env));return a==null?b:(b==null?a:Math.max(a,b));}
    arity(n,1,1);const {T,col}=needCol(n.args[0],'MAX');return extremum(colVals(T,col,env.ctx),true,n);},
  COUNT(n,env){arity(n,1,1);const {T,col}=needCol(n.args[0],'COUNT');const k=colVals(T,col,env.ctx).filter(v=>v!=null).length;return k||null;},   // COUNT of nothing is BLANK, as in DAX
  COUNTA(n,env){return FN.COUNT(n,env);},
  COUNTBLANK(n,env){arity(n,1,1);const {T,col}=needCol(n.args[0],'COUNTBLANK');return colVals(T,col,env.ctx).filter(v=>v==null||v==='').length;},
  DISTINCTCOUNT(n,env){arity(n,1,1);const {T,col}=needCol(n.args[0],'DISTINCTCOUNT');const k=new Set(colVals(T,col,env.ctx).map(norm)).size;return k||null;},
  COUNTROWS(n,env){arity(n,1,1);const k=tableArg(n.args[0],env).rows.length;return k||null;},   // COUNTROWS of an empty table is BLANK, as in DAX
  ISEMPTY(n,env){arity(n,1,1);return tableArg(n.args[0],env).rows.length===0;},
  SUMX(n,env){return sumNums(iterVals(n,env).map(x=>numOf(x,n)));},
  AVERAGEX(n,env){const v=iterVals(n,env).map(x=>numOf(x,n));return v.length?v.reduce((a,b)=>a+b,0)/v.length:null;},
  MAXX(n,env){return extremum(iterVals(n,env),true,n);},
  MINX(n,env){return extremum(iterVals(n,env),false,n);},
  COUNTX(n,env){return iterVals(n,env).length||null;},
  CONCATENATEX(n,env){
    arity(n,2,Infinity);
    const tv=tableArg(n.args[0],env);
    const delim=n.args[2]&&n.args[2].t!=='empty'?String(sc(ev(n.args[2],env),n.args[2])):'';
    let items=tv.rows.map((row,i)=>{const e=withRow(env,tv,row);return {s:fmtText(sc(ev(n.args[1],e),n)),keys:[],i:i,e:e};});
    const ords=[];
    for(let k=3;k<n.args.length;k+=2)ords.push({expr:n.args[k],desc:orderSpec(n.args[k+1],env)});
    if(ords.length){
      items.forEach(it=>{it.keys=ords.map(o=>sc(ev(o.expr,it.e),o.expr));});
      items.sort((a,b)=>{for(let k=0;k<ords.length;k++){const c=cmpKey(a.keys[k],b.keys[k]);if(c)return ords[k].desc?-c:c;}return a.i-b.i;});
    }
    return items.length?items.map(x=>x.s).join(delim):'';
  },
  FILTER(n,env){
    arity(n,2,2);
    const tv=tableArg(n.args[0],env);
    const rows=tv.rows.filter(row=>truthy(sc(ev(n.args[1],withRow(env,tv,row)),n)));
    return {isTable:true,full:tv.full,T:tv.T,cols:tv.cols,rows:rows};
  },
  ALL(n,env){
    arity(n,0,Infinity);
    if(n.args.length===0)throw new DaxError('ALL() with no arguments only works as a CALCULATE filter argument.',n.pos,3);
    const x=n.args[0];
    if(x.t==='col'){
      const rs=n.args.map(a=>{if(a.t!=='col')throw new DaxError('ALL takes either one table or one or more columns of the same table.',n.pos,3);return resolveCol(a);});
      const T=rs[0].T;if(rs.some(r=>r.T!==T))throw new DaxError('ALL(col1, col2, ...) needs columns from the same table.',n.pos,3);
      if(rs.length===1){const {col}=rs[0];return vt([colId(T,col)],allValues(T,col).map(v=>({[colId(T,col)]:v})));}
      const seen=new Set(),rows=[];
      for(const r of DB[T]){const key=rs.map(c=>String(norm(r[c.col]))).join('\u0002');if(!seen.has(key)){seen.add(key);const o={};rs.forEach(c=>o[colId(T,c.col)]=r[c.col]);rows.push(o);}}
      return vt(rs.map(c=>colId(T,c.col)),rows);
    }
    if(x.t==='id'&&!(x.name.toLowerCase() in env.vars)){const T=resolveTable(x.name,x);return ft(T,DB[T]);}
    throw new DaxError('ALL takes a table (ALL(Shipment)) or columns (ALL(Shipment[Mode])).',n.pos,3);
  },
  ALLSELECTED(n,env){
    arity(n,1,1);const x=n.args[0];
    const mods={removes:[],sets:[],keeps:[],restores:[],rel:undefined};
    collectFilter(n,env,mods,false);
    const f=new Map(env.ctx.f);
    for(const r of mods.restores){
      for(const k of [...new Set([...f.keys(),...env.ctx.slicers.keys()])]){
        const hit=r.all||(r.col?k===colId(r.T,r.col):k.startsWith(r.T+'['));
        if(!hit)continue;
        if(env.ctx.slicers.has(k))f.set(k,new Set(env.ctx.slicers.get(k)));else f.delete(k);
      }
    }
    const c2=mkCtx(f,env.ctx,{});
    if(x.t==='col'){const {T,col}=resolveCol(x);return vt([colId(T,col)],distinctVals(T,col,c2).map(v=>({[colId(T,col)]:v})));}
    const T=resolveTable(x.name,x);return ft(T,visibleRows(T,c2));
  },
  ALLEXCEPT(n){throw new DaxError('ALLEXCEPT only works as a filter argument of CALCULATE, e.g. CALCULATE(..., ALLEXCEPT(Customer, Customer[Country])).',n.pos,9);},
  VALUES(n,env){
    arity(n,1,1);const x=n.args[0];
    if(x.t==='col'){const {T,col}=resolveCol(x);return vt([colId(T,col)],distinctVals(T,col,env.ctx).map(v=>({[colId(T,col)]:v})));}
    return tableArg(x,env);
  },
  DISTINCT(n,env){return FN.VALUES(n,env);},
  CALCULATE(n,env){return fnCalculate(n,env);},
  CALCULATETABLE(n,env){
    if(n.args.length<1)throw new DaxError('CALCULATETABLE needs a table as its first argument.',n.pos,14);
    const ctx2=calcContext(n,env,1);
    return tableArg(n.args[0],{ctx:ctx2,rows:[],vars:env.vars});
  },
  KEEPFILTERS(n){throw new DaxError('KEEPFILTERS only works as a filter argument of CALCULATE, e.g. CALCULATE(..., KEEPFILTERS(Shipment[Ffe] > 0)).',n.pos,11);},
  REMOVEFILTERS(n){throw new DaxError('REMOVEFILTERS only works as a filter argument of CALCULATE.',n.pos,13);},
  USERELATIONSHIP(n){throw new DaxError('USERELATIONSHIP only works inside CALCULATE (or CALCULATETABLE) as a filter argument.',n.pos,15);},
  TREATAS(n){throw new DaxError('TREATAS is used as a filter argument of CALCULATE, e.g. CALCULATE(SUM(Target[TargetRevenue]), TREATAS(VALUES(Date[YearMonth]), Target[YearMonth])).',n.pos,7);},
  RELATED(n,env){
    arity(n,1,1);const x=n.args[0];
    if(x.t!=='col')throw new DaxError('RELATED takes a column, e.g. RELATED(Customer[Segment]).',n.pos,7);
    const {T,col}=resolveCol(x);
    if(T==='Shipment')throw new DaxError('RELATED fetches a column from the ONE side of a relationship (Customer or Date). Shipment is the many side, so just use '+T+'['+col+'] directly in a row context.',n.pos,7);
    if(T==='Target')throw new DaxError('Target has no relationship to the other tables, so RELATED cannot reach it. Use TREATAS inside CALCULATE.',n.pos,7);
    let e=null;for(let i=env.rows.length-1;i>=0;i--)if(env.rows[i].row&&env.rows[i].table==='Shipment'){e=env.rows[i];break;}
    if(!e)throw new DaxError('RELATED needs a row context on Shipment - use it inside an iterator such as SUMX(Shipment, ...) or FILTER(Shipment, ...).',n.pos,7);
    const dr=T==='Customer'?e.row._c:(env.ctx&&env.ctx.rel==='DeliveryDateKey'?e.row._dd:e.row._d);
    return dr?dr[col]:null;
  },
  RELATEDTABLE(n,env){
    arity(n,1,1);
    if(!env.rows.length)throw new DaxError('RELATEDTABLE needs a row context (for example inside SUMX(Customer, ...)).',n.pos,12);
    const f=new Map(env.ctx.f);transitionInto(f,env);
    return tableArg(n.args[0],{ctx:mkCtx(f,env.ctx,{}),rows:[],vars:env.vars});
  },
  ADDCOLUMNS(n,env){
    arity(n,3,Infinity);
    if(n.args.length%2!==1)throw new DaxError('ADDCOLUMNS(table, "name", expression, ...) takes a name and an expression for each new column.',n.pos,10);
    const tv=tableArg(n.args[0],env);
    const names=[];
    for(let k=1;k<n.args.length;k+=2){
      if(n.args[k].t!=='str')throw new DaxError('The name of an ADDCOLUMNS column must be text in double quotes, e.g. "Revenue".',n.args[k].pos);
      names.push('['+n.args[k].v.toLowerCase()+']');
    }
    const rows=tv.rows.map(row=>{
      const copy=Object.assign({},row);
      for(let k=1,j=0;k<n.args.length;k+=2,j++){
        const e=withRow(env,tv,copy);
        copy[names[j]]=sc(ev(n.args[k+1],e),n.args[k+1]);
      }
      return copy;
    });
    return {isTable:true,full:tv.full,T:tv.T,cols:tv.cols.concat(names),rows:rows};
  },
  SUMMARIZE(n,env){
    arity(n,2,Infinity);
    const tv=tableArg(n.args[0],env);
    const cols=[];
    for(const a of n.args.slice(1)){
      if(a.t!=='col')throw new DaxError('SUMMARIZE in this trainer takes only group-by columns (Table[Column]). Add calculated columns with ADDCOLUMNS(SUMMARIZE(...), "Name", expression).',a.pos);
      cols.push(resolveCol(a));
    }
    if(!tv.full)throw new DaxError('SUMMARIZE needs a table such as Shipment, Customer or FILTER(Shipment, ...) as its first argument.',n.args[0].pos);
    const seen=new Set(),rows=[];
    for(const row of tv.rows){
      const o={};let key='';
      for(const c of cols){
        let v;try{v=dimRowVal(row,tv.T,c.T,c.col,env.ctx);}
        catch(e){throw new DaxError('SUMMARIZE over '+tv.T+' cannot group by '+c.T+'['+c.col+'] in this trainer (group by columns of '+tv.T+' or of the tables on its one-side).',n.pos,9);}
        o[colId(c.T,c.col)]=v;key+=String(norm(v))+'\u0002';
      }
      if(!seen.has(key)){seen.add(key);rows.push(o);}
    }
    const ids=cols.map(c=>colId(c.T,c.col));
    rows.sort((a,b)=>{for(const id of ids){const c=cmpKey(a[id],b[id]);if(c)return c;}return 0;});
    return vt(ids,rows);
  },
  TOPN(n,env){
    arity(n,2,Infinity);
    const cnt=numOf(sc(ev(n.args[0],env),n.args[0]),n);
    const tv=tableArg(n.args[1],env);
    const ords=[];
    for(let k=2;k<n.args.length;k+=2)ords.push({expr:n.args[k],desc:orderSpec(n.args[k+1],env)});
    if(!ords.length)throw new DaxError('TOPN(n, table, orderByExpression [, ASC|DESC]) needs an expression to rank by.',n.pos,4);
    if(cnt==null||cnt<=0)return {isTable:true,full:tv.full,T:tv.T,cols:tv.cols,rows:[]};
    const items=tv.rows.map((row,i)=>{const e=withRow(env,tv,row);return {row:row,i:i,keys:ords.map(o=>sc(ev(o.expr,e),o.expr))};});
    const cmp=(a,b)=>{for(let k=0;k<ords.length;k++){const c=cmpKey(a.keys[k],b.keys[k]);if(c)return ords[k].desc?-c:c;}return 0;};
    items.sort((a,b)=>cmp(a,b)||a.i-b.i);
    let rows;
    if(items.length<=cnt)rows=items;
    else{const cut=items[Math.floor(cnt)-1];rows=items.filter((it,idx)=>idx<Math.floor(cnt)||cmp(it,cut)===0);}
    return {isTable:true,full:tv.full,T:tv.T,cols:tv.cols,rows:rows.map(x=>x.row)};
  },
  RANKX(n,env){
    arity(n,2,6);
    const tv=tableArg(n.args[0],env);
    const expr=n.args[1];
    const valNode=n.args[2]&&n.args[2].t!=='empty'?n.args[2]:null;
    const desc=orderSpec(n.args[3],env);
    let dense=false;
    const tn=n.args[4];
    if(tn&&tn.t!=='empty'){
      if(tn.t==='id'&&tn.name.toUpperCase()==='DENSE')dense=true;
      else if(!(tn.t==='id'&&tn.name.toUpperCase()==='SKIP'))throw new DaxError('The ties argument of RANKX must be SKIP or DENSE.',tn.pos);
    }
    const val=sc(valNode?ev(valNode,env):ev(expr,env),expr);
    if(val==null)return null;
    const vals=rowValues(tv,env,expr).filter(v=>v!=null);
    const better=vals.filter(v=>desc?cmpVals(v,val)>0:cmpVals(v,val)<0);
    if(!dense)return better.length+1;
    return new Set(better.map(norm)).size+1;
  },
  DIVIDE(n,env){
    arity(n,2,3);
    const a=numOf(sc(ev(n.args[0],env),n),n),b=numOf(sc(ev(n.args[1],env),n),n);
    if(b==null||b===0)return n.args.length===3?sc(ev(n.args[2],env),n):null;
    if(a==null)return null;
    return a/b;
  },
  IF(n,env){
    arity(n,2,3);
    const c=sc(ev(n.args[0],env),n);
    if(truthy(c))return sc(ev(n.args[1],env),n);
    return n.args.length===3?sc(ev(n.args[2],env),n):null;
  },
  SWITCH(n,env){
    arity(n,3,Infinity);
    const v=sc(ev(n.args[0],env),n.args[0]);
    let k=1;
    for(;k+1<n.args.length;k+=2){
      const t=sc(ev(n.args[k],env),n.args[k]);
      const hit=(typeof v==='boolean'||typeof t==='boolean')?(v===t):cmpVals(v,t,n)===0;
      if(hit)return sc(ev(n.args[k+1],env),n.args[k+1]);
    }
    if(k<n.args.length)return sc(ev(n.args[k],env),n.args[k]);
    return null;
  },
  COALESCE(n,env){arity(n,2,Infinity);for(const a of n.args){const v=sc(ev(a,env),a);if(v!=null)return v;}return null;},
  AND(n,env){arity(n,2,2);return truthy(sc(ev(n.args[0],env),n))&&truthy(sc(ev(n.args[1],env),n));},
  OR(n,env){arity(n,2,2);return truthy(sc(ev(n.args[0],env),n))||truthy(sc(ev(n.args[1],env),n));},
  NOT(n,env){arity(n,1,1);return !truthy(sc(ev(n.args[0],env),n));},
  BLANK(n){arity(n,0,0);return null;},
  TRUE(n){arity(n,0,0);return true;},
  FALSE(n){arity(n,0,0);return false;},
  ISBLANK(n,env){arity(n,1,1);return sc(ev(n.args[0],env),n)==null;},
  ABS(n,env){arity(n,1,1);const v=numOf(sc(ev(n.args[0],env),n),n);return v==null?null:Math.abs(v);},
  ROUND(n,env){arity(n,2,2);const v=numOf(sc(ev(n.args[0],env),n),n),d=numOf(sc(ev(n.args[1],env),n),n)||0;if(v==null)return null;const m=Math.pow(10,d);return Math.sign(v)*Math.round(Math.abs(v)*m+1e-9)/m;},
  INT(n,env){arity(n,1,1);const v=numOf(sc(ev(n.args[0],env),n),n);return v==null?null:Math.floor(v);},
  MOD(n,env){arity(n,2,2);const a=numOf(sc(ev(n.args[0],env),n),n),b=numOf(sc(ev(n.args[1],env),n),n);if(a==null||b==null)return null;if(b===0)throw new DaxError('MOD by zero is an error in DAX.',n.pos,3);return a-b*Math.floor(a/b);},
  HASONEVALUE(n,env){arity(n,1,1);const {T,col}=needCol(n.args[0],'HASONEVALUE');return distinctVals(T,col,env.ctx).length===1;},
  SELECTEDVALUE(n,env){
    arity(n,1,2);const {T,col}=needCol(n.args[0],'SELECTEDVALUE');
    const d=distinctVals(T,col,env.ctx);
    if(d.length===1)return d[0];
    return n.args.length===2?sc(ev(n.args[1],env),n.args[1]):null;
  },
  ISINSCOPE(n,env){arity(n,1,1);const {T,col}=needCol(n.args[0],'ISINSCOPE');return env.ctx.groupBy.includes(colId(T,col));},
  ISFILTERED(n,env){arity(n,1,1);const {T,col}=needCol(n.args[0],'ISFILTERED');return env.ctx.f.has(colId(T,col));},
  /* ----- dates ----- */
  DATE(n,env){arity(n,3,3);const [y,m,d]=n.args.map(a=>numOf(sc(ev(a,env),a),n));if(y==null||m==null||d==null)return null;return mkDate(Math.floor(Date.UTC(y,m-1,d)/DAY_MS));},
  YEAR(n,env){arity(n,1,1);const v=sc(ev(n.args[0],env),n);if(v==null)return null;if(!(v.isDate))throw new DaxError('YEAR needs a date.',n.pos,4);return ymdOf(v.n).y;},
  MONTH(n,env){arity(n,1,1);const v=sc(ev(n.args[0],env),n);if(v==null)return null;if(!(v.isDate))throw new DaxError('MONTH needs a date.',n.pos,5);return ymdOf(v.n).m;},
  DAY(n,env){arity(n,1,1);const v=sc(ev(n.args[0],env),n);if(v==null)return null;if(!(v.isDate))throw new DaxError('DAY needs a date.',n.pos,3);return ymdOf(v.n).d;},
  QUARTER(n,env){arity(n,1,1);const v=sc(ev(n.args[0],env),n);if(v==null)return null;if(!(v.isDate))throw new DaxError('QUARTER needs a date.',n.pos,7);return Math.floor((ymdOf(v.n).m-1)/3)+1;},
  EOMONTH(n,env){arity(n,2,2);const v=sc(ev(n.args[0],env),n),k=numOf(sc(ev(n.args[1],env),n),n);if(v==null)return null;if(!v.isDate)throw new DaxError('EOMONTH needs a date as its first argument.',n.pos,7);return mkDate(eomN(shiftMonths(somN(v.n),k)));},
  DATESYTD(n,env){arity(n,1,2);return tiYTD(n,env,'DATESYTD','Y');},
  DATESQTD(n,env){arity(n,1,1);return tiYTD(n,env,'DATESQTD','Q');},
  DATESMTD(n,env){arity(n,1,1);return tiYTD(n,env,'DATESMTD','M');},
  TOTALYTD(n,env){return totalTI(n,env,'DATESYTD');},
  TOTALQTD(n,env){return totalTI(n,env,'DATESQTD');},
  TOTALMTD(n,env){return totalTI(n,env,'DATESMTD');},
  DATEADD(n,env){arity(n,3,3);const ns=dateNs(n.args[0],env,'DATEADD');const k=numOf(sc(ev(n.args[1],env),n.args[1]),n);return dateTable(shiftDates(ns,k,intervalOf(n.args[2],'DATEADD'),n));},
  SAMEPERIODLASTYEAR(n,env){arity(n,1,1);return dateTable(shiftDates(dateNs(n.args[0],env,'SAMEPERIODLASTYEAR'),-1,'YEAR',n));},
  PARALLELPERIOD(n,env){
    arity(n,3,3);const ns=dateNs(n.args[0],env,'PARALLELPERIOD');const k=numOf(sc(ev(n.args[1],env),n.args[1]),n);const iv=intervalOf(n.args[2],'PARALLELPERIOD');
    if(!ns.length)return dateTable([]);
    if(iv==='DAY')return dateTable(ns.map(x=>x+k));
    const months=k*IVMONTHS[iv],lo=shiftMonths(ns[0],months),hi=shiftMonths(ns[ns.length-1],months);
    if(iv==='MONTH')return dateTable(rangeNs(somN(lo),eomN(hi)));
    if(iv==='QUARTER')return dateTable(rangeNs(sqN(lo),eqN(hi)));
    return dateTable(rangeNs(epochDay(ymdOf(lo).y,1,1),epochDay(ymdOf(hi).y,12,31)));
  },
  DATESBETWEEN(n,env){
    arity(n,3,3);dateNs(n.args[0],env,'DATESBETWEEN');
    const s=scalarDate(n.args[1],env,'DATESBETWEEN',true),e=scalarDate(n.args[2],env,'DATESBETWEEN',true);
    const lo=s==null?DB.Date[0]._n:s,hi=e==null?DB.Date[DB.Date.length-1]._n:e;
    return dateTable(rangeNs(Math.max(lo,DB.Date[0]._n),Math.min(hi,DB.Date[DB.Date.length-1]._n)));
  },
  DATESINPERIOD(n,env){
    arity(n,4,4);dateNs(n.args[0],env,'DATESINPERIOD');
    const st=scalarDate(n.args[1],env,'DATESINPERIOD',false);
    const k=numOf(sc(ev(n.args[2],env),n.args[2]),n);const iv=intervalOf(n.args[3],'DATESINPERIOD');
    let lo,hi;
    if(iv==='DAY'){if(k<0){lo=st+k+1;hi=st;}else{lo=st;hi=st+k-1;}}
    else{
      const months=k*IVMONTHS[iv];const isEom=st===eomN(st);
      const sh=isEom?eomN(shiftMonths(st,months)):shiftMonths(st,months);
      if(k<0){lo=sh+1;hi=st;}else{lo=st;hi=sh-1;}
    }
    return dateTable(rangeNs(Math.max(lo,DB.Date[0]._n),Math.min(hi,DB.Date[DB.Date.length-1]._n)));
  },
  PREVIOUSMONTH(n,env){arity(n,1,1);const ns=dateNs(n.args[0],env,'PREVIOUSMONTH');if(!ns.length)return dateTable([]);const s=shiftMonths(somN(ns[0]),-1);return dateTable(rangeNs(s,eomN(s)));},
  NEXTMONTH(n,env){arity(n,1,1);const ns=dateNs(n.args[0],env,'NEXTMONTH');if(!ns.length)return dateTable([]);const s=shiftMonths(somN(ns[ns.length-1]),1);return dateTable(rangeNs(s,eomN(s)));},
  PREVIOUSQUARTER(n,env){arity(n,1,1);const ns=dateNs(n.args[0],env,'PREVIOUSQUARTER');if(!ns.length)return dateTable([]);const s=shiftMonths(sqN(ns[0]),-3);return dateTable(rangeNs(s,eqN(s)));},
  PREVIOUSYEAR(n,env){
    arity(n,1,2);const ns=dateNs(n.args[0],env,'PREVIOUSYEAR');if(!ns.length)return dateTable([]);
    const ye=yearEndArg(n.args[1],env);const last=ns[ns.length-1];
    const cur=yearStartN(last,ye);                     // start of the (fiscal) year containing the last date
    const prevStart=yearStartN(cur-1,ye);
    return dateTable(rangeNs(prevStart,cur-1));
  },
  FIRSTDATE(n,env){arity(n,1,1);const ns=dateNs(n.args[0],env,'FIRSTDATE');return dateTable(ns.length?[ns[0]]:[]);},
  LASTDATE(n,env){arity(n,1,1);const ns=dateNs(n.args[0],env,'LASTDATE');return dateTable(ns.length?[ns[ns.length-1]]:[]);}
};
// TOTALYTD(expr, dates, [filter], [yearEnd]) == CALCULATE(expr, DATESYTD(dates [, yearEnd]), filter)
function totalTI(n,env,inner){
  arity(n,2,4);
  const nm=n.name;let filter=null,ye=null;
  for(const a of n.args.slice(2)){
    if(a.t==='str'){if(inner!=='DATESYTD')throw new DaxError(nm+' takes no year-end argument.',a.pos);ye=a;}
    else filter=a;
  }
  const dargs=[n.args[1]];if(ye)dargs.push(ye);
  const calc={t:'call',name:'CALCULATE',raw:'CALCULATE',pos:n.pos,end:n.end,args:[n.args[0],{t:'call',name:inner,raw:inner,pos:n.pos,end:n.end,args:dargs}].concat(filter?[filter]:[])};
  return fnCalculate(calc,env);
}

function evalLibMeasure(m,n,env){
  const ast=parseCached(m.code);
  if(!env.rows.length){
    const c=env.ctx.cache;c.m=c.m||{};
    if(m.name in c.m)return c.m[m.name];
    return c.m[m.name]=ev(ast,{ctx:env.ctx,rows:[],vars:{}});
  }
  // implicit CALCULATE: the current row context(s) become filters
  const f=new Map(env.ctx.f);transitionInto(f,env);
  return ev(ast,{ctx:mkCtx(f,env.ctx,{}),rows:[],vars:{}});
}
function ev(n,env){
  switch(n.t){
    case 'num':case 'str':case 'bool':return n.v;
    case 'empty':return null;
    case 'list':return {isList:true,items:n.items.map(x=>sc(ev(x,env),x))};
    case 'col':return lookupRow(env,n);
    case 'mref':{
      const key='['+n.name.toLowerCase()+']';
      for(let i=env.rows.length-1;i>=0;i--){
        const e=env.rows[i],src=e.row||e.vrow;
        if(src&&Object.prototype.hasOwnProperty.call(src,key))return src[key];
      }
      const m=MEASURE_LC[n.name.toLowerCase()];
      if(m)return evalLibMeasure(m,n,env);
      const hit=Object.keys(TABLES).filter(T=>TABLES[T].cols.some(c=>c.toLowerCase()===n.name.toLowerCase()));
      const sug=nearest(n.name,MEASURES.map(x=>x.name));
      throw new DaxError("There is no measure named ["+n.name+"]."+(hit.length?" ["+n.name+"] is a column - columns need their table name: "+hit[0]+"["+TABLES[hit[0]].cols.find(c=>c.toLowerCase()===n.name.toLowerCase())+"].":(sug?" Did you mean ["+sug+"]?":" Columns are written Table[Column], e.g. Shipment[Revenue]; the available measures are listed under \"Measures you can use\".")),n.pos,n.end-n.pos);
    }
    case 'id':{
      const k=n.name.toLowerCase();
      if(k in env.vars)return env.vars[k];
      const T=TABLE_LC[k];
      if(T)return ft(T,visibleRows(T,env.ctx));
      const all=Object.keys(TABLES).concat(Object.keys(env.vars));
      const s=nearest(n.name,all);
      throw new DaxError("Unknown name '"+n.name+"'."+(s?" Did you mean "+s+"?":""),n.pos,n.name.length);
    }
    case 'let':{
      const vars=Object.create(env.vars);
      const e2={ctx:env.ctx,rows:env.rows,vars:vars};
      for(const v of n.vars)vars[v.name.toLowerCase()]=ev(v.e,e2);
      return ev(n.body,e2);
    }
    case 'un':{if(n.op==='NOT')return !truthy(sc(ev(n.e,env),n));const v=numOf(sc(ev(n.e,env),n),n);return v==null?null:-v;}
    case 'call':{
      const f=FN[n.name];
      if(!f){const s=nearest(n.name,Object.keys(FN));throw new DaxError("Unknown function "+n.raw+"()."+(s?" Did you mean "+s+"()?":" This trainer supports: "+Object.keys(FN).join(', ')+"."),n.pos,n.raw.length);}
      return f(n,env);
    }
    case 'bin':{
      const op=n.op;
      if(op==='&&')return truthy(sc(ev(n.l,env),n))&&truthy(sc(ev(n.r,env),n));
      if(op==='||')return truthy(sc(ev(n.l,env),n))||truthy(sc(ev(n.r,env),n));
      if(op==='in'){
        const l=sc(ev(n.l,env),n),r=ev(n.r,env);
        let items;
        if(r&&r.isList)items=r.items;
        else if(r&&r.isTable&&r.cols.length===1)items=r.rows.map(x=>x[r.cols[0]]);
        else throw new DaxError('IN needs a list such as {"Ocean","Air"} or a one-column table on its right.',n.pos,2);
        return items.some(x=>cmpVals(l,x,n)===0);
      }
      const l=sc(ev(n.l,env),n.l),r=sc(ev(n.r,env),n.r);
      switch(op){
        case '=':return cmpVals(l,r,n)===0;
        case '<>':return cmpVals(l,r,n)!==0;
        case '<':return cmpVals(l,r,n)<0;
        case '>':return cmpVals(l,r,n)>0;
        case '<=':return cmpVals(l,r,n)<=0;
        case '>=':return cmpVals(l,r,n)>=0;
        case '&':return fmtText(l)+fmtText(r);
        default:{
          const ld=l&&typeof l==='object'&&l.isDate, rd=r&&typeof r==='object'&&r.isDate;
          if(ld||rd){
            if(op==='-'&&ld&&rd)return l.n-r.n;
            if(op==='+'&&ld&&!rd&&typeof r!=='string')return mkDate(l.n+(numOf(r,n)||0));
            if(op==='+'&&rd&&!ld&&typeof l!=='string')return mkDate(r.n+(numOf(l,n)||0));
            if(op==='-'&&ld&&!rd&&typeof r!=='string')return mkDate(l.n-(numOf(r,n)||0));
            throw new DaxError('These operands cannot be combined with '+op+': date - date gives days, date +/- days gives a date.',n.pos,1);
          }
          const a=numOf(l,n),b=numOf(r,n);
          if(op==='/'){
            if(b===0||b==null){if(a==null)return null;return a===0?NaN:(a>0?Infinity:-Infinity);}
            if(a==null)return null;
            return a/b;
          }
          if(a==null&&b==null)return null;
          const x=a||0,y=b||0;
          return op==='+'?x+y:(op==='-'?x-y:x*y);
        }
      }
    }
  }
  throw new DaxError('Unsupported expression',n.pos);
}
function fmtText(v){
  if(v==null)return '';
  if(typeof v==='boolean')return v?'TRUE':'FALSE';
  return String(v);
}
// rc: {slicers:[{col,vals}], rowFilters:[{col,vals}], groupBy:['Table[Col]']}  (an array is read as rowFilters, for convenience)
function evalMeasure(code,rc){
  const ast=parseCached(code);
  const ctx=baseCtx(Array.isArray(rc)?{rowFilters:rc}:rc);
  const v=ev(ast,{ctx:ctx,rows:[],vars:{}});
  if(v&&v.isTable)throw new DaxError('A measure must return one value, but this returns a table. Wrap it in an aggregation such as COUNTROWS(...).',0);
  if(v&&v.isList)throw new DaxError('A measure must return one value, not a list.',0);
  return v;
}
function fmt(v){
  if(v==null)return '(blank)';
  if(typeof v==='boolean')return v?'TRUE':'FALSE';
  if(typeof v==='object'&&v.isDate)return String(v);
  if(typeof v==='number'){
    if(Number.isNaN(v))return 'NaN';
    if(!Number.isFinite(v))return v>0?'Infinity':'-Infinity';
    return v.toLocaleString('en-US',{maximumFractionDigits:4});
  }
  return String(v);
}
