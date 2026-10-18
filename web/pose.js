'use strict';
const FootPose=(()=>{
  const MODEL='mediapipe-pose-lite-1';
  async function load(signal){
    if(signal.aborted)throw new Error('Analysis cancelled.');
    const worker=new Worker('/pose-worker.js');let pending=null;
    const close=()=>{worker.terminate();signal.removeEventListener('abort',cancel);pending?.(new Error('Analysis cancelled.'));};
    const cancel=()=>close();signal.addEventListener('abort',cancel,{once:true});
    function request(data,transfer=[]){
      return new Promise((resolve,reject)=>{
        if(signal.aborted){reject(new Error('Analysis cancelled.'));return;}
        const finish=(error,value)=>{clearTimeout(timer);pending=null;worker.onmessage=worker.onerror=null;error?reject(error):resolve(value);};
        const timer=setTimeout(()=>{finish(new Error('Pose processing timed out. Disable foot evidence and retry.'));close();},60000);
        pending=error=>finish(error);worker.onerror=()=>finish(new Error('Could not start local pose processing. Run: python tools/fetch_pose.py'));
        worker.onmessage=({data})=>finish(data.error?new Error('Pose evidence unavailable: '+data.error+'. Run: python tools/fetch_pose.py'):null,data);
        worker.postMessage(data,transfer);
      });
    }
    try{await request({type:'load'});}catch(error){close();throw error;}
    return {close,async detect(video){
      const scale=Math.min(1,640/video.videoWidth),bitmap=await createImageBitmap(video,{resizeWidth:Math.round(video.videoWidth*scale),resizeHeight:Math.round(video.videoHeight*scale)});
      if(signal.aborted){bitmap.close();throw new Error('Analysis cancelled.');}
      return (await request({type:'detect',bitmap},[bitmap])).pose;
    }};
  }
  return {MODEL,load};
})();
