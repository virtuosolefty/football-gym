// Playwright callback: export human-reference frames through native video decoding.
async (page) => {
  await page.goto('http://127.0.0.1:8767');
  await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
  const metadata=[];
  for(const id of ['daylight','indoor','strobe']) {
    await page.getByRole('combobox',{name:'Saved video'}).selectOption({label:id+'.mp4'});
    await page.waitForFunction(()=>Number.isFinite(document.querySelector('#lab-video').duration)&&document.querySelector('#lab-video').readyState>=2);
    const meta=await page.locator('#lab-video').evaluate(v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight}));
    // This is the same capped canvas size used by the existing app.
    const dimensions=await page.locator('#lab-frame').evaluate(canvas=>{canvas.style.width=canvas.width+'px';canvas.style.height=canvas.height+'px';return {width:canvas.width,height:canvas.height};});
    for(let i=0;i<30;i++) {
      const time=i/10;
      await page.locator('#lab-video').evaluate((v,t)=>{v.pause();v.currentTime=t;},time);
      await page.waitForFunction(t=>!document.querySelector('#lab-video').seeking && Math.abs(document.querySelector('#lab-video').currentTime-t)<.01,time);
      await page.locator('#lab-frame').screenshot({path:'D:/football helper/test-results/real-footage/frames/'+id+'-'+String(i).padStart(2,'0')+'.png'});
    }
    // More frequent frame references let us check visible contacts independently of suggestions.
    for(let i=0;i<75;i++) {
      const time=i*.04;
      await page.locator('#lab-video').evaluate((v,t)=>{v.pause();v.currentTime=t;},time);
      await page.waitForFunction(t=>!document.querySelector('#lab-video').seeking && Math.abs(document.querySelector('#lab-video').currentTime-t)<.01,time);
      await page.locator('#lab-frame').screenshot({path:'D:/football helper/test-results/real-footage/contacts/'+id+'-'+String(i).padStart(2,'0')+'.png'});
    }
    metadata.push({id,...meta,canvas:dimensions,start:0,end:3,samples:30,contact_reference_step_seconds:.04});
  }
  return metadata;
}
