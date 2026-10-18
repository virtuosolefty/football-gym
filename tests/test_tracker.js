'use strict';
const test=require('node:test'),assert=require('node:assert/strict'),tracker=require('../web/tracker.js');
function image(balls=[]) {
  const width=120,height=80,data=new Uint8ClampedArray(width*height*4);
  for(let i=0;i<width*height;i++)data.set([20,60,40,255],i*4);
  for(const {x,y,r=5} of balls)for(let py=0;py<height;py++)for(let px=0;px<width;px++)if((px-x)**2+(py-y)**2<=r*r)data.set([230,200,30,255],(py*width+px)*4);
  return {width,height,data};
}
test('seed and tracking follow a visible ball through movement',()=>{
  const colour=tracker.seed(image([{x:30,y:40}]),30,40,5);
  assert.deepEqual(colour,[230,200,30]);
  let previous=null;
  for(const x of [30,35,40,45]){const point=tracker.locate(image([{x,y:40}]),colour,5,previous);assert.ok(point);assert.equal(point.x,x);assert.equal(point.y,40);previous=point;}
});
test('no detection is returned for missing or ambiguous ball patches',()=>{
  assert.equal(tracker.locate(image(),[230,200,30],5),null);
  assert.equal(tracker.locate(image([{x:30,y:40},{x:60,y:40}]),[230,200,30],5),null);
});
test('oversized background and abrupt jumps are rejected',()=>{
  assert.equal(tracker.locate(image([{x:30,y:40,r:20}]),[230,200,30],5),null);
  assert.equal(tracker.locate(image([{x:100,y:40}]),[230,200,30],5,{x:10,y:40}),null);
});
const colour=[230,200,30];
function run(frames,start,r=5){
  let state=tracker.begin(start);const points=[];
  for(const balls of frames){const result=tracker.step(state,image(balls),colour,r);points.push(result.point);state=result.state;}
  return {points,state};
}
test('tracking starts at the clicked ball, not at another patch of the same colour',()=>{
  const {points}=run([[{x:30,y:40},{x:100,y:20}]],{x:30,y:40});
  assert.equal(points[0].x,30);
  assert.equal(points[0].y,40);
});
test('a seed that does not sit on a ball-shaped patch loses the track immediately',()=>{
  const {points,state}=run([[{x:100,y:20}],[{x:100,y:20}]],{x:30,y:40});
  assert.deepEqual(points,[null,null]);
  assert.equal(state.lost,true);
});
test('a missed frame does not reopen the search to the whole image',()=>{
  const {points}=run([[{x:30,y:40}],[],[{x:105,y:20},{x:34,y:40}]],{x:30,y:40});
  assert.equal(points[1],null);
  assert.equal(points[2].x,34,'the distant look-alike must not beat the ball near the last position');
});
test('the search widens gradually while the ball is missing',()=>{
  const near=run([[{x:30,y:40}],[],[{x:75,y:40}]],{x:30,y:40});
  assert.ok(near.points[2],'a ball that moved 45 px during a single-frame gap is reacquired');
  const far=run([[{x:30,y:40}],[{x:75,y:40}]],{x:30,y:40});
  assert.equal(far.points[1],null,'the same jump without a gap is rejected');
});
test('the track is declared lost after too many consecutive misses and never reacquires',()=>{
  const frames=[[{x:30,y:40}],...Array(8).fill([]),[{x:32,y:40}]];
  const {points,state}=run(frames,{x:30,y:40});
  assert.equal(state.lost,true);
  assert.equal(points.at(-1),null);
});
test('the candidate nearest the last position wins; near-ties are abstentions',()=>{
  const win=run([[{x:30,y:40}],[{x:34,y:40},{x:60,y:40}]],{x:30,y:40});
  assert.equal(win.points[1].x,34);
  const tie=run([[{x:30,y:40}],[{x:20,y:40},{x:40,y:40}]],{x:30,y:40});
  assert.equal(tie.points[1],null);
});
test('step never mutates the state it was given',()=>{
  const start=tracker.begin({x:30,y:40}),frozen=JSON.stringify(start);
  tracker.step(start,image([{x:30,y:40}]),colour,5);
  assert.equal(JSON.stringify(start),frozen);
});
test('verify reports whether the seed sits on a ball-shaped patch',()=>{
  const seedImage=image([{x:30,y:40}]);
  assert.equal(tracker.verify(seedImage,colour,5,{x:30,y:40}),true);
  assert.equal(tracker.verify(seedImage,colour,5,{x:90,y:20}),false);
});
test('advance applies the same association rules to detector candidates and keeps their extra fields',()=>{
  const first=tracker.advance(tracker.begin({x:30,y:40}),[{x:31,y:40,score:.9},{x:100,y:10,score:.95}],5,120);
  assert.equal(first.point.x,31);
  assert.equal(first.point.score,.9,'the strongest far-away candidate must not beat the one at the click');
  const far=tracker.advance(first.state,[{x:100,y:10,score:.99}],5,120);
  assert.equal(far.point,null);
  assert.equal(far.state.misses,1);
  const tie=tracker.advance(first.state,[{x:21,y:40},{x:41,y:40}],5,120);
  assert.equal(tie.point,null);
});
test('advance loses the track when nothing sits at the click on the first frame',()=>{
  const result=tracker.advance(tracker.begin({x:30,y:40}),[{x:90,y:10}],5,120);
  assert.equal(result.point,null);
  assert.equal(result.state.lost,true);
  assert.equal(tracker.advance(result.state,[{x:30,y:40}],5,120).point,null,'a lost track never reacquires');
});
test('the gate grows with consecutive misses so detector crops can match it',()=>{
  assert.equal(tracker.gate(5,120),40);
  assert.equal(tracker.gate(5,120,2),60);
  assert.equal(tracker.gate(5,1000),150);
});
test('invalid seeds fail with actionable feedback',()=>{
  assert.throws(()=>tracker.seed(image(),-1,30,5));
  assert.throws(()=>tracker.seed(image(),30,30,1));
});
test('reach is the seed gate on the first frame and the widening gate afterwards',()=>{
  assert.equal(tracker.reach(tracker.begin({x:1,y:1}),5,120),10);
  const missed=tracker.advance(tracker.advance(tracker.begin({x:30,y:40}),[{x:30,y:40}],5,120).state,[],5,120).state;
  assert.equal(tracker.reach(missed,5,120),50);
});
const ball=(x,y,d,score=.8)=>({x,y,w:d,h:d,score});
test('a candidate far smaller than the established ball is rejected even when it is the nearest',()=>{
  const first=tracker.advance(tracker.begin({x:60,y:40}),[ball(60,40,24)],12,320);
  const cone=tracker.advance(first.state,[ball(70,40,8)],12,320);
  assert.equal(cone.point,null,'a 24 px ball cannot become an 8 px object between samples');
  assert.equal(cone.state.misses,1);
});
test('ball size may change smoothly: each step within a factor of two is accepted and updates the reference size',()=>{
  let state=tracker.advance(tracker.begin({x:60,y:40}),[ball(60,40,12)],6,320).state;
  for(const d of [20,34,54]){const next=tracker.advance(state,[ball(62,40,d)],6,320);assert.ok(next.point,`diameter ${d}`);state=next.state;}
  assert.equal(tracker.advance(state,[ball(64,40,160)],6,320).point,null,'a jump to three times the size is not the same ball');
});
test('the size rule does not apply to candidates that carry no size, such as colour components',()=>{
  const first=tracker.advance(tracker.begin({x:60,y:40}),[ball(60,40,24)],12,320);
  assert.ok(tracker.advance(first.state,[{x:64,y:40}],12,320).point);
});
test('non-finite or zero sizes are ignored and never poison the reference size',()=>{
  for(const bad of [NaN,0,Infinity,-5]){
    const first=tracker.advance(tracker.begin({x:60,y:40}),[ball(60,40,bad)],12,320);
    assert.ok(first.point,`a candidate with size ${bad} can still be the ball at the click`);
    assert.equal(first.state.size,undefined);
    assert.ok(tracker.advance(first.state,[ball(62,40,24)],12,320).point,`a normal candidate is accepted after size ${bad}`);
  }
});
test('the reference size survives misses',()=>{
  let state=tracker.advance(tracker.begin({x:60,y:40}),[ball(60,40,24)],12,320).state;
  state=tracker.advance(state,[],12,320).state;
  state=tracker.advance(state,[],12,320).state;
  assert.equal(state.size,24);
  assert.equal(tracker.advance(state,[ball(62,40,6)],12,320).point,null);
});
test('small steps cannot compound into an unbounded size drift',()=>{
  let state=tracker.advance(tracker.begin({x:60,y:40}),[ball(60,40,10)],5,320).state,diameter=10,accepted=0;
  while(accepted<12){const next=tracker.advance(state,[ball(61,40,diameter*1.9)],5,320);if(!next.point)break;state=next.state;diameter*=1.9;accepted++;}
  assert.ok(diameter<=60.001,`the track must stop following a ball that has grown more than 6x (grew to ${diameter})`);
});

test('an edge exit loses the track on the first miss and never adopts the bottle',()=>{
  for(const [x,y] of [[5,90],[315,90],[160,5],[160,175]]){
    const first=tracker.advance(tracker.begin({x,y}),[ball(x,y,10)],5,320,180);
    const miss=tracker.advance(first.state,[],5,320,180);
    assert.equal(miss.state.lost,true);assert.equal(miss.state.reason,'edge_exit');
    assert.equal(tracker.advance(miss.state,[ball(x+10,y,10,.66)],5,320,180).point,null);
  }
});
test('two misses require a new user seed even when a confident floor ball is nearby',()=>{
  let state=tracker.advance(tracker.begin({x:160,y:90}),[ball(160,90,10)],5,320,180).state;
  for(let i=0;i<2;i++)state=tracker.advance(state,[],5,320,180).state;
  assert.equal(state.lost,true);assert.equal(state.reason,'gap');
  assert.equal(tracker.advance(state,[ball(165,90,10,.99)],5,320,180).point,null);
  assert.ok(tracker.advance(tracker.begin({x:165,y:90}),[ball(165,90,10,.99)],5,320,180).point);
});

test('a widespread scene change alarms even when a similar ball remains at the same position',()=>{
  const before=image([{x:60,y:40}]).data,after=new Uint8ClampedArray(before);
  for(let i=0;i<after.length;i+=4)after[i+2]+=40;
  assert.equal(tracker.sceneChanged(before,after),true);
  assert.equal(tracker.sceneChanged(before,image([{x:70,y:40}]).data),false);
  assert.equal(tracker.sceneChanged(null,after),false);
});
test('motion prediction follows a fast ball instead of returning to the old position',()=>{
  let state=tracker.begin({x:50,y:90});
  for(const x of [50,90,140]){const next=tracker.advance(state,[ball(x,90,10)],5,320,180);assert.ok(next.point);state=next.state;}
  assert.deepEqual(tracker.expected(state),{x:190,y:90});
  const next=tracker.advance(state,[ball(140,90,10),ball(190,90,10)],5,320,180);
  assert.equal(next.point.x,190);
});
