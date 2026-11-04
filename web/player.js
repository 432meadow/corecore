// Canvas compositor + scheduler. Keeps a pool of <video> elements loading upcoming cues, cuts between
// them on the AudioContext clock, and paints each frame with the corecore treatment.
import { makeRng } from './prng.js';

const POOL_SIZE = 8;
const AHEAD = 5;
const QUEUE_MIN = 10;
const FLASH_SECONDS = 0.14;

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
    this.flashUntil = 0;
    this.flashStrength = 0;
    this.showInfo = false;
    this.snapEnabled = true;
    this.waitingSince = null;
    this.setAspect('16:9');
  }

  on(ev, fn) { (this.listeners[ev] ||= []).push(fn); }
  emit(ev, data) { for (const fn of this.listeners[ev] || []) fn(data); }

  setAspect(a) {
    this.aspect = a;
    const [w, h] = a === '9:16' ? [720, 1280] : a === '1:1' ? [900, 900] : [1280, 720];
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
    let t = 0;
    let guard = 0;
    while (t < seconds && guard++ < 600) {
      let cues = [];
      try { cues = await this.sequencer.nextPhrase(); } catch (err) { break; }
      if (!cues.length) continue;
      for (const c of cues) {
        if (t >= seconds) { this.queue.push(c); continue; }
        if (t + c.dur > seconds) {
          const into = seconds - t;
          if (c.kind === 'clip') c.offset += into * c.speed;
          c.dur -= into;
          t = seconds;
          if (c.dur >= 0.15) this.queue.push(c);
        } else {
          t += c.dur;
        }
      }
    }
    this.stats.skipped = Math.round(t);
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
    this.waitingSince = null;
    const prev = this.current;
    next.start = now;
    next.end = now + next.dur;
    if (next.kind === 'clip') {
      const el = next.slot.el;
      this.audio.setClipGain(el, next.audio.clip || 0);
      el.play().catch(() => {});
      if (next.fx.hold) next.holdAt = now + next.dur * 0.8;
    }
    this.audio.duck(next.audio?.duck ?? 1);
    if (next.fx?.flash?.at === 'start') this.flash(next.fx.flash.strength);
    if (prev?.fx?.flash?.at === 'end') this.flash(prev.fx.flash.strength);
    if (this.previous?.slot) { this.release(this.previous.slot); this.previous.slot = null; this.previous = null; }
    if (prev && prev.kind === 'clip' && prev.slot) {
      const overlap = next.fadeIn > 0 ? next.fadeIn : (next.fx?.double ? next.dur : 0);
      if (overlap > 0) {
        this.previous = prev;
        prev.releaseAt = now + overlap;
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
    this.render(now);
  }

  render(now) {
    const ctx = this.ctx, W = this.canvas.width, H = this.canvas.height;
    const c = this.current;
    ctx.save();
    ctx.filter = 'none';
    ctx.globalCompositeOperation = 'source-over';
    ctx.globalAlpha = 1;
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, W, H);
    if (c && c.kind === 'clip' && c.slot) {
      const p = this.previous;
      const fadeT = c.fadeIn > 0 ? Math.min(1, (now - c.start) / c.fadeIn) : 1;
      if (p && p.slot && p.kind === 'clip') this.drawClip(p, now, 1);
      this.drawClip(c, now, c.fx.double ? 0.62 : fadeT);
    }
    ctx.restore();
    this.drawOverlays(now, c);
  }

  viewport(cue) {
    const W = this.canvas.width, H = this.canvas.height;
    let vx = 0, vy = 0, vw = W, vh = H;
    const lb = cue.fx?.letterbox;
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
    if (el.readyState < 2) return;
    const ctx = this.ctx;
    const prog = Math.min(1, Math.max(0, (now - cue.start) / cue.dur));
    const e = prog < 0.5 ? 2 * prog * prog : 1 - Math.pow(-2 * prog + 2, 2) / 2;
    const zoom = cue.zoom.from + (cue.zoom.to - cue.zoom.from) * e;
    const { vx, vy, vw, vh } = this.viewport(cue);
    const iw = el.videoWidth || 16, ih = el.videoHeight || 9;
    const scale = Math.max(vw / iw, vh / ih) * zoom;
    const dw = iw * scale, dh = ih * scale;
    const ox = (dw - vw) / 2, oy = (dh - vh) / 2;
    let dx = vx - ox - cue.pan.x * ox;
    let dy = vy - oy - cue.pan.y * oy;
    if (cue.fx.shake) {
      dx += (this.fxRng.next() * 2 - 1) * cue.fx.shake;
      dy += (this.fxRng.next() * 2 - 1) * cue.fx.shake;
    }
    ctx.save();
    ctx.beginPath();
    ctx.rect(vx, vy, vw, vh);
    ctx.clip();
    const f = this.sequencer.params.fx || {};
    const filters = [];
    if (cue.fx.bw) filters.push('grayscale(1)');
    else if (f.desat) filters.push(`saturate(${(1 - f.desat).toFixed(2)})`);
    if (f.contrast && f.contrast !== 1) filters.push(`contrast(${f.contrast})`);
    if (filters.length && 'filter' in ctx) ctx.filter = filters.join(' ');
    ctx.globalAlpha = alpha;
    try { ctx.drawImage(el, dx, dy, dw, dh); } catch (err) { /* decoder hiccup; skip frame */ }
    ctx.restore();
  }

  drawOverlays(now, c) {
    const ctx = this.ctx, W = this.canvas.width, H = this.canvas.height;
    const grain = c?.fx?.grain ?? 0.08;
    const vig = c?.fx?.vignette ?? 0.45;
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
    if (vig > 0 && this.vignette) {
      ctx.save();
      ctx.globalAlpha = vig;
      ctx.drawImage(this.vignette, 0, 0);
      ctx.restore();
    }
    if (now < this.flashUntil) {
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
    const a = Math.min(1, t / 0.4) * Math.min(1, Math.max(0, (c.end - now) / 0.3));
    const s = Math.min(W, H) / 720;
    ctx.save();
    ctx.globalAlpha = a;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.shadowColor = 'rgba(0,0,0,0.85)';
    ctx.shadowBlur = 14 * s;
    ctx.fillStyle = '#fff';
    const quote = c.text.style === 'quote';
    ctx.font = quote ? `italic ${Math.round(36 * s)}px Georgia, "Times New Roman", serif`
      : `500 ${Math.round(26 * s)}px "Helvetica Neue", Helvetica, Arial, sans-serif`;
    const lines = this.wrap(ctx, c.text.str, W * 0.78);
    const lh = (quote ? 46 : 34) * s;
    const y0 = quote ? H / 2 - (lines.length - 1) * lh / 2 : H * 0.84 - (lines.length - 1) * lh;
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
      `queue ${this.queue.length}  pool ${this.catalog.size}  cues ${this.stats.cues}  snaps ${this.stats.snaps}  fails ${this.stats.failures}`,
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
    if (this.current) this.current.end = this.audio.now();
  }

  nextPhrase() {
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
      if (fastForward > 0) await this.fastForward(fastForward);
    } finally {
      this.restarting = false;
    }
    this.skip();
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
