// The desk: a room with a computer in it. A PC fan that runs all the time and speeds up when the edit
// gets frantic, typing in words with spaces and the odd backspace, mouse clicks and scroll-wheel ticks,
// a mug set down now and then. Everything is synthesized from noise bursts and short sine bodies; nothing
// is sampled. The player tells it which phrase is on screen: the desk is busy through builds and bursts,
// still at the climax, and nearly silent after the cut to black. Clicks and keys emit onsets so cuts can
// land on them.

const SCENE = { dwell: 0.35, voice: 0.3, jumpcut: 0.5, juxtapose: 0.6, build: 1.0, burst: 1.5, climax: 0.15, black: 0.05, empty: 0.2, wait: 0.3 };

export class DeskGenerator {
  constructor(engine, params = {}, rng) {
    this.e = engine;
    this.ctx = engine.ctx;
    this.rng = rng;
    this.p = Object.assign({ level: 0.8, fan: 1, keys: 0.8, mouse: 0.8, mug: 0.9, room: 1 }, params);
    this.alive = false;
    this.activity = 0.4;
    this.targetActivity = 0.4;
    this.nextTypingAt = 0;
    this.nextClickAt = 0;
    this.nextScrollAt = 0;
    this.nextMugAt = 0;
    this.nextSlideAt = 0;
    this.timer = null;
    this.sources = [];
  }

  // ---- graph ----------------------------------------------------------------------------------

  start() {
    const ctx = this.ctx, now = ctx.currentTime;
    this.alive = true;
    this.out = ctx.createGain();
    this.out.gain.value = 0.0001;
    this.comp = ctx.createDynamicsCompressor();     // catches the transients, leaves the bed alone
    this.comp.threshold.value = -18;
    this.comp.knee.value = 6;
    this.comp.ratio.value = 6;
    this.comp.attack.value = 0.0005;
    this.comp.release.value = 0.15;
    this.out.connect(this.comp);
    this.comp.connect(this.e.musicBus);
    this.noiseBuf = this.makeNoise(4);

    // the fan: lowpassed noise with a blade tone, breathing a little, speeding up with the edit
    this.fanNoise = this.loopNoise(now);
    this.fanLp = ctx.createBiquadFilter();
    this.fanLp.type = 'lowpass';
    this.fanLp.frequency.value = 520;
    this.fanLp.Q.value = 0.8;
    this.fanPeak = ctx.createBiquadFilter();
    this.fanPeak.type = 'peaking';
    this.fanPeak.frequency.value = 140;
    this.fanPeak.Q.value = 5;
    this.fanPeak.gain.value = 9;
    this.fanGain = ctx.createGain();
    this.fanGain.gain.value = 0.0001;
    this.fanNoise.connect(this.fanLp);
    this.fanLp.connect(this.fanPeak);
    this.fanPeak.connect(this.fanGain);
    this.fanGain.connect(this.out);
    this.lfo(this.fanGain.gain, 0.37, 0.004);       // turbulence
    this.lfo(this.fanLp.frequency, 0.06, 45);       // slow wander
    this.fanTone = ctx.createOscillator();
    this.fanTone.type = 'sine';
    this.fanTone.frequency.value = 140;
    this.fanTone2 = ctx.createOscillator();
    this.fanTone2.type = 'sine';
    this.fanTone2.frequency.value = 280;
    this.toneGain = ctx.createGain();
    this.toneGain.gain.value = 0.0001;
    const t2 = ctx.createGain();
    t2.gain.value = 0.3;
    this.fanTone.connect(this.toneGain);
    this.fanTone2.connect(t2);
    t2.connect(this.toneGain);
    this.toneGain.connect(this.out);
    this.fanTone.start(now);
    this.fanTone2.start(now);
    this.sources.push(this.fanTone, this.fanTone2);
    this.lfo(this.fanTone.frequency, 0.9, 0.6);     // a wobble in the bearing

    // room tone: a very low rumble so silence is never digital
    this.roomNoise = this.loopNoise(now);
    this.roomLp = ctx.createBiquadFilter();
    this.roomLp.type = 'lowpass';
    this.roomLp.frequency.value = 110;
    this.roomGain = ctx.createGain();
    this.roomGain.gain.value = 0.012 * this.p.room;
    this.roomNoise.connect(this.roomLp);
    this.roomLp.connect(this.roomGain);
    this.roomGain.connect(this.out);

    this.out.gain.setTargetAtTime(this.p.level, now, 2);
    this.applyActivity(true);
    this.nextTypingAt = now + this.rng.range(4, 12);
    this.nextClickAt = now + this.rng.range(2, 6);
    this.nextScrollAt = now + this.rng.range(6, 14);
    this.nextMugAt = now + this.rng.range(40, 120);
    this.nextSlideAt = now + this.rng.range(3, 9);
    this.timer = setInterval(() => this.tick(), 200);
  }

  loopNoise(at) {
    const src = this.ctx.createBufferSource();
    src.buffer = this.noiseBuf;
    src.loop = true;
    src.start(at, this.rng.range(0, 3));
    this.sources.push(src);
    return src;
  }

  lfo(param, hz, depth) {
    const o = this.ctx.createOscillator();
    o.type = 'sine';
    o.frequency.value = hz;
    const g = this.ctx.createGain();
    g.gain.value = depth;
    o.connect(g);
    g.connect(param);
    o.start();
    this.sources.push(o);
    return o;
  }

  makeNoise(seconds) {
    const rate = this.ctx.sampleRate;
    const len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < len; i++) d[i] = Math.random() * 2 - 1;
    }
    return buf;
  }

  // ---- one-shot sounds ------------------------------------------------------------------------

  // a filtered noise burst with an optional sine body: the atom every desk sound is made of
  burst(at, { freq = 3000, q = 1.5, dur = 0.01, gain = 0.2, pan = 0, body = 0, bodyFreq = 200, bodyDur = 0.03 } = {}) {
    const ctx = this.ctx;
    const pn = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    const dest = pn || this.out;
    if (pn) { pn.pan.value = pan; pn.connect(this.out); }
    const src = ctx.createBufferSource();
    src.buffer = this.noiseBuf;
    const bp = ctx.createBiquadFilter();
    bp.type = 'bandpass';
    bp.frequency.value = freq;
    bp.Q.value = q;
    const g = ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(gain, at + 0.0012);
    g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    src.connect(bp);
    bp.connect(g);
    g.connect(dest);
    src.start(at, this.rng.range(0, 3.5));
    src.stop(at + dur + 0.02);
    if (body > 0) {
      const o = ctx.createOscillator();
      o.type = 'sine';
      o.frequency.setValueAtTime(bodyFreq * 1.4, at);
      o.frequency.exponentialRampToValueAtTime(bodyFreq, at + 0.006);   // a little pitch drop: the thock
      const bg = ctx.createGain();
      bg.gain.setValueAtTime(0.0001, at);
      bg.gain.exponentialRampToValueAtTime(body, at + 0.002);
      bg.gain.exponentialRampToValueAtTime(0.0001, at + bodyDur);
      o.connect(bg);
      bg.connect(dest);
      o.start(at);
      o.stop(at + bodyDur + 0.02);
    }
  }

  key(at, kind = 'key') {
    const v = this.rng.range(0.7, 1.3) * this.p.keys;
    const pan = this.rng.range(-0.25, 0.2);
    if (kind === 'space') {
      this.burst(at, { freq: 2200, q: 1.2, dur: 0.018, gain: 0.16 * v, pan, body: 0.16 * v, bodyFreq: 110, bodyDur: 0.05 });
      this.e.emitOnsetAt(1.1, at);
    } else if (kind === 'enter') {
      this.burst(at, { freq: 2600, q: 1.2, dur: 0.016, gain: 0.18 * v, pan: 0.25, body: 0.18 * v, bodyFreq: 130, bodyDur: 0.045 });
      this.e.emitOnsetAt(1.3, at);
    } else {
      this.burst(at, { freq: this.rng.range(2600, 4600), q: 1.6, dur: this.rng.range(0.006, 0.012), gain: 0.12 * v, pan,
        body: 0.09 * v, bodyFreq: this.rng.range(170, 260), bodyDur: 0.028 });
      // key release, quieter and brighter
      this.burst(at + this.rng.range(0.05, 0.09), { freq: this.rng.range(4000, 6000), q: 2, dur: 0.005, gain: 0.05 * v, pan });
    }
  }

  // a few words, pauses between them, a backspace run now and then, sometimes an enter at the end
  typingSession(at) {
    const words = this.rng.int(2, 7);
    let t = at;
    const pace = 1 + (1 - Math.min(1, this.activity)) * 0.5;   // slower when the room is calm
    for (let w = 0; w < words; w++) {
      const len = this.rng.int(2, 8);
      for (let k = 0; k < len; k++) { this.key(t); t += this.rng.range(0.07, 0.17) * pace; }
      if (this.rng.chance(0.18)) {   // mistake: a pause, two or three backspaces, retype
        t += this.rng.range(0.3, 0.7);
        const n = this.rng.int(2, 3);
        for (let b = 0; b < n; b++) { this.key(t); t += 0.11; }
        t += 0.2;
        for (let b = 0; b < n; b++) { this.key(t); t += this.rng.range(0.09, 0.15); }
      }
      if (w < words - 1) { this.key(t, 'space'); t += this.rng.range(0.16, 0.5) * pace; }
    }
    if (this.rng.chance(0.4)) { t += this.rng.range(0.2, 0.6); this.key(t, 'enter'); }
    return t - at;
  }

  click(at, double = false) {
    const v = this.rng.range(0.8, 1.2) * this.p.mouse;
    const pan = 0.3;
    this.burst(at, { freq: 3800, q: 2.2, dur: 0.006, gain: 0.22 * v, pan, body: 0.05 * v, bodyFreq: 300, bodyDur: 0.015 });
    this.burst(at + this.rng.range(0.07, 0.11), { freq: 4400, q: 2.2, dur: 0.005, gain: 0.14 * v, pan });
    this.e.emitOnsetAt(1.5, at);
    if (double) {
      const d = at + this.rng.range(0.14, 0.2);
      this.burst(d, { freq: 3800, q: 2.2, dur: 0.006, gain: 0.2 * v, pan, body: 0.04 * v, bodyFreq: 300, bodyDur: 0.015 });
      this.burst(d + 0.08, { freq: 4400, q: 2.2, dur: 0.005, gain: 0.12 * v, pan });
    }
  }

  scroll(at) {
    const n = this.rng.int(5, 18);
    let t = at;
    let step = this.rng.range(0.02, 0.035);
    for (let i = 0; i < n; i++) {
      this.burst(t, { freq: 5200, q: 3, dur: 0.003, gain: 0.07 * this.p.mouse, pan: 0.3 });
      step *= this.rng.range(1.0, 1.06);   // the wheel slows as the finger lifts
      t += step;
    }
    return t - at;
  }

  // the mouse sliding on the desk: a soft lowpassed swell
  slide(at) {
    const dur = this.rng.range(0.15, 0.45);
    const src = this.ctx.createBufferSource();
    src.buffer = this.noiseBuf;
    const lp = this.ctx.createBiquadFilter();
    lp.type = 'lowpass';
    lp.frequency.value = 900;
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(0.02 * this.p.mouse, at + dur * 0.4);
    g.gain.exponentialRampToValueAtTime(0.0001, at + dur);
    const pn = this.ctx.createStereoPanner ? this.ctx.createStereoPanner() : null;
    src.connect(lp);
    lp.connect(g);
    if (pn) { pn.pan.value = 0.3; g.connect(pn); pn.connect(this.out); } else g.connect(this.out);
    src.start(at, this.rng.range(0, 3.5));
    src.stop(at + dur + 0.02);
  }

  // a mug set down on the desk: a thud and a short ceramic ring
  mug(at) {
    this.burst(at, { freq: 600, q: 1, dur: 0.03, gain: 0.18 * this.p.mug, pan: -0.4, body: 0.14 * this.p.mug, bodyFreq: 75, bodyDur: 0.07 });
    const o = this.ctx.createOscillator();
    o.type = 'sine';
    o.frequency.value = this.rng.range(1500, 2300);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at + 0.003);
    g.gain.exponentialRampToValueAtTime(0.03 * this.p.mug, at + 0.006);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 0.35);
    o.connect(g);
    g.connect(this.out);
    o.start(at);
    o.stop(at + 0.4);
    this.e.emitOnsetAt(1.3, at);
  }

  // ---- following the edit ---------------------------------------------------------------------

  setScene(phrase) {
    this.targetActivity = SCENE[phrase] ?? 0.4;
  }

  applyActivity(immediate = false) {
    const a = Math.min(1.5, this.activity);
    const now = this.ctx.currentTime, tc = immediate ? 0.01 : 2.5;
    // the machine works harder when the person does: fan speed, tone and pitch rise a little
    const speed = 0.85 + 0.3 * Math.min(1, a / 1.2);
    this.fanLp.frequency.setTargetAtTime(520 * speed, now, tc);
    this.fanPeak.frequency.setTargetAtTime(140 * speed, now, tc);
    this.fanTone.frequency.setTargetAtTime(140 * speed, now, tc);
    this.fanTone2.frequency.setTargetAtTime(280 * speed, now, tc);
    this.fanGain.gain.setTargetAtTime(0.07 * speed * this.p.fan, now, tc);
    this.toneGain.gain.setTargetAtTime(0.007 * speed * this.p.fan, now, tc);
  }

  tick() {
    if (!this.alive) return;
    const now = this.ctx.currentTime;
    this.activity += (this.targetActivity - this.activity) * 0.15;
    this.applyActivity();
    const a = this.activity;
    const calm = a < 0.12;   // the dark: only the fan
    if (now >= this.nextTypingAt) {
      if (!calm && this.rng.chance(Math.min(0.9, 0.35 + 0.5 * a))) {
        const len = this.typingSession(now + 0.1);
        this.nextTypingAt = now + len + this.rng.range(6, 30) / Math.max(0.3, a);
      } else {
        this.nextTypingAt = now + this.rng.range(3, 8);
      }
    }
    if (now >= this.nextClickAt) {
      if (!calm) this.click(now + 0.1, this.rng.chance(0.2));
      this.nextClickAt = now + this.rng.range(2, 12) / Math.max(0.3, a);
    }
    if (now >= this.nextScrollAt) {
      if (!calm) this.scroll(now + 0.1);
      this.nextScrollAt = now + this.rng.range(4, 20) / Math.max(0.3, a);
    }
    if (now >= this.nextSlideAt) {
      if (!calm) this.slide(now + 0.1);
      this.nextSlideAt = now + this.rng.range(2, 9) / Math.max(0.4, a);
    }
    if (now >= this.nextMugAt) {
      if (a < 0.9) this.mug(now + 0.1);
      this.nextMugAt = now + this.rng.range(45, 150);
    }
  }

  stop() {
    this.alive = false;
    clearInterval(this.timer);
    const now = this.ctx.currentTime;
    this.out.gain.cancelScheduledValues(now);
    this.out.gain.setValueAtTime(Math.max(0.0001, this.out.gain.value), now);
    this.out.gain.exponentialRampToValueAtTime(0.0001, now + 1.2);
    for (const s of this.sources) { try { s.stop(now + 1.5); } catch (e) { /* already stopped */ } }
    this.fanNoise.onended = () => { try { this.comp.disconnect(); } catch (e) { /* ignore */ } };
  }
}
