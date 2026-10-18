'use strict';
// shortcut: colour/shape tracking needs a distinct ball patch and fixed camera; use validated ball detection for general footage.
const BallTracker = (() => {
  function seed(image, x, y, radius) {
    if(!Number.isFinite(x) || !Number.isFinite(y) || x<0 || y<0 || x>=image.width || y>=image.height || radius<2 || radius>40) throw new Error('Select a visible ball and a radius between 2 and 40 tracking pixels.');
    const colours=[[],[],[]], inner=Math.max(1,Math.floor(radius/3));
    for(let dy=-inner;dy<=inner;dy++) for(let dx=-inner;dx<=inner;dx++) {
      const px=Math.round(x+dx),py=Math.round(y+dy); if(px<0 || py<0 || px>=image.width || py>=image.height)continue;
      const i=(py*image.width+px)*4; for(let c=0;c<3;c++)colours[c].push(image.data[i+c]);
    }
    return colours.map(channel=>channel.sort((a,b)=>a-b)[Math.floor(channel.length/2)]);
  }
  // Tracking policy. Units are tracking pixels / consecutive sampled frames.
  const MAX_MISSES=2, GATE_GROWTH=.25, SEED_GATE=2, TIE_MARGIN=2, SIZE_RATIO=2, SIZE_DRIFT=6;
  // shortcut: widespread RGB changes are a conservative cut alarm, not identity verification; calibrate on independent clips.
  const SCENE_CHANNEL_DELTA=24, SCENE_CHANGED_FRACTION=.65;
  function sceneChanged(previous, current) {
    if(!previous || previous.length!==current.length)return false;
    let changed=0;
    for(let i=0;i<current.length;i+=4)if(Math.max(...[0,1,2].map(c=>Math.abs(current[i+c]-previous[i+c])))>=SCENE_CHANNEL_DELTA)changed++;
    return changed/(current.length/4)>=SCENE_CHANGED_FRACTION;
  }
  const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
  const gate=(radius,width,misses=0)=>Math.max(radius*8,width*.15)*(1+GATE_GROWTH*misses);
  // Nearest candidate to the anchor wins unless a runner-up is almost as close, which is ambiguity and therefore a gap.
  function choose(candidates, anchor, limit, radius) {
    if(!anchor)return candidates.length===1 ? candidates[0] : null;
    const near=candidates.map(c=>({c,d:distance(c,anchor)})).filter(item=>item.d<=limit).sort((a,b)=>a.d-b.d);
    if(!near.length || (near.length>1 && near[1].d-near[0].d<radius*TIE_MARGIN))return null;
    return near[0].c;
  }
  // The track begins at the clicked ball and may only leave it through short, bounded gaps.
  function begin(point) { return {anchor:{x:point.x,y:point.y},misses:0,lost:false,first:true}; }
  // Prediction follows sampling order, including a backward walk from the seed.
  const expected=state=>({x:state.anchor.x+(state.velocity?.x||0)*(state.misses+1),y:state.anchor.y+(state.velocity?.y||0)*(state.misses+1)});
  // How far from the anchor a candidate may be: the click itself on the first frame, then a gate that widens while the ball is missing.
  const reach=(state, radius, width) => state.first ? radius*SEED_GATE : gate(radius,width,state.misses);
  const sizeOf=candidate => {const size=(candidate.w+candidate.h)/2;return Number.isFinite(size) && size>0 ? size : undefined;};
  // A ball changes size smoothly between samples; a much smaller or larger object is something else (a cone, a head, a different scene).
  // It is also bounded against the first size seen, so a chain of acceptable steps cannot drift onto a much larger object.
  const within=(size, reference, ratio) => size*ratio>=reference && size<=reference*ratio;
  const plausible=(state, candidate) => {const size=sizeOf(candidate);return state.size===undefined || size===undefined || (within(size,state.size,SIZE_RATIO) && within(size,state.base,SIZE_DRIFT));};
  // Candidates may come from any source (colour components, a ball detector); they only need x and y.
  function advance(state, candidates, radius, width, height=Infinity) {
    if(state.lost)return {point:null,state};
    const point=choose(candidates.filter(candidate=>Number.isFinite(candidate.x) && Number.isFinite(candidate.y) && plausible(state,candidate)),state.first?state.anchor:expected(state),reach(state,radius,width),radius);
    if(point)return {point,state:{anchor:{x:point.x,y:point.y},velocity:state.first?null:{x:(point.x-state.anchor.x)/(state.misses+1),y:(point.y-state.anchor.y)/(state.misses+1)},misses:0,lost:false,first:false,size:sizeOf(point) ?? state.size,base:state.base ?? sizeOf(point)}};
    const misses=state.misses+1;
    const margin=Math.max(radius*2,(state.size||0)/2),edge=state.anchor.x<=margin || state.anchor.x>=width-margin || state.anchor.y<=margin || state.anchor.y>=height-margin;
    const lost=state.first || edge || misses>=MAX_MISSES;
    return {point:null,state:{...state,misses,lost,first:false,reason:lost?(state.first?'seed_missing':edge?'edge_exit':'gap'):undefined}};
  }
  const step=(state, image, colour, radius) => state.lost ? {point:null,state} : advance(state,components(image,colour,radius),radius,image.width,image.height);
  function verify(image, colour, radius, point) { return choose(components(image,colour,radius),point,radius*SEED_GATE,radius)!==null; }
  function locate(image, colour, radius, previous=null) {
    return choose(components(image,colour,radius),previous,gate(radius,image.width),radius);
  }
  function components(image, colour, radius) {
    const {width,height,data}=image, mask=new Uint8Array(width*height), queue=new Int32Array(width*height), found=[];
    for(let i=0;i<mask.length;i++) { const p=i*4; mask[i]=((data[p]-colour[0])**2+(data[p+1]-colour[1])**2+(data[p+2]-colour[2])**2)<=45**2 ? 1 : 0; }
    for(let i=0;i<mask.length;i++) {
      if(mask[i]!==1)continue;
      let head=0,tail=1,sx=0,sy=0,minX=width,maxX=0,minY=height,maxY=0;queue[0]=i;mask[i]=2;
      while(head<tail) {
        const p=queue[head++], x=p%width,y=Math.floor(p/width);sx+=x;sy+=y;minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);
        const neighbours=[];if(x>0)neighbours.push(p-1);if(x<width-1)neighbours.push(p+1);if(y>0)neighbours.push(p-width);if(y<height-1)neighbours.push(p+width);
        for(const next of neighbours)if(mask[next]===1){mask[next]=2;queue[tail++]=next;}
      }
      const w=maxX-minX+1,h=maxY-minY+1,area=Math.PI*radius**2,centre={x:sx/tail,y:sy/tail};
      if(tail<area*.25 || tail>area*2.8 || w/h<.5 || w/h>2 || tail/(w*h)<.35)continue;
      found.push({...centre,area:tail});
    }
    return found;
  }
  return {seed,begin,advance,step,verify,locate,gate,reach,expected,MAX_MISSES,sceneChanged,SCENE_CHANNEL_DELTA,SCENE_CHANGED_FRACTION};
})();
if(typeof module!=='undefined')module.exports=BallTracker;
else globalThis.BallTracker=BallTracker;
