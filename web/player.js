// Canvas compositor + scheduler. Keeps a pool of <video> elements loading upcoming cues, cuts between
// them on the AudioContext clock, and paints each frame with the corecore treatment.
import { makeRng } from './prng.js';
import { GRADES } from './sequencer.js';

const POOL_SIZE = 8;
const AHEAD = 5;
const QUEUE_MIN = 10;
const FLASH_SECONDS = 0.14;
// The page behind the picture. Dark is the screen; light is an off-white sheet, where captions are set in
// ink with a pale halo and the vignette is gentler, so the picture reads as a print rather than a window.
const FIELDS = {
  dark: { rgb: [0, 0, 0], bg: 'rgb(0,0,0)', ink: '#fff', inkSoft: '#d8d8d8', halo: 'rgba(0,0,0,0.85)', vignette: 1, light: false },
  light: { rgb: [250, 250, 250], bg: 'rgb(250,250,250)', ink: '#121212', inkSoft: '#2a2a2a', halo: 'rgba(250,250,250,0.9)', vignette: 0.6, light: true },
};
const FIELD_FADE_MS = 700;   // the page changes colour as slowly as the controls around it do
// Canvas filters (blur, saturate...) are missing in some browsers; setting ctx.filter there does nothing.
const CAN_FILTER = typeof CanvasRenderingContext2D !== 'undefined' && 'filter' in CanvasRenderingContext2D.prototype;

function waitEvent(el, ev, timeout) {
  return new Promise((resolve, reject) => {
    if (ev === 'loadedmetadata' && el.readyState >= 1) return resolve();
    const cleanup = () => { clearTimeout(timer); el.removeEventListener(ev, ok); el.removeEventListener('error', bad); };
    const ok = () => { cleanup(); resolve(); };
    const bad = () => { cleanup(); reject(new Error('media error')); };
    const timer = setTimeout(() => { cleanup(); reject(new Error(`timeout waiting for ${ev}`)); }, timeout);
    el.addEventListener(ev, ok, { once: true });
    el.addEventListener('error', bad, { once: true });
  });
}

function waitSeek(el, timeout) {
  return new Promise((resolve, reject) => {
    let done = false;
    const finish = (err) => {
      if (done) return;
      done = true;
      clearTimeout(timer);
      el.removeEventListener('seeked', check);
      el.removeEventListener('canplay', check);
      el.removeEventListener('error', bad);
      err ? reject(err) : resolve();
    };
    const check = () => { if (!el.seeking && el.readyState >= 2) finish(); };
    const bad = () => finish(new Error('media error'));
    const timer = setTimeout(() => finish(new Error('seek timeout')), timeout);
    el.addEventListener('seeked', check);
    el.addEventListener('canplay', check);
    el.addEventListener('error', bad);
    setTimeout(check, 0);
  });
}

export class Player {
  constructor({ canvas, audio, catalog, sequencer, videoHost }) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', { alpha: false });
    this.audio = audio;
    this.catalog = catalog;
    this.sequencer = sequencer;
    this.videoHost = videoHost || document.body;
    this.queue = [];
    this.current = null;
    this.previous = null;
    this.running = false;
    this.paused = false;
    this.pool = [];
    this.fxRng = makeRng('fx');
    this.listeners = {};
    this.stats = { cues: 0, failures: 0, snaps: 0 };
    this.filling = null;
    this.noise = [];
    this.vignette = null;
    this.field = FIELDS.dark;   // the page behind the picture: black, or off-white like paper
    this.fieldFrom = null;      // while the page changes colour: where it started
    this.fieldT0 = 0;
    this.fieldNow = FIELDS.dark;   // the page as painted this frame
    this.flashUntil = 0;
    this.flashStrength = 0;
    this.showInfo = false;
    this.snapEnabled = true;
    this.waitingSince = null;
    this.scratch = {};
    this.edge = 1;           // 0 = full bleed; 1 = a small, soft picture with wide hazy edges (the default)
    this.origin = null;      // live channel: audio-clock time of stream time zero
    this.streamTime = 0;     // scheduled stream time of the next cue appended to the queue
    this.setAspect('16:9');
  }

  on(ev, fn) { (this.listeners[ev] ||= []).push(fn); }
  emit(ev, data) { for (const fn of this.listeners[ev] || []) fn(data); }

  setEdge(e) {
    this.edge = Math.max(0, Math.min(1, e));
  }

  // The field: 'dark' is a black screen, 'light' an off-white page the picture sits on like a print.
  // While playing, the page cross-fades to the new colour, in step with the controls.
  setField(name) {
    const to = FIELDS[name] || FIELDS.dark;
    if (to === this.field && !this.fieldFrom) return;
    const t = performance.now();
    this.fieldFrom = this.running ? this.fieldAt(t) : null;
    this.fieldT0 = t;
    this.field = to;
    if (!this.running) this.fieldNow = to;
  }

  fieldAt(t) {
    const a = this.fieldFrom, b = this.field;
    if (!a) return b;
    const k = (t - this.fieldT0) / FIELD_FADE_MS;
    if (k >= 1) { this.fieldFrom = null; return b; }
    const e = k <= 0 ? 0 : k * k * (3 - 2 * k);
    const rgb = a.rgb.map((v, i) => Math.round(v + (b.rgb[i] - v) * e));
    const near = e < 0.5 ? a : b;
    return { rgb, bg: `rgb(${rgb.join(',')})`, ink: near.ink, inkSoft: near.inkSoft, halo: near.halo, vignette: a.vignette + (b.vignette - a.vignette) * e, light: b.light };
  }

  // Where the picture sits once framed: the whole canvas at edge 0 or when nothing is playing.
  pictureRect(c) {
    const W = this.canvas.width, H = this.canvas.height;
    if (!(this.edge > 0 && c && c.kind === 'clip')) return { x: 0, y: 0, w: W, h: H };
    const inset = 0.18 * this.edge, pw = Math.round(W * (1 - inset)), ph = Math.round(H * (1 - inset));
    return { x: (W - pw) / 2, y: (H - ph) / 2, w: pw, h: ph };
  }

  // The picture sits inside the frame, smaller, its edges feathered into the page: an alpha mask applied
  // to the composited picture before it is drawn back scaled down. The mask is computed, not blurred: its
  // alpha is exactly 0 on the border (no faint outline where the picture ends), rises with a smootherstep
  // shoulder to 1 at 1.8 x feather inside, and its corners are round. It is fitted to the clip's own
  // viewport, so a letterboxed shot fades out at its own edges rather than being cut by the bars.
  // A few are kept, since cuts move between letterboxed and full shots.
  frameMask(W, H, feather) {
    const key = `${W}x${H}:${feather}`;
    this.masks ||= new Map();
    const hit = this.masks.get(key);
    if (hit) return hit;
    const c = document.createElement('canvas');
    c.width = W; c.height = H;
    const x = c.getContext('2d');
    const img = x.createImageData(W, H), d = img.data;
    const span = Math.max(1, feather * 1.8), R = feather * 2.4;   // the fully opaque core has corners of radius 0.6 x feather
    const n = Math.ceil(span) + 1, lut = new Float32Array(n + 1);
    for (let i = 0; i <= n; i++) { const t = Math.min(1, i / span); lut[i] = 255 * t * t * t * (t * (6 * t - 15) + 10); }
    for (let y = 0; y < H; y++) {
      const dy = Math.min(y + 0.5, H - y - 0.5);
      let i = y * W * 4;
      for (let xx = 0; xx < W; xx++, i += 4) {
        const dx = Math.min(xx + 0.5, W - xx - 0.5);
        let dist;
        if (dx < R && dy < R) { const ax = R - dx, ay = R - dy; dist = R - Math.sqrt(ax * ax + ay * ay); } else dist = dx < dy ? dx : dy;
        let a;
        if (dist <= 0) a = 0;
        else if (dist >= span) a = 255;
        else { const j = Math.floor(dist), fr = dist - j; a = lut[j] + (lut[j + 1] - lut[j]) * fr; }
        d[i] = d[i + 1] = d[i + 2] = 255;
        d[i + 3] = a;
      }
    }
    x.putImageData(img, 0, 0);
    this.masks.set(key, c);
    if (this.masks.size > 6) this.masks.delete(this.masks.keys().next().value);
    return c;
  }

  applyFrame() {
    const ctx = this.ctx, W = this.canvas.width, H = this.canvas.height;
    const { vx, vy, vw, vh } = this.viewport(this.current);
    const feather = Math.round(120 * this.edge * Math.min(vw, vh) / 720);
    const r = this.pictureRect(this.current);
    const pic = this.scratchCanvas('pic', W, H);
    const px = pic.getContext('2d');
    px.globalCompositeOperation = 'source-over';
    px.clearRect(0, 0, W, H);
    if (CAN_FILTER) px.drawImage(this.canvas, 0, 0);
    else {   // no canvas blur in this browser: soften the haze by a trip through a smaller canvas instead
      const k = 1 / (1 + 1.2 * this.edge), sw = Math.max(2, Math.round(W * k)), sh = Math.max(2, Math.round(H * k));
      const soft = this.scratchCanvas('soft', sw, sh), sx = soft.getContext('2d');
      sx.imageSmoothingEnabled = true;
      sx.imageSmoothingQuality = 'high';
      sx.clearRect(0, 0, sw, sh);
      sx.drawImage(this.canvas, 0, 0, sw, sh);
      px.imageSmoothingEnabled = true;
      px.imageSmoothingQuality = 'high';
      px.drawImage(soft, 0, 0, W, H);
    }
    px.globalCompositeOperation = 'destination-in';
    px.drawImage(this.frameMask(vw, vh, feather), vx, vy);
    px.globalCompositeOperation = 'source-over';
    if (vw < W || vh < H) {   // the letterbox bars are page: keep them clear whatever the browser's compositing
      px.clearRect(0, 0, W, vy); px.clearRect(0, vy + vh, W, H - vy - vh);
      px.clearRect(0, vy, vx, vh); px.clearRect(vx + vw, vy, W - vx - vw, vh);
    }
    ctx.save();
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.filter = 'none';
    ctx.fillStyle = this.fieldNow.bg;
    ctx.fillRect(0, 0, W, H);
    ctx.drawImage(pic, r.x, r.y, r.w, r.h);
    ctx.restore();
  }

  setAspect(a) {
    this.aspect = a;
    const [w, h] = a === '9:16' ? [720, 1280] : a === '1:1' ? [900, 900] : a === '2.39:1' ? [1280, 536] : [1280, 720];
    this.canvas.width = w;
    this.canvas.height = h;
    this.buildOverlays();
  }

  buildOverlays() {
    const W = this.canvas.width, H = this.canvas.height;
    if (!this.noise.length) {
      for (let n = 0; n < 4; n++) {
        const c = document.createElement('canvas');
        c.width = c.height = 256;
        const cx = c.getContext('2d');
        const img = cx.createImageData(256, 256);
        for (let i = 0; i < img.data.length; i += 4) {
          const v = 96 + Math.random() * 64;
          img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
          img.data[i + 3] = 255;
        }
        cx.putImageData(img, 0, 0);
        this.noise.push({ canvas: c, pattern: this.ctx.createPattern(c, 'repeat') });
      }
    }
    const v = document.createElement('canvas');
    v.width = W; v.height = H;
    const vx = v.getContext('2d');
    const r = Math.hypot(W, H) / 2;
    const g = vx.createRadialGradient(W / 2, H / 2, r * 0.35, W / 2, H / 2, r);
    g.addColorStop(0, 'rgba(0,0,0,0)');
    g.addColorStop(1, 'rgba(0,0,0,0.92)');
    vx.fillStyle = g;
    vx.fillRect(0, 0, W, H);
    this.vignette = v;
  }

  scratchCanvas(name, w, h) {
    let c = this.scratch[name];
    if (!c) { c = document.createElement('canvas'); this.scratch[name] = c; }
    if (c.width !== w || c.height !== h) { c.width = w; c.height = h; }
    return c;
  }

  initPool() {
    for (let i = 0; i < POOL_SIZE; i++) {
      const v = document.createElement('video');
      v.preload = 'auto';
      v.playsInline = true;
      v.setAttribute('playsinline', '');
      v.crossOrigin = 'anonymous';
      v.disablePictureInPicture = true;
      v.muted = false;
      this.videoHost.appendChild(v);
      this.audio.attachVideo(v);
      this.pool.push({ el: v, busy: false, clipId: null });
    }
  }

  acquire(clipId) {
    const slot = this.pool.find((s) => !s.busy && s.clipId === clipId) || this.pool.find((s) => !s.busy);
    if (slot) slot.busy = true;
    return slot;
  }

  release(slot) {
    if (!slot) return;
    try { slot.el.pause(); } catch (e) { /* ignore */ }
    this.audio.setClipGain(slot.el, 0);
    slot.busy = false;
  }

  async start({ fastForward = 0 } = {}) {
    if (!this.pool.length) this.initPool();
    this.running = true;
    this.paused = false;
    if (fastForward > 0) await this.fastForward(fastForward);
    await this.fillQueue();
    this.advance();
    requestAnimationFrame(() => this.frame());
  }

  // Walk the deterministic cue stream without showing it, so a viewer joining a live channel lands
  // on the same cue everyone else is watching. The straddling cue is trimmed to the remaining time.
  async fastForward(seconds) {
    // stream time zero is pinned to the wall clock here, so whatever this viewer's preload latency,
    // late cues get shortened and everyone converges on the same cut at the same moment
    this.origin = this.audio.now() - seconds;
    let t = 0;
    let guard = 0;
    while (t < seconds && guard++ < 600) {
      let cues = [];
      try { cues = await this.sequencer.nextPhrase(); } catch (err) { break; }
      if (!cues.length) continue;
      for (const c of cues) {
        if (t >= seconds) { c.at = t; t += c.dur; this.queue.push(c); continue; }
        if (t + c.dur > seconds) {
          const into = seconds - t;
          if (c.kind === 'clip') c.offset += into * c.speed;
          c.dur -= into;
          t = seconds;
          if (c.dur >= 0.15) { c.at = t; t += c.dur; this.queue.push(c); }
        } else {
          t += c.dur;
        }
      }
    }
    this.streamTime = t;
    this.stats.skipped = Math.round(seconds);
  }

  stop() {
    this.running = false;
    for (const s of this.pool) this.release(s);
  }

  async fillQueue() {
    if (this.filling) return this.filling;
    this.filling = (async () => {
      let guard = 0;
      while (this.queue.length < QUEUE_MIN && guard++ < 8) {
        let cues = [];
        try { cues = await this.sequencer.nextPhrase(); } catch (err) { this.emit('warn', `sequencer: ${err.message}`); }
        for (const c of cues) { c.at = this.streamTime; this.streamTime += c.dur; }
        if (cues.length) this.queue.push(...cues);
      }
      if (!this.queue.length) {
        // nothing to show (empty pool or server away): hold black briefly instead of spinning
        this.queue.push({ kind: 'black', dur: 0.6, audio: { duck: 1 }, fx: {}, phrase: 'empty', text: null, snap: false, fadeIn: 0 });
      }
    })().finally(() => {
      this.filling = null;
      this.prepareAhead();
    });
    return this.filling;
  }

  prepareAhead() {
    let n = 0;
    for (const cue of this.queue) {
      if (n >= AHEAD) break;
      if (cue.kind !== 'clip') continue;
      n++;
      if (cue.ready || cue.preparing || cue.failed) continue;
      this.prepare(cue);
    }
  }

  async prepare(cue) {
    cue.preparing = true;
    const slot = this.acquire(cue.clip.id);
    if (!slot) { cue.preparing = false; return; }
    const el = slot.el;
    // a cue can be discarded (next phrase, restart, timeout) while we wait on the network: give the slot back
    const abandoned = () => cue.dropped || cue.failed;
    try {
      if (slot.clipId !== cue.clip.id || !el.currentSrc) {
        slot.clipId = cue.clip.id;
        el.src = cue.clip.url;
        el.load();
        await waitEvent(el, 'loadedmetadata', 8000);
        if (abandoned()) { this.release(slot); cue.preparing = false; return; }
      }
      el.playbackRate = cue.speed;
      el.defaultPlaybackRate = cue.speed;
      el.currentTime = cue.offset;
      await waitSeek(el, 8000);
      if (abandoned()) { this.release(slot); cue.preparing = false; return; }
      cue.slot = slot;
      cue.ready = true;
    } catch (err) {
      cue.failed = true;
      this.stats.failures++;
      this.catalog.markBad(cue.clip.id);
      slot.clipId = null;
      this.release(slot);
      this.emit('warn', `clip ${cue.clip.id} failed: ${err.message}`);
    }
    cue.preparing = false;
  }

  advance() {
    const now = this.audio.now();
    if (this.restarting) {
      if (this.current) this.current.end = now + 0.05;
      return;
    }
    let next = this.queue.shift();
    while (next && next.kind === 'clip' && next.failed) next = this.queue.shift();
    if (!next) {
      this.fillQueue();
      if (this.current) this.current.end = now + 0.1;
      return;
    }
    if (next.kind === 'clip' && !next.ready) {
      if (!next.preparing) this.prepare(next);
      this.queue.unshift(next);
      this.waitingSince ??= now;
      if (now - this.waitingSince > 2.0) {
        next.failed = true;
        next.dropped = true;
        this.queue.shift();
        if (next.slot) { this.release(next.slot); next.slot = null; }
        this.waitingSince = null;
        return this.advance();
      }
      if (this.current) this.current.end = now + 0.05;
      else this.current = { kind: 'black', start: now, end: now + 0.05, dur: 0.05, audio: { duck: 1 }, fx: {}, phrase: 'wait' };
      return;
    }
    if (this.origin != null && next.at != null) {
      const sched = this.origin + next.at;
      if (sched + next.dur <= now + 0.08) {   // entirely in the past: the broadcast moved on
        if (next.slot) { this.release(next.slot); next.slot = null; }
        next.dropped = true;
        return this.advance();
      }
    }
    this.waitingSince = null;
    const prev = this.current;
    next.start = now;
    next.end = this.origin != null && next.at != null ? Math.max(now + 0.1, this.origin + next.at + next.dur) : now + next.dur;
    if (next.kind === 'clip') {
      const el = next.slot.el;
      this.audio.setClipGain(el, next.audio.clip || 0);
      if (next.ramp) el.playbackRate = Math.max(0.1, Math.min(4, next.ramp.from));
      el.play().catch(() => {});
      if (next.fx.hold) next.holdAt = now + next.dur * 0.8;
    }
    this.audio.duck(next.audio?.duck ?? 1);
    this.audio.setScene(next.phrase, next);
    if (next.fx?.flash?.at === 'start') this.flash(next.fx.flash.strength);
    if (prev?.fx?.flash?.at === 'end') this.flash(prev.fx.flash.strength);
    if (this.previous?.slot) { this.release(this.previous.slot); this.previous.slot = null; this.previous = null; }
    if (prev && prev.kind === 'clip' && prev.slot) {
      const visual = next.fadeIn > 0 ? next.fadeIn : (next.fx?.double ? next.dur : 0);
      // L-cut: a voice keeps talking under the next shot, fading out over the tail
      const tail = prev.audio?.clip > 0 && next.audioTail > 0 ? next.audioTail : 0;
      const keep = Math.max(visual, tail);
      if (keep > 0) {
        this.previous = prev;
        prev.drawUntil = now + visual;
        prev.releaseAt = now + keep;
        if (tail > 0) this.audio.fadeClipGain(prev.slot.el, 0, tail);
      } else {
        this.release(prev.slot);
        prev.slot = null;
      }
    }
    this.current = next;
    this.stats.cues++;
    this.emit('cue', next);
    if (this.queue.length < QUEUE_MIN) this.fillQueue();
    else this.prepareAhead();
  }

  flash(strength) {
    this.flashStrength = strength;
    this.flashUntil = this.audio.now() + FLASH_SECONDS;
  }

  // Music onsets can pull a cut forward once most of the planned duration has elapsed.
  onOnset(strength) {
    const c = this.current;
    if (!c || !c.snap || this.paused || !this.snapEnabled) return;
    const now = this.audio.now();
    const head = this.queue[0];
    if (now - c.start > c.dur * 0.6 && strength > 1.2 && head && (head.kind !== 'clip' || head.ready)) {
      this.stats.snaps++;
      this.advance();
    }
  }

  frame() {
    if (!this.running) return;
    requestAnimationFrame(() => this.frame());
    this.audio.tick();
    if (this.paused) return;
    const now = this.audio.now();
    const c = this.current;
    if (!c || now >= c.end) this.advance();
    if (this.previous && now >= this.previous.releaseAt) {
      this.release(this.previous.slot);
      this.previous.slot = null;
      this.previous = null;
    }
    const cur = this.current;
    if (cur?.holdAt && now >= cur.holdAt && cur.slot) {
      cur.slot.el.pause();
      cur.holdAt = null;
    }
    if (cur?.kind === 'clip' && cur.ramp && cur.slot && !cur.slot.el.paused) {
      const prog = Math.min(1, Math.max(0, (now - cur.start) / cur.dur));
      const e = prog * prog * (3 - 2 * prog);
      const rate = Math.max(0.1, Math.min(4, cur.ramp.from + (cur.ramp.to - cur.ramp.from) * e));
      if (Math.abs(rate - cur.slot.el.playbackRate) > 0.03) cur.slot.el.playbackRate = rate;
    }
    this.render(now);
  }

  render(now) {
    const ctx = this.ctx, W = this.canvas.width, H = this.canvas.height;
    const c = this.current;
    this.fieldNow = this.fieldAt(performance.now());
    ctx.save();
    ctx.filter = 'none';
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.fillStyle = this.fieldNow.bg;   // a cut to black is a cut to the page: off-white when the field is light
    ctx.fillRect(0, 0, W, H);
    let drawn = false;
    if (c && c.kind === 'clip' && c.slot) {
      const p = this.previous;
      const fadeT = c.fadeIn > 0 ? Math.min(1, (now - c.start) / c.fadeIn) : 1;
      if (p && p.slot && p.kind === 'clip' && now < (p.drawUntil ?? Infinity)) drawn = this.drawClip(p, now, 1) || drawn;
      drawn = this.drawClip(c, now, c.fx.double ? 0.62 : fadeT) || drawn;
    }
    ctx.restore();
    if (drawn) {
      this.drawPicture(now, c);              // grade, vignette, a flash on paper: part of the picture
      if (this.edge > 0) this.applyFrame();  // ...so the frame feathers and scales them with it
    }
    this.drawOverlays(now, c);
  }

  // In a 16:9 or 1:1 frame a portrait clip fills the frame edge to edge, cropped: no blurred sides and no
  // letterbox bars, which would leave a phone clip a sliver. A 2.39:1 frame still shows it whole, since a
  // fill there would keep only a quarter of its height.
  fillsFrame(cue) {
    if (this.aspect !== '16:9' && this.aspect !== '1:1') return false;
    const el = cue.slot?.el;
    const w = el?.videoWidth || cue.clip?.width, h = el?.videoHeight || cue.clip?.height;
    return !!(w && h && h > w);
  }

  viewport(cue) {
    const W = this.canvas.width, H = this.canvas.height;
    let vx = 0, vy = 0, vw = W, vh = H;
    const lb = this.fillsFrame(cue) ? null : cue.fx?.letterbox;
    if (lb === '4:3') {
      if (W >= H) { vw = Math.min(W, Math.round(H * 4 / 3)); vx = Math.round((W - vw) / 2); }
      else { vh = Math.min(H, Math.round(W * 3 / 4)); vy = Math.round((H - vh) / 2); }
    } else if (lb === 'scope') {
      if (W >= H) { vh = Math.min(H, Math.round(W / 2.39)); vy = Math.round((H - vh) / 2); }
      else { vh = Math.min(H, Math.round(W / 1.5)); vy = Math.round((H - vh) / 2); }
    }
    return { vx, vy, vw, vh };
  }

  drawClip(cue, now, alpha) {
    const el = cue.slot.el;
    if (el.readyState < 2) return false;
    const ctx = this.ctx;
    const prog = Math.min(1, Math.max(0, (now - cue.start) / cue.dur));
    const e = prog < 0.5 ? 2 * prog * prog : 1 - Math.pow(-2 * prog + 2, 2) / 2;
    const zoom = cue.zoom.from + (cue.zoom.to - cue.zoom.from) * e;
    const { vx, vy, vw, vh } = this.viewport(cue);
    const iw = el.videoWidth || 16, ih = el.videoHeight || 9;
    // phone footage in a wide frame: shown whole over a soft dark copy of itself, not cropped to a sliver
    const fill = this.fillsFrame(cue);
    const blurFit = cue.fit === 'blur' && !fill && ih / iw > (vh / vw) * 1.2;
    let dx, dy, dw, dh;
    if (blurFit) {
      const scale = (vh / ih) * zoom;
      dw = iw * scale; dh = ih * scale;
      dx = vx + (vw - dw) / 2;
      dy = vy + (vh - dh) / 2 - cue.pan.y * (dh - vh) / 2;
    } else {
      const scale = Math.max(vw / iw, vh / ih) * zoom;
      dw = iw * scale; dh = ih * scale;
      const ox = (dw - vw) / 2, oy = (dh - vh) / 2;
      // a phone clip cropped to a wide frame keeps its upper middle, where the faces usually are
      const py = fill ? Math.max(-1, Math.min(1, cue.pan.y * 0.6 - 0.22)) : cue.pan.y;
      dx = vx - ox - cue.pan.x * ox;
      dy = vy - oy - py * oy;
    }
    if (cue.fx.shake) {
      dx += (this.fxRng.next() * 2 - 1) * cue.fx.shake;
      dy += (this.fxRng.next() * 2 - 1) * cue.fx.shake;
    }
    ctx.save();
    ctx.beginPath();
    ctx.rect(vx, vy, vw, vh);
    ctx.clip();
    const f = this.sequencer.params.fx || {};
    const g = GRADES[cue.grade] || GRADES.neutral;
    const filters = [];
    if (cue.fx.bw) filters.push('grayscale(1)');
    else if (f.desat) filters.push(`saturate(${(1 - f.desat).toFixed(2)})`);
    if (f.contrast && f.contrast !== 1) filters.push(`contrast(${f.contrast})`);
    if (g.filter) filters.push(g.filter);
    // the haze: a slight gaussian blur before the grain; not on the low-res texture, whose blocks are the point
    if (this.edge > 0 && !(cue.fx.pixelate > 1)) filters.push(`blur(${(1.6 * this.edge).toFixed(2)}px)`);
    const filterStr = CAN_FILTER ? filters.join(' ') : '';
    ctx.globalAlpha = alpha;
    if (blurFit) {
      const bg = this.scratchCanvas('bg', 160, 90);
      const bx = bg.getContext('2d');
      bx.filter = 'blur(6px) brightness(0.45)';
      try { bx.drawImage(el, 0, 0, 160, 90); } catch (err) { /* skip */ }
      bx.filter = 'none';
      if (!CAN_FILTER) { bx.fillStyle = 'rgba(0,0,0,0.55)'; bx.fillRect(0, 0, 160, 90); }   // the darkening, without filters
      if (filterStr) ctx.filter = filterStr;
      ctx.drawImage(bg, vx, vy, vw, vh);
    }
    if (filterStr) ctx.filter = filterStr;
    try {
      if (cue.fx.pixelate > 1) {
        // the re-uploaded-at-240p texture: render small, scale up without smoothing
        const k = cue.fx.pixelate;
        const pw = Math.max(16, Math.round(vw / k)), ph = Math.max(9, Math.round(vh / k));
        const pix = this.scratchCanvas('pix', pw, ph);
        const px = pix.getContext('2d');
        px.clearRect(0, 0, pw, ph);
        px.drawImage(el, (dx - vx) / k, (dy - vy) / k, dw / k, dh / k);
        ctx.imageSmoothingEnabled = false;
        ctx.drawImage(pix, vx, vy, vw, vh);
        ctx.imageSmoothingEnabled = true;
      } else {
        ctx.drawImage(el, dx, dy, dw, dh);
      }
    } catch (err) { /* decoder hiccup; skip frame */ }
    ctx.filter = 'none';
    if (cue.fx.aberration > 0 && alpha >= 1) this.aberrate(vx, vy, vw, vh, cue.fx.aberration);
    ctx.restore();
    return true;
  }

  // Chromatic aberration without per-pixel work: the frame split into a red copy and a cyan copy,
  // offset in opposite directions and added back together.
  aberrate(vx, vy, vw, vh, k) {
    const ctx = this.ctx;
    const a = this.scratchCanvas('abA', vw, vh), b = this.scratchCanvas('abB', vw, vh);
    for (const [c, color] of [[a, '#ff0000'], [b, '#00ffff']]) {
      const cx = c.getContext('2d');
      cx.globalCompositeOperation = 'source-over';
      cx.drawImage(this.canvas, vx, vy, vw, vh, 0, 0, vw, vh);
      cx.globalCompositeOperation = 'multiply';
      cx.fillStyle = color;
      cx.fillRect(0, 0, vw, vh);
    }
    ctx.globalCompositeOperation = 'source-over';
    ctx.drawImage(a, vx - k, vy);
    ctx.globalCompositeOperation = 'lighter';
    ctx.drawImage(b, vx + k, vy);
    ctx.globalCompositeOperation = 'source-over';
  }

  // Everything that belongs to the picture, painted before the frame so that it is feathered and scaled
  // with the picture and never touches the page: the grade (lifted blacks, tint, bloom), the vignette, and
  // on the light field the flash. All of it stays inside the clip's viewport, so letterbox bars are page.
  drawPicture(now, c) {
    const ctx = this.ctx;
    const g = GRADES[c?.grade] || GRADES.neutral;
    const vig = c?.fx?.vignette ?? 0.45;
    const { vx, vy, vw, vh } = this.viewport(c);
    ctx.save();
    ctx.filter = 'none';
    ctx.beginPath();
    ctx.rect(vx, vy, vw, vh);
    ctx.clip();
    if (g.lift > 0) {   // lifted blacks: nothing in the picture is ever quite black
      ctx.globalCompositeOperation = 'lighten';
      ctx.globalAlpha = 1;
      ctx.fillStyle = `rgb(${g.lift},${g.lift},${g.lift})`;
      ctx.fillRect(vx, vy, vw, vh);
    }
    if (g.tint && g.tintAlpha > 0) {
      ctx.globalCompositeOperation = g.tintBlend || 'soft-light';
      ctx.globalAlpha = g.tintAlpha;
      ctx.fillStyle = g.tint;
      ctx.fillRect(vx, vy, vw, vh);
    }
    if (g.bloom > 0) {   // highlights bleed a little, from a tiny blurred copy of the picture
      const bl = this.scratchCanvas('bloom', 160, 90);
      const bx = bl.getContext('2d');
      bx.filter = 'blur(4px) brightness(1.1) contrast(1.3)';
      bx.drawImage(this.canvas, vx, vy, vw, vh, 0, 0, 160, 90);
      bx.filter = 'none';
      ctx.globalCompositeOperation = 'screen';
      ctx.globalAlpha = g.bloom;
      ctx.drawImage(bl, vx, vy, vw, vh);
    }
    if (vig > 0 && this.vignette) {   // fitted to the viewport, so a letterboxed shot is vignetted as a picture
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = vig * this.fieldNow.vignette;
      ctx.drawImage(this.vignette, vx, vy, vw, vh);
    }
    if (this.fieldNow.light && now < this.flashUntil) {   // on paper, only the picture blows out
      ctx.globalCompositeOperation = 'source-over';
      ctx.globalAlpha = Math.min(1, this.flashStrength * (this.flashUntil - now) / FLASH_SECONDS);
      ctx.fillStyle = '#fff';
      ctx.fillRect(vx, vy, vw, vh);
    }
    ctx.restore();
  }

  // After the frame: the grain (over everything; on either page it is invisible), the flash on a dark
  // screen (the whole screen blows out), captions and the info overlay.
  drawOverlays(now, c) {
    const ctx = this.ctx, W = this.canvas.width, H = this.canvas.height;
    const g = GRADES[c?.grade] || GRADES.neutral;
    const grain = ((c?.fx?.grain ?? 0.08) + 0.07 * this.edge) * (g.grain ?? 1);
    if (grain > 0 && this.noise.length) {
      const tile = this.noise[Math.floor(this.fxRng.next() * this.noise.length)];
      const ox = Math.floor(this.fxRng.next() * 256), oy = Math.floor(this.fxRng.next() * 256);
      ctx.save();
      ctx.globalCompositeOperation = 'overlay';
      ctx.globalAlpha = grain;
      ctx.translate(-ox, -oy);
      ctx.fillStyle = tile.pattern;
      ctx.fillRect(0, 0, W + 256, H + 256);
      ctx.restore();
    }
    if (!this.fieldNow.light && now < this.flashUntil) {
      ctx.save();
      ctx.globalAlpha = Math.min(1, this.flashStrength * (this.flashUntil - now) / FLASH_SECONDS);
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, W, H);
      ctx.restore();
    }
    if (c?.text) this.drawText(c, now);
    if (this.showInfo) this.drawInfo(c);
  }

  drawText(c, now) {
    const ctx = this.ctx, W = this.canvas.width, H = this.canvas.height;
    const t = now - c.start;
    const title = c.text.style === 'title';
    const fadeIn = title ? 0.7 : 0.4, fadeOut = title ? 0.6 : 0.3;
    const a = Math.min(1, t / fadeIn) * Math.min(1, Math.max(0, (c.end - now) / fadeOut));
    const s = Math.min(W, H) / 720;
    ctx.save();
    ctx.globalAlpha = a;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = this.fieldNow.halo;
    ctx.shadowBlur = title ? 0 : 14 * s;
    ctx.fillStyle = title ? this.fieldNow.inkSoft : this.fieldNow.ink;
    const quote = c.text.style === 'quote';
    ctx.font = quote ? `italic ${Math.round(36 * s)}px Georgia, "Times New Roman", serif`
      : title ? `300 ${Math.round(22 * s)}px Georgia, "Times New Roman", serif`
        : `500 ${Math.round(26 * s)}px "Helvetica Neue", Helvetica, Arial, sans-serif`;
    if (title && 'letterSpacing' in ctx) ctx.letterSpacing = '0.2em';
    const lines = this.wrap(ctx, c.text.str, W * 0.78);
    const lh = (quote ? 46 : title ? 34 : 34) * s;
    const y0 = quote || title ? H / 2 - (lines.length - 1) * lh / 2 : H * 0.84 - (lines.length - 1) * lh;
    lines.forEach((line, i) => ctx.fillText(line, W / 2, y0 + i * lh));
    ctx.restore();
  }

  wrap(ctx, text, maxWidth) {
    const words = text.split(' ');
    const lines = [];
    let line = '';
    for (const w of words) {
      const test = line ? `${line} ${w}` : w;
      if (ctx.measureText(test).width > maxWidth && line) { lines.push(line); line = w; } else line = test;
    }
    if (line) lines.push(line);
    return lines;
  }

  drawInfo(c) {
    const ctx = this.ctx;
    const lines = [
      `mode ${this.sequencer.mode}  seed ${this.sequencer.seed}  cycle ${this.sequencer.cycleCount}`,
      `phrase ${c?.phrase || '-'}  dur ${c ? c.dur.toFixed(2) : '-'}s  speed ${c?.speed ? c.speed.toFixed(2) : '-'}  snap ${c?.snap ? 'y' : 'n'}`,
      c?.clip ? `clip #${c.clip.id}  ${c.clip.source_title || ''}  (${c.clip.provider || ''})` : 'no clip',
      c?.clip ? `tags ${c.clip.tags.join(' ')}` : '',
      c?.clip ? `b ${c.clip.brightness ?? '-'} s ${c.clip.saturation ?? '-'} m ${c.clip.motion ?? '-'}` : '',
      `queue ${this.queue.length}  pool ${this.catalog.size}  cues ${this.stats.cues}  snaps ${this.stats.snaps}  fails ${this.stats.failures}` + (this.origin != null && c?.at != null ? `  drift ${(this.audio.now() - this.origin - c.at - (this.audio.now() - c.start)).toFixed(2)}s` : ''),
      `theme ${this.sequencer.theme ? this.sequencer.theme.join(' / ') : 'none'}  music ${this.audio.mode}  level ${this.audio.level.toFixed(2)}`,
    ];
    ctx.save();
    ctx.font = '13px ui-monospace, Menlo, monospace';
    ctx.textBaseline = 'top';
    ctx.fillStyle = 'rgba(0,0,0,0.6)';
    ctx.fillRect(8, 8, 620, 18 * lines.length + 10);
    ctx.fillStyle = '#9f9';
    lines.forEach((l, i) => ctx.fillText(l, 14, 14 + i * 18));
    ctx.restore();
  }

  // --- controls ------------------------------------------------------------------------------

  skip() {
    if (this.origin != null) return;   // no skipping ahead on a broadcast
    if (this.current) this.current.end = this.audio.now();
  }

  nextPhrase() {
    if (this.origin != null) return;
    const ph = this.current?.phrase;
    const cyc = this.current?.cycle;
    while (this.queue.length && this.queue[0].phrase === ph && this.queue[0].cycle === cyc) {
      const c = this.queue.shift();
      c.dropped = true;
      if (c.slot) { this.release(c.slot); c.slot = null; }
    }
    this.skip();
    this.prepareAhead();
  }

  // Drop everything queued and start over from the sequencer (new seed or mode), optionally
  // fast-forwarded into the new stream.
  async restart(fastForward = 0) {
    this.restarting = true;
    try {
      if (this.filling) await this.filling.catch(() => {});
      for (const c of this.queue) { c.dropped = true; if (c.slot) { this.release(c.slot); c.slot = null; } }
      this.queue = [];
      this.origin = null;
      this.streamTime = 0;
      if (fastForward > 0) await this.fastForward(fastForward);
    } finally {
      this.restarting = false;
    }
    if (this.current) this.current.end = this.audio.now();
    return this.fillQueue();
  }

  flush() { return this.restart(0); }

  async pause() {
    this.paused = true;
    this.current?.slot?.el.pause();
    this.previous?.slot?.el.pause();
    if (this.audio.ctx) await this.audio.ctx.suspend();
  }

  async resume() {
    this.paused = false;
    if (this.audio.ctx) await this.audio.ctx.resume();
    if (this.current?.slot && !this.current.holdAt && this.current.fx?.hold !== true) this.current.slot.el.play().catch(() => {});
    else if (this.current?.slot && this.current.holdAt) this.current.slot.el.play().catch(() => {});
    this.previous?.slot?.el.play().catch(() => {});
  }

  async banCurrent() {
    const c = this.current;
    if (c?.kind === 'clip') {
      await this.catalog.ban(c.clip.id);
      this.skip();
      return c.clip.id;
    }
    return null;
  }
}
