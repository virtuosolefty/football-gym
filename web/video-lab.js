'use strict';
const VideoLab = (() => {
  let run=null, events=[], dirty=false, seedPoint=null, engine=null, controller=null, selectionController=null, pendingTime=null, recovery=null, generation=0;
  const stamp=time=>Number(time).toFixed(2)+' s';
  function playbackError(video){
    if(!video.error)return '';
    if(video.error.code===1)return 'Video loading was interrupted. Select the clip again to retry.';
    if(video.error.code===2)return 'The video could not be loaded. Check that the local server is running, then select the clip again.';
    return 'This browser cannot play this clip: its codec is unsupported or its video data cannot be decoded. Export a new MP4 using H.264 video, constant frame rate and frequent keyframes, then upload that copy. Changing the filename to .mp4 will not convert it.';
  }
  function bindPlayback(video,box){
    const update=()=>box.textContent=video.getAttribute('src')?playbackError(video):'';
    video.onerror=update;video.onloadstart=update;video.onloadeddata=update;video.onemptied=()=>box.textContent='';update();
  }
  const kinds=id=>id==='juggling'?['contact','drop']:id==='slalom'?['start','finish','miss']:['pass'];
  function teardown(){generation++;selectionController?.abort();controller?.abort();BallDetector.close?.();controller=null;recovery=null;}
  const statusOf=a=>a.samples.length && !a.report.quality && a.report.status!=='UNMEASURABLE'?'SUSPECT':a.report.status;
  function runsView(s){return `<section class="card" id="lab-runs"><h2>Saved video runs</h2>${s.analyses?.length ? `<div class="table-wrap"><table><thead><tr><th>Assessment</th><th>Window</th><th>Track coverage</th><th>Reviewed events</th><th>Open</th></tr></thead><tbody>${[...s.analyses].reverse().map(a=>`<tr><td data-label="Assessment">${e(s.protocols.find(p=>p.id===a.protocol).name)}</td><td data-label="Window">${stamp(a.start)} – ${stamp(a.end)}</td><td data-label="Track coverage">${Math.round(a.report.coverage*100)}% · ${e(statusOf(a))}</td><td data-label="Reviewed events">${a.annotation?`${a.annotation.events.length} (reviewed)`:'Not reviewed'}</td><td data-label="Open"><button class="link-button" data-lab-open="${a.id}">Review clip ↗</button></td></tr>`).join('')}</tbody></table></div>` : '<p>Tracking reports and reviewed event timelines will appear here.</p>'}</section>`;}
  function updateRuns(){const box=document.querySelector('#lab-runs');if(box)box.outerHTML=runsView(state);}
  function render(s) {
    return title('See what happened.', 'Review a clip, mark the evidence, and turn it into a useful next step.', 'VIDEO / FEEDBACK WORKSPACE') +
      `<div class="notice amber">Ball tracking is experimental and unvalidated on football footage. Coverage cannot prove that the right ball was followed. Review the full window and every provisional contact before creating a measurement. Confirm foot evidence and label pass outcomes yourself.</div>
      <div class="lab-grid"><section class="card"><div class="card-head"><h2>Your evidence clip</h2><span class="pill">Processed on this machine</span></div>
      <div class="form-grid"><label>Saved video<select id="lab-media"><option value="">Choose a clip</option>${s.media.map(m=>`<option value="${m.id}" ${selected(run?.media_id,m.id)}>${e(m.name)}</option>`).join('')}</select></label><label>Assessment type<select id="lab-protocol">${s.protocols.map(p=>`<option value="${p.id}" ${selected(run?.protocol||s.profile.goal,p.id)}>${e(p.name)}</option>`).join('')}</select></label></div>
      <p class="fine">Upload evidence on the Record screen first. Short clips can be annotated; an assessment needs its complete protocol window.</p>
      <p id="lab-playback-error" role="alert" class="form-error"></p><div class="lab-player"><video id="lab-video" controls preload="metadata" playsinline ${run?`src="/api/media/${run.media_id}"`:''}></video><canvas id="lab-frame" width="320" height="180" aria-label="Paused video frame; click the ball to select or re-confirm it" tabindex="0"></canvas></div>
      <div class="toolbar"><button id="lab-back" class="secondary" type="button">−0.1 sec</button><button id="lab-forward" class="secondary" type="button">+0.1 sec</button><label class="check">Playback speed<select id="lab-speed" aria-label="Video playback speed"><option value=".25">0.25×</option><option value=".5">0.5×</option><option value="1" selected>1×</option></select></label></div>
      <div class="form-grid subtitle-divider"><label>Window start (seconds)<input id="lab-start" type="number" min="0" max="600" step=".1" value="${run?.start||0}"></label><label>Window end (seconds)<input id="lab-end" type="number" min=".1" max="600" step=".1" value="${run?.end||30}"></label></div>
      <div class="form-grid"><label>Ball radius (tracking pixels)<input id="lab-radius" type="number" min="2" max="40" value="8"></label><label>Ball centre x / y (normalized)<div class="coordinate-pair"><input id="lab-x" aria-label="Ball centre x" type="number" min="0" max=".999" step=".001" placeholder="0–1"><input id="lab-y" aria-label="Ball centre y" type="number" min="0" max=".999" step=".001" placeholder="0–1"></div></label></div>
      <p class="fine">Pause where the ball is clear. Click the ball or enter its x/y and press Select ball. After two missed samples, any miss near an edge, or a scene change, tracking pauses for another click. Skip the remaining direction if the ball is gone.</p>
      <label class="check"><input id="lab-pose" type="checkbox">Add experimental foot evidence (slower; optional local pose model)</label><p class="fine">Install once: python tools/fetch_pose.py. A nearby foot supports a possible contact; you still confirm it.</p>
      <div class="actions"><button id="lab-select" class="secondary" type="button">Select ball</button><button id="lab-track" class="primary" type="button">Track selected ball ↗</button><button id="lab-manual" class="secondary" type="button">Use manual timeline</button><button id="lab-skip" class="secondary" type="button" hidden>Skip remaining track in this direction</button><button id="lab-cancel" class="secondary" type="button" hidden>Cancel analysis</button></div>
      <p id="lab-status" role="status" aria-live="polite" class="fine subtitle-divider">${run?reportText(run):'Select a saved video to begin.'}</p><p id="lab-quality" class="fine">${run?qualityText(run):''}</p><button id="lab-export" class="secondary" type="button">Export analysis JSON</button><p id="lab-error" role="alert" class="form-error"></p></section>
      <section class="card"><div class="card-head"><h2>Review the event timeline</h2><span id="lab-event-count" class="pill">0 events</span></div>
      <div class="form-grid"><label>Event type<select id="lab-kind"></select></label><label>Foot side<select id="lab-side"><option value="unknown">Not labelled</option><option value="left">Left foot</option><option value="right">Right foot</option></select></label><label>Foot used<select id="lab-foot"><option value="unknown">Not labelled</option><option value="strong">Stronger foot</option><option value="weak">Weaker foot</option></select></label></div>
      <label class="check"><input id="lab-success" type="checkbox" checked>Pass met the target outcome</label><button id="lab-add" class="secondary" type="button">Mark event at playhead</button><div id="lab-events" class="event-list subtitle-divider"></div>
      <label class="subtitle-divider">Timeline reviewer<input id="lab-reviewer" maxlength="80" value="${e(run?.annotation?.reviewer||s.profile.name)}"></label><label class="check"><input id="lab-confirmed" type="checkbox">I checked the full window, removed false contacts and added missed events.</label><button id="lab-save" class="primary" type="button">Save reviewed timeline</button><p id="lab-save-error" class="form-error" role="alert"></p><div id="lab-feedback" class="subtitle-divider"></div>
      <details class="subtitle-divider"><summary>Create an assessment from this timeline</summary><form data-form="video-assessment"><p class="fine">Metrics come from the saved, reviewed events. Enter the physical setup used in this recording. An unchanged timeline can create only one assessment.</p>
      <div class="form-grid"><label>Distance / cone spacing (m)<input name="distance" type="number" min=".1" max="30" step=".1" value="3" required></label><label>Target width (m)<input name="width" type="number" min=".1" max="10" step=".1" value="1" required></label></div><label>Surface<select name="surface"><option>Grass</option><option>Turf</option><option>Hard court</option><option>Indoor</option></select></label>
      ${[['visible','Player, ball and targets were visible'],['fixed_camera','Camera / observation viewpoint was fixed'],['setup_valid','I followed the stated assessment setup']].map(([key,label])=>`<label class="check"><input name="${key}" type="checkbox">${label}</label>`).join('')}<label>Notes<textarea name="notes" maxlength="1000" rows="2"></textarea></label><button class="primary" type="submit">Create video assessment</button><p class="form-error" role="alert"></p></form></details></section></div>${runsView(s)}
      <p class="fine"><a href="/label.html" target="_blank" rel="noopener">Open blind evaluation labelling tool ↗</a></p>`;
  }
  function reportText(a){return a.samples.length ? `Tracker ${statusOf(a)} · Ball found in ${Math.round(a.report.coverage*100)}% of sampled frames (coverage, not model accuracy). ${a.candidates.length} provisional contact proposals. ${a.report.reasons.join(' ')} (${a.configuration?.method==='detector'?'local ball detector':'colour tracker'})` : 'Manual timeline · no automatic ball track. Mark and review events from the full window.';}
  function qualityText(a){const q=a.report.quality?.metrics;if(!a.samples.length)return '';if(!q)return 'Legacy run: correctness diagnostics were not computed. Re-track this window with the current tracker; the original report is preserved.';return `Minimum confidence: ${q.min_score===null?'unavailable':Math.round(q.min_score*100)+'%'}. Maximum motion: ${q.max_speed} frame widths/s. Longest stationary interval (within 1 pixel): ${q.max_stationary_seconds} s. Correctness gate: ${a.report.quality.configured?'configured, unvalidated':'uncalibrated'}.`;}
  function frame(){
    const v=document.querySelector('#lab-video'),canvas=document.querySelector('#lab-frame');if(!v || !canvas || v.readyState<2 || (controller && !recovery))return;
    const scale=Math.min(320/v.videoWidth,640/v.videoHeight);canvas.width=Math.max(16,Math.round(v.videoWidth*scale));canvas.height=Math.max(16,Math.round(v.videoHeight*scale));const ctx=canvas.getContext('2d',{willReadFrequently:true});ctx.drawImage(v,0,0,canvas.width,canvas.height);
    const point=seedPoint || (!recovery && run?.samples?.filter(s=>s.found && Math.abs(s.time-v.currentTime)<=.06).reduce((best,s)=>!best || Math.abs(s.time-v.currentTime)<Math.abs(best.time-v.currentTime)?s:best,null));
    if(point){ctx.strokeStyle='#d0ec8a';ctx.lineWidth=2;ctx.beginPath();ctx.arc(point.x*canvas.width,point.y*canvas.height,Number(document.querySelector('#lab-radius').value),0,Math.PI*2);ctx.stroke();}
  }
  function timeline(){
    const box=document.querySelector('#lab-events');if(!box)return;
    document.querySelector('#lab-event-count').textContent=events.length+' events';
    box.innerHTML=events.map((event,i)=>`<div class="event-row"><button class="link-button" data-lab-seek="${event.time}">${stamp(event.time)}</button><span>${e(event.kind)} · ${e(event.foot)}${event.uncertain?' · uncertain trajectory':''}${event.kind==='pass'?(event.success?' · on target':' · off target'):''}</span><button class="link-button" data-lab-remove="${i}" aria-label="Remove event ${i+1}">Remove</button></div>`).join('') || (run?.annotation && !dirty ? '<p class="fine">Reviewed: no events in this window.</p>' : '<p class="fine">Pause at a contact or pass outcome, choose the label, and mark it. Juggling track proposals appear here for correction.</p>');
  }
  function markDirty(){dirty=true;document.querySelector('#lab-confirmed').checked=false;document.querySelector('#lab-feedback').textContent='Save a reviewed timeline to update feedback.';timeline();}
  function eventOptions(){document.querySelector('#lab-kind').innerHTML=kinds(document.querySelector('#lab-protocol').value).map(k=>`<option>${k}</option>`).join('');}
  function feedbackView(){document.querySelector('#lab-feedback').innerHTML=run?.feedback?.map(f=>`<div class="notice"><strong>${e(f.observation)}</strong><p>${e(f.cue)}</p><div class="actions">${f.times.map(time=>`<button class="link-button" data-lab-seek="${time}">Clip ${stamp(time)} ↗</button>`).join('')}</div><small>Guidance: ${e(drill(f.drill_id)?.name)} · ${e(reviewLabel(drill(f.drill_id)))}</small></div>`).join('') || '<p class="fine">Feedback uses your confirmed outcome and foot labels. It does not infer biomechanics or a cause.</p>';}
  async function seek(v,time,signal){
    if(signal?.aborted)throw new Error('Analysis cancelled.');
    if(v.error)throw new Error(playbackError(v));
    if(Math.abs(v.currentTime-time)<.001 && v.readyState>=2 && !v.seeking)return;
    await new Promise((resolve,reject)=>{
      const done=()=>{if(v.readyState<2 || Math.abs(v.currentTime-time)>.06){failed();return;}cleanup();resolve();};
      const failed=()=>{cleanup();reject(new Error(signal?.aborted?'Analysis cancelled.':'The requested frame could not be decoded reliably. The clip may have irregular timestamps or sparse keyframes. Re-encode to MP4 (H.264, constant frame rate, frequent keyframes) and upload again.'));};
      const timer=setTimeout(failed,15000);function cleanup(){clearTimeout(timer);v.removeEventListener('seeked',done);v.removeEventListener('error',failed);signal?.removeEventListener('abort',failed);}
      v.addEventListener('seeked',done,{once:true});v.addEventListener('error',failed,{once:true});signal?.addEventListener('abort',failed,{once:true});try{v.currentTime=time;}catch{failed();}
    });
  }
  const sampleOf=(time,point,canvas)=>({time:Number(time.toFixed(3)),found:!!point,x:point?Number((point.x/canvas.width).toFixed(6)):null,y:point?Number((point.y/canvas.height).toFixed(6)):null,...(point?.score===undefined?{}:{score:Number(point.score.toFixed(3))})});
  const videoSize=v=>({width:v.videoWidth,height:v.videoHeight});
  async function pickBall(v,canvas,centre,hint,signal){
    let detector=null,note='';try{detector=await BallDetector.load(signal);}catch(error){if(signal?.aborted)throw error;note=error.message;}
    if(detector){
      const first=BallTracker.begin(centre);
      for(const radius of new Set([hint,hint*4,Math.max(2,hint/4)])){
        const found=await BallDetector.near(detector,v,videoSize(v),canvas,centre,{radius,gate:BallTracker.reach(first,radius,canvas.width),signal});
        const underClick=found.filter(box=>Math.abs(box.x-centre.x)<=box.w*.625 && Math.abs(box.y-centre.y)<=box.h*.625),point=BallTracker.advance(first,underClick,radius,canvas.width,canvas.height).point;
        if(!point)continue;
        const fitted=Math.min(40,Math.max(2,Math.round((point.w+point.h)/4)));
        return {centre:{x:point.x,y:point.y},engine:{method:'detector',detector,radius:fitted},note:`Ball found by the local detector (confidence ${Math.round(point.score*100)}%). Radius set to ${fitted} tracking pixels. Start tracking when ready.`};
      }
      throw new Error('The local ball detector found no ball at the clicked spot. Click the centre of the ball, adjust the radius, or use the manual timeline.');
    }
    const clean=document.createElement('canvas');clean.width=canvas.width;clean.height=canvas.height;const ctx=clean.getContext('2d',{willReadFrequently:true});ctx.drawImage(v,0,0,clean.width,clean.height);
    const image=ctx.getImageData(0,0,clean.width,clean.height),colour=BallTracker.seed(image,centre.x,centre.y,hint);
    if(!BallTracker.verify(image,colour,hint,centre))throw new Error(`No ball was found at the clicked spot. Click the ball centre, adjust the radius, or use the manual timeline. ${note}`.trim());
    return {centre,engine:{method:'colour',colour,radius:hint},note:`Colour patch selected. ${note} Review its size, then start tracking.`.replace('  ',' ')};
  }
  function locator(v,canvas,{method,detector,colour,radius},signal){
    const thumbnail=document.createElement('canvas');thumbnail.width=32;thumbnail.height=18;
    const sceneContext=thumbnail.getContext('2d',{willReadFrequently:true}),ctx=canvas.getContext('2d',{willReadFrequently:true});
    return async state=>{
      sceneContext.drawImage(v,0,0,32,18);const scene=sceneContext.getImageData(0,0,32,18).data;
      if(!state.first && BallTracker.sceneChanged(state.scene,scene))return {point:null,state:{...state,lost:true,reason:'scene_change'}};
      let result;
      if(method==='detector')result=BallTracker.advance(state,await BallDetector.near(detector,v,videoSize(v),canvas,state.first?state.anchor:BallTracker.expected(state),{radius:state.size?state.size/2:radius,gate:BallTracker.reach(state,radius,canvas.width),detail:!state.first,signal,accept:boxes=>!!BallTracker.advance(state,boxes,radius,canvas.width,canvas.height).point}),radius,canvas.width,canvas.height);
      else {ctx.drawImage(v,0,0,canvas.width,canvas.height);result=BallTracker.step(state,ctx.getImageData(0,0,canvas.width,canvas.height),colour,radius);}
      return {...result,radius:result.state.size?result.state.size/2:radius,state:{...result.state,scene}};
    };
  }
  async function trackWindow(v,canvas,signal,{seed,locate,start,end,pose},progress,onLost){
    const interval=.1, reseeds=[];let completed=0;
    const ladder=direction=>{const times=[];for(let k=1;;k++){const time=Number((seed.time+direction*k*interval).toFixed(3));if(direction>0?time>=end:time<start)return times;times.push(time);}};
    const forward=ladder(1),backward=ladder(-1),total=forward.length+backward.length+1;
    const advance=async(state,time,find,segment)=>{
      if(signal.aborted)throw new Error('Analysis cancelled.');
      if(state.lost){completed++;progress(time,completed,total);return {state,sample:{...sampleOf(time,null,canvas),segment}};}
      progress(time,completed,total,'Decoding');await seek(v,time,signal);progress(time,completed,total,'Detecting');const result=await find(state);
      if(signal.aborted)throw new Error('Analysis cancelled.');
      const sample={...sampleOf(time,result.point,canvas),segment,...(result.state.reason?{lost_reason:result.state.reason}:{})};
      if(result.point){sample.radius=Number(((result.radius ?? (result.state.size?result.state.size/2:seed.radius))/canvas.width).toFixed(6));}
      if(pose && result.point){progress(time,completed,total,'Foot evidence');sample.pose=await pose.detect(v);}
      if(signal.aborted)throw new Error('Analysis cancelled.');
      completed++;progress(time,completed,total);return {state:result.state,sample};
    };
    const walk=async(from,times,direction)=>{
      let state=from,find=locate,segment=0,skip=false;const out=[];
      for(let i=0;i<times.length;i++){
        const time=times[i],next=await advance(state,time,find,segment);state=next.state;out.push(next.sample);
        if(state.lost && !skip && onLost){
          await seek(v,time,signal);const picked=await onLost({time,direction,bound:times.at(-1),reason:state.reason,signal});
          if(!picked){skip=true;continue;}
          segment=reseeds.length+1;reseeds.push({...picked.seed,segment});find=picked.locate;
          while(i+1<times.length && direction*(times[i+1]-picked.seed.time)<=0){out.push({...sampleOf(times[++i],null,canvas),segment});completed++;}
          state=BallTracker.begin({x:picked.seed.x*canvas.width,y:picked.seed.y*canvas.height});
          const confirmed=await advance(state,picked.seed.time,find,segment);completed--;state=confirmed.state;
          const existing=out.findIndex(s=>s.time===confirmed.sample.time);if(existing>=0)out[existing]=confirmed.sample;else out.push(confirmed.sample);
          if(state.lost)throw new Error('The re-confirmed ball was not detected. Select it again and restart the analysis.');
        }
      }
      return out;
    };
    const anchor=await advance(BallTracker.begin({x:seed.x*canvas.width,y:seed.y*canvas.height}),seed.time,locate,0);
    const after=await walk(anchor.state,forward,1),before=await walk(anchor.state,backward,-1);
    return {samples:[...before,anchor.sample,...after].sort((a,b)=>a.time-b.time),reseeds};
  }
  function assessmentData(form){
    if(!run?.annotation || dirty)throw new Error('Save the current reviewed timeline before creating an assessment.');
    const f=new FormData(form);return {analysis_id:run.id,annotation_id:run.annotation.id,conditions:{distance:Number(f.get('distance')),width:Number(f.get('width')),surface:f.get('surface'),duration:protocol(run.protocol).duration},quality:{visible:f.has('visible'),fixed_camera:f.has('fixed_camera'),setup_valid:f.has('setup_valid')},notes:f.get('notes')};
  }
  function open(id,time,annotationId){run=structuredClone(state.analyses.find(a=>a.id===id)||null);if(run && annotationId){run.annotation=state.video_annotations.find(a=>a.id===annotationId)||run.annotation;run.feedback=state.attempts.find(a=>a.evidence?.annotation_id===annotationId)?.feedback||[];}events=structuredClone(run?.annotation?.events||run?.candidates||[]);dirty=false;seedPoint=engine=null;pendingTime=time??run?.start??0;}
  function reset(){generation++;run=null;events=[];dirty=false;seedPoint=engine=null;pendingTime=null;}
  function bind(){
    const v=document.querySelector('#lab-video'),canvas=document.querySelector('#lab-frame');if(!v)return;
    let locating=false;
    eventOptions();timeline();feedbackView();bindPlayback(v,document.querySelector('#lab-playback-error'));if(v.getAttribute('src'))v.load();
    v.addEventListener('loadeddata',frame);v.addEventListener('seeked',frame);v.addEventListener('timeupdate',frame);
    v.addEventListener('loadedmetadata',()=>{const position=()=>{const time=pendingTime??0;pendingTime=null;v.currentTime=Math.min(v.duration,time);};if(v.duration===Infinity){const discovered=()=>{if(Number.isFinite(v.duration)){v.removeEventListener('durationchange',discovered);position();}};v.addEventListener('durationchange',discovered);v.currentTime=600;}else if(Number.isFinite(v.duration))position();});
    document.querySelector('#lab-media').onchange=event=>{reset();v.pause();canvas.getContext('2d').clearRect(0,0,canvas.width,canvas.height);document.querySelector('#lab-error').textContent='';document.querySelector('#lab-playback-error').textContent='';if(event.target.value)v.src='/api/media/'+event.target.value;else {v.removeAttribute('src');v.load();}eventOptions();timeline();feedbackView();document.querySelector('#lab-confirmed').checked=false;document.querySelector('#lab-status').textContent=event.target.value?'New clip selected. Set a window and save a new video run.':'Select a saved video to begin.';document.querySelector('#lab-quality').textContent='';};
    document.querySelector('#lab-protocol').onchange=()=>{reset();eventOptions();timeline();feedbackView();document.querySelector('#lab-confirmed').checked=false;document.querySelector('#lab-status').textContent='Assessment type changed. Save a new video run for its timeline.';};
    document.querySelector('#lab-speed').onchange=event=>v.playbackRate=Number(event.target.value);
    canvas.onclick=event=>{if(v.readyState<2 || (controller && !recovery) || locating)return;v.pause();const rect=canvas.getBoundingClientRect();document.querySelector('#lab-x').value=((event.clientX-rect.left)/rect.width).toFixed(3);document.querySelector('#lab-y').value=((event.clientY-rect.top)/rect.height).toFixed(3);selectBall();};
    async function selectBall(){
      if(locating || (controller && !recovery))return;
      const token=generation,errorBox=document.querySelector('#lab-error'),status=document.querySelector('#lab-status'),locking=document.querySelectorAll('#lab-select,#lab-track,#lab-manual,#lab-media,#lab-protocol');locating=true;const selection=new AbortController();selectionController=selection;
      try{
        v.pause();if(v.error || v.readyState<2)throw new Error(playbackError(v)||'Wait for the video to load.');seedPoint=engine=null;frame();
        if(!document.querySelector('#lab-x').value || !document.querySelector('#lab-y').value)throw new Error('Click the ball in the paused frame first.');
        const x=Number(document.querySelector('#lab-x').value),y=Number(document.querySelector('#lab-y').value),hint=Number(document.querySelector('#lab-radius').value);
        if(!(hint>=2 && hint<=40) || !(x>=0 && x<1) || !(y>=0 && y<1))throw new Error('Select a visible ball and a radius between 2 and 40 tracking pixels.');
        const time=Number(v.currentTime.toFixed(3));if(recovery && (recovery.direction*(time-recovery.time)<0 || recovery.direction*(time-recovery.bound)>0))throw new Error('Re-confirm the ball inside the remaining tracking direction.');
        errorBox.textContent='';for(const button of locking)button.disabled=true;status.textContent='Looking for the ball…';document.querySelector('#lab-cancel').hidden=false;const picked=await pickBall(v,canvas,{x:x*canvas.width,y:y*canvas.height},hint,selection.signal);
        if(generation!==token || document.querySelector('#lab-video')!==v || controller?.signal.aborted || selection.signal.aborted)return;
        if(Math.abs(v.currentTime-time)>.001)throw new Error('The video moved while the ball was being located. Select the ball again.');
        engine=picked.engine;document.querySelector('#lab-radius').value=engine.radius;seedPoint={x:Number((picked.centre.x/canvas.width).toFixed(6)),y:Number((picked.centre.y/canvas.height).toFixed(6)),time};frame();status.textContent=picked.note;
        if(recovery)recovery.finish({seed:{...seedPoint,radius:engine.radius},locate:locator(v,canvas,engine,controller.signal)});
      }catch(error){if(generation===token && document.querySelector('#lab-video')===v){engine=null;frame();if(!recovery)status.textContent='Select the ball in a paused frame to begin.';errorBox.textContent=selection.signal.aborted?'Analysis cancelled.':error.message;}}
      finally{locating=false;if(selectionController===selection)selectionController=null;if(generation===token && document.querySelector('#lab-video')===v){document.querySelector('#lab-cancel').hidden=!controller;for(const button of locking)button.disabled=!!controller;const select=document.querySelector('#lab-select');if(select && document.querySelector('#lab-video')===v)select.disabled=!!controller && !recovery;}}
    }
    document.querySelector('#lab-select').onclick=selectBall;
    document.querySelector('#lab-export').onclick=()=>{if(!run){document.querySelector('#lab-error').textContent='Save a video run first.';return;}const url=URL.createObjectURL(new Blob([JSON.stringify(run,null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='analysis-'+run.id+'.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
    document.querySelector('#lab-back').onclick=()=>{v.pause();v.currentTime=Math.max(0,v.currentTime-.1);};
    document.querySelector('#lab-forward').onclick=()=>{v.pause();v.currentTime=Math.min(Number.isFinite(v.duration)?v.duration:600,v.currentTime+.1);};
    document.querySelector('#lab-cancel').onclick=()=>{selectionController?.abort();controller?.abort();BallDetector.close?.();if(engine?.method==='detector'){engine=seedPoint=null;document.querySelector('#lab-status').textContent='Select the ball again to restart analysis.';}};document.querySelector('#lab-skip').onclick=()=>recovery?.finish(null);
    async function confirmLost(info){
      const status=document.querySelector('#lab-status'),select=document.querySelector('#lab-select'),skip=document.querySelector('#lab-skip');status.textContent=`Ball lost at ${stamp(info.time)} (${info.reason}). Scrub to a visible ball in the remaining ${info.direction>0?'forward':'backward'} window and click to re-confirm, or skip this direction.`;
      seedPoint=engine=null;v.controls=true;select.disabled=false;skip.hidden=false;for(const id of ['lab-back','lab-forward'])document.querySelector('#'+id).disabled=false;
      return await new Promise((resolve,reject)=>{
        const aborted=()=>finish(null,new Error('Analysis cancelled.'));
        function finish(value,error){info.signal.removeEventListener('abort',aborted);recovery=null;skip.hidden=true;select.disabled=true;v.pause();v.controls=false;for(const id of ['lab-back','lab-forward']){const button=document.querySelector('#'+id);if(button)button.disabled=true;}error?reject(error):resolve(value);}
        recovery={...info,finish};info.signal.addEventListener('abort',aborted,{once:true});frame();if(info.signal.aborted)aborted();
      });
    }
    for(const id of ['lab-track','lab-manual'])document.querySelector('#'+id).onclick=()=>process(id==='lab-track');
    async function process(track){
      if(controller || locating)return;const token=generation,errorBox=document.querySelector('#lab-error'),status=document.querySelector('#lab-status');errorBox.textContent='';let signal,pose,heartbeat;
      try{
        if(v.error)throw new Error(playbackError(v));
        if(!document.querySelector('#lab-media').value || !Number.isFinite(v.duration) || v.readyState<2)throw new Error('Select a playable clip with a finite duration. If timestamps prevent this, re-encode to MP4 (H.264, constant frame rate) and upload again.');
        const start=Number(document.querySelector('#lab-start').value),end=Number(document.querySelector('#lab-end').value);if(!Number.isFinite(start) || !Number.isFinite(end) || start<0 || end<=start || end>v.duration+.01 || end-start>60)throw new Error('Choose a window within the clip, up to 60 seconds.');
        if(track && (!engine || !seedPoint))throw new Error('Select the ball in a clear paused frame first.');if(track && (seedPoint.time<start || seedPoint.time>=end))throw new Error('The ball was selected outside the analysis window. Move the window to include that frame, or select the ball again.');
        const seed=track?{...seedPoint,radius:engine.radius,...(engine.colour?{colour:[...engine.colour]}:{})}:null;
        const tracking=track?{method:engine.method,...(engine.method==='detector'?{detector:{model:BallDetector.MODEL.name,size:BallDetector.MODEL.size,score_threshold:BallDetector.SCORE_MIN}}:{})}:{};
        const media_id=document.querySelector('#lab-media').value,protocol=document.querySelector('#lab-protocol').value;
        controller=new AbortController();signal=controller.signal;document.querySelector('#lab-cancel').hidden=false;
        for(const element of document.querySelectorAll('#lab-track,#lab-manual,#lab-select,#lab-save,#lab-add,#lab-media,#lab-protocol,#lab-start,#lab-end,#lab-radius,#lab-back,#lab-forward,#lab-pose'))element.disabled=true;
        v.pause();v.controls=false;const began=performance.now();let phase='Preparing analysis';
        const showProgress=()=>{if(!recovery && token===generation)status.textContent=`${phase} · ${Math.round((performance.now()-began)/1000)} s elapsed`;};
        heartbeat=setInterval(showProgress,500);showProgress();
        if(track && document.querySelector('#lab-pose').checked){phase='Loading foot evidence';showProgress();pose=await FootPose.load(signal);tracking.pose_model=FootPose.MODEL;}
        const tracked=track?await trackWindow(v,canvas,signal,{seed,locate:locator(v,canvas,engine,controller.signal),start,end,pose},(time,done,total,stage='Tracking')=>{phase=`${stage} · ${Math.min(done,total)}/${total} samples · ${Math.min(100,Math.round(done/total*100))}% · ${stamp(time)}`;showProgress();},confirmLost):{samples:[],reseeds:[]};
        if(signal.aborted)throw new Error('Analysis cancelled.');
        const result=await api('/api/analyses',{media_id,protocol,duration:v.duration,width:v.videoWidth,height:v.videoHeight,start,end,...tracked,seed,...tracking},{signal});
        const s=await api('/api/state',undefined,{signal});if(signal.aborted || token!==generation)return;
        clearInterval(heartbeat);state=s;run=s.analyses.find(a=>a.id===result.id);events=structuredClone(run.candidates);dirty=false;seedPoint=null;status.textContent=reportText(run);document.querySelector('#lab-quality').textContent=qualityText(run);document.querySelector('#lab-confirmed').checked=false;timeline();feedbackView();updateRuns();await seek(v,start,signal);toast('Video run saved locally. Review its timeline.');
      }catch(error){if(token===generation && document.querySelector('#lab-video')===v)errorBox.textContent=signal?.aborted?'Analysis cancelled.':error.message;}
      finally{clearInterval(heartbeat);pose?.close();if(token===generation && document.querySelector('#lab-video')===v){controller=null;recovery=null;v.controls=true;document.querySelector('#lab-cancel').hidden=true;document.querySelector('#lab-skip').hidden=true;for(const element of document.querySelectorAll('#lab-track,#lab-manual,#lab-select,#lab-save,#lab-add,#lab-media,#lab-protocol,#lab-start,#lab-end,#lab-radius,#lab-back,#lab-forward,#lab-pose'))element.disabled=false;frame();}}
    }
    document.querySelector('#lab-add').onclick=()=>{const error=document.querySelector('#lab-save-error');error.textContent='';if(!run){error.textContent='Save a tracked run or use a manual timeline first.';return;}if(v.currentTime<run.start || v.currentTime>run.end){error.textContent='Move the playhead inside the saved window.';return;}const event={time:Number(v.currentTime.toFixed(3)),kind:document.querySelector('#lab-kind').value,foot:document.querySelector('#lab-foot').value,side:document.querySelector('#lab-side').value,success:document.querySelector('#lab-success').checked};if(events.some(e=>e.time===event.time && e.kind===event.kind)){error.textContent='An event already exists at this timestamp.';return;}events.push(event);events.sort((a,b)=>a.time-b.time);markDirty();};
    document.querySelector('#lab-save').onclick=async()=>{const button=document.querySelector('#lab-save'),box=document.querySelector('#lab-save-error');box.textContent='';button.disabled=true;try{if(!run)throw new Error('Save a video run first.');await api('/api/video/annotations',{analysis_id:run.id,events,reviewer:document.querySelector('#lab-reviewer').value,confirmed:document.querySelector('#lab-confirmed').checked});state=await api('/api/state');run=state.analyses.find(a=>a.id===run.id);dirty=false;timeline();feedbackView();updateRuns();toast('Reviewed events saved. Original tracking preserved.');}catch(error){box.textContent=error.message;}finally{button.disabled=false;}};
    document.querySelector('#lab-events').onclick=async event=>{const button=event.target.closest('button');if(!button)return;if(button.dataset.labRemove!==undefined){events.splice(Number(button.dataset.labRemove),1);markDirty();}if(button.dataset.labSeek){v.pause();await seek(v,Number(button.dataset.labSeek)).catch(error=>document.querySelector('#lab-error').textContent=error.message);}};
    document.querySelector('#lab-feedback').onclick=event=>{const button=event.target.closest('[data-lab-seek]');if(button){v.pause();seek(v,Number(button.dataset.labSeek)).catch(error=>document.querySelector('#lab-error').textContent=error.message);}};
  }
  return {render,bind,teardown,open,reset,assessmentData,trackWindow,seek,reportText,playbackError,bindPlayback};
})();
if(typeof module!=='undefined')module.exports=VideoLab;
