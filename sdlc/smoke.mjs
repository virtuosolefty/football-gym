// Exercise the actual SDLC integration; always stop only the processes started here.
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {readFileSync, mkdirSync, writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadConfig} from './runtime/src/config.js';
import {startApp, stopAll, waitForUrl} from './runtime/src/appRunner.js';
import {killTree} from './runtime/src/proc.js';

const here=path.dirname(fileURLToPath(import.meta.url)), root=path.resolve(here,'..');
const cfg=loadConfig(path.join(here,'runtime/sdlc.config.json'));
assert.equal(cfg.project.repoPath,root);
const provenance=JSON.parse(readFileSync(path.join(here,'runtime/source-provenance.json'),'utf8'));
for(const [name,hash] of Object.entries(provenance.sha256)) {
  assert.equal(createHash('sha256').update(readFileSync(path.join(provenance.source,name))).digest('hex'),hash,`Reference SDLC changed: ${name}`);
}
await assert.rejects(waitForUrl('http://invalid',1,async()=>({status:403})),/HTTP 403/);
const url=`http://127.0.0.1:${cfg.server.port}`;
try {
  await fetch(url,{signal:AbortSignal.timeout(1000)});
  throw new Error('SDLC dashboard port is occupied; refusing to use another process.');
} catch(error) {
  if(error.message.includes('occupied'))throw error;
}
const dashboard=spawn(process.execPath,['src/server.js'],{cwd:path.join(here,'runtime'),windowsHide:true,stdio:['ignore','pipe','pipe']});
let log='';dashboard.stdout.on('data',c=>log+=c);dashboard.stderr.on('data',c=>log+=c);
let spawnError;dashboard.on('error',e=>spawnError=e);
const exited=new Promise(resolve=>dashboard.once('exit',resolve));
try {
  await waitForUrl(`${url}/api/state`,10000,fetch,()=>Boolean(spawnError)||dashboard.exitCode!==null);
  const {data:state}=await(await fetch(`${url}/api/state`)).json();
  assert.equal(state.project.repoPath,root);
  const backlog=JSON.parse(readFileSync(path.join(here,'backlog.json'),'utf8'));
  for(const task of backlog) {
    if(state.tasks.some(t=>t.title===task.title))continue;
    const response=await fetch(`${url}/api/tasks`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(task)});
    assert.ok(response.ok,await response.text());
  }
  const app=await startApp({name:'football-smoke',cwd:root,command:cfg.app.startCommand,port:cfg.app.previewPort,
    logFile:path.join(here,'runtime/data/smoke-preview.log')});
  assert.match(app.url,/127\.0\.0\.1/);
  const response=await fetch(app.url);
  assert.equal(response.status,200);
  assert.match(await response.text(),/Football Helper/);
  const cookie=response.headers.get('set-cookie').split(';')[0];
  const appState=await(await fetch(`${app.url}/api/state`,{headers:{Cookie:cookie}})).json();
  assert.equal(appState.analyses.length,0);
  const report={dashboard:'passed',preview:'passed',readiness_rejects_403:true,reference_source_hashes_unchanged:true,
    project:root,appData:path.join(here,'app-data',String(cfg.app.previewPort)),backlogTasks:backlog.length,
    automated_model_plan_build_qa:'not run; this phase uses the documented manual lifecycle'};
  mkdirSync(path.join(root,'evaluation/phase-2026-10-18'),{recursive:true});
  writeFileSync(path.join(root,'evaluation/phase-2026-10-18/sdlc-smoke.json'),JSON.stringify(report,null,2)+'\n');
  console.log(JSON.stringify(report));
} catch(error) {
  console.error(log);
  throw error;
} finally {
  await stopAll();
  killTree(dashboard);
  await Promise.race([exited,new Promise(resolve=>setTimeout(resolve,5000))]);
}
