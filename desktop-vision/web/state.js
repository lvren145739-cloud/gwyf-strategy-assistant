/* Explicit, reversible visible-card history. Screenshots never archive by themselves. */
const VisionState=(()=>{
'use strict';
const ranks=['A','2','3','4','5','6','7','8','9','10','J','Q','K'];
const suits=['spades','hearts','diamonds','clubs'];
const pokerRanks=['2','3','4','5','6','7','8','9','10','J','Q','K','A'];
const blank=()=>({schema:1,mode:'blackjack',regions:{blackjack:{},poker:{}},aspect:{},owned:{},settings:{},team:'solo',
 blackjack:{player:[],dealer:[],used:Array(10).fill(0)},poker:{player:[],used:[],phase:'initial'},undo:null});
const clone=x=>JSON.parse(JSON.stringify(x));
function validateCards(cards,mode){
 if(!Array.isArray(cards)||cards.some(c=>!c||!ranks.includes(c.rank)||(mode==='poker'&&!suits.includes(c.suit))))throw Error('请先补全牌面。');
 if(mode==='poker'){
  const ids=cards.map(cardId);if(ids.length!==5||new Set(ids).size!==5)throw Error('扑克需要五张互不重复的牌。');
 }
}
function cardId(c){return suits.indexOf(c.suit)*13+pokerRanks.indexOf(c.rank);}
const rankIndex=r=>r==='A'?0:Math.min(10,['J','Q','K'].includes(r)?10:Number(r))-1;
function assertDeck(s){
 const hand=s.blackjack,counts=hand.used.slice();
 for(const c of [...hand.player,...hand.dealer])counts[rankIndex(c.rank)]++;
 if(counts.some((n,i)=>!Number.isInteger(n)||n<0||n>(i===9?16:4)))throw Error('记录超过单副牌数量；请检查识别结果或在游戏洗牌后重置牌堆。');
}
function commit(s,cards){
 const next=clone(s);const mode=s.mode;
 const player=cards.filter(c=>c.role==='player').map(({rank,suit})=>({rank,suit}));
 const dealer=cards.filter(c=>c.role==='dealer').map(({rank,suit})=>({rank,suit}));
 validateCards(player,mode);
 if(mode==='blackjack'){
  validateCards(dealer,mode);
  if(player.length<2||dealer.length<1)throw Error('请至少录入两张手牌和一张庄家明牌。');
  next.blackjack.player=player;next.blackjack.dealer=dealer;assertDeck(next);
 }else{
  const hand=next.poker,ids=player.map(cardId);
  if(ids.some(id=>hand.used.includes(id)))throw Error('这张牌已在已用牌中；请检查识别或先撤销错误归档。');
  if(hand.phase==='replacement'){
   const old=hand.player;
   for(const retained of old.filter(Boolean))if(!ids.includes(cardId(retained)))throw Error('补牌结果缺少保留牌，请核对五张牌。');
  }
  hand.player=player;
 }
 next.undo={label:'更新手牌',snapshot:clone({...s,undo:null})};
 return next;
}
function archive(s){
 const next=clone(s),hand=next[s.mode];
 if(!hand.player.length)throw Error('当前没有可归档手牌。');
 if(s.mode==='blackjack'){
  assertDeck(s);
  for(const c of [...hand.player,...hand.dealer])hand.used[rankIndex(c.rank)]++;
  hand.player=[];hand.dealer=[];
 }else{
  validateCards(hand.player,'poker');
  hand.used=[...new Set([...hand.used,...hand.player.map(cardId)])];hand.player=[];hand.phase='initial';
 }
 next.undo={label:'归档',snapshot:clone({...s,undo:null})};return next;
}
function discard(s,mask){
 if(s.mode!=='poker'||!Number.isInteger(mask)||mask<0||mask>31)throw Error('换牌计划无效。');
 const next=clone(s),hand=next.poker;validateCards(hand.player,'poker');
 if(hand.phase!=='initial')throw Error('本手已进入补牌阶段。');
 const discarded=hand.player.filter((_,i)=>!(mask&(1<<i))).map(cardId);
 if(!discarded.length)throw Error('推荐保留全部五张，无需换牌。');
 hand.used=[...new Set([...hand.used,...discarded])];
 hand.player=hand.player.map((c,i)=>mask&(1<<i)?c:null);hand.phase='replacement';
 next.undo={label:'换牌',snapshot:clone({...s,undo:null})};return next;
}
function resetDeck(s){
 const next=clone(s);
 if(s.mode==='blackjack')next.blackjack={player:[],dealer:[],used:Array(10).fill(0)};
 else next.poker={player:[],used:[],phase:'initial'};
 next.undo={label:'重置牌堆',snapshot:clone({...s,undo:null})};return next;
}
function restore(raw){
 // Saved state is untrusted. Keep only data fields used by the prototype.
 const s=blank();if(!raw||raw.schema!==1)return s;
 if(['blackjack','poker'].includes(raw.mode))s.mode=raw.mode;
 for(const mode of ['blackjack','poker']){
  const h=raw[mode];if(!h)continue;
  try{
   if(!Array.isArray(h.player)||h.player.length>16)continue;
   const known=h.player.filter(Boolean);validateCards(known,'blackjack');
   if(mode==='blackjack'){
    validateCards(h.dealer,'blackjack');
    if(h.dealer.length>16||!Array.isArray(h.used)||h.used.length!==10)continue;
    s.blackjack=clone(h);assertDeck(s);
   }else{
    if(known.some(c=>!suits.includes(c.suit))||!Array.isArray(h.used)||h.used.some(x=>!Number.isInteger(x)||x<0||x>51))continue;
    s.poker={player:clone(h.player),used:[...new Set(h.used)],phase:h.phase==='replacement'?'replacement':'initial'};
   }
  }catch(_){s[mode]=blank()[mode];}
 }
 if(raw.regions&&typeof raw.regions==='object')for(const mode of ['blackjack','poker'])for(const role of ['player','dealer']){
  const r=raw.regions[mode]?.[role];
  if(Array.isArray(r)&&r.length===4&&r.every(x=>Number.isFinite(x)&&x>=0&&x<=1)&&r[0]<r[2]&&r[1]<r[3])s.regions[mode][role]=r;
 }
 if(raw.aspect&&typeof raw.aspect==='object')for(const mode of ['blackjack','poker'])if(Number.isFinite(raw.aspect[mode]))s.aspect[mode]=raw.aspect[mode];
 for(const id of ['confidence','insurance','statue','stakeholder','drink','microphone','camera']){
  const v=raw.owned?.[id];if(Number.isInteger(v)&&v>=0&&v<=100)s.owned[id]=v;
 }
 if(raw.settings?.captureMode==='manual')s.settings.captureMode='manual';
 if(raw.team==='group')s.team='group';
 for(const [id,min,max] of [['tipsy',1,20],['melody',0,1]])if(Number.isFinite(raw.settings?.[id]))s.settings[id]=Math.max(min,Math.min(max,raw.settings[id]));
 return s;
}
return {ranks,suits,pokerRanks,blank,clone,rankIndex,cardId,commit,archive,discard,resetDeck,restore,assertDeck};
})();
if(typeof module!=='undefined')module.exports=VisionState;
