async(page)=>{
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(BASE_URL);await page.goto(BASE_URL+'/label.html');
  await page.locator('#label-file').setInputFiles('tests/fixtures/contrast-ball.webm');
  await page.waitForFunction(()=>document.querySelector('#label-video').readyState>=2 && document.querySelector('#label-id').value);
  const digest=await page.evaluate(async()=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',await document.querySelector('#label-file').files[0].arrayBuffer())),x=>x.toString(16).padStart(2,'0')).join(''));
  const task={format:'football-labelling-task-1',clip:{id:'blind-001',sha256:digest,start:.2,end:1},conditions:[]};
  const load=async data=>page.locator('#label-task').setInputFiles({name:'review.task.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(data))});
  await load({...task,clip:{...task.clip,sha256:'0'.repeat(64)}});await page.getByText('Load the matching video before its blind task.',{exact:true}).waitFor();
  await load({...task,frames:[]});await page.getByText('Invalid blind task:',{exact:false}).waitFor();
  await load({...task,clip:{...task.clip,end:99}});await page.getByText('Invalid blind task:',{exact:false}).waitFor();
  await page.locator('#label-reviewer').fill('Previous person');await page.locator('#label-independent').check();
  await load(task);await page.getByText('Blind task loaded.',{exact:false}).waitFor();
  if(await page.locator('#label-independent').isChecked() || await page.locator('#label-reviewer').inputValue() || await page.locator('#label-id').inputValue()!=='blind-001')throw new Error('Task invented reviewer provenance');
  await page.waitForFunction(()=>!document.querySelector('#label-video').seeking);
  await page.locator('#label-auto').uncheck();await page.locator('#label-absent').click();
  await load(task);await page.getByText('Export your current labels',{exact:false}).waitFor();
  if(await page.locator('#label-count').textContent()!=='1 frame labels '+String.fromCharCode(183)+' 0 contacts')throw new Error('Task overwrote work');
  await page.screenshot({path:'test-results/review-practice-2026-10-18/05-blind-task.png',fullPage:true});
  if(errors.length)throw new Error(errors.join('; '));
  return {result:'PASS',hashMismatchRejected:true,invalidTaskRejected:true,reviewerNotPrefilled:true,existingWorkPreserved:true,browserErrors:errors};
}
