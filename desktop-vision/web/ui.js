'use strict';
const V=VisionState,E=GWYFEngine,$=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
let state=V.blank(),draft=[],frame=null,frameImage=null,selectRegion=null,drag=null,busy=false,worker=null,job=0,lastResult=null,compact=false,detections=[];
const glyph={spades:'♠',hearts:'♥',diamonds:'♦',clubs:'♣'};
const api=()=>window.pywebview?.api;
const nativeRequired=!!document.querySelector('meta[name="gwyf-desktop"]');
const bridgeMethods=['status','windows','select_window','capture','open_image','recognize','load_state','save_state','compact'];
let nativeReady=false,nativeConnecting=null,stateRevision=0;
function bridgeComplete(){return bridgeMethods.every(name=>typeof api()?.[name]==='function');}
function desktopCall(name,...args){
 const bridge=api();
 if(typeof bridge?.[name]!=='function')throw Error(bridge||nativeRequired?'桌面接口尚未连接完成，请点击“刷新”重新连接。':'请通过 Start-Windows.bat 启动；浏览器预览不能读取游戏窗口。');
 return bridge[name](...args);
}
function withTimeout(promise,ms,note){
 return new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error(note)),ms);Promise.resolve(promise).then(value=>{clearTimeout(timer);resolve(value);},error=>{clearTimeout(timer);reject(error);});});
}
function waitForBridge(){
 if(bridgeComplete())return Promise.resolve();
 return new Promise((resolve,reject)=>{const started=Date.now();const timer=setInterval(()=>{
  if(bridgeComplete()){clearInterval(timer);resolve();}
  else if(Date.now()-started>=12000){clearInterval(timer);reject(Error('桌面接口连接超时。请关闭旧浮窗，完整解压0.3版后使用 Start-Windows.bat 启动。'));}
 },100);});
}
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label=c=>c?`${glyph[c.suit]||''}${c.rank||'?'}`:'待补';
const red=c=>['hearts','diamonds'].includes(c?.suit)?'red':'';
function message(text,error=false){$('#status').textContent=text;$('#status').classList.toggle('error',error);}
function advice(title,body='',warn=false,kicker='当前手牌 · 已考虑已用牌'){
 $('#advice').classList.toggle('warn',warn);$('#advice').innerHTML=`<small>${esc(kicker)}</small><h1>${esc(title)}</h1><p>${esc(body)}</p>`;
}
let saveQueue=Promise.resolve();
function save(){
 stateRevision++;
 const snapshot=JSON.parse(JSON.stringify({...state,undo:null}));
 try{localStorage.setItem('gwyf-vision-v1',JSON.stringify(snapshot));}catch(_){}
 if(nativeReady)saveQueue=saveQueue.then(()=>desktopCall('save_state',snapshot)).catch(e=>message('状态未保存：'+e.message,true));
}
function stopSolver(){job++;if(worker){worker.terminate();worker=null;}lastResult=null;}
function render(){
 $$('[data-mode]').forEach(b=>b.classList.toggle('active',b.dataset.mode===state.mode));
 const h=state[state.mode];
 $('#autoLocate').classList.toggle('active',state.settings.captureMode!=='manual');
 $('#current').innerHTML=[['我',h.player],...(state.mode==='blackjack'?[['庄',h.dealer]]:[])].map(([n,cards])=>`<div class="cardsline"><small>${n}</small>${cards.length?cards.map(c=>`<span class="chip ${red(c)}">${esc(label(c))}</span>`).join(''):'<span class="muted">尚未录入</span>'}</div>`).join('');
 $('#undo').disabled=!state.undo;
 $('#archive').disabled=!h.player.length||h.player.some(c=>!c);
 $('#role option[value=dealer]').disabled=state.mode==='poker';
 if(state.mode==='poker')$('#role').value='player';
 $('[data-region=dealer]').hidden=state.mode==='poker';
 $('#suit').hidden=state.mode==='blackjack';
 $('#usedCount').textContent=(state.mode==='blackjack'?h.used.reduce((a,b)=>a+b,0):h.used.length)+' 张';
 if(state.mode==='blackjack')$('#used').innerHTML='<div class="used-grid">'+h.used.map((n,i)=>`<button data-add-used="${i}" title="点一次补记一张；右键减一">${i===0?'A':i+1} · ${n}</button>`).join('')+'</div><p class="muted">点一次加一，右键减一；10包含J/Q/K。不要重复补记当前牌。</p>';
 else $('#used').innerHTML='<div class="used-grid">'+h.used.map(id=>{const c={rank:V.pokerRanks[id%13],suit:V.suits[Math.floor(id/13)]};return `<span class="chip ${red(c)}">${esc(label(c))}</span>`;}).join('')+'</div>';
 const b=E.buffs(state.owned,state.settings,state.team);$('#buffLabel').textContent=`净赢 ×${(b.a*(1+b.cameraRate)).toFixed(2)} / 净亏 ${(b.b*100).toFixed(1)}%`;
 paintFrame();
}
function calculate(){
 stopSolver();const h=state[state.mode],id=job;
 if(!h.player.length){advice('等待识牌','选择游戏窗口，按 Ctrl+Shift+Space 自动识牌并计算。',false,'本地运行 · 按需截图');return;}
 if(h.player.some(c=>!c)){advice('等待补牌','已丢弃的牌已计入历史；补全新牌后重新计算。',true);return;}
 const b=E.buffs(state.owned,state.settings,state.team);let payload;
 try{
  if(state.mode==='blackjack'){
   V.assertDeck(state);const value=E.bjValue(h.player.map(c=>c.rank));
   if(value.total>21){advice('已爆牌','补录庄家已亮出的牌后，可归档本手。',true);return;}
   if(!h.dealer.length){advice('等待庄家明牌','请录入庄家第一张可见牌。',true);return;}
   if(h.dealer.length>1){advice('庄家阶段 · 可归档','庄家已亮出底牌；此时不再推荐玩家要牌。');return;}
   const counts=h.used.map((n,i)=>(i===9?16:4)-n);
   for(const c of [...h.player,...h.dealer])counts[V.rankIndex(c.rank)]--;
   payload={counts,...value,two:h.player.length===2,canDouble:h.player.length===2,dealer:['J','Q','K'].includes(h.dealer[0].rank)?'10':h.dealer[0].rank,...b};
  }else{
   if(h.phase==='replacement'){advice('补牌完成 · 等待结算','本手已经换过牌，不再推荐第二次换牌。');return;}
   payload={cards:h.player.map(V.cardId),used:h.used,objective:'ev',...b};
  }
  advice('计算中…','在后台工作线程中计算，界面仍可操作。');
  worker=new Worker('solver-worker.js');
  worker.onerror=()=>{if(id===job)advice('无法启动策略线程','请通过桌面启动器或本地HTTP打开。',true);};
  worker.onmessage=({data})=>{
   if(data.id!==job)return;
   if(data.error){advice('需要核对',data.error,true);return;}
   if(data.progress!=null){advice('计算中…',`扑克方案枚举 ${Math.min(100,Math.round(data.progress*100))}%`);return;}
   lastResult=data.result;worker.terminate();worker=null;
   if(state.mode==='blackjack'){
    const names={H:'要牌 HIT',S:'停牌 STAND',D:'加倍 DOUBLE',N:'自然21 · 已结算'};
    const r=data.result;advice(names[r.action]||'请核对',r.natural?'初始两张自然21，按原版模型总返还3×。':`期望净收益 ${r.ev>=0?'+':''}${r.ev.toFixed(3)} / 原始下注 · ${E.bjValue(h.player.map(c=>c.rank)).total}点${r.rebuild?' · 包含牌堆重建分支':''}`);
   }else{
    const r=data.result.solutions[0],keep=h.player.filter((_,i)=>r.mask&(1<<i));
    advice(r.mask===31?'保留全部五张':`保留 ${keep.length} 张 · 换 ${5-keep.length} 张`,`${keep.length?keep.map(label).join(' '):'全部换掉'} · 期望净收益 ${r.ev>=0?'+':''}${r.ev.toFixed(3)}`);
    if(r.mask!==31){const button=document.createElement('button');button.textContent='按推荐换牌 · 丢弃牌立即入历史';button.className='primary full';button.id='discard';button.onclick=()=>mutate(()=>V.discard(state,r.mask),'已记录丢弃牌，按快捷键识别补牌后的五张牌。');$('#advice').append(button);}
   }
  };
  worker.postMessage({id,mode:state.mode,payload});
 }catch(e){advice('需要核对',e.message,true);}
}
function mutate(fn,note){try{state=fn();draft=[];$('#draftPanel').hidden=true;save();render();calculate();message(note||'已更新。');}catch(e){message(e.message,true);}}
function renderDraft(){
 $('#draftPanel').hidden=false;
 $('#archive').disabled=true;
 $('#draft').innerHTML=draft.map((c,i)=>`<div class="draft-card ${c.review?'review':''}" data-index="${i}">${c.preview?`<img src="${c.preview}" alt="自动转正牌面" title="${esc((c.issues||[]).join('；')||(c.rotation?'自动转正 '+c.rotation+'°':'原始牌面'))}">`:''}<select class="card-role" data-field="role" aria-label="第${i+1}张归属"><option value="player" ${c.role==='player'?'selected':''}>我的牌</option><option value="dealer" ${c.role==='dealer'?'selected':''}>庄家牌</option></select><select data-field="rank" aria-label="第${i+1}张点数"><option value="">?</option>${V.ranks.map(r=>`<option ${r===c.rank?'selected':''}>${r}</option>`).join('')}</select>${state.mode==='poker'?`<select data-field="suit" aria-label="第${i+1}张花色"><option value="">?</option>${V.suits.map(s=>`<option value="${s}" ${s===c.suit?'selected':''}>${glyph[s]}</option>`).join('')}</select>`:''}<span class="score" title="${esc((c.issues||[]).join('；')+(c.score!=null?' · 模型分数 '+c.score+'，不是准确率':''))}">${c.score==null?'手动':!c.rank||(state.mode==='poker'&&!c.suit)?'未读全':c.review?'待核对':'已读取'}</span><button data-remove="${i}" aria-label="排除此牌">×</button></div>`).join('');
 $('#apply').disabled=!draft.length;
}
$('#draft').addEventListener('change',event=>{const row=event.target.closest('[data-index]');if(row&&event.target.dataset.field){const c=draft[+row.dataset.index];c[event.target.dataset.field]=event.target.value;c.review=false;}});
$('#draft').addEventListener('click',event=>{if(event.target.dataset.remove!=null){draft.splice(+event.target.dataset.remove,1);renderDraft();}});
$('#apply').onclick=()=>mutate(()=>V.commit(state,draft),'已采用本次牌面。截图没有增加历史计数。');
$('#applyTop').onclick=()=>$('#apply').click();
window.acceptDraft=()=>{if(!busy&&!$('#draftPanel').hidden&&!$('#apply').disabled)$('#apply').click();};
$('#cancelDraft').onclick=()=>{draft=[];$('#draftPanel').hidden=true;render();calculate();message('已放弃草稿，保留原手牌和历史。');};
$('#archive').onclick=()=>mutate(()=>V.archive(state),'已归档当前可见手牌；未看见的底牌不会凭空记入。');
$('#undo').onclick=()=>mutate(()=>{if(!state.undo)throw Error('没有可撤销的操作。');return V.clone(state.undo.snapshot);},'已撤销上次操作。');
$('#resetDeck').onclick=()=>mutate(()=>V.resetDeck(state),'已清空当前手牌和已用牌，可撤销。仅在游戏实际洗牌后使用。');
$('#used').addEventListener('click',event=>addUsed(event,1));$('#used').addEventListener('contextmenu',event=>{if(event.target.dataset.addUsed!=null){event.preventDefault();addUsed(event,-1);}});
function addUsed(event,delta){const v=event.target.dataset.addUsed;if(v==null)return;mutate(()=>{const s=V.clone(state);s.blackjack.used[+v]+=delta;V.assertDeck(s);s.undo={label:'历史补记',snapshot:V.clone({...state,undo:null})};return s;},'已更新已用牌，建议已重算。');}
$$('[data-mode]').forEach(button=>button.onclick=()=>{if(busy)return;state.mode=button.dataset.mode;draft=[];$('#draftPanel').hidden=true;save();render();calculate();});
$('#rankPad').innerHTML=V.ranks.map(r=>`<button data-rank="${r}">${r}</button>`).join('');
function editCurrent(){if(!draft.length){const h=state[state.mode];draft=[...h.player.filter(Boolean).map(c=>({...c,role:'player'})),...(h.dealer||[]).map(c=>({...c,role:'dealer'}))];}}
$('#manual').addEventListener('toggle',()=>{if($('#manual').open){editCurrent();renderDraft();}});
$('#rankPad').onclick=event=>{if(event.target.dataset.rank){draft.push({rank:event.target.dataset.rank,suit:$('#suit').value,role:$('#role').value});renderDraft();}};
$('#clearDraft').onclick=()=>{draft=[];renderDraft();};
const buffs=[['confidence','赌徒自信'],['insurance','保险'],['statue','神圣雕像'],['stakeholder','利益相关者'],['camera','相机'],['drink','饮料'],['microphone','麦克风']];
$('#buffs').innerHTML=buffs.map(([id,n])=>`<label>${n}<input data-buff="${id}" type="number" min="0" max="100" step="1" value="0"></label>`).join('');
$('#buffs').onchange=event=>{const id=event.target.dataset.buff,n=Number(event.target.value);if(id&&Number.isInteger(n)&&n>=0&&n<=100){state.owned[id]=n;save();render();calculate();}else message('道具数量需要是0–100的整数。',true);};
for(const id of ['tipsy','melody','team'])$('#'+id).onchange=()=>{state.team=$('#team').value;state.settings.tipsy=Math.max(1,Math.min(20,Number($('#tipsy').value)||1));state.settings.melody=Math.max(0,Math.min(1,Number($('#melody').value)||0));save();render();calculate();};
$('#compact').onclick=()=>{compact=!compact;document.body.classList.toggle('compact',compact);$('#compact').textContent=compact?'展开':'收起';if(nativeReady)desktopCall('compact',compact).catch(e=>message(e.message,true));};
async function refreshWindows(){
 const previous=$('#target').value;
 const rows=await withTimeout(desktopCall('windows'),5000,'读取窗口列表超时，请点击刷新重试。');
 if(!Array.isArray(rows))throw Error('桌面窗口列表格式无效，请完整更新程序。');
 $('#target').innerHTML='<option value="">选择游戏窗口</option>'+rows.map(r=>`<option value="${esc(r.id)}">${esc(r.title)}${r.minimized?'（已最小化）':''}</option>`).join('');
 const chosen=rows.find(r=>String(r.id)===previous)||rows.find(r=>/gamble.*friends|朋友.*梭哈|gwyf/i.test(r.title));
 $('#target').value=chosen?String(chosen.id):'';
 await desktopCall('select_window',$('#target').value);
 $('#windowStatus').textContent=!rows.length?'未找到可选择的窗口。先打开游戏，再点击刷新。':chosen?(chosen.minimized?'已找到游戏窗口，请先恢复游戏再截图。':'已选择：'+chosen.title):`找到 ${rows.length} 个窗口，请选择游戏窗口。`;
}
async function refresh(){
 try{
  if(!nativeReady){const connected=await connectDesktop(true);if(!connected)return;}
  else {await refreshWindows();message($('#windowStatus').textContent);}
 }catch(e){$('#windowStatus').textContent=e.message;message(e.message,true);}
}
$('#refresh').onclick=refresh;
$('#target').onchange=async()=>{try{await desktopCall('select_window',$('#target').value);$('#windowStatus').textContent=$('#target').value?'已选择：'+$('#target').selectedOptions[0].textContent:'请选择游戏窗口。';message($('#windowStatus').textContent);}catch(e){$('#windowStatus').textContent=e.message;message(e.message,true);}};
function setFrame(data){
 frame=data;frameImage=new Image();frameImage.onload=paintFrame;frameImage.src=data.image;$('#emptyFrame').hidden=true;
 const old=state.aspect[state.mode],now=data.width/data.height;
 if(old&&Math.abs(old/now-1)>.02){state.regions[state.mode]={};state.settings.captureMode='auto';message('窗口宽高比已改变，已切回自动找牌。');}
 state.aspect[state.mode]=now;
}
async function recognize(){
 if(!frame){message('请先截图或打开测试图片。',true);return;}
 const regions=state.settings.captureMode==='manual'?state.regions[state.mode]:{};
 if(state.settings.captureMode==='manual'&&(!regions.player||(state.mode==='blackjack'&&!regions.dealer))){message('请框出双方牌区，或点“自动找牌”。',true);$('#setup').open=true;return;}
 const start=performance.now();draft=[];detections=[];$('#draftPanel').hidden=true;message('正在本地找牌、核对并计算…');
 const out=await desktopCall('recognize',regions,state.mode);
 detections=out.cards||[];paintFrame();
 $('#timing').textContent=`识别 ${out.recognitionMs} ms / 往返 ${Math.round(performance.now()-start)} ms`;
 const checked=VisionRecognition.assess(state,out);
 if(checked.ok){
  const next=V.commit(state,checked.cards),oldHand=JSON.stringify(state[state.mode]),newHand=JSON.stringify(next[next.mode]);
  if(oldHand!==newHand){state=next;save();}
  draft=[];$('#draftPanel').hidden=true;render();calculate();
  message(`已自动识别并计算 · ${checked.cards.filter(c=>c.role==='player').map(label).join(' ')}${out.hiddenCount?' · 庄家暗牌不读取':''}${out.rejectedCount?` · 已排除 ${out.rejectedCount} 个非牌面候选`:''}`);
  return;
 }
 draft=detections.filter(c=>!c.faceDown);renderDraft();
 const players=draft.filter(c=>c.role==='player').length;
 message(!draft.length?'没有找到可靠牌面。请对准当前牌桌再试。':`本次需核对 · 我的牌 ${players} 张${out.hiddenCount?` · 排除 ${out.hiddenCount} 张背面`:''}${out.rejectedCount?` · 排除 ${out.rejectedCount} 个非牌面`:''}`,true);
 if(compact){compact=false;document.body.classList.remove('compact');$('#compact').textContent='收起';if(nativeReady)desktopCall('compact',false).catch(e=>message(e.message,true));}
 advice('本次识别需要核对',checked.reasons.slice(0,2).join('；')||'核对草稿后点击采用；本次未写入手牌或历史。',true,'自动计算已暂停 · 原手牌保留');
}
async function captureNow(){
 if(busy)return;busy=true;$('#capture').disabled=true;
 // Stop a prior poker enumeration so its late result cannot replace the draft warning.
 stopSolver();
 draft=[];detections=[];$('#draftPanel').hidden=true;
 try{
  const data=await desktopCall('capture');setFrame(data);await recognize();
 }catch(e){message(e.message||String(e),true);advice('截图未完成','请检查游戏窗口是否可见；旧手牌仍保留。',true);}
 finally{busy=false;$('#capture').disabled=false;}
}
window.captureNow=captureNow;$('#capture').onclick=captureNow;
$('#openImage').onclick=async()=>{if(busy)return;try{busy=true;const data=await desktopCall('open_image');if(data){stopSolver();detections=[];setFrame(data);await recognize();}}catch(e){message(e.message,true);}finally{busy=false;}};
$('#read').onclick=async()=>{if(busy)return;busy=true;stopSolver();try{await recognize();}catch(e){message(e.message,true);advice('识别未完成','请调整牌区或手动录牌；本帧尚未采用。',true);}finally{busy=false;}};
function paintFrame(){
 const canvas=$('#frame'),ctx=canvas.getContext('2d');ctx.clearRect(0,0,canvas.width,canvas.height);
 if(!frameImage?.complete||!frame)return;
 canvas.width=frameImage.naturalWidth;canvas.height=frameImage.naturalHeight;ctx.drawImage(frameImage,0,0);
 const regions={...state.regions[state.mode]};if(drag&&selectRegion)regions[selectRegion]=[Math.min(drag[0],drag[2]),Math.min(drag[1],drag[3]),Math.max(drag[0],drag[2]),Math.max(drag[1],drag[3])];
 for(const c of detections){if(!c.quad)continue;ctx.strokeStyle=c.review?'#e5bd75':c.role==='player'?'#8ce6bc':'#8fbbff';ctx.lineWidth=Math.max(2,canvas.width/450);ctx.beginPath();c.quad.forEach((p,i)=>i?ctx.lineTo(p[0]*canvas.width/frame.width,p[1]*canvas.height/frame.height):ctx.moveTo(p[0]*canvas.width/frame.width,p[1]*canvas.height/frame.height));ctx.closePath();ctx.stroke();}
 for(const [role,r] of Object.entries(regions)){if(state.mode==='poker'&&role==='dealer')continue;ctx.strokeStyle=role==='player'?'#8ce6bc':'#e5bd75';ctx.lineWidth=Math.max(2,canvas.width/400);ctx.strokeRect(r[0]*canvas.width,r[1]*canvas.height,(r[2]-r[0])*canvas.width,(r[3]-r[1])*canvas.height);}
}
$$('[data-region]').forEach(button=>button.onclick=()=>{if(!frame){message('请先截一帧。',true);return;}selectRegion=button.dataset.region;$('#regionHint').textContent=`在截图上拖动框选${selectRegion==='player'?'我的手牌':'庄家牌'}，只包含对应的一排牌。`;});
const point=event=>{const r=$('#frame').getBoundingClientRect();return [Math.max(0,Math.min(1,(event.clientX-r.left)/r.width)),Math.max(0,Math.min(1,(event.clientY-r.top)/r.height))];};
$('#frame').onpointerdown=event=>{if(!selectRegion||!frame)return;const p=point(event);drag=[...p,...p];event.target.setPointerCapture(event.pointerId);};
$('#frame').onpointermove=event=>{if(drag){const p=point(event);drag[2]=p[0];drag[3]=p[1];paintFrame();}};
$('#frame').onpointerup=()=>{if(!drag||!selectRegion)return;const r=[Math.min(drag[0],drag[2]),Math.min(drag[1],drag[3]),Math.max(drag[0],drag[2]),Math.max(drag[1],drag[3])];if(r[2]-r[0]>.015&&r[3]-r[1]>.01){state.regions[state.mode][selectRegion]=r;state.settings.captureMode='manual';save();render();message('归属牌区已保存。完整牌面不会被选区边界裁开。');}drag=null;selectRegion=null;paintFrame();};
$('#frame').onpointercancel=()=>{drag=null;paintFrame();};
$('#clearRegions').onclick=()=>{state.regions[state.mode]={};state.settings.captureMode='auto';save();render();message('已切回自动找牌。');};
$('#autoLocate').onclick=()=>{state.settings.captureMode='auto';save();render();message('已启用自动找牌，无需先框选。');};
function showState(){
 for(const [id] of buffs)$(`[data-buff=${id}]`).value=state.owned[id]||0;
 $('#tipsy').value=state.settings.tipsy??2;$('#melody').value=state.settings.melody??1;$('#team').value=state.team;
 render();calculate();
}
function showNativeStatus(out){
 $('#nativeBadge').textContent=`桌面已连接 · ${out.version||'本地模型'} · ${out.modelBytes>1048576?(out.modelBytes/1048576).toFixed(1)+' MB':(out.modelBytes/1024).toFixed(0)+' KB'}`;
 $('#hotkey').textContent=out.hotkey+(out.python?' · Python '+out.python:'');
}
async function connectDesktop(manual=false){
 if(nativeReady)return true;
 if(nativeConnecting)return nativeConnecting;
 if(!api()&&!nativeRequired){if(manual)message('请通过 Start-Windows.bat 启动；浏览器预览不能读取游戏窗口。',true);return false;}
 $('#nativeBadge').textContent='正在连接桌面…';
 $('#windowStatus').textContent='等待桌面接口就绪…';
 $('#refresh').disabled=true;
 const revision=stateRevision;
 nativeConnecting=(async()=>{
  try{
   await waitForBridge();
   const out=await withTimeout(desktopCall('status'),5000,'桌面服务没有响应，请关闭并重新启动浮窗。');
   let stateWarning='';
   try{const raw=await withTimeout(desktopCall('load_state'),2500,'读取本机存档超时');if(raw&&revision===stateRevision){state=V.restore(raw);showState();}}
   catch(e){stateWarning='本机存档未读取：'+e.message;}
   nativeReady=true;showNativeStatus(out);
   await refreshWindows();
   message(stateWarning||'桌面已连接。'+$('#windowStatus').textContent,!!stateWarning);
   setTimeout(async()=>{try{showNativeStatus(await withTimeout(desktopCall('status'),3000,'桌面状态查询超时'));}catch(e){message(e.message,true);}},700);
   return true;
  }catch(e){
   if(!nativeReady){$('#nativeBadge').textContent='桌面连接失败';$('#hotkey').textContent='连接失败时仍可手动录牌；点击刷新可重试连接。';}
   $('#windowStatus').textContent=e.message;message(e.message,true);return false;
  }finally{nativeConnecting=null;$('#refresh').disabled=false;}
 })();
 return nativeConnecting;
}
// Readiness can arrive before or after this script; an empty api object is not ready.
try{const raw=JSON.parse(localStorage.getItem('gwyf-vision-v1')||'null');if(raw)state=V.restore(raw);}catch(e){message('浏览器存档无效，已使用空白状态。',true);}
showState();
window.addEventListener('pywebviewready',()=>connectDesktop());
if(nativeRequired||api())connectDesktop();
else {
 const started=Date.now();const probe=setInterval(()=>{if(api()){clearInterval(probe);connectDesktop();}else if(Date.now()-started>15000)clearInterval(probe);},100);
}
