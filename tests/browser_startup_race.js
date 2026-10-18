// Playwright callback; run against a QA server on 8766. Clicking navigation before the first /api/state response must not throw.
async (page) => {
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.route('**/api/state',async route=>{await new Promise(done=>setTimeout(done,1500));route.continue();});
  await page.goto(BASE_URL,{waitUntil:'domcontentloaded'});
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  await page.getByRole('button',{name:'Edit player profile'}).click();   // also clickable before the first state load
  await page.waitForFunction(()=>document.querySelector('#profile-dialog[open]'),{},{timeout:15000});
  if(!await page.evaluate(()=>location.hash==='#analysis'))throw new Error('The clicked route was lost while state was loading.');
  if(errors.length)throw new Error('Navigation before the first state load raised: '+errors.join('; '));
  return {result:'PASS',browserErrors:errors};
}
