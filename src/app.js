/* 旅人使用GPT-6制作 | GWYF offline companion v7.7 */
(()=>{'use strict';
const E=GWYFEngine,$=id=>document.getElementById(id),VERSION=7,KEY='GWYF_COMPANION_V7';
const RELEASE='7.7';
const f=(x,n=2)=>Number.isFinite(x)?x.toLocaleString('zh-CN',{minimumFractionDigits:n,maximumFractionDigits:n}):'—';
const pc=(x,n=2)=>x>0&&x<.00001?'＜0.001%':f(x*100,n)+'%';
const signed=(x,n=2)=>(x>1e-9?'+':x< -1e-9?'−':'')+f(Math.abs(x)<1e-9?0:Math.abs(x),n);
const sp=x=>signed(x*100)+'%';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const ranks=['2','3','4','5','6','7','8','9','10','J','Q','K','A'],suits=['♠','♥','♦','♣'];
const bjRanks=['A','2','3','4','5','6','7','8','9','10'];
const meta={
 recommend:['◈','局势总览','OVERVIEW','看清这局，决定下一步。','按当前楼层与生效道具比较玩法，先看净收益，再看承担的波动。'],
 roulette:['◎','轮盘','ROULETTE','把整桌下注，一次算清。','点击区域叠加筹码，精确查看37个结果的整桌净盈亏。'],
 baccarat:['▣','游戏百家乐','BACCARAT','四张牌的游戏版百家乐。','庄闲各两张，不补牌、不收佣金；和局时庄闲下注也会输。'],
 poker:['♠','单人扑克','DRAW POKER','这五张，应该留哪几张？','枚举全部32种保留方案；支持记录跨局已用牌，计算过程可取消。'],
 bj:['♧','二十一点','BLACKJACK','先看点数，再看剩余牌。','点选牌局与已用牌，自动比较要牌、停牌和加倍。'],
 craps:['⚄','街头骰子','STREET CRAPS','跟踪每一掷，算清剩余机会。','首掷与目标点阶段采用不同结算；公平骰子是计算假设。'],
 money:['◉','颜色转盘','MONEY WHEEL','命中率与收益率，分开看。','37个等角扇区，选一种颜色；橙色倍率高，也最容易连续落空。'],
 fortune:['✺','倍率转盘','WHEEL OF FORTUNE','转到Spin，只是再转一次。','20格里有2格重转；最终收益按18个有效倍率格计算。'],
 hilo:['⇅','HiLo猜大小','OVER / UNDER','选你愿意承担的概率。','阈值决定胜率，方向决定哪一边；这里不是扑克牌猜大小。'],
 crash:['↗','Crash','CRASH','先设提现目标，再开始。','理论概率不包含点击延迟；正常目标的基础期望相近。'],
 dragon:['♜','爬龙塔','DRAGON TOWER','下一层，值得继续吗？','6层，每层3/4安全；比较当前提现与继续一步的条件价值。'],
 penguin:['🐧','企鹅过路','PENGUIN CROSS','已经走到这里，下一步呢？','当前成功不等于下一步更容易；从当前位置重新计算风险。'],
 mines:['✦','扫雷','MINE SWEEPER','每翻一格，风险都在变化。','25格随机扫雷，无数字线索；不放回概率决定倍率。'],
 keno:['▦','基诺 Keno','KENO','选几个，比选哪几个更重要。','48个号码开10个；精确计算命中、盈利与倍率分布。'],
 duck:['🦆','鸭子赛跑','DUCK RACE','四只鸭，一只赢家。','赔率已知；每只25%是对称假设，不是实局分布的保证。'],
 plinko:['⠿','弹珠台','PLINKO','落槽倍率已知，落点概率未知。','记录自己的落槽样本，查看实测分布与单次结算。'],
 slots:['▥','老虎机','SLOTS','图案、倍率、概率，一起查。','11种中奖结构、4种符号系数与9格盘面验算；概率模型和实局证据分开标明。'],
 items:['◇','道具与增益','ITEMS & BUFFS','选择生效数量，整站同步。','道具和升级都能直接加减数量，0即不生效；已知叠加规则自动计算。'],
 camera:['▧','相机与免费筹码','ITEM CALCULATORS','把额外入账单独算明白。','计算相机充能兑现与黄金筹码的单次免费下注，不把它们当成提高胜率。'],
 budget:['◷','局内资金','RUN PLANNER','这笔下注，占了多少资金？','检查单次风险、配额缺口与实际盈亏记录；本工具不连接游戏。'],
 floors:['▤','楼层图鉴','FLOOR GUIDE','这层，哪些游戏可能出现？','四层候选池不同；在候选池内，也不保证这次实际刷出。'],
 sources:['ⓘ','规则与版本','RULES & SOURCES','每个数字，都说明来处。','官方公告核对更新；具体赔率来自社区规则整理和本地计算。']
};
const groups=[['工作台',['recommend','items','budget','camera','floors']],['下注与牌局',['roulette','baccarat','poker','bj','craps']],['转盘与概率',['money','fortune','hilo','keno','slots']],['继续 / 提现',['crash','dragon','penguin','mines']],['物理玩法',['duck','plinko']],['资料',['sources']]];
const quickGroups=[['牌桌',['roulette','baccarat','poker','bj','craps']],['转盘',['money','fortune','hilo','keno','slots']],['闯关',['crash','dragon','penguin','mines']],['物理',['duck','plinko']]];
const quickNames={roulette:'轮盘',baccarat:'百家乐',poker:'扑克',bj:'21点',craps:'骰子',money:'颜色盘',fortune:'倍率盘',hilo:'HiLo',keno:'基诺',slots:'老虎机',crash:'Crash',dragon:'龙塔',penguin:'企鹅',mines:'扫雷',duck:'鸭赛',plinko:'弹珠'};
const gameIds=gameFacts.map(g=>g.id);
const defaults={tab:'recommend',profile:{floor:2,goal:'money',risk:'normal',team:'group',bankroll:1000,stake:20,quota:2000,tickets:10},owned:{},settings:{melody:1,tipsy:2},roulette:{base:10,multiple:1,wagers:[]},baccarat:{base:10,multiple:1,wagers:[]},poker:{cards:[12,25,30,7+39,10],used:[],track:false,objective:'ev',entry:0},bj:{mode:'quick',type:'hard',hard:16,soft:7,pair:'8',dealer:'10',first:true,cards:['10','6'],dealerCards:[],track:false,used:Array(10).fill(0),recent:[]},craps:{rolls:[]},money:{color:'orange'},fortune:{},hilo:{threshold:50,side:'under'},crash:{target:2},dragon:{level:0,target:3},penguin:{level:0,target:3},mines:{mine:10,k:3,target:20},keno:{picks:4},duck:{},plinko:{pocket:0,samples:Array(12).fill(0),recent:[]},slots:{view:'patterns',symbol:0,board:[0,1,2,1,0,3,2,3,0],target:10,rounds:10},camera:{bank:0,charge:1,captures:[0,0,0,0],maxBet:300,game:'money'},budget:{net:0,label:''},history:[]};
const constraints={
 'profile.floor':[1,4,1],'profile.bankroll':[0,1e15],'profile.stake':[.01,1e12],'profile.quota':[0,1e15],'profile.tickets':[0,1000000,1],
 'poker.entry':[-1,4,1],
 'settings.melody':[0,1],'settings.tipsy':[1,20],
 'roulette.base':[.01,1e9],'baccarat.base':[.01,1e9],'roulette.multiple':[1,10,1],'baccarat.multiple':[1,10,1],
 'bj.hard':[4,30,1],'bj.soft':[2,10,1],'hilo.threshold':[1,99,1],'crash.target':[1.2,100],
 'dragon.level':[0,6,1],'penguin.level':[0,10,1],'dragon.target':[1,1000],'penguin.target':[1,10000],
 'mines.mine':[1,24,1],'mines.k':[0,24,1],'mines.target':[1,1e9],'keno.picks':[1,10,1],
 'slots.symbol':[0,3,1],'slots.target':[1,1000000],'slots.rounds':[1,1000,1],'camera.bank':[0,1e15],'camera.charge':[1,4,1],'camera.maxBet':[.01,1e12],'plinko.pocket':[0,11,1], 'budget.net':[-1e15,1e15]
};
const enums={'tab':Object.keys(meta),'profile.goal':['money','safe','quota','tickets','challenge'],'profile.risk':['normal','careful','bold'],'profile.team':['solo','group'],'bj.mode':['quick','cards'],'bj.type':['hard','soft','pair'],'bj.pair':bjRanks,'bj.dealer':['',...bjRanks],'hilo.side':['under','over'],'money.color':Object.keys(E.money),'poker.objective':['ev','win'],'camera.game':['money','roulette','baccarat','fortune','hilo','duck','keno'],'slots.view':['patterns','board','model']};
function cleanNumber(v,d,path){const [lo,hi,integer]=constraints[path]||(path.startsWith('camera.captures.')?[0,1e15]:[-1e15,1e15]);const n=typeof v==='number'&&Number.isFinite(v)?v:d;return integer?Math.round(E.clamp(n,lo,hi)):E.clamp(n,lo,hi);}
function normalize(raw){
 const plain=o=>o&&typeof o==='object'&&!Array.isArray(o);
 function walk(d,v,path=''){
  if(Array.isArray(d))return structuredClone(d);
  if(typeof d==='number')return cleanNumber(v,d,path);
  if(typeof d==='boolean')return typeof v==='boolean'?v:d;
  if(typeof d==='string')return enums[path]?.includes(v)?v:path==='budget.label'&&typeof v==='string'?v.slice(0,60):d;
  const out={};for(const k of Object.keys(d))out[k]=walk(d[k],plain(v)?v[k]:undefined,path?path+'.'+k:k);return out;
 }
 const s=walk(defaults,raw);
 if(plain(raw?.owned))for(const it of guideItems)s.owned[it.id]=Math.round(E.clamp(Number(raw.owned[it.id])||0,0,999));
 for(const id of ['roulette','baccarat']){const defs=id==='roulette'?E.roulette:E.baccaratDefs;s[id].multiple=[1,2,5,10].includes(s[id].multiple)?s[id].multiple:1;const w=raw?.[id]?.wagers;s[id].wagers=Array.isArray(w)?w.filter(x=>x&&Object.hasOwn(defs,x.key)&&typeof x.amount==='number'&&Number.isFinite(x.amount)&&x.amount>0&&x.amount<=1e12).slice(0,2000).map(x=>({key:x.key,amount:Math.round(x.amount*100)/100})).filter(x=>x.amount>0):[];}
 const ints=(a,min,max)=>Array.isArray(a)?a.filter(x=>Number.isInteger(x)&&x>=min&&x<=max):[];
 if(Array.isArray(raw?.poker?.cards)&&raw.poker.cards.length===5&&raw.poker.cards.every(x=>x===null||Number.isInteger(x)&&x>=0&&x<=51))s.poker.cards=raw.poker.cards.slice();
 if(!Number.isInteger(raw?.poker?.entry))s.poker.entry=Math.max(0,s.poker.cards.indexOf(null));
 s.poker.used=[...new Set(ints(raw?.poker?.used,0,51))].filter(id=>!s.poker.cards.includes(id));
 if(Array.isArray(raw?.bj?.cards))s.bj.cards=raw.bj.cards.filter(x=>ranks.includes(x)).slice(0,12);
 if(Array.isArray(raw?.bj?.dealerCards))s.bj.dealerCards=raw.bj.dealerCards.filter(x=>ranks.includes(x)).slice(0,12);
 if(Array.isArray(raw?.bj?.recent))s.bj.recent=raw.bj.recent.filter(x=>Number.isInteger(x)&&Math.abs(x)>=1&&Math.abs(x)<=10).slice(-2000);
 if(Array.isArray(raw?.bj?.used)&&raw.bj.used.length===10)s.bj.used=raw.bj.used.map((x,i)=>Math.round(E.clamp(Number(x)||0,0,i===9?16:4)));
 s.craps.rolls=ints(raw?.craps?.rolls,2,12).slice(0,4);
 if(Array.isArray(raw?.plinko?.samples)&&raw.plinko.samples.length===12)s.plinko.samples=raw.plinko.samples.map(x=>Math.round(E.clamp(Number(x)||0,0,1e7)));
 s.plinko.recent=ints(raw?.plinko?.recent,0,11).slice(-2000);
 const slotBoard=ints(raw?.slots?.board,0,3);if(slotBoard.length===9)s.slots.board=slotBoard;
 if(Array.isArray(raw?.camera?.captures)&&raw.camera.captures.length===4)s.camera.captures=raw.camera.captures.map(x=>E.clamp(Number(x)||0,0,1e15));
 if(Array.isArray(raw?.history))s.history=raw.history.filter(x=>x&&typeof x.net==='number'&&Number.isFinite(x.net)&&Math.abs(x.net)<=1e15&&typeof x.label==='string'&&typeof x.time==='string').slice(0,200).map(x=>({net:x.net,label:x.label.slice(0,60),time:x.time.slice(0,32)}));
 if(s.bj.type==='hard'&&s.bj.hard>=21)s.bj.first=false;
 s.mines.k=Math.min(s.mines.k,25-s.mines.mine);return s;
}
let state=structuredClone(defaults),storageOK=true,saveTimer=0,search='',floorOnly=false,pokerJob=null,pokerResult=null,pokerProgress=0,pokerError='',calcToken=0,tableUndo={roulette:[],baccarat:[]};
function readStored(){try{const v=JSON.parse(localStorage.getItem(KEY)||'null');if(v?.version===VERSION){state=normalize(v.state);return;}const b=JSON.parse(localStorage.getItem('GWYF_BUILD_V2')||'null');const old=JSON.parse(localStorage.getItem('GWYF_SESSION_V54')||'null');if(b||old){const merged=structuredClone(defaults);if(b){for(const k of ['floor','goal','risk','team'])if(b[k]!==undefined)merged.profile[k]=b[k];merged.owned=b.owned||{};}if(old){for(const k of ['roulette','baccarat','bj','hilo','mines','money','fortune','crash','craps'])if(old[k])merged[k]=old[k];if(old.b)merged.bj={...merged.bj,...old.b};if(Array.isArray(old.pkCards))merged.poker.cards=old.pkCards.map(c=>suits.indexOf(c[1])*13+ranks.indexOf(c[0]));if(meta[old.tab])merged.tab=old.tab;}state=normalize(merged);}}catch{storageOK=false;}}
function save(){try{localStorage.setItem(KEY,JSON.stringify({version:VERSION,savedAt:new Date().toISOString(),state}));storageOK=true;}catch{storageOK=false;}updateSaveStatus();}
function updateSaveStatus(){const el=$('saveState');if(el){el.innerHTML=storageOK?'<i></i>已自动保存':'本地保存不可用';el.title=storageOK?'局面与设置已保存在此浏览器，可导出跨设备继续。':'浏览器限制本地存储，请使用导出存档。';}}
function toast(s){$('toast').textContent=s;$('toast').classList.add('show');clearTimeout(saveTimer);saveTimer=setTimeout(()=>$('toast').classList.remove('show'),3500);}
function owned(id){return state.owned[id]||0;}
function buffs(){return E.buffs(state.owned,state.settings,state.profile.team);}
function fact(id){return gameFacts.find(g=>g.id===id);}
const btn=(label,action,value='',kind='')=>`<button class="btn ${kind}" data-action="${action}" data-value="${esc(value)}">${label}</button>`;
const go=(id,label,kind='ghost')=>`<button class="btn ${kind}" data-go="${id}">${label||'打开决策器 →'}</button>`;
const input=(label,path,value,min=0,max=1e12,step='any',help='')=>`<label class="field"><span>${label}</span><input type="number" inputmode="decimal" data-path="${path}" value="${value}" min="${min}" max="${max}" step="${step}">${help?`<div class="field-help">${help}</div>`:''}</label>`;
const select=(label,path,value,options)=>`<label class="field"><span>${label}</span><select data-path="${path}">${options.map(([v,n])=>`<option value="${v}" ${value===v?'selected':''}>${n}</option>`).join('')}</select></label>`;
const choices=(path,value,options,cols=4)=>`<div class="choices" style="--cols:${cols}">${options.map(([v,n])=>`<button class="choice ${String(v)===String(value)?'selected':''}" aria-pressed="${String(v)===String(value)}" data-action="set" data-path="${path}" data-value="${v}">${n}</button>`).join('')}</div>`;
const check=(label,path,value)=>`<label class="check"><input type="checkbox" data-path="${path}" ${value?'checked':''}><span>${label}</span></label>`;
const stat=(name,value,cls='')=>`<div class="stat"><span>${name}</span><strong class="${cls}">${value}</strong></div>`;
const hero=(title,desc,kicker='当前局面',type='')=>`<div class="hero-result ${type}"><div class="kicker">${kicker}</div><div class="decision">${title}</div><p>${desc}</p></div>`;
const chip=(text,type='')=>`<span class="chip ${type}">${text}</span>`;
const alert=(text,type='')=>`<div class="alert ${type}">${text}</div>`;
const table=(headers,rows)=>`<div class="table-wrap"><table class="data-table"><thead><tr>${headers.map(x=>`<th scope="col">${x}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr${r.selected?' class="selected"':''}>${(r.cells||r).map(x=>`<td>${x}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
const details=(name,inner,open=false)=>`<details class="disclosure" data-detail="${esc(name.replace(/\d+/g,'#'))}" ${open?'open':''}><summary>${name}</summary>${inner}</details>`;
const panel=(title,inner,extra='')=>`<section class="panel ${extra}"><h2>${title}</h2>${inner}</section>`;
const link=(url,label='查看规则依据 ↗')=>`<a href="${url}" target="_blank" rel="noopener noreferrer">${label}</a>`;
const workspace=(left,right)=>`<div class="mobile-jump"><span>关键建议随选择更新</span><button data-action="scrollResults">详细计算 ↓</button></div><div class="workspace"><div class="stack">${left}</div><div class="stack" id="resultRegion" aria-live="polite" aria-atomic="false">${right}</div></div>`;
function contextNote(id,text=''){const g=fact(id);return `<p class="note">${text?text+' ':''}${g?link(g.url):''} · 规则基准 v1.0.30</p>`;}
function resultBar(o){return `<div class="risk-bar" aria-label="盈利${pc(o.win)}，保本${pc(o.flat)}，亏损${pc(o.lose)}"><span class="win" style="width:${o.win*100}%"></span><span class="flat" style="width:${o.flat*100}%"></span><span class="loss" style="width:${o.lose*100}%"></span></div><div class="legend"><span><i style="background:#89d8a8"></i>净盈利 ${pc(o.win)}</span><span><i style="background:#657e6b"></i>保本 ${pc(o.flat)}</span><span><i style="background:#c08076"></i>净亏损 ${pc(o.lose)}</span></div>`;}
function modelSummary(){const b=buffs();return `<div class="chips">${chip('正利润 ×'+f(b.a,2))}${chip('亏损保留 '+pc(b.b))}${b.camera?chip('含'+owned('camera')+'台相机单拍 +'+pc(b.cameraRate),'unknown'):''}${b.bonusChance?chip('盈利后额外抽签 '+pc(b.bonusChance,0),'neutral'):''}</div>`;}
function scenarioSummary(o,unit=true){return `${resultBar(o)}<div class="stats">${stat(unit?'期望净收益率':'期望净收益',unit?sp(o.roi):signed(o.ev),o.ev>=-1e-9?'positive':'negative')}${stat('净盈利概率',pc(o.win))}${stat(unit?'最差净收益率':'最差净盈亏',unit?sp(o.min/o.total):signed(o.min),o.min<0?'negative':'')}${stat(unit?'最好净收益率':'最好净盈亏',unit?sp(o.max/o.total):signed(o.max),'positive')}</div>${buffs().bonusChance?`<div class="chips">${chip('每轮额外Ticket期望 '+f(o.win*buffs().bonusChance,3),'neutral')}</div>`:''}`;}
function amountDetails(o,label='按当前单次投入换算'){const stake=state.profile.stake,balance=state.profile.bankroll;return details(label,`${input('计划总投入（游戏币）','profile.stake',stake,.01,1e12)}<div class="stats">${stat('投入占共享资金',balance?pc(stake/balance):'资金为0')}${stat('期望净收益',signed(o.roi*stake),o.ev>=0?'positive':'negative')}${stat('最差净盈亏',signed(o.min/o.total*stake),o.min<0?'negative':'')}${stat('最好净盈亏',signed(o.max/o.total*stake),'positive')}</div>${stake>balance?alert('当前投入超过记录的共享资金，请先核对资金或调整金额。'):''}<p class="note">这是模型期望；实际单局只会落在某个结果上。${go('budget','管理局内资金 →','ghost small')}</p>`);}
function buffBlock(summary=modelSummary()){return details(`生效道具 · ${Object.values(state.owned).filter(n=>n>0).length}种`,inventory()+advancedBuffs())+`<div class="buff-summary" style="margin:14px 0">${summary}</div>`;}
function profileFields(compact=false){const p=state.profile;return `<div class="${compact?'profile-fields':''}"><label class="field"><span>所在楼层</span>${choices('profile.floor',p.floor,[1,2,3,4].map(n=>[n,'F'+n]),4)}</label>${select('本局目标','profile.goal',p.goal,[['money','比较长期收益'],['quota','补足当前配额'],['safe','降低单次波动'],['tickets','积累Tickets'],['challenge','完成游戏挑战']])}${select('波动偏好','profile.risk',p.risk,[['careful','谨慎'],['normal','均衡'],['bold','可承受大波动']])}${select('游玩方式','profile.team',p.team,[['group','多人 · 共享账户'],['solo','单人']])}</div>`;}
function renderNav(){let count=0;$('nav').innerHTML=groups.map(([name,ids])=>{const shown=ids.filter(id=>{if(search&&!`${meta[id][1]} ${meta[id][2]} ${id}`.toLowerCase().includes(search.toLowerCase()))return false;const g=fact(id);return !(floorOnly&&g&&!g.floors.includes(state.profile.floor));});if(!shown.length)return '';return `<div class="nav-section">${name}</div>${shown.map(id=>{if(gameIds.includes(id))count++;const g=fact(id);return `<button class="nav-item ${state.tab===id?'active':''}" data-go="${id}" ${state.tab===id?'aria-current="page"':''}><span class="nav-icon" aria-hidden="true">${meta[id][0]}</span><span>${meta[id][1]}</span>${g?`<small>F${g.floors.join('·')}</small>`:''}</button>`;}).join('')}`;}).join('')||'<div class="empty">没有找到相关游戏</div>';$('navCount').textContent=count+' 款';$('navFilter').textContent=floorOnly?'F'+state.profile.floor+' 可出现':'全部游戏';$('navFilter').classList.toggle('on',floorOnly);}
function renderQuickNav(){
 $('quickNav').innerHTML=`<div class="quick-nav-head"><button class="quick-home ${state.tab==='recommend'?'active':''}" data-go="recommend">◈ 总览</button><span class="quick-floor">F${state.profile.floor} · 游戏直达</span><div class="quick-utilities">${[['items','道具'],['budget','资金'],['camera','相机'],['floors','楼层'],['sources','资料']].map(([id,name])=>`<button data-go="${id}" ${state.tab===id?'aria-current="page"':''}>${name}</button>`).join('')}</div></div><div class="quick-groups">${quickGroups.map(([label,ids])=>`<div class="quick-group"><span class="quick-label">${label}</span><div class="quick-buttons">${ids.map(id=>`<button class="quick-game ${state.tab===id?'active':''}" data-go="${id}" aria-label="打开${meta[id][1]}" ${state.tab===id?'aria-current="page"':''} title="${meta[id][1]} · F${fact(id).floors.join('/F')}">${quickNames[id]}</button>`).join('')}</div></div>`).join('')}</div>`;
 requestAnimationFrame(()=>{document.documentElement.style.setProperty('--nav-offset',(document.querySelector('.topbar').offsetHeight+12)+'px');});
}
function renderChrome(){document.body.dataset.page=state.tab;renderNav();renderQuickNav();$('pageName').textContent=meta[state.tab][1];document.title=`${meta[state.tab][1]} · 朋友，梭哈吧决策器`;
 const b=buffs(),p=state.profile;$('contextbar').innerHTML=`<button class="floor-label" data-go="floors">F${p.floor} 楼层 ↗</button><span class="separator"></span><span>共享资金 <b>${f(p.bankroll,0)}</b></span><span class="separator"></span><button class="buff-tag" data-go="items">利润 ×${f(b.a,2)} · 亏损保留 ${pc(b.b,0)}</button><button class="context-edit" data-go="items">调整生效道具 ↗</button>`;
 const m=meta[state.tab],g=fact(state.tab);$('pageHeading').innerHTML=`<div class="page-heading"><div><div class="eyebrow">${m[2]} / GWYF</div><h1>${m[3]}</h1><p>${m[4]}</p></div><div class="page-badge">${g?'F'+g.floors.join(' / F')+' · '+g.kind:'本地计算 · v'+RELEASE}</div></div>`;updateSaveStatus();}
function setPath(path,value){const keys=path.split('.');let obj=state;for(let i=0;i<keys.length-1;i++){if(!Object.hasOwn(obj,keys[i]))return;obj=obj[keys[i]];}const key=keys.at(-1);if(!Object.hasOwn(obj,key))return;const d=obj[key];if(typeof d==='number'){const n=typeof value==='number'?value:Number(value);if(!Number.isFinite(n)){toast('请输入有效数字');return;}obj[key]=cleanNumber(n,d,path);}else if(typeof d==='boolean')obj[key]=!!value;else if(enums[path]?.includes(value))obj[key]=value;else if(path==='budget.label')obj[key]=String(value).slice(0,60);else return;
 if(state.bj.type==='hard'&&state.bj.hard>=21)state.bj.first=false;
 if(path.startsWith('settings.')||path==='profile.team'||path.startsWith('poker.'))invalidatePoker();state.mines.k=Math.min(state.mines.k,25-state.mines.mine);save();render();}
function focusGameControls(){if(innerWidth<=1000&&gameIds.includes(state.tab))requestAnimationFrame(()=>$('content').scrollIntoView({block:'start',behavior:'instant'}));}
function navigate(id){if(!meta[id])return;state.tab=id;closeNav();save();render();history.replaceState(null,'','#'+id);window.scrollTo(0,0);focusGameControls();}
function render(){if(pointerBusy){renderPending=true;return;}const opened=new Set([...document.querySelectorAll('#content details[open]')].map(d=>d.dataset.detail));const active=document.activeElement;const focusKey=active?.dataset.path?['data-path',active.dataset.path]:active?.dataset.itemCount?['data-item-count',active.dataset.itemCount]:active?.dataset.action&&active?.dataset.value?['data-action',active.dataset.action,'data-value',active.dataset.value]:null;const navScroll=$('nav').scrollTop;renderChrome();$('nav').scrollTop=navScroll;const draws={recommend:drawOverview,items:drawItems,roulette:drawRoulette,baccarat:drawBaccarat,poker:drawPoker,bj:drawBJ,craps:drawCraps,money:drawMoney,fortune:drawFortune,hilo:drawHiLo,crash:drawCrash,dragon:()=>drawLadder('dragon'),penguin:()=>drawLadder('penguin'),mines:drawMines,keno:drawKeno,duck:drawDuck,plinko:drawPlinko,slots:drawSlots,camera:drawCamera,budget:drawBudget,floors:drawFloors,sources:drawSources};$('content').innerHTML=draws[state.tab]();renderInlineDecision();document.querySelectorAll('#content details').forEach(d=>{if(opened.has(d.dataset.detail))d.open=true;});if(focusKey){let selector=`[${focusKey[0]}="${CSS.escape(focusKey[1])}"]`;if(focusKey.length>2)selector+=`[${focusKey[2]}="${CSS.escape(focusKey[3])}"]`;document.querySelector('#content '+selector)?.focus({preventScroll:true});}}
function renderInlineDecision(){
 const content=$('content'),right=content.querySelector('#resultRegion'),first=content.querySelector('.workspace > .stack > .panel');
 content.querySelectorAll('.inline-decision').forEach(n=>n.remove());
 if(!right||!first||state.tab==='roulette')return;
 const source=right.querySelector('.hero-result'),error=right.querySelector('.alert.error');if(!source&&!error)return;
 const card=document.createElement('div');card.className='inline-decision'+(source?.classList.contains('caution')||error?' caution':'');card.dataset.for=state.tab;
 const caption=document.createElement('div');caption.className='inline-decision-caption';caption.textContent=source?.querySelector('.kicker')?.textContent||'输入提示';
 const title=document.createElement('strong');title.className='inline-decision-title';title.textContent=source?.querySelector('.decision')?.textContent||'请先检查输入';
 const desc=document.createElement('p');desc.textContent=source?.querySelector('p')?.textContent||error.textContent;card.append(caption,title,desc);
 const selectors={bj:'.bj-selection',poker:'[data-action="solvePoker"], [data-action="cancelPoker"]',baccarat:'.bacc-table',money:'.choices',fortune:'.wheel-visual',hilo:'.grid2',crash:'input[data-path="crash.target"]',dragon:'.ladder-track',penguin:'.ladder-track',mines:'[data-action="mineReset"]',keno:'.choices',plinko:'.ladder-track',slots:'.slot-board',craps:'.choices',budget:'.grid2'};
 let anchor=first.querySelector(selectors[state.tab]||':scope > h2');
 if(state.tab==='bj'&&anchor){(anchor.querySelector('.bj-live-decision')||anchor).append(card);return;}
 if(state.tab==='crash')anchor=anchor?.closest('.field');
 if(state.tab==='mines')anchor=anchor?.closest('.row');
 if(anchor)anchor.after(card);else first.append(card);
}
/*__VIEWS__*/
/*__EVENTS__*/
})();
