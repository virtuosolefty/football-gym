// Optional local diagnostic replay; needs October 14 footage and TEST_DETECTOR=1. Never run against player data.
async (page) => {
  const errors=[],results=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(BASE_URL);
  await page.getByRole('textbox',{name:'Name',exact:true}).fill('Regression replay QA');
  await page.getByRole('combobox',{name:'Development goal'}).selectOption('juggling');
  await page.getByRole('checkbox',{name:'I agree to store and process'}).check();
  await page.getByRole('button',{name:'Save my profile'}).click();await page.locator('dialog').waitFor({state:'hidden'});
  const clips=[
    {id:'rain-context',file:'rain.mp4',start:4,end:7,time:4,x:.593,y:.537,radius:2},
    {id:'bottle',file:'u17.webm',directory:'conditions-footage',start:34,end:37,time:34,x:.5391,y:.6222,radius:3},
    {id:'cone',file:'tennis.webm',directory:'other-footage',start:5,end:8,time:5,x:.6583,y:.3241,radius:6},
    {id:'floor-ball',file:'tennis-dark.mp4',start:1,end:5,time:2,x:.6639,y:.5586,radius:8},
    {id:'studio-pose',file:'studio-juggle.mp4',start:0,end:5,time:0,x:.385,y:.616,radius:10,pose:true}
  ];
  for(const clip of clips){
    await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Record',exact:false}).click();
    await page.locator('#evidence-file').setInputFiles('test-results/'+(clip.directory||'validation-2026-10-14')+'/footage/'+clip.file);
    await page.evaluate(async()=>{const file=document.querySelector('#evidence-file').files[0];const r=await fetch('/api/upload',{method:'POST',headers:{'Content-Type':file.type,'X-Filename':encodeURIComponent(file.name),'X-Football-Request':'1'},body:file});if(!r.ok)throw new Error(await r.text());});
    await page.reload();await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
    await page.locator('#lab-media').selectOption({label:clip.file});await page.waitForFunction(()=>Number.isFinite(document.querySelector('#lab-video').duration) && document.querySelector('#lab-video').readyState>=2);
    await page.locator('#lab-start').fill(String(clip.start));await page.locator('#lab-end').fill(String(clip.end));
    await page.locator('#lab-video').evaluate((v,t)=>{v.pause();v.currentTime=t;},clip.time);
    await page.waitForFunction(t=>!document.querySelector('#lab-video').seeking && Math.abs(document.querySelector('#lab-video').currentTime-t)<.01,clip.time);
    for(const [field,value] of [['x',clip.x],['y',clip.y],['radius',clip.radius]])await page.locator('#lab-'+field).fill(String(value));
    if(clip.pose)await page.locator('#lab-pose').check();
    await page.locator('#lab-select').click();await page.getByText('Ball found by the local detector',{exact:false}).waitFor({timeout:90000});
    const began=Date.now(),losses=[];await page.locator('#lab-track').click();
    while(true){
      await page.waitForFunction(()=>!document.querySelector('#lab-skip').hidden || document.querySelector('#lab-cancel').hidden,{},{timeout:180000});
      if(await page.locator('#lab-cancel').isHidden())break;
      losses.push(await page.locator('#lab-status').textContent());await page.locator('#lab-skip').click();await page.locator('#lab-skip').waitFor({state:'hidden'});
    }
    const error=await page.locator('#lab-error').textContent();if(error)throw new Error(clip.id+': '+error);
    const run=await page.evaluate(async()=>(await(await fetch('/api/state')).json()).analyses.at(-1));
    const wrongWindow={bottle:36.3,cone:5.8,'floor-ball':3.4}[clip.id];
    if(wrongWindow!==undefined && run.samples.some(s=>s.found && s.time>=wrongWindow))throw new Error(clip.id+' emitted points in the known decoy window.');
    if(!['SUSPECT','UNMEASURABLE'].includes(run.report.status) || run.report.quality.validated)throw new Error('Uncalibrated replay was treated as validated.');
    if(clip.pose && !run.samples.some(s=>s.pose?.left?.length===3))throw new Error('The installed pose model returned no foot evidence on the studio replay.');
    const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#lab-export').click()]);await download.saveAs((RESULTS_DIR||'test-results/priorities-2026-10-18')+'/'+clip.id+'.json');
    const item={id:clip.id,coverage:run.report.coverage,status:run.report.status,found:run.samples.filter(s=>s.found).length,losses,poseFrames:run.samples.filter(s=>s.pose?.status==='single').length,elapsed_ms:Date.now()-began};
    results.push(item);console.log('REPLAY',JSON.stringify(item));
  }
  if(errors.length)throw new Error(errors.join('; '));
  return {result:'PASS',diagnosticOnly:true,clips:results,browserErrors:errors};
}
