const bjFull=[4,4,4,4,4,4,4,4,4,16],bjNames={H:'要牌 HIT',S:'停牌 STAND',D:'加倍 DOUBLE'};
let bjArchiveUndo=null;let bjJob=null;const bjCache=new Map();
function bjSituation(){const a=state.bj;if(a.mode==='cards')return {...E.bjValue(a.cards),two:a.cards.length===2,label:a.cards.join(' + ')};if(a.type==='hard')return {total:a.hard,soft:false,two:a.first&&a.hard<21,label:'硬手'+a.hard};if(a.type==='soft')return {total:11+a.soft,soft:true,two:a.first,label:'软手'+(11+a.soft)};return {total:a.pair==='A'?12:Number(a.pair)*2,soft:a.pair==='A',two:true,label:a.pair+' + '+a.pair};}
function bjKnown(){const a=state.bj;return a.mode==='cards'?a.cards:a.type==='pair'?[a.pair,a.pair]:a.type==='soft'&&a.first?['A',String(a.soft)]:[];}
function bjIndex(c){return ['J','Q','K'].includes(c)?9:bjRanks.indexOf(String(c));}
function bjTableCards(){return [...bjKnown(),...(state.bj.dealer?[state.bj.dealer]:[]),...state.bj.dealerCards];}
function bjHistoryCaps(){const c=bjFull.slice();for(const r of bjTableCards()){const i=bjIndex(r);if(i>=0)c[i]--;}return c.map(n=>Math.max(0,n));}
function bjModel(){
 const a=state.bj,s=bjSituation(),known=bjKnown(),counts=bjFull.map((v,i)=>v-a.used[i]);
 for(const r of bjTableCards()){const i=bjIndex(r);if(i>=0)counts[i]--;}
 const revealed=a.dealerCards.length>0,n=counts.reduce((z,v)=>z+v,0),exact=known.length>=2,canDouble=!revealed&&E.bjCanDouble(s)&&state.profile.bankroll>=2*state.profile.stake;
 let error=a.mode==='cards'&&a.cards.length<2?'请先输入至少两张自己的牌。':!a.dealer?'请先选择庄家明牌。':counts.some(v=>v<0)?'手牌、庄家明牌与已用牌超出单副牌数量，请修正记录。':s.total>21?'本手已爆牌，不能再要牌。':!revealed&&n<1?'未知池应留有庄家底牌；请核对记录及游戏是否已重建牌堆。':'';
 const payload={counts,total:s.total,soft:s.soft,two:s.two,canDouble,dealer:a.dealer,a:1+.5*owned('confidence'),b:owned('statue')?0:.75**owned('insurance'),cameraRate:buffs().cameraRate};
 let scope=exact?'完整手牌 · 剩余牌模型':'快捷点数 · 组成估算';
 if(!error&&!exact&&s.two){
  const scenarios=[];for(let i=0;i<10;i++)for(let j=i;j<10;j++){const v=E.bjValue([bjRanks[i],bjRanks[j]]),w=i===j?counts[i]*(counts[i]-1)/2:counts[i]*counts[j];if(w>0&&v.total===s.total&&v.soft===s.soft){const c=counts.slice();c[i]--;c[j]--;scenarios.push({counts:c,weight:w});}}
  if(!scenarios.length||n<3)error='剩余牌无法组成所选两张手牌，请核对计数。';else{payload.scenarios=scenarios;delete payload.counts;}
 }else if(!error&&!exact&&n<4)error='快捷点数缺少手牌组成，牌堆接近耗尽时请改用逐张输入。';
 return {s,counts,n,exact,revealed,canDouble,payload,error,scope,key:JSON.stringify(payload)};
}
function bjSolution(m){
 if(m.error||m.revealed||m.s.two&&m.s.total===21)return null;
 if(bjCache.has(m.key))return bjCache.get(m.key);
 if(bjJob?.key===m.key)return null;
 if(bjJob){clearTimeout(bjJob.timer);clearTimeout(bjJob.deadline);bjJob.worker?.terminate();}
 const job={key:m.key};bjJob=job;
 const done=value=>{if(bjJob!==job)return;clearTimeout(job.deadline);job.worker?.terminate();bjJob=null;bjCache.set(m.key,value);if(bjCache.size>30)bjCache.delete(bjCache.keys().next().value);if(state.tab==='bj')render();};
 job.timer=setTimeout(()=>{
  try{
   const url=URL.createObjectURL(new Blob(['const solve='+GWYFBlackjackSolve.toString()+';onmessage=e=>{try{postMessage({result:solve(e.data)})}catch(x){postMessage({error:x.message})}}'],{type:'text/javascript'}));
   try{job.worker=new Worker(url);}finally{URL.revokeObjectURL(url);}
   job.worker.onmessage=e=>done(e.data);job.worker.onerror=e=>{e.preventDefault();done({error:'计算线程异常，请刷新重试。'});};
   job.deadline=setTimeout(()=>done({error:'本局计算超时，请逐张输入完整手牌后重试。'}),15000);job.worker.postMessage(m.payload);
  }catch{try{done({result:GWYFBlackjackSolve(m.payload)});}catch(e){done({error:e.message});}}
 },80);
 return null;
}
function drawBJ(){
 const a=state.bj,m=bjModel(),s=m.s,empty=a.mode==='cards'&&a.cards.length<2,natural=!m.error&&s.two&&s.total===21,canDouble=!m.error&&m.canDouble,solved=bjSolution(m),result=solved?.result,error=m.error||solved?.error;
 const title=empty?'等待手牌':!a.dealer?'等待庄家明牌':error?(s.total>21?'已爆牌 BUST':'请核对牌局'):natural?'自然21 · 3×已结算':m.revealed?'庄家阶段 · 可归档':result?bjNames[result.action]:'正在比较动作…';
 const desc=error?esc(error):natural?'初始两张21点已结算，无需继续操作。':m.revealed?'已记录庄家后续牌；本手结束后归档双方已知牌。':result?`每份初始下注净期望 ${signed(result.ev,3)}；${m.exact?'已扣除当前手牌与已用牌。':'手牌组成不全，结果为估算。'}`:'按当前牌池比较要牌、停牌与合法加倍。';
 const bjBuff=buffBlock(`<div class="chips">${chip('本游戏正利润 ×'+f(m.payload.a,2))}${chip('亏损保留 '+pc(m.payload.b))}${m.payload.cameraRate?chip('含相机额外收入 '+pc(m.payload.cameraRate),'unknown'):''}</div>`);
 let controls=`<div class="bj-selection">`+choices('bj.mode',a.mode,[['quick','快捷点数'],['cards','逐张输入']],2);
 if(a.mode==='quick'){
  controls+=`<h3>当前手牌类型</h3>${choices('bj.type',a.type,[['hard','硬手'],['soft','含A软手'],['pair','两张对子']],3)}<div class="spacer"></div>`;
  if(a.type==='hard')controls+=choices('bj.hard',a.hard,Array.from({length:18},(_,i)=>[i+4,String(i+4)]),6);
  if(a.type==='soft')controls+=choices('bj.soft',a.soft,Array.from({length:9},(_,i)=>[i+2,'软'+(i+13)]),3);
  if(a.type==='pair')controls+=choices('bj.pair',a.pair,bjRanks.map(r=>[r,r+'+'+r]),5);
  else controls+=`<div class="bj-phase-label">手牌阶段</div><div class="choices" style="--cols:2"><button class="choice ${s.two?'selected':''}" data-action="bjPhase" data-value="initial" aria-pressed="${s.two}" ${a.type==='hard'&&a.hard>=21?'disabled':''}>尚未要牌 · 2张</button><button class="choice ${!s.two?'selected':''}" data-action="bjPhase" data-value="later" aria-pressed="${!s.two}">已要牌 · 3张以上</button></div>`;
 }else controls+=`<div class="cards-row">${a.cards.map(c=>`<span class="playing">${c}</span>`).join('')||'<p class="micro">先点选手牌</p>'}</div><div class="choices" style="--cols:7">${['A',...ranks.filter(r=>r!=='A')].map(c=>`<button class="choice" data-action="bjAdd" data-value="${c}" ${a.cards.length>=12?'disabled':''}>${c}</button>`).join('')}</div><div class="row" style="margin-top:12px">${btn('撤销一张','bjUndo','','ghost small')}${btn('清空手牌','bjReset','','ghost small')}</div><p class="micro">手牌张数决定能否加倍，无需另设开关。</p>`;
 controls+=`<h3>庄家明牌</h3>${choices('bj.dealer',a.dealer,bjRanks.map(r=>[r,r]),5)}<div class="spacer"></div><div class="chips">${chip('庄家软17停牌','neutral')}${chip(empty?'待录入手牌':natural?'自然21已结算':m.revealed?'庄家阶段 · 待归档':canDouble?'初始两张 · 可加倍':'本手不能再加倍',canDouble?'':'neutral')}</div>`;
 controls+='<div class="bj-live-decision"></div>';
 if(a.mode==='cards')controls+=bjDealerEntry();
 controls+='</div>'+bjBuff;

 controls+=details('原版固定规则与依据',`<p class="note">单副52张牌跨局消耗，抽空时重建；庄家不足17要牌，软17停牌。初始两张可加倍，加倍只补一张。自然21立即3×总返还；普通21按点数比较，平局退回本金。庄家不预先检查自然21。原版不提供分牌或投降。</p><p class="note">${link('https://justinbecker.dev/blog/2026/05/30/gamble-with-your-friends-casino-analysis/#blackjack','原版逆向分析 ↗')} · ${link(fact('bj').url,'v1.0.30社区资料 ↗')}。按公开规则建立模型，未独立验证游戏程序全部结算分支。</p>`);
 controls+=check('展开已用牌 · 点牌加一（已记录始终扣除）','bj.track',a.track);
 if(a.track){const caps=bjHistoryCaps();controls+=`<div class="row between"><span class="micro">已记录 ${a.used.reduce((z,v)=>z+v,0)} 张 · 点牌面 +1</span><span class="micro" role="status">自动更新推荐</span></div><div class="rank-counts bj-history">${bjRanks.map((r,i)=>`<div class="rank-count"><button class="bj-count-add" data-action="bjUsedAdd" data-value="${i}" aria-label="已用${r}点加一，当前${a.used[i]}张" ${a.used[i]>=caps[i]?'disabled':''}><b>${r}</b><strong>${a.used[i]}</strong><small>${a.used[i]>=caps[i]?'已记满':'+1'}</small></button><button class="bj-count-minus" data-action="bjUsedMinus" data-value="${i}" aria-label="已用${r}点减一" ${a.used[i]<=0?'disabled':''}>−</button></div>`).join('')}</div><div class="bj-count-result" role="status"><b>${title}</b><span>${desc}</span></div><div class="row bj-history-actions"><button class="btn ghost small" data-action="bjUsedUndo" ${a.recent.length?'':'disabled'}>撤销计牌</button>${btn('游戏已洗牌 · 清空历史','bjClearUsed','','ghost small')}</div><p class="note">只录入之前已离开牌堆的牌；当前手牌与庄家牌由上方自动扣除，归档时一并转入历史。10包含10/J/Q/K共16张。庄家底牌未知时不要录入，揭开后在下一局记入。游戏重建牌堆时清空历史。</p>`;}
 let right=panel('推荐动作 · 考虑已用牌',hero(title,desc,m.revealed?'本手记录 · 等待归档':m.scope,result?.action==='D'?'caution':'neutral')+`<div class="chips">${chip(esc(s.label||'待输入'),'neutral')}${chip(a.dealer?'庄家 '+a.dealer:'庄家待选','neutral')}${chip('已用 '+a.used.reduce((z,v)=>z+v,0)+' 张','neutral')}</div>`+
 (result?table(['动作','净期望 / 初始下注','赢 / 和 / 输'],result.actions.map(r=>({selected:r.action===result.action,cells:[bjNames[r.action],signed(r.ev,4)+(r.action==='D'?'（投入2份）':''),pc(r.win,1)+' / '+pc(r.push,1)+' / '+pc(r.lose,1)]})))+`<p class="note">按净期望最高推荐。要牌包含随后继续要牌或停牌的选择；加倍仅补一张。以最初下注为统一分母，加倍盈亏已乘2。当前每份 ${f(state.profile.stake,2)}，推荐动作期望净额 ${signed(result.ev*state.profile.stake,2)}。</p>`:'')+
 (!m.revealed&&!canDouble&&E.bjCanDouble(s)&&!error?alert('当前资金不足初始下注的2倍，已排除加倍。'):'')+
 (!m.exact?`<p class="note">快捷初始硬手会按剩余牌枚举可行的两张组成并加权；已要牌但只填点数时未扣未知手牌，属于近似。逐张输入可准确扣除当前手牌。</p>`:'')+
 details('计算口径与道具',`<p class="note">保留庄家底牌未知，不按已知底牌选择动作。模型按单副牌不放回抽取，牌堆耗尽时重建；按S17规则计算庄家最终点数。相同期望优先较低投入，再优先停牌。当前输入假定手牌与历史来自同一副；若本手已跨过实际洗牌边界，无法准确标注旧副手牌，请从新局重新记录。</p><p class="note">本局正利润 ×${f(m.payload.a,2)}，亏损保留 ${pc(m.payload.b)}${m.payload.cameraRate?'，含相机团队额外收入 '+pc(m.payload.cameraRate):''}。纳入自信、保险、雕像与现有相机模型；酒和麦克风缺少该游戏直接结算依据，未计入。所有概率均是所述规则模型的条件结果，不是游戏下一张牌预测。</p>${result?.rebuild?alert('某些后续分支会抽空牌堆，计算已包含新一副52张牌。','info'):''}`));
 if(!error&&!natural&&!m.revealed){
  const scenarios=m.payload.scenarios||[{counts:m.counts,weight:1}],weight=scenarios.reduce((z,r)=>z+r.weight,0),prob=Array(10).fill(0);
  for(const r of scenarios){const n=r.counts.reduce((z,v)=>z+v,0),draw=n===1?bjFull:r.counts,dn=n===1?52:n;draw.forEach((v,i)=>prob[i]+=r.weight/weight*v/dn);}
  const dist=prob.map((p,i)=>({p,rank:bjRanks[i],total:E.bjNext(s.total,s.soft,bjRanks[i])}));
  right+=panel('下一张风险',`<div class="stats">${stat('下一张爆牌',pc(dist.filter(r=>r.total>21).reduce((z,r)=>z+r.p,0)),'negative')}${stat('下一张到21',pc(dist.filter(r=>r.total===21).reduce((z,r)=>z+r.p,0)),'positive')}</div>`+details('展开点数分布',table(['下一张','概率','新点数'],dist.map(r=>[r.rank,pc(r.p,3),r.total>21?'爆牌':r.total])))+`<p class="note">下一张风险与动作期望分别计算；牌堆仅剩未知底牌时，下一次要牌从重建的52张中抽取。</p>`);
 }
 return workspace(panel('快速选择牌局',controls),right);
}

function bjCanArchive(){const a=state.bj;const c=bjFull.map((n,i)=>n-a.used[i]);for(const r of bjTableCards())c[bjIndex(r)]--;return a.mode==='cards'&&a.cards.length>=2&&!!a.dealer&&c.every(n=>n>=0);}
function bjCanUndoArchive(){const a=state.bj;return !!bjArchiveUndo&&a.cards.length===0&&!a.dealer&&a.dealerCards.length===0&&JSON.stringify(a.used)===JSON.stringify(bjArchiveUndo.after);}
function bjDealerDone(){const a=state.bj;return a.dealerCards.length>0&&E.bjValue([a.dealer,...a.dealerCards]).total>=17;}
function bjDealerEntry(){const a=state.bj,cap=bjHistoryCaps(),dv=E.bjValue([a.dealer,...a.dealerCards]);return `<div class="bj-dealer-followup"><h3>庄家后续牌 <small>含揭开的底牌；10含J/Q/K</small></h3><div class="bj-dealer-record"><span class="micro">${a.dealerCards.length?a.dealerCards.join(' · ')+'（庄家'+dv.total+(dv.total>21?' · 爆牌':bjDealerDone()?' · 停牌':' · 需补牌')+'）':'底牌未揭开时留空'}</span><button class="btn ghost small" data-action="bjDealerUndo" ${a.dealerCards.length?'':'disabled'}>撤销</button></div><div class="choices" style="--cols:5">${bjRanks.map((c,i)=>`<button class="choice" data-action="bjDealerAdd" data-value="${c}" ${!a.dealer||bjDealerDone()||a.dealerCards.length>=12||cap[i]<=a.used[i]?'disabled':''}>${c}</button>`).join('')}</div><div class="row bj-archive-actions"><button class="btn primary small" data-action="bjArchive" ${bjCanArchive()?'':'disabled'}>归档双方牌 · 下一局</button>${bjCanUndoArchive()?btn('撤销归档','bjArchiveUndo','','ghost small'):''}</div></div>`;}
function archiveBJ(){
 if(!bjCanArchive())return;const a=state.bj,used=a.used.slice();for(const r of bjTableCards())used[bjIndex(r)]++;
 bjArchiveUndo={cards:a.cards.slice(),dealer:a.dealer,dealerCards:a.dealerCards.slice(),used:a.used.slice(),recent:a.recent.slice(),after:used.slice()};
 const n=a.cards.length+1+a.dealerCards.length;a.used=used;a.recent=[];a.cards=[];a.dealer='';a.dealerCards=[];save();render();toast('已将双方'+n+'张已知牌计入历史。未揭开的牌不猜记。');
}
