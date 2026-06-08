let allServants=[],currentServant=null,groupServants=[],groupSelected=new Set();
let chatHistory=[],currentFilter='all',currentMode='single';
let lang=localStorage.getItem('chaldea_lang')||'cn';
let masterName=localStorage.getItem('chaldea_master')||'';
let isGroupChat=false,isTyping=false,typewriterTimer=null;

// ═══ Bond System ═══
const BOND_KEY='chaldea_bonds';
const BOND_LEVELS=[
  {level:1,label:'Lv.1',points:0,color:'#999'},
  {level:2,label:'Lv.2',points:5000,color:'#4CAF50'},
  {level:3,label:'Lv.3',points:15000,color:'#2196F3'},
  {level:4,label:'Lv.4',points:30000,color:'#9C27B0'},
  {level:5,label:'Lv.5',points:50000,color:'#FF9800'},
  {level:6,label:'Lv.6',points:80000,color:'#F44336'},
  {level:7,label:'Lv.7',points:120000,color:'#E91E63'},
  {level:8,label:'Lv.8',points:170000,color:'#00BCD4'},
  {level:9,label:'Lv.9',points:230000,color:'#FFD700'},
  {level:10,label:'Lv.10',points:300000,color:'#FF6B00'},
  {level:11,label:'Lv.EX',points:400000,color:'#FF1744'},
  {level:12,label:'Lv.EX',points:500000,color:'#D500F9'},
  {level:13,label:'Lv.EX',points:700000,color:'#651FFF'},
  {level:14,label:'Lv.EX',points:1000000,color:'#00E5FF'},
  {level:15,label:'Lv.MAX',points:1500000,color:'#FFD740'},
];
const BOND_PER_MSG=10;

function getBonds(){try{return JSON.parse(localStorage.getItem(BOND_KEY)||'{}')}catch{return{}}}
function saveBonds(bonds){localStorage.setItem(BOND_KEY,JSON.stringify(bonds))}

function getBond(pid){
  const bonds=getBonds();
  const b=bonds[pid]||{points:0};
  let lvl=1;
  for(let i=BOND_LEVELS.length-1;i>=0;i--){if(b.points>=BOND_LEVELS[i].points){lvl=BOND_LEVELS[i].level;break}}
  const curIdx=BOND_LEVELS.findIndex(l=>l.level===lvl);
  const nextIdx=curIdx<BOND_LEVELS.length-1?curIdx+1:curIdx;
  const cur=BOND_LEVELS[curIdx];
  const next=BOND_LEVELS[nextIdx];
  const progress=curIdx===nextIdx?1:(b.points-cur.points)/(next.points-cur.points);
  return{points:b.points,level:lvl,label:cur.label,color:cur.color,progress:Math.min(1,progress),nextPoints:next.points,isMax:curIdx===nextIdx};
}

function addBondPoints(pid,amount){
  const bonds=getBonds();
  if(!bonds[pid])bonds[pid]={points:0};
  const oldLevel=getBond(pid).level;
  bonds[pid].points+=amount;
  saveBonds(bonds);
  const newBond=getBond(pid);
  return{oldLevel,newLevel:newBond.level,leveled:newBond.level>oldLevel};
}

function resetBond(pid){
  const bonds=getBonds();
  delete bonds[pid];
  saveBonds(bonds);
}

function resetAllBonds(){
  if(!confirm('确定要重置所有从者的羁绊等级吗？\n这将清除所有羁绊点数，此操作不可撤销。'))return;
  localStorage.removeItem(BOND_KEY);
  renderGrid();
  alert('所有羁绊已重置');
}

function updateChatBondDisplay(){
  if(!currentServant||isGroupChat)return;
  const bond=getBond(currentServant.page_id);
  const pct=Math.round(bond.progress*100);
  document.getElementById('chatMeta').innerHTML=currentServant.class+' '+'\u2605'.repeat(currentServant.rarity||0)+' \u00b7 <span style="color:'+bond.color+';cursor:pointer;font-weight:700" onclick="showBondModal('+currentServant.page_id+')">'+bond.label+' ('+bond.points.toLocaleString()+')</span><div class="chat-bond-bar"><div class="bond-bar-bg"><div class="bond-bar-fg" style="width:'+pct+'%;background:'+bond.color+'"></div></div><span class="bond-label" style="color:'+bond.color+'">'+pct+'%</span></div>';
}

function showBondLevelUp(servant,newLevel){
  const bond=getBond(servant.page_id);
  const name=lang==='jp'?servant.name_jp:servant.name_cn;
  const popup=document.createElement('div');
  popup.className='bond-levelup-popup';
  popup.innerHTML='<div class="bond-levelup-inner"><div class="bond-levelup-icon">\u2764</div><div class="bond-levelup-text">羁绊等级提升！</div><div class="bond-levelup-name">'+esc(name)+'</div><div class="bond-levelup-level" style="color:'+bond.color+'">'+bond.label+'</div></div>';
  document.body.appendChild(popup);
  setTimeout(()=>popup.classList.add('show'),10);
  setTimeout(()=>{popup.classList.remove('show');setTimeout(()=>popup.remove(),400)},2500);
}

function showBondModal(pid){
  const servant=allServants.find(s=>s.page_id===pid);
  if(!servant)return;
  const bond=getBond(pid);
  const name=lang==='jp'?servant.name_jp:servant.name_cn;
  const pct=Math.round(bond.progress*100);
  document.getElementById('bondServantName').textContent=name;
  const lvlEl=document.getElementById('bondLevel');
  lvlEl.textContent=bond.label;lvlEl.style.color=bond.color;
  document.getElementById('bondPoints').textContent=bond.points.toLocaleString();
  document.getElementById('bondProgress').style.width=pct+'%';
  document.getElementById('bondProgress').style.background=bond.color;
  if(bond.isMax){document.getElementById('bondNext').textContent='\u5df2\u8fbe\u5230\u6700\u9ad8\u7f81\u7eca';document.getElementById('bondPct').textContent='MAX'}
  else{document.getElementById('bondNext').textContent='\u4e0b\u4e00\u7ea7: '+bond.nextPoints.toLocaleString()+' ('+pct+'%)';document.getElementById('bondPct').textContent=pct+'%'}
  document.getElementById('bondResetBtn').onclick=function(){
    if(!confirm('\u786e\u5b9a\u8981\u91cd\u7f6e\u300c'+name+'\u300d\u7684\u7f81\u7eca\u7b49\u7ea7\u5417\uff1f\n\u8fd9\u5c06\u6e05\u9664\u6240\u6709\u7f81\u7eca\u70b9\u6570\uff0c\u6b64\u64cd\u4f5c\u4e0d\u53ef\u6492\u9500\u3002'))return;
    resetBond(pid);showBondModal(pid);renderGrid();
  };
  document.getElementById('bondModal').classList.add('show');
}
function closeBondModal(){document.getElementById('bondModal').classList.remove('show')}

// ═══ Helpers ═══
function esc(t){return t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\n/g,'<br>')}
function formatText(t){return esc(t)}
function getServantIcon(s){
  if(s.mooncell_icon)return'/assets/mooncell/'+encodeURIComponent(s.mooncell_icon.split('/').pop());
  if(s.icon_file)return'/assets/icon/'+encodeURIComponent(s.icon_file.split('/').pop());
  return'';
}
function downloadText(text,filename){
  const blob=new Blob([text],{type:'text/plain;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=filename;a.click();URL.revokeObjectURL(a.href);
}
function getMasterCall(){return masterName||'前辈'}

// ═══ Archive ═══
const ARCHIVE_KEY='chaldea_archives';
function getArchives(){try{return JSON.parse(localStorage.getItem(ARCHIVE_KEY)||'{}')}catch{return{}}}
function saveArchiveData(k,d){const a=getArchives();a[k]={...d,updated_at:Date.now()};
  // 清理：每个角色最多保留5条存档
  const ids=d.servant_ids||[];
  const prefix='chat_'+[...ids].sort((x,y)=>x-y).join('_')+'_';
  const sameServant=Object.entries(a).filter(([key])=>key.startsWith(prefix)).sort((x,y)=>(y[1].updated_at||0)-(x[1].updated_at||0));
  if(sameServant.length>5){sameServant.slice(5).forEach(([key])=>delete a[key]);}
  localStorage.setItem(ARCHIVE_KEY,JSON.stringify(a))}
function deleteArchiveEntry(k){const a=getArchives();delete a[k];localStorage.setItem(ARCHIVE_KEY,JSON.stringify(a))}
function makeChatKey(ids){return'chat_'+[...ids].sort((a,b)=>a-b).join('_')+'_'+Date.now()}
function autoSave(){
  const tmChar = window._currentTypemoonChar;
  if(!chatHistory.length||(!currentServant&&!groupServants.length&&!tmChar))return;
  let ids, key, names;
  if(isGroupChat){
    ids=groupServants.map(s=>s.page_id);
    key=makeChatKey(ids);
    names=groupServants.map(s=>getCharName(s)).join('、');
  }else if(tmChar){
    ids=[tmChar.page_id];
    key='tm_'+makeChatKey(ids);
    names=getCharName(tmChar);
  }else{
    ids=[currentServant.page_id];
    key=makeChatKey(ids);
    names=getCharName(currentServant);
  }
  saveArchiveData(key,{servant_ids:ids,servant_names:names,is_group:isGroupChat,history:chatHistory,master_name:masterName,language:lang});
}
function timeAgo(ts){const d=Date.now()-ts;if(d<60000)return'刚刚';if(d<3600000)return Math.floor(d/60000)+'分钟前';if(d<86400000)return Math.floor(d/3600000)+'小时前';return Math.floor(d/86400000)+'天前'}

function renderArchiveList(){
  const list=document.getElementById('archiveList');
  const archives=getArchives();
  const entries=Object.entries(archives).sort((a,b)=>(b[1].updated_at||0)-(a[1].updated_at||0));
  if(!entries.length){list.innerHTML='<div class="archive-empty"><div class="icon">📂</div><p>还没有对话记录</p><p style="font-size:12px;margin-top:8px">开始对话后会自动保存</p></div>';return}
  // 型月模式只显示型月存档，FGO模式只显示FGO存档
  const filtered = appMode==='typemoon' ? entries.filter(([k])=>k.startsWith('tm_')) : entries.filter(([k])=>!k.startsWith('tm_'));
  if(!filtered.length){list.innerHTML='<div class="archive-empty"><div class="icon">📂</div><p>还没有对话记录</p></div>';return}
  let html='';
  for(const[key,data]of filtered){
    const time=data.updated_at?timeAgo(data.updated_at):'';
    const lastMsg=data.history&&data.history.length?data.history[data.history.length-1].content:'';
    const preview=lastMsg.length>40?lastMsg.slice(0,40)+'...':lastMsg;
    const sp=getCharById(data.servant_ids[0]);
    let iconSrc=sp?getCharIcon(sp):'';
    html+='<div class="archive-item" onclick="resumeChat(\''+key+'\')">';
    if(iconSrc)html+='<img src="'+iconSrc+'" onerror="this.style.display=\'none\'">';
    html+='<div class="a-info"><div class="a-name">'+esc(data.servant_names||'未知')+(data.is_group?' (群聊)':'')+'</div>';
    html+='<div class="a-preview">'+esc(preview)+'</div></div>';
    html+='<div class="a-time">'+time+'</div>';
    html+='<div class="a-actions">';
    html+='<button class="a-btn" onclick="event.stopPropagation();exportArchive(\''+key+'\')" title="导出">📥</button>';
    html+='<button class="a-btn" onclick="event.stopPropagation();deleteArchiveConfirm(\''+key+'\')" title="删除">🗑</button>';
    html+='</div></div>';
  }
  list.innerHTML=html;
}

function resumeChat(key){
  const data=getArchives()[key];if(!data)return;
  chatHistory=data.history||[];
  isGroupChat=data.is_group||false;
  const isTM = key.startsWith('tm_');
  if(isGroupChat){
    groupServants=data.servant_ids.map(id=>getCharById(id)).filter(Boolean);
    setupGroupChatUI();
  }else{
    const char=getCharById(data.servant_ids[0]);
    if(!char)return;
    if(isTM){
      window._currentTypemoonChar=char;
      window._currentTypemoonKey=char.tm_key;
      currentServant=null;
    }else{
      currentServant=char;
      window._currentTypemoonChar=null;
    }
    setupSingleChatUI();
  }
  const c=document.getElementById('chatMessages');c.innerHTML='';
  for(const msg of chatHistory){if(msg.role==='user')addMsgDOM('user',msg.content);else addMsgDOM('servant',msg.content,msg.servant_name_cn,msg.servant_icon)}
  showScreen('chat');document.getElementById('msgInput').focus();
  checkAchievements();
}
function deleteArchiveConfirm(key){if(!confirm('确定删除这条对话记录？'))return;deleteArchiveEntry(key);renderArchiveList()}
function exportArchive(key){
  const data=getArchives()[key];if(!data)return;
  let text='# CHALDEA 对话记录\n# '+data.servant_names+(data.is_group?' (群聊)':'')+'\n# 御主: '+(data.master_name||'前辈')+'\n\n';
  for(const msg of(data.history||[])){const name=msg.role==='user'?(data.master_name||'前辈'):(msg.servant_name_cn||'从者');text+=name+': '+msg.content+'\n\n'}
  downloadText(text,'chaldea_'+key+'.txt');
}

// ═══ Typewriter ═══
function typewriterEffect(bubbleEl,fullText,onDone){
  if(typewriterTimer){clearInterval(typewriterTimer);typewriterTimer=null}
  isTyping=true;let idx=0;
  const cursor=document.createElement('span');cursor.className='tw-cursor';
  bubbleEl.innerHTML='';bubbleEl.appendChild(cursor);
  const speed=Math.max(15,Math.min(40,2000/fullText.length));
  typewriterTimer=setInterval(()=>{
    if(idx>=fullText.length){clearInterval(typewriterTimer);typewriterTimer=null;cursor.remove();bubbleEl.innerHTML=formatText(fullText);isTyping=false;if(onDone)onDone();return}
    bubbleEl.insertBefore(document.createTextNode(fullText[idx]),cursor);idx++;
    const c=document.getElementById('chatMessages');c.scrollTop=c.scrollHeight;
  },speed);
}

// ═══ Mode ═══
function setMode(mode){
  currentMode=mode;
  document.querySelectorAll('.mode-tab').forEach(t=>t.classList.toggle('active',t.dataset.mode===mode));
  const panels=['single','group','archive','ency','quiz','fortune','compat','moments','calendar','timeline','network','achievements'];
  panels.forEach(p=>{
    const el=document.getElementById(p+'-panel');
    if(el)el.style.display=(p===mode)?'flex':'none';
  });
  if(mode==='archive')renderArchiveList();
  if(mode==='group'){groupSelected.clear();renderGroupGrid()}
  if(mode==='quiz')loadQuiz();
  if(mode==='fortune')renderFortune();
  if(mode==='ency')renderEncyList();
  if(mode==='compat')resetCompat();
  if(mode==='moments')loadMoments();
  if(mode==='calendar')renderCalendar();
  if(mode==='timeline')renderTimeline();
  if(mode==='network')initNetwork();
  if(mode==='achievements')renderAchievements();
}

// ═══ Type-Moon Grid ═══
function renderTypemoonGrid(){
  const grid=document.getElementById('servantGrid');
  const q=document.getElementById('searchInput').value.toLowerCase();
  let html='';
  Object.entries(typemoonChars).forEach(([key,c])=>{
    if(typemoonSeries!=='all'&&c.series!==typemoonSeries)return;
    if(q&&!c.name_cn.toLowerCase().includes(q)&&!(c.name_jp&&c.name_jp.includes(q)))return;
    const initial=c.name_cn[0];
    const roleTag=c.role?'<span class="cls" style="background:rgba(212,168,67,0.15);color:#d4a843">'+c.role+'</span>':'';
    const safeName=c.name_cn.replace(/\//g,'_').replace(/（/g,'(').replace(/）/g,')');
    const iconSrc='/assets/typemoon_icons/'+encodeURIComponent(safeName)+'.jpg';
    html+='<div class="servant-card" onclick="openChatTypemoon(\''+key+'\')">';
    html+='<img src="'+iconSrc+'" alt="'+c.name_cn+'" loading="lazy" onerror="this.style.display=\'none\';this.nextElementSibling.style.display=\'flex\'" style="width:56px;height:56px;border-radius:50%;object-fit:cover;display:block;margin:0 auto 6px;border:2px solid var(--border)">';
    html+='<div style="width:56px;height:56px;border-radius:50%;display:none;align-items:center;justify-content:center;font-size:24px;background:var(--primary);color:var(--accent);margin:0 auto 6px;border:2px solid var(--border)">'+initial+'</div>';
    html+='<div class="name">'+c.name_cn+'</div><div class="meta"><span class="cls">'+c.series+'</span>'+roleTag+'</div>';
    html+='</div>';
  });
  grid.innerHTML=html||'<div style="text-align:center;padding:60px;color:var(--text-light)">没有找到匹配的角色</div>';
}

function openChatTypemoon(key){
  const c=typemoonChars[key];
  if(!c)return;
  // 暂时跳转到 FGO 模式的聊天，后续可以独立实现
  document.getElementById('selection-screen').style.display='none';
  document.getElementById('chat-screen').style.display='flex';
  document.getElementById('chatName').textContent=c.name_cn;
  document.getElementById('chatMeta').textContent=c.series+(c.role?' · '+c.role:'');
  document.getElementById('chatAvatars').innerHTML='<div style="width:40px;height:40px;border-radius:50%;border:2px solid var(--accent);display:flex;align-items:center;justify-content:center;font-size:18px;background:var(--primary);color:var(--accent)">'+c.name_cn[0]+'</div>';
  document.getElementById('chatMessages').innerHTML='<div class="welcome-msg"><div class="icon">🌙</div><p>开始与'+c.name_cn+'对话吧</p></div>';
  // 存储当前聊天的型月角色
  window._currentTypemoonChar = c;
  window._currentTypemoonKey = key;
}

// ═══ Grid ═══
function renderGrid(){
  // Type-Moon mode
  if(appMode==='typemoon'){
    renderTypemoonGrid();
    return;
  }
  // FGO mode (original)
  const grid=document.getElementById('servantGrid');
  const q=document.getElementById('searchInput').value.toLowerCase();
  let filtered=allServants.filter(s=>{
    if(currentFilter!=='all'){if(currentFilter==='Extra'){if(!['Ruler','Avenger','MoonCancer','Alterego','Foreigner','Pretender','Beast','Shielder'].includes(s.class))return false}else if(s.class!==currentFilter)return false}
    if(q)return(s.name_cn&&s.name_cn.toLowerCase().includes(q))||(s.name_jp&&s.name_jp.toLowerCase().includes(q))||(s.nicknames&&s.nicknames.toLowerCase().includes(q));
    return true;
  });
  let html='';
  for(const s of filtered){
    const stars='★'.repeat(s.rarity||0);
    const name=lang==='jp'?(s.name_jp||s.name_cn):(s.name_cn||s.name_jp);
    const iconSrc=getServantIcon(s);
    const bond=getBond(s.page_id);
    const bondBadge=bond.level>1?'<div class="bond-badge" style="background:'+bond.color+'">'+bond.label+'</div>':'';
    const bondRing=bond.level>3?'<div class="bond-ring" style="background:'+bond.color+'">'+bond.level+'</div>':'';
    const bondBar=bond.level>1?'<div class="bond-bar"><div class="bond-bar-fill" style="width:'+Math.round(bond.progress*100)+'%;background:'+bond.color+'"></div></div>':'';
    html+='<div class="servant-card" onclick="openChat('+s.page_id+')" oncontextmenu="event.preventDefault();showBondModal('+s.page_id+')">';
    if(bondBadge)html+=bondBadge;
    if(bondRing)html+=bondRing;
    if(iconSrc)html+='<img src="'+iconSrc+'" alt="'+name+'" loading="lazy" onerror="this.style.display=\'none\'">';
    html+='<div class="name">'+name+'</div><div class="meta"><span class="cls">'+s.class+'</span><span class="rarity">'+stars+'</span></div>';
    if(bondBar)html+=bondBar;
    html+='</div>';
  }
  grid.innerHTML=html;
}

function renderGroupGrid(){
  const grid=document.getElementById('groupGrid');
  const q=document.getElementById('groupSearchInput').value.toLowerCase();
  const chars = getAllChars();
  let filtered=chars.filter(s=>{
    if(q)return(s.name_cn&&s.name_cn.toLowerCase().includes(q))||(s.name_jp&&s.name_jp.toLowerCase().includes(q))||(s.nicknames&&s.nicknames.toLowerCase().includes(q));
    return true;
  });
  let html='';
  for(const s of filtered){
    const name=getCharName(s);
    const iconSrc=getCharIcon(s);
    const sel=groupSelected.has(s.page_id);
    const cls=s.class||s.series||'';
    const stars=s.rarity?'★'.repeat(s.rarity):'';
    html+='<div class="servant-card'+(sel?' selected':'')+'" onclick="toggleGroupSelect('+s.page_id+',this)">';
    html+='<div class="check-mark">✓</div>';
    if(iconSrc)html+='<img src="'+iconSrc+'" alt="'+name+'" loading="lazy" onerror="this.style.display=\'none\'">';
    html+='<div class="name">'+name+'</div><div class="meta"><span class="cls">'+cls+'</span>'+(stars?'<span class="rarity">'+stars+'</span>':'')+'</span></div></div>';
  }
  grid.innerHTML=html;
  updateGroupBar();
}

function toggleGroupSelect(pid,el){
  if(groupSelected.has(pid)){groupSelected.delete(pid);el.classList.remove('selected')}
  else{if(groupSelected.size>=6){alert('最多选择6位从者');return}groupSelected.add(pid);el.classList.add('selected')}
  updateGroupBar();
}
function updateGroupBar(){
  const bar=document.getElementById('groupConfirmBar');
  const info=document.getElementById('groupInfo');
  const btn=document.getElementById('groupConfirmBtn');
  const n=groupSelected.size;
  bar.classList.toggle('show',n>0);
  info.textContent='已选择 '+n+' 位从者'+(n>=2?'':' (至少选2位)');
  btn.disabled=n<2;
}

function setFilter(cls,el){
  currentFilter=cls;
  document.querySelectorAll('.filter-tab').forEach(t=>t.classList.remove('active'));
  el.classList.add('active');renderGrid();
}

// ═══ Language ═══
function toggleLang(){lang=lang==='cn'?'jp':'cn';localStorage.setItem('chaldea_lang',lang);document.getElementById('langToggle').textContent=lang==='cn'?'CN':'JP';renderGrid()}
function updateLangBtn(){document.getElementById('langToggle').textContent=lang==='cn'?'CN':'JP'}

// ═══ Master ═══
function openMasterModal(){document.getElementById('masterNameInput').value=masterName;document.getElementById('masterModal').classList.add('show');document.getElementById('masterNameInput').focus()}
function closeMasterModal(){document.getElementById('masterModal').classList.remove('show')}
function saveMasterName(){masterName=document.getElementById('masterNameInput').value.trim();localStorage.setItem('chaldea_master',masterName);document.getElementById('masterNameBtn').textContent=masterName||'设定御主';closeMasterModal()}
function updateMasterBtn(){document.getElementById('masterNameBtn').textContent=masterName||'设定御主'}

// ═══ Lightbox ═══
function openLightbox(src,name){document.getElementById('lightboxImg').src=src;document.getElementById('lightboxName').textContent=name;document.getElementById('lightbox').classList.add('show')}
function closeLightbox(){document.getElementById('lightbox').classList.remove('show')}

// ═══ Chat Setup ═══
function showScreen(screen){
  document.getElementById('selection-screen').style.display=screen==='selection'?'flex':'none';
  document.getElementById('chat-screen').style.display=screen==='chat'?'flex':'none';
}

function setupSingleChatUI(){
  const name=lang==='jp'?currentServant.name_jp:currentServant.name_cn;
  document.getElementById('chatName').textContent=name;
  const bond=getBond(currentServant.page_id);const pct=Math.round(bond.progress*100);
  document.getElementById('chatMeta').innerHTML=currentServant.class+' '+'\u2605'.repeat(currentServant.rarity||0)+' \u00b7 <span style="color:'+bond.color+';cursor:pointer;font-weight:700" onclick="showBondModal('+currentServant.page_id+')">'+bond.label+' ('+bond.points.toLocaleString()+')</span><div class="chat-bond-bar"><div class="bond-bar-bg"><div class="bond-bar-fg" style="width:'+pct+'%;background:'+bond.color+'"></div></div><span class="bond-label" style="color:'+bond.color+'">'+pct+'%</span></div>';
  const iconPath=getServantIcon(currentServant);
  let avHtml='';
  if(iconPath)avHtml='<img class="avatar" src="'+iconPath+'" onerror="this.style.display=\'none\'">';
  else avHtml='<div class="avatar-ph">?</div>';
  document.getElementById('chatAvatars').innerHTML=avHtml;
  document.getElementById('typingIcon').src=iconPath;
}

function setupGroupChatUI(){
  const names=groupServants.map(s=>lang==='jp'?s.name_jp:s.name_cn).join('、');
  document.getElementById('chatName').textContent=names;
  document.getElementById('chatMeta').textContent='群聊 · '+groupServants.length+'位从者';
  let avHtml='';
  for(const s of groupServants){
    const icon=getServantIcon(s);
    if(icon)avHtml+='<img class="avatar" src="'+icon+'" style="margin-left:-8px" onerror="this.style.display=\'none\'">';
  }
  document.getElementById('chatAvatars').innerHTML=avHtml;
}

function openChat(pid){
  currentServant=allServants.find(s=>s.page_id===pid);if(!currentServant)return;
  chatHistory=[];isGroupChat=false;
  setupSingleChatUI();
  document.getElementById('chatMessages').innerHTML='<div class="welcome-msg"><div class="icon">💬</div><p>开始与 '+(lang==='jp'?currentServant.name_jp:currentServant.name_cn)+' 对话吧</p></div>';
  showScreen('chat');document.getElementById('msgInput').focus();
  localStorage.setItem('chaldea_group_created','1');
  checkAchievements();
}

function startGroupChat(){
  groupServants=[...groupSelected].map(id=>getCharById(id)).filter(Boolean);
  if(groupServants.length<2)return;
  chatHistory=[];isGroupChat=true;
  setupGroupChatUI();
  const names=groupServants.map(s=>getCharName(s)).join('、');
  document.getElementById('chatMessages').innerHTML='<div class="welcome-msg"><div class="icon">👥</div><p>群聊已创建：'+esc(names)+'</p><p style="font-size:12px;margin-top:8px;color:var(--text-light)">从者们会依次回复你的消息</p></div>';
  showScreen('chat');document.getElementById('msgInput').focus();
  localStorage.setItem('chaldea_group_created','1');
  checkAchievements();
}

function goBack(){
  autoSave();
  showScreen('selection');currentServant=null;
  window._currentTypemoonChar=null;
  window._currentTypemoonKey=null;
}

// ═══ Messages ═══
function addMsgDOM(role,text,servantName,servantIcon){
  const c=document.getElementById('chatMessages');
  const w=document.getElementById('welcomeMsg');if(w)w.remove();
  const d=document.createElement('div');d.className='msg '+role;
  if(role==='user'){
    const label=masterName?'<div class="master-label">'+esc(masterName)+'</div>':'';
    d.innerHTML=label+'<div class="bubble">'+esc(text)+'</div>';
  }else{
    let icon=servantIcon||'';
    if(!icon&&currentServant)icon=getServantIcon(currentServant);
    if(!icon&&window._currentTypemoonChar)icon=getTypemoonIcon(window._currentTypemoonChar);
    const label=servantName?'<div class="servant-label">'+esc(servantName)+'</div>':'';
    d.innerHTML=(icon?'<img class="msg-icon" src="'+icon+'" onerror="this.style.display=\'none\'">':'')+'<div class="bubble">'+label+formatText(text)+'</div>';
  }
  c.appendChild(d);c.scrollTop=c.scrollHeight;
  return d;
}

function addMsgDOMWithTypewriter(role,text,servantName,servantIcon){
  const c=document.getElementById('chatMessages');
  const w=document.getElementById('welcomeMsg');if(w)w.remove();
  const d=document.createElement('div');d.className='msg '+role;
  let icon=servantIcon||'';
  if(!icon&&currentServant)icon=getServantIcon(currentServant);
  if(!icon&&window._currentTypemoonChar)icon=getTypemoonIcon(window._currentTypemoonChar);
  const label=servantName?'<div class="servant-label">'+esc(servantName)+'</div>':'';
  const iconHtml=icon?'<img class="msg-icon" src="'+icon+'" onerror="this.style.display=\'none\'">':'';
  d.innerHTML=iconHtml+'<div class="bubble">'+label+'<span class="tw-content"></span></div>';
  c.appendChild(d);
  const bubble=d.querySelector('.tw-content');
  typewriterEffect(bubble,text);
  c.scrollTop=c.scrollHeight;
  return d;
}

function showTyping(v){document.getElementById('typing').style.display=v?'flex':'none'}

// ═══ Send ═══
async function sendMessage(){
  const inp=document.getElementById('msgInput');
  const text=inp.value.trim();if(!text||(!currentServant&&!groupServants.length&&!window._currentTypemoonChar))return;
  if(isTyping){cancelTypewriter();return}
  inp.value='';inp.style.height='auto';
  addMsgDOM('user',text);
  chatHistory.push({role:'user',content:text});
  // 彩蛋：迦勒底亚斯是谎言
  if(text.includes('迦勒底亚斯是谎言')&&appMode==='fgo'){
    localStorage.setItem('chaldeas_lie','1');
    checkAchievements();
  }
  document.getElementById('sendBtn').disabled=true;
  showTyping(true);

  if(isGroupChat){
    await sendGroupMessage(text);
  }else{
    await sendSingleMessage(text);
  }
  document.getElementById('sendBtn').disabled=false;
  inp.focus();
  autoSave();
  checkAchievements();
}

async function sendSingleMessage(text){
  // Type-Moon mode
  if(window._currentTypemoonChar){
    try{
      const c=window._currentTypemoonChar;
      const resp=await fetch('/api/chat',{method:'POST',headers:apiHeaders(),
        body:JSON.stringify({servant_id:0,message:text,history:chatHistory.slice(0,-1),language:lang,master_name:masterName,typemoon_prompt:c.system_prompt,typemoon_name:c.name_cn,typemoon_address:c.address_user||''})
      });
      const data=await resp.json();
      showTyping(false);
      if(data.error){
        addMsgDOM('servant','[错误] '+data.error);
      }else{
        addMsgDOMWithTypewriter('servant',data.response);
        chatHistory.push({role:'assistant',content:data.response});
      }
    }catch(e){
      showTyping(false);addMsgDOM('servant','[连接错误] '+e.message);
    }
    return;
  }
  // FGO mode (original)
  try{
    const resp=await fetch('/api/chat',{method:'POST',headers:apiHeaders(),
      body:JSON.stringify({servant_id:currentServant.page_id,message:text,history:chatHistory.slice(0,-1),language:lang,master_name:masterName})
    });
    const data=await resp.json();
    showTyping(false);
    if(data.error){
      const errMsg=data.error.includes('high risk')||data.error.includes('sensitive')?'原神牛逼':'[错误] '+data.error;
      addMsgDOM('servant',errMsg);
      chatHistory.push({role:'assistant',content:errMsg});
    }else{
      // Easter egg notification
      if(data.easter_egg){
        showEasterEgg();
      }
      addMsgDOMWithTypewriter('servant',data.response);
      chatHistory.push({role:'assistant',content:data.response,servant_name_cn:data.servant_name_cn,servant_icon:getServantIcon(currentServant)});
      // Add bond points
      const bondResult=addBondPoints(currentServant.page_id,BOND_PER_MSG);
      updateChatBondDisplay();
      if(bondResult.leveled){
        setTimeout(()=>showBondLevelUp(currentServant,bondResult.newLevel),500);
      }
    }
  }catch(e){
    showTyping(false);addMsgDOM('servant','[连接错误] '+e.message);
  }
}

async function sendGroupMessage(text){
  try{
    const resp=await fetch('/api/group_chat',{method:'POST',headers:apiHeaders(),
      body:JSON.stringify({servant_ids:groupServants.map(s=>s.page_id),message:text,history:chatHistory.slice(0,-1),language:lang,master_name:masterName})
    });
    const data=await resp.json();
    showTyping(false);
    if(data.error){
      addMsgDOM('servant','[错误] '+data.error);
    }else{
      for(const r of(data.responses||[])){
        const icon=r.icon?('/assets/mooncell/'+encodeURIComponent(r.icon.split('/').pop())):'';
        const name=lang==='jp'?r.servant_name_jp:r.servant_name_cn;
        addMsgDOMWithTypewriter('servant',r.response,name,icon);
        chatHistory.push({role:'assistant',content:r.response,servant_name_cn:r.servant_name_cn,servant_icon:icon});
        // Add bond points for each responding servant
        const bondResult=addBondPoints(r.servant_id,BOND_PER_MSG);
        if(bondResult.leveled){
          const s=allServants.find(sv=>sv.page_id===r.servant_id);
          if(s)showBondLevelUp(s,bondResult.newLevel);
        }
        await new Promise(resolve=>setTimeout(resolve,300));
      }
    }
  }catch(e){
    showTyping(false);addMsgDOM('servant','[连接错误] '+e.message);
  }
}

function handleKey(e){
  if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();sendMessage()}
  e.target.style.height='auto';e.target.style.height=Math.min(e.target.scrollHeight,100)+'px';
}

// ═══ Export Current Chat ═══
function exportChat(){
  if(!chatHistory.length){alert('没有对话记录');return}
  const name=isGroupChat?groupServants.map(s=>lang==='jp'?s.name_jp:s.name_cn).join('、'):(lang==='jp'?currentServant.name_jp:currentServant.name_cn);
  let text='# CHALDEA 对话记录\n# '+name+(isGroupChat?' (群聊)':'')+'\n# 御主: '+(masterName||'前辈')+'\n\n';
  for(const msg of chatHistory){
    const n=msg.role==='user'?(masterName||'前辈'):(msg.servant_name_cn||name);
    text+=n+': '+msg.content+'\n\n';
  }
  downloadText(text,'chaldea_'+name+'.txt');
}

// ═══ Settings ═══
function openSettings(){document.getElementById('settingsModal').classList.add('show')}
function closeSettings(){document.getElementById('settingsModal').classList.remove('show')}

// ── Provider presets (fetched from backend) ──
let providerPresets={};

function onProviderChange(){
  const p=document.getElementById('cfgProvider').value;
  const preset=providerPresets[p];
  if(!preset)return;
  document.getElementById('cfgApiBase').value=preset.api_base||'';
  document.getElementById('cfgModel').value=preset.model||'';
  // Update datalist
  const dl=document.getElementById('modelList');
  dl.innerHTML='';
  (preset.models||[]).forEach(m=>{const o=document.createElement('option');o.value=m;dl.appendChild(o);});
  // Update hints
  document.getElementById('cfgApiBaseHint').textContent='默认: '+preset.api_base;
  document.getElementById('cfgModelHint').textContent=preset.note||('默认: '+preset.model);
}

async function saveSettings(){
  const d={
    provider:document.getElementById('cfgProvider').value,
    api_base:document.getElementById('cfgApiBase').value,
    model:document.getElementById('cfgModel').value
  };
  const k=document.getElementById('cfgApiKey').value;if(k)d.api_key=k;
  await fetch('/api/config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(d)});
  closeSettings();alert('设置已保存');
}

// ── Easter Egg ──
function showEasterEgg(){
  const el=document.getElementById('easterEggModal');
  if(el){el.classList.add('show');}
  // Save achievement
  const a=JSON.parse(localStorage.getItem('chaldea_achievements')||'{}');
  a.look=true;
  localStorage.setItem('chaldea_achievements',JSON.stringify(a));
}
function closeEasterEgg(){
  document.getElementById('easterEggModal').classList.remove('show');
}

// ── Redeem Code ──
function getRedeemCode(){return localStorage.getItem('chaldea_redeemed')||'';}
function apiHeaders(){
  const h={'Content-Type':'application/json'};
  const c=getRedeemCode();if(c)h['X-Redeem-Code']=c;
  return h;
}

async function submitRedeem(){
  const code=document.getElementById('cfgRedeem').value.trim();
  const msgEl=document.getElementById('redeemMsg');
  if(!code){msgEl.textContent='请输入兑换码';msgEl.style.color='#F44336';msgEl.style.display='block';return;}
  try{
    const r=await fetch('/api/redeem',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({code})});
    const d=await r.json();
    if(d.ok){
      localStorage.setItem('chaldea_redeemed',code);
      msgEl.textContent='✅ 兑换成功！已解锁 MiMo 额度';msgEl.style.color='#4CAF50';msgEl.style.display='block';
      updateRedeemStatus();
    }else{
      msgEl.textContent=d.error||'兑换码无效';msgEl.style.color='#F44336';msgEl.style.display='block';
    }
  }catch(e){msgEl.textContent='网络错误';msgEl.style.color='#F44336';msgEl.style.display='block';}
}
function updateRedeemStatus(){
  const code=localStorage.getItem('chaldea_redeemed');
  const el=document.getElementById('redeemStatus');
  if(code){el.textContent='（已兑换 ✅）';el.style.color='#4CAF50';}else{el.textContent='';}
}

// ═══ Init ═══
async function init(){
  updateLangBtn();updateMasterBtn();
  try{
    const resp=await fetch('/api/servants');
    allServants=await resp.json();
    // Merge collection numbers from timeline
    try{
      const tl=await fetch('/api/timeline').then(r=>r.json());
      const cmap={};
      for(const s of(tl.servants||[]))cmap[s.page_id]=s.collection_no;
      for(const s of allServants)s.collection_no=cmap[s.page_id]||9999;
    }catch(e){}
    renderGrid();
  }catch(e){
    document.getElementById('servantGrid').innerHTML='<div style="text-align:center;padding:60px;color:#999">加载失败: '+e.message+'</div>';
  }
  try{
    const cfg=await fetch('/api/config').then(r=>r.json());
    // Load provider presets
    providerPresets=await fetch('/api/providers').then(r=>r.json());
    document.getElementById('cfgProvider').value=cfg.provider||'xiaomi';
    document.getElementById('cfgApiBase').value=cfg.api_base||'';
    document.getElementById('cfgModel').value=cfg.model||'';
    // Set up datalist for current provider
    const cp=cfg.provider||'xiaomi';
    const pp=providerPresets[cp];
    if(pp){
      const dl=document.getElementById('modelList');
      dl.innerHTML='';
      (pp.models||[]).forEach(m=>{const o=document.createElement('option');o.value=m;dl.appendChild(o);});
      document.getElementById('cfgApiBaseHint').textContent='默认: '+pp.api_base;
      document.getElementById('cfgModelHint').textContent=pp.note||('默认: '+pp.model);
    }
  }catch(e){}
  updateRedeemStatus();
}


// ═══ Encyclopedia ═══
function renderEncyList(){
  const panel=document.getElementById('encyContent');
  let html='<div style="padding:12px"><div class="search-bar" style="padding:0 0 12px"><input type="text" id="encySearch" placeholder="搜索从者..." oninput="filterEncy()"></div>';
  html+='<div class="servant-grid" id="encyGrid" style="padding:0"></div></div>';
  panel.innerHTML=html;
  filterEncy();
}
function filterEncy(){
  const q=(document.getElementById('encySearch')?.value||'').toLowerCase();
  const grid=document.getElementById('encyGrid');
  if(!grid)return;
  let html='';
  for(const s of allServants){
    const name=lang==='jp'?(s.name_jp||s.name_cn):(s.name_cn||s.name_jp);
    if(q&&!(name.toLowerCase().includes(q)||(s.nicknames||'').toLowerCase().includes(q)))continue;
    const iconSrc=getServantIcon(s);
    const bond=getBond(s.page_id);
    const bondBadge=bond.level>1?'<div class="bond-badge" style="background:'+bond.color+'">'+bond.label+'</div>':'';
    html+='<div class="servant-card" onclick="openEncy('+s.page_id+')">';
    if(bondBadge)html+=bondBadge;
    if(iconSrc)html+='<img src="'+iconSrc+'" loading="lazy" onerror="this.style.display=\'none\'">';
    html+='<div class="name">'+name+'</div></div>';
  }
  grid.innerHTML=html;
}
async function openEncy(pid){
  const panel=document.getElementById('encyContent');
  panel.innerHTML='<div style="text-align:center;padding:60px;color:var(--text-light)">加载中...</div>';
  try{
    const data=await fetch('/api/servant/'+pid).then(r=>r.json());
    if(data.error){panel.innerHTML='<div style="text-align:center;padding:60px;color:#999">未找到</div>';return}
    const bond=getBond(pid);
    const iconSrc=getServantIcon({mooncell_icon:data.mooncell_icon,icon_file:data.icon_file});
    const name=lang==='jp'?(data.name_jp||data.name_cn):(data.name_cn||data.name_jp);
    let html='<div class="ency-hero">';
    if(iconSrc)html+='<img src="'+iconSrc+'" onerror="this.style.display=\'none\'">';
    html+='<div class="name">'+esc(name)+'</div>';
    html+='<div class="subtitle">'+(data.class||'')+' \\u2605'.repeat(data.rarity||0)+'</div>';
    html+='<div class="rarity" style="color:'+bond.color+';margin-top:8px">'+bond.label+' \\u00b7 '+bond.points.toLocaleString()+' pts</div>';
    html+='</div>';
    // Stats
    html+='<div class="ency-section"><h4>\\u2694 基础属性</h4>';
    html+='<div class="ency-row"><span class="label">ATK</span><span class="value">'+(data.atk_base||'?')+' → '+(data.atk_max||'?')+'</span></div>';
    html+='<div class="ency-row"><span class="label">HP</span><span class="value">'+(data.hp_base||'?')+' → '+(data.hp_max||'?')+'</span></div>';
    html+='<div class="ency-row"><span class="label">性别</span><span class="value">'+(data.gender||'?')+'</span></div>';
    html+='<div class="ency-row"><span class="label">身高</span><span class="value">'+(data.height||'?')+'</span></div>';
    html+='<div class="ency-row"><span class="label">体重</span><span class="value">'+(data.weight||'?')+'</span></div>';
    html+='<div class="ency-row"><span class="label">属性</span><span class="value">'+(data.alignment||'?')+'</span></div>';
    html+='<div class="ency-row"><span class="label">CV</span><span class="value">'+(data.cv||'?')+'</span></div>';
    html+='</div>';
    // Traits
    if(data.traits&&data.traits.length){
      html+='<div class="ency-section"><h4>\\u2728 特性</h4><div class="ency-traits">';
      for(const t of data.traits)html+='<span class="ency-trait">'+esc(t)+'</span>';
      html+='</div></div>';
    }
    // NP
    if(data.noble_phantasms&&data.noble_phantasms.length){
      html+='<div class="ency-section"><h4>\\u26a1 宝具</h4>';
      for(const np of data.noble_phantasms){
        html+='<div class="skill-item" style="padding:10px 0;border-bottom:1px solid var(--bg)">';
        html+='<div class="skill-name">'+esc(np.name_cn||np.name||'')+'</div>';
        html+='<div class="skill-desc">'+esc(np.description||'')+'</div></div>';
      }
      html+='</div>';
    }
    // Skills
    if(data.skills&&data.skills.length){
      html+='<div class="ency-section"><h4>\\u2b50 技能</h4>';
      for(const sk of data.skills){
        html+='<div class="skill-item" style="padding:10px 0;border-bottom:1px solid var(--bg)">';
        html+='<div class="skill-name">'+esc(sk.name_cn||sk.name||'')+'</div>';
        html+='<div class="skill-desc">'+esc(sk.description||'')+'</div></div>';
      }
      html+='</div>';
    }
    // Chat button
    html+='<button class="ency-chat-btn" onclick="openChat('+pid+')">开始对话</button>';
    html+='<div style="height:40px"></div>';
    panel.innerHTML=html;
  }catch(e){
    panel.innerHTML='<div style="text-align:center;padding:60px;color:#999">加载失败: '+e.message+'</div>';
  }
}

// ═══ Quiz ═══
let quizScore=0,quizAnswered=false;
async function loadQuiz(){
  quizAnswered=false;
  const content=document.getElementById('quizContent');
  content.innerHTML='<div class="quiz-loading">加载题目中...</div>';
  try{
    const data=await fetch('/api/quiz').then(r=>r.json());
    if(data.error){content.innerHTML='<div class="quiz-loading">加载失败</div>';return}
    let html='<div class="quiz-q">'+esc(data.question)+'</div>';
    html+='<div class="quiz-choices">';
    for(let i=0;i<data.choices.length;i++){
      html+='<div class="quiz-choice" data-idx="'+i+'" onclick="answerQuiz('+i+','+data.correct_index+')">'+esc(data.choices[i])+'</div>';
    }
    html+='</div>';
    if(data.hint)html+='<div class="quiz-hint">提示: '+esc(data.hint)+'</div>';
    html+='<button class="quiz-next" onclick="loadQuiz()" style="display:none" id="quizNextBtn">下一题</button>';
    content.innerHTML=html;
    document.getElementById('quizScoreNum').textContent=quizScore;
  }catch(e){
    content.innerHTML='<div class="quiz-loading">加载失败: '+e.message+'</div>';
  }
}
function answerQuiz(selected,correct){
  if(quizAnswered)return;
  quizAnswered=true;
  const choices=document.querySelectorAll('.quiz-choice');
  choices.forEach((el,i)=>{
    if(i===correct)el.classList.add('correct');
    else if(i===selected)el.classList.add('wrong');
    el.classList.add('disabled');
  });
  if(selected===correct){quizScore++;document.getElementById('quizScoreNum').textContent=quizScore}
  document.getElementById('quizNextBtn').style.display='block';
}

// ═══ Fortune ═══
function renderFortune(){
  const container=document.getElementById('fortuneContainer');
  const today=new Date();
  const dateStr=today.getFullYear()+'-'+(today.getMonth()+1)+'-'+today.getDate();
  // Use date as seed for daily consistency
  const seed=today.getFullYear()*10000+(today.getMonth()+1)*100+today.getDate();
  const fortunes=[
    {icon:'\\u2728',title:'大吉',text:'今日运势极佳！适合挑战高难度副本，抽卡也有好运加持。'},
    {icon:'\\u2b50',title:'吉',text:'今天适合培养从者和刷素材，稳定推进会有好结果。'},
    {icon:'\\u2606',title:'中吉',text:'运势平稳，适合回顾剧情和整理从者资料。'},
    {icon:'\\u2605',title:'小吉',text:'今天可能会有小惊喜，注意身边的小细节。'},
    {icon:'\\u263c',title:'末吉',text:'运势一般，建议稳扎稳打，不要冲动行事。'},
    {icon:'\\u2603',title:'凶',text:'今天运气不太好，抽卡建议克制，体力可以留到明天。'},
  ];
  const fortune=fortunes[seed%fortunes.length];
  // Pick a random servant as fortune servant
  const servantIdx=seed%allServants.length;
  const servant=allServants[servantIdx];
  const servantName=lang==='jp'?(servant.name_jp||servant.name_cn):(servant.name_cn||servant.name_jp);
  const iconSrc=getServantIcon(servant);
  const luckyColors=['红色','蓝色','金色','绿色','紫色','白色','黑色'];
  const luckyNums=[1,3,5,7,8,9,11,13,21,42];
  const luckyColor=luckyColors[seed%luckyColors.length];
  const luckyNum=luckyNums[seed%luckyNums.length];
  let html='<div class="fortune-card">';
  html+='<div class="icon">'+fortune.icon+'</div>';
  html+='<div class="title">'+fortune.title+'</div>';
  html+='<div class="date">'+dateStr+'</div>';
  html+='<div style="margin:16px 0"><div style="font-size:12px;color:var(--text-light);margin-bottom:8px">今日守护从者</div>';
  if(iconSrc)html+='<img class="servant-img" src="'+iconSrc+'" onerror="this.style.display=\'none\'">';
  html+='<div class="servant-name">'+esc(servantName)+'</div></div>';
  html+='<div class="fortune-text">'+fortune.text+'</div>';
  html+='<div class="lucky">幸运色: <span>'+luckyColor+'</span></div>';
  html+='<div class="lucky">幸运数字: <span>'+luckyNum+'</span></div>';
  html+='<div class="lucky">今日羁绊加成: <span>+50 点</span></div>';
  html+='</div>';
  html+='<button class="fortune-refresh" onclick="claimFortuneBond('+servant.page_id+')">领取羁绊奖励</button>';
  container.innerHTML=html;
}
function claimFortuneBond(pid){
  const key='fortune_'+new Date().toISOString().slice(0,10);
  if(localStorage.getItem(key)){alert('今天已经领取过了');return}
  localStorage.setItem(key,'1');
  addBondPoints(pid,50);
  alert('获得50羁绊点数！');
  checkAchievements();
  renderFortune();
}

// ═══ Compatibility ═══
let compatSlot1=null,compatSlot2=null;
function resetCompat(){
  compatSlot1=null;compatSlot2=null;
  document.getElementById('compatSlot1').innerHTML='<div class="placeholder">+</div>';
  document.getElementById('compatSlot2').innerHTML='<div class="placeholder">+</div>';
  document.getElementById('compatResult').innerHTML='';
  document.getElementById('compatGoBtn').disabled=true;
}
let pickerTarget=0;
function openPicker(target){
  pickerTarget=target;
  document.getElementById('pickerTitle').textContent=target===1?'选择第一位从者':'选择第二位从者';
  document.getElementById('pickerSearch').value='';
  document.getElementById('pickerOverlay').classList.add('show');
  renderPickerGrid();
}
function closePicker(){document.getElementById('pickerOverlay').classList.remove('show')}
function renderPickerGrid(){
  const q=document.getElementById('pickerSearch').value.toLowerCase();
  const grid=document.getElementById('pickerGrid');
  let html='';
  for(const s of allServants){
    const name=lang==='jp'?(s.name_jp||s.name_cn):(s.name_cn||s.name_jp);
    if(q&&!(name.toLowerCase().includes(q)||(s.nicknames||'').toLowerCase().includes(q)))continue;
    const iconSrc=getServantIcon(s);
    html+='<div class="picker-item" onclick="pickServant('+s.page_id+')">';
    if(iconSrc)html+='<img src="'+iconSrc+'" onerror="this.style.display=\'none\'">';
    html+='<div class="name">'+esc(name)+'</div></div>';
  }
  grid.innerHTML=html;
}
function pickServant(pid){
  const servant=allServants.find(s=>s.page_id===pid);
  if(!servant)return;
  const iconSrc=getServantIcon(servant);
  const name=lang==='jp'?(servant.name_jp||servant.name_cn):(servant.name_cn||servant.name_jp);
  if(pickerTarget===1){
    compatSlot1=servant;
    document.getElementById('compatSlot1').innerHTML=iconSrc?'<img src="'+iconSrc+'" title="'+esc(name)+'">':'<div class="placeholder">'+esc(name.charAt(0))+'</div>';
  }else{
    compatSlot2=servant;
    document.getElementById('compatSlot2').innerHTML=iconSrc?'<img src="'+iconSrc+'" title="'+esc(name)+'">':'<div class="placeholder">'+esc(name.charAt(0))+'</div>';
  }
  document.getElementById('compatGoBtn').disabled=!(compatSlot1&&compatSlot2);
  closePicker();
}
async function runCompatibility(){
  if(!compatSlot1||!compatSlot2)return;
  const result=document.getElementById('compatResult');
  result.innerHTML='<div class="compat-loading">分析中...</div>';
  try{
    const resp=await fetch('/api/compatibility',{method:'POST',headers:apiHeaders(),
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({servant_id_1:compatSlot1.page_id,servant_id_2:compatSlot2.page_id,language:lang})
    });
    const data=await resp.json();
    if(data.error){result.innerHTML='<div class="compat-loading">分析失败: '+esc(data.error)+'</div>';return}
    let html='<div class="compat-result">';
    html+='<div class="compat-score-ring" style="border-color:'+(data.score>=70?'#4CAF50':data.score>=40?'#FF9800':'#F44336')+'">'+data.score+'</div>';
    html+='<div style="font-size:14px;color:var(--text-dim);margin-bottom:16px">相性分数</div>';
    html+='<div class="compat-analysis">'+esc(data.analysis||'')+'</div>';
    if(data.fun_interaction)html+='<div class="compat-dialogue">\\u201c'+esc(data.fun_interaction)+'\\u201d</div>';
    html+='</div>';
    result.innerHTML=html;
  }catch(e){
    result.innerHTML='<div class="compat-loading">请求失败: '+e.message+'</div>';
  }
}


// ═══ Moments (朋友圈) ═══
let momentsLiked=new Set(JSON.parse(localStorage.getItem('chaldea_moments_liked')||'[]'));
async function loadMoments(){
  const container=document.getElementById('momentsContainer');
  container.innerHTML='<button class="moment-refresh" onclick="loadMoments()">刷新朋友圈</button><div style="text-align:center;padding:40px;color:var(--text-light)">生成中...</div>';
  const chars = getAllChars();
  const pool=[...chars].sort(()=>Math.random()-0.5).slice(0,5);
  const ids=pool.map(s=>s.page_id);
  const isTM = appMode === 'typemoon';
  try{
    const resp=await fetch('/api/moments',{method:'POST',headers:apiHeaders(),body:JSON.stringify({servant_ids:ids,language:lang,typemoon:isTM})});
    const data=await resp.json();
    if(data.error){container.innerHTML='<div style="text-align:center;padding:40px;color:#999">'+esc(data.error)+'</div>';return}
    let html='<button class="moment-refresh" onclick="loadMoments()">刷新朋友圈</button>';
    for(const post of(data.posts||[])){
      const sp=getCharById(post.servant_id);
      const icon=sp?getCharIcon(sp):'';
      const name=getCharName(sp)||post.servant_name_cn||'';
      const liked=momentsLiked.has(post.servant_id+'_'+post.timestamp);
      html+='<div class="moment-card">';
      html+='<div class="moment-header">';
      if(icon)html+='<img src="'+icon+'" onerror="this.style.display=\'none\'">';
      html+='<div class="info"><div class="name">'+esc(name)+'</div><div class="time">'+(post.timestamp||'刚刚')+'</div></div></div>';
      html+='<div class="moment-content">'+esc(post.content||'')+'</div>';
      html+='<div class="moment-actions">';
      html+='<button class="moment-action'+(liked?' liked':'')+'" onclick="likeMoment(this,\''+post.servant_id+'_'+post.timestamp+'\')">'+(liked?'❤️':'🤍')+' '+(post.likes||0)+'</button>';
      html+='<button class="moment-action" onclick="commentMoment('+post.servant_id+')">💬 评论</button>';
      html+='</div></div>';
    }
    container.innerHTML=html;
  }catch(e){
    container.innerHTML='<button class="moment-refresh" onclick="loadMoments()">刷新朋友圈</button><div style="text-align:center;padding:40px;color:#999">加载失败: '+e.message+'</div>';
  }
}
function likeMoment(el,key){
  if(momentsLiked.has(key)){momentsLiked.delete(key);el.classList.remove('liked');el.innerHTML='🤍 '+(parseInt(el.textContent.match(/\d+/)?.[0]||'0'))}
  else{momentsLiked.add(key);el.classList.add('liked');el.innerHTML='❤️ '+(parseInt(el.textContent.match(/\d+/)?.[0]||'0')+1)}
  localStorage.setItem('chaldea_moments_liked',JSON.stringify([...momentsLiked]));
}
function commentMoment(pid){
  const char=getCharById(pid);
  if(char){
    if(isTypemoon(pid)){window._currentTypemoonChar=char;window._currentTypemoonKey=char.tm_key;currentServant=null}
    else{currentServant=char;window._currentTypemoonChar=null}
    openChat(pid);
  }
}

// ═══ Calendar ═══
let calYear,calMonth;
const BIRTHDAYS={1:[{d:1,n:'冲田总司'},{d:30,n:'贞德'}],2:[{d:3,n:'尼禄'},{d:14,n:'BB'}],3:[{d:8,n:'玛修'},{d:22,n:'斯卡哈'}],4:[{d:6,n:'梅林'},{d:15,n:'迦尔纳'}],5:[{d:1,n:'伊斯坎达尔'},{d:24,n:'恩奇都'}],6:[{d:1,n:'阿尔托莉雅'},{d:19,n:'吉尔伽美什'}],7:[{d:7,n:'库丘林'},{d:30,n:'阿周那'}],8:[{d:1,n:'阿斯托尔福'},{d:15,n:'伊什塔尔'}],9:[{d:20,n:'美杜莎'},{d:29,n:'玉藻前'}],10:[{d:1,n:'弗拉德三世'},{d:21,n:'杰克'}],11:[{d:3,n:'开膛手杰克'},{d:22,n:'南丁格尔'}],12:[{d:1,n:'玛尔达'},{d:25,n:'阿比盖尔'}]};
const TM_BIRTHDAYS={1:[{d:15,n:'远野秋叶'}],2:[{d:3,n:'苍崎橙子'}],3:[{d:12,n:'两仪式'}],4:[{d:11,n:'卫宫士郎'}],5:[{d:3,n:'远坂凛'}],6:[{d:9,n:'间桐樱'}],7:[{d:7,n:'远野志贵'}],8:[{d:15,n:'黑桐干也'}],9:[{d:22,n:'爱尔奎特'}],10:[{d:4,n:'苍崎青子'}],11:[{d:11,n:'黑桐鲜花'}],12:[{d:20,n:'阿尔托莉雅'}]};
function renderCalendar(){
  const now=new Date();
  const bdays = appMode==='typemoon' ? TM_BIRTHDAYS : BIRTHDAYS;
  if(!calYear){calYear=now.getFullYear();calMonth=now.getMonth()+1}
  const container=document.getElementById('calendarContainer');
  const firstDay=new Date(calYear,calMonth-1,1).getDay();
  const daysInMonth=new Date(calYear,calMonth,0).getDate();
  const today=now.getDate();
  const isCurrentMonth=now.getFullYear()===calYear&&now.getMonth()+1===calMonth;
  let html='<div class="calendar-month-header">';
  html+='<button onclick="calMonth--;if(calMonth<0){calMonth=12;calYear--}renderCalendar()">◀</button>';
  html+='<h3>'+calYear+'年'+calMonth+'月</h3>';
  html+='<button onclick="calMonth++;if(calMonth>12){calMonth=1;calYear++}renderCalendar()">▶</button></div>';
  html+='<div class="calendar-grid">';
  const dayNames=['日','一','二','三','四','五','六'];
  for(const d of dayNames)html+='<div class="calendar-day-header">'+d+'</div>';
  for(let i=0;i<firstDay;i++)html+='<div class="calendar-day empty"></div>';
  const monthBdays=bdays[calMonth]||[];
  for(let d=1;d<=daysInMonth;d++){
    const hasBday=monthBdays.some(b=>b.d===d);
    const cls=['calendar-day'];
    if(isCurrentMonth&&d===today)cls.push('today');
    if(hasBday)cls.push('has-birthday');
    html+='<div class="'+cls.join(' ')+'" onclick="showDayEvents('+calMonth+','+d+')">'+d+'</div>';
  }
  html+='</div>';
  // Show birthdays for this month
  if(monthBdays.length){
    html+='<div class="calendar-events"><h4 style="font-size:14px;margin-bottom:10px;color:var(--accent)">🎂 本月生日</h4>';
    for(const b of monthBdays){
      html+='<div class="calendar-event"><div style="font-size:24px;width:36px;text-align:center">🎂</div>';
      html+='<div class="info"><div class="name">'+esc(b.n)+'</div><div class="desc">'+calMonth+'月'+b.d+'日</div></div>';
      html+='<div class="badge">生日</div></div>';
    }
    html+='</div>';
  }
  container.innerHTML=html;
}
function showDayEvents(m,d){
  const bdayList=bdays[m]||[];
  const match=bdayList.filter(b=>b.d===d);
  if(match.length){
    alert(m+'月'+d+'日 生日: '+match.map(b=>b.n).join('、'));
  }
}

// ═══ Timeline ═══
function renderTimeline(){
  const container=document.getElementById('timelineContainer');
  if(appMode==='typemoon'){
    renderTypemoonTimeline(container);
    return;
  }
  const sorted=[...allServants].sort((a,b)=>(a.collection_no||9999)-(b.collection_no||9999));
  // FGO release wave labels (approximate collection number ranges)
  const waves=[
    {start:1,end:58,label:'序章 / 初期从者',year:'2015.7'},
    {start:59,end:106,label:'第一特异点 ~ 第三特异点',year:'2015.8-10'},
    {start:107,end:149,label:'第四特异点 ~ 第五特异点',year:'2015.11-12'},
    {start:150,end:184,label:'第六特异点',year:'2016.1-3'},
    {start:185,end:222,label:'第七特异点 ~ 终章',year:'2016.3-7'},
    {start:223,end:260,label:'第一部完结 / 活动从者',year:'2016.7-12'},
    {start:261,end:310,label:'第二部序章 ~ Lostbelt 1',year:'2017.1-7'},
    {start:311,end:350,label:'Lostbelt 2 ~ 3',year:'2017.7-12'},
    {start:351,end:400,label:'Lostbelt 4 ~ 5',year:'2018.1-12'},
    {start:401,end:450,label:'Lostbelt 6 ~ 7',year:'2019.1-12'},
    {start:451,end:9999,label:'后续从者',year:'2020+'},
  ];
  let html='<h2 style="text-align:center;margin-bottom:8px;color:var(--primary)">从者实装时间线</h2>';
  html+='<p style="text-align:center;font-size:12px;color:var(--text-dim);margin-bottom:24px">按灵基编号（Collection No.）排序 · 共'+sorted.length+'位从者</p>';
  let currentWave='';
  for(const s of sorted){
    const cno=s.collection_no||9999;
    // Find wave
    let wave='';
    for(const w of waves){if(cno>=w.start&&cno<=w.end){wave=w.label;break}}
    if(wave&&wave!==currentWave){
      currentWave=wave;
      const w=waves.find(w=>w.label===wave);
      html+='<div style="text-align:center;margin:24px 0 16px;padding:8px;background:var(--accent-glow);border-radius:8px"><span style="font-weight:700;color:var(--accent);font-size:13px">'+wave+'</span><span style="font-size:11px;color:var(--text-dim);margin-left:8px">'+(w?w.year:'')+'</span></div>';
    }
    const name=lang==='jp'?(s.name_jp||s.name_cn):(s.name_cn||s.name_jp);
    const icon=getServantIcon(s);
    const stars='\u2605'.repeat(s.rarity||0);
    html+='<div class="timeline-item">';
    html+='<div class="tl-dot"></div>';
    html+='<div class="tl-card">';
    if(icon)html+='<img src="'+icon+'" onerror="this.style.display=\'none\'">';
    html+='<div class="name">#'+cno+' '+esc(name)+'</div>';
    html+='<div class="meta">'+s.class+'</div>';
    html+='<div class="rarity">'+stars+'</div>';
    html+='</div></div>';
  }
  container.innerHTML=html;
}

function renderTypemoonTimeline(container){
  const chars = Object.values(typemoonChars);
  const seriesOrder = ['Fate/stay night','Fate/Zero','空之境界','月姬','魔法使之夜','Fate/Apocrypha'];
  const seriesYears = {'Fate/stay night':'2004','Fate/Zero':'2006-2007','空之境界':'1998-1999','月姬':'2000','魔法使之夜':'2012','Fate/Apocrypha':'2012'};
  let html='<h2 style="text-align:center;margin-bottom:8px;color:var(--accent)">型月作品时间线</h2>';
  html+='<p style="text-align:center;font-size:12px;color:var(--text-dim);margin-bottom:24px">按作品分类 · 共'+chars.length+'个角色</p>';
  for(const series of seriesOrder){
    const group = chars.filter(c=>c.series===series);
    if(!group.length) continue;
    html+='<div style="text-align:center;margin:24px 0 16px;padding:8px;background:rgba(74,158,255,0.1);border-radius:8px">';
    html+='<span style="font-weight:700;color:var(--accent);font-size:13px">'+series+'</span>';
    html+='<span style="font-size:11px;color:var(--text-dim);margin-left:8px">'+(seriesYears[series]||'')+'</span></div>';
    for(const c of group){
      const name=getCharName(c);
      const icon=getTypemoonIcon(c);
      const role=c.role||'';
      html+='<div class="timeline-item">';
      html+='<div class="tl-dot"></div>';
      html+='<div class="tl-card">';
      if(icon)html+='<img src="'+icon+'" onerror="this.style.display=\'none\'">';
      html+='<div class="name">'+esc(name)+'</div>';
      html+='<div class="meta">'+series+'</div>';
      if(role)html+='<div class="rarity" style="color:#d4a843">'+role+'</div>';
      html+='</div></div>';
    }
  }
  container.innerHTML=html;
}

// ═══ Relationship Network ═══
function initNetwork(){
  const sel=document.getElementById('networkServant');
  if(sel.options.length<=1){
    let html='<option value="">选择从者...</option>';
    for(const s of allServants){
      const name=lang==='jp'?(s.name_jp||s.name_cn):(s.name_cn||s.name_jp);
      html+='<option value="'+s.page_id+'">'+esc(name)+'</option>';
    }
    sel.innerHTML=html;
  }
}
function updateNetworkBtn(){
  document.getElementById('networkGoBtn').disabled=!document.getElementById('networkServant').value;
}
async function showNetwork(){
  const pid=parseInt(document.getElementById('networkServant').value);
  if(!pid)return;
  const center=allServants.find(s=>s.page_id===pid);
  if(!center)return;
  const result=document.getElementById('networkResult');
  result.innerHTML='<div class="compat-loading">分析关系中...</div>';
  const centerIcon=getServantIcon(center);
  const centerName=lang==='jp'?(center.name_jp||center.name_cn):(center.name_cn||center.name_jp);
  try{
    const resp=await fetch('/api/network',{method:'POST',headers:apiHeaders(),body:JSON.stringify({servant_id:pid})});
    const data=await resp.json();
    if(data.error){result.innerHTML='<div class="compat-loading">'+esc(data.error)+'</div>';return}
    const related=data.relations||[];
    let html='<div class="network-graph">';
    html+='<div class="network-center">';
    if(centerIcon)html+='<img src="'+centerIcon+'" onerror="this.style.display=\'none\'">';
    html+='<div class="name">'+esc(centerName)+'</div></div>';
    const radius=140;
    for(let i=0;i<related.length;i++){
      const s=related[i];
      const angle=(i/related.length)*2*Math.PI-Math.PI/2;
      const x=50+radius*Math.cos(angle)/3;
      const y=50+radius*Math.sin(angle)/3;
      const icon=getServantIcon(s);
      const name=lang==='jp'?(s.name_jp||s.name_cn):(s.name_cn||s.name_jp);
      html+='<div class="network-node" style="left:'+x+'%;top:'+y+'%;transform:translate(-50%,-50%)" onclick="openChat('+s.page_id+')">';
      if(icon)html+='<img src="'+icon+'" onerror="this.style.display=\'none\'">';
      html+='<div class="name">'+esc(name)+'</div></div>';
      const dx=x-50;const dy=y-50;
      const len=Math.sqrt(dx*dx+dy*dy);
      const angleDeg=Math.atan2(dy,dx)*180/Math.PI;
      html+='<div class="network-line" style="left:50%;top:50%;width:'+len+'%;transform:rotate('+angleDeg+'deg)"></div>';
    }
    html+='</div>';
    html+='<div class="network-info">';
    html+='<h4 style="margin-bottom:8px;color:var(--accent)">'+esc(centerName)+' 的关系从者</h4>';
    for(const s of related){
      const name=lang==='jp'?(s.name_jp||s.name_cn):(s.name_cn||s.name_jp);
      html+='<div style="display:flex;align-items:center;gap:8px;padding:6px 0;border-bottom:1px solid var(--bg)">';
      html+='<span style="font-size:12px;color:var(--accent);font-weight:600">'+esc(s.relation||'')+'</span>';
      html+='<span style="font-size:13px;cursor:pointer;color:var(--text)" onclick="openChat('+s.page_id+')">'+esc(name)+'</span>';
      html+='</div>';
    }
    html+='</div>';
    result.innerHTML=html;
  }catch(e){
    result.innerHTML='<div class="compat-loading">请求失败: '+e.message+'</div>';
  }
}

// ═══ Achievements ═══
const ACHIEVEMENTS=[
  {id:'first_chat',name:'初次对话',desc:'与第一位从者对话',icon:'💬',check:()=>{const a=getArchives();return Object.keys(a).length>=1}},
  {id:'chat_5',name:'社交达人',desc:'与5位不同的从者对话',icon:'🗣️',check:()=>{const a=getArchives();return Object.keys(a).length>=5}},
  {id:'chat_10',name:'迦勒底之星',desc:'与10位不同的从者对话',icon:'⭐',check:()=>{const a=getArchives();return Object.keys(a).length>=10}},
  {id:'bond_5',name:'羁绊之心',desc:'任意从者羁绊达到Lv.5',icon:'❤️',check:()=>{const b=getBonds();return Object.values(b).some(v=>v.points>=50000)}},
  {id:'bond_10',name:'永恒羁绊',desc:'任意从者羁绊达到Lv.10',icon:'💖',check:()=>{const b=getBonds();return Object.values(b).some(v=>v.points>=300000)}},
  {id:'quiz_5',name:'FGO学者',desc:'答对5道题',icon:'📚',check:()=>{return quizScore>=5}},
  {id:'quiz_10',name:'FGO大师',desc:'答对10道题',icon:'🎓',check:()=>{return quizScore>=10}},
  {id:'group_chat',name:'群聊达人',desc:'创建一次群聊',icon:'👥',check:()=>{return localStorage.getItem('chaldea_group_created')==='1'}},
  {id:'fortune',name:'每日占卜',desc:'领取一次运势奖励',icon:'🔮',check:()=>{return Object.keys(localStorage).some(k=>k.startsWith('fortune_'))}},
  {id:'ency_5',name:'图鉴收藏家',desc:'查看5位从者的图鉴',icon:'📖',check:()=>{return(parseInt(localStorage.getItem('chaldea_ency_count')||'0'))>=5}},
  {id:'ten_pulls',name:'抽卡模拟',desc:'在抽卡模拟器中抽10次',icon:'🎰',check:()=>{return(parseInt(localStorage.getItem('chaldea_gacha_count')||'0'))>=10}},
  {id:'compat',name:'相性测试',desc:'完成一次从者相性测试',icon:'💕',check:()=>{return localStorage.getItem('chaldea_compat_done')==='1'}},
  {id:'chaldeas_lie',name:'马里斯比利的阴谋',desc:'???',icon:'🔮',check:()=>{return localStorage.getItem('chaldeas_lie')==='1'}},
];
const TM_ACHIEVEMENTS=[
  {id:'tm_first_chat',name:'型月初遇',desc:'与第一位型月角色对话',icon:'🌙',check:()=>{const a=getArchives();return Object.keys(a).some(k=>k.startsWith('tm_'))}},
  {id:'tm_chat_5',name:'型月交际',desc:'与5位不同的型月角色对话',icon:'⭐',check:()=>{const a=getArchives();return Object.keys(a).filter(k=>k.startsWith('tm_')).length>=5}},
  {id:'tm_chat_10',name:'型月百晓',desc:'与10位不同的型月角色对话',icon:'🌟',check:()=>{const a=getArchives();return Object.keys(a).filter(k=>k.startsWith('tm_')).length>=10}},
  {id:'tm_group',name:'型月群英',desc:'创建一次型月群聊',icon:'👥',check:()=>{return localStorage.getItem('tm_group_created')==='1'}},
  {id:'tm_fsn',name:'FSN全角色',desc:'与所有FSN角色对话',icon:'⚔️',check:()=>{const a=getArchives();const fsn=['卫宫士郎','阿尔托莉雅','远坂凛','间桐樱','美杜莎','伊莉雅丝菲尔','吉尔伽美什','言峰绮礼'];return fsn.every(n=>Object.keys(a).some(k=>k.includes(n)))}},
  {id:'tm_kara',name:'空境探索者',desc:'与所有空之境界角色对话',icon:'🔪',check:()=>{const a=getArchives();const kara=['两仪式','黑桐干也','苍崎橙子'];return kara.every(n=>Object.keys(a).some(k=>k.includes(n)))}},
];
function getAchievementData(){try{return JSON.parse(localStorage.getItem('chaldea_achievements')||'{}')}catch{return{}}}
function saveAchievementData(d){localStorage.setItem('chaldea_achievements',JSON.stringify(d))}
function checkAchievements(){
  const data=getAchievementData();
  let newUnlock=false;
  for(const a of ACHIEVEMENTS){
    if(!data[a.id]&&a.check()){
      data[a.id]={unlocked_at:Date.now()};
      newUnlock=true;
      showAchievementPopup(a);
    }
  }
  saveAchievementData(data);
  return newUnlock;
}
function showAchievementPopup(achievement){
  const popup=document.createElement('div');
  popup.className='bond-levelup-popup';
  popup.innerHTML='<div class="bond-levelup-inner"><div class="bond-levelup-icon">'+achievement.icon+'</div><div class="bond-levelup-text">成就解锁！</div><div class="bond-levelup-name">'+achievement.name+'</div></div>';
  document.body.appendChild(popup);
  setTimeout(()=>popup.classList.add('show'),10);
  setTimeout(()=>{popup.classList.remove('show');setTimeout(()=>popup.remove(),400)},3000);
}
function renderAchievements(){
  const container=document.getElementById('achievementsContainer');
  const data=getAchievementData();
  const achievements = appMode==='typemoon' ? TM_ACHIEVEMENTS : ACHIEVEMENTS;
  const unlocked=Object.keys(data).filter(id=>achievements.some(a=>a.id===id)).length;
  let html='<h2 style="text-align:center;margin-bottom:20px;color:'+(appMode==='typemoon'?'var(--accent)':'var(--primary)')+'">'+(appMode==='typemoon'?'型月成就':'成就系统')+'</h2>';
  html+='<div class="achievement-stats">';
  html+='<div class="achievement-stat"><div class="num">'+unlocked+'</div><div class="label">已解锁</div></div>';
  html+='<div class="achievement-stat"><div class="num">'+achievements.length+'</div><div class="label">总成就</div></div>';
  html+='<div class="achievement-stat"><div class="num">'+Math.round(unlocked/achievements.length*100)+'%</div><div class="label">完成度</div></div>';
  html+='</div>';
  for(const a of achievements){
    const isUnlocked=!!data[a.id];
    html+='<div class="achievement-card '+(isUnlocked?'unlocked':'locked')+'">';
    html+='<div class="icon">'+a.icon+'</div>';
    html+='<div class="info"><div class="name">'+a.name+'</div><div class="desc">'+a.desc+'</div></div>';
    html+=isUnlocked?'<div class="unlocked-badge">已解锁</div>':'<div class="progress">🔒</div>';
    html+='</div>';
  }
  container.innerHTML=html;
}

document.addEventListener('keydown',e=>{if(e.key==='Escape'){closeLightbox();closeMasterModal();closeSettings();closeBondModal()}});
init();
