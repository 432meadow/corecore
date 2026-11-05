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

const state = {
  live: params.get('seed') === 'live',
  seed: params.get('seed') === 'live' ? liveSeed() : (params.get('seed') || randomSeed()),
  mode: MODES[params.get('mode')] ? params.get('mode') : 'corecore',
  aspect: ['16:9', '9:16', '1:1', '2.39:1'].includes(params.get('aspect')) ? params.get('aspect') : '16:9',
  music: params.get('music') || 'generated',
  tags: (params.get('tags') || '').split(',').map((t) => t.trim().toLowerCase()).filter(Boolean),
  edge: params.has('edge') ? Math.max(0, Math.min(1, Number(params.get('edge')) || 0)) : 0.6,
  slowed: params.get('slowed') === '1',
  started: false,
};

const audio = new AudioEngine();
const catalog = STATIC ? new StaticCatalog({ seed: seedToInt(state.seed), manifestUrl: STATIC, tags: state.tags }) : new Catalog({ seed: seedToInt(state.seed), tags: state.tags });
const sequencer = new Sequencer({ catalog, seed: state.seed, mode: state.mode });
const canvas = $('#stage');
const player = new Player({ canvas, audio, catalog, sequencer, videoHost: $('#videos') });
const recorder = new Recorder(canvas, audio);
window.corecore = { audio, catalog, sequencer, player, recorder, state, MODES };

// ---- HUD ------------------------------------------------------------------------------------

const toastEl = $('#toast');
let toastTimer = null;
function toast(msg, ms = 2200) {
  toastEl.textContent = msg;
  toastEl.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toastEl.classList.remove('show'), ms);
}

function syncUrl() {
  const p = new URLSearchParams({ seed: state.live ? 'live' : state.seed, mode: state.mode, aspect: state.aspect, music: state.music });
  if (state.slowed) p.set('slowed', '1');
  if (state.tags.length) p.set('tags', state.tags.join(','));
  if (state.edge !== 0.6) p.set('edge', String(state.edge));
  history.replaceState(null, '', `?${p}`);
}

function fillModes() {
  const sel = $('#mode');
  sel.innerHTML = '';
  for (const [k, m] of Object.entries(MODES)) {
    const o = document.createElement('option');
    o.value = k;
    o.textContent = m.label;
    sel.appendChild(o);
  }
  sel.value = state.mode;
  $('#modeBlurb').textContent = MODES[state.mode].blurb;
}

async function fillMusic() {
  const sel = $('#music');
  sel.innerHTML = '<option value="generated">generated (mode default)</option>'
    + '<option value="desk">computer desk (fan, keys, clicks)</option><option value="wash">ambient wash</option>'
    + '<option value="ambient">ambient pad (old)</option><option value="piano">piano</option>';
  try {
    let tracks = [];
    if (STATIC) {
      await catalog.load();
      tracks = (catalog.manifest.music || []).map((t) => ({ name: t.name, url: STATIC.replace(/[^/]*$/, '') + t.url }));
    } else {
      const r = await fetch('api/music');
      tracks = (await r.json()).tracks;
    }
    for (const t of tracks) {
      const o = document.createElement('option');
      o.value = t.url;
      o.textContent = t.name;
      sel.appendChild(o);
    }
  } catch (e) { /* no music endpoint */ }
  sel.value = [...sel.options].some((o) => o.value === state.music) ? state.music : 'generated';
  state.music = sel.value;
}

async function applyMusic() {
  if (!state.started) return;
  if (['generated', 'desk', 'wash', 'ambient', 'piano'].includes(state.music)) {
    const base = MODES[state.mode].music;
    const style = state.music === 'generated' ? (base.style || 'wash') : state.music === 'ambient' ? 'pad' : state.music;
    audio.startGenerated(Object.assign({}, base, { style }), makeRng(`${state.seed}:music`));
  } else {
    try {
      await audio.playFile(state.music, { slowed: state.slowed });
    } catch (e) {
      toast(`could not play track: ${e.message}`);
      audio.startGenerated(MODES[state.mode].music, makeRng(`${state.seed}:music`));
    }
  }
}

function setMode(name) {
  state.mode = name;
  sequencer.setMode(name);
  $('#mode').value = name;
  $('#modeBlurb').textContent = MODES[name].blurb;
  if (state.started) {
    player.flush();
    if (['generated', 'desk', 'wash', 'ambient', 'piano'].includes(state.music)) applyMusic();
  }
  syncUrl();
  toast(`mode: ${MODES[name].label}`);
}

function setSeed(seed, { live = false } = {}) {
  state.live = live;
  state.seed = seed;
  $('#seed').value = live ? 'live' : seed;
  sequencer.reseed(seed);
  catalog.seed = seedToInt(seed);
  player.snapEnabled = !live;
  if (state.started) {
    player.restart(live ? liveElapsed() : 0);
    if (['generated', 'desk', 'wash', 'ambient', 'piano'].includes(state.music)) applyMusic();
  }
  syncUrl();
  toast(live ? 'live channel: everyone sees this edit right now' : `seed: ${seed}`);
}

function goLive() { setSeed(liveSeed(), { live: true }); }

function checkLive() {
  if (state.live && state.started && liveSeed() !== state.seed) setSeed(liveSeed(), { live: true });
}

function setAspect(a) {
  state.aspect = a;
  $('#aspect').value = a;
  player.setAspect(a);
  syncUrl();
}

async function refreshStats() {
  try {
    const s = await catalog.refreshStats();
    const tags = Object.entries(s.tags || {}).slice(0, 14).map(([t, n]) => `${t} ${n}`).join(' · ');
    $('#stats').textContent = `${s.clips} clips · ${s.sources} sources · ${Math.round(s.seconds / 60)} min · ${s.with_audio} with audio`;
    $('#tags').textContent = tags || 'no tags yet';
    $('#empty').classList.toggle('hidden', s.clips > 0);
    if (STATIC && catalog.manifest && !$('#credits').dataset.filled) fillCredits();
  } catch (e) {
    $('#stats').textContent = STATIC ? 'could not load manifest.json' : 'server unreachable';
  }
}

function fillCredits() {
  const m = catalog.manifest;
  const built = m.built_at ? new Date(m.built_at).toLocaleDateString() : '';
  $('#staticNote').textContent = `static edition built ${built}: ${m.clips.length} clips from ${m.sources.length} public-domain and open-licence sources, re-scraped by the build pipeline. run it locally to scrape your own.`;
  $('#staticNote').classList.remove('hidden');
  const ul = $('#credits ul');
  ul.innerHTML = '';
  for (const s of m.sources) {
    const li = document.createElement('li');
    const a = document.createElement('a');
    a.href = s.url;
    a.target = '_blank';
    a.rel = 'noopener';
    a.textContent = s.title || s.url;
    li.appendChild(a);
    if (s.uploader) li.appendChild(document.createTextNode(` · ${s.uploader}`));
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
      li.innerHTML = `<span class="st">${job.status}</span> <b>${job.provider}</b> ${escapeHtml(target)} `
        + `<span class="pct">${pct}%</span> <span class="msg">${escapeHtml(job.message || '')}</span>`
        + (job.clips_added ? ` <span class="added">+${job.clips_added}</span>` : '')
        + (['queued', 'running'].includes(job.status) ? ` <button data-cancel="${job.id}">cancel</button>` : '');
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
  const provider = $('#provider').value;
  const query = $('#query').value.trim();
  const isUrl = /^https?:\/\//.test(query);
  const body = {
    provider,
    query: isUrl ? null : query || null,
    url: isUrl ? query : null,
    max_items: Number($('#maxItems').value) || 5,
    tags: $('#jobTags').value,
  };
  const r = await fetch('api/jobs', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json();
  toast(r.ok ? `queued job #${j.id}` : `error: ${j.detail || r.status}`);
  if (r.ok) $('#query').value = '';
  refreshJobs();
}

async function seedStarter(set) {
  const r = await fetch(`api/seed?set=${encodeURIComponent(set)}`, { method: 'POST' });
  const j = await r.json();
  toast(`queued ${j.queued.length} ${set} jobs`);
  refreshJobs();
}

async function toggleRecord() {
  if (!state.started) { toast('start playback first'); return; }
  if (recorder.active) {
    const blob = await recorder.stop();
    if (blob) recorder.download(blob, `corecore-${state.mode}-${state.seed}-${Date.now()}.webm`);
    $('#record').textContent = 'record';
    toast('saved recording (webm)');
  } else {
    recorder.start();
    $('#record').textContent = 'stop recording';
    toast('recording');
  }
}

function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen().catch(() => {});
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
  await player.start({ fastForward: state.live ? liveElapsed() : 0 });
}

// ---- wiring ---------------------------------------------------------------------------------

function wire() {
  if (STATIC) document.body.classList.add('static');
  fillModes();
  fillMusic();
  $('#seed').value = state.live ? 'live' : state.seed;
  $('#poolTags').value = state.tags.join(', ');
  $('#poolTags').addEventListener('change', async (e) => {
    state.tags = e.target.value.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean);
    catalog.setTags(state.tags);
    await refreshStats();
    if (state.started) player.restart(state.live ? liveElapsed() : 0);
    syncUrl();
    toast(state.tags.length ? `playing only: ${state.tags.join(', ')}` : 'playing everything');
  });
  $('#aspect').value = state.aspect;
  $('#slowed').checked = state.slowed;
  $('#edge').value = String(state.edge);
  player.setEdge(state.edge);
  $('#edge').addEventListener('input', (e) => { state.edge = Number(e.target.value); player.setEdge(state.edge); syncUrl(); });
  player.setAspect(state.aspect);
  syncUrl();

  $('#start').addEventListener('click', start);
  $('#splash').addEventListener('click', (e) => { if (e.target.id !== 'start') start(); });
  $('#mode').addEventListener('change', (e) => setMode(e.target.value));
  $('#aspect').addEventListener('change', (e) => setAspect(e.target.value));
  $('#reseed').addEventListener('click', () => setSeed(randomSeed()));
  $('#live').addEventListener('click', goLive);
  $('#seed').addEventListener('change', (e) => { const v = e.target.value.trim(); v === 'live' ? goLive() : setSeed(v || 'corecore'); });
  $('#music').addEventListener('change', (e) => { state.music = e.target.value; syncUrl(); applyMusic(); });
  $('#slowed').addEventListener('change', (e) => { state.slowed = e.target.checked; syncUrl(); if (audio.mode === 'file') audio.setSlowed(state.slowed); });
  $('#volume').addEventListener('input', (e) => audio.setVolume(Number(e.target.value)));
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
  $('#next').addEventListener('click', () => player.nextPhrase());
  $('#ban').addEventListener('click', async () => { const id = await player.banCurrent(); if (id) toast(`banned clip #${id}`); });
  $('#info').addEventListener('click', () => { player.showInfo = !player.showInfo; });
  $('#hideHud').addEventListener('click', () => $('#hud').classList.add('hidden'));
  $('#jobForm').addEventListener('submit', submitJob);
  $('#seedStarter').addEventListener('click', () => seedStarter('contemporary'));
  $('#seedArchival').addEventListener('click', () => seedStarter('archival'));
  $('#jobs').addEventListener('click', async (e) => {
    const id = e.target.dataset.cancel;
    if (id) { await fetch(`api/jobs/${id}/cancel`, { method: 'POST' }); refreshJobs(); }
  });
  $('#copyLink').addEventListener('click', async () => {
    try { await navigator.clipboard.writeText(location.href); toast('link copied'); } catch (e) { toast(location.href, 5000); }
  });

  player.on('warn', (m) => console.warn(m));
  player.on('cue', (c) => {
    if (c.kind === 'clip') {
      const t = c.clip.source_title ? `${c.clip.source_title}${c.clip.source_uploader ? ' · ' + c.clip.source_uploader : ''}` : '';
      $('#nowPlaying').textContent = t;
    }
  });

  document.addEventListener('keydown', (e) => {
    if (e.target.matches('input, textarea, select')) return;
    const k = e.key.toLowerCase();
    if (!state.started && (k === ' ' || k === 'enter')) { start(); return; }
    if (k === ' ') { e.preventDefault(); player.paused ? player.resume() : player.pause(); toast(player.paused ? 'paused' : 'playing', 800); }
    else if (k === 'n') player.nextPhrase();
    else if (k === '.') player.skip();
    else if (k === 'h') $('#hud').classList.toggle('hidden');
    else if (k === 'i') player.showInfo = !player.showInfo;
    else if (k === 'f') toggleFullscreen();
    else if (k === 'r') toggleRecord();
    else if (k === 's') setSeed(randomSeed());
    else if (k === 'l') goLive();
    else if (k === 'x') player.banCurrent().then((id) => id && toast(`banned clip #${id}`));
    else if (k === 'v') setAspect({ '16:9': '9:16', '9:16': '2.39:1', '2.39:1': '16:9' }[state.aspect] || '16:9');
    else if (k === 'm') { const keys = Object.keys(MODES); setMode(keys[(keys.indexOf(state.mode) + 1) % keys.length]); }
  });

  refreshStats();
  refreshJobs();
  setInterval(refreshJobs, 2500);
  setInterval(refreshStats, 15000);
  setInterval(checkLive, 5000);
}

wire();
