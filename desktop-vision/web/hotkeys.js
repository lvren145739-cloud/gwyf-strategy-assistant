'use strict';
const VisionHotkeys=(()=>{
 const defaults=Object.freeze({capture:'F8',archive:'F9',accept:'F10',reset:'F11'});
 const modifiers=['Ctrl','Alt','Shift','Win'];
 const named=['Space','Enter','Tab','Backspace','Insert','Delete','Home','End','PageUp','PageDown','Up','Down','Left','Right','Escape'];
 function keyAllowed(key){return named.includes(key)||/^[A-Z0-9]$/.test(key)||/^Num[0-9]$/.test(key)||/^F([1-9]|1[0-9]|2[0-4])$/.test(key);}
 function canonical(value){
  if(value==='')return '';
  if(typeof value!=='string'||value.length>60)throw Error('快捷键格式无效。');
  const parts=value.split('+'),key=parts.pop();
  if(!keyAllowed(key)||parts.some(m=>!modifiers.includes(m))||new Set(parts).size!==parts.length)throw Error('这个按键暂不支持，请使用功能键、字母、数字或组合键。');
  return [...modifiers.filter(m=>parts.includes(m)),key].join('+');
 }
 function normalise(config){
  if(config&&Object.keys(config).sort().join(',')==='accept,archive,capture')config={...defaults,...config};
  if(!config||typeof config!=='object'||Object.keys(config).sort().join(',')!==Object.keys(defaults).sort().join(','))throw Error('需要分别设置四个操作的快捷键。');
  const result=Object.fromEntries(Object.keys(defaults).map(a=>[a,canonical(config[a])])),enabled=Object.values(result).filter(Boolean);
  if(new Set(enabled).size!==enabled.length)throw Error('快捷键重复，请为不同操作设置不同按键。');
  return result;
 }
 function fromEvent(event){
  if(['Control','Shift','Alt','Meta','AltGraph'].includes(event.key))return null;
  let key=event.code||event.key;
  if(/^Key[A-Z]$/.test(key))key=key.slice(3);
  else if(/^Digit[0-9]$/.test(key))key=key.slice(5);
  else if(/^Numpad[0-9]$/.test(key))key='Num'+key.slice(6);
  else if(key==='NumpadEnter')key='Enter';
  else if(key.startsWith('Arrow'))key=key.slice(5);
  else if(key===' ')key='Space';
  if(!keyAllowed(key))throw Error('这个按键暂不支持，请换一个功能键或组合键。');
  return [...[event.ctrlKey,event.altKey,event.shiftKey,event.metaKey].map((on,i)=>on?modifiers[i]:null).filter(Boolean),key].join('+');
 }
 return {defaults,canonical,normalise,fromEvent};
})();
if(typeof module!=='undefined')module.exports=VisionHotkeys;
