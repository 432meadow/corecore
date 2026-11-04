// The wash: an emotive ambient bed with almost no notes. Layers of detuned strings, a formant choir, a
// breath of filtered noise, a sub and an occasional shimmer, moving through slow suspended harmony by
// voice leading (every voice glides to its nearest new pitch), under a long reverb, breathing with a
// sub-audio LFO and following the edit: the player tells it which phrase is on screen and it swells,
// darkens, thins out or drops accordingly.

const midiToFreq = (m) => 440 * Math.pow(2, (m - 69) / 12);

export const MODES_SCALES = {
  aeolian: [0, 2, 3, 5, 7, 8, 10],
  dorian: [0, 2, 3, 5, 7, 9, 10],
  phrygian: [0, 1, 3, 5, 7, 8, 10],
  ionian: [0, 2, 4, 5, 7, 9, 11],
  lydian: [0, 2, 4, 6, 7, 9, 11],
};

// Chord recipes as scale degrees (0-based) above a root degree. Suspensions and added tones, no plain
// triads for long: the harmony is meant to hover, not resolve.
const RECIPES = [
  { name: 'sus2', tones: [0, 1, 4] },
  { name: 'add9', tones: [0, 2, 4, 8] },
  { name: 'sus4', tones: [0, 3, 4] },
  { name: 'm7', tones: [0, 2, 4, 6] },
  { name: 'm9', tones: [0, 2, 4, 6, 8] },
  { name: '5+9', tones: [0, 4, 8] },
  { name: 'm11', tones: [0, 2, 4, 6, 10] },
];

// Scene intensities: how much the bed opens up for each phrase of the edit.
const SCENE = { dwell: 0.28, voice: 0.2, jumpcut: 0.35, juxtapose: 0.45, build: 0.65, burst: 0.9, climax: 1.0, black: 0.12, empty: 0.2, wait: 0.3 };

export class WashGenerator {
  constructor(engine, params = {}, rng) {
    this.e = engine;
    this.ctx = engine.ctx;
    this.rng = rng;
    this.p = Object.assign({
      root: 57, mode: 'aeolian', chordSeconds: [14, 26], glide: [2.5, 5], level: 0.36, brightness: 0.35,
      motion: 0.4, strings: 1, choir: 0.7, air: 0.6, sub: 0.8, shimmer: 0.6, dissonance: 0.0, voices: 4,
    }, params);
    this.voices = [];
    this.alive = false;
    this.intensity = 0.3;
    this.targetIntensity = 0.3;
    this.degree = 0;
    this.nextChordAt = 0;
    this.nextShimmerAt = 0;
    this.timer = null;
    this.lfos = [];
  }

  // ---- graph ----------------------------------------------------------------------------------

  start() {
    const ctx = this.ctx, now = ctx.currentTime;
    this.alive = true;
    this.out = ctx.createGain();
    this.out.gain.value = 0.0001;
    this.comp = ctx.createDynamicsCompressor();
    this.comp.threshold.value = -24;
    this.comp.knee.value = 14;
    this.comp.ratio.value = 2.5;
    this.comp.attack.value = 0.2;
    this.comp.release.value = 1.5;
    this.breath = ctx.createGain();          // slow breathing of the whole bed
    this.breath.gain.value = 1;
    this.out.connect(this.breath);
    this.breath.connect(this.comp);
    this.comp.connect(this.e.musicBus);

    // long reverb with pre-delay and a darkening tail
    this.predelay = ctx.createDelay(1);
    this.predelay.delayTime.value = 0.07;
    this.verb = ctx.createConvolver();
    this.verb.buffer = this.makeIR(7.5);
    this.verbTone = ctx.createBiquadFilter();
    this.verbTone.type = 'lowpass';
    this.verbTone.frequency.value = 5600;
    this.send = ctx.createGain();
    this.send.gain.value = 0.9;
    this.send.connect(this.predelay);
    this.predelay.connect(this.verb);
    this.verb.connect(this.verbTone);
    this.verbTone.connect(this.out);

    // string layer bus: lowpass that opens with intensity, slow wander, gentle stereo drift
    this.stringsHp = ctx.createBiquadFilter();
    this.stringsHp.type = 'highpass';
    this.stringsHp.frequency.value = 85;
    this.stringsFilter = ctx.createBiquadFilter();
    this.stringsFilter.type = 'lowpass';
    this.stringsFilter.Q.value = 0.6;
    this.stringsFilter.frequency.value = 800;
    this.stringsGain = ctx.createGain();
    this.stringsGain.gain.value = 0.0001;
    this.stringsPan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    this.stringsHp.connect(this.stringsFilter);
    this.stringsFilter.connect(this.stringsGain);
    let tail = this.stringsGain;
    if (this.stringsPan) { this.stringsGain.connect(this.stringsPan); tail = this.stringsPan; }
    tail.connect(this.out);
    tail.connect(this.send);
    this.lfo(this.stringsFilter.frequency, 0.045 * (0.6 + this.p.motion), 160);
    if (this.stringsPan) this.lfo(this.stringsPan.pan, 0.023, 0.35);

    // choir layer: two formant bands in parallel
    this.choirIn = ctx.createGain();
    this.choirGain = ctx.createGain();
    this.choirGain.gain.value = 0.0001;
    for (const [f, q, g] of [[720, 3, 1], [1150, 4, 0.8], [2500, 4, 0.65]]) {
      const bp = ctx.createBiquadFilter();
      bp.type = 'bandpass';
      bp.frequency.value = f;
      bp.Q.value = q;
      const bg = ctx.createGain();
      bg.gain.value = g;
      this.choirIn.connect(bp);
      bp.connect(bg);
      bg.connect(this.choirGain);
      this.lfo(bp.frequency, 0.03 + this.rng.range(0, 0.02), f * 0.08);
    }
    this.choirPan = ctx.createStereoPanner ? ctx.createStereoPanner() : null;
    if (this.choirPan) {
      this.choirGain.connect(this.choirPan);
      this.choirPan.connect(this.out);
      this.choirPan.connect(this.send);
      const drift = this.lfo(this.choirPan.pan, 0.019, 0.4);   // drifts against the strings
      drift.frequency.value = 0.019;
    } else {
      this.choirGain.connect(this.out);
      this.choirGain.connect(this.send);
    }

    // air: filtered noise, wandering band, mostly in the reverb
    this.noise = ctx.createBufferSource();
    this.noise.buffer = this.makeNoise(5);
    this.noise.loop = true;
    this.airBand = ctx.createBiquadFilter();
    this.airBand.type = 'bandpass';
    this.airBand.frequency.value = 2600;
    this.airBand.Q.value = 0.7;
    this.airHp = ctx.createBiquadFilter();
    this.airHp.type = 'highpass';
    this.airHp.frequency.value = 900;
    this.airGain = ctx.createGain();
    this.airGain.gain.value = 0.0001;
    this.noise.connect(this.airBand);
    this.airBand.connect(this.airHp);
    this.airHp.connect(this.airGain);
    this.airGain.connect(this.send);
    this.airDirect = ctx.createGain();
    this.airDirect.gain.value = 1.6;
    this.airGain.connect(this.airDirect);
    this.airDirect.connect(this.out);
    this.lfo(this.airBand.frequency, 0.017, 1100);
    this.noise.start(now);

    // sub: one sine on the root, two octaves down, slow amplitude breathing
    this.subOsc = ctx.createOscillator();
    this.subOsc.type = 'sine';
    this.subOsc.frequency.value = midiToFreq(this.p.root - 24);
    this.subGain = ctx.createGain();
    this.subGain.gain.value = 0.0001;
    this.subOsc.connect(this.subGain);
    this.subGain.connect(this.out);
    this.subOsc.start(now);
    this.lfo(this.subGain.gain, 0.021, 0.02);

    // breathing: the whole bed rises and falls over about 25 seconds
    this.lfo(this.breath.gain, 0.035, 0.15);

    this.out.gain.setTargetAtTime(this.p.level, now, 4);
    this.playChord(now + 0.05, true);
    this.nextChordAt = now + this.rng.range(this.p.chordSeconds[0], this.p.chordSeconds[1]);
    this.nextShimmerAt = now + this.rng.range(4, 10);
    this.applyIntensity(true);
    this.timer = setInterval(() => this.tick(), 250);
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
    this.lfos.push(o);
    return o;
  }

  makeIR(seconds) {
    const rate = this.ctx.sampleRate;
    const len = Math.floor(rate * seconds);
    const buf = this.ctx.createBuffer(2, len, rate);
    for (let ch = 0; ch < 2; ch++) {
      const d = buf.getChannelData(ch);
      let lp = 0;
      for (let i = 0; i < len; i++) {
        const t = i / len;
        // the tail darkens as it decays: a one-pole lowpass whose coefficient tightens over time
        const white = Math.random() * 2 - 1;
        lp += (white - lp) * (0.55 - 0.45 * t);
        d[i] = lp * Math.pow(1 - t, 2.2) * (i < rate * 0.02 ? i / (rate * 0.02) : 1);
      }
    }
    return buf;
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

  // ---- harmony --------------------------------------------------------------------------------

  chordPitches() {
    const scale = MODES_SCALES[this.p.mode] || MODES_SCALES.aeolian;
    const recipe = this.rng.weighted(RECIPES, (r) => (r.tones.length <= 3 ? 1.2 : 1) * (this.intensity > 0.7 && r.tones.length >= 4 ? 1.4 : 1));
    const pitches = recipe.tones.map((t) => {
      const deg = this.degree + t;
      return this.p.root + scale[deg % 7] + 12 * Math.floor(deg / 7);
    });
    if (this.p.dissonance > 0 && this.rng.chance(this.p.dissonance)) pitches.push(this.p.root + scale[(this.degree + 1) % 7] + 12);
    // spread the voicing across two octaves, root an octave down
    const spread = pitches.map((m, i) => (i === 0 ? m - 12 : i >= 3 ? m + 12 : m));
    const n = Math.max(3, Math.min(this.p.voices + (this.intensity > 0.6 ? 1 : 0), spread.length));
    return { name: recipe.name, pitches: spread.slice(0, n) };
  }

  playChord(at, first = false) {
    // slow walk through the mode: the next root is close, with a tendency to fall
    const step = this.rng.weighted([0, -1, -2, 1, 2, -3, 3], (s) => ({ 0: 1.2, '-1': 1.4, '-2': 1.1, 1: 1.0, 2: 0.8, '-3': 0.6, 3: 0.5 })[s]);
    this.degree = ((this.degree + step) % 7 + 7) % 7;
    const chord = this.chordPitches();
    const glide = first ? 0 : this.rng.range(this.p.glide[0], this.p.glide[1]);
    // voice leading: each existing voice goes to its nearest new pitch; leftovers fade out; missing ones fade in
    const targets = chord.pitches.slice();
    const kept = [];
    for (const v of this.voices) {
      if (!targets.length) { this.releaseVoice(v, at, glide + 2); continue; }
      let best = 0;
      for (let i = 1; i < targets.length; i++) if (Math.abs(targets[i] - v.midi) < Math.abs(targets[best] - v.midi)) best = i;
      const m = targets.splice(best, 1)[0];
      this.glideVoice(v, m, at, glide);
      kept.push(v);
    }
    for (const m of targets) kept.push(this.makeVoice(m, at, first ? 6 : 5 + glide));
    this.voices = kept;
    this.chordName = chord.name;
    this.e.emitOnsetAt(1.3, at + glide * 0.5);
  }

  makeVoice(midi, at, attack) {
    const ctx = this.ctx;
    const f = midiToFreq(midi);
    const gain = ctx.createGain();
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(1, at + attack);
    const oscs = [];
    const lowest = !this.voices.length || midi <= Math.min(...this.voices.map((v) => v.midi));
    // strings: two detuned saws through the shared lowpass; a triangle an octave down only under the lowest voice
    for (const [type, det, amp, octave] of [['sawtooth', -9, 0.15, 0], ['sawtooth', 8, 0.15, 0], ['triangle', 0, lowest ? 0.12 : 0.08, lowest ? -12 : 0]]) {
      const o = ctx.createOscillator();
      o.type = type;
      o.frequency.value = midiToFreq(midi + octave);
      o.detune.value = det + this.rng.range(-3, 3);
      const g = ctx.createGain();
      g.gain.value = amp * this.p.strings;
      o.connect(g);
      g.connect(gain);
      o.start(at);
      oscs.push({ o, octave });
    }
    // choir: three sines with slow vibrato into the formant bank
    const vib = ctx.createOscillator();
    vib.type = 'sine';
    vib.frequency.value = 4.6 + this.rng.range(0, 1.2);
    const vibDepth = ctx.createGain();
    vibDepth.gain.setValueAtTime(0, at);
    vibDepth.gain.linearRampToValueAtTime(7, at + attack * 1.5);
    vib.connect(vibDepth);
    vib.start(at);
    for (const [mult, amp] of [[1, 0.5], [2, 0.22], [3, 0.08]]) {
      const o = ctx.createOscillator();
      o.type = 'sine';
      o.frequency.value = f * mult;
      vibDepth.connect(o.detune);
      const g = ctx.createGain();
      g.gain.value = amp * this.p.choir;
      o.connect(g);
      g.connect(gain);
      o.start(at);
      oscs.push({ o, octave: 0, mult });
    }
    const toStrings = ctx.createGain();
    toStrings.gain.value = 1;
    gain.connect(toStrings);
    toStrings.connect(this.stringsHp);
    gain.connect(this.choirIn);
    this.lfos.push(vib);
    return { midi, gain, oscs, vib };
  }

  glideVoice(v, midi, at, glide) {
    if (v.midi === midi) return;
    for (const { o, octave, mult } of v.oscs) {
      const target = midiToFreq(midi + (octave || 0)) * (mult || 1);
      o.frequency.cancelScheduledValues(at);
      o.frequency.setValueAtTime(o.frequency.value, at);
      o.frequency.exponentialRampToValueAtTime(target, at + Math.max(0.05, glide));
    }
    v.midi = midi;
  }

  releaseVoice(v, at, release) {
    v.gain.gain.cancelScheduledValues(at);
    v.gain.gain.setValueAtTime(Math.max(0.0001, v.gain.gain.value), at);
    v.gain.gain.exponentialRampToValueAtTime(0.0001, at + release);
    setTimeout(() => {
      for (const { o } of v.oscs) { try { o.stop(); } catch (e) { /* already stopped */ } }
      try { v.vib.stop(); } catch (e) { /* ignore */ }
      try { v.gain.disconnect(); } catch (e) { /* ignore */ }
    }, (at - this.ctx.currentTime + release + 0.5) * 1000);
  }

  shimmer(at) {
    // one high tone, slightly sharp, four seconds to arrive, mostly reverb
    const scale = MODES_SCALES[this.p.mode] || MODES_SCALES.aeolian;
    const midi = this.p.root + 24 + scale[this.rng.pick([0, 2, 4])];
    const o = this.ctx.createOscillator();
    o.type = 'sine';
    o.frequency.value = midiToFreq(midi);
    o.detune.value = 8;
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(0.07 * this.p.shimmer, at + 4);
    g.gain.exponentialRampToValueAtTime(0.0001, at + 11);
    o.connect(g);
    const o2 = this.ctx.createOscillator();
    o2.type = 'sine';
    o2.frequency.value = midiToFreq(midi + 12);
    o2.detune.value = -5;
    const g2 = this.ctx.createGain();
    g2.gain.value = 0.35;
    o2.connect(g2);
    g2.connect(g);
    g.connect(this.send);
    o.start(at);
    o.stop(at + 11.5);
    o2.start(at);
    o2.stop(at + 11.5);
  }

  // ---- following the edit ---------------------------------------------------------------------

  setScene(phrase, cue) {
    const base = SCENE[phrase] ?? 0.4;
    this.targetIntensity = base;
    const now = this.ctx.currentTime;
    if (phrase === 'climax') {
      // the swell: three seconds of rising, then the top
      this.out.gain.cancelScheduledValues(now);
      this.out.gain.setValueAtTime(this.out.gain.value, now);
      this.out.gain.linearRampToValueAtTime(this.p.level * 1.35, now + Math.min(3, (cue?.dur || 3) * 0.8));
      this.e.emitOnsetAt(2.0, now + Math.min(3, (cue?.dur || 3) * 0.8));
    } else if (phrase === 'black') {
      // the drop: the bed falls away and the reverb carries
      this.out.gain.cancelScheduledValues(now);
      this.out.gain.setValueAtTime(this.out.gain.value, now);
      this.out.gain.exponentialRampToValueAtTime(this.p.level * 0.25, now + 0.35);
      this.out.gain.setTargetAtTime(this.p.level, now + 0.5, 3.5);
    } else {
      this.out.gain.cancelScheduledValues(now);
      this.out.gain.setTargetAtTime(this.p.level, now, 2.5);
    }
  }

  applyIntensity(immediate = false) {
    const i = this.intensity, b = this.p.brightness;
    const now = this.ctx.currentTime, tc = immediate ? 0.01 : 1.6;
    const cutoff = 420 + (900 + 3200 * b) * Math.pow(i, 1.3);
    this.stringsFilter.frequency.setTargetAtTime(cutoff, now, tc);
    this.stringsGain.gain.setTargetAtTime((0.1 + 0.18 * i) * this.p.strings, now, tc);
    this.choirGain.gain.setTargetAtTime((0.05 + 0.13 * i) * this.p.choir, now, tc);
    this.airGain.gain.setTargetAtTime((0.03 + 0.09 * i) * this.p.air, now, tc);
    this.subGain.gain.setTargetAtTime((0.03 + 0.03 * (1 - i)) * this.p.sub, now, tc);
    this.send.gain.setTargetAtTime(0.6 + 0.3 * (1 - i), now, tc);
  }

  tick() {
    if (!this.alive) return;
    const now = this.ctx.currentTime;
    // intensity slews toward its target; changes are what you hear, so keep them slow
    this.intensity += (this.targetIntensity - this.intensity) * 0.12;
    this.applyIntensity();
    if (now >= this.nextChordAt - 0.3) {
      this.playChord(this.nextChordAt);
      const scale = 1 - 0.35 * this.intensity;   // harmony moves faster when the edit does
      this.nextChordAt += this.rng.range(this.p.chordSeconds[0], this.p.chordSeconds[1]) * scale;
    }
    if (now >= this.nextShimmerAt) {
      if (this.rng.chance(0.3 + 0.6 * this.intensity) && this.p.shimmer > 0) this.shimmer(now + 0.1);
      this.nextShimmerAt = now + this.rng.range(7, 16);
    }
  }

  stop() {
    this.alive = false;
    clearInterval(this.timer);
    const now = this.ctx.currentTime;
    this.out.gain.cancelScheduledValues(now);
    this.out.gain.setValueAtTime(Math.max(0.0001, this.out.gain.value), now);
    this.out.gain.exponentialRampToValueAtTime(0.0001, now + 1.8);
    setTimeout(() => {
      for (const v of this.voices) { for (const { o } of v.oscs) { try { o.stop(); } catch (e) { /* ignore */ } } try { v.vib.stop(); } catch (e) { /* ignore */ } }
      for (const o of this.lfos) { try { o.stop(); } catch (e) { /* ignore */ } }
      try { this.noise.stop(); this.subOsc.stop(); } catch (e) { /* ignore */ }
      try { this.comp.disconnect(); } catch (e) { /* ignore */ }
    }, 2200);
  }
}
