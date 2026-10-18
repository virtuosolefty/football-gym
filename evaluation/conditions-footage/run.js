'use strict';
// Drives the real app over the clips in reference.json (window, click and radius hint come from that file).
// Usage: node run.js <port> <label>   -> writes runs-<label>.json. Needs playwright-core and an Edge/Chrome that decodes H.264/VP9.
const {chromium}=require('playwright-core');
const fs=require('fs'),path=require('path');
const [port,label]=[process.argv[2]||'8780',process.argv[3]||'detector'];
const reference=JSON.parse(fs.readFileSync(path.join(__dirname,'reference.json'),'utf8'));
(async()=>{
  const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'msedge',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  let current='setup';const pageErrors=[];page.on('pageerror',error=>pageErrors.push({clip:current,message:error.message,stack:String(error.stack||'').slice(0,400)}));
  await page.goto(`http://127.0.0.1:${port}`);
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  const clips=[];
  for(const clip of reference.clips.filter(c=>!process.env.ONLY||process.env.ONLY.split(',').includes(c.id))){
    current=clip.id;console.log('clip',clip.id,new Date().toISOString().slice(11,19));const [start,end]=clip.window,[x,y]=clip.click_normalized;
    await page.getByRole('combobox',{name:'Saved video'}).selectOption({label:clip.file});
    await page.waitForFunction(()=>Number.isFinite(document.querySelector('#lab-video').duration)&&document.querySelector('#lab-video').readyState>=2,{},{timeout:60000});
    await page.getByRole('spinbutton',{name:'Window start (seconds)'}).fill(String(start));
    await page.getByRole('spinbutton',{name:'Window end (seconds)'}).fill(String(end));
    await page.locator('#lab-video').evaluate((v,t)=>{v.pause();v.currentTime=t;},start);
    await page.waitForFunction(t=>!document.querySelector('#lab-video').seeking&&Math.abs(document.querySelector('#lab-video').currentTime-t)<.05,start);
    await page.getByRole('spinbutton',{name:'Ball centre x',exact:true}).fill(String(x));
    await page.getByRole('spinbutton',{name:'Ball centre y',exact:true}).fill(String(y));
    await page.getByRole('spinbutton',{name:'Ball radius (tracking pixels)'}).fill(String(clip.radius_hint_canvas_px));
    await page.getByRole('button',{name:'Select ball',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#lab-error').textContent||/Ball found|Colour patch/.test(document.querySelector('#lab-status').textContent),{},{timeout:120000});
    const selection={status:await page.locator('#lab-status').innerText(),error:await page.locator('#lab-error').innerText()};
    if(selection.error){clips.push({id:clip.id,selection,analysis:null});continue;}
    const before=await page.evaluate(async()=>(await(await fetch('/api/state')).json()).analyses.length);
    const began=Date.now();
    await page.getByRole('button',{name:'Track selected ball'}).click();
    await page.waitForFunction(async n=>(await(await fetch('/api/state')).json()).analyses.length>n,before,{timeout:300000});
    await page.getByRole('button',{name:'Cancel analysis'}).waitFor({state:'hidden',timeout:180000});
    const state=await page.evaluate(async()=>await(await fetch('/api/state')).json());
    clips.push({id:clip.id,selection,elapsed_ms:Date.now()-began,analysis:state.analyses.at(-1),attempts:state.attempts.length});
  }
  await browser.close();
  fs.writeFileSync(path.join(__dirname,`runs-${label}.json`),JSON.stringify({label,page_errors:pageErrors,clips},null,1));
  for(const c of clips)console.log(c.id.padEnd(11),c.analysis?`${c.analysis.report.status} coverage ${c.analysis.report.coverage} via ${c.analysis.configuration.method}`:'REFUSED: '+c.selection.error.slice(0,90));
  console.log('page errors:',pageErrors.length);
})().catch(error=>{console.error(error);process.exit(1);});
