'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),detector=require('../web/detector.js');
const SIZE=416,CLASSES=80,ROW=5+CLASSES,ANCHORS=52*52+26*26+13*13;
// Builds a raw YOLOX output with the given anchors set; every other anchor scores zero.
function output(cells=[]) {
  const data=new Float32Array(ANCHORS*ROW).fill(0);
  for(let i=0;i<ANCHORS;i++)data[i*ROW+4]=-20,data[i*ROW+2]=0,data[i*ROW+3]=0;
  for(const {index,dx=0,dy=0,w=2,h=2,obj=1,cls=32,score=1} of cells){
    const row=index*ROW;data[row]=dx;data[row+1]=dy;data[row+2]=Math.log(w);data[row+3]=Math.log(h);data[row+4]=obj;data[row+5+cls]=score;
  }
  return data;
}
test('crop is square, centred on the ball and kept inside the frame',()=>{
  const frame={width:1280,height:720};
  assert.deepEqual(detector.cropRect({x:640,y:360},{gate:150,diameter:32},frame),{x:490,y:210,side:300});
  assert.deepEqual(detector.cropRect({x:10,y:10},{gate:150,diameter:32},frame),{x:0,y:0,side:300});
  assert.deepEqual(detector.cropRect({x:1275,y:715},{gate:150,diameter:32},frame),{x:980,y:420,side:300});
});
test('crop gives a small ball context and never exceeds the frame',()=>{
  const frame={width:1280,height:720};
  assert.equal(detector.cropRect({x:640,y:360},{gate:10,diameter:32},frame).side,256,'at least eight ball diameters');
  assert.equal(detector.cropRect({x:640,y:360},{gate:10,diameter:4},frame).side,128,'never below the minimum');
  assert.equal(detector.cropRect({x:640,y:360},{gate:5000,diameter:32},frame).side,720,'bounded by the shorter frame side');
});
test('tensor is channel-first BGR in 0-255',()=>{
  const rgba=new Uint8ClampedArray([10,20,30,255, 40,50,60,255, 70,80,90,255, 100,110,120,255]);
  const tensor=detector.toTensor(rgba,2);
  assert.deepEqual(Array.from(tensor),[30,60,90,120, 20,50,80,110, 10,40,70,100]);
});
test('decode applies grid offsets and strides and keeps only confident balls',()=>{
  // Stride-8 grid is 52 x 52; cell (col 3,row 5) has index 5*52+3.
  const raw=output([{index:5*52+3,dx:.5,dy:.25,w:4,h:6,obj:.9,score:.8}]);
  const found=detector.decode(raw,SIZE,.2);
  assert.equal(found.length,1);
  assert.ok(Math.abs(found[0].x-(3.5*8))<1e-3 && Math.abs(found[0].y-(5.25*8))<1e-3);
  assert.ok(Math.abs(found[0].w-32)<1e-3 && Math.abs(found[0].h-48)<1e-3);
  assert.ok(Math.abs(found[0].score-.72)<1e-6);
});
test('decode uses the right stride for coarser grids and ignores other classes and weak scores',()=>{
  const coarse=52*52+26*26+2*13+4;// stride-32 grid, row 2, col 4
  const found=detector.decode(output([{index:coarse,w:1,h:1,obj:1,score:.9},{index:10,cls:0,score:1},{index:20,obj:.3,score:.3}]),SIZE,.2);
  assert.equal(found.length,1);
  assert.equal(found[0].x,4*32);
  assert.equal(found[0].y,2*32);
});
test('non-maximum suppression keeps the strongest of overlapping boxes only',()=>{
  const boxes=[{x:50,y:50,w:20,h:20,score:.5},{x:52,y:51,w:20,h:20,score:.9},{x:200,y:200,w:20,h:20,score:.4}];
  const kept=detector.nms(boxes,.45);
  assert.deepEqual(kept.map(b=>b.score),[.9,.4]);
  assert.equal(boxes[0].score,.5,'input is not reordered');
});
test('detections map back from model pixels to native frame pixels',()=>{
  const mapped=detector.toFrame({x:208,y:104,w:52,h:26,score:.7},{x:100,y:200,side:832},SIZE);
  assert.deepEqual(mapped,{x:100+416,y:200+208,w:104,h:52,score:.7});
});
test('near crops around the anchor in native pixels and returns confident candidates in canvas pixels',async()=>{
  const calls=[],fake={async detect(source,rect){calls.push({source,rect});return [{x:640,y:380,w:64,h:64,score:.9},{x:700,y:390,w:20,h:20,score:.1}];}};
  const video={width:1280,height:720},canvas={width:320,height:180};
  const found=await detector.near(fake,'frame',video,canvas,{x:160,y:90},{radius:8,gate:64});
  assert.equal(calls[0].source,'frame');
  assert.deepEqual(calls[0].rect,{x:384,y:104,side:512},'gate of 64 canvas px is 256 native px each way');
  assert.deepEqual(found,[{x:160,y:95,w:16,h:16,score:.9}],'weak detections are dropped and coordinates return to canvas space');
});
test('near clamps candidate centres of partly visible balls into the canvas',async()=>{
  const fake={async detect(){return [{x:-6,y:728,w:64,h:64,score:.9}];}};
  const [found]=await detector.near(fake,'frame',{width:1280,height:720},{width:320,height:180},{x:2,y:178},{radius:8,gate:64});
  assert.equal(found.x,0);
  assert.equal(found.y,180);
});
test('decode refuses output that does not match the model input size',()=>{
  assert.throws(()=>detector.decode(new Float32Array(ROW*10),SIZE),/does not match/);
});
test('a box whose centre lies inside a stronger box is the same ball and is suppressed',()=>{
  const kept=detector.nms([{x:100,y:100,w:60,h:60,score:.9},{x:104,y:98,w:20,h:20,score:.6},{x:190,y:100,w:60,h:60,score:.5}],.45);
  assert.deepEqual(kept.map(box=>box.score),[.9,.5],'an adjacent, separate ball survives');
});

test('small ball detail crops magnify native pixels and fall back when the tight crop is empty',async()=>{
  const rects=[],fake={async detect(_,rect){rects.push(rect);return rect.side<=160?[]:[{x:640,y:360,w:20,h:20,score:.8}];}};
  const result=await detector.near(fake,'frame',{width:1280,height:720},{width:320,height:180},{x:160,y:90},{radius:2.5,gate:64,detail:true});
  assert.deepEqual(rects.map(r=>r.side),[160,512]);assert.equal(result[0].w,5);
});

test('a rejected tight-crop distractor does not hide the moving ball in the wider crop',async()=>{
  const rects=[],fake={async detect(_,rect){rects.push(rect);return [{x:rect.side<=160?640:800,y:360,w:20,h:20,score:.9}];}};
  const found=await detector.near(fake,'frame',{width:1280,height:720},{width:320,height:180},{x:160,y:90},{radius:2.5,gate:64,detail:true,accept:boxes=>boxes.some(b=>b.x===200)});
  assert.equal(rects.length,2);assert.equal(found[0].x,200);
});
