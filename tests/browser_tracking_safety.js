// Software safety regressions use a deterministic detector; they do not claim model accuracy.
async (page) => {
  const assert=(value,message)=>{if(!value)throw new Error(message);},errors=[];
  page.on('pageerror',error=>errors.push(error.message));
  await page.goto(BASE_URL);
  await page.getByRole('textbox',{name:'Name',exact:true}).fill('Tracking safety QA');
  await page.getByRole('combobox',{name:'Development goal'}).selectOption('juggling');
  await page.getByRole('checkbox',{name:'I agree to store and process'}).check();
  await page.getByRole('button',{name:'Save my profile'}).click();await page.locator('dialog').waitFor({state:'hidden'});
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Record',exact:false}).click();
  await page.locator('#evidence-file').setInputFiles('tests/fixtures/contrast-ball.webm');
  await page.getByRole('spinbutton',{name:'Best consecutive contacts'}).fill('0');
  await page.getByRole('button',{name:'Save assessment'}).click();await page.getByRole('heading',{name:'Progress you can trace.'}).waitFor();
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  await page.getByRole('combobox',{name:'Saved video'}).selectOption({label:'contrast-ball.webm'});
  await page.waitForFunction(()=>Number.isFinite(document.querySelector('#lab-video').duration) && document.querySelector('#lab-video').readyState>=2);
  await page.evaluate(()=>{
    window.testMode='gap';window.detectionTimes=[];
    BallDetector.load=async()=>({model:BallDetector.MODEL});
    BallDetector.near=async(_,v)=>{const t=Number(v.currentTime.toFixed(1));window.detectionTimes.push(t);if(window.testMode==='gap' && t>=.2 && t<=.3)return [];if(window.testMode==='edge' && t===.1)return [];return [{x:window.testMode==='edge' && t===0?5:160,y:90,w:16,h:16,score:.8}];};
  });
  await page.locator('#lab-end').fill('1');
  const snapshot=()=>page.evaluate(async()=>(await(await fetch('/api/state')).json()));
  const select=async(x='.5')=>{
    await page.locator('#lab-video').evaluate(v=>{v.pause();v.currentTime=0;});
    await page.waitForFunction(()=>!document.querySelector('#lab-video').seeking && document.querySelector('#lab-video').currentTime<.01);
    await page.locator('#lab-x').fill(x);await page.locator('#lab-y').fill('.5');await page.getByRole('button',{name:'Select ball',exact:true}).click();await page.getByText('Ball found by the local detector',{exact:false}).waitFor();
  };
  await select();await page.getByRole('button',{name:'Track selected ball'}).click();
  await page.getByText('Ball lost at 0.30 s',{exact:false}).waitFor();
  assert(!(await page.evaluate(()=>window.detectionTimes)).some(t=>t>.3),'A decoy after the gap must not be inferred before confirmation.');
  await page.getByRole('button',{name:'+0.1 sec',exact:true}).click();
  await page.waitForFunction(()=>!document.querySelector('#lab-video').seeking && Math.abs(document.querySelector('#lab-video').currentTime-.4)<.01);
  const bounds=await page.locator('#lab-frame').boundingBox();await page.locator('#lab-frame').click({position:{x:bounds.width*.5,y:bounds.height*.5}});
  await page.getByRole('button',{name:'Cancel analysis'}).waitFor({state:'hidden'});
  let state=await snapshot(),run=state.analyses[0];
  assert(run.configuration.reseeds.length===1 && run.configuration.reseeds[0].time===.4,'The new user confirmation must be retained.');
  assert(run.samples.find(s=>s.time===.3).found===false && run.samples.find(s=>s.time===.4).segment===1,'No invented detections in the gap.');
  assert(run.media_sha256?.length===64,'Analysis must bind to the uploaded video hash.');
  await page.evaluate(()=>{window.testMode='edge';window.detectionTimes=[];});
  await select('.016');await page.getByRole('button',{name:'Track selected ball'}).click();
  await page.getByText('Ball lost at 0.10 s (edge_exit)',{exact:false}).waitFor();
  await page.getByRole('button',{name:'Skip remaining track in this direction'}).click();
  await page.getByRole('button',{name:'Cancel analysis'}).waitFor({state:'hidden'});
  state=await snapshot();run=state.analyses[1];assert(run.samples.filter(s=>s.found).length===1,'Skipping an edge exit must not adopt a bottle.');
  await select('.016');await page.getByRole('button',{name:'Track selected ball'}).click();await page.getByText('Ball lost at 0.10 s',{exact:false}).waitFor();
  await page.getByRole('button',{name:'Cancel analysis'}).click();await page.getByText('Analysis cancelled.',{exact:true}).waitFor();
  assert((await snapshot()).analyses.length===2,'Cancel during confirmation must not save a partial run.');
  assert(await page.getByRole('button',{name:'Track selected ball'}).isEnabled(),'Tracking must be usable after cancellation.');
  await select('.016');await page.getByRole('button',{name:'Track selected ball'}).click();await page.getByText('Ball lost at 0.10 s',{exact:false}).waitFor();
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Home',exact:false}).click();
  assert((await snapshot()).analyses.length===2,'Navigation cancels a pending confirmation.');
  assert(!errors.length,errors.join('; '));
  return {result:'PASS',reseed:true,edgeExit:true,cancelDuringConfirmation:true,navigationCancellation:true,browserErrors:errors};
}
