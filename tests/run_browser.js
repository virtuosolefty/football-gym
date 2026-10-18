'use strict';
// Each callback gets a fresh server and browser context; never touches the player's .data workspace.
const {chromium}=require('playwright'),{spawn}=require('node:child_process'),fs=require('node:fs'),path=require('node:path'),os=require('node:os'),vm=require('node:vm');
const root=path.resolve(__dirname,'..');
const callbacks=process.argv.slice(2).length?process.argv.slice(2):['browser_startup_race.js','browser_workflow.js','browser_video_workflow.js','browser_tracking_safety.js','browser_label_workflow.js','browser_scene_cut.js','browser_pose_workflow.js'];
async function main(){
  const browser=await chromium.launch({headless:true,...(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL}:{})});
  try{
    fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
    for(const file of callbacks){
      if(path.basename(file)!==file || !/^browser_[a-z_]+\.js$/.test(file))throw new Error('Choose a browser callback filename in tests/.');
      const data=fs.mkdtempSync(path.join(os.tmpdir(),'football-browser-'));
      const server=spawn(process.env.PYTHON||'python',['-u','app.py','--port','0','--data-dir',data],{cwd:root,stdio:['ignore','pipe','pipe'],windowsHide:true});
      let output='';server.stderr.on('data',chunk=>output+=chunk);
      const exited=new Promise(resolve=>server.once('exit',resolve));
      const context=await browser.newContext({viewport:{width:1440,height:1100}});let page;
      try{
        const baseURL=await new Promise((resolve,reject)=>{let stdout='';const timer=setTimeout(()=>reject(new Error('Test server startup timed out: '+output)),15000);server.once('error',error=>{clearTimeout(timer);reject(error);});server.once('exit',()=>{clearTimeout(timer);reject(new Error('Test server exited: '+output));});server.stdout.on('data',chunk=>{stdout+=chunk;const match=stdout.match(/Football Helper is running at (http:\/\/127\.0\.0\.1:\d+)\r?\n/);if(match){clearTimeout(timer);resolve(match[1]);}});});
        page=await context.newPage();page.setDefaultTimeout(20000);
        // Synthetic workflow uses the colour fixture, irrespective of optional locally installed models.
        if(process.env.TEST_DETECTOR!=='1')await page.route('**/models/yolox_nano.onnx',route=>route.fulfill({status:404,body:'not installed in synthetic QA'}));
        const callback=vm.runInNewContext(fs.readFileSync(path.join(__dirname,file),'utf8'),{console,setTimeout,clearTimeout,Buffer,BASE_URL:baseURL},{filename:file});
        console.log(file,JSON.stringify(await callback(page)));
      }catch(error){
        if(page){console.error(await page.evaluate(()=>({status:document.querySelector('#lab-status')?.textContent,error:document.querySelector('#lab-error')?.textContent,videos:Array.from(document.querySelectorAll('video'),v=>({id:v.id,readyState:v.readyState,src:v.currentSrc,error:v.error?.message,time:v.currentTime}))})));await page.screenshot({path:path.join(root,'test-results',file+'-failure.png'),fullPage:true});}
        throw error;
      }finally{
        await context.close();server.kill();await exited;
        const resolved=path.resolve(data);
        if(path.dirname(resolved)!==path.resolve(os.tmpdir()) || !path.basename(resolved).startsWith('football-browser-'))throw new Error('Unsafe QA cleanup path.');
        fs.rmSync(resolved,{recursive:true,force:true});
      }
    }
  }finally{await browser.close();}
}
main().catch(error=>{console.error(error);process.exitCode=1;});
