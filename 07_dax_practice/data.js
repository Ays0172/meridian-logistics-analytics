"use strict";
/* =====================================================================
   data.js - seeded PRNG, date helpers, schema, random data, parameters,
   base-measure library and the oracle helper object H.
   Loaded first; everything here is a plain global (no modules, works from file://).
   ===================================================================== */
function mulberry32(a){return function(){a|=0;a=a+0x6D2B79F5|0;let t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;};}

/* ---------- dates: a Date value is an interned DateVal wrapping an epoch-day number ---------- */
const DAY_MS=86400000;
function epochDay(y,m,d){return Math.floor(Date.UTC(y,m-1,d)/DAY_MS);}
function ymdOf(n){const t=new Date(n*DAY_MS);return {y:t.getUTCFullYear(),m:t.getUTCMonth()+1,d:t.getUTCDate()};}
function isoOf(n){const o=ymdOf(n);return o.y+'-'+String(o.m).padStart(2,'0')+'-'+String(o.d).padStart(2,'0');}
function daysInMonth(y,m){return new Date(Date.UTC(y,m,0)).getUTCDate();}
function dateKeyOfN(n){const o=ymdOf(n);return o.y*10000+o.m*100+o.d;}
function nOfDateKey(k){return epochDay(Math.floor(k/10000),Math.floor(k/100)%100,k%100);}
function shiftMonths(n,k){const o=ymdOf(n);const t=o.y*12+(o.m-1)+k;const y=Math.floor(t/12),m=((t%12)+12)%12+1;return epochDay(y,m,Math.min(o.d,daysInMonth(y,m)));}
function eomN(n){const o=ymdOf(n);return epochDay(o.y,o.m,daysInMonth(o.y,o.m));}
function somN(n){const o=ymdOf(n);return epochDay(o.y,o.m,1);}
function sqN(n){const o=ymdOf(n);return epochDay(o.y,Math.floor((o.m-1)/3)*3+1,1);}   // start of calendar quarter
function eqN(n){return eomN(shiftMonths(sqN(n),2));}                                     // end of calendar quarter
// first day of the year-period that contains n, for a year ending on "MM-DD" (default calendar year)
function yearStartN(n,ye){
  const mm=ye?parseInt(ye.slice(0,2),10):12, dd=ye?parseInt(ye.slice(3,5),10):31;
  const y=ymdOf(n).y;
  const endThis=epochDay(y,mm,Math.min(dd,daysInMonth(y,mm)));
  if(n<=endThis)return epochDay(y-1,mm,Math.min(dd,daysInMonth(y-1,mm)))+1;
  return endThis+1;
}
class DateVal{constructor(n){this.n=n;this.isDate=true;}valueOf(){return this.n;}toString(){return isoOf(this.n);}}
const _DV=new Map();
function mkDate(n){let d=_DV.get(n);if(!d){d=new DateVal(n);_DV.set(n,d);}return d;}

/* ---------- schema ---------- */
const TABLES={
  Shipment:{key:'ShipmentID',cols:['ShipmentID','CustomerKey','Mode','Region','Revenue','Cost','Ffe','Weight','IsOnTime','DateKey','DeliveryDateKey']},
  Customer:{key:'CustomerKey',cols:['CustomerKey','CustomerName','Segment','Country','AccountManager']},
  Date:{key:'DateKey',cols:['DateKey','Date','Year','MonthNo','MonthName','YearMonth','Quarter','FiscalYear','DayOfWeek']},
  Target:{key:'_i',cols:['YearMonth','Region','TargetRevenue']}
};
const RELATIONSHIPS=[
  {from:'Shipment[CustomerKey]',to:'Customer[CustomerKey]',active:true,note:'many-to-one'},
  {from:'Shipment[DateKey]',to:'Date[DateKey]',active:true,note:'many-to-one (order date)'},
  {from:'Shipment[DeliveryDateKey]',to:'Date[DateKey]',active:false,note:'many-to-one, INACTIVE - use USERELATIONSHIP inside CALCULATE'}
];
const COLUMN_NOTES={
  'Shipment[Weight]':'kg','Shipment[IsOnTime]':'1 = on time, 0 = late','Shipment[Ffe]':'forty-foot equivalents; Air shipments have Ffe = 0',
  'Date[Date]':'real date column; Date is marked as the date table','Date[FiscalYear]':'FY starts 1 Oct, named for the year it ends in (Oct 2025 - Sep 2026 = 2026)',
  'Date[Quarter]':'calendar quarter 1-4','Date[DayOfWeek]':'1 = Monday ... 7 = Sunday','Date[YearMonth]':'text such as "2025-03"',
  'Target[YearMonth]':'text such as "2025-03" (same format as Date[YearMonth])','Target[Region]':'same values as Shipment[Region]'
};
const MODES=['Ocean','Air','Road'], REGIONS=['Asia','Europe','Americas'];
const COUNTRIES=['Germany','USA','China','Brazil','India'];
const MANAGERS=['Ana Ruiz','Ben Okoye','Chen Li','Dara Quinn'];
const MONTH_NAMES=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const CUST_NAMES=['Northwind Foods','Apex Retail','Blue Harbor Co','Cedar Textiles','Delta Motors','Evergreen Pharma','Falcon Electronics','Granite Tools','Harbor Toys','Iris Home','Juniper Paper','Kestrel Sports','Lumen Optics','Maple Beverages','Nordic Furniture'];
const FIRST_N=epochDay(2024,1,1), LAST_N=epochDay(2026,12,31), SHIP_LAST_N=epochDay(2026,6,30);

/* ---------- base-measure library (shown in the UI; usable from Topic 2 on) ---------- */
const MEASURES=[
  {name:'Total Revenue',code:'SUM(Shipment[Revenue])'},
  {name:'Total Cost',code:'SUM(Shipment[Cost])'},
  {name:'Profit',code:'[Total Revenue] - [Total Cost]'},
  {name:'Shipments',code:'COUNTROWS(Shipment)'},
  {name:'Total FFE',code:'SUM(Shipment[Ffe])'},
  {name:'On-Time %',code:'DIVIDE(SUM(Shipment[IsOnTime]), COUNTROWS(Shipment))'}
];
const MEASURE_LC={};MEASURES.forEach(m=>MEASURE_LC[m.name.toLowerCase()]=m);

/* ---------- date table (identical for every seed) ---------- */
function buildDateRows(fromN,toN){
  const rows=[];
  for(let n=fromN;n<=toN;n++){
    const o=ymdOf(n);
    rows.push({DateKey:o.y*10000+o.m*100+o.d,Date:mkDate(n),Year:o.y,MonthNo:o.m,MonthName:MONTH_NAMES[o.m-1],
      YearMonth:o.y+'-'+String(o.m).padStart(2,'0'),Quarter:Math.floor((o.m-1)/3)+1,FiscalYear:o.m>=10?o.y+1:o.y,
      DayOfWeek:((n+3)%7)+1,_n:n});   // 1970-01-01 was a Thursday: (0+3)%7+1 = 4
  }
  return rows;
}
const DATE_ROWS=buildDateRows(FIRST_N,LAST_N);
const YEAR_MONTHS=(function(){const out=[];for(let y=2024;y<=2026;y++)for(let m=1;m<=12;m++){if(y===2026&&m>6)break;out.push({y:y,m:m,ym:y+'-'+String(m).padStart(2,'0')});}return out;})();

/* assign _i (row ordinal) and the join helpers the engine and oracles rely on */
function finalizeData(D){
  for(const T of Object.keys(TABLES))D[T].forEach((r,i)=>{r._i=i;});
  const cust={};D.Customer.forEach(c=>cust[c.CustomerKey]=c);
  const dt={};D.Date.forEach(d=>dt[d.DateKey]=d);
  D.Shipment.forEach(s=>{s._c=cust[s.CustomerKey];s._d=dt[s.DateKey];s._dd=dt[s.DeliveryDateKey]||null;s._n=nOfDateKey(s.DateKey);s._dn=nOfDateKey(s.DeliveryDateKey);});
  return D;
}

function buildData(seed,attempt){
  const r=mulberry32((seed*2654435761+attempt*40503+12345)>>>0);
  const ri=(a,b)=>a+Math.floor(r()*(b-a+1));
  const pick=a=>a[Math.floor(r()*a.length)];
  const shuffle=a=>{a=a.slice();for(let i=a.length-1;i>0;i--){const j=Math.floor(r()*(i+1));const t=a[i];a[i]=a[j];a[j]=t;}return a;};
  const nCust=15;
  const names=shuffle(CUST_NAMES).slice(0,nCust);
  const segs=shuffle(names.map((_,i)=>i<5?'Key':'Standard'));
  const customers=names.map((nm,i)=>({CustomerKey:i+1,CustomerName:nm,Segment:segs[i],Country:pick(COUNTRIES),AccountManager:pick(MANAGERS)}));
  // shipment dates: 6 per month guaranteed, the rest weighted towards later months (growth)
  const months=[];
  for(let k=0;k<180;k++)months.push(k%30);
  const cum=[];let tot=0;for(let k=0;k<30;k++){tot+=1+k/10;cum.push(tot);}
  for(let k=0;k<220;k++){const u=r()*tot;let m=0;while(cum[m]<u)m++;months.push(m);}
  const dated=months.map(mi=>{const ym=YEAR_MONTHS[mi];return {mi:mi,n:epochDay(ym.y,ym.m,ri(1,daysInMonth(ym.y,ym.m)))};});
  dated.sort((a,b)=>a.n-b.n||a.mi-b.mi);
  // each customer ships mostly in one primary mode (and sometimes a second), so not every customer appears in every mode
  const pickMode=()=>{const u=r();return u<0.5?'Ocean':(u<0.7?'Air':'Road');};
  const prof=customers.map(()=>{const a=pickMode();let b=null;if(r()<0.4){b=pickMode();if(b===a)b=null;}return {a:a,b:b,w:1+ri(0,4)};});
  const cumW=[];let totW=0;prof.forEach(p=>{totW+=p.w;cumW.push(totW);});
  const ships=[];
  dated.forEach((x,idx)=>{
    const uc=r()*totW;let ci=0;while(cumW[ci]<uc)ci++;
    const pr=prof[ci];
    const mode=(pr.b&&r()<0.25)?pr.b:pr.a;
    const base=mode==='Ocean'?ri(3000,9000):(mode==='Air'?ri(1500,6000):ri(500,3000));
    const rev=Math.round(base*(1+0.012*x.mi));
    const cost=Math.round(rev*(0.55+r()*0.42));
    const wt=mode==='Ocean'?ri(8000,24000):(mode==='Air'?ri(100,2500):ri(1000,9000));
    const lag=mode==='Ocean'?ri(18,40):(mode==='Air'?ri(2,6):ri(2,10));
    ships.push({ShipmentID:idx+1,CustomerKey:ci+1,Mode:mode,Region:pick(REGIONS),Revenue:rev,Cost:cost,
      Ffe:mode==='Air'?0:(mode==='Ocean'?ri(1,6):ri(1,2)),Weight:wt,IsOnTime:r()<0.75?1:0,
      DateKey:dateKeyOfN(x.n),DeliveryDateKey:dateKeyOfN(x.n+lag)});
  });
  const targets=[];
  for(const ym of YEAR_MONTHS)for(const g of REGIONS){
    let act=0;for(const s of ships)if(s.Region===g&&Math.floor(s.DateKey/100)===ym.y*100+ym.m)act+=s.Revenue;
    targets.push({YearMonth:ym.ym,Region:g,TargetRevenue:Math.max(1000,Math.round(act*(0.85+r()*0.3)/100)*100)});
  }
  return finalizeData({Shipment:ships,Customer:customers,Date:DATE_ROWS,Target:targets,seed:seed});
}

/* derive challenge parameters and reject data that would make a challenge degenerate */
function deriveParams(D){
  const S=D.Shipment, C=D.Customer;
  const yOf=s=>Math.floor(s.DateKey/10000);
  for(const m of MODES)for(const y of [2024,2025,2026]) if(S.filter(s=>s.Mode===m&&yOf(s)===y).length<4) return null;
  for(const g of REGIONS)for(const y of [2024,2025,2026]) if(S.filter(s=>s.Region===g&&yOf(s)===y).length<4) return null;
  for(const ym of YEAR_MONTHS) if(S.filter(s=>Math.floor(s.DateKey/100)===ym.y*100+ym.m).length<3) return null;
  if(!S.some(s=>s.Mode==='Air'&&s.Revenue>0)) return null;
  if(new Set(S.map(s=>s.IsOnTime)).size<2) return null;
  const seg={}; C.forEach(c=>seg[c.CustomerKey]=c.Segment);
  for(const m of MODES){
    if(!S.some(s=>s.Mode===m&&seg[s.CustomerKey]==='Key')) return null;
    if(!S.some(s=>s.Mode===m&&seg[s.CustomerKey]==='Standard')) return null;
    if(new Set(S.filter(s=>s.Mode===m).map(s=>s.CustomerKey)).size>=C.length) return null;
  }
  for(const country of COUNTRIES) if(!C.some(c=>c.Country===country)) return null;
  // every customer ships in each year, so per-customer YoY and rankings are never all-blank
  for(const c of C)for(const y of [2024,2025]) if(!S.some(s=>s.CustomerKey===c.CustomerKey&&yOf(s)===y)) return null;
  // top-N must not tie at the cut-off (N = 3), overall and per year
  const topN=3;
  const revBy=(pred)=>{const o={};S.filter(pred).forEach(s=>o[s.CustomerKey]=(o[s.CustomerKey]||0)+s.Revenue);return Object.values(o).sort((a,b)=>b-a);};
  for(const pred of [()=>true,s=>yOf(s)===2024,s=>yOf(s)===2025,s=>yOf(s)===2026]){
    const v=revBy(pred); if(v.length<=topN||v[topN-1]===v[topN]||v[0]===v[1]) return null;
  }
  // n: customers with more than n shipments; a customer with exactly n shipments must exist
  const cnt={}; S.forEach(s=>cnt[s.CustomerKey]=(cnt[s.CustomerKey]||0)+1);
  const counts=Object.values(cnt).sort((a,b)=>a-b);
  const n=counts[Math.floor(counts.length*0.4)];
  if(!(counts.some(x=>x>n)&&counts.some(x=>x<n)&&counts.filter(x=>x===n).length>=1)) return null;
  // tieN: a shipment count shared by two or more customers (for RANKX tie challenges)
  let tieN=null;for(const c of counts){if(counts.filter(x=>x===c).length>=2&&c<counts[counts.length-1]){tieN=c;break;}}
  if(tieN===null) return null;
  // T: profit threshold
  const profits=S.map(s=>s.Revenue-s.Cost).sort((a,b)=>a-b);
  const T=profits[Math.floor(profits.length*0.6)];
  const gt=S.filter(s=>s.Revenue-s.Cost>T).length, ge=S.filter(s=>s.Revenue-s.Cost>=T).length;
  if(gt===ge||gt<2) return null;
  if(S.filter(s=>s.Revenue>T).length===gt) return null;
  return {n:n,T:T,tieN:tieN,topN:topN,year:2025,prevYear:2024,ym:'2025-06',ymPrev:'2025-05',ymLY:'2024-06'};
}
function generateData(seed){
  for(let a=0;a<2000;a++){
    const D=buildData(seed,a); const P=deriveParams(D);
    if(P){D.params=P;D.attempt=a;return D;}
  }
  throw new Error('Could not generate valid data for seed '+seed);
}

/* =====================================================================
   H - helpers for oracles (plain JS over the arrays, no DAX engine).
   An oracle context looks like:
     { label, P, level, groupBy:['Date[Year]','Date[MonthNo]'], sel:{'Date[Year]':2025,...},
       slicers:{'Shipment[Mode]':['Ocean','Air']} }
   ===================================================================== */
const H={
  epochDay:epochDay, ymd:ymdOf, iso:isoOf, daysInMonth:daysInMonth, dateKey:dateKeyOfN, nOfKey:nOfDateKey,
  shiftMonths:shiftMonths, eom:eomN, som:somN, sq:sqN, eq:eqN, yearStart:yearStartN,
  sum(rows,f){let t=0;for(const r of rows)t+=f(r);return t;},
  // SUM-like: BLANK (null) when there are no rows, like DAX
  sumOrNull(rows,f){return rows.length?H.sum(rows,f):null;},
  div(a,b){return (b==null||b===0||a==null)?null:a/b;},
  colVal(s,id){
    const i=id.indexOf('[');const T=id.slice(0,i),c=id.slice(i+1,-1);
    if(T==='Shipment')return s[c];
    if(T==='Customer')return s._c[c];
    if(T==='Date')return s._d[c];
    throw new Error('colVal: unsupported '+id);
  },
  // merge ctx.slicers (arrays) and ctx.sel (scalars) into {id: [allowed values]}; same column in both -> intersection
  filters(ctx){
    const f={};
    for(const k of Object.keys(ctx.slicers||{}))f[k]=ctx.slicers[k].slice();
    for(const k of Object.keys(ctx.sel||{})){const v=ctx.sel[k];f[k]=(k in f)?f[k].filter(x=>x===v):[v];}
    return f;
  },
  // shipments visible under the context. opts: drop:[ids | 'Date' | 'Customer' ...], add:{id:[vals]}, from/to: epoch-day range,
  // dateField:'DateKey'|'DeliveryDateKey' (which date drives the Date filters and from/to)
  vis(D,ctx,opts){
    const o=opts||{};const f=H.filters(ctx);
    for(const d of (o.drop||[])){
      if(d.indexOf('[')<0){for(const k of Object.keys(f))if(k.startsWith(d+'['))delete f[k];}
      else delete f[d];
    }
    Object.assign(f,o.add||{});
    const keys=Object.keys(f);
    const useDel=o.dateField==='DeliveryDateKey';
    return D.Shipment.filter(s=>{
      for(const k of keys){
        let v;
        if(k.startsWith('Date[')){const dr=useDel?s._dd:s._d;if(!dr)return false;v=dr[k.slice(5,-1)];}
        else v=H.colVal(s,k);
        if(!f[k].includes(v))return false;
      }
      if(o.from!=null||o.to!=null){const n=useDel?s._dn:s._n;if(o.from!=null&&n<o.from)return false;if(o.to!=null&&n>o.to)return false;}
      return true;
    });
  },
  // Date rows visible under the Date[...] filters of the context (opts.drop works as in vis)
  dates(D,ctx,opts){
    const o=opts||{};const f=H.filters(ctx);
    for(const d of (o.drop||[])){if(d.indexOf('[')<0){for(const k of Object.keys(f))if(k.startsWith(d+'['))delete f[k];}else delete f[d];}
    const keys=Object.keys(f).filter(k=>k.startsWith('Date['));
    return D.Date.filter(d=>keys.every(k=>f[k].includes(d[k.slice(5,-1)])));
  },
  // {min,max} epoch days of the dates visible under the context, or null
  dateRange(D,ctx,opts){const ds=H.dates(D,ctx,opts);return ds.length?{min:ds[0]._n,max:ds[ds.length-1]._n}:null;},
  // revenue-like sum over shipments in an inclusive epoch-day range, ignoring every Date filter of the context
  inRange(D,ctx,from,to,f,dateField){const rows=H.vis(D,ctx,{drop:['Date'],from:from,to:to,dateField:dateField});return H.sumOrNull(rows,f);},
  // customers ranked by a value, ties kept: returns [{key,val}] sorted descending
  byCustomer(rows,f){const o={};rows.forEach(s=>o[s.CustomerKey]=(o[s.CustomerKey]||0)+f(s));return Object.keys(o).map(k=>({key:+k,val:o[k]})).sort((a,b)=>b.val-a.val||a.key-b.key);}
};
