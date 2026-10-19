// Invoke the original D:\SDLC visual-QA stage; all app data and reports stay in this project.
import assert from 'node:assert/strict';
import {spawn,execFileSync} from 'node:child_process';
import {readFileSync,writeFileSync,mkdirSync,copyFileSync,existsSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(here,'..');
const reference=path.resolve(process.env.SDLC_SOURCE || 'D:/SDLC');
const {runQa}=await import(pathToFileURL(path.join(reference,'src/stages/qa.js')));
const {createStore}=await import(pathToFileURL(path.join(reference,'src/store.js')));
const {bus}=await import(pathToFileURL(path.join(reference,'src/events.js')));
const {killTree}=await import(pathToFileURL(path.join(reference,'src/proc.js')));
const {activeChildren}=await import(pathToFileURL(path.join(reference,'src/claude.js')));
const {waitForUrl}=await import('./runtime/src/appRunner.js');
const cases=JSON.parse(readFileSync(path.join(here,'visual-five.json'),'utf8'));
assert.equal(new Set(cases.map(c=>c.collection)).size,5);
assert.equal(new Set(cases.map(c=>c.sha256)).size,5);
const selected=process.argv.slice(2);
const scenario=process.env.SDLC_VISUAL_SCENARIO;
const focused=['responsive-review','review-practice'].includes(scenario);
if(process.env.SDLC_VISUAL_SCENARIO)assert.ok(focused && selected.length===1 && selected[0]==='indoor','The responsive review scenario uses only the indoor fixture');
assert.ok(selected.every(id=>cases.some(c=>c.id===id)),'Unknown visual test case');
const suite=process.env.SDLC_VISUAL_SUITE || 'sdlc-visual-five-2026-10-18';assert.ok(/^[a-z0-9-]+$/.test(suite),'Invalid suite folder');
const outputs=path.join(root,'test-results',suite);mkdirSync(outputs,{recursive:true});
const dataDir=path.join(here,'runtime/data'),store=createStore(dataDir);
const config=JSON.parse(readFileSync(path.join(here,'runtime/sdlc.config.json'),'utf8'));
const referenceHash=createHash('sha256').update(readFileSync(path.join(reference,'src/stages/qa.js'))).digest('hex');
const sourceFiles=Object.fromEntries(['web/app.js','web/video-lab.js','web/detector.js','web/detector-worker.js','web/video.css','web/label.js','football/video.py','football/knowledge.py','football/domain.py'].map(file=>[file,createHash('sha256').update(readFileSync(path.join(root,file))).digest('hex')]));
const sourceCommit=execFileSync('git',['rev-parse','HEAD'],{cwd:root,encoding:'utf8'}).trim();
bus.on('log',({scope,line})=>console.log(scope,line));
let server;
const stop=()=>{for(const child of activeChildren)killTree(child);killTree(server);};
process.on('SIGINT',()=>{stop();process.exit(130);});process.on('SIGTERM',()=>{stop();process.exit(143);});

function instructions(c){if(focused)return readFileSync(path.join(here,scenario==='review-practice'?'review-practice-2026-10-18/VISUAL.md':'reliability-2026-10-18/VISUAL.md'),'utf8');return `Run this complete VISUAL regression through the app UI using Playwright browser tools. Use a 1440x1000 desktop viewport initially. Screenshots must show the actual application, not a fabricated report. Work efficiently: after inspecting the UI, batch related Playwright locator fills/clicks with browser_run_code. Avoid repeated unchanged snapshots and stale element refs. Relevant UI IDs include lab-video, lab-start, lab-end, lab-x, lab-y, lab-radius, lab-select, lab-track, lab-status, lab-skip and lab-export; verify the page before using them. Use browser tools for all app interactions.
Dataset collection: ${c.collection}; case: ${c.id}. Focus: ${c.focus}
One representative clip is sampled from this collection; do not claim the whole dataset was tested or that labels are independent.
The unmodified video is in your working directory as QA_INPUT${path.extname(c.file)} (use its absolute path under the current working directory when the upload tool requests one).
1. Onboard a fresh test-only profile called "SDLC visual ${c.id}", Development goal "Ball mastery" (its stored value is juggling), adult age band, and consent to LOCAL processing. Capture the initial app screenshot.
2. In Record, upload QA_INPUT${path.extname(c.file)}. Enter zero for Best consecutive contacts and Save assessment ONLY to attach this public clip to this disposable QA profile. That zero is a test fixture, not a measured athlete result. Navigate to Video feedback and select the uploaded video.
3. Set Window start ${c.start}, Window end ${c.end}. Pause at ${c.seed.time} seconds. Using a browser UI DOM action to set the native video's currentTime is permitted for precise seeking; never call app APIs or change tracking state. Wait for seeking to finish. Enter Ball centre x ${c.seed.x}, Ball centre y ${c.seed.y}, radius ${c.seed.radius}, then Select ball. Visually inspect the displayed frame/selection and take a screenshot. Leave experimental foot evidence OFF. The local detector is installed. If the seed fails, one visually justified correction is allowed; record the correction, do not silently change the test. If selection still fails, record the limitation and exercise Use manual timeline instead of inventing a successful track.
4. If selected, Track selected ball. Wait for completion or a loss prompt (up to 3 minutes, polling briefly). At EVERY loss prompt capture it and click Skip remaining track in this direction. Do not re-seed onto another object. Inspect whether the message makes uncertainty clear. After completion, record exact visible coverage, status and provisional event count. Suspect/unmeasurable is an acceptable protective outcome; low useful tracking coverage or missed contacts should be a warning, not an accuracy pass. If it stalls or fails to save, capture the exact error and report a defect.
5. Inspect the saved timeline and paused video at the start, middle and last sampled frame (end minus 0.1 seconds), comparing the displayed track/marker with the visible ball where possible. Scroll the video into view before screenshots. Keep this a limited visual spot-check, not exhaustive accuracy validation. Do not mark the full timeline as human-reviewed or create an assessment from provisional detections. Export analysis JSON via the Export analysis JSON button. After export, leave any browser downloads tab open; select the original app tab if necessary. Do not close tabs (the SDLC browser tool previously hung doing that). Keep its automatically generated download filename: do not rename it, use shell commands or rewrite its contents. The reporting harness will collect it. No direct API calls. Take a desktop results screenshot.
6. Resize to 390x844 and take a mobile screenshot. Check for clipped controls, horizontal overflow and readable warnings. Inspect every field and the Review clip button of saved runs; narrow screens should show labelled stacked rows. On an unplayable clip, inspect whether the error is already shown beside the player before clicking any analysis button; do not guess its codec. The public-small source has an mp4v sample entry. Check whether the Record preview warned before Save. Scroll to inspect below the fold; normal vertical scrolling is fine. Check browser console messages for errors.
Return an evidence-backed SDLC report with screenshots, any bugs and exact reproduction steps. State detector, contact and validation limits. A UI workflow pass is not verified football accuracy. If the tools cannot operate, report couldnt_run; never convert a tool failure into an app defect. Be concise and complete all six steps without repeatedly taking the same screenshot.`;}

for(const c of cases.filter(c=>!selected.length || selected.includes(c.id))){
  const source=path.resolve(root,c.file);assert.ok(source.startsWith(root+path.sep));
  assert.equal(createHash('sha256').update(readFileSync(source)).digest('hex'),c.sha256,`Changed video: ${c.id}`);
  const attempt=Date.now().toString(36),appData=path.join(outputs,'app-data',`${c.id}-${attempt}`);
  mkdirSync(appData,{recursive:true});
  server=spawn(process.env.PYTHON||'python',['-u','app.py','--port','0','--data-dir',appData],{cwd:root,windowsHide:true,stdio:['ignore','pipe','pipe']});
  let stderr='';server.stderr.on('data',chunk=>stderr+=chunk);
  const exited=new Promise(resolve=>server.once('exit',resolve));
  try{
    const url=await new Promise((resolve,reject)=>{let output='';const timer=setTimeout(()=>reject(new Error('QA app startup timeout')),15000);server.once('error',error=>{clearTimeout(timer);reject(error);});server.once('exit',()=>{clearTimeout(timer);reject(new Error('QA app exited: '+stderr));});server.stdout.on('data',chunk=>{output+=chunk;const match=output.match(/Football Helper is running at (http:\/\/127\.0\.0\.1:\d+)/);if(match){clearTimeout(timer);resolve(match[1]);}});});
    await waitForUrl(url,10000);
    const title=focused?(scenario==='review-practice'?'Review tools and distinct practice':'Responsive cancellation and empty review'):`Five datasets / ${c.collection} / ${c.id}`;
    const script=instructions(c);
    const previous=store.tests.findAll(t=>t.title===title)[0];
    const test=previous?store.tests.update(previous.id,{instructions:script}):store.tests.create({title,instructions:script,source:'five-dataset-visual-qa'});
    const ctx={cfg:config,store,dataDir,runDir:id=>{
      const directory=path.join(dataDir,'runs',id);mkdirSync(directory,{recursive:true});
      const target=path.join(directory,`QA_INPUT${path.extname(source)}`);if(!existsSync(target))copyFileSync(source,target);
      if(scenario==='review-practice')writeFileSync(path.join(directory,'QA_TASK.json'),JSON.stringify({format:'football-labelling-task-1',clip:{id:'blind-visual-001',sha256:c.sha256,start:0,end:3},conditions:[]}));
      return directory;
    }};
    console.log('START',c.id,url);
    const result=await runQa(ctx,{title,instructions:script,url,testId:test.id,environment:'isolated-public-footage'});
    const record={case:c,scenario:focused?scenario:'five-datasets',sourceCommit,sourceFiles,sdlcSource:reference,sdlcQaSha256:referenceHash,appData,result};
    writeFileSync(path.join(outputs,`${c.id}-${result.id}.json`),JSON.stringify(record,null,2)+'\n');
    writeFileSync(path.join(outputs,`${c.id}-${result.id}-server.log`),stderr);
    console.log('RESULT',JSON.stringify({case:c.id,id:result.id,status:result.status,verdict:result.verdict,reason:result.couldntRunReason,screenshots:result.screenshots,costUsd:result.costUsd}));
  }finally{killTree(server);await Promise.race([exited,new Promise(resolve=>setTimeout(resolve,5000))]);}
}
