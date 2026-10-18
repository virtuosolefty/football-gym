// Exercise the real worker client with CPU-busy workers; no production model required in CI.
async (page) => {
  let mode='load';const errors=[],cancellations=[];page.on('pageerror',e=>errors.push(e.message));
  await page.context().route('**/detector-worker.js',route=>route.fulfill({contentType:'text/javascript',body:`
    let count=0;
    const busy=()=>{const end=Date.now()+15000;while(Date.now()<end){}};
    self.onmessage=({data})=>{
      if(data.type==='load'){if('${mode}'==='load')busy();postMessage({ready:true});}
      else {count++;if('${mode}'==='select' || ('${mode}'==='track' && count>1))busy();postMessage({boxes:[{x:data.rect.x+data.rect.side/2,y:data.rect.y+data.rect.side/2,w:32,h:32,score:.9}]});}
    };`}));
  await page.addInitScript(()=>{
    const Native=Worker;window.workerStats={started:0,closed:0,detect:0};
    window.Worker=class extends Native{
      constructor(...args){super(...args);workerStats.started++;}
      terminate(){workerStats.closed++;super.terminate();}
      postMessage(data,...args){if(data.type==='detect')workerStats.detect++;super.postMessage(data,...args);}
    };
  });
  await page.goto(BASE_URL);
  await page.getByRole('textbox',{name:'Name',exact:true}).fill('Worker QA');
  await page.getByRole('combobox',{name:'Development goal'}).selectOption('juggling');
  await page.getByRole('checkbox',{name:'I agree to store and process'}).check();
  await page.getByRole('button',{name:'Save my profile'}).click();await page.locator('dialog').waitFor({state:'hidden'});
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Record',exact:false}).click();
  await page.locator('#evidence-file').setInputFiles('tests/fixtures/contrast-ball.webm');
  await page.getByRole('spinbutton',{name:'Best consecutive contacts'}).fill('0');
  await page.getByRole('button',{name:'Save assessment'}).click();await page.getByRole('heading',{name:'Progress you can trace.'}).waitFor();
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  await page.locator('#lab-media').selectOption({label:'contrast-ball.webm'});await page.waitForFunction(()=>document.querySelector('#lab-video').readyState>=2);

  await page.locator('#lab-end').fill('1');
  const snapshot=()=>page.evaluate(async()=>(await(await fetch('/api/state')).json()));
  const select=async()=>{await page.locator('#lab-x').fill('.5');await page.locator('#lab-y').fill('.5');await page.locator('#lab-select').click();};
  const cancel=async stage=>{
    const before=Date.now();await page.locator('#lab-cancel').click();await page.getByText('Analysis cancelled.',{exact:true}).waitFor();
    await page.locator('#lab-cancel').waitFor({state:'hidden'});
    const elapsed=Date.now()-before;cancellations.push({stage,elapsed_ms:elapsed});
    if(elapsed>2500)throw new Error('Cancel blocked the UI: '+elapsed);
    if((await snapshot()).analyses.length)throw new Error('Cancelled analysis saved partial data');
    const stats=await page.evaluate(()=>workerStats);if(stats.started!==stats.closed)throw new Error('Worker leaked: '+JSON.stringify(stats));
  };
  await select();await cancel('loading');
  mode='select';await select();await page.waitForFunction(()=>workerStats.detect>=1);await cancel('selection inference');
  mode='track';await select();await page.getByText('Ball found by the local detector',{exact:false}).waitFor();
  const detects=await page.evaluate(()=>workerStats.detect);await page.locator('#lab-track').click();
  await page.waitForFunction(n=>workerStats.detect>n,detects);await cancel('tracking inference');
  mode='load';await select();await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Record',exact:false}).click();
  await page.waitForFunction(()=>workerStats.started===workerStats.closed);
  if((await snapshot()).analyses.length)throw new Error('Navigation saved a partial run');
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  await page.locator('#lab-media').selectOption({label:'contrast-ball.webm'});await page.waitForFunction(()=>document.querySelector('#lab-video').readyState>=2);
  // A full-window explicit negative review is distinct from an untouched empty timeline.
  await page.locator('#lab-end').fill('30');await page.locator('#lab-manual').click();
  await page.locator('#lab-runs').getByText('Not reviewed',{exact:true}).waitFor();
  await page.locator('#lab-save').click();await page.locator('#lab-save-error').filter({hasText:'review'}).waitFor();
  if((await snapshot()).video_annotations.length)throw new Error('Saved without review confirmation');
  await page.locator('#lab-confirmed').check();await page.locator('#lab-save').click();
  await page.getByText('Reviewed: no events in this window.',{exact:true}).waitFor();
  await page.locator('#lab-runs').getByText('0 (reviewed)',{exact:true}).waitFor();
  await page.reload();await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  await page.locator('[data-lab-open]').click();await page.getByText('Reviewed: no events in this window.',{exact:true}).waitFor();
  const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#lab-export').click()]);
  const stream=await download.createReadStream();let text='';for await(const chunk of stream)text+=chunk;
  const exported=JSON.parse(text);if(exported.annotation.events.length || !exported.annotation.confirmed || exported.samples.length)throw new Error('Empty review export changed');
  if(errors.length)throw new Error(errors.join('; '));
  await page.setViewportSize({width:390,height:844});await page.locator('#lab-runs').scrollIntoViewIfNeeded();
  await page.screenshot({path:'test-results/worker-empty-review-mobile.png',fullPage:true});
  return {result:'PASS',cancellations,navigationCleanup:true,reviewedZeroPersisted:true,exportedEmptyReview:true,browserErrors:errors};
}
