'use strict';
const assert=require('node:assert/strict'),solve=require('../src/blackjack-engine.js');
let checks=0;function near(a,b,t=1e-10){assert.ok(Math.abs(a-b)<t,`${a} != ${b}`);checks++;}
function perms(a){if(!a.length)return [[]];return a.flatMap((x,i)=>perms(a.filter((_,j)=>j!==i)).map(r=>[x,...r]));}
// Independent reference: explicitly reserve a hidden hole, then keep full ordered
// worlds. Future choices group worlds by the player's observation, never the hole.
const all=perms([6,6,7,8,9,10]).map(p=>({hole:p[0],deck:p.slice(1)}));
function next(total,soft,rank){const cards=soft?[1,total-11,rank]:[total,rank];let t=cards.reduce((z,c)=>z+c,0),ace=cards.includes(1)&&t+10<=21;return [t+(ace?10:0),ace];}
function brute(total,soft,up,A=1,B=1,worlds=all){
 const ev=v=>A*v[0]-B*v[2],average=vs=>[0,1,2].map(i=>vs.reduce((z,v)=>z+v[i],0)/vs.length);
 function stand(worlds,t){return average(worlds.map(w=>{let [d,a]=next(up===1?11:up,up===1,w.hole),k=0;while(d<17){assert.ok(k<w.deck.length,'Reference fixture exhausted');[d,a]=next(d,a,w.deck[k++]);}return d>21||t>d?[1,0,0]:t===d?[0,1,0]:[0,0,1];}));}
 function hit(worlds,t,s,once){const groups=new Map();for(const w of worlds){const r=w.deck[0];assert.ok(r);if(!groups.has(r))groups.set(r,[]);groups.get(r).push({hole:w.hole,deck:w.deck.slice(1)});}const vs=[];for(const [r,g]of groups){const [tt,ss]=next(t,s,r),v=tt>21?[0,0,1]:once?stand(g,tt):play(g,tt,ss);vs.push(...Array(g.length).fill(v));}return average(vs);}
 function play(ws,t,s){const st=stand(ws,t);if(t===21)return st;const h=hit(ws,t,s,false);return ev(h)>ev(st)+1e-12?h:st;}
 return {S:stand(worlds,total),H:hit(worlds,total,soft,false),D:hit(worlds,total,soft,true)};
}
const counts=[0,0,0,0,0,2,1,1,1,1];
for(const up of ['2','6','10','A'])for(const [total,soft]of [[12,false],[16,false],[20,false],[13,true],[18,true]])for(const [a,b]of [[1,1],[2,.5625],[1,0]]){
 const actual=solve({counts,total,soft,two:true,canDouble:true,dealer:up,a,b}),expected=brute(total,soft,up==='A'?1:Number(up),a,b);
 for(const r of actual.actions){expected[r.action].forEach((p,i)=>near([r.win,r.push,r.lose][i],p));near(r.ev,(a*r.win-b*r.lose)*r.stake);}
 near(actual.ev,Math.max(...actual.actions.map(r=>r.ev)));
}
// Explicit Ace worlds exercise soft-to-hard conversion and dealer soft17.
const aceWorlds=perms([1,8,9,9,10,10]).map(p=>({hole:p[0],deck:p.slice(1)}));
for(const up of ['2','10','A'])for(const [total,soft]of [[16,false],[20,false],[18,true],[21,true]]){
 const c=[1,0,0,0,0,0,0,1,2,2],x=solve({counts:c,total,soft,two:false,dealer:up});
 const y=brute(total,soft,up==='A'?1:Number(up),1,1,aceWorlds);
 for(const r of x.actions)y[r.action].forEach((v,i)=>near([r.win,r.push,r.lose][i],v));
}
// Last unknown is reserved as the hole; next player card must come from a fresh52.
let r=solve({counts:[0,0,0,0,0,0,0,0,0,1],total:20,soft:false,two:true,canDouble:true,dealer:'10'});
near(r.actions.find(x=>x.action==='S').push,1);near(r.actions.find(x=>x.action==='H').win,4/52);near(r.actions.find(x=>x.action==='H').lose,48/52);assert.equal(r.action,'S');assert.equal(r.rebuild,true);checks+=2;
assert.equal(solve({counts,total:21,two:true,dealer:'A',a:1.5}).ev,3);checks++;
assert.equal(solve({counts,total:16,two:false,canDouble:true,dealer:'10'}).actions.length,2);checks++;
assert.throws(()=>solve({counts:counts.map(()=>0),total:16,dealer:'10'}));checks++;
// Composition can reverse the action for the SAME known hand and dealer.
const full=[4,4,4,4,4,4,4,4,4,16];full[9]-=2;full[5]--; // player10+6 vs10
const base=solve({counts:full,total:16,two:true,canDouble:true,dealer:'10'});
let reversal;
for(let i=0;i<10&&!reversal;i++)for(let n=1;n<=full[i];n++){const c=full.slice();c[i]-=n;const x=solve({counts:c,total:16,two:true,canDouble:true,dealer:'10'});if(x.action!==base.action){reversal={rank:i+1,n,from:base.action,to:x.action};break;}}
assert.ok(reversal,'Used cards should change the policy in a close hand');checks++;
console.log(JSON.stringify({checks,independentFixtures:72,compositionReversal:reversal}));
