/* Finite-deck Blackjack expectimax. Unknown dealer hole is never revealed to a decision. */
function GWYFBlackjackSolve(data){
 'use strict';
 const full=[4,4,4,4,4,4,4,4,4,16],radix=[],ranks=[1,2,3,4,5,6,7,8,9,10];
 let mult=1;for(let i=0;i<10;i++){radix[i]=mult;mult*=full[i]+1;}
 const codeOf=c=>c.reduce((z,n,i)=>z+n*radix[i],0),fullCode=codeOf(full),sum=c=>c.reduce((z,n)=>z+n,0);
 const A=(data.a??1)*(1+(data.cameraRate||0)),B=data.b??1,up=data.dealer==='A'?11:Number(data.dealer);
 if(!(up>=2&&up<=11)||!Number.isFinite(A)||A<0||!Number.isFinite(B)||B<0)throw Error('庄家明牌或结算参数无效。');
 const next=(t,soft,i)=>{const low=t-(soft?10:0)+ranks[i],flex=(soft||i===0)&&low+10<=21;return [low+(flex?10:0),!!flex];};
 const ev=v=>A*v[0]-B*v[2],loss=[0,0,1],pMemo=new Map(),dMemo=new Map();
 let states=0,rebuild=false;
 const touch=()=>{if(++states>1800000)throw Error('此局分支较多，请逐张输入以缩小牌池或减少未知组成。');};
 function dealer(c,n,code,t,soft){
  if(t>21)return [1,0,0,0,0,0];
  if(t>=17){const v=[0,0,0,0,0,0];v[t-16]=1;return v;}
  if(n===0){rebuild=true;return dealer(full.slice(),52,fullCode,t,soft);}
  const key=code*64+t+(soft?32:0),cached=dMemo.get(key);if(cached)return cached;touch();
  const out=[0,0,0,0,0,0];
  for(let i=0;i<10;i++)if(c[i]){const p=c[i]/n;c[i]--;const v=next(t,soft,i),dist=dealer(c,n-1,code-radix[i],v[0],v[1]);c[i]++;for(let j=0;j<6;j++)out[j]+=p*dist[j];}
  dMemo.set(key,out);return out;
 }
 function stand(c,n,code,t,hole){
  let start=up,soft=up===11;
  if(hole>=0){const v=next(start,soft,hole);start=v[0];soft=v[1];}
  const d=dealer(c,n,code,start,soft);let win=d[0],push=0;
  for(let v=17;v<=21;v++){if(v<t)win+=d[v-16];else if(v===t)push+=d[v-16];}
  return [win,push,Math.max(0,1-win-push)];
 }
 function draw(c,n,code,t,soft,hole,forceStand){
  // With an unobserved hole, n includes that reserved card. The last card is
  // then inferable, and the physical draw pile is empty: rebuild without drawing it.
  if(hole<0&&n===1){rebuild=true;const h=c.findIndex(x=>x>0);return draw(full.slice(),52,fullCode,t,soft,h,forceStand);}
  if(n===0){rebuild=true;return draw(full.slice(),52,fullCode,t,soft,hole,forceStand);}
  const out=[0,0,0];
  for(let i=0;i<10;i++)if(c[i]){
   const p=c[i]/n;c[i]--;const v=next(t,soft,i),result=v[0]>21?loss:forceStand?stand(c,n-1,code-radix[i],v[0],hole):play(c,n-1,code-radix[i],v[0],v[1],hole);c[i]++;
   for(let j=0;j<3;j++)out[j]+=p*result[j];
  }
  return out;
 }
 function play(c,n,code,t,soft,hole){
  if(t>21)return loss;
  const key=(code*64+t+(soft?32:0))*12+hole+1,cached=pMemo.get(key);if(cached)return cached;touch();
  const s=stand(c,n,code,t,hole);if(t===21){pMemo.set(key,s);return s;}
  const h=draw(c,n,code,t,soft,hole,false),best=ev(h)>ev(s)+1e-12?h:s;pMemo.set(key,best);return best;
 }
 const scenarios=data.scenarios||[{counts:data.counts,weight:1}],totalWeight=scenarios.reduce((z,s)=>z+s.weight,0);
 if(!scenarios.length||!Number.isFinite(totalWeight)||totalWeight<=0||!Number.isInteger(data.total)||data.total<2||data.total>21)throw Error('当前手牌或剩余牌无效。');
 if(data.two&&data.total===21)return {natural:true,action:'N',actions:[],ev:2*A,rebuild:false,states:0};
 const defs=[['S',false],['H',false],...(data.canDouble&&data.two?[['D',true]]:[])],actions=defs.map(([action])=>({action,win:0,push:0,lose:0,ev:0,stake:action==='D'?2:1}));
 for(const scenario of scenarios){
  const c=scenario.counts?.slice();if(!Array.isArray(c)||c.length!==10||c.some((n,i)=>!Number.isInteger(n)||n<0||n>full[i]))throw Error('剩余牌超过单副牌数量。');
  const n=sum(c);if(n<1)throw Error('未知牌池至少应包含一张庄家底牌；请核对牌堆是否已重建。');
  const code=codeOf(c),w=scenario.weight/totalWeight;
  for(const row of actions){const v=row.action==='S'?stand(c,n,code,data.total,-1):draw(c,n,code,data.total,!!data.soft,-1,row.action==='D');row.win+=w*v[0];row.push+=w*v[1];row.lose+=w*v[2];row.ev+=w*ev(v)*row.stake;}
 }
 actions.sort((x,y)=>y.ev-x.ev||x.stake-y.stake||(['S','H','D'].indexOf(x.action)-['S','H','D'].indexOf(y.action)));
 return {action:actions[0].action,ev:actions[0].ev,actions,rebuild,states,playerStates:pMemo.size,dealerStates:dMemo.size};
}
if(typeof module==='object'&&module.exports)module.exports=GWYFBlackjackSolve;
