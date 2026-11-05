// The sound: clip audio routing with the speaker voicing, ducking, onset detection, and the desk (the
// only generated soundscape: a room with a computer in it) so the stream never runs silent.

import { DeskGenerator } from './desk.js';

// The wash: when a clip's sound is cut, its last moment is thrown into a long, dark reverb, so it washes
// away instead of stopping. WASH_LEVEL sets how loud the tail blooms against the sound it came from.
const WASH_LEVEL = 0.8;
const WASH_FEED = 0.2;        // seconds of the clip, past the cut and unheard dry, that feed the reverb
const WASH_LCUT = 0.7;        // how far an L-cut's fading sound goes wet before it is gone


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
    this.buildWash();
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

  // A stereo hall for the wash: noise decaying to -60 dB over `seconds`, darkening as it goes (air takes
  // the top first), after a short pre-delay and a soft onset; unit energy per channel.
  makeWashIR(seconds) {
    const rate = this.ctx.sampleRate;
    const len = Math.floor(rate * seconds), pre = Math.floor(rate * 0.01), rise = Math.floor(rate * 0.03);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      let y = 0, energy = 0;
      for (let i = pre; i < len; i++) {
        const t = (i - pre) / rate;
        const env = Math.pow(10, -3 * t / seconds) * Math.min(1, (i - pre) / rise);
        const fc = 7000 * Math.pow(900 / 7000, Math.min(1, t / seconds));
        y += (1 - Math.exp(-2 * Math.PI * fc / rate)) * ((Math.random() * 2 - 1) - y);
        d[i] = y * env;
        energy += d[i] * d[i];
      }
      const k = 1 / Math.sqrt(energy || 1);
      for (let i = pre; i < len; i++) d[i] *= k;
    }
    return buf;
  }

  // The wash is fed only by throws (every clip's send is closed otherwise), so nothing else in the piece is
  // reverberant. It is voiced like the clip sound going in, then let out wide and dark.
  buildWash() {
    const ctx = this.ctx;
    const w = (this.wash = {});
    w.input = ctx.createGain();
    w.hp = ctx.createBiquadFilter(); w.hp.type = 'highpass'; w.hp.Q.value = 0.6;
    w.lp = ctx.createBiquadFilter(); w.lp.type = 'lowpass'; w.lp.Q.value = 0.6;
    w.verb = ctx.createConvolver(); w.verb.normalize = false; w.verb.buffer = this.makeWashIR(4.6);
    w.dark = ctx.createBiquadFilter(); w.dark.type = 'lowpass'; w.dark.frequency.value = 3600; w.dark.Q.value = 0.5;
    w.out = ctx.createGain(); w.out.gain.value = WASH_LEVEL;
    w.input.connect(w.hp); w.hp.connect(w.lp); w.lp.connect(w.verb); w.verb.connect(w.dark); w.dark.connect(w.out);
    w.out.connect(this.master);
  }

  voiceWash(mode) {
    const w = this.wash;
    if (!w) return;
    w.hp.frequency.value = mode === 'phone' ? 460 : mode === 'direct' ? 70 : 240;
    w.lp.frequency.value = mode === 'phone' ? 3800 : mode === 'direct' ? 9000 : 4800;
  }

  // 'direct' (as recorded), 'speaker' (computer speakers across the room), 'phone' (tinnier still)
  setClipVoicing(mode) {
    this.clipVoicing = mode;
    if (!this.ctx) return;
    this.voiceWash(mode);
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
    const send = this.ctx.createGain();   // pre-fader, into the wash; open only while the clip is thrown
    send.gain.value = 0;
    src.connect(send);
    if (this.wash) send.connect(this.wash.input);
    el._ccSource = src;
    el._ccGain = g;
    el._ccSend = send;
  }

  setClipGain(el, v) {
    if (!el._ccGain) return;
    const now = this.now();
    el._ccGain.gain.cancelScheduledValues(now);
    el._ccGain.gain.setTargetAtTime(v, now, 0.04);
    if (v > 0) this.closeSend(el);   // a clip starting: nothing of it goes to the wash until it is thrown
  }

  closeSend(el) {
    if (!el._ccSend) return;
    const now = this.now();
    el._ccSend.gain.cancelScheduledValues(now);
    el._ccSend.gain.setValueAtTime(0, now);
  }

  // The throw, as a clip is cut: the dry is muted at once, and the send opens to what the audience was
  // hearing, for WASH_FEED seconds of the sound that follows (the clip plays on, unheard), then closes. The
  // wash rings on for seconds. Returns how long the clip must keep playing, or 0 if it was not audible.
  throwClip(el) {
    if (!el._ccSend || !this.ctx) return 0;
    const now = this.now(), g = el._ccGain.gain.value;
    if (g < 0.03) return 0;
    const s = el._ccSend.gain;
    s.cancelScheduledValues(now);
    s.setValueAtTime(0, now);
    s.linearRampToValueAtTime(g, now + 0.012);
    s.setValueAtTime(g, now + WASH_FEED);
    s.linearRampToValueAtTime(0, now + WASH_FEED + 0.09);
    el._ccGain.gain.cancelScheduledValues(now);
    el._ccGain.gain.setValueAtTime(g, now);
    el._ccGain.gain.setTargetAtTime(0, now, 0.025);   // the dry lets go as the wash arrives, with no hole between
    return WASH_FEED + 0.12;
  }

  // An L-cut's sound, fading out under the next shot, dissolves into the wash on its way out.
  washOut(el, seconds) {
    if (!el._ccSend || !this.ctx) return;
    const now = this.now(), g = el._ccGain.gain.value;
    if (g < 0.03) return;
    const s = el._ccSend.gain;
    s.cancelScheduledValues(now);
    s.setValueAtTime(0, now);
    s.linearRampToValueAtTime(g * WASH_LCUT, now + seconds * 0.5);
    s.linearRampToValueAtTime(0, now + seconds);
  }

  fadeClipGain(el, v, seconds) {
    if (el._ccGain) el._ccGain.gain.setTargetAtTime(v, this.now(), Math.max(0.05, seconds / 3));
  }

  duck(target, tc = 0.25) {
    if (this.duckGain) this.duckGain.gain.setTargetAtTime(target, this.now(), tc);
  }

  setVolume(v) {
    this.volume = v;
    if (this.master && !this.silenced) this.master.gain.setTargetAtTime(v, this.now(), 0.05);
  }

  // Between two streams: every sound fades out with the picture and stays silent until unsilence(),
  // when the next stream's first shot comes up. A volume change meanwhile is kept for the return.
  silence(fadeOut) {
    if (!this.master) return;
    const now = this.now(), g = this.master.gain;
    this.silenced = true;
    g.cancelScheduledValues(now);
    g.setValueAtTime(g.value, now);
    g.linearRampToValueAtTime(0, now + fadeOut);
  }

  unsilence(fadeIn) {
    if (!this.master || !this.silenced) return;
    const now = this.now(), g = this.master.gain;
    this.silenced = false;
    g.cancelScheduledValues(now);
    g.setValueAtTime(g.value, now);
    g.linearRampToValueAtTime(this.volume, now + fadeIn);
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
