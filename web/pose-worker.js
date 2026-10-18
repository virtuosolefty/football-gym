'use strict';
let model;
self.onmessage=async({data})=>{
  try{
    if(data.type==='load'){
      const {FilesetResolver,PoseLandmarker}=await import('/vendor/mediapipe/vision_bundle.mjs');
      model=await PoseLandmarker.createFromOptions(await FilesetResolver.forVisionTasks('/vendor/mediapipe/wasm'),{
        baseOptions:{modelAssetPath:'/models/pose_landmarker_lite.task',delegate:'CPU'},runningMode:'IMAGE',numPoses:2
      });
      self.postMessage({ready:true});return;
    }
    // IMAGE mode permits backward sampling and reseeds; VIDEO mode requires increasing timestamps.
    const result=model.detect(data.bitmap),landmarks=result.landmarks;
    let pose={status:landmarks.length===1?'single':landmarks.length?'multiple':'absent'};
    if(landmarks.length===1){
      for(const [side,indices] of [['left',[27,29,31]],['right',[28,30,32]]]){
        const foot=indices.map(i=>landmarks[0][i]);
        if(foot.every(p=>[p.x,p.y,p.visibility,p.presence??p.visibility].every(Number.isFinite) && p.x>=0 && p.x<=1 && p.y>=0 && p.y<=1))
          pose[side]=foot.map(p=>[p.x,p.y,Math.min(p.visibility,p.presence??p.visibility)].map(n=>Number(n.toFixed(5))));
      }
    }
    self.postMessage({pose});
  }catch(error){self.postMessage({error:error.message});}
  finally{data.bitmap?.close();}
};
