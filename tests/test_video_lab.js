'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
global.BallTracker=require('../web/tracker.js');
const lab=require('../web/video-lab.js');
class Video extends EventTarget {
  constructor(){super();this.readyState=2;this.seeking=false;this.position=0;}
  get currentTime(){return this.position;}
  set currentTime(value){this.position=value;queueMicrotask(()=>this.dispatchEvent(new Event('seeked')));}
}
const canvas={width:320,height:180},seed={x:.5,y:.5,time:0,radius:5};
const point=(x=160,y=90)=>({x,y,score:.8});
const locator=(v,missing=[])=>async state=>BallTracker.advance(state,missing.includes(Number(v.currentTime.toFixed(1)))?[]:[point()],5,320,180);
test('loss pauses before a look-alike can be accepted, and skip fills the remaining window with misses',async()=>{
  const v=new Video(),signal=new AbortController().signal;let confirmations=0,calls=0;
  const locate=async state=>{calls++;return locator(v,[.1,.2,.3])(state);};
  const result=await lab.trackWindow(v,canvas,signal,{seed,locate,start:0,end:1},()=>{},async info=>{confirmations++;assert.equal(info.time,.2);assert.equal(info.reason,'gap');return null;});
  assert.equal(confirmations,1);assert.equal(calls,3);assert.equal(result.samples.length,10);assert.equal(result.samples.filter(s=>s.found).length,1);assert.equal(result.samples[2].lost_reason,'gap');
});
test('reconfirmation can scrub ahead and starts a separate segment without backfilling the gap',async()=>{
  const v=new Video(),locate=locator(v,[.1,.2,.3]);
  const result=await lab.trackWindow(v,canvas,new AbortController().signal,{seed,locate,start:0,end:1},()=>{},async()=>({seed:{x:.5,y:.5,time:.55,radius:5},locate:locator(v)}));
  assert.equal(result.reseeds.length,1);assert.equal(result.reseeds[0].time,.55);assert.equal(result.samples.find(s=>s.time===.5).found,false);assert.equal(result.samples.find(s=>s.time===.55).segment,1);assert.equal(result.samples.at(-1).found,true);
  assert.equal(new Set(result.samples.map(s=>s.time)).size,result.samples.length);
});
test('backward tracking starts from the anchor and handles a backward reseed in chronological output',async()=>{
  const v=new Video(),middle={...seed,time:.5},locate=locator(v,[.4,.3,.2]);
  const result=await lab.trackWindow(v,canvas,new AbortController().signal,{seed:middle,locate,start:0,end:1},()=>{},async info=>{assert.equal(info.direction,-1);return {seed:{x:.5,y:.5,time:.1,radius:5},locate:locator(v)};});
  assert.ok(result.samples.every((s,i)=>i===0 || result.samples[i-1].time<s.time));assert.equal(result.samples[0].segment,1);assert.equal(result.samples.at(-1).segment,0);
});
test('cancel during inference discards the result and never requests re-confirmation',async()=>{
  const v=new Video(),controller=new AbortController();let asked=false;
  await assert.rejects(lab.trackWindow(v,canvas,controller.signal,{seed,start:0,end:1,locate:async state=>{controller.abort();return {point:point(),state};}},()=>{},async()=>{asked=true;}),/cancelled/);
  assert.equal(asked,false);
});
test('cancel during a decode wait removes event handlers and rejects promptly',async()=>{
  const v=new EventTarget();v.readyState=0;v.currentTime=0;const controller=new AbortController(),pending=lab.seek(v,1,controller.signal);controller.abort();await assert.rejects(pending,/cancelled/);
});
test('a seek landing outside the requested timestamp is rejected with re-encoding guidance',async()=>{
  class WrongClock extends Video {
    get currentTime(){return this.position;}
    set currentTime(value){this.position=12;queueMicrotask(()=>this.dispatchEvent(new Event('seeked')));}
  }
  await assert.rejects(lab.seek(new WrongClock(),1),/irregular timestamps/);
});

test('a synchronous seek failure is also actionable and cleans up its wait',async()=>{
  class BrokenSeek extends Video {
    get currentTime(){return 0;}
    set currentTime(value){throw new Error('Decoder rejected timestamp');}
  }
  await assert.rejects(lab.seek(new BrokenSeek(),1),/irregular timestamps/);
});
test('saved legacy coverage-only reports are displayed as suspect without rewriting them',()=>{
  const old={samples:[{time:0,found:true}],candidates:[],report:{status:'REVIEW_REQUIRED',coverage:1,reasons:[]}};
  assert.match(lab.reportText(old),/Tracker SUSPECT/);assert.equal(old.report.status,'REVIEW_REQUIRED');
});

test('playback errors distinguish codec, network and interrupted loading',()=>{
  assert.equal(lab.playbackError({error:null}),'');
  for(const code of [3,4])assert.match(lab.playbackError({error:{code}}),/H\.264/);
  assert.match(lab.playbackError({error:{code:2}}),/local server/);
  assert.match(lab.playbackError({error:{code:1}}),/interrupted/);
});

test('a permanently failed decoder rejects immediately with specific guidance',async()=>{
  const v=new Video();v.error={code:4};
  await assert.rejects(lab.seek(v,1),/Changing the filename/);
});


test('review moments group contiguous misses, retain re-seeds and leave original evidence unchanged',()=>{
  const analysis={samples:[{time:0,found:true},{time:.1,found:false},{time:.2,found:false},{time:.3,found:true},{time:.4,found:false},{time:1,found:false}],configuration:{reseeds:[{time:.3}]}},before=JSON.stringify(analysis);
  const moments=lab.reviewMoments(analysis,[{time:.05,kind:'contact',uncertain:true},{time:.9,kind:'drop'}]);
  assert.deepEqual(moments.filter(m=>m.kind==='gap').map(m=>[m.time,m.end]),[[.1,.2],[.4,.4],[1,1]]);
  assert.equal(lab.nextIssue(moments,.2),.3);assert.equal(lab.nextIssue(moments,1),.05);
  assert.equal(lab.nextIssue(lab.reviewMoments({samples:[]},[{time:1,kind:'contact'}]),0),undefined);
  assert.equal(JSON.stringify(analysis),before);assert.deepEqual(lab.reviewMoments(null),[]);
});


test('a stale seeked event during a newer decode does not report a corrupt clip',async()=>{
  const v=new Video();
  Object.defineProperty(v,'currentTime',{get(){return this.position;},set(value){
    this.position=value;this.seeking=true;this.readyState=1;
    queueMicrotask(()=>{this.dispatchEvent(new Event('seeked'));setTimeout(()=>{this.seeking=false;this.readyState=2;this.dispatchEvent(new Event('seeked'));},5);});
  }});
  await lab.seek(v,.3);assert.equal(v.currentTime,.3);assert.equal(v.seeking,false);assert.equal(v.readyState,2);
});
