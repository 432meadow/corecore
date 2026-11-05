// Music bed, clip audio routing, ducking, onset detection and a procedural ambient generator
// so the stream never runs silent even with an empty music folder.

import { WashGenerator } from './wash.js';
import { DeskGenerator } from './desk.js';

const midiToFreq = (m) => 440 * Math.pow(2, (m - 69) / 12);
const SCALES = { minor: [0, 2, 3, 5, 7, 8, 10], major: [0, 2, 4, 5, 7, 9, 11] };

class AmbientGenerator {
  constructor(engine, params, rng) {
    this.e = engine;
    this.ctx = engine.ctx;
    this.p = Object.assign({ root: 57, scale: 'minor', chordSeconds: [7, 11], pluck: 0.3, cutoff: 900, level: 0.5, style: 'pad', bpm: 72 }, params);
    this.rng = rng;
    this.degree = 0;
    this.nextChordAt = 0;
    this.nextPluckAt = 0;
    this.nextBeatAt = 0;
    this.beatIndex = 0;
    this.chordMidis = [];
    this.nodes = [];
  }

  get piano() { return this.p.style === 'piano'; }

  start() {
    const ctx = this.ctx;
    this.out = ctx.createGain();
    this.out.gain.value = 0;
    this.filter = ctx.createBiquadFilter();
    this.filter.type = 'lowpass';
    this.filter.frequency.value = this.piano ? Math.max(this.p.cutoff, 2400) : this.p.cutoff;
    this.filter.Q.value = 0.7;
    this.delay = ctx.createDelay(2);
    this.delay.delayTime.value = 0.43;
    this.fb = ctx.createGain();
    this.fb.gain.value = 0.38;
    this.delay.connect(this.fb);
    this.fb.connect(this.delay);
    this.filter.connect(this.out);
    this.filter.connect(this.delay);
    this.delay.connect(this.out);
    this.out.connect(this.e.musicBus);
    this.send = ctx.createGain();
    this.send.gain.value = 0.7;
    this.out.connect(this.send);
    this.send.connect(this.e.reverb);
    this.out.gain.setTargetAtTime(this.p.level, ctx.currentTime, 2.0);
    this.nextChordAt = ctx.currentTime + 0.05;
    this.nextPluckAt = ctx.currentTime + 1.5;
    this.nextBeatAt = ctx.currentTime + 0.4;
    this.timer = setInterval(() => this.schedule(), 200);
    this.schedule();
  }

  schedule() {
    const now = this.ctx.currentTime;
    while (this.nextChordAt < now + 0.8) {
      const dur = this.rng.range(this.p.chordSeconds[0], this.p.chordSeconds[1]);
      this.playChord(this.nextChordAt, dur);
      this.nextChordAt += dur;
    }
    if (this.piano) {
      // a slow, slightly drunk arpeggio over the chord: the sad-piano register of these edits
      const beat = 60 / this.p.bpm;
      while (this.nextBeatAt < now + 0.8) {
        this.beatStep(this.nextBeatAt + this.rng.range(-0.015, 0.035));
        this.nextBeatAt += beat * (this.beatIndex % 2 ? 1.1 : 0.9);
        this.beatIndex++;
      }
      return;
    }
    while (this.nextPluckAt < now + 0.8) {
      if (this.rng.chance(this.p.pluck)) {
        const scale = SCALES[this.p.scale];
        const deg = this.rng.pick([0, 2, 4, 6, 7, 9, 11]);
        const midi = this.p.root + 12 + scale[deg % 7] + 12 * Math.floor(deg / 7);
        this.pluck(this.nextPluckAt, midi);
      }
      this.nextPluckAt += this.rng.range(0.9, 2.4);
    }
  }

  beatStep(at) {
    const i = this.beatIndex;
    if (i % 16 >= 14 && this.rng.chance(0.5)) return;                   // breathe at the end of a phrase
    const tones = this.chordMidis.length ? this.chordMidis : [this.p.root];
    if (i % 4 === 0) this.pianoNote(at, tones[0] - 12, this.rng.range(0.18, 0.26), 3.2);   // bass
    if (this.rng.chance(0.8)) {
      const m = tones[(i + Math.floor(i / 4)) % tones.length] + (this.rng.chance(0.25) ? 12 : 0);
      this.pianoNote(at + this.rng.range(0, 0.03), m, this.rng.range(0.1, 0.2), this.rng.range(1.6, 2.6));
    }
    if (i % 2 === 1 && this.rng.chance(0.3)) {                            // a melody note above
      const scale = SCALES[this.p.scale];
      const m = this.p.root + 24 + scale[this.rng.int(0, 6)];
      this.pianoNote(at + this.rng.range(0.02, 0.08), m, this.rng.range(0.08, 0.16), this.rng.range(1.2, 2.0));
    }
  }

  pianoNote(at, midi, vel, decay) {
    this.e.emitOnsetAt(1.8, at);
    const f = midiToFreq(midi);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(vel, at + 0.006);
    g.gain.exponentialRampToValueAtTime(vel * 0.35, at + 0.25);
    g.gain.exponentialRampToValueAtTime(0.0001, at + decay);
    g.connect(this.filter);
    g.connect(this.send);
    for (const [mult, amp, det] of [[1, 1, 0], [2, 0.45, 3], [3, 0.18, -2], [4, 0.06, 0]]) {
      const o = this.ctx.createOscillator();
      o.type = 'sine';
      o.frequency.value = f * mult;
      o.detune.value = det;
      const ag = this.ctx.createGain();
      ag.gain.value = amp;
      o.connect(ag);
      ag.connect(g);
      o.start(at);
      o.stop(at + decay + 0.1);
    }
  }

  playChord(at, dur) {
    const scale = SCALES[this.p.scale];
    const walk = this.rng.pick([0, 2, 3, 4, 5]);
    this.degree = (this.degree + walk) % 7;
    const notes = [0, 2, 4].map((i) => scale[(this.degree + i) % 7] + 12 * Math.floor((this.degree + i) / 7));
    if (this.rng.chance(0.4)) notes.push(scale[(this.degree + 6) % 7] + 12 * Math.floor((this.degree + 6) / 7));
    const voices = notes.map((n, i) => this.p.root + n + (i === 0 ? -12 : 0));
    voices.push(this.p.root + notes[0] - 24);
    this.chordMidis = notes.map((n) => this.p.root + n);
    this.e.emitOnsetAt(1.5, at);
    const level = this.piano ? 0.035 : 0.09;   // under a piano the pad is just glue
    for (const m of voices) {
      const f = midiToFreq(m);
      const g = this.ctx.createGain();
      g.gain.setValueAtTime(0.0001, at);
      g.gain.exponentialRampToValueAtTime(level, at + 2.2);
      g.gain.setValueAtTime(level, at + dur - 0.5);
      g.gain.exponentialRampToValueAtTime(0.0001, at + dur + 3.5);
      g.connect(this.filter);
      for (const det of [-6, 5]) {
        const o = this.ctx.createOscillator();
        o.type = m < this.p.root - 6 ? 'sine' : 'triangle';
        o.frequency.value = f;
        o.detune.value = det;
        o.connect(g);
        o.start(at);
        o.stop(at + dur + 4);
        this.nodes.push(o);
      }
    }
    this.nodes = this.nodes.filter((o) => true).slice(-64);
  }

  pluck(at, midi) {
    this.e.emitOnsetAt(2.0, at);
    const f = midiToFreq(midi);
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(0.22, at + 0.012);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 1.9);
    g.connect(this.out);
    g.connect(this.send);
    for (const [mult, amp] of [[1, 1], [2, 0.35], [3, 0.12]]) {
      const o = this.ctx.createOscillator();
      o.type = 'sine';
      o.frequency.value = f * mult;
      const ag = this.ctx.createGain();
      ag.gain.value = amp;
      o.connect(ag);
      ag.connect(g);
      o.start(at);
      o.stop(at + 2.2);
    }
  }

  stop() {
    clearInterval(this.timer);
    const t = this.ctx.currentTime;
    this.out.gain.setTargetAtTime(0, t, 0.4);
    setTimeout(() => { try { this.out.disconnect(); this.send.disconnect(); } catch (e) { /* gone */ } }, 2500);
  }
}

export class AudioEngine {
  constructor() {
    this.ctx = null;
    this.onsetHandlers = [];
    this.level = 0;
    this.flux = 0;
    this.history = [];
    this.lastOnset = 0;
    this.mode = 'none';
    this.gen = null;
    this.audioEl = null;
    this.volume = 0.9;
  }

  async init() {
    if (this.ctx) {
      if (this.ctx.state === 'suspended') await this.ctx.resume();
      return;
    }
    const ctx = (this.ctx = new (window.AudioContext || window.webkitAudioContext)());
    this.master = ctx.createGain();
    this.master.gain.value = this.volume;
    this.musicBus = ctx.createGain();
    this.duckGain = ctx.createGain();
    this.clipBus = ctx.createGain();
    this.analyser = ctx.createAnalyser();
    this.analyser.fftSize = 1024;
    this.analyser.smoothingTimeConstant = 0.4;
    this.musicBus.connect(this.duckGain);
    this.duckGain.connect(this.analyser);
    this.analyser.connect(this.master);
    this.buildSpeaker();
    this.setClipVoicing(this.clipVoicing || 'speaker');
    this.master.connect(ctx.destination);
    this.recDest = ctx.createMediaStreamDestination();
    this.master.connect(this.recDest);
    this.freq = new Uint8Array(this.analyser.frequencyBinCount);
    this.prevFreq = new Uint8Array(this.analyser.frequencyBinCount);
    this.reverb = this.makeReverb(3.2);
    this.reverb.connect(this.musicBus);
    this.reverbSend = ctx.createGain();
    this.reverbSend.gain.value = 0;
    this.reverbSend.connect(this.reverb);
    if (ctx.state === 'suspended') await ctx.resume();
  }

  now() { return this.ctx ? this.ctx.currentTime : performance.now() / 1000; }

  // The footage's own sound arrives through a small speaker across the room: no low end, a rolled-off
  // top, a plastic cabinet resonance and a boxy dip, a touch of soft clipping, a short bright room
  // reflection, and a narrowed image. One layer removed from the audience.
  buildSpeaker() {
    const ctx = this.ctx;
    const sp = (this.speaker = {});
    sp.input = ctx.createGain();
    sp.hp = ctx.createBiquadFilter();
    sp.hp.type = 'highpass';
    sp.hp.Q.value = 0.7;
    sp.dip = ctx.createBiquadFilter();
    sp.dip.type = 'peaking';
    sp.dip.frequency.value = 480;
    sp.dip.Q.value = 1.2;
    sp.dip.gain.value = -3;
    sp.peak = ctx.createBiquadFilter();
    sp.peak.type = 'peaking';
    sp.peak.Q.value = 1.4;
    sp.lp = ctx.createBiquadFilter();
    sp.lp.type = 'lowpass';
    sp.lp.Q.value = 0.9;
    sp.hp2 = ctx.createBiquadFilter();    // the cone itself: whatever the distortion made below here is lost
    sp.hp2.type = 'highpass';
    sp.hp2.Q.value = 0.8;
    sp.drive = ctx.createGain();
    sp.shaper = ctx.createWaveShaper();
    sp.shaper.curve = this.softClipCurve(2.5);
    sp.shaper.oversample = '2x';
    sp.mono = ctx.createGain();           // small speakers are not wide
    sp.mono.channelCount = 1;
    sp.mono.channelCountMode = 'explicit';
    sp.room = ctx.createConvolver();
    sp.room.buffer = this.makeRoomIR(0.45);
    sp.roomMix = ctx.createGain();
    sp.dry = ctx.createGain();
    sp.output = ctx.createGain();
    // highpass -> boxy dip -> drive -> soft clip -> cabinet resonance -> (dry + room) -> lowpass last,
    // so the distortion's harmonics and the room's brightness are heard through the same small cone
    sp.input.connect(sp.hp);
    sp.hp.connect(sp.dip);
    sp.dip.connect(sp.drive);
    sp.drive.connect(sp.shaper);
    sp.shaper.connect(sp.peak);
    sp.peak.connect(sp.dry);
    sp.dry.connect(sp.lp);
    sp.peak.connect(sp.room);
    sp.room.connect(sp.roomMix);
    sp.roomMix.connect(sp.lp);
    sp.lp.connect(sp.hp2);
    sp.hp2.connect(sp.mono);
    sp.mono.connect(sp.output);
    sp.output.connect(this.master);
  }

  // unity slope at zero (quiet signal passes unchanged), gentle compression toward the rails
  softClipCurve(k) {
    const n = 2048, curve = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const x = (i / (n - 1)) * 2 - 1;
      curve[i] = Math.tanh(k * x) / k;
    }
    return curve;
  }

  makeRoomIR(seconds) {
    const rate = this.ctx.sampleRate;
    const len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.exp(-8 * i / len);
    }
    return buf;
  }

  // 'direct' (as recorded), 'speaker' (computer speakers across the room), 'phone' (tinnier still)
  setClipVoicing(mode) {
    this.clipVoicing = mode;
    if (!this.ctx) return;
    const sp = this.speaker;
    try { this.clipBus.disconnect(); } catch (e) { /* not connected yet */ }
    if (mode === 'direct') { this.clipBus.connect(this.master); return; }
    const phone = mode === 'phone';
    sp.hp.frequency.value = phone ? 420 : 210;
    sp.hp2.frequency.value = phone ? 460 : 240;
    sp.lp.frequency.value = phone ? 3800 : 4800;
    sp.peak.frequency.value = phone ? 3000 : 2400;
    sp.peak.gain.value = phone ? 7 : 5;
    sp.dip.gain.value = phone ? -5 : -4;
    sp.drive.gain.value = phone ? 2.2 : 1.6;
    sp.dry.gain.value = phone ? 0.75 : 0.85;
    sp.roomMix.gain.value = phone ? 0.3 : 0.24;
    this.clipBus.connect(sp.input);
  }

  makeReverb(seconds) {
    const rate = this.ctx.sampleRate;
    const len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6);
    }
    const conv = this.ctx.createConvolver();
    conv.buffer = buf;
    return conv;
  }

  attachVideo(el) {
    if (el._ccGain || !this.ctx) return;
    const src = this.ctx.createMediaElementSource(el);
    const g = this.ctx.createGain();
    g.gain.value = 0;
    src.connect(g);
    g.connect(this.clipBus);
    el._ccSource = src;
    el._ccGain = g;
  }

  setClipGain(el, v) {
    if (el._ccGain) el._ccGain.gain.setTargetAtTime(v, this.now(), 0.04);
  }

  fadeClipGain(el, v, seconds) {
    if (el._ccGain) el._ccGain.gain.setTargetAtTime(v, this.now(), Math.max(0.05, seconds / 3));
  }

  duck(target, tc = 0.25) {
    if (this.duckGain) this.duckGain.gain.setTargetAtTime(target, this.now(), tc);
  }

  setVolume(v) {
    this.volume = v;
    if (this.master) this.master.gain.setTargetAtTime(v, this.now(), 0.05);
  }

  stopMusic() {
    if (this.audioEl) {
      try { this.audioEl.pause(); } catch (e) { /* ignore */ }
      this.audioEl.removeAttribute('src');
      this.audioEl.load();
      this.audioEl = null;
    }
    if (this.fileSrc) {
      try { this.fileSrc.disconnect(); } catch (e) { /* ignore */ }
      this.fileSrc = null;
    }
    if (this.gen) { this.gen.stop(); this.gen = null; }
    this.mode = 'none';
  }

  async playFile(url, { slowed = false } = {}) {
    this.stopMusic();
    const el = new Audio();
    el.crossOrigin = 'anonymous';
    el.loop = true;
    el.preload = 'auto';
    el.src = url;
    const src = this.ctx.createMediaElementSource(el);
    const dry = this.ctx.createGain();
    src.connect(dry);
    dry.connect(this.musicBus);
    src.connect(this.reverbSend);
    this.audioEl = el;
    this.fileSrc = src;
    this.fileDry = dry;
    this.mode = 'file';
    this.setSlowed(slowed);
    await el.play();
  }

  // "slowed + reverb": 0.8x with pitch following (daycore style) and a long synthetic tail.
  setSlowed(on) {
    this.slowed = on;
    const el = this.audioEl;
    if (!el) return;
    el.playbackRate = on ? 0.8 : 1;
    el.preservesPitch = !on;
    if ('mozPreservesPitch' in el) el.mozPreservesPitch = !on;
    if ('webkitPreservesPitch' in el) el.webkitPreservesPitch = !on;
    this.reverbSend.gain.setTargetAtTime(on ? 0.55 : 0, this.now(), 0.2);
    this.fileDry.gain.setTargetAtTime(on ? 0.75 : 1, this.now(), 0.2);
  }

  startGenerated(params, rng) {
    this.stopMusic();
    const style = params.style || 'wash';
    this.gen = style === 'desk' ? new DeskGenerator(this, params, rng)
      : style === 'wash' ? new WashGenerator(this, params, rng) : new AmbientGenerator(this, params, rng);
    this.gen.start();
    this.mode = 'generated';
  }

  // The edit tells the music what is on screen; generators that can follow, do.
  setScene(phrase, cue) {
    if (this.gen && typeof this.gen.setScene === 'function') this.gen.setScene(phrase, cue);
  }

  onOnset(fn) { this.onsetHandlers.push(fn); }

  // Scheduled sources (the generator) know their own onsets ahead of time.
  emitOnsetAt(strength, at) {
    const delay = Math.max(0, (at - this.now()) * 1000);
    setTimeout(() => {
      if (!this.ctx || this.ctx.state !== 'running') return;
      this.lastOnset = this.now();
      for (const fn of this.onsetHandlers) fn(strength);
    }, delay);
  }

  // Spectral-flux onset detection over the music bus; called once per animation frame.
  tick() {
    if (!this.analyser) return;
    this.analyser.getByteFrequencyData(this.freq);
    let flux = 0, energy = 0;
    const n = Math.min(this.freq.length, 200);
    for (let i = 1; i < n; i++) {
      const d = this.freq[i] - this.prevFreq[i];
      if (d > 0) flux += d;
      energy += this.freq[i];
    }
    this.prevFreq.set(this.freq);
    this.level = this.level * 0.8 + (energy / n / 255) * 0.2;
    this.flux = flux / n;
    const h = this.history;
    h.push(this.flux);
    if (h.length > 45) h.shift();
    if (h.length < 20) return;
    const mean = h.reduce((s, x) => s + x, 0) / h.length;
    const sd = Math.sqrt(h.reduce((s, x) => s + (x - mean) ** 2, 0) / h.length);
    const thresh = mean + 1.6 * sd + 0.25;
    const t = this.now();
    if (this.flux > thresh && t - this.lastOnset > 0.12) {
      this.lastOnset = t;
      const strength = Math.min(3, this.flux / Math.max(1e-6, thresh));
      for (const fn of this.onsetHandlers) fn(strength);
    }
  }
}
