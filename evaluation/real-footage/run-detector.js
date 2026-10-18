'use strict';
// Drives the real app (local ball detector, default radius box) over the same three 0-3 s windows and seed clicks as run.js.
// Needs `npm install playwright-core` and an Edge/Chrome build that decodes H.264.
// Usage: node run-detector.js [port]   (app started with: python app.py --port 8768 --data-dir <prepared workspace>)
const {chromium}=require('playwright-core');
const fs=require('fs'),path=require('path');
const port=process.argv[2]||'8768';
const seeds={daylight:{x:.7625,y:.58348},indoor:{x:.428125,y:.822222},strobe:{x:.428125,y:.360947}};
(async()=>{
  const browser=await chromium.launch({channel:process.env.BROWSER_CHANNEL||'msedge',headless:true});
  const page=await browser.newPage({viewport:{width:1440,height:1100}});
  const pageErrors=[];page.on('pageerror',error=>pageErrors.push(error.message));
  await page.goto(`http://127.0.0.1:${port}`);
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  const clips=[];
  for(const [id,seed] of Object.entries(seeds)){
    await page.getByRole('combobox',{name:'Saved video'}).selectOption({label:id+'.mp4'});
    await page.waitForFunction(()=>Number.isFinite(document.querySelector('#lab-video').duration)&&document.querySelector('#lab-video').readyState>=2);
    await page.locator('#lab-video').evaluate(v=>{v.pause();v.currentTime=0;});
    await page.waitForFunction(()=>!document.querySelector('#lab-video').seeking&&document.querySelector('#lab-video').currentTime<.01);
    await page.getByRole('spinbutton',{name:'Window start (seconds)'}).fill('0');
    await page.getByRole('spinbutton',{name:'Window end (seconds)'}).fill('3');
    await page.getByRole('spinbutton',{name:'Ball centre x',exact:true}).fill(String(seed.x));
    await page.getByRole('spinbutton',{name:'Ball centre y',exact:true}).fill(String(seed.y));
    await page.getByRole('spinbutton',{name:'Ball radius (tracking pixels)'}).fill('8'); // the UI default; the detector fits the real radius
    await page.getByRole('button',{name:'Select ball',exact:true}).click();
    await page.waitForFunction(()=>document.querySelector('#lab-error').textContent||/Ball found|Colour patch/.test(document.querySelector('#lab-status').textContent),{},{timeout:120000});
    const selection={status:await page.locator('#lab-status').innerText(),error:await page.locator('#lab-error').innerText()};
    if(selection.error){clips.push({id,selection,analysis:null});continue;}
    const before=await page.evaluate(async()=>(await(await fetch('/api/state')).json()).analyses.length);
    const began=Date.now();
    await page.getByRole('button',{name:'Track selected ball'}).click();
    await page.waitForFunction(async n=>(await(await fetch('/api/state')).json()).analyses.length>n,before,{timeout:300000});
    await page.getByRole('button',{name:'Cancel analysis'}).waitFor({state:'hidden'});
    const state=await page.evaluate(async()=>await(await fetch('/api/state')).json());
    clips.push({id,selection,elapsed_ms:Date.now()-began,analysis:state.analyses.at(-1),attempts:state.attempts.length});
  }
  await browser.close();
  fs.writeFileSync(path.join(__dirname,'detector-runs.json'),JSON.stringify({page_errors:pageErrors,clips},null,1));
  console.log(clips.map(c=>`${c.id}: ${c.analysis?`${c.analysis.report.status} coverage ${c.analysis.report.coverage}`:'refused'}`).join('\n'),'\npage errors:',pageErrors.length);
})().catch(error=>{console.error(error);process.exit(1);});
