'use strict';
(() => {
  const $=id=>document.getElementById('label-'+id),video=$('video'),canvas=$('frame');
  let clip=null,url=null,labels=new Map(),contacts=[],busy=false,dirty=false,loadGeneration=0;
  const time=()=>Number(video.currentTime.toFixed(3));
  const error=message=>$('error').textContent=message;
  const windowBounds=()=>{const start=Number($('start').value),end=Number($('end').value);if(!clip || !Number.isFinite(video.duration) || !(start>=0 && end>start && end<=video.duration+.01 && end-start<=60))throw new Error('Select a playable video and a window within it, up to 60 seconds.');return {start,end};};
  function draw(){
    if(video.readyState<2)return;
    const scale=Math.min(960/video.videoWidth,640/video.videoHeight);canvas.width=Math.round(video.videoWidth*scale);canvas.height=Math.round(video.videoHeight*scale);
    const ctx=canvas.getContext('2d');ctx.drawImage(video,0,0,canvas.width,canvas.height);
    const label=labels.get(time());if(label?.status==='visible'){ctx.beginPath();ctx.arc(label.x*canvas.width,label.y*canvas.height,label.radius*scale,0,2*Math.PI);ctx.strokeStyle='#d0ec8a';ctx.lineWidth=2;ctx.stroke();}
    $('time').textContent=`${time().toFixed(3)} s · ${label?.status||'unlabelled'}`;
    $('count').textContent=`${labels.size} frame labels · ${contacts.length} contacts`;
    $('contacts').replaceChildren(...contacts.map((contact,index)=>{const row=document.createElement('div');row.className='event-row';const seek=document.createElement('button');seek.className='link-button';seek.textContent=contact.time.toFixed(3)+' s';seek.onclick=()=>move(contact.time);const name=document.createElement('span');name.textContent=contact.foot;const remove=document.createElement('button');remove.className='link-button';remove.textContent='Remove';remove.onclick=()=>{contacts.splice(index,1);dirty=true;$('contacts-reviewed').checked=false;draw();};row.append(seek,name,remove);return row;}));
  }
  async function move(target){
    if(busy)return;busy=true;error('');video.pause();
    try{if(Math.abs(video.currentTime-target)>.001 || video.readyState<2)await new Promise((resolve,reject)=>{const done=()=>{if(video.readyState<2 || Math.abs(video.currentTime-target)>.06){failed();return;}cleanup();resolve();},failed=()=>{cleanup();reject(new Error('Could not decode this frame. Re-encode to MP4 (H.264, constant frame rate, frequent keyframes).'));};const timer=setTimeout(failed,15000);function cleanup(){clearTimeout(timer);video.removeEventListener('seeked',done);video.removeEventListener('error',failed);}video.addEventListener('seeked',done,{once:true});video.addEventListener('error',failed,{once:true});try{video.currentTime=target;}catch{failed();}});draw();}catch(e){error(e.message);}finally{busy=false;}
  }
  async function step(direction){try{const {start,end}=windowBounds();const index=Math.max(0,Math.min(Math.ceil((end-start)*10-1e-7)-1,Math.round((video.currentTime-start)*10)+direction));await move(Number((start+index/10).toFixed(3)));}catch(e){error(e.message);}}
  function label(status,point={}){
    try{const {start,end}=windowBounds();if(busy || video.seeking || !video.paused || time()<start || time()>=end)throw new Error('Pause inside the selected window before labelling.');const radius=Number($('radius').value);if(!(radius>=1 && radius<=500))throw new Error('Use a ball radius between 1 and 500 native pixels.');labels.set(time(),{time:time(),status,...point,...(status==='visible'?{radius}:{})});dirty=true;draw();if($('auto').checked && time()+.1<end)step(1);}catch(e){error(e.message);}
  }
  function visible(){const x=Number($('x').value),y=Number($('y').value);if(!$('x').value || !$('y').value || !(x>=0 && x<=1 && y>=0 && y<=1)){error('Enter ball coordinates between 0 and 1, or click its centre.');return;}label('visible',{x,y});}
  canvas.onclick=event=>{const rect=canvas.getBoundingClientRect();$('x').value=((event.clientX-rect.left)/rect.width).toFixed(6);$('y').value=((event.clientY-rect.top)/rect.height).toFixed(6);visible();};
  $('visible').onclick=visible;
  video.addEventListener('seeked',draw);video.addEventListener('loadeddata',draw);video.addEventListener('timeupdate',draw);
  $('file').onchange=async()=>{
    const file=$('file').files[0];if(!file)return;
    const token=++loadGeneration;clip=null;labels.clear();contacts=[];dirty=false;$('contacts-reviewed').checked=false;if(url)URL.revokeObjectURL(url);url=URL.createObjectURL(file);video.src=url;error('');
    try{if(file.size>512*1024*1024)throw new Error('Use an evaluation clip under 512 MB.');const digest=await crypto.subtle.digest('SHA-256',await file.arrayBuffer());if(token!==loadGeneration)return;clip={filename:file.name,sha256:Array.from(new Uint8Array(digest),x=>x.toString(16).padStart(2,'0')).join('')};$('id').value=file.name.replace(/\.[^.]+$/,'');draw();}catch(e){error(e.message);}
  };
  $('begin').onclick=()=>{try{move(windowBounds().start);}catch(e){error(e.message);}};
  $('prev').onclick=()=>step(-1);$('next').onclick=()=>step(1);$('absent').onclick=()=>label('absent');$('occluded').onclick=()=>label('occluded');$('clear').onclick=()=>{labels.delete(time());dirty=true;draw();};
  $('contact').onclick=()=>{try{const {start,end}=windowBounds();if(busy || !video.paused || time()<start || time()>end)throw new Error('Pause at a clear contact inside the window.');if(contacts.some(c=>c.time===time()))throw new Error('A contact is already labelled at this time.');contacts.push({time:time(),kind:'contact',foot:$('foot').value});contacts.sort((a,b)=>a.time-b.time);dirty=true;$('contacts-reviewed').checked=false;draw();}catch(e){error(e.message);}};
  $('export').onclick=()=>{
    try{
      const {start,end}=windowBounds(),reviewer=$('reviewer').value.trim(),id=$('id').value.trim();if(!reviewer || !id || !labels.size)throw new Error('Enter a clip ID, annotator ID and at least one frame label.');
      const conditions=Array.from(document.querySelectorAll('[name=condition]:checked'),x=>x.value);if(!conditions.length)throw new Error('Select the recorded conditions.');
      const data={format:'football-evaluation-1',clip:{...clip,id,width:video.videoWidth,height:video.videoHeight,start,end},annotator:{id:reviewer,role:$('role').value,independent:$('independent').checked && ['coach','second-annotator'].includes($('role').value)},conditions,notes:$('notes').value,sample_interval:.1,frames:[...labels.values()].filter(s=>s.time>=start && s.time<end).sort((a,b)=>a.time-b.time),contacts_reviewed:$('contacts-reviewed').checked,contacts:contacts.filter(c=>c.time>=start && c.time<=end)};
      const link=document.createElement('a'),download=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));link.href=download;link.download=id.replace(/[^a-z0-9_-]/gi,'_')+'-'+reviewer.replace(/[^a-z0-9_-]/gi,'_')+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(download),1000);dirty=false;
    }catch(e){error(e.message);}
  };
  $('import').onchange=async()=>{
    try{const file=$('import').files[0];if(!file || file.size>2_000_000)throw new Error('Choose a labels JSON under 2 MB.');const data=JSON.parse(await file.text());if(data.format!=='football-evaluation-1' || !clip || data.clip?.sha256!==clip.sha256 || !Array.isArray(data.frames) || !Array.isArray(data.contacts))throw new Error('Load the matching video before resuming its labels.');
      if(data.frames.length>1200 || data.contacts.length>1000 || data.frames.some(s=>!Number.isFinite(s.time) || !['visible','absent','occluded'].includes(s.status) || (s.status==='visible' && (!(s.x>=0 && s.x<=1 && s.y>=0 && s.y<=1 && s.radius>=1 && s.radius<=500)))) || data.contacts.some(c=>!Number.isFinite(c.time) || !['left','right','body','unknown'].includes(c.foot)))throw new Error('Invalid evaluation labels.');
      labels=new Map(data.frames.map(s=>[s.time,s]));contacts=data.contacts;$('contacts-reviewed').checked=data.contacts_reviewed===true;$('start').value=data.clip.start;$('end').value=data.clip.end;$('id').value=data.clip.id;$('reviewer').value=data.annotator?.id||'';$('role').value=data.annotator?.role||'second-annotator';$('independent').checked=data.annotator?.independent===true;$('notes').value=data.notes||'';for(const input of document.querySelectorAll('[name=condition]'))input.checked=data.conditions?.includes(input.value);dirty=false;draw();error('');
    }catch(e){error(e.message);}
  };
  document.addEventListener('keydown',event=>{if(event.ctrlKey || event.metaKey || event.altKey || event.target.closest('input,select,textarea,button'))return;const action={ArrowLeft:()=>step(-1),ArrowRight:()=>step(1),a:()=>label('absent'),o:()=>label('occluded')}[event.key];if(action){event.preventDefault();action();}});
  document.addEventListener('change',event=>{if(event.target.id!=='label-import' && event.target.id!=='label-file')dirty=true;if(['label-start','label-end'].includes(event.target.id))$('contacts-reviewed').checked=false;});
  window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});
})();
