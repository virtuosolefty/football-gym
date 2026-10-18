'use strict';
const {chromium}=require('playwright'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'../..'),data=path.join(root,'test-results','validation-2026-10-14'),ref=JSON.parse(fs.readFileSync(path.join(__dirname,'reference.json'),'utf8'));
(async()=>{
  const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage();
  try{
    await page.goto('http://127.0.0.1:8784');await page.waitForFunction(()=>typeof state!=='undefined' && state?.profile,{}, {timeout:60000});await page.getByRole('navigation',{name:'Workspace navigation'}).getByRole('button',{name:'Video feedback'}).click();
    const metadata=[];
    for(const clip of ref.clips){
      if(process.env.ONLY && !process.env.ONLY.split(',').includes(clip.id))continue;
      await page.locator('#lab-media').selectOption({label:clip.file});await page.waitForFunction(()=>Number.isFinite(document.querySelector('#lab-video').duration) && document.querySelector('#lab-video').readyState>=2);
      const times=process.env.ALL_FRAMES==='1'?Array.from({length:Math.round((clip.window[1]-clip.window[0])*10)},(_,i)=>Number((clip.window[0]+i*.1).toFixed(3))):[clip.seed_time];
      const folder=path.join(data,'reference-frames',clip.id);fs.mkdirSync(folder,{recursive:true});
      for(const time of times){
        await page.locator('#lab-video').evaluate((v,t)=>{v.pause();v.currentTime=t;},time);await page.waitForFunction(t=>!document.querySelector('#lab-video').seeking && document.querySelector('#lab-video').readyState>=2 && Math.abs(document.querySelector('#lab-video').currentTime-t)<.01,time);
        const image=await page.locator('#lab-video').evaluate(v=>{const c=document.createElement('canvas');c.width=v.videoWidth;c.height=v.videoHeight;c.getContext('2d').drawImage(v,0,0);return {width:c.width,height:c.height,time:v.currentTime,png:c.toDataURL('image/png').split(',')[1]};});
        fs.writeFileSync(path.join(folder,time.toFixed(3)+'.png'),Buffer.from(image.png,'base64'));metadata.push({id:clip.id,time,width:image.width,height:image.height,actual_clock:image.time});
      }
      console.log('captured',clip.id,times.length);
    }
    fs.writeFileSync(path.join(data,'capture-metadata-'+(process.env.ALL_FRAMES==='1'?'all':'seeds')+'.json'),JSON.stringify(metadata,null,2));
  }catch(e){console.error((await page.locator('body').innerText()).slice(0,1600));await page.screenshot({path:path.join(data,'capture-error.png'),fullPage:true});throw e;}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
