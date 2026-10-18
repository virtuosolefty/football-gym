// Direct Playwright visual fallback when the original SDLC agent cannot run. Installed local models required.
async(page)=>{
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  const folder='test-results/reliability-2026-10-18/';
  await page.goto(BASE_URL);
  await page.getByRole('textbox',{name:'Name',exact:true}).fill('Reliability visual QA');
  await page.getByRole('combobox',{name:'Development goal'}).selectOption('juggling');
  await page.getByRole('checkbox',{name:'I agree to store and process'}).check();
  await page.getByRole('button',{name:'Save my profile'}).click();await page.locator('dialog').waitFor({state:'hidden'});
  await page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name:'Record',exact:false}).click();
  await page.locator('#evidence-file').setInputFiles('test-results/real-footage/footage/indoor.mp4');
  await page.getByRole('spinbutton',{name:'Best consecutive contacts'}).fill('0');
  await page.getByRole('button',{name:'Save assessment'}).click();await page.getByRole('heading',{name:'Progress you can trace.'}).waitFor();
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  await page.locator('#lab-media').selectOption({label:'indoor.mp4'});await page.waitForFunction(()=>document.querySelector('#lab-video').readyState>=2);

  await page.locator('#lab-end').fill('3');
  const coordinates=async()=>{await page.locator('#lab-x').fill('.428125');await page.locator('#lab-y').fill('.822222');await page.locator('#lab-radius').fill('8');};
  await coordinates();await page.locator('#lab-select').click();
  await page.locator('#lab-cancel').click();await page.getByText('Analysis cancelled.',{exact:true}).waitFor();
  const cancelled=await page.evaluate(async()=>(await(await fetch('/api/state')).json()).analyses.length);
  if(cancelled)throw new Error('Real-model load cancellation saved a partial run');
  await page.screenshot({path:folder+'01-cancelled.png',fullPage:true});
  await coordinates();await page.locator('#lab-select').click();await page.getByText('Ball found by the local detector',{exact:false}).waitFor({timeout:90000});
  await page.locator('#lab-track').click();
  await page.waitForFunction(()=>document.querySelector('#lab-cancel').hidden,{},{timeout:90000});
  if(await page.locator('#lab-error').textContent())throw new Error(await page.locator('#lab-error').textContent());
  const status=await page.locator('#lab-status').textContent();
  await page.screenshot({path:folder+'02-real-tracking.png',fullPage:true});
  const exportRun=async name=>{const [download]=await Promise.all([page.waitForEvent('download'),page.locator('#lab-export').click()]);await download.saveAs(folder+name+'.json');};
  await exportRun('indoor-worker-analysis');
  await page.locator('#lab-end').fill('.1');await page.locator('#lab-manual').click();
  await page.getByText('Manual timeline',{exact:false}).first().waitFor();
  await page.locator('#lab-save').click();await page.getByText('Review the entire selected window before confirming its events.',{exact:true}).waitFor();
  await page.screenshot({path:folder+'03-review-required.png',fullPage:true});
  await page.locator('#lab-confirmed').check();await page.locator('#lab-save').click();
  await page.getByText('Reviewed: no events in this window.',{exact:true}).waitFor();
  await page.reload();await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  await page.locator('[data-lab-open]').first().click();await page.getByText('Reviewed: no events in this window.',{exact:true}).waitFor();
  await page.waitForFunction(()=>document.querySelector('#lab-video').readyState>=2 && !document.querySelector('#lab-video').seeking);
  await page.screenshot({path:folder+'04-empty-reviewed-desktop.png',fullPage:true});await exportRun('empty-reviewed-analysis');
  await page.setViewportSize({width:390,height:844});await page.locator('#lab-runs').scrollIntoViewIfNeeded();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  if(overflow || errors.length)throw new Error(JSON.stringify({overflow,errors}));
  await page.screenshot({path:folder+'05-empty-reviewed-mobile.png',fullPage:true});
  return {result:'PASS',kind:'direct-playwright-fallback',realModelLoadCancel:true,retryTrackingStatus:status,emptyReviewReload:true,noHorizontalOverflow:true,browserErrors:errors};
}
