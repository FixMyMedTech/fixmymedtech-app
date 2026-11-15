#!/usr/bin/env node
// scripts/docs_screenshots.js — screenshots for the user guides (docs/).
//
// Logs in as the seeded accounts (scripts/seed_test_data.py, password
// Pass123!) and saves one PNG per shot into docs/docs/images/guide/, in
// English (<name>.png) and French (<name>.fr.png). The French files are
// picked up by the mkdocs-static-i18n plugin on the French pages.
//
//   node scripts/docs_screenshots.js                 # app at http://localhost:8890
//   BASE_URL=http://localhost:8888 node scripts/docs_screenshots.js
//   node scripts/docs_screenshots.js --only=dashboard,qr-page   # some shots
//   node scripts/docs_screenshots.js --lang=en                  # one language
//   node scripts/docs_screenshots.js --seed-demo     # first create the demo call
//
// --seed-demo creates, once, a "Call an engineer" request on the seeded
// Ultrasound at Mulago (as admin@mulago.org) and a visit offer on it (as
// eng@mulago.org), so the call, request and fault screens are not empty.
// It skips both when they already exist.
//
// Needs Playwright with Chromium (require('playwright')). No other package.

const path = require('path');
const { execFileSync } = require('child_process');
const fs = require('fs');
const { chromium } = require('playwright');

const BASE = (process.env.BASE_URL || 'http://localhost:8890').replace(/\/$/, '');
const OUT = path.join(__dirname, '..', 'docs', 'docs', 'images', 'guide');
const PASSWORD = process.env.SEED_PASSWORD || 'Pass123!';
const args = Object.fromEntries(process.argv.slice(2).map(a => {
  const [k, v] = a.replace(/^--/, '').split('=');
  return [k, v === undefined ? true : v];
}));
const ONLY = args.only ? new Set(String(args.only).split(',')) : null;
const LANGS = args.lang ? String(args.lang).split(',') : ['en', 'fr'];

// Seeded ids (scripts/seed_test_data.py).
const MULAGO = '00000000-0000-0000-0000-000000000001';
const ACCOUNTS = {
  engineer: 'eng759585@fmt-demo.org',     // quests done, has clinics (scripts/walk_onboarding.py)
  engineer_mulago: 'eng@mulago.org',      // responsible engineer at Mulago: gets its requests
  clinic_admin: 'admin@mulago.org',
  nurse: 'nurse@mulago.org',
  lead: 'tech@mulago.org',                // Community Builder lead
  visitor: 'visitor@fmt-demo.org',        // welcome quests not done
  host: 'host@fmt-demo.org',              // talk host
};

const PHONE = 390;
const DESKTOP = 1280;

// One entry per screenshot. `as` is a key of ACCOUNTS (or 'anon'), `path` a
// page or a function of the discovered ids, `width` the viewport width.
// `clip`: crop {y, height} in CSS pixels from the top of the page; `el`: a
// CSS selector to screenshot alone; `act`: an action before the shot.
const SHOTS = [
  // Start here
  { name: 'home-doors', as: 'engineer', path: '/home', width: DESKTOP, clip: { y: 0, height: 580 } },
  { name: 'phone-worlds', as: 'engineer', path: '/dashboard', width: PHONE },
  { name: 'visitor-start', as: 'visitor', path: '/community/start', width: PHONE },
  { name: 'visitor-quests', as: 'visitor', path: '/community/start/quests', width: PHONE },
  { name: 'clinic-menu', as: 'clinic_admin', path: '/home', width: DESKTOP, clip: { y: 0, height: 560 } },
  // Clinics
  { name: 'clinic-signup', as: 'anon', path: '/clinic/signup', width: PHONE },
  { name: 'clinic-setup-find', as: 'clinic_admin', path: '/clinic/setup?q=Douala', width: PHONE, clip: { y: 0, height: 410 } },
  { name: 'clinic-setup-talk', as: 'clinic_admin', path: `/clinic/setup/talk?org=${MULAGO}`, width: PHONE },
  { name: 'clinic-engineers', as: 'clinic_admin', path: `/groups/${MULAGO}/engineers`, width: DESKTOP, clip: { y: 0, height: 640 } },
  { name: 'clinic-privacy', as: 'clinic_admin', path: `/groups/${MULAGO}/privacy`, width: DESKTOP, clip: { y: 0, height: 640 } },
  { name: 'groups', as: 'clinic_admin', path: '/groups', width: DESKTOP, clip: { y: 0, height: 480 } },
  { name: 'group-members', as: 'clinic_admin', path: `/groups/${MULAGO}`, width: DESKTOP, full: true, maxHeight: 1100 },
  { name: 'dashboard', as: 'clinic_admin', path: '/dashboard', width: DESKTOP, full: true, maxHeight: 1250 },
  { name: 'devices-list', as: 'clinic_admin', path: '/devices', width: DESKTOP, clip: { y: 0, height: 700 } },
  { name: 'device-page', as: 'nurse', path: ids => `/device/${ids.ultrasound}`, width: PHONE },
  { name: 'device-qr', as: 'clinic_admin', path: ids => `/device/${ids.ultrasound}`, width: PHONE,
    act: async p => { await p.click('text=Show QR').catch(() => p.evaluate(() => window.showDeviceQR && window.showDeviceQR())); await p.waitForTimeout(800); } },
  { name: 'qr-page', as: 'anon', path: ids => `/d/${ids.ecg}`, width: PHONE },
  { name: 'report-fault', as: 'nurse', path: ids => `/d/${ids.ecg}/report`, width: PHONE, full: true, maxHeight: 1500 },
  { name: 'call-form', as: 'clinic_admin', path: ids => `/d/${ids.oxygen}/call`, width: PHONE, full: true, maxHeight: 1300 },
  { name: 'call-offers', as: 'clinic_admin', path: ids => ids.call ? `/calls/${ids.call}` : null, width: PHONE, full: true, maxHeight: 1700 },
  { name: 'fault-detail', as: 'clinic_admin', path: ids => ids.call ? `/device/${ids.ultrasound}/fault/${ids.call}` : null, width: DESKTOP, full: true, maxHeight: 1300 },
  { name: 'faults-list', as: 'clinic_admin', path: '/faults', width: DESKTOP, clip: { y: 0, height: 520 } },
  { name: 'register-scan', as: 'engineer', path: '/new_device', width: PHONE },
  { name: 'register-step1', as: 'engineer', path: '/device/3f6c2a1e-9b7d-4c2e-8a1f-0d5e6b7c8a90/new', width: PHONE, full: true, maxHeight: 1400 },
  { name: 'register-locked', as: 'host', path: '/new_device', width: PHONE },
  { name: 'device-edit-docs', as: 'clinic_admin', path: ids => `/devices/${ids.ecg}/edit`, width: PHONE, el: '#documents',
    act: async p => { await p.evaluate(() => document.querySelectorAll('#documents details').forEach(d => { d.open = true; })); } },
  { name: 'library', as: 'nurse', path: '/library?q=Philips', width: DESKTOP, clip: { y: 0, height: 760 } },
  // Engineers
  { name: 'invite-clinic', as: 'engineer', path: '/invite-clinic', width: DESKTOP, full: true, maxHeight: 1100 },
  { name: 'tasks', as: 'engineer_mulago', path: '/tasks', width: PHONE, full: true, maxHeight: 1400 },
  { name: 'requests', as: 'engineer_mulago', path: '/requests', width: PHONE, full: true, maxHeight: 1400 },
  { name: 'request-offer', as: 'engineer_mulago', path: ids => ids.call ? `/requests/${ids.call}` : null, width: PHONE, full: true, maxHeight: 1700 },
  { name: 'devices-by-clinic', as: 'engineer', path: '/devices?status=&view=clinics', width: DESKTOP, clip: { y: 0, height: 640 } },
  { name: 'spare-part', as: 'engineer', path: ids => ids.engineerDevice ? `/device/${ids.engineerDevice}/spare-part` : null, width: PHONE, full: true, maxHeight: 1500 },
  // Community
  { name: 'host', as: 'host', path: '/host', width: DESKTOP, full: true, maxHeight: 1100 },
  { name: 'to-validate', as: 'lead', path: '/lead', width: DESKTOP, full: true, maxHeight: 900 },
  { name: 'community-admin', as: 'lead', path: '/community/admin/applicants', width: DESKTOP, clip: { y: 0, height: 620 } },
  { name: 'achievements-map', as: 'engineer', path: '/community/achievements', width: DESKTOP, clip: { y: 0, height: 760 } },
  { name: 'task-board', as: 'engineer', path: '/community/tasks', width: DESKTOP, full: true, maxHeight: 1000 },
  { name: 'claims', as: 'engineer', path: '/community/claims', width: PHONE, full: true, maxHeight: 1500 },
  { name: 'network', as: 'engineer', path: '/network', width: DESKTOP, clip: { y: 0, height: 640 } },
  { name: 'profile', as: 'visitor', path: '/profile', width: PHONE, full: true, maxHeight: 1500 },
];

async function login(ctx, who) {
  const page = await ctx.newPage();
  if (who !== 'anon') {
    await page.goto(`${BASE}/login`);
    await page.fill('#email', ACCOUNTS[who]);
    await page.fill('#password', PASSWORD);
    await Promise.all([page.waitForLoadState('networkidle'), page.click('button[type=submit]')]);
    if (page.url().includes('/login')) throw new Error(`login failed for ${ACCOUNTS[who]}`);
  }
  return page;
}

async function setLang(page, lang) {
  await page.request.post(`${BASE}/lang`, { form: { lang } });
}

async function hrefs(page, pattern) {
  return page.evaluate(re => [...document.querySelectorAll('a[href]')]
    .map(a => a.getAttribute('href')).filter(h => new RegExp(re).test(h)), pattern);
}

// Device ids from the clinic's device list, by name; the demo call from the
// Ultrasound page; one device the engineer can see.
async function discover(browser) {
  const ids = {};
  const ctx = await browser.newContext();
  const page = await login(ctx, 'clinic_admin');
  await page.goto(`${BASE}/devices`, { waitUntil: 'networkidle' });
  const rows = await page.evaluate(() => [...document.querySelectorAll('a[href^="/device/"]')]
    .map(a => [a.innerText.trim(), a.getAttribute('href').split('/')[2]]));
  for (const [text, id] of rows) {
    if (/Ultrasound/i.test(text)) ids.ultrasound = id;
    if (/ECG/i.test(text)) ids.ecg = id;
    if (/Oxygen/i.test(text)) ids.oxygen = id;
  }
  if (ids.ultrasound) {
    await page.goto(`${BASE}/device/${ids.ultrasound}`, { waitUntil: 'networkidle' });
    const calls = await hrefs(page, '^/calls/[0-9a-f-]{36}$');
    const faults = await hrefs(page, `^/device/${ids.ultrasound}/fault/[0-9a-f-]{36}$`);
    ids.call = (calls[0] || faults[0] || '').split('/').pop() || null;
  }
  await ctx.close();
  const ctx2 = await browser.newContext();
  const eng = await login(ctx2, 'engineer');
  await eng.goto(`${BASE}/devices`, { waitUntil: 'networkidle' });
  ids.engineerDevice = ((await hrefs(eng, '^/device/[0-9a-f-]{36}$'))[0] || '').split('/').pop() || null;
  await ctx2.close();
  return ids;
}

async function seedDemo(browser, ids) {
  if (!ids.ultrasound) { console.log('seed: no Ultrasound device found, skipped'); return; }
  if (!ids.call) {
    const ctx = await browser.newContext();
    const page = await login(ctx, 'clinic_admin');
    await page.goto(`${BASE}/d/${ids.ultrasound}/call`, { waitUntil: 'networkidle' });
    await page.fill('textarea[name=description]', 'The screen stays black after start-up.');
    // The radio itself is visually hidden behind its label.
    await page.evaluate(() => { document.querySelector('input[name=urgency][value=this_week]').checked = true; });
    await Promise.all([page.waitForLoadState('networkidle'), page.click('form[action$="/call"] button[type=submit]')]);
    ids.call = page.url().split('/').pop().split('?')[0];
    console.log('seed: call started', ids.call);
    await ctx.close();
  }
  const ctx = await browser.newContext();
  const eng = await login(ctx, 'engineer_mulago');
  await eng.goto(`${BASE}/requests/${ids.call}`, { waitUntil: 'networkidle' });
  if (await eng.$('input[name=visit_fee]')) {
    const t = new Date(Date.now() + 26 * 3600e3);
    t.setMinutes(0);
    const pad = n => String(n).padStart(2, '0');
    await eng.fill('input[name=visit_fee]', '15000');
    await eng.fill('input[name=arrival_at]', `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}T${pad(t.getHours())}:00`);
    const note = await eng.$('[name=note]');
    if (note) await note.fill('I bring a spare fuse.');
    await Promise.all([eng.waitForLoadState('networkidle'), eng.click('form[action$="/offer"] button[type=submit]')]);
    console.log('seed: offer sent');
  } else {
    console.log('seed: offer already there (or this engineer was not told)');
  }
  await ctx.close();
}

async function shoot(browser, shot, lang, ids) {
  const target = typeof shot.path === 'function' ? shot.path(ids) : shot.path;
  if (!target) { console.log(`skip ${shot.name}: needs demo data (run with --seed-demo)`); return; }
  const height = shot.width < 600 ? 844 : 860;
  const ctx = await browser.newContext({ viewport: { width: shot.width, height }, deviceScaleFactor: 2 });
  const page = await login(ctx, shot.as);
  await setLang(page, lang);
  await page.goto(BASE + target, { waitUntil: 'networkidle' });
  if (shot.act) await shot.act(page);
  // The floating "?" help button covers content in crops; hide it.
  await page.addStyleTag({ content: '#fb-btn,.fb-btn,.fb-menu{display:none!important}' }).catch(() => {});
  const file = path.join(OUT, lang === 'en' ? `${shot.name}.png` : `${shot.name}.${lang}.png`);
  if (shot.el) {
    const el = await page.$(shot.el);
    if (el) { await el.screenshot({ path: file }); await ctx.close(); return report(file); }
    if (!shot.fallbackFull) { console.log(`skip ${shot.name}: ${shot.el} not found`); await ctx.close(); return; }
  }
  if (shot.clip) {
    await page.screenshot({ path: file, clip: { x: 0, y: shot.clip.y, width: shot.width, height: shot.clip.height } });
  } else if (shot.full || shot.fallbackFull) {
    const full = await page.evaluate(() => document.documentElement.scrollHeight);
    const h = Math.min(full, shot.maxHeight || 1400);
    await page.setViewportSize({ width: shot.width, height: Math.max(h, height) });
    await page.screenshot({ path: file, clip: { x: 0, y: 0, width: shot.width, height: h } });
  } else {
    await page.screenshot({ path: file });
  }
  await ctx.close();
  report(file);
}

// Screenshots at 2x are large; when python3 with Pillow is there, reduce
// each PNG to 256 colours (about a third of the size, no visible loss on UI).
const SHRINK = `
import sys
from PIL import Image
f = sys.argv[1]
Image.open(f).convert("RGB").quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).save(f, optimize=True)
`;
function shrink(file) {
  if (args['no-shrink']) return;
  try { execFileSync('python3', ['-I', '-c', SHRINK, file], { stdio: 'ignore' }); } catch (e) { /* keep the full PNG */ }
}

function report(file) {
  shrink(file);
  console.log(`saved ${path.relative(process.cwd(), file)} (${Math.round(fs.statSync(file).size / 1024)} KB)`);
}

(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch();
  try {
    const ids = await discover(browser);
    if (args['seed-demo']) await seedDemo(browser, ids);
    console.log('ids', JSON.stringify(ids));
    for (const shot of SHOTS) {
      if (ONLY && !ONLY.has(shot.name)) continue;
      for (const lang of LANGS) {
        try { await shoot(browser, shot, lang, ids); }
        catch (e) { console.log(`FAILED ${shot.name} (${lang}): ${e.message.split('\n')[0]}`); }
      }
    }
  } finally {
    await browser.close();
  }
})();
