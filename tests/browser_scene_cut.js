async (page) => {
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(BASE_URL);
  await page.getByRole('textbox',{name:'Name',exact:true}).fill('Scene cut QA');
  await page.getByRole('combobox',{name:'Development goal'}).selectOption('juggling');
  await page.getByRole('checkbox',{name:'I agree to store and process'}).check();
  await page.getByRole('button',{name:'Save my profile'}).click();await page.locator('dialog').waitFor({state:'hidden'});
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Record',exact:false}).click();
  await page.locator('#evidence-file').setInputFiles('tests/fixtures/scene-cut-decoy.mp4');
  await page.getByRole('spinbutton',{name:'Best consecutive contacts'}).fill('0');
  await page.getByRole('button',{name:'Save assessment'}).click();await page.getByRole('heading',{name:'Progress you can trace.'}).waitFor();
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  await page.locator('#lab-media').selectOption({label:'scene-cut-decoy.mp4'});
  await page.waitForFunction(()=>document.querySelector('#lab-video').readyState>=2);
  await page.evaluate(()=>BallDetector.load=async()=>{throw new Error('Synthetic colour regression.');});
  await page.locator('#lab-end').fill('4');await page.locator('#lab-radius').fill('16');
  await page.locator('#lab-x').fill('.5');await page.locator('#lab-y').fill('.5');
  await page.locator('#lab-select').click();await page.getByText('Colour patch selected.',{exact:false}).waitFor();
  await page.locator('#lab-track').click();await page.getByText('Ball lost at 1.50 s (scene_change)',{exact:false}).waitFor();
  await page.locator('#lab-skip').click();await page.locator('#lab-cancel').waitFor({state:'hidden'});
  const run=await page.evaluate(async()=>(await(await fetch('/api/state')).json()).analyses.at(-1));
  if(!run || run.samples.some(s=>s.time>=1.5 && s.found) || !run.samples.some(s=>s.lost_reason==='scene_change') || errors.length)throw new Error(JSON.stringify({run,errors}));
  return {result:'PASS',coverage:run.report.coverage,wrongPostCutPoints:0,browserErrors:errors};
}
