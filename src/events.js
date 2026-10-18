let renderPending=false,pointerBusy=false;
function commit(){save();render();}
function rememberTable(kind){tableUndo[kind].push(structuredClone(state[kind].wagers));if(tableUndo[kind].length>300)tableUndo[kind].shift();}
function changeItem(id,amount){if(!guideItems.some(it=>it.id===id))return;state.owned[id]=Math.round(E.clamp(Number(amount)||0,0,999));invalidatePoker();commit();}
function closeNav(){$('sidebar').classList.remove('open');$('navShade').classList.remove('show');const b=document.querySelector('[data-action="menu"]');if(b)b.setAttribute('aria-expanded','false');}
function exportSave(){save();const blob=new Blob([JSON.stringify({app:'GWYF Companion',version:VERSION,savedAt:new Date().toISOString(),state},null,2)],{type:'application/json;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='梭哈决策器-存档-'+new Date().toISOString().slice(0,10)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('存档已导出，可在另一台设备导入继续。');}
document.addEventListener('pointerdown',()=>{pointerBusy=true;},{capture:true});
document.addEventListener('pointerup',()=>{setTimeout(()=>{pointerBusy=false;if(renderPending){renderPending=false;render();}},0);},{capture:true});
document.addEventListener('pointercancel',()=>{pointerBusy=false;if(renderPending){renderPending=false;render();}},{capture:true});
document.addEventListener('click',e=>{
 const nav=e.target.closest('[data-go]');if(nav){navigate(nav.dataset.go);return;}
 const t=e.target.closest('[data-action]');if(!t||t.disabled)return;const action=t.dataset.action,v=t.dataset.value;
 if(action==='set'){setPath(t.dataset.path,v);return;}
 if(action==='go'){navigate(v);return;}
 if(action==='applyPlan'){
  if(v==='money')state.money.color=singleModel(v).action;
  else if(v==='keno')state.keno.picks=Number(singleModel(v).action);
  else if(v==='roulette'||v==='baccarat'){rememberTable(v);state[v].wagers=presetWagers(v,v==='roulette'?'red':state.profile.goal==='safe'?'player':'tie',state[v].base*state[v].multiple);}
  else if(v==='hilo'){const pr=state.profile.risk==='careful'?.75:.5;state.hilo.threshold=Math.round((state.hilo.side==='under'?pr:1-pr)*100);}
  else if(v==='crash')state.crash.target=1.5;
  else if(v==='mines'){state.mines.mine=1;state.mines.k=0;state.mines.target=Math.max(1,1+E.settle(25/24-1,{...buffs(),cameraRate:0}));}
  else if(v==='dragon'||v==='penguin'){state[v].level=0;state[v].target=1+E.settle(E[v][1]-1,{...buffs(),cameraRate:0});}
  else return;
  navigate(v);toast('已填入总览推荐方案；直接选游戏会保留原局面。');return;
 }
 if(action==='scrollResults'){$('resultRegion')?.scrollIntoView({behavior:'smooth',block:'start'});return;}
 if(action==='menu'){const open=$('sidebar').classList.toggle('open');$('navShade').classList.toggle('show',open);t.setAttribute('aria-expanded',String(open));if(open)setTimeout(()=>$('navSearch').focus(),100);return;}
 if(action==='navFilter'){floorOnly=!floorOnly;renderNav();return;}
 if(action==='export'){exportSave();return;}
 if(action==='import'){$('importFile').click();return;}
 if(action==='item'){changeItem(v,owned(v)+1);return;}
 if(action==='itemMinus'){changeItem(v,owned(v)-1);return;}
 if(action==='clearItems'){state.owned={};invalidatePoker();commit();return;}
 if(action==='pickCard'){openPicker(Number(v));return;}
 if(action==='pokerEntryCard'){enterPokerCard(Number(v));return;}
 if(action==='pokerEntryClear'){rememberPokerEntry();state.poker.cards=Array(5).fill(null);state.poker.entry=0;invalidatePoker();commit();return;}
 if(action==='pokerEntryUndo'){const prev=pokerEntryUndo.pop();if(prev){state.poker.cards=prev.cards;state.poker.used=prev.used;state.poker.entry=prev.entry;invalidatePoker();commit();}return;}
 if(action==='pokerEntryClose'){state.poker.entry=-1;commit();return;}
 if(action==='pokerExchange'){pokerExchange();return;}
 if(action==='solvePoker'){solvePoker();return;}
 if(action==='cancelPoker'){invalidatePoker();render();toast('已取消，可修改局面后重新计算。');return;}
 if(action==='usedCard'){const id=Number(v);if(state.poker.cards.includes(id)||pokerJob)return;pokerEntryUndo=[];const a=state.poker.used;a.includes(id)?a.splice(a.indexOf(id),1):a.push(id);invalidatePoker();commit();return;}
 if(action==='pokerClearUsed'){pokerEntryUndo=[];state.poker.used=[];invalidatePoker();commit();return;}
 if(action==='pokerNext'){
  if(state.poker.cards.some(id=>!Number.isInteger(id))||new Set(state.poker.cards).size!==5){toast('先录入完整且不重复的本手五张牌。');return;}
  state.poker.used=[...new Set([...state.poker.used,...state.poker.cards])];state.poker.cards=Array(5).fill(null);state.poker.entry=0;state.poker.track=false;pokerEntryUndo=[];invalidatePoker();commit();toast('当前5张已归档，换掉的旧牌此前已自动记录。');return;
 }
 if(action==='slotCell'){state.slots.board[Number(v)]=state.slots.symbol;commit();return;}
 if(action==='slotFill'){state.slots.board=Array(9).fill(state.slots.symbol);commit();return;}
 if(action==='slotReset'){state.slots.board=[0,1,2,1,0,3,2,3,0];commit();return;}
 if(action.startsWith('wager')||action==='preset'){
  const [kind,key]=String(v).split(':');if(!['roulette','baccarat'].includes(kind))return;const a=state[kind],defs=kind==='roulette'?E.roulette:E.baccaratDefs;
  if(action==='wagerUndo'){if(tableUndo[kind].length)a.wagers=tableUndo[kind].pop();else if(a.wagers.length)a.wagers.pop();}
  else if(action==='wagerPlace'&&Object.hasOwn(defs,key)){if(a.wagers.length>=2000){toast('下注记录已达2000条，请合并金额或清空桌面。');return;}rememberTable(kind);a.wagers.push({key,amount:Math.round(a.base*a.multiple*100)/100});}
  else if(action==='wagerRemove'){rememberTable(kind);a.wagers=a.wagers.filter(w=>w.key!==key);}
  else if(action==='wagerClear'){rememberTable(kind);a.wagers=[];}
  else if(action==='preset'){rememberTable(kind);a.wagers=presetWagers(kind,key,Math.round(a.base*a.multiple*100)/100);}
  commit();return;
 }
 if(action==='dice'){if(crapsState().result===null)state.craps.rolls.push(Number(v));commit();return;}
 if(action==='diceUndo'){state.craps.rolls.pop();commit();return;}
 if(action==='diceReset'){state.craps.rolls=[];commit();return;}
 if(action==='bjDealerAdd'){const i=bjIndex(v);if(state.bj.mode==='cards'&&state.bj.dealer&&!bjDealerDone()&&i>=0&&state.bj.dealerCards.length<12&&bjHistoryCaps()[i]>state.bj.used[i])state.bj.dealerCards.push(v);commit();return;}
 if(action==='bjDealerUndo'){state.bj.dealerCards.pop();commit();return;}
 if(action==='bjArchive'){archiveBJ();return;}
 if(action==='bjArchiveUndo'){if(bjCanUndoArchive()){const a=bjArchiveUndo;Object.assign(state.bj,{cards:a.cards,dealer:a.dealer,dealerCards:a.dealerCards,used:a.used,recent:a.recent});bjArchiveUndo=null;commit();}return;}
 if(action==='bjPhase'){state.bj.first=v==='initial'&&!(state.bj.type==='hard'&&state.bj.hard>=21);commit();return;}
 if(action==='bjAdd'){if(state.bj.cards.length<12)state.bj.cards.push(v);commit();return;}
 if(action==='bjUndo'){state.bj.cards.pop();commit();return;}
 if(action==='bjReset'){state.bj.cards=[];commit();return;}
 if(action==='bjUsedAdd'||action==='bjUsedMinus'){const i=Number(v);if(!Number.isInteger(i)||i<0||i>9)return;const d=action==='bjUsedAdd'?1:-1;if(d>0&&state.bj.used[i]>=bjHistoryCaps()[i]||d<0&&state.bj.used[i]<=0)return;state.bj.used[i]+=d;state.bj.recent.push(d*(i+1));if(state.bj.recent.length>2000)state.bj.recent.shift();commit();return;}
 if(action==='bjUsedUndo'){const v=state.bj.recent.pop();if(v){const i=Math.abs(v)-1;state.bj.used[i]=Math.max(0,Math.min(i===9?16:4,state.bj.used[i]-Math.sign(v)));}commit();return;}
 if(action==='bjClearUsed'){bjArchiveUndo=null;state.bj.used=Array(10).fill(0);state.bj.recent=[];commit();return;}
 if(action==='hiloPreset'){const pr=Number(v);state.hilo.threshold=Math.round((state.hilo.side==='under'?pr:1-pr)*100);commit();return;}
 if(action==='minePreset'){const [m,k]=v.split(':').map(Number);state.mines.mine=m;state.mines.k=k;commit();return;}
 if(action==='mineSafe'){state.mines.k=Math.min(25-state.mines.mine,state.mines.k+1);commit();return;}
 if(action==='mineRoute'){const [m,k]=v.split(':').map(Number),route=E.minesRoutes(state.mines.target,buffs().a).find(r=>r.m===m&&r.k===k);if(!route)return;state.mines.mine=m;state.mines.k=0;commit();toast(`已填入新局${m}雷；安全${k}格后提现即可达到目标。`);return;}
 if(action==='mineUndo'){state.mines.k=Math.max(0,state.mines.k-1);commit();return;}
 if(action==='mineReset'){state.mines.k=0;commit();return;}
 if(action==='plinkoRecord'){state.plinko.samples[state.plinko.pocket]++;state.plinko.recent.push(state.plinko.pocket);state.plinko.recent=state.plinko.recent.slice(-2000);commit();return;}
 if(action==='plinkoUndo'){const id=state.plinko.recent.pop();if(id===undefined){toast('没有可撤销的最近落槽记录。');return;}state.plinko.samples[id]=Math.max(0,state.plinko.samples[id]-1);commit();return;}
 if(action==='plinkoClear'){state.plinko.samples=Array(12).fill(0);state.plinko.recent=[];commit();return;}
 if(action==='recordBudget'){const net=state.budget.net;if(!net){toast('请填写这次实际净盈亏。');return;}if(state.profile.bankroll+net<0){toast('净亏损超过记录余额，请核对余额与金额。');return;}state.profile.bankroll=E.clamp(state.profile.bankroll+net,0,1e15);state.history.unshift({net,label:state.budget.label||meta[state.tab][1],time:new Date().toISOString()});state.history=state.history.slice(0,200);state.budget.net=0;state.budget.label='';commit();toast('实际盈亏已记录，工具余额已更新。');return;}
 if(action==='removeBudget'){const i=Number(v),r=state.history[i];if(!r)return;if(state.profile.bankroll-r.net<0){toast('余额后来已被修改，无法直接回滚此条；请先核对当前余额。');return;}state.profile.bankroll=E.clamp(state.profile.bankroll-r.net,0,1e15);state.history.splice(i,1);commit();return;}
});
document.addEventListener('change',e=>{const t=e.target;
 if(t.dataset.path){if(t.type==='number'&&!Number.isFinite(t.valueAsNumber)){toast('请输入有效数字，已保留上一次设置。');render();return;}setPath(t.dataset.path,t.type==='checkbox'?t.checked:t.type==='number'?t.valueAsNumber:t.value);return;}
 if(t.dataset.itemCount){changeItem(t.dataset.itemCount,t.value);return;}
 if(t.dataset.wagerKind){const kind=t.dataset.wagerKind,key=t.dataset.wagerKey,n=Number(t.value);if(!Number.isFinite(n)||n<0){toast('请输入非负金额。');render();return;}rememberTable(kind);state[kind].wagers=state[kind].wagers.filter(w=>w.key!==key);const amount=Math.round(Math.min(n,1e12)*100)/100;if(amount>0)state[kind].wagers.push({key,amount});commit();}
});
document.addEventListener('input',e=>{const t=e.target;if(t.id==='navSearch'){search=t.value;renderNav();return;}if(t.dataset.range==='hilo'){state.hilo.threshold=Number(t.value);const oldFocus=document.activeElement;const holder=$('content');const next=document.createElement('div');next.innerHTML=drawHiLo();const currentRight=holder.querySelector('#resultRegion'),newRight=next.querySelector('#resultRegion');if(currentRight&&newRight)currentRight.innerHTML=newRight.innerHTML;const label=holder.querySelector('.row.between .gold');if(label)label.textContent=t.value+'%';const exact=holder.querySelector('[data-path="hilo.threshold"]');if(exact)exact.value=t.value;renderInlineDecision();save();}});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeNav();return;}if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName)&&!$('cardPicker')){e.preventDefault();if(innerWidth<=760){$('sidebar').classList.add('open');$('navShade').classList.add('show');}$('navSearch').focus();}});
$('navShade').addEventListener('click',closeNav);
$('importFile').addEventListener('change',async e=>{const file=e.target.files?.[0];if(!file)return;try{if(file.size>2*1024*1024)throw Error('文件超过2MB，请选择本工具导出的JSON存档。');const obj=JSON.parse(await file.text());if(obj.version!==VERSION||!obj.state||typeof obj.state!=='object'||Array.isArray(obj.state))throw Error('这不是v7决策器存档；原版浏览器数据会在首次打开时自动尝试迁移。');const next=normalize(obj.state);pokerEntryUndo=[];bjArchiveUndo=null;invalidatePoker();state=next;tableUndo={roulette:[],baccarat:[]};commit();toast('存档已导入并校验。');}catch(err){toast('导入失败：'+err.message);}finally{e.target.value='';}});
window.addEventListener('hashchange',()=>{const id=location.hash.slice(1);if(meta[id]&&id!==state.tab)navigate(id);});
function updateNavOffset(){document.documentElement.style.setProperty('--nav-offset',(document.querySelector('.topbar').offsetHeight+12)+'px');}
if(typeof ResizeObserver!=='undefined'){const navObserver=new ResizeObserver(updateNavOffset);navObserver.observe(document.querySelector('.topbar'));}else window.addEventListener('resize',updateNavOffset);
readStored();if(meta[location.hash.slice(1)])state.tab=location.hash.slice(1);save();render();focusGameControls();
