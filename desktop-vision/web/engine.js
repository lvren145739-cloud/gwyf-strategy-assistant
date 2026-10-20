/* Deterministic probability engine. All payouts include the stake. */
const GWYFEngine=(()=>{
'use strict';
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const reds=new Set([1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]);
const roulette={};
function def(key,name,nums,gross){roulette[key]={key,name,nums,gross};}
for(let n=0;n<=36;n++)def('n'+n,String(n),[n],36);
def('red','红色',[...reds],2);def('black','黑色',Array.from({length:36},(_,i)=>i+1).filter(n=>!reds.has(n)),2);
for(const [key,name,predicate] of [['odd','奇数',n=>n%2===1],['even','偶数',n=>n%2===0],['low','1–18',n=>n<=18],['high','19–36',n=>n>=19]])def(key,name,Array.from({length:36},(_,i)=>i+1).filter(predicate),2);
for(let i=0;i<3;i++){def('doz'+i,`${i*12+1}–${i*12+12}`,Array.from({length:12},(_,j)=>i*12+j+1),3);def('col'+i,`第${i+1}列`,Array.from({length:12},(_,j)=>i+1+j*3),3);}
const rouletteScenarios=Array.from({length:37},(_,id)=>({id,p:1/37}));
const baccaratDefs={player:{name:'闲 PLAYER',gross:2,count:2927104},banker:{name:'庄 BANKER',gross:2,count:2927104},tie:{name:'和 TIE',gross:10,count:643192}};
const baccaratScenarios=Object.keys(baccaratDefs).map(id=>({id,p:baccaratDefs[id].count/6497400}));
const fortune=[{g:0,n:1},{g:.1,n:5},{g:.25,n:4},{g:.5,n:3},{g:2,n:2},{g:3,n:2},{g:5,n:1}];
const money={green:{name:'绿色',n:14,g:2,color:'#7fc39b'},blue:{name:'蓝色',n:10,g:3,color:'#7faed5'},red:{name:'红色',n:8,g:5,color:'#db8a82'},orange:{name:'橙色',n:5,g:10,color:'#e5b16c'}};
const penguin=[1,1.2,1.5,2,3,5,10,25,75,250,1000];
const dragon=Array.from({length:7},(_,i)=>(4/3)**i);
const plinko=[24,6,2.8,1.2,.5,.2,.2,.5,1.2,2.8,6,24];
const pay=[0,1,2,3,4,6,9,25,50];
const handNames=['高牌','一对','两对','三条','顺子','同花','葫芦','四条','同花顺'];
const diceWays={2:1,3:2,4:3,5:4,6:5,7:6,8:5,9:4,10:3,11:2,12:1};
const duckBaseline=Object.freeze({p:.25,g:4}); // Symmetry benchmark, not measured live odds.
// Early reverse-engineering model; not a verified live RNG distribution.
const slotSymbols=[{name:'莲花',en:'Lotus',glyph:'❀',factor:1.75,q:7},{name:'甲虫',en:'Beetle',glyph:'♜',factor:1.25,q:5},{name:'权杖',en:'Staff',glyph:'⚚',factor:.75,q:3},{name:'眼睛',en:'Eye',glyph:'◉',factor:.25,q:1}];
const slotPatterns=[
 {name:'上横线',cells:[0,1,2],g:2},{name:'中横线',cells:[3,4,5],g:2},{name:'下横线',cells:[6,7,8],g:2},
 {name:'左竖线',cells:[0,3,6],g:2},{name:'中竖线',cells:[1,4,7],g:2},{name:'右竖线',cells:[2,5,8],g:2},
 {name:'斜线 ＼',cells:[0,4,8],g:2},{name:'斜线 ／',cells:[2,4,6],g:2},
 {name:'菱形',cells:[1,3,5,7],g:5},{name:'X形',cells:[0,2,4,6,8],g:20},{name:'九格满盘',cells:[0,1,2,3,4,5,6,7,8],g:59}
];
function slotMatches(board){
 if(!Array.isArray(board)||board.length!==9||board.some(v=>!Number.isInteger(v)||v<0||v>3))throw Error('请为九个格子各选择一种图案。');
 return slotPatterns.flatMap((p,index)=>{const symbol=board[p.cells[0]];return p.cells.every(i=>board[i]===symbol)?[{index,symbol,g:p.g*slotSymbols[symbol].factor}]:[];});
}
let slotCache=null;
function slotsIID(){
 if(slotCache)return slotCache;
 const total=4**9,hist=new Map(),counts=Array(11).fill(0),board=new Array(9);
 for(let code=0;code<total;code++){
  let bits=code,q=0;for(let i=0;i<9;i++){board[i]=bits&3;bits>>=2;}
  for(let j=0;j<slotPatterns.length;j++){const p=slotPatterns[j],symbol=board[p.cells[0]];let hit=true;for(let k=1;k<p.cells.length;k++)if(board[p.cells[k]]!==symbol){hit=false;break;}if(hit){q+=p.g*slotSymbols[symbol].q;counts[j]++;}}
  hist.set(q,(hist.get(q)||0)+1);
 }
 const rows=[...hist].sort((a,b)=>a[0]-b[0]).map(([q,count])=>({g:q/4,count,p:count/total}));
 slotCache={total,counts,rows};return slotCache;
}
function buffs(owned={},settings={},team='group'){
 const n=id=>Number(owned[id])||0,S=1+.5*n('stakeholder');
 const melody=n('microphone')?clamp(settings.melody??1,0,1):0;
 const tipsy=n('drink')?clamp(settings.tipsy??2,1,20):1;
 const a=(1+.5*n('confidence'))*tipsy*(1+melody);
 const recovery=n('statue')?1:clamp(1-.75**n('insurance')+melody,0,1);
 const camera=!!n('camera')&&team==='group';
 return {a,b:1-recovery,recovery,S,melody,tipsy,camera,cameraRate:camera?.25*S*n('camera'):0,bonusChance:clamp(.1*n('bonus'),0,1)};
}
function settle(raw,b={a:1,b:1,cameraRate:0}){return Math.abs(raw)<1e-10?0:raw>0?raw*b.a*(1+(b.cameraRate||0)):raw*b.b;}
function distribution(rows,b={a:1,b:1,cameraRate:0},total=1){
 let ev=0,base=0,win=0,flat=0,any=0,min=Infinity,max=-Infinity,square=0;
 const out=rows.map(r=>{const raw=r.raw??total*(r.g-1),net=settle(raw,b),p=r.p;ev+=p*net;base+=p*raw;square+=p*net*net;if(net>1e-8)win+=p;else if(net>=-1e-8)flat+=p;if(r.hit??r.g>0)any+=p;if(p>0){min=Math.min(min,net);max=Math.max(max,net);}return {...r,raw,net};});
 if(Math.abs(ev)<1e-12*Math.max(1,total))ev=0;if(Math.abs(base)<1e-12*Math.max(1,total))base=0;
 return {total,ev,roi:total?ev/total:0,base,win:clamp(win,0,1),flat:clamp(flat,0,1),lose:clamp(1-win-flat,0,1),any:clamp(any,0,1),min:total?min:0,max:total?max:0,sd:Math.sqrt(Math.max(0,square-ev*ev)),out};
}
function single(p,g,b){return distribution([{id:'hit',p,g,hit:true},{id:'miss',p:1-p,g:0,hit:false}],b);}
function portfolio(wagers,kind,b){
 const defs=kind==='roulette'?roulette:baccaratDefs,scenarios=kind==='roulette'?rouletteScenarios:baccaratScenarios;
 const total=wagers.reduce((z,w)=>z+w.amount,0);
 return distribution(scenarios.map(s=>{let raw=0,hit=false;for(const w of wagers){const d=defs[w.key];if(!d)continue;const yes=kind==='roulette'?d.nums.includes(s.id):w.key===s.id;const g=yes?d.gross:0;raw+=w.amount*(g-1);if(yes)hit=true;}return {...s,raw,hit};}),b,total);
}
function pointModel(point,left=3){const w=diceWays[point]/36,l=6/36,r=1-w-l,t=r**left;return [{id:'point',p:w*(1-t)/(w+l),g:4},{id:'loss',p:l*(1-t)/(w+l),g:0},{id:'push',p:t,g:1}];}
function crapsRows(){const rows=[{id:'comeout',p:8/36,g:2},{id:'immediateLoss',p:4/36,g:0}];for(const point of [4,5,6,8,9,10])for(const r of pointModel(point))rows.push({...r,id:point+'-'+r.id,p:r.p*diceWays[point]/36});return rows;}
function minesP(m,k){let p=1;for(let i=0;i<k;i++)p*=(25-m-i)/(25-i);return p;}
function minesRoutes(target,a=1){
 if(!Number.isFinite(target)||target<1||!Number.isFinite(a)||a<=0)throw Error('目标和利润倍数无效。');
 const rows=[];
 for(let m=1;m<=24;m++){
  let p=1,clicks=0;
  for(let k=1;k<=25-m;k++){
   clicks+=p;p*=(26-m-k)/(26-k);const g=1/p,final=1+(g-1)*a;
   if(final+1e-8>=target){rows.push({m,k,p,g,final,expectedClicks:clicks/p});break;}
  }
 }
 return rows;
}
function choose(n,k){if(k<0||k>n)return 0;k=Math.min(k,n-k);let v=1;for(let i=1;i<=k;i++)v=v*(n-k+i)/i;return v;}
function kenoRows(n,estimated=1){const rows=Array.from({length:n+1},(_,h)=>({id:h,p:choose(10,h)*choose(38,n-h)/choose(48,n),g:h?2**h:0,hit:h>0}));const scale=estimated/rows.reduce((z,r)=>z+r.p*r.g,0);return rows.map(r=>({...r,g:r.g*scale}));}
function bjValue(cards){let low=0,aces=0;for(const c of cards){if(c==='A'){low++;aces++;}else low+=['J','Q','K'].includes(c)?10:Number(c);}const soft=aces>0&&low+10<=21;return {total:low+(soft?10:0),soft};}
function bjNext(total,soft,rank){let low=total-(soft?10:0);const ace=rank==='A';low+=ace?1:Number(rank);return low+((soft||ace)&&low+10<=21?10:0);}
// Vanilla rules, not user-selectable casino variants. See the dated source notes.
const bjRules=Object.freeze({dealerStand:17,hitSoft17:false,doubleInitialOnly:true,naturalGross:3,split:false});
function bjCanDouble(s){return s.two===true&&s.total<21;}
function bjReference(s,d){
 const canDouble=bjCanDouble(s);
 const t=s.total,dealer=d==='A'?11:Number(d);let action='H',why='点数偏低，常规查表倾向要牌。';
 if(t>21)return {action:'B',why:'手牌已超过21点。'};
 if(t===21)return {action:'S',why:'21点停牌；初始两张自然21按游戏规则已直接结算。'};
 if(s.soft){
  if(t>=20){action='S';why='软20以上，常规查表倾向停牌。';}
  else if(t===19){action='S';why='软19，常规S17查表参考停牌。';}
  else if(t===18){action=dealer>=3&&dealer<=6?'DS':[2,7,8].includes(dealer)?'S':'H';why='软18对3–6参考加倍，对2/7/8停牌，对9/10/A要牌。';}
  else if(t===17){action=dealer>=3&&dealer<=6?'DH':'H';why='软17通常要牌，对3–6可参考加倍。';}
  else if(t===15||t===16){action=dealer>=4&&dealer<=6?'DH':'H';why='软15/16对4–6可参考加倍。';}
  else if(t===13||t===14){action=dealer>=5&&dealer<=6?'DH':'H';why='软13/14对5–6可参考加倍。';}
 }else{
  if(t>=17){action='S';why='硬17以上，常规查表倾向停牌。';}
  else if(t>=13){action=dealer<=6?'S':'H';why='硬13–16：庄家2–6时停牌，7–A时要牌。';}
  else if(t===12){action=dealer>=4&&dealer<=6?'S':'H';why='硬12只对4、5、6停牌。';}
  else if(t===11){action=dealer!==11?'DH':'H';why='硬11通常加倍；常规S17查表对A参考要牌。';}
  else if(t===10){action=dealer<=9?'DH':'H';why='硬10对2–9可参考加倍。';}
  else if(t===9){action=dealer>=3&&dealer<=6?'DH':'H';why='硬9对3–6可参考加倍。';}
 }
 if(action==='DH'||action==='DS'){const fallback=action==='DH'?'H':'S';return {action:canDouble?'D':fallback,why:why+(canDouble?'':' 已经要过牌，按原版规则不能再加倍，采用备用动作。'),fallback};}
 return {action,why};
}
function pokerCategory(ids){
 let mask=0,flush=true,firstSuit=ids[0]/13|0;const counts=new Uint8Array(13);
 for(let i=0;i<5;i++){const id=ids[i],r=id%13;counts[r]++;mask|=1<<r;if((id/13|0)!==firstSuit)flush=false;}
 let pairs=0,triple=0,quad=0;for(let i=0;i<13;i++){if(counts[i]===4)quad++;else if(counts[i]===3)triple++;else if(counts[i]===2)pairs++;}
 let straight=false;if(!pairs&&!triple&&!quad){straight=mask===4111;for(let i=0;i<=8&&!straight;i++)straight=mask===(31<<i);}
 return straight&&flush?8:quad?7:triple&&pairs?6:flush?5:straight?4:triple?3:pairs===2?2:pairs?1:0;
}
function* pokerSolve(data){
 const {cards,used=[],a=1,b=1,cameraRate=0,objective='ev'}=data;
 if(cards.length!==5||cards.some(id=>!Number.isInteger(id)||id<0||id>51))throw Error('请先录入完整的五张手牌。');
 if(new Set(cards).size!==5)throw Error('五张手牌不能重复。');
 const absent=new Set([...cards,...used]);const rem=Array.from({length:52},(_,i)=>i).filter(id=>!absent.has(id));
 if(rem.length<5)throw Error('剩余不足5张，换牌可能跨越重建边界。请核对游戏内重洗状态后重新记录。');
 const total=choose(rem.length+5,5),solutions=[];let done=0,chunk=0;const grossPay=[0,1,2,3,4,6,9,25,50];
 for(let mask=31;mask>=0;mask--){
  const fixed=cards.filter((_,i)=>mask&(1<<i)),need=5-fixed.length,hist=Array(9).fill(0),work=[...fixed],idx=Array.from({length:need},(_,i)=>i);let n=0;
  for(;;){for(let j=0;j<need;j++)work[fixed.length+j]=rem[idx[j]];hist[pokerCategory(work)]++;n++;done++;chunk++;
   if(chunk>=25000){chunk=0;yield {progress:done/total,done,total};}
   if(need===0)break;let j=need-1;while(j>=0&&idx[j]===rem.length-need+j)j--;if(j<0)break;idx[j]++;for(let k=j+1;k<need;k++)idx[k]=idx[k-1]+1;
  }
  let ev=0,base=0,win=0,flat=0,sq=0;for(let k=0;k<9;k++){const raw=grossPay[k]-1,net=raw>0?raw*a*(1+cameraRate):raw*b,p=hist[k]/n;ev+=p*net;base+=p*raw;sq+=p*net*net;if(net>1e-8)win+=p;else if(net>=-1e-8)flat+=p;}
  solutions.push({mask,n,hist,ev,base,win,flat,lose:Math.max(0,1-win-flat),sd:Math.sqrt(Math.max(0,sq-ev*ev))});
 }
 solutions.sort((x,y)=>objective==='win'?y.win-x.win||y.ev-x.ev||y.mask-x.mask:y.ev-x.ev||y.win-x.win||y.mask-x.mask);
 return {solutions,total,remaining:rem.length};
}
return {clamp,reds,roulette,rouletteScenarios,baccaratDefs,baccaratScenarios,fortune,money,penguin,dragon,plinko,pay,handNames,diceWays,duckBaseline,slotSymbols,slotPatterns,slotMatches,slotsIID,buffs,settle,distribution,single,portfolio,pointModel,crapsRows,minesP,minesRoutes,choose,kenoRows,bjValue,bjNext,bjRules,bjCanDouble,bjReference,pokerCategory,pokerSolve};
})();
if(typeof module!=='undefined'&&module.exports)module.exports=GWYFEngine;
