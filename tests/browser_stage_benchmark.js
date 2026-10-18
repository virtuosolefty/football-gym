// Optional compute diagnostic. Requires local models and the documented local footage.
// Fixed crops deliberately measure model cost even after loss; this is not tracking accuracy or app throughput.
async (page) => {
  const errors=[],results=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(BASE_URL);
  await page.evaluate(()=>{const input=document.createElement('input');input.type='file';input.id='benchmark-file';document.body.append(input);});
  const clips=[
    {id:'u17-original',file:'test-results/conditions-footage/footage/u17.webm',start:34,count:30,pose:false},
    {id:'u17-normalized',file:'test-results/phase-2026-10-18/u17-normalized.mp4',start:34,count:30,pose:false},
    {id:'looped-30s-with-pose',file:'test-results/validation-2026-10-14/footage/benchmark-volley-loop-30s.mp4',start:0,count:300,pose:true}
  ];
  for(const clip of clips){
    await page.locator('#benchmark-file').setInputFiles(clip.file);
    const result=await page.evaluate(async clip=>{
      const file=document.querySelector('#benchmark-file').files[0],url=URL.createObjectURL(file),video=document.createElement('video');
      video.muted=true;video.preload='auto';video.src=url;document.body.append(video);
      const controller=new AbortController();let pose;
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await file.arrayBuffer())),x=>x.toString(16).padStart(2,'0')).join('');
      try{
        if(video.readyState<2)await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(new Error('Benchmark media did not load')),15000);video.onloadeddata=()=>{clearTimeout(timer);resolve();};video.onerror=()=>{clearTimeout(timer);reject(new Error('Benchmark media failed to decode'));};});
        const loadStart=performance.now(),detector=await BallDetector.load(),detectorLoad=performance.now()-loadStart;
        const poseStart=performance.now();if(clip.pose)pose=await FootPose.load(controller.signal);const poseLoad=performance.now()-poseStart;
        const stages={decode:[],detector:[],pose:[]},started=performance.now();
        for(let i=0;i<clip.count;i++){
          const time=Number((clip.start+i/10).toFixed(3));let before=performance.now();
          await VideoLab.seek(video,time,controller.signal);stages.decode.push(performance.now()-before);before=performance.now();
          const size={width:video.videoWidth,height:video.videoHeight};
          const rect=BallDetector.cropRect({x:size.width/2,y:size.height/2},{gate:150,diameter:20},size);
          await detector.detect(video,rect);stages.detector.push(performance.now()-before);
          if(pose){before=performance.now();await pose.detect(video);stages.pose.push(performance.now()-before);}
        }
        const elapsed=performance.now()-started;
        const stats=values=>{if(!values.length)return null;const ordered=[...values].sort((a,b)=>a-b);return {count:values.length,total_ms:values.reduce((a,b)=>a+b,0),median_ms:ordered[Math.floor(ordered.length/2)],p95_ms:ordered[Math.ceil(ordered.length*.95)-1]};};
        return {id:clip.id,file:clip.file,sha256:digest,width:video.videoWidth,height:video.videoHeight,start:clip.start,window_seconds:clip.count/10,
          samples:clip.count,elapsed_ms:elapsed,detector_load_ms:detectorLoad,pose_load_ms:pose?poseLoad:null,
          stages:Object.fromEntries(Object.entries(stages).map(([key,value])=>[key,stats(value)]))};
      }finally{controller.abort();pose?.close();video.removeAttribute('src');video.load();video.remove();URL.revokeObjectURL(url);}
    },clip);
    if(result.stages.decode.count!==clip.count || result.stages.detector.count!==clip.count || (clip.pose && result.stages.pose.count!==clip.count))throw new Error('Incomplete stage benchmark');
    console.log('BENCHMARK',JSON.stringify(result));results.push(result);
  }
  if(errors.length)throw new Error(errors.join('; '));
  const report={format:'football-stage-benchmark-1',diagnosticOnly:true,notes:'One sequential run per clip; same browser session (model warm after first clip). Fixed native 300 px centre crop, one inference per sample, pose on every sample of the looped clip. Includes decoded-frame copy/pre/post-processing in model timing. Does not measure tracking accuracy, fallback crop cost, UI throughput or natural 30-second juggling.',results,browserErrors:errors};
  const [download]=await Promise.all([page.waitForEvent('download'),page.evaluate(report=>{const a=document.createElement('a'),url=URL.createObjectURL(new Blob([JSON.stringify(report,null,2)],{type:'application/json'}));a.href=url;a.download='stage-benchmark.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);},report)]);
  await download.saveAs('test-results/phase-2026-10-18/stage-benchmark.json');
  return {result:'PASS',diagnosticOnly:true,clips:results.length,samples:results.reduce((total,r)=>total+r.samples,0)};
}
