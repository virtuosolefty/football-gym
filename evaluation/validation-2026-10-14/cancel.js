'use strict';
const {chromium}=require('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const here=__dirname, data=path.resolve(here,'../../test-results/validation-2026-10-14');
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true});
  const page=await browser.newPage(), errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  try{
    await page.goto('http://127.0.0.1:8784');
    await page.waitForFunction(()=>typeof state!=='undefined' && state?.profile);
    await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
    const clip=JSON.parse(fs.readFileSync(path.join(here,'reference.json'),'utf8')).clips.find(c=>c.id==='benchmark-volley-loop-30s');
    await page.locator('#lab-media').selectOption({label:clip.file});
    await page.waitForFunction(()=>document.querySelector('#lab-video').readyState>=2);
    await page.locator('#lab-start').fill('0');await page.locator('#lab-end').fill('30');
    await page.locator('#lab-video').evaluate(v=>{v.pause();v.currentTime=0;});
    await page.waitForFunction(()=>!document.querySelector('#lab-video').seeking);
    for(const [id,value] of [['lab-x',clip.click_normalized[0]],['lab-y',clip.click_normalized[1]],['lab-radius',clip.radius]])await page.locator('#'+id).fill(String(value));
    await page.locator('#lab-select').click();
    await page.waitForFunction(()=>/Ball found/.test(document.querySelector('#lab-status').textContent),{}, {timeout:90000});
    const counts=()=>page.evaluate(async()=>{const s=await(await fetch('/api/state')).json();return {analyses:s.analyses.length,attempts:s.attempts.length};});
    const before=await counts(),progress=[];
    await page.locator('#lab-track').click();
    for(const minimum of [5,12]){
      await page.waitForFunction(n=>{const m=document.querySelector('#lab-status').textContent.match(/(\d+)\/300 samples/);return m&&Number(m[1])>=n;},minimum,{timeout:60000});
      progress.push(await page.locator('#lab-status').textContent());
    }
    await page.screenshot({path:path.join(data,'cancel-progress.png'),fullPage:true});
    const began=Date.now();await page.locator('#lab-cancel').click();
    await page.locator('#lab-cancel').waitFor({state:'hidden',timeout:10000});
    const cancellation_ms=Date.now()-began,error=await page.locator('#lab-error').textContent();
    assert.equal(error,'Analysis cancelled.');assert.deepEqual(await counts(),before);
    assert.equal(await page.locator('#lab-media').isEnabled(),true);
    assert.equal(await page.locator('#lab-select').isEnabled(),true);
    assert.equal(await page.locator('#lab-video').evaluate(v=>v.controls),true);
    assert.deepEqual(errors,[]);
    const result={status:'PASS',model:'actual installed YOLOX nano',progress,cancellation_ms,error,before,after:await counts(),page_errors:errors};
    fs.writeFileSync(path.join(here,'cancel-results.json'),JSON.stringify(result,null,2));console.log(result);
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
