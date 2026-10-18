// Playwright callback. Runs the existing UI/production tracker without modifying it.
async (page) => {
  await page.goto('http://127.0.0.1:8767');
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  const seeds=[{id:'daylight',x:.7625,y:.58348,radius:37},{id:'indoor',x:.428125,y:.822222,radius:8},{id:'strobe',x:.428125,y:.360947,radius:11}];
  const results=[];
  for(const seed of seeds) {
    await page.getByRole('combobox',{name:'Saved video'}).selectOption({label:seed.id+'.mp4'});
    await page.waitForFunction(()=>Number.isFinite(document.querySelector('#lab-video').duration)&&document.querySelector('#lab-video').readyState>=2);
    await page.locator('#lab-video').evaluate(v=>{v.pause();v.currentTime=0;});
    await page.waitForFunction(()=>!document.querySelector('#lab-video').seeking&&document.querySelector('#lab-video').currentTime<.01);
    await page.getByRole('spinbutton',{name:'Window start (seconds)'}).fill('0');
    await page.getByRole('spinbutton',{name:'Window end (seconds)'}).fill('3');
    await page.getByRole('spinbutton',{name:'Ball centre x',exact:true}).fill(String(seed.x));
    await page.getByRole('spinbutton',{name:'Ball centre y',exact:true}).fill(String(seed.y));
    await page.getByRole('spinbutton',{name:'Ball radius (tracking pixels)'}).fill(String(seed.radius));
    await page.getByRole('button',{name:'Select ball',exact:true}).click();
    const before=await page.evaluate(async()=>{const s=await(await fetch('/api/state')).json();return s.analyses.length;});
    const began=Date.now();
    await page.getByRole('button',{name:'Track selected ball'}).click();
    await page.waitForFunction(async n=>{const s=await(await fetch('/api/state')).json();return s.analyses.length>n;},before,{timeout:45000});
    await page.getByRole('button',{name:'Cancel analysis'}).waitFor({state:'hidden'});
    const current=await page.evaluate(async()=>{const s=await(await fetch('/api/state')).json();return {analysis:s.analyses.at(-1),attempts:s.attempts.length};});
    const error=await page.locator('#lab-error').innerText();
    if(error)throw new Error(seed.id+': '+error);
    await page.screenshot({path:'D:/football helper/test-results/real-footage/'+seed.id+'-app.png',fullPage:true});
    results.push({id:seed.id,elapsed_ms:Date.now()-began,...current});
  }
  return results;
}
