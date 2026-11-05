// The sound: clip audio routing with the speaker voicing, ducking, onset detection, and the desk (the
// only generated soundscape: a room with a computer in it) so the stream never runs silent.

import { DeskGenerator } from './desk.js';


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
    if (this.gen) { this.gen.stop(); this.gen = null; }
    this.mode = 'none';
  }

  // The desk, with the mode's own balance of fan, keys, mouse, mug and room.
  startGenerated(params, rng) {
    this.stopMusic();
    this.gen = new DeskGenerator(this, params, rng);
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
