// Optional actual-model experiment; fixed seed-centred crops are diagnostics, not a tracker accuracy test.
async page => {
 const errors=[],results=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(BASE_URL);
 await page.evaluate(()=>{const input=document.createElement('input');input.type='file';input.id='crop-file';document.body.append(input);});
 for(const clip of [{id:'rain',file:'test-results/validation-2026-10-14/footage/rain.mp4',start:4,x:.593,y:.537},{id:'edge',file:'test-results/conditions-footage/footage/u17.webm',start:34,x:.5391,y:.6222}]) {
  await page.locator('#crop-file').setInputFiles(clip.file);
  const result=await page.evaluate(async clip=>{
   const file=document.querySelector('#crop-file').files[0],url=URL.createObjectURL(file),video=document.createElement('video');video.src=url;video.muted=true;document.body.append(video);
   try {
    await new Promise((resolve,reject)=>{const timer=setTimeout(()=>reject(Error('Decode timeout')),15000);video.onloadeddata=()=>{clearTimeout(timer);resolve();};video.onerror=()=>{clearTimeout(timer);reject(Error(VideoLab.playbackError(video)));};});
    const detector=await BallDetector.load(),rows=[];
    for(let frame=0;frame<6;frame++) {
     const time=clip.start+frame/10;await VideoLab.seek(video,time);
     for(const side of [128,192,256,384,512]) {
      const rect=BallDetector.cropRect({x:clip.x*video.videoWidth,y:clip.y*video.videoHeight},{gate:side/2,diameter:0},{width:video.videoWidth,height:video.videoHeight});
      const start=performance.now(),boxes=await detector.detect(video,rect);
      rows.push({time,side,elapsed_ms:performance.now()-start,boxes:boxes.map(b=>({...b,x:b.x/video.videoWidth,y:b.y/video.videoHeight}))});
     }
    }
    return {id:clip.id,rows};
   } finally {video.removeAttribute('src');video.load();video.remove();URL.revokeObjectURL(url);}
  },clip);
  results.push(result);console.log('CROP',JSON.stringify(result));
 }
 if(errors.length)throw Error(errors.join('; '));
 const [download]=await Promise.all([page.waitForEvent('download'),page.evaluate(results=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(results,null,2)],{type:'application/json'}));a.download='crop-diagnostic.json';a.click();},results)]);
 await download.saveAs('test-results/priorities-2026-10-18/crop-diagnostic.json');
 return {result:'PASS',diagnosticOnly:true,inferences:results.reduce((n,r)=>n+r.rows.length,0)};
}
