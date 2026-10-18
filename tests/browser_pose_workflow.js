// Deterministic worker checks wiring, persistence and cancellation; installed-model smoke is separate.
async (page) => {
  let hang=false;const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/pose-worker.js',route=>route.fulfill({contentType:'text/javascript',body:hang?'self.onmessage=()=>{};':`self.onmessage=({data})=>{if(data.type==='load')postMessage({ready:true});else{data.bitmap.close();postMessage({pose:{status:'single',left:[[.5,.5,.9],[.49,.51,.9],[.53,.51,.9]]}});}};`}));
  await page.goto(BASE_URL);
  await page.getByRole('textbox',{name:'Name',exact:true}).fill('Pose QA');
  await page.getByRole('combobox',{name:'Development goal'}).selectOption('juggling');
  await page.getByRole('checkbox',{name:'I agree to store and process'}).check();
  await page.getByRole('button',{name:'Save my profile'}).click();await page.locator('dialog').waitFor({state:'hidden'});
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Record',exact:false}).click();
  await page.locator('#evidence-file').setInputFiles('tests/fixtures/contrast-ball.webm');
  await page.getByRole('spinbutton',{name:'Best consecutive contacts'}).fill('0');
  await page.getByRole('button',{name:'Save assessment'}).click();await page.getByRole('heading',{name:'Progress you can trace.'}).waitFor();
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  await page.locator('#lab-media').selectOption({label:'contrast-ball.webm'});await page.waitForFunction(()=>document.querySelector('#lab-video').readyState>=2);
  await page.evaluate(()=>{BallDetector.load=async()=>({});BallDetector.near=async()=>[{x:160,y:90,w:16,h:16,score:.9}];});
  const select=async()=>{await page.locator('#lab-x').fill('.5');await page.locator('#lab-y').fill('.5');await page.locator('#lab-select').click();await page.getByText('Ball found by the local detector',{exact:false}).waitFor();};
  await page.locator('#lab-end').fill('1');await page.locator('#lab-pose').check();await select();await page.locator('#lab-track').click();await page.locator('#lab-cancel').waitFor({state:'hidden'});
  const snapshot=()=>page.evaluate(async()=>(await(await fetch('/api/state')).json()));
  const run=(await snapshot()).analyses[0];
  if(run.configuration.pose_model!=='mediapipe-pose-lite-1' || run.samples.filter(s=>s.pose?.left?.length===3).length!==10)throw new Error('Pose evidence was not retained.');
  await page.locator('#lab-side').selectOption('left');await page.locator('#lab-add').click();await page.locator('#lab-confirmed').check();await page.locator('#lab-save').click();
  await page.getByText('Reviewed events saved.',{exact:false}).waitFor();
  if((await snapshot()).video_annotations[0].events[0].side!=='left')throw new Error('Anatomical foot label was lost.');
  hang=true;await select();await page.locator('#lab-track').click();await page.getByText('Loading foot evidence',{exact:false}).waitFor();
  await page.locator('#lab-cancel').click();await page.getByText('Analysis cancelled.',{exact:true}).waitFor();
  if((await snapshot()).analyses.length!==1 || !await page.locator('#lab-track').isEnabled() || errors.length)throw new Error(JSON.stringify(errors));
  return {result:'PASS',posePersistence:true,sideLabels:true,cancelDuringPoseLoad:true,browserErrors:errors};
}
