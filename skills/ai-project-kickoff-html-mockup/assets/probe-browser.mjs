// Node >=22 built-ins only. Chrome is short-lived, local CDP only, isolated profile.
import {spawn} from 'node:child_process';
import {mkdtemp, rm, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {pathToFileURL} from 'node:url';

const [chrome, page, widthArg, ...options] = process.argv.slice(2);
const width = Number(widthArg);
if (!chrome || !page || !Number.isInteger(width) || typeof WebSocket !== 'function') {
  console.error('Requires Chrome path, local page, integer width, Node >=22 WebSocket');
  process.exit(2);
}
const profile = await mkdtemp(join(tmpdir(), 'html-mockup-'));
let child, ws;
let nextId = 0;
const pending = new Map();
const deadline = setTimeout(() => { console.error('browser probe timeout'); child?.kill('SIGKILL'); process.exitCode = 1; ws?.close(); }, 35000);
try {
  const flags = ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'];
  if (options.includes('--no-sandbox')) flags.unshift('--no-sandbox');
  child = spawn(chrome, flags, {stdio: ['ignore', 'ignore', 'pipe']});
  const endpoint = await new Promise((resolve, reject) => {
    let stderr = '';
    child.stderr.on('data', chunk => {
      stderr += chunk.toString();
      const m = stderr.match(/DevTools listening on (ws:\/\/127\.0\.0\.1:[^\s]+)/);
      if (m) resolve(m[1]);
    });
    child.once('error', reject);
    child.once('exit', code => reject(new Error(`Chrome exited ${code}: ${stderr.slice(-1000)}`)));
  });
  ws = new WebSocket(endpoint);
  await new Promise((resolve, reject) => {ws.onopen = resolve; ws.onerror = reject; ws.onclose = ()=>reject(new Error("CDP closed before connection"));});
  ws.onclose = () => { for (const waiter of pending.values()) waiter.reject(new Error("CDP connection closed")); pending.clear(); };
  ws.onmessage = event => {
    const message = JSON.parse(event.data);
    if (!message.id) return;
    const waiter = pending.get(message.id);
    if (!waiter) return;
    pending.delete(message.id);
    message.error ? waiter.reject(new Error(JSON.stringify(message.error))) : waiter.resolve(message.result);
  };
  const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => {
    const id = ++nextId;
    pending.set(id, {resolve, reject});
    ws.send(JSON.stringify({id, method, params, ...(sessionId ? {sessionId} : {})}));
  });
  const {targetId} = await send('Target.createTarget', {url:'about:blank'});
  const {sessionId} = await send('Target.attachToTarget', {targetId, flatten:true});
  const call = (method, params) => send(method, params, sessionId);
  await call('Page.enable');
  await call('Runtime.enable');
  // Set layout viewport directly, not --window-size (Chrome may clamp 390 to 500).
  await call('Emulation.setDeviceMetricsOverride', {width, height:900, deviceScaleFactor:1, mobile:false});
  const nav = await call('Page.navigate', {url:pathToFileURL(page).href});
  if (nav.errorText) throw new Error(nav.errorText);
  let ready = false;
  for (let i = 0; i < 100; i++) {
    const result = await call('Runtime.evaluate', {expression:'document.readyState === "complete"', returnByValue:true});
    if (result.result?.value) {ready = true; break;}
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  if (!ready) throw new Error('document never completed loading');
  const evaluated = await call('Runtime.evaluate', {awaitPromise:true, returnByValue:true, expression:`(async()=>{
    await document.fonts.ready;
    await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));
    const root=document.documentElement, vw=root.clientWidth, offenders=[];
    const contained=e=>{for(let p=e.parentElement;p&&p!==root&&p!==document.body;p=p.parentElement){if(['auto','scroll','hidden','clip'].includes(getComputedStyle(p).overflowX))return true;}return false;};
    for(const e of document.querySelectorAll('body *')){
      if(e.namespaceURI==='http://www.w3.org/2000/svg')continue;
      const style=getComputedStyle(e),r=e.getBoundingClientRect();
      if(style.display==='none'||!e.getClientRects().length||contained(e))continue;
      if(r.right>vw+1||r.left < -1||(style.overflowX==='visible'&&e.scrollWidth>e.clientWidth+1))offenders.push({tag:e.tagName,class:e.className?.toString(),left:r.left,right:r.right,scroll:e.scrollWidth,client:e.clientWidth});
    }
    return {requested:${width},innerWidth:innerWidth,clientWidth:vw,overflow:Math.max(root.scrollWidth,document.body.scrollWidth)-vw,offenders};
  })()`});
  if (evaluated.exceptionDetails || !evaluated.result?.value) throw new Error('JS probe did not return a measurement');
  if (options.includes('--screenshot')) {
    const output = options[options.indexOf('--screenshot')+1];
    if (!output) throw new Error('missing screenshot output');
    const shot = await call('Page.captureScreenshot', {format:'png', captureBeyondViewport:true});
    await writeFile(output, Buffer.from(shot.data, 'base64'));
  }
  process.stdout.write(JSON.stringify(evaluated.result.value));
} catch (error) {
  console.error(error.message || String(error));
  process.exitCode = 1;
} finally {
  clearTimeout(deadline);
  ws?.close();
  if (child && child.exitCode === null) {
    child.kill('SIGTERM');
    await Promise.race([new Promise(resolve=>child.once('exit',resolve)),new Promise(resolve=>setTimeout(resolve,1500))]);
    if (child.exitCode === null) child.kill('SIGKILL');
  }
  await rm(profile,{recursive:true,force:true,maxRetries:3,retryDelay:100});
}
