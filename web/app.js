import { AudioEngine } from './audio.js';
import { Catalog } from './catalog.js';
import { Player } from './player.js';
import { Recorder } from './recorder.js';
import { MODES, Sequencer } from './sequencer.js';
import { makeRng, seedToInt } from './prng.js';

const $ = (sel) => document.querySelector(sel);
const params = new URLSearchParams(location.search);

const state = {
  seed: params.get('seed') || Math.random().toString(36).slice(2, 8),
  mode: MODES[params.get('mode')] ? params.get('mode') : 'corecore',
  aspect: ['16:9', '9:16', '1:1'].includes(params.get('aspect')) ? params.get('aspect') : '16:9',
  music: params.get('music') || 'generated',
  slowed: params.get('slowed') === '1',
  started: false,
};

const audio = new AudioEngine();
const catalog = new Catalog({ seed: seedToInt(state.seed) });
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
  const p = new URLSearchParams({ seed: state.seed, mode: state.mode, aspect: state.aspect, music: state.music });
  if (state.slowed) p.set('slowed', '1');
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
  sel.innerHTML = '<option value="generated">generated ambient (built in)</option>';
  try {
    const r = await fetch('/api/music');
    const j = await r.json();
    for (const t of j.tracks) {
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
  if (state.music === 'generated') {
    audio.startGenerated(MODES[state.mode].music, makeRng(`${state.seed}:music`));
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
    if (state.music === 'generated') applyMusic();
  }
  syncUrl();
  toast(`mode: ${MODES[name].label}`);
}

function setSeed(seed) {
  state.seed = seed;
  $('#seed').value = seed;
  sequencer.reseed(seed);
  catalog.seed = seedToInt(seed);
  if (state.started) {
    player.flush();
    if (state.music === 'generated') applyMusic();
  }
  syncUrl();
  toast(`seed: ${seed}`);
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
  } catch (e) {
    $('#stats').textContent = 'server unreachable';
  }
}

async function refreshJobs() {
  try {
    const r = await fetch('/api/jobs?limit=12');
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
  const body = {
    provider,
    query: /^https?:\/\//.test(query) ? null : query || null,
    url: /^https?:\/\//.test(query) ? query : null,
    max_items: Number($('#maxItems').value) || 5,
    tags: $('#jobTags').value,
  };
  const r = await fetch('/api/jobs', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json();
  toast(r.ok ? `queued job #${j.id}` : `error: ${j.detail || r.status}`);
  if (r.ok) $('#query').value = '';
  refreshJobs();
}

async function seedStarter() {
  const r = await fetch('/api/seed', { method: 'POST' });
  const j = await r.json();
  toast(`queued ${j.queued.length} starter jobs (Internet Archive)`);
  refreshJobs();
}

async function toggleRecord() {
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
  await player.start();
}

// ---- wiring ---------------------------------------------------------------------------------

function wire() {
  fillModes();
  fillMusic();
  $('#seed').value = state.seed;
  $('#aspect').value = state.aspect;
  $('#slowed').checked = state.slowed;
  player.setAspect(state.aspect);
  syncUrl();

  $('#start').addEventListener('click', start);
  $('#splash').addEventListener('click', (e) => { if (e.target.id !== 'start') start(); });
  $('#mode').addEventListener('change', (e) => setMode(e.target.value));
  $('#aspect').addEventListener('change', (e) => setAspect(e.target.value));
  $('#reseed').addEventListener('click', () => setSeed(Math.random().toString(36).slice(2, 8)));
  $('#seed').addEventListener('change', (e) => setSeed(e.target.value.trim() || 'corecore'));
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
  $('#seedStarter').addEventListener('click', seedStarter);
  $('#jobs').addEventListener('click', async (e) => {
    const id = e.target.dataset.cancel;
    if (id) { await fetch(`/api/jobs/${id}/cancel`, { method: 'POST' }); refreshJobs(); }
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
    else if (k === 's') setSeed(Math.random().toString(36).slice(2, 8));
    else if (k === 'x') player.banCurrent().then((id) => id && toast(`banned clip #${id}`));
    else if (k === 'v') setAspect(state.aspect === '16:9' ? '9:16' : '16:9');
    else if (k === 'm') { const keys = Object.keys(MODES); setMode(keys[(keys.indexOf(state.mode) + 1) % keys.length]); }
  });

  refreshStats();
  refreshJobs();
  setInterval(refreshJobs, 2500);
  setInterval(refreshStats, 15000);
}

wire();
