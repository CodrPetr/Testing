// Scripted 1v1 between two headless browsers; streams the host's screen as timestamped JPEG frames.
// usage: node capture.mjs --out work/cap3 --seconds 320
import { chromium } from 'playwright';
import { mkdirSync, appendFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > -1 ? process.argv[i + 1] : d; };
const OUT = resolve(arg('out', 'work/cap')); const SECONDS = Number(arg('seconds', 320));
mkdirSync(OUT, { recursive: true }); writeFileSync(`${OUT}/frames.txt`, ''); writeFileSync(`${OUT}/log.txt`, '');
const log = m => { const line = `${new Date().toISOString().slice(11, 19)} ${m}`; console.log(line); appendFileSync(`${OUT}/log.txt`, line + '\n'); };
const args = ['--use-gl=angle', '--use-angle=swiftshader', '--enable-webgl', '--ignore-gpu-blocklist', '--enable-unsafe-swiftshader', '--autoplay-policy=no-user-gesture-required'];
const b = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium', args });
const sleep = ms => new Promise(r => setTimeout(r, ms));
async function open(vp) {
  const ctx = await b.newContext({ viewport: vp }); const p = await ctx.newPage();
  await p.goto('https://ironveil.live', { waitUntil: 'networkidle', timeout: 90000 }); await p.waitForTimeout(1500);
  await p.getByText('Decline', { exact: true }).first().click({ timeout: 3000 }).catch(() => {});
  await p.getByText('Play', { exact: false }).first().click(); await p.waitForTimeout(1200);
  return p;
}
// click an element by CSS selector at its centre, no actionability waits (the page renders at ~1 fps)
const clickSel = async (p, sel) => { const c = await p.evaluate(s => { const el = document.querySelector(s); if (!el || !el.offsetParent) return null; const r = el.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; }, sel); if (!c) { log(`miss ${sel}`); return false; } await p.mouse.click(c[0], c[1]); return true; };
const clickText = async (p, re, minY = 0) => { const c = await p.evaluate(([src, flags, minY]) => { const rx = new RegExp(src, flags); const el = [...document.querySelectorAll('button')].find(e => e.offsetParent && rx.test(e.innerText) && e.getBoundingClientRect().y >= minY); if (!el) return null; const r = el.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2, el.innerText.trim().replace(/\s+/g, ' ').slice(0, 40)]; }, [re.source, re.flags, minY]); if (!c) { log(`miss /${re.source}/`); return false; } await p.mouse.click(c[0], c[1]); log(`clicked "${c[2]}"`); return true; };
const credits = p => p.evaluate(() => { const m = document.body.innerText.match(/Deploy\s+([\d,]+)/); return m ? Number(m[1].replace(/,/g, '')) : 0; });
const closeDialogs = async p => { await p.evaluate(() => document.querySelectorAll('dialog[open]').forEach(d => d.close())); };
const buttons = (p, minY = 0) => p.evaluate(minY => [...document.querySelectorAll('button')].filter(e => e.offsetParent && e.getBoundingClientRect().y >= minY).map(e => (e.id ? e.id + ':' : '') + e.innerText.trim().replace(/\s+/g, ' ').slice(0, 30)), minY);

const A = await open({ width: 1080, height: 1920 });
await A.locator('#host-game').click(); await A.waitForTimeout(4000);
const code = new URL(A.url()).searchParams.get('room'); log('room ' + code);
const B = await open({ width: 960, height: 540 });
await B.locator('input').first().fill(code); await B.getByText('Join game', { exact: false }).first().click(); await B.waitForTimeout(3000);
await A.getByText('Start game', { exact: false }).first().click(); log('started');
await A.waitForTimeout(12000);
await clickSel(A, '#close-army'); await clickSel(A, '#close-map');
await clickText(A, /GOT IT/i).catch(() => {});
const t0 = Date.now(); const T = () => (Date.now() - t0) / 1000;
const until = async s => { while (T() < s) await sleep(200); };

let n = 0;
const cdp = await A.context().newCDPSession(A);
cdp.on('Page.screencastFrame', async ({ data, sessionId }) => {
  try { writeFileSync(`${OUT}/f${String(n).padStart(4, '0')}.jpg`, Buffer.from(data, 'base64')); appendFileSync(`${OUT}/frames.txt`, `${n} ${T().toFixed(3)}\n`); n++; } catch (e) { log('frame err ' + e.message); }
  await cdp.send('Page.screencastFrameAck', { sessionId }).catch(() => {});
});
await cdp.send('Page.startScreencast', { format: 'jpeg', quality: 92, maxWidth: 1080, maxHeight: 1920, everyNthFrame: 1 });

const advanceAll = async (p, flag, x, y) => { await p.keyboard.press('Control+a'); await sleep(300); await clickSel(p, '#objective-' + flag); await sleep(1200); await p.mouse.click(x, y); await sleep(600); await p.keyboard.press('Escape'); };

// Opponent: everything to the centre flag, keep reinforcing, re-issue the push every 20 s.
const driveB = (async () => {
  await advanceAll(B, 'C', 480, 270);
  for (const k of ['2', '2', '1', '1', '3']) { await B.keyboard.press(k); await sleep(400); }
  let i = 0;
  while (T() < SECONDS) { await sleep(20000); await advanceAll(B, ['C', 'D', 'C', 'B'][i++ % 4], 440 + Math.random() * 80, 250 + Math.random() * 40); await B.keyboard.press('2'); await sleep(300); await B.keyboard.press('1'); await closeDialogs(B); }
})();

// Host (recorded)
const driveA = (async () => {
  log('A: overview then advance to E');
  await clickSel(A, '#camera-overview'); await sleep(4000);
  await advanceAll(A, 'E', 540, 900);
  for (const k of ['2', '2', '1', '1', '3']) { await A.keyboard.press(k); await sleep(500); }
  await A.keyboard.press('Space'); for (let i = 0; i < 3; i++) { await clickSel(A, '#camera-zoom-in'); await sleep(400); }
  await until(20); await A.keyboard.press('Space');
  await until(30); log('A: strike enemy side'); await clickSel(A, '#objective-F'); await sleep(1500);
  if (await credits(A) >= 140 && await clickText(A, /^Air strike\s+\d+ points/i, 1500)) { await sleep(800); await A.mouse.click(540, 900); await sleep(1500); }
  await closeDialogs(A); await A.keyboard.press('Space');
  await until(45); log('A: FPV');
  try {
    await clickSel(A, '#catalog-category'); await sleep(2500); await clickText(A, /Drones/i); await sleep(2000);
    await A.keyboard.press('3'); await sleep(300); await A.keyboard.press('3'); log('bought 2 FPV via key 3');
    await until(64);
    await clickSel(A, '#toggle-army'); await sleep(2500);
    const roster = await A.evaluate(() => [...document.querySelectorAll('.roster-card')].map(e => e.id + ':' + e.innerText.trim().replace(/\s+/g, ' ').slice(0, 30)));
    log('roster: ' + JSON.stringify(roster.slice(-6)));
    const fpvCard = await A.evaluate(() => { const el = [...document.querySelectorAll('.roster-card')].find(e => /wasp|fpv/i.test(e.innerText)); if (!el) return null; el.scrollIntoView(); const r = el.getBoundingClientRect(); return [r.x + r.width / 2, r.y + r.height / 2]; });
    if (fpvCard) {
      await A.mouse.click(fpvCard[0], fpvCard[1]); await sleep(2500); log('selected fpv; buttons: ' + JSON.stringify((await buttons(A)).filter(t => !/^roster|^objective|^resource/.test(t))));
      let ok = await clickText(A, /pilot|direct flight|take control|fly/i);
      if (!ok) { await clickText(A, /commands/i); await sleep(2500); log('cmds: ' + JSON.stringify((await buttons(A)).filter(t => !/^roster|^objective|^resource/.test(t)))); ok = await clickText(A, /pilot|direct flight|take control|fly/i); }
      if (ok) {
        await sleep(4000); log('fpv-active: ' + await A.evaluate(() => document.body.classList.contains('fpv-active')));
        await clickSel(A, '#close-army');
        await A.keyboard.down('w'); await sleep(5000); await A.keyboard.press('f'); log('armed');
        for (let i = 0; i < 8; i++) { const k = i % 2 ? 'a' : 'd'; await A.keyboard.down(k); await sleep(600); await A.keyboard.up(k); await sleep(2000); }
        await A.keyboard.down('Control'); await sleep(3000); await A.keyboard.up('Control'); await sleep(8000); await A.keyboard.up('w');
        log('fpv-active after: ' + await A.evaluate(() => document.body.classList.contains('fpv-active')));
        await A.keyboard.press('Escape'); log('exit FPV');
      }
    } else log('no fpv in roster');
    await clickSel(A, '#close-army');
    await clickSel(A, '#catalog-category'); await sleep(2500); await clickText(A, /Quick picks/i); await sleep(1500);
  } catch (e) { log('FPV err ' + e.message.split('\n')[0]); }
  await closeDialogs(A);
  let i = 0;
  while (T() < SECONDS) {
    const flag = ['E', 'D', 'E', 'F'][i++ % 4];
    await advanceAll(A, flag, 500 + Math.random() * 200, 800 + Math.random() * 250);
    await sleep(800); await A.keyboard.press('Space'); await A.keyboard.press('2'); await A.keyboard.press('1'); await closeDialogs(A);
    if (i % 2 === 0 && await credits(A) >= 140) { await clickSel(A, '#objective-' + (i % 4 === 0 ? 'F' : 'E')); await sleep(1500); if (await clickText(A, /^Air strike\s+\d+ points/i, 1500)) { await sleep(800); await A.mouse.click(540 + (Math.random() - .5) * 300, 900 + (Math.random() - .5) * 300); } await sleep(1500); await closeDialogs(A); await A.keyboard.press('Space'); }
    if (i % 3 === 0) await clickSel(A, '#camera-rotate');
    await sleep(14000);
  }
})();
await Promise.all([driveA, driveB]);
await cdp.send('Page.stopScreencast').catch(() => {});
log(`captured ${n} frames over ${T().toFixed(0)}s`);
log('final: ' + await A.evaluate(() => document.body.innerText.replace(/\s+/g, ' ').slice(0, 260)));
await b.close();
