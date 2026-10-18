'use strict';
// Real installed ONNX model and real app. Reports refusals, skips lost directions, never auto-reseeds or creates assessments.
const {chromium}=require('playwright'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const root=path.resolve(__dirname,'../..'),port=Number(process.argv[2]||8784),label=process.argv[3]||'detector';
const reference=JSON.parse(fs.readFileSync(path.join(__dirname,'reference.json'),'utf8'));
const out=path.join(__dirname,`runs-${label}.json`),data=path.join(root,'test-results','validation-2026-10-14');
async function main(){
  const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'msedge',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}}),errors=[],clips=[];let current='setup';
  page.on('pageerror',e=>errors.push({clip:current,error:e.message}));
  const save=()=>fs.writeFileSync(out,JSON.stringify({label,loss_policy:reference.loss_policy,page_errors:errors,clips},null,2));
  try{
    await page.goto(`http://127.0.0.1:${port}`);await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
    if(label==='colour')await page.evaluate(()=>BallDetector.load=async()=>{throw new Error('Detector disabled only in this evaluation browser to test colour fallback.');});
    for(const clip of reference.clips.filter(c=>process.env.ONLY?process.env.ONLY.split(',').includes(c.id):!c.followup)){
      current=clip.id;const item={id:clip.id,kind:clip.kind,window:clip.window,loss_prompts:[]};console.log('START',clip.id);
      try{
        await page.locator('#lab-media').selectOption({label:clip.file});
        await page.waitForFunction(()=>Number.isFinite(document.querySelector('#lab-video').duration) && document.querySelector('#lab-video').readyState>=2,{}, {timeout:30000});
        const [start,end]=clip.window;await page.locator('#lab-start').fill(String(start));await page.locator('#lab-end').fill(String(end));
        await page.locator('#lab-video').evaluate((v,t)=>{v.pause();v.currentTime=t;},clip.seed_time);
        await page.waitForFunction(t=>!document.querySelector('#lab-video').seeking && Math.abs(document.querySelector('#lab-video').currentTime-t)<.01,clip.seed_time);
        for(const [id,value] of [['lab-x',clip.click_normalized[0]],['lab-y',clip.click_normalized[1]],['lab-radius',clip.radius]])await page.locator('#'+id).fill(String(value));
        await page.locator('#lab-select').click();
        await page.waitForFunction(()=>document.querySelector('#lab-error').textContent || /Ball found|Colour patch/.test(document.querySelector('#lab-status').textContent),{}, {timeout:90000});
        item.selection={status:await page.locator('#lab-status').textContent(),error:await page.locator('#lab-error').textContent()};
        if(!item.selection.error){
          const before=await page.evaluate(async()=>(await(await fetch('/api/state')).json()).analyses.length),began=Date.now();
          await page.locator('#lab-track').click();
          for(;;){
            await page.waitForFunction(()=>!document.querySelector('#lab-cancel').hidden && !document.querySelector('#lab-skip').hidden || document.querySelector('#lab-cancel').hidden || document.querySelector('#lab-error').textContent,{}, {timeout:300000});
            if(!await page.locator('#lab-skip').isHidden()){
              item.loss_prompts.push({status:await page.locator('#lab-status').textContent(),time:await page.locator('#lab-video').evaluate(v=>v.currentTime)});
              await page.locator('#lab-skip').click();
              await page.waitForFunction(()=>document.querySelector('#lab-skip').hidden);
              continue;
            }
            break;
          }
          await page.locator('#lab-cancel').waitFor({state:'hidden',timeout:300000});
          item.elapsed_ms=Date.now()-began;item.error=await page.locator('#lab-error').textContent();
          const state=await page.evaluate(async()=>(await(await fetch('/api/state')).json()));
          item.analysis=state.analyses.length>before?state.analyses.at(-1):null;item.attempts=state.attempts.length;
          if(item.analysis)fs.writeFileSync(path.join(data,clip.id+'-'+label+'-analysis.json'),JSON.stringify(item.analysis,null,2));
        }
        await page.screenshot({path:path.join(data,clip.id+'-'+label+'-app.png'),fullPage:true});
      }catch(error){item.error=error.message;await page.locator('#lab-cancel').click({timeout:1000}).catch(()=>{});}
      clips.push(item);save();console.log('DONE',clip.id,item.analysis?`${item.analysis.report.status} ${item.analysis.report.coverage*100}% ${item.elapsed_ms}ms`:'REFUSED/ERROR '+(item.selection?.error||item.error));
    }
    const files=['web/tracker.js','web/detector.js','web/video-lab.js','football/video.py'];
    fs.writeFileSync(path.join(__dirname,'code-version.json'),JSON.stringify(Object.fromEntries(files.map(file=>[file,crypto.createHash('sha256').update(fs.readFileSync(path.join(root,file))).digest('hex')])),null,2));
  }finally{save();await browser.close();}
}
main().catch(e=>{console.error(e);process.exitCode=1;});
