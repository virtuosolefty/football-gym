// Real browser decode failure and source recovery; no installed models or private footage required.
async page => {
 const assert=(ok,message)=>{if(!ok)throw Error(message);},errors=[];page.on('pageerror',e=>errors.push(e.message));
 const nav=name=>page.getByRole('navigation',{name:'Main navigation'}).getByRole('button',{name,exact:false}).click();
 const feedback=()=>page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
 await page.goto(BASE_URL);await page.getByRole('textbox',{name:'Name',exact:true}).fill('Playback QA');
 await page.getByRole('combobox',{name:'Development goal'}).selectOption('juggling');await page.getByRole('checkbox',{name:'I agree to store and process'}).check();
 await page.getByRole('button',{name:'Save my profile'}).click();await page.locator('dialog').waitFor({state:'hidden'});
 await nav('Record');
 const bad={name:'unplayable.mp4',mimeType:'video/mp4',buffer:Buffer.from('000000186674797069736f6d0000000069736f6d6d703432','hex')};
 await page.locator('#evidence-file').setInputFiles(bad);
 await page.waitForFunction(()=>document.querySelector('#attempt-playback-error').textContent.includes('H.264'));
 await page.locator('#evidence-file').setInputFiles('tests/fixtures/contrast-ball.webm');
 await page.waitForFunction(()=>document.querySelector('#attempt-preview').readyState>=2 && !document.querySelector('#attempt-playback-error').textContent);
 await page.locator('#evidence-file').setInputFiles(bad);
 await page.waitForFunction(()=>document.querySelector('#attempt-playback-error').textContent.includes('codec'));
 await page.getByRole('spinbutton',{name:'Best consecutive contacts'}).fill('0');await page.getByRole('button',{name:'Save assessment'}).click();
 await page.getByRole('heading',{name:'Progress you can trace.'}).waitFor();await nav('Record');
 await page.locator('#evidence-file').setInputFiles('tests/fixtures/contrast-ball.webm');await page.getByRole('spinbutton',{name:'Best consecutive contacts'}).fill('0');
 await page.getByRole('button',{name:'Save assessment'}).click();await page.getByRole('heading',{name:'Progress you can trace.'}).waitFor();await feedback();
 await page.locator('#lab-media').selectOption({label:'unplayable.mp4'});
 await page.waitForFunction(()=>document.querySelector('#lab-playback-error').textContent.includes('H.264'));
 const message=await page.locator('#lab-playback-error').textContent();
 for(const id of ['lab-select','lab-track','lab-manual']) {
  await page.locator('#'+id).click();assert(await page.locator('#lab-error').textContent()===message,'Actions must preserve the decoder explanation');
 }
 await page.locator('#lab-export').click();assert(await page.locator('#lab-playback-error').textContent()===message,'Export must not erase the persistent warning');
 await page.locator('#lab-playback-error').scrollIntoViewIfNeeded();await page.screenshot({path:'test-results/playback-error-desktop.png'});
 await page.locator('#lab-media').selectOption({label:'contrast-ball.webm'});
 await page.waitForFunction(()=>document.querySelector('#lab-video').readyState>=2 && !document.querySelector('#lab-playback-error').textContent);
 assert(await page.locator('#lab-error').textContent()==='','Switching clips must clear stale action errors');
 await page.locator('#lab-end').fill('3');await page.locator('#lab-manual').click();await page.locator('#lab-runs [data-lab-open]').waitFor();
 await page.setViewportSize({width:390,height:844});await page.locator('#lab-runs').scrollIntoViewIfNeeded();
 assert(await page.locator('#lab-runs').evaluate(el=>el.scrollWidth<=el.clientWidth),'Saved run card must not hide columns in a sideways scroll');
 const bounds=await page.locator('#lab-runs td').evaluateAll(cells=>cells.map(c=>({label:c.dataset.label,left:c.getBoundingClientRect().left,right:c.getBoundingClientRect().right})));
 assert(bounds.length===5 && bounds.every(c=>c.label && c.left>=0 && c.right<=390),'All five labelled fields must fit mobile');
 await page.screenshot({path:'test-results/saved-runs-mobile.png'});await page.locator('#lab-runs [data-lab-open]').click();await page.reload();await page.locator('#lab-runs [data-lab-open]').click();
 await page.waitForFunction(()=>document.querySelector('#lab-video').readyState>=2);assert(!(await page.locator('#lab-playback-error').textContent()),'Reloaded playable run must remain usable');
 await page.locator('#lab-media').selectOption('');await page.waitForFunction(()=>!document.querySelector('#lab-video').getAttribute('src'));
 assert(await page.locator('#lab-frame').evaluate(c=>c.getContext('2d').getImageData(0,0,1,1).data[3])===0,'Empty selection must clear stale frame');
 assert(!(await page.locator('#lab-playback-error').textContent()),'Empty selection is not a decode error');assert(!errors.length,errors.join('; '));
 return {result:'PASS',groups:8,browserErrors:errors};
}
