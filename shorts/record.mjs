// Record a browser game with headless Chromium.
// usage: node record.mjs --url <url> --out work/raw --seconds 40 [--width 1080 --height 1920] [--actions ./actions.mjs]
import { chromium } from 'playwright';
import { mkdirSync, renameSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const arg = (k, d) => { const i = process.argv.indexOf('--' + k); return i > -1 ? process.argv[i + 1] : d; };
const url = arg('url'); if (!url) { console.error('need --url'); process.exit(1); }
const out = resolve(arg('out', 'work/raw'));
const seconds = Number(arg('seconds', 40));
const width = Number(arg('width', 1080)), height = Number(arg('height', 1920));
const actionsPath = arg('actions');
mkdirSync(out, { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));

// Default driver: generic "mash the game" input so something happens on screen.
async function defaultActions(page, seconds) {
  const keys = ['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'w', 'a', 's', 'd', 'Space', 'Enter', 'e', 'q'];
  const end = Date.now() + seconds * 1000;
  await page.mouse.click(width / 2, height / 2).catch(() => {});
  let shot = 0;
  while (Date.now() < end) {
    const r = Math.random();
    if (r < 0.4) await page.keyboard.press(keys[(Math.random() * keys.length) | 0]).catch(() => {});
    else if (r < 0.7) await page.mouse.move(Math.random() * width, Math.random() * height, { steps: 5 }).catch(() => {});
    else if (r < 0.9) await page.mouse.click(Math.random() * width, Math.random() * height).catch(() => {});
    else await page.mouse.wheel(0, (Math.random() - 0.5) * 600).catch(() => {});
    if ((Date.now() - (end - seconds * 1000)) / 3000 > shot) {
      await page.screenshot({ path: `${out}/shot-${String(shot).padStart(2, '0')}.png` }).catch(() => {});
      shot++;
    }
    await sleep(80 + Math.random() * 200);
  }
}

const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || (existsSync('/opt/pw-browsers/chromium') ? '/opt/pw-browsers/chromium' : undefined), args: ['--autoplay-policy=no-user-gesture-required', '--use-gl=swiftshader', '--enable-webgl'] });
const context = await browser.newContext({
  viewport: { width, height },
  deviceScaleFactor: 1,
  recordVideo: { dir: out, size: { width, height } },
  userAgent: 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Mobile Safari/537.36',
});
const page = await context.newPage();
page.on('console', m => { if (m.type() === 'error') console.error('[page]', m.text()); });
console.log('loading', url);
await page.goto(url, { waitUntil: 'load', timeout: 60000 });
await page.screenshot({ path: `${out}/shot-load.png` });
await sleep(1500);

const drive = actionsPath ? (await import(pathToFileURL(resolve(actionsPath)).href)).default : defaultActions;
await drive(page, seconds, { width, height, out });

const video = page.video();
await context.close();
const p = await video.path();
const final = `${out}/footage.webm`;
if (existsSync(final)) renameSync(final, `${out}/footage-${Date.now()}.webm`);
renameSync(p, final);
await browser.close();
console.log('wrote', final);
