'use strict';
// shortcut: a COCO-trained YOLOX finds "sports ball" in general footage but was not trained on football juggling; its output still needs review.
// Pre/post-processing is pure and unit-tested. Inference runs locally through ONNX Runtime Web (wasm); nothing leaves this machine.
const BallDetector = (() => {
  const BALL_CLASS=32, STRIDES=[8,16,32], ROW=85, MIN_SIDE=128, CONTEXT_BALLS=8, SCORE_MIN=.2, NMS_IOU=.45;
  const MODEL={name:'yolox_nano',url:'/models/yolox_nano.onnx',size:416}, RUNTIME='/vendor/ort/';
  const NOT_INSTALLED='The local ball detector is not installed. Run: python tools/fetch_detector.py';
  const clamp=(value,low,high)=>Math.min(Math.max(value,low),high);
  // Square native-pixel window around the expected ball: wide enough for the whole search gate, and never so tight that a ball loses context.
  function cropRect(centre, {gate,diameter}, frame) {
    const side=Math.round(clamp(Math.max(gate*2,diameter*CONTEXT_BALLS,MIN_SIDE),1,Math.min(frame.width,frame.height)));
    return {x:Math.round(clamp(centre.x-side/2,0,frame.width-side)),y:Math.round(clamp(centre.y-side/2,0,frame.height-side)),side};
  }
  // YOLOX expects channel-first BGR in 0..255 without normalisation.
  function toTensor(rgba, size) {
    const plane=size*size, tensor=new Float32Array(3*plane);
    for(let i=0;i<plane;i++){tensor[i]=rgba[i*4+2];tensor[plane+i]=rgba[i*4+1];tensor[2*plane+i]=rgba[i*4];}
    return tensor;
  }
  // Raw output rows are [x, y, log w, log h, objectness, 80 class scores] per grid cell, stride 8, 16 then 32.
  function decode(raw, size, threshold=SCORE_MIN) {
    if(raw.length!==STRIDES.reduce((cells,stride)=>cells+(size/stride)**2,0)*ROW)throw new Error('Detector output does not match the model input size.');
    const found=[];let cell=0;
    for(const stride of STRIDES) {
      const cells=size/stride;
      for(let row=0;row<cells;row++) for(let col=0;col<cells;col++,cell++) {
        const base=cell*ROW, score=raw[base+4]*raw[base+5+BALL_CLASS];
        if(score>=threshold)found.push({x:(raw[base]+col)*stride,y:(raw[base+1]+row)*stride,w:Math.exp(raw[base+2])*stride,h:Math.exp(raw[base+3])*stride,score});
      }
    }
    return found;
  }
  function overlap(a, b) {
    const width=Math.min(a.x+a.w/2,b.x+b.w/2)-Math.max(a.x-a.w/2,b.x-b.w/2), height=Math.min(a.y+a.h/2,b.y+b.h/2)-Math.max(a.y-a.h/2,b.y-b.h/2);
    if(width<=0 || height<=0)return 0;
    const shared=width*height;return shared/(a.w*a.h+b.w*b.h-shared);
  }
  const centred=(inner, outer) => Math.abs(inner.x-outer.x)<=outer.w/2 && Math.abs(inner.y-outer.y)<=outer.h/2;
  function nms(boxes, limit=NMS_IOU) {
    const kept=[];
    for(const box of [...boxes].sort((a,b)=>b.score-a.score))if(kept.every(other=>overlap(box,other)<limit && !centred(box,other)))kept.push(box);
    return kept;
  }
  function toFrame(box, rect, size) {
    const scale=rect.side/size;
    return {x:rect.x+box.x*scale,y:rect.y+box.y*scale,w:box.w*scale,h:box.h*scale,score:box.score};
  }
  // `draw(source, rect, size)` returns the crop resampled to size x size RGBA; the browser draws it on a canvas.
  function create(ort, session, draw, model=MODEL) {
    const input=session.inputNames[0], output=session.outputNames[0];
    return {model, async detect(source, rect) {
      const tensor=new ort.Tensor('float32',toTensor(draw(source,rect,model.size),model.size),[1,3,model.size,model.size]);
      const result=await session.run({[input]:tensor});
      return nms(decode(result[output].data,model.size)).map(box=>toFrame(box,rect,model.size));
    }};
  }
  // Confident detections around an anchor given in tracking-canvas pixels, returned in the same space.
  async function near(detector, source, video, canvas, anchor, {radius,gate,threshold=SCORE_MIN,detail=false,accept=()=>true}) {
    const sx=video.width/canvas.width, centre={x:anchor.x*sx,y:anchor.y*sx},diameter=2*radius*sx;
    const rect=cropRect(centre,{gate:gate*sx,diameter},video);
    const inside=(value, limit) => Math.min(limit,Math.max(0,value));
    const find=async rect=>(await detector.detect(source,rect)).filter(box=>box.score>=threshold).map(box=>({x:inside(box.x/sx,canvas.width),y:inside(box.y/sx,canvas.height),w:box.w/sx,h:box.h/sx,score:box.score}));
    // A small ball gets more model pixels in a tight native crop; fall back to the normal motion gate if absent.
    if(detail && diameter<25){
      const tight=cropRect(centre,{gate:0,diameter},video);
      if(tight.side<rect.side){const boxes=await find(tight);if(boxes.length && accept(boxes))return boxes;}
      // A tiny crop can remove useful context. Try one intermediate scale, within the existing search area.
      const context=cropRect(centre,{gate:tight.side,diameter},video);
      if(context.side>tight.side && context.side<rect.side){const boxes=await find(context);if(boxes.length && accept(boxes))return boxes;}
    }
    return find(rect);
  }
  let pending=null;
  const loadScript=src=>new Promise((resolve,reject)=>{const el=document.createElement('script');el.src=src;el.onload=resolve;el.onerror=()=>reject(new Error(NOT_INSTALLED));document.head.append(el);});
  function drawOnCanvas() {
    const canvas=document.createElement('canvas'), ctx=canvas.getContext('2d',{willReadFrequently:true});
    canvas.width=canvas.height=MODEL.size;
    return (source, rect, size) => {ctx.drawImage(source,rect.x,rect.y,rect.side,rect.side,0,0,size,size);return ctx.getImageData(0,0,size,size).data;};
  }
  // Loads the runtime and model once per page; a failed load can be retried after installing the files.
  function load() {
    pending ||= (async () => {
      if(!globalThis.ort)await loadScript(RUNTIME+'ort.wasm.min.js');
      Object.assign(ort.env.wasm,{wasmPaths:RUNTIME,numThreads:1,proxy:false});
      const response=await fetch(MODEL.url);
      if(!response.ok)throw new Error(NOT_INSTALLED);
      return create(ort,await ort.InferenceSession.create(new Uint8Array(await response.arrayBuffer()),{executionProviders:['wasm']}),drawOnCanvas());
    })();
    pending.catch(() => {pending=null;});
    return pending;
  }
  return {MODEL,SCORE_MIN,cropRect,toTensor,decode,nms,toFrame,create,near,load};
})();
if(typeof module!=='undefined')module.exports=BallDetector;
else globalThis.BallDetector=BallDetector;
