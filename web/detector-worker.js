'use strict';
let detector;
self.onmessage=async({data})=>{
  try{
    if(data.type==='load'){
      importScripts('/detector.js','/vendor/ort/ort.wasm.min.js');
      Object.assign(ort.env.wasm,{wasmPaths:new URL('/vendor/ort/',self.location.href).href,numThreads:1,proxy:false});
      const response=await fetch(BallDetector.MODEL.url);
      if(!response.ok)throw new Error('The local ball detector is not installed. Run: python tools/fetch_detector.py');
      const session=await ort.InferenceSession.create(new Uint8Array(await response.arrayBuffer()),{executionProviders:['wasm']});
      detector=BallDetector.create(ort,session,rgba=>rgba);
      postMessage({ready:true});
    }else if(data.type==='detect'){
      if(!detector)throw new Error('Load the ball detector before detection.');
      postMessage({boxes:await detector.detect(data.rgba,data.rect)});
    }
  }catch(error){postMessage({error:error.message});}
};
