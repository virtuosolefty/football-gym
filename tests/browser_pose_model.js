// Optional installed-model smoke test; synthetic footage checks execution, not pose accuracy.
async (page) => {
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(BASE_URL);
  const result=await page.evaluate(async()=>{
    const canvas=document.createElement('canvas');canvas.width=320;canvas.height=180;
    const ctx=canvas.getContext('2d');ctx.fillStyle='black';ctx.fillRect(0,0,320,180);
    const controller=new AbortController(),pose=await FootPose.load(controller.signal);
    try{
      // detect accepts a decoded source with video dimensions; a canvas avoids codec dependence.
      canvas.videoWidth=320;canvas.videoHeight=180;
      const result=await pose.detect(canvas);
      controller.abort();let cancelled=false;
      try{await pose.detect(canvas);}catch(error){cancelled=/cancelled/.test(error.message);}
      return {result,cancelled};
    }finally{pose.close();}
  });
  if(result.result.status!=='absent' || !result.cancelled || errors.length)throw new Error(JSON.stringify({result,errors}));
  return {result:'PASS',actualModel:true,...result,browserErrors:errors};
}
