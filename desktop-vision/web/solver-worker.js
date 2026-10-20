importScripts('engine.js','blackjack-engine.js');
self.onmessage=({data})=>{
 const {id,mode,payload}=data;
 try{
  if(mode==='blackjack')postMessage({id,result:GWYFBlackjackSolve(payload)});
  else{
   const gen=GWYFEngine.pokerSolve(payload);let next;
   do{next=gen.next();if(!next.done)postMessage({id,progress:next.value.progress});}while(!next.done);
   postMessage({id,result:next.value});
  }
 }catch(e){postMessage({id,error:e.message});}
};
