import { AudioEngine } from './audio.js';
import { Catalog, StaticCatalog } from './catalog.js';
import { Player } from './player.js';
import { Recorder } from './recorder.js';
import { MODES, Sequencer } from './sequencer.js';
import { makeRng, seedToInt } from './prng.js';

const $ = (sel) => document.querySelector(sel);
const params = new URLSearchParams(location.search);
const STATIC = window.CORECORE_STATIC || null;   // set by the exported index.html: path of manifest.json

// The live channel: the seed is derived from the clock in 10-minute windows and every viewer
// fast-forwards to the same point, so everybody watches the same edit at the same moment.
const LIVE_WINDOW_MS = 10 * 60 * 1000;
const liveSeed = () => `live-${Math.floor(Date.now() / LIVE_WINDOW_MS)}`;
const liveElapsed = () => (Date.now() % LIVE_WINDOW_MS) / 1000;
const randomSeed = () => Math.random().toString(36).slice(2, 8);

const ASPECTS = ['16:9', '9:16', '1:1', '2.39:1'];
// A phone: a touch screen whose short side is phone-sized. It gets the vertical frame while held upright,
// and follows the phone as it turns, until a frame is chosen by hand.
const PHONE = matchMedia('(pointer: coarse)').matches && Math.min(screen.width, screen.height) <= 600;
const UPRIGHT = matchMedia('(orientation: portrait)');
const defaultAspect = () => (PHONE && UPRIGHT.matches ? '9:16' : '16:9');
// frame and haze on load: at its fullest on a computer (the small, soft picture); on a phone's small screen
// the picture keeps more of itself, at 0.40
const EDGE_DEFAULT = PHONE ? 0.4 : 0.5;
const CLIPFX = { speaker: 'through computer speakers', phone: 'through a phone', direct: 'direct' };
const PROVIDERS = { archive: 'internet archive', ytdlp: 'yt-dlp', dailymotion: 'dailymotion', reddit: 'reddit', stream: 'a stream', local: 'local files' };

const state = {
  live: params.get('seed') === 'live',
  seed: params.get('seed') === 'live' ? liveSeed() : (params.get('seed') || randomSeed()),
  mode: MODES[params.get('mode')] ? params.get('mode') : 'corecore',
  // The frame belongs to the screen, not the link: a phone always opens in its own (9:16 held upright), whatever
  // an address says, and the address never carries one. On a computer ?aspect= typed in still sets the frame
  // (a projection in scope, say). A frame picked by hand holds for the visit.
  aspect: !PHONE && ASPECTS.includes(params.get('aspect')) ? params.get('aspect') : defaultAspect(),
  aspectChosen: !PHONE && ASPECTS.includes(params.get('aspect')),
  tags: (params.get('tags') || '').split(',').map((t) => t.trim().toLowerCase()).filter(Boolean),
  edge: params.has('edge') ? Math.max(0, Math.min(1, Number(params.get('edge')) || 0)) : EDGE_DEFAULT,
  clipfx: Object.keys(CLIPFX).includes(params.get('clipfx')) ? params.get('clipfx') : 'speaker',
  provider: 'archive',
  started: false,
};

const audio = new AudioEngine();
const catalog = STATIC ? new StaticCatalog({ seed: seedToInt(state.seed), manifestUrl: STATIC, tags: state.tags }) : new Catalog({ seed: seedToInt(state.seed), tags: state.tags });
const sequencer = new Sequencer({ catalog, seed: state.seed, mode: state.mode });
const canvas = $('#stage');
const player = new Player({ canvas, audio, catalog, sequencer, videoHost: $('#videos') });
// ?preroll=1 tries the pre-roll on a computer, ?preroll=0 turns it off on a phone (see the player)
if (params.has('preroll')) player.setPreroll(params.get('preroll') !== '0');
// ?filters=0 draws without canvas filters (as Safari and Firefox do), ?filters=1 with them where the browser has them
if (params.has('filters')) player.setFilters(params.get('filters') !== '0');
const recorder = new Recorder(canvas, audio);
window.corecore = { audio, catalog, sequencer, player, recorder, state, MODES };

// ---- the look: words in brackets, a status line, no toasts -----------------------------------

// A row of words in brackets; the chosen one is lit (role=switch + aria-checked).
function seg(host, items, current, onPick, what) {
  host.innerHTML = '';
  host.setAttribute('role', 'group');
  host.setAttribute('aria-label', what);
  for (const [value, label] of items) {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'switch';
    b.dataset.value = value;
    b.setAttribute('role', 'switch');
    b.setAttribute('aria-checked', String(value === current));
    b.setAttribute('aria-label', `Choose ${label} for ${what}`);
    b.title = `choose ${label} for ${what}`;
    b.textContent = `[ ${label} ]`;
    b.addEventListener('click', () => onPick(value));
    host.appendChild(b);
  }
}
function light(host, value) {
  for (const b of host.querySelectorAll('button')) b.setAttribute('aria-checked', String(b.dataset.value === value));
}
function flip(btn, on) { btn.setAttribute('aria-checked', String(!!on)); }

// A button says what it did, or what it is waiting on, in its own brackets, then goes back to its word.
const words = new WeakMap();
function say(btn, text, ms = 1800) {
  if (!btn) return;
  if (!words.has(btn)) words.set(btn, { text: btn.textContent, timer: null });
  const w = words.get(btn);
  clearTimeout(w.timer);
  btn.textContent = `[ ${text} ]`;
  if (ms > 0) w.timer = setTimeout(() => { btn.textContent = w.text; }, ms);
}
function rename(btn, text, label) {   // a lasting change of word, e.g. record -> stop recording, with its sentence
  const w = words.get(btn) || { text: '', timer: null };
  clearTimeout(w.timer);
  w.text = `[ ${text} ]`;
  words.set(btn, w);
  btn.textContent = w.text;
  if (label) { btn.setAttribute('aria-label', label); btn.title = label.toLowerCase(); }
}

// The status line at the top of the controls: mode · seed · what is happening, fields separated by
// middle dots. The viewer itself carries no text; a key pressed with the controls hidden is simply obeyed.
let note = '', noteTimer = null;
function status(msg, ms = 2400) {
  note = msg;
  clearTimeout(noteTimer);
  if (ms > 0) noteTimer = setTimeout(() => { note = ''; drawStatus(); }, ms);
  drawStatus();
}
function drawStatus() {
  const f = [MODES[state.mode].label.toLowerCase().replace(/\s*\(.*?\)/g, ''), state.live ? 'the live channel' : `seed ${state.seed}`];
  if (state.tags.length) f.push(`only ${state.tags.join(', ')}`);
  if (!state.started) f.push('waiting');
  else if (player.paused) f.push('paused');
  if (recorder.active) f.push('recording');
  if (note) f.push(note);
  const el = $('#status'), text = f.join(' · ');
  if (el.textContent !== text) el.textContent = text;   // only a change is announced
}

function setHud(open) { $('#hud').classList.toggle('hidden', !open); }

// Every button carries its sentence as a title too, lowercased, as the look has it.
function entitle(root = document) {
  for (const b of root.querySelectorAll('button[aria-label]')) if (!b.title) b.title = b.getAttribute('aria-label').toLowerCase();
}

// The page: 'light' is off-white, the default; 'dark' a black screen; 'system' follows the device.
// The picture's field follows along, so a cut to black becomes a cut to the page.
const fieldOf = (t) => (t === 'system' ? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light') : t);
function setTheme(t) {
  if (t === 'system') delete document.documentElement.dataset.theme;
  else document.documentElement.dataset.theme = t;
  try { localStorage.setItem('corecore.theme', t); } catch (e) { /* private mode */ }
  for (const [id, v] of [['#tLight', 'light'], ['#tDark', 'dark'], ['#tSys', 'system']]) flip($(id), v === t);
  player.setField(fieldOf(t));
  // theme-color in the head stays #121212 whatever the page, as the look has it
}

function syncUrl() {
  const p = new URLSearchParams({ seed: state.live ? 'live' : state.seed, mode: state.mode });
  if (state.tags.length) p.set('tags', state.tags.join(','));
  if (state.edge !== EDGE_DEFAULT) p.set('edge', String(state.edge));
  if (state.clipfx !== 'speaker') p.set('clipfx', state.clipfx);
  history.replaceState(null, '', `?${p}`);
}

// ---- the stream -------------------------------------------------------------------------------

// The desk, balanced as the mode has it; the only sound there is.
function applyMusic() {
  if (!state.started) return;
  audio.startGenerated(MODES[state.mode].music, makeRng(`${state.seed}:music`));
}

function setMode(name) {
  state.mode = name;
  sequencer.setMode(name);
  light($('#modes'), name);
  $('#modeBlurb').textContent = MODES[name].blurb;
  if (state.started) {
    player.flush();
    applyMusic();
  }
  syncUrl();
  status('', 0);
}

function setSeed(seed, { live = false } = {}) {
  state.live = live;
  state.seed = seed;
  $('#seed').value = live ? 'live' : seed;
  flip($('#live'), live);
  syncUrl();
  status(live ? 'everyone sees this edit right now' : 'a new stream', 2400);
  // the old stream fades out; under the second of silence that follows, the new one is seeded and its desk
  // started, then it fades in
  const swap = () => {
    sequencer.reseed(seed);
    catalog.seed = seedToInt(seed);
    player.snapEnabled = !live;
    if (state.started) applyMusic();
  };
  if (!state.started) { swap(); return; }
  player.transition({ fastForward: live ? liveElapsed : 0, swap });
}

function goLive() { setSeed(liveSeed(), { live: true }); }

function checkLive() {
  if (state.live && state.started && liveSeed() !== state.seed) setSeed(liveSeed(), { live: true });
}

function setAspect(a, { chosen = true } = {}) {
  state.aspect = a;
  state.aspectChosen = state.aspectChosen || chosen;
  light($('#aspects'), a);
  player.setAspect(a);
  syncUrl();
  status(a, 1600);
}

function togglePause() {
  if (!state.started) return;
  if (player.paused) player.resume(); else player.pause();
  rename($('#pause'), player.paused ? 'play' : 'pause', player.paused ? 'Play the stream again' : 'Pause the stream');
  status('', 0);
}

function setClipFx(v) {
  state.clipfx = v;
  light($('#clipfxs'), v);
  audio.setClipVoicing(v);
  syncUrl();
}

// ---- the pool ---------------------------------------------------------------------------------

async function refreshStats() {
  try {
    const s = await catalog.refreshStats();
    const tags = Object.entries(s.tags || {}).slice(0, 14).map(([t, n]) => `${t} ${n}`).join(' · ');
    $('#stats').textContent = `${s.clips} clips · ${s.sources} sources · ${Math.round(s.seconds / 60)} min · ${s.with_audio} with sound`;
    $('#tags').textContent = tags || 'no tags yet';
    $('#empty').classList.toggle('hidden', s.clips > 0);
    if (STATIC && catalog.manifest && !$('#credits').dataset.filled) fillCredits();
  } catch (e) {
    $('#stats').textContent = STATIC ? 'the manifest would not load' : 'the server is not answering';
  }
}

function fillCredits() {
  const m = catalog.manifest;
  const built = m.built_at ? new Date(m.built_at).toLocaleDateString() : '';
  $('#staticNote').textContent = `a static edition built ${built}: ${m.clips.length} clips from ${m.sources.length} public-domain and open-licence sources, re-scraped by the build pipeline. run it locally to scrape more.`;
  $('#staticNote').classList.remove('hidden');
  const ul = $('#credits ul');
  ul.innerHTML = '';
  for (const s of m.sources) {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = s.url;
    a.target = '_blank';
    a.rel = 'noopener';
    a.textContent = (s.title || s.url).toLowerCase();
    li.appendChild(a);
    if (s.uploader) li.appendChild(document.createTextNode(` · ${String(s.uploader).toLowerCase()}`));
    if (s.license) li.appendChild(document.createTextNode(` · ${s.license.replace(/^https?:\/\/(www\.)?/, '')}`));
    ul.appendChild(li);
  }
  $('#credits').classList.remove('hidden');
  $('#credits').dataset.filled = '1';
}

async function refreshJobs() {
  if (STATIC) return;
  try {
    const r = await fetch('api/jobs?limit=12');
    const j = await r.json();
    const list = $('#jobs');
    list.innerHTML = '';
    for (const job of j.jobs) {
      const li = document.createElement('li');
      li.className = `job ${job.status}`;
      const pct = Math.round((job.progress || 0) * 100);
      const target = job.query || job.url || '(inbox)';
      li.innerHTML = `<span class="st">${job.status}</span> · <b>${escapeHtml(job.provider)}</b> · ${escapeHtml(target)} · `
        + `<span class="pct">${pct}%</span> <span class="msg">${escapeHtml(String(job.message || '').toLowerCase())}</span>`
        + (job.clips_added ? ` · <i>${job.clips_added} clips</i>` : '')
        + (['queued', 'running'].includes(job.status) ? ` <button type="button" class="act" data-cancel="${job.id}" aria-label="Cancel this job" title="cancel this job">[ cancel ]</button>` : '');
      list.appendChild(li);
    }
    const active = j.jobs.some((x) => ['queued', 'running'].includes(x.status));
    if (active) refreshStats();
  } catch (e) { /* ignore */ }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

async function submitJob(ev) {
  ev.preventDefault();
  const btn = $('#jobForm button[type="submit"]');
  const query = $('#query').value.trim();
  const isUrl = /^https?:\/\//.test(query);
  const body = {
    provider: state.provider,
    query: isUrl ? null : query || null,
    url: isUrl ? query : null,
    max_items: Number($('#maxItems').value) || 5,
    tags: $('#jobTags').value,
  };
  say(btn, 'queueing', 0);
  try {
    const r = await fetch('api/jobs', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
    const j = await r.json();
    say(btn, r.ok ? 'queued' : `scrape — ${String(j.detail || r.status).toLowerCase()}`, r.ok ? 1800 : 5000);
    if (r.ok) $('#query').value = '';
  } catch (e) {
    say(btn, 'scrape — the server is not answering', 5000);
  }
  refreshJobs();
}

async function seedStarter(btn, set) {
  say(btn, 'queueing', 0);
  try {
    const r = await fetch(`api/seed?set=${encodeURIComponent(set)}`, { method: 'POST' });
    const j = await r.json();
    say(btn, r.ok ? `queued ${j.queued.length} jobs` : `the ${set} set — ${String(j.detail || r.status).toLowerCase()}`, r.ok ? 2400 : 5000);
  } catch (e) {
    say(btn, `the ${set} set — the server is not answering`, 5000);
  }
  refreshJobs();
}

// ---- acts -------------------------------------------------------------------------------------

async function toggleRecord() {
  const btn = $('#record');
  if (!state.started) { say(btn, 'begin first'); status('begin first'); return; }
  if (recorder.active) {
    say(btn, 'saving', 0);
    const blob = await recorder.stop();
    if (blob) recorder.download(blob, `absolute-clarity-${state.mode}-${state.seed}-${Date.now()}.webm`);
    rename(btn, 'record', 'Record what you see and hear to a file');
    say(btn, 'saved a webm', 2400);
    status('saved a webm');
  } else {
    recorder.start();
    rename(btn, 'stop recording', 'Stop the recording and save it');
    status('', 0);
  }
}

function toggleFullscreen() {
  if (!document.fullscreenEnabled) { say($('#fullscreen'), 'fullscreen — not on this device', 4000); return; }
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen().catch(() => say($('#fullscreen'), 'fullscreen — refused', 4000));
}

async function banCurrent(btn) {
  const id = await player.banCurrent();
  if (btn) say(btn, id ? 'banned' : 'nothing to ban');
  else status(id ? 'banned that clip' : 'nothing to ban');
}

function setInfo(on) {
  player.showInfo = on;
  flip($('#info'), on);
}

async function start() {
  if (state.started) return;
  state.started = true;
  $('#splash').classList.add('hidden');
  await audio.init();
  audio.setVolume(Number($('#volume').value));
  audio.onOnset((s) => player.onOnset(s));
  await applyMusic();
  await refreshStats();
  player.snapEnabled = !state.live;
  drawStatus();
  await player.start({ fastForward: state.live ? liveElapsed() : 0 });
}

// ---- wiring ---------------------------------------------------------------------------------

function wire() {
  if (STATIC) document.body.classList.add('static');
  let theme = 'light';
  try { theme = localStorage.getItem('corecore.theme') || 'light'; } catch (e) { /* ignore */ }
  setTheme(['dark', 'light', 'system'].includes(theme) ? theme : 'light');
  matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => { if (!document.documentElement.dataset.theme) player.setField(fieldOf('system')); });
  $('#tDark').addEventListener('click', () => setTheme('dark'));
  $('#tLight').addEventListener('click', () => setTheme('light'));
  $('#tSys').addEventListener('click', () => setTheme('system'));

  seg($('#modes'), Object.entries(MODES).map(([k, m]) => [k, m.label.toLowerCase().replace(/\s*\(.*?\)/g, '')]), state.mode, setMode, 'the mode');
  $('#modeBlurb').textContent = MODES[state.mode].blurb;
  seg($('#aspects'), ASPECTS.map((a) => [a, a]), state.aspect, setAspect, 'the frame');
  seg($('#clipfxs'), Object.entries(CLIPFX), state.clipfx, setClipFx, 'the clip sound');
  seg($('#providers'), Object.entries(PROVIDERS), state.provider, (v) => { state.provider = v; light($('#providers'), v); }, 'the source');
  entitle();

  $('#seed').value = state.live ? 'live' : state.seed;
  flip($('#live'), state.live);
  $('#poolTags').value = state.tags.join(', ');
  $('#poolTags').addEventListener('change', async (e) => {
    state.tags = e.target.value.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean);
    catalog.setTags(state.tags);
    await refreshStats();
    if (state.started) player.restart(state.live ? liveElapsed() : 0);
    syncUrl();
    drawStatus();
  });
  $('#edge').value = String(state.edge);
  $('#edgeV').textContent = state.edge.toFixed(2);
  player.setEdge(state.edge);
  $('#edge').addEventListener('input', (e) => { state.edge = Number(e.target.value); $('#edgeV').textContent = state.edge.toFixed(2); player.setEdge(state.edge); syncUrl(); });
  $('#volumeV').textContent = Number($('#volume').value).toFixed(2);
  $('#volume').addEventListener('input', (e) => { $('#volumeV').textContent = Number(e.target.value).toFixed(2); audio.setVolume(Number(e.target.value)); });
  audio.clipVoicing = state.clipfx;
  player.setAspect(state.aspect);
  syncUrl();

  $('#start').addEventListener('click', start);
  // a tap or click on the picture opens and closes the controls: the viewer carries no text, so this is
  // the way in on a phone, which has no keys
  canvas.addEventListener('click', () => { if (state.started) setHud($('#hud').classList.contains('hidden')); });
  if (PHONE) UPRIGHT.addEventListener('change', () => { if (!state.aspectChosen) setAspect(defaultAspect(), { chosen: false }); });
  if (matchMedia('(pointer: coarse)').matches) $('#hint').textContent = 'tap the picture for the controls. sound on.';
  $('#pause').addEventListener('click', togglePause);
  $('#splash').addEventListener('click', (e) => { if (e.target.id !== 'start') start(); });
  $('#reseed').addEventListener('click', () => setSeed(randomSeed()));
  $('#live').addEventListener('click', () => (state.live ? setSeed(randomSeed()) : goLive()));
  $('#seed').addEventListener('change', (e) => { const v = e.target.value.trim(); v === 'live' ? goLive() : setSeed(v || 'corecore'); });
  $('#customText').addEventListener('input', (e) => {
    sequencer.customText = e.target.value.split('\n').map((s) => s.trim()).filter(Boolean);
    try { localStorage.setItem('corecore.text', e.target.value); } catch (err) { /* private mode */ }
  });
  try {
    const saved = localStorage.getItem('corecore.text');
    if (saved) { $('#customText').value = saved; sequencer.customText = saved.split('\n').map((s) => s.trim()).filter(Boolean); }
  } catch (err) { /* ignore */ }
  $('#record').addEventListener('click', toggleRecord);
  $('#fullscreen').addEventListener('click', toggleFullscreen);
  document.addEventListener('fullscreenchange', () => rename($('#fullscreen'), document.fullscreenElement ? 'leave fullscreen' : 'fullscreen', document.fullscreenElement ? 'Leave fullscreen' : 'Fill the screen'));
  $('#credits').addEventListener('toggle', (e) => { $('#credits summary').textContent = e.target.open ? '[ hide the sources ]' : '[ sources and credits ]'; });
  // a button clicked with a pointer gives focus back, so space still pauses afterwards
  document.addEventListener('click', (e) => { const b = e.target.closest('button'); if (b && e.detail > 0) b.blur(); });
  $('#next').addEventListener('click', () => { player.nextPhrase(); say($('#next'), 'next'); });
  $('#ban').addEventListener('click', () => banCurrent($('#ban')));
  $('#copyBans').addEventListener('click', async (e) => {
    const btn = e.currentTarget;   // gone from the event once we have awaited
    const lines = catalog.banLines();
    if (lines === null) return say(btn, 'bans here go straight into the pool', 4000);
    if (!lines.length) return say(btn, 'no bans yet');
    const text = `# bans from ${location.host}, ${new Date().toISOString().slice(0, 10)}\n${lines.join('\n')}\n`;
    try { await navigator.clipboard.writeText(text); say(btn, `${lines.length} copied, for bans.txt`, 4000); } catch (err) { window.prompt('your bans, for bans.txt', text); }
  });
  $('#info').addEventListener('click', () => setInfo(!player.showInfo));
  $('#hideHud').addEventListener('click', () => setHud(false));
  $('#jobForm').addEventListener('submit', submitJob);
  $('#seedStarter').addEventListener('click', (e) => seedStarter(e.currentTarget, 'contemporary'));
  $('#seedBeauty').addEventListener('click', (e) => seedStarter(e.currentTarget, 'beauty'));
  $('#seedArchival').addEventListener('click', (e) => seedStarter(e.currentTarget, 'archival'));
  $('#jobs').addEventListener('click', async (e) => {
    const id = e.target.dataset.cancel;
    if (id) { say(e.target, 'cancelling', 0); await fetch(`api/jobs/${id}/cancel`, { method: 'POST' }); refreshJobs(); }
  });
  $('#copyLink').addEventListener('click', async (e) => {
    const btn = e.currentTarget;   // gone from the event once we have awaited
    try { await navigator.clipboard.writeText(location.href); say(btn, 'the link is copied'); } catch (err) { say(btn, 'share — copy the address bar', 5000); }
  });

  player.on('warn', (m) => console.warn(m));
  player.on('cue', (c) => {
    if (c.kind === 'clip') {
      const t = c.clip.source_title ? `${c.clip.source_title}${c.clip.source_uploader ? ' · ' + c.clip.source_uploader : ''}` : '';
      $('#nowPlaying').textContent = t.toLowerCase();
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, textarea, select')) return;
    const k = e.key.toLowerCase();
    if ((k === ' ' || k === 'enter') && e.target.matches('button, summary, a')) return;   // the focused control takes it
    if (!state.started && (k === ' ' || k === 'enter')) { start(); return; }
    if (k === ' ') { e.preventDefault(); togglePause(); }
    else if (k === 'n') { player.nextPhrase(); status('next phrase', 1200); }
    else if (k === '.') player.skip();
    else if (k === 'h') setHud($('#hud').classList.contains('hidden'));
    else if (k === 'i') setInfo(!player.showInfo);
    else if (k === 'f') toggleFullscreen();
    else if (k === 'r') toggleRecord();
    else if (k === 's') setSeed(randomSeed());
    else if (k === 'l') goLive();
    else if (k === 'x') banCurrent(null);
    else if (k === 'v') setAspect(ASPECTS[(ASPECTS.indexOf(state.aspect) + 1) % ASPECTS.length]);
    else if (k === 'm') { const keys = Object.keys(MODES); setMode(keys[(keys.indexOf(state.mode) + 1) % keys.length]); }
  });

  drawStatus();
  refreshStats();
  refreshJobs();
  setInterval(refreshJobs, 2500);
  setInterval(refreshStats, 15000);
  setInterval(checkLive, 5000);
}

wire();
