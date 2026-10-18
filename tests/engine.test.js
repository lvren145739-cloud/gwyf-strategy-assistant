'use strict';
const assert=require('node:assert/strict');
const E=require('../src/engine.js');
let checks=0;
const near=(a,b,t=1e-10)=>{checks++;assert.ok(Math.abs(a-b)<=t,`${a} ≠ ${b}`)};
const normal={a:1,b:1,cameraRate:0};
for(const d of Object.values(E.roulette)){const o=E.portfolio([{key:d.key,amount:37}],'roulette',normal);near(o.ev,-1);near(o.win,d.nums.length/37);}
for(let k=1;k<=20;k++){const wagers=Object.keys(E.roulette).filter((_,i)=>(i+k)%k===0).map((key,i)=>({key,amount:(i+1)*.17}));const o=E.portfolio(wagers,'roulette',normal);near(o.ev,-o.total/37);near(o.win+o.flat+o.lose,1);}
const paired=[{key:'red',amount:100},{key:'black',amount:100}];
const b=E.buffs({confidence:2,insurance:2});
const pairedResult=E.portfolio(paired,'roulette',b);
near(pairedResult.win,0);near(pairedResult.flat,36/37);near(pairedResult.min,-200*.75**2);
const all37=Array.from({length:37},(_,i)=>({key:'n'+i,amount:1}));near(E.portfolio(all37,'roulette',normal).min,-1);near(E.portfolio(all37,'roulette',normal).max,-1);near(E.portfolio(all37,'roulette',E.buffs({statue:1,camera:2})).ev,0);
near(E.buffs({insurance:2}).recovery,.4375);near(E.buffs({confidence:7}).a,4.5);near(E.buffs({insurance:1,microphone:2},{melody:.75}).b,0);near(E.buffs({statue:10}).recovery,1);near(E.buffs({camera:3,stakeholder:2},{},'group').cameraRate,1.5);near(E.buffs({camera:3},{},'solo').cameraRate,0);near(E.buffs({bonus:12}).bonusChance,1);near(E.buffs({bonus:3}).bonusChance,.3);near(E.distribution([{p:1,g:2},{p:0,g:0}]).min,1);
for(let n=1;n<=10;n++){const r=E.kenoRows(n),o=E.distribution(r);near(r.reduce((z,x)=>z+x.p,0),1);near(o.roi,0);near(E.distribution(E.kenoRows(n,.8)).roi,-.2);}
near(E.distribution(E.kenoRows(4)).win,.6206444650015418);
near(E.kenoRows(1)[1].g,4.8);
const variances=Array.from({length:10},(_,i)=>E.distribution(E.kenoRows(i+1)).sd**2);assert.equal(variances.indexOf(Math.min(...variances))+1,6);checks++;
const fortune=E.distribution(E.fortune.map(r=>({p:r.n/18,g:r.g})));near(fortune.roi,0);near(fortune.win,5/18);
const craps=E.distribution(E.crapsRows());near(craps.roi,.3774934270690443);near(craps.win,.3937209457399786);near(craps.flat,.2470540885535742);near(craps.out.reduce((z,r)=>z+r.p,0),1);
for(const point of [4,5,6,8,9,10])for(let left=1;left<=3;left++)near(E.pointModel(point,left).reduce((z,r)=>z+r.p,0),1);
near(E.minesP(19,2),.05);near(1/E.minesP(20,1),5);
for(let m=1;m<25;m++)for(let k=0;k<25-m;k++){const p=(25-m-k)/(25-k);near(E.minesP(m,k)*p,E.minesP(m,k+1));}
for(const arr of [E.dragon,E.penguin])for(let k=0;k<arr.length-1;k++)near((arr[k]/arr[k+1])*arr[k+1],arr[k]);
assert.deepEqual(E.bjValue(['A','A','9']),{total:21,soft:true});assert.deepEqual(E.bjValue(['A','A','9','K']),{total:21,soft:false});checks+=2;
near(E.bjNext(18,true,'10'),18);near(E.bjNext(16,false,'10'),26);near(E.bjNext(12,true,'A'),13);
assert.equal(E.bjReference({total:11,soft:false,two:true},'6').action,'D');assert.equal(E.bjReference({total:16,soft:false},'10').action,'H');assert.equal(E.bjReference({total:18,soft:true,two:false},'6').action,'S');checks+=3;

// Legality follows the hand, never a user-selected casino variant.
assert.equal(Object.isFrozen(E.bjRules),true);assert.equal(E.bjRules.hitSoft17,false);checks+=2;
for(const [hand,expected] of [[{total:11,two:true},true],[{total:11,two:false},false],[{total:21,two:true},false],[{total:22,two:true},false]]){assert.equal(E.bjCanDouble(hand),expected);checks++;}
assert.equal(E.bjReference({total:11,soft:false,two:false},'6').action,'H');assert.equal(E.bjReference({total:19,soft:true,two:true},'6',true,true).action,'S');checks+=2;
near(E.buffs({camera:1},{cameraInEV:false},'group').cameraRate,.25);near(E.buffs({camera:1},{},'solo').cameraRate,0);
const routes20=E.minesRoutes(20),best20=[...routes20].sort((x,y)=>y.p-x.p||x.k-y.k)[0],oneClick=routes20.find(r=>r.k===1);
assert.equal(best20.m,19);assert.equal(best20.k,2);near(best20.p,.05);near(best20.expectedClicks,24.8);assert.equal(oneClick.m,24);near(oneClick.expectedClicks,25);checks+=3;
for(const target of [1,5,10,20,100,1000000])for(const factor of [1,2,4,17])for(const r of E.minesRoutes(target,factor)){
 const combinatorial=E.choose(25-r.m,r.k)/E.choose(25,r.k);near(r.p,combinatorial);near(r.g,1/combinatorial,1e-6);
 assert.ok(r.final+1e-8>=target);checks++;
 if(r.k>1){assert.ok(1+(1/E.minesP(r.m,r.k-1)-1)*factor<target+1e-8);checks++;}
 const independentClicks=Array.from({length:r.k},(_,j)=>E.choose(25-r.m,j)/E.choose(25,j)).reduce((z,p)=>z+p,0)/combinatorial;near(r.expectedClicks,independentClicks,1e-6);
}
assert.equal(E.minesRoutes(1e10).length,0);checks++;

// Independent full ordered four-card count, with physical card removal.
let player=0,tie=0,banker=0;const ranks=Array.from({length:52},(_,i)=>Math.min(i%13+1,10));
for(let a=0;a<52;a++)for(let b=0;b<52;b++){if(b===a)continue;for(let c=0;c<52;c++){if(c===a||c===b)continue;const x=(ranks[a]+ranks[c])%10;for(let d=0;d<52;d++){if(d===a||d===b||d===c)continue;const y=(ranks[b]+ranks[d])%10;if(x>y)player++;else if(x<y)banker++;else tie++;}}}
assert.deepEqual([player,banker,tie],[2927104,2927104,643192]);checks++;
// All 2,598,960 poker hands must match the known exact category census.
const census=Array(9).fill(0),hand=[];
for(let a=0;a<48;a++)for(let b=a+1;b<49;b++)for(let c=b+1;c<50;c++)for(let d=c+1;d<51;d++)for(let e=d+1;e<52;e++){hand[0]=a;hand[1]=b;hand[2]=c;hand[3]=d;hand[4]=e;census[E.pokerCategory(hand)]++;}
assert.deepEqual(census,[1302540,1098240,123552,54912,10200,5108,3744,624,40]);checks++;
function solve(cards,used=[]){const g=E.pokerSolve({cards,used});for(;;){const r=g.next();if(r.done)return r.value;}}
const sf=solve([8,9,10,11,12]);assert.equal(sf.solutions[0].mask,31);near(sf.solutions[0].ev,49);assert.equal(sf.total,2598960);checks+=2;
const aa=solve([12,25,30,46,10]);assert.equal(aa.solutions[0].mask,3);assert.equal(aa.solutions.length,32);checks+=2;
for(const s of aa.solutions)near(s.hist.reduce((z,v)=>z+v,0),s.n);
const short=solve([8,9,10,11,12],Array.from({length:42},(_,i)=>i).filter(i=>![8,9,10,11,12].includes(i)));assert.equal(short.remaining,10);checks++;
// Slot-pattern probabilities and the whole-board distribution are different events.
const slots=E.slotsIID();assert.equal(slots.total,262144);assert.equal(slots.rows.reduce((z,r)=>z+r.count,0),262144);checks+=2;
assert.deepEqual(slots.counts,[16384,16384,16384,16384,16384,16384,16384,16384,4096,1024,4]);checks++;
for(let i=0;i<E.slotPatterns.length;i++)near(slots.counts[i]/slots.total,4**(1-E.slotPatterns[i].cells.length));
const slotModel=E.distribution(slots.rows);near(1+slotModel.roi,1+5/64+20/256+59/65536);near(slotModel.any,.418182373046875);near(slotModel.win,.3246612548828125);
for(let symbol=0;symbol<4;symbol++){const matches=E.slotMatches(Array(9).fill(symbol));assert.equal(matches.length,11);checks++;near(matches.reduce((z,m)=>z+m.g,0),100*E.slotSymbols[symbol].factor);}
assert.equal(E.slotMatches([0,1,2,1,0,3,2,3,0]).length,1);checks++;
const enhanced={a:2,b:.75,cameraRate:0};near(E.distribution(slots.rows,enhanced).ev,slots.rows.reduce((z,r)=>z+r.p*((r.g-1)>0?2*(r.g-1):.75*(r.g-1)),0));
assert.throws(()=>E.slotMatches(Array(9).fill(4)),/九个格子/);checks++;
assert.throws(()=>E.pokerSolve({cards:[null,null,null,null,null]}).next(),/完整/);checks++;
console.log(`PASS ${checks} probability/invariant checks; full Baccarat deals and all poker categories verified.`);
