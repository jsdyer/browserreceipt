import {SCHEMA,STORAGE,displayValue,compareReceipts,validateReceipt,receiptJSON,normalizeConnection,observerURL} from './model.mjs';
const $=s=>document.querySelector(s),status=$('#status');
let current,baseline=null;
const notes={
'Browser · User agent':'A compatibility string, often reduced or spoofed; it is not proof of your exact device.',
'Hardware · Logical processors':'The browser may expose fewer logical processors than the computer actually has.',
'Hardware · Memory estimate (GB)':'A rounded, privacy-limited estimate, not installed RAM.',
'Display · Viewport':'This tab’s content area. Resizing changes it.',
'Network · Browser online':'An interface hint, not an internet connectivity test.',
'Connection · Network organization':'A VPN, proxy or mobile carrier may appear instead of your home ISP.',
'Connection · Cloudflare edge':'The serving data centre, not your physical location.'};
function safe(fn){try{return fn()??null;}catch{return null;}}
function capture(){
 const n=navigator,s=screen,m=q=>matchMedia(q).matches;
 const values={
 'Browser · User agent':n.userAgent,'Browser · Platform':n.platform||null,
 'Browser · Client hints':n.userAgentData?n.userAgentData.brands.map(x=>x.brand+' '+x.version).join(', '):null,
 'Browser · Mobile hint':n.userAgentData?.mobile??null,'Browser · Languages':n.languages.join(', '),
 'Browser · Cookies enabled':n.cookieEnabled,'Browser · PDF viewer':n.pdfViewerEnabled??null,
 'Privacy · Global Privacy Control':n.globalPrivacyControl??null,'Privacy · Do Not Track':n.doNotTrack??null,
 'Privacy · Reduced motion':m('(prefers-reduced-motion: reduce)'),'Privacy · Colour preference':m('(prefers-color-scheme: dark)')?'Dark':'Light / no dark preference',
 'Locale · Time zone':safe(()=>Intl.DateTimeFormat().resolvedOptions().timeZone),'Locale · UTC offset (minutes)':-new Date().getTimezoneOffset(),
 'Hardware · Logical processors':n.hardwareConcurrency??null,'Hardware · Memory estimate (GB)':n.deviceMemory??null,'Hardware · Touch points':n.maxTouchPoints??null,
 'Display · Screen':s.width+' × '+s.height+' CSS pixels','Display · Available screen':s.availWidth+' × '+s.availHeight+' CSS pixels',
 'Display · Viewport':innerWidth+' × '+innerHeight+' CSS pixels','Display · Pixel ratio':devicePixelRatio,'Display · Colour depth':s.colorDepth,
 'Network · Browser online':n.onLine,'Network · Effective connection':n.connection?.effectiveType??null,'Network · Save-data hint':n.connection?.saveData??null,
 'Capabilities · Secure context':isSecureContext,'Capabilities · WebRTC':typeof RTCPeerConnection!=='undefined',
 'Capabilities · WebGL':safe(()=>!!document.createElement('canvas').getContext('webgl')),'Capabilities · WebGPU API':!!n.gpu,
 'Capabilities · Service workers':'serviceWorker' in n,'Capabilities · Clipboard API':!!n.clipboard,'Capabilities · WebAssembly':typeof WebAssembly!=='undefined'};
 for(const [label,type]of [['H.264','video/mp4; codecs="avc1.42E01E"'],['VP9','video/webm; codecs="vp9"'],['AV1','video/mp4; codecs="av01.0.05M.08"']])values['Media · '+label+' playback']=document.createElement('video').canPlayType(type)||'Not advertised';
 current={schema:SCHEMA,capturedAt:new Date().toISOString(),values};render();status.textContent='Captured browser-visible values. No connection or DNS probe has been sent.';
}
function render(){
 $('#captured').textContent=new Date(current.capturedAt).toLocaleString();$('#count').textContent=Object.keys(current.values).length;
 const grouped=new Map();for(const [key,value]of Object.entries(current.values)){const group=key.split(' · ')[0];if(!grouped.has(group))grouped.set(group,[]);grouped.get(group).push([key,value]);}
 $('#receipt').replaceChildren();for(const [group,rows]of grouped){const section=document.createElement('section');section.className='receipt-card';const h=document.createElement('h2');h.textContent=group;section.append(h);const dl=document.createElement('dl');for(const [key,value]of rows){const dt=document.createElement('dt');dt.textContent=key.split(' · ').slice(1).join(' · ');const dd=document.createElement('dd');dd.textContent=displayValue(value);if(notes[key]){const note=document.createElement('small');note.textContent=notes[key];dd.append(note);}dl.append(dt,dd);}section.append(dl);$('#receipt').append(section);}
 const changes=baseline?compareReceipts(baseline,current):[];
 $('#baseline').textContent=baseline?'Saved '+new Date(baseline.capturedAt).toLocaleString()+' · '+changes.length+' changed fields':'No baseline saved. Save one before changing browser settings or connecting your VPN.';
 $('#changes').replaceChildren();for(const row of changes){const li=document.createElement('li'),strong=document.createElement('strong'),p=document.createElement('p');strong.textContent=row.key;p.textContent=row.before+' → '+row.after;li.append(strong,p);$('#changes').append(li);}$('#forget').disabled=!baseline;
}
function download(text,name){const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type:'application/json'}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);}
$('#capture').onclick=capture;
$('#save').onclick=()=>{try{baseline=validateReceipt(JSON.parse(receiptJSON(current,$('#include-network').checked)));localStorage.setItem(STORAGE,JSON.stringify(baseline));render();status.textContent='Baseline saved in this browser only. Network fields follow the export checkbox.';}catch{status.textContent='Browser storage is unavailable. Export a receipt instead.';}};
$('#forget').onclick=()=>{try{localStorage.removeItem(STORAGE);}catch{}baseline=null;render();status.textContent='Saved baseline removed.';};
$('#export').onclick=()=>download(receiptJSON(current,$('#include-network').checked),'browser-receipt.json');
$('#import').onchange=async e=>{try{const file=e.target.files[0];if(!file)return;if(file.size>100000)throw new Error('Receipt is too large.');baseline=validateReceipt(JSON.parse(await file.text()));render();status.textContent='Imported baseline for this tab only.';}catch(err){status.textContent=err.message;}e.target.value='';};
$('#connection').onclick=async()=>{const button=$('#connection');button.disabled=true;status.textContent='Checking the connection used for this request…';try{const r=await fetch('https://coolcode-visitor-api.jeffdyer.workers.dev/api/browserreceipt/connection',{credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(10000)});if(!r.ok)throw new Error('Connection lookup is unavailable. Your local receipt still works.');Object.assign(current.values,normalizeConnection(await r.json()));render();status.textContent='Connection checked: the address and network seen by this request.';}catch(err){status.textContent=err.name==='TimeoutError'?'Connection lookup timed out.':err.message;}finally{button.disabled=false;}};
$('#permissions').onclick=async()=>{for(const name of ['geolocation','camera','microphone','notifications']){try{current.values['Permissions · '+name]=(await navigator.permissions.query({name})).state;}catch{current.values['Permissions · '+name]='Not queryable in this browser';}}render();status.textContent='Read this site’s permission states. No permission was requested and no device was opened.';};
$('#dns').onclick=async()=>{const button=$('#dns');button.disabled=true;try{const origin=observerURL($('#observer').value);$('#dns-status').textContent='Contacting your selected observer…';const r=await fetch(origin+'/challenge',{method:'POST',credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(8000)});if(!r.ok)throw new Error('The observer could not create a probe.');const challenge=await r.json();if(!/^[a-f0-9]{32}$/.test(challenge.token)||typeof challenge.hostname!=='string'||!new RegExp('^'+challenge.token+'\\.[a-z0-9.-]+$').test(challenge.hostname))throw new Error('The observer returned an invalid probe.');
 const trigger=new AbortController();setTimeout(()=>trigger.abort(),2500);fetch('https://'+challenge.hostname+'/',{mode:'no-cors',credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',signal:trigger.signal}).catch(()=>{});
 let seen=[];for(let i=0;i<5;i++){await new Promise(resolve=>setTimeout(resolve,1200));const result=await fetch(origin+'/result/'+challenge.token,{credentials:'omit',cache:'no-store',referrerPolicy:'no-referrer',signal:AbortSignal.timeout(5000)});if(!result.ok)throw new Error('The observer result is unavailable.');const data=await result.json();seen=Array.isArray(data.resolvers)?data.resolvers.filter(x=>typeof x==='string'&&/^[0-9a-f:.]+$/i.test(x)).slice(0,16):[];if(seen.length)break;}
 current.values['DNS · Observed resolver addresses']=seen.length?seen.join(', '):'No observation';render();$('#dns-status').textContent=seen.length?'Observed recursive resolver egress: '+seen.join(', ')+'. This does not reveal every resolver in the chain.':'No observation arrived. Browser policies, DNS filtering or network failures can prevent this probe; it is not proof of a DNS leak.';
 }catch(err){$('#dns-status').textContent=err.name==='TimeoutError'?'The observer timed out.':err.message;}finally{button.disabled=false;}};
try{const saved=localStorage.getItem(STORAGE);if(saved)baseline=validateReceipt(JSON.parse(saved));}catch{}
capture();
