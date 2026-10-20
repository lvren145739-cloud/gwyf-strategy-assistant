/* Recognition can update this visible hand, never archive or press game buttons. */
const VisionRecognition=(()=>{
'use strict';
function assess(state,out){
 const reasons=[];
 if(!out||!Array.isArray(out.cards))return {ok:false,reasons:['识别结果格式无效']};
 const cards=out.cards.filter(c=>!c.faceDown),players=cards.filter(c=>c.role==='player'),dealer=cards.filter(c=>c.role==='dealer');
 if(out.autoReady!==true)reasons.push('整手识别尚未通过校验');
 if((out.warnings||[]).length)reasons.push(...out.warnings);
 if(cards.some(c=>!Number.isFinite(c.score)||c.score<.94||!Number.isFinite(c.suitScore)||c.suitScore<.92||!Number.isFinite(c.cardScore)||c.cardScore<.94))reasons.push('牌面清晰度未达到自动计算条件');
 if(out.cards.some(c=>c.review))reasons.push('存在需要核对的牌');
 if(cards.some(c=>!VisionState.ranks.includes(c.rank)||!VisionState.suits.includes(c.suit)))reasons.push('点数或花色没有读全');
 if(cards.some(c=>!['player','dealer'].includes(c.role)))reasons.push('牌的归属不完整');
 if(state.mode==='poker'&&(players.length!==5||dealer.length))reasons.push('扑克必须是自己的完整五张牌');
 if(state.mode==='blackjack'&&(players.length<2||dealer.length<1))reasons.push('需要至少两张手牌和庄家明牌');
 const ids=cards.map(c=>c.rank+':'+c.suit);
 if(new Set(ids).size!==ids.length)reasons.push('单副牌中出现了重复牌面');
 if(out.cards.filter(c=>c.faceDown).some(c=>c.role!=='dealer')||out.cards.filter(c=>c.faceDown).length>1)reasons.push('暗牌的数量或归属不确定');
 if(!reasons.length){try{VisionState.commit(state,cards);}catch(e){reasons.push(e.message);}}
 return {ok:reasons.length===0,reasons:[...new Set(reasons)],cards};
}
return {assess};
})();
if(typeof module!=='undefined')module.exports=VisionRecognition;
