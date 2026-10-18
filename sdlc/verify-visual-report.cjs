const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
const assert = require('assert/strict');
const {pathToFileURL} = require('url');
(async()=>{
const suite=process.env.SDLC_VISUAL_SUITE || 'sdlc-visual-five-2026-10-18';assert.match(suite,/^[a-z0-9-]+$/);
const report=path.resolve('test-results',suite,'report/report.html');
const cases=JSON.parse(fs.readFileSync(path.join(path.dirname(report),'results.json'),'utf8'));assert.ok(cases.length>0);
const browser=await chromium.launch({channel:'msedge',headless:true});
try {
const page=await browser.newPage(); const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(pathToFileURL(report).href);
assert.equal(await page.locator('section').count(),cases.length);
for (const width of [1440,390]) {
 await page.setViewportSize({width,height:1000});
 const checks=await page.evaluate(async()=>{
  const images=[...document.images];images.forEach(i=>i.loading='eager');
  await Promise.all(images.map(i=>i.decode()));
  return {width:document.documentElement.clientWidth,scrollWidth:document.documentElement.scrollWidth,images:images.length};
 });
 await page.screenshot({path:path.join(path.dirname(report),`report-preview-${width}.png`)});
 console.log(JSON.stringify({viewport:width,...checks}));
 assert.ok(checks.scrollWidth<=width,'Report has page-level horizontal overflow');
 assert.ok(checks.images>=cases.length);
}
assert.deepEqual(errors,[]);
for(const href of await page.locator('a').evaluateAll(a=>a.map(e=>e.getAttribute('href')))) if(!/^(https?:|#)/.test(href)) assert.ok(fs.existsSync(path.resolve(path.dirname(report),href)),href);
} finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
