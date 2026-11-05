// The wash: an emotive ambient bed with almost no notes. Layers of detuned strings, a formant choir, a
// breath of filtered noise, a sub and an occasional shimmer, moving through slow suspended harmony with
// a home (the tonic) and colours away from it; voices live in registers and are led by pitch class, so
// small moves glide and big ones crossfade like a section changing bow. A long reverb returns outside
// the scene gain so the tail carries through the drops. The player tells the bed which phrase is on
// screen: it thins on a dwell, pulls away from home through a build, holds through a burst, arrives
// home at the top of the climax and falls away on the cut to black.

const midiToFreq = (m) => 440 * Math.pow(2, (m - 69) / 12);

export const MODES_SCALES = {
  aeolian: [0, 2, 3, 5, 7, 8, 10],
  dorian: [0, 2, 3, 5, 7, 9, 10],
  phrygian: [0, 1, 3, 5, 7, 8, 10],
  ionian: [0, 2, 4, 5, 7, 9, 11],
  lydian: [0, 2, 4, 6, 7, 9, 11],
};
const MAJOR_FAMILY = new Set(['ionian', 'lydian']);

// Chord recipes as scale-degree offsets above the chord root, in order of importance for a thin voicing:
// the root first, then the colour tones, the third last and the fifth is the first thing dropped.
const RECIPES = {
  sus2: [0, 1, 4],
  sus4: [0, 3, 4],
  add9: [0, 8, 2, 4],
  open9: [0, 8, 2],
  m7: [0, 6, 2, 4],
  m9: [0, 8, 6, 2, 4],
  m11: [0, 10, 6, 2, 4],
  '5+9': [0, 8, 4],
};

// Where the harmony lives: a home degree, the colours it drifts to, and which recipes sit well on each.
const PLAN = {
  minor: {
    away: { 5: 1.5, 3: 1.2, 2: 1.0, 6: 0.8, 4: 0.5 },
    recipes: { 0: ['sus2', 'add9', 'm9', 'm11', 'open9', '5+9'], 5: ['add9', 'm7', 'sus2', 'open9'], 2: ['sus2', 'add9', 'm7'],
               3: ['sus2', 'sus4', 'm9', 'm11'], 6: ['sus4', 'sus2', 'add9'], 4: ['sus4', 'm7'] },
  },
  major: {
    away: { 3: 1.4, 5: 1.2, 1: 1.0, 4: 0.9 },
    recipes: { 0: ['add9', 'sus2', '5+9', 'm9', 'open9'], 3: ['add9', 'sus2', 'm7'], 5: ['m7', 'm9', 'sus2'],
               1: ['sus2', 'm7', 'add9'], 4: ['sus4', 'add9', 'sus2'] },
  },
};

// Voice registers as semitone windows relative to the palette root (bass to top).
const REGISTERS = [[-17, -6], [-7, 2], [-2, 7], [3, 12], [8, 17]];

// Scene intensities: how much the bed opens up for each phrase of the edit.
const SCENE = { dwell: 0.28, voice: 0.2, jumpcut: 0.35, juxtapose: 0.45, build: 0.65, burst: 0.9, climax: 1.0, black: 0.12, empty: 0.2, wait: 0.3 };

// Cancel pending automation at t and hold whatever value the curve has there (no snap back to "now").
function hold(param, t, floor = 0.0001) {
  if (param.cancelAndHoldAtTime) {
    param.cancelAndHoldAtTime(t);
  } else {
    const v = Math.max(floor, param.value);
    param.cancelScheduledValues(t);
    param.setValueAtTime(v, t);
  }
}

export class WashGenerator {
  constructor(engine, params = {}, rng) {
    this.e = engine;
    this.ctx = engine.ctx;
    this.rng = rng;
    this.p = Object.assign({
      root: 57, mode: 'aeolian', chordSeconds: [20, 36], glide: [4, 8], level: 0.5, brightness: 0.35,
      motion: 0.4, strings: 1, choir: 0.7, air: 0.6, sub: 0.8, shimmer: 0.6, dissonance: 0.0, voices: 4,
    }, params);
    this.scale = MODES_SCALES[this.p.mode] || MODES_SCALES.aeolian;
    this.plan = MAJOR_FAMILY.has(this.p.mode) ? PLAN.major : PLAN.minor;
    this.voices = [];
    this.alive = false;
    this.intensity = 0.3;
    this.targetIntensity = 0.3;
    this.degree = 0;
    this.pull = null;          // 'away' (tension) or 'home' (arrival), set by the edit
    this.chordPcs = [];
    this.nextChordAt = 0;
    this.nextShimmerAt = 0;
    this.holdUntil = 0;        // the scene gain is left alone until then (a drop needs its silence)
    this.timer = null;
    this.lfos = [];
  }

  // ---- graph ----------------------------------------------------------------------------------

  start() {
    const ctx = this.ctx, now = ctx.currentTime;
    this.alive = true;
    // mix -> compressor -> scene gain (swell/drop) -> breath -> music bus; the reverb returns into breath
    this.mix = ctx.createGain();
    this.comp = ctx.createDynamicsCompressor();
    this.comp.threshold.value = -10;
    this.comp.knee.value = 10;
    this.comp.ratio.value = 2;
    this.comp.attack.value = 0.2;
    this.comp.release.value = 0.8;
    this.scene = ctx.createGain();
    this.scene.gain.value = this.p.level;
    this.breath = ctx.createGain();
    this.breath.gain.value = 0.0001;
    this.mix.connect(this.comp);
    this.comp.connect(this.scene);
    this.scene.connect(this.breath);
    this.breath.connect(this.e.musicBus);

    // long reverb: highpassed send, pre-delay, exponential 10 s tail that darkens, returned after the scene gain
    this.send = ctx.createGain();
    this.send.gain.value = 0.9;
    this.sendHp = ctx.createBiquadFilter();
    this.sendHp.type = 'highpass';
    this.sendHp.frequency.value = 180;
    this.predelay = ctx.createDelay(1);
    this.predelay.delayTime.value = 0.07;
    this.verb = ctx.createConvolver();
    this.verb.buffer = this.makeIR(10);
    this.verbTone = ctx.createBiquadFilter();
    this.verbTone.type = 'lowpass';
    this.verbTone.frequency.value = 5600;
    this.verbReturn = ctx.createGain();
    this.verbReturn.gain.value = this.p.level;
    this.send.connect(this.sendHp);
    this.sendHp.connect(this.predelay);
    this.predelay.connect(this.verb);
    this.verb.connect(this.verbTone);
    this.verbTone.connect(this.verbReturn);
    this.verbReturn.connect(this.breath);

    // strings bus: highpass under the sub, a lowpass that opens with intensity and wanders, gentle drift
    this.stringsHp = ctx.createBiquadFilter();
    this.stringsHp.type = 'highpass';
    this.stringsHp.frequency.value = 85;
    this.stringsFilter = ctx.createBiquadFilter();
    this.stringsFilter.type = 'lowpass';
    this.stringsFilter.Q.value = 0.6;
    this.stringsFilter.frequency.value = 800;
    this.stringsGain = ctx.createGain();
    this.stringsGain.gain.value = 0.0001;
    this.stringsHp.connect(this.stringsFilter);
    this.stringsFilter.connect(this.stringsGain);
    this.stringsOut = this.panned(this.stringsGain, 0.023, 0.2);
    this.lfo(this.stringsFilter.frequency, 0.045 * (0.6 + this.p.motion), 160);

    // choir bus: three formant bands in parallel, drifting the other way
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
    this.choirOut = this.panned(this.choirGain, 0.019, 0.25);

    // air: filtered noise, a wandering band, half of it straight into the room
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
    this.airDirect.gain.value = 1.2;
    this.airGain.connect(this.airDirect);
    this.airDirect.connect(this.mix);
    this.lfo(this.airBand.frequency, 0.017, 1100);
    this.noise.start(now);

    // sub: one sine two octaves under the root, barely moving
    this.subOsc = ctx.createOscillator();
    this.subOsc.type = 'sine';
    this.subOsc.frequency.value = midiToFreq(this.p.root - 24);
    this.subGain = ctx.createGain();
    this.subGain.gain.value = 0.0001;
    this.subOsc.connect(this.subGain);
    this.subGain.connect(this.mix);
    this.subOsc.start(now);
    this.lfo(this.subGain.gain, 0.021, 0.012);

    // breathing: the whole bed, tail included, rises and falls over about half a minute
    this.lfo(this.breath.gain, 0.035, 0.15);
    this.breath.gain.setTargetAtTime(1, now, 4);

    this.playChord(now + 0.05, true);
    this.nextChordAt = now + this.interval();
    this.nextShimmerAt = now + this.rng.range(8, 16);
    this.applyIntensity(true);
    this.timer = setInterval(() => this.tick(), 250);
  }

  panned(node, hz, depth) {
    if (!this.ctx.createStereoPanner) {
      node.connect(this.mix);
      node.connect(this.send);
      return node;
    }
    const pan = this.ctx.createStereoPanner();
    node.connect(pan);
    pan.connect(this.mix);
    pan.connect(this.send);
    this.lfo(pan.pan, hz, depth);
    return pan;
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
        const white = Math.random() * 2 - 1;
        lp += (white - lp) * (0.55 - 0.45 * t);          // the tail darkens as it decays
        d[i] = lp * Math.exp(-6.9 * t) * (i < rate * 0.02 ? i / (rate * 0.02) : 1);   // true RT60 = length
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

  interval() {
    return this.rng.range(this.p.chordSeconds[0], this.p.chordSeconds[1]) * (1 - 0.2 * this.intensity);
  }

  nextDegree() {
    const away = Object.keys(this.plan.away).map(Number);
    const pickAway = () => this.rng.weighted(away, (d) => this.plan.away[d]);
    if (this.pull === 'home') return 0;
    if (this.pull === 'away') return pickAway();
    if (this.degree === 0) return this.rng.chance(0.7) ? pickAway() : 0;
    return this.rng.chance(0.55) ? 0 : pickAway();
  }

  // pitch classes of the chord, most important first (root, colours, third, fifth)
  chordClasses(degree) {
    const names = this.plan.recipes[degree] || Object.keys(RECIPES);
    const name = this.rng.pick(names);
    const pcs = [];
    for (const t of RECIPES[name]) {
      const d = degree + t;
      const pc = ((this.scale[d % 7] + 12 * Math.floor(d / 7)) % 12 + 12) % 12;
      if (!pcs.includes(pc)) pcs.push(pc);
    }
    if (this.p.dissonance > 0 && this.rng.chance(this.p.dissonance)) {
      const sigh = ((this.scale[5] + (this.plan === PLAN.minor ? 0 : 1)) % 12 + 12) % 12;   // the b6 (or b2 in major)
      if (!pcs.includes(sigh)) pcs.splice(1, 0, sigh);
    }
    return { name, pcs };
  }

  // nearest pitch with this class inside a register window, measured from a reference pitch
  pitchInRegister(pc, register, from) {
    const [lo, hi] = [this.p.root + register[0], this.p.root + register[1]];
    let best = null;
    for (let m = lo; m <= hi; m++) {
      if (((m % 12) + 12) % 12 !== pc) continue;
      if (best === null || Math.abs(m - from) < Math.abs(best - from)) best = m;
    }
    return best;
  }

  playChord(at, first = false) {
    this.degree = this.nextDegree();
    this.pull = null;
    const { name, pcs } = this.chordClasses(this.degree);
    this.chordName = name;
    this.chordPcs = pcs;
    const n = Math.max(3, Math.min(REGISTERS.length, this.p.voices + (this.intensity > 0.6 ? 1 : 0), pcs.length + 1));
    const glide = first ? 0 : this.rng.range(this.p.glide[0], this.p.glide[1]);
    const kept = [];
    for (let i = 0; i < n; i++) {
      const pc = pcs[i % pcs.length];
      const v = this.voices.find((x) => x.register === i && !x.dying);
      const from = v ? v.midi : this.p.root + (REGISTERS[i][0] + REGISTERS[i][1]) / 2;
      const target = this.pitchInRegister(pc, REGISTERS[i], from);
      if (target === null) { if (v) this.releaseVoice(v, at, glide + 2); continue; }
      if (v && Math.abs(target - v.midi) <= 5) {
        this.glideVoice(v, target, at, glide);            // a small move: the section slides
        kept.push(v);
      } else {
        if (v) this.releaseVoice(v, at, glide + 2);       // a big move: one voice fades as another arrives
        kept.push(this.makeVoice(target, i, at, first ? 6 : glide + 3));
      }
    }
    for (const v of this.voices) if (!kept.includes(v) && !v.dying) this.releaseVoice(v, at, glide + 2);
    this.voices = kept;
    this.e.emitOnsetAt(1.3, at + glide * 0.5);
  }

  makeVoice(midi, register, at, attack) {
    const ctx = this.ctx;
    const f = midiToFreq(midi);
    const strEnv = ctx.createGain();
    const choirEnv = ctx.createGain();
    for (const env of [strEnv, choirEnv]) {
      env.gain.setValueAtTime(0.0001, at);
      env.gain.exponentialRampToValueAtTime(1, at + attack);
    }
    const oscs = [];
    // strings: two gently detuned saws and a triangle for body, all at pitch; the sub owns the bottom
    for (const [type, det, amp] of [['sawtooth', -4.5, 0.15], ['sawtooth', 4, 0.15], ['triangle', 0, 0.14]]) {
      const o = ctx.createOscillator();
      o.type = type;
      o.frequency.value = f;
      o.detune.value = det + this.rng.range(-2, 2);
      const g = ctx.createGain();
      g.gain.value = amp * this.p.strings;
      o.connect(g);
      g.connect(strEnv);
      o.start(at);
      oscs.push({ o, mult: 1 });
    }
    // choir: three sine partials with slow vibrato into the formant bank
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
      g.connect(choirEnv);
      o.start(at);
      oscs.push({ o, mult });
    }
    strEnv.connect(this.stringsHp);
    choirEnv.connect(this.choirIn);
    return { midi, register, strEnv, choirEnv, oscs, vib, dying: false };
  }

  glideVoice(v, midi, at, glide) {
    if (v.midi === midi) return;
    for (const { o, mult } of v.oscs) {
      hold(o.frequency, at, 1);
      o.frequency.exponentialRampToValueAtTime(midiToFreq(midi) * mult, at + Math.max(0.05, glide));
    }
    v.midi = midi;
  }

  releaseVoice(v, at, release) {
    v.dying = true;
    for (const env of [v.strEnv, v.choirEnv]) {
      hold(env.gain, at);
      env.gain.exponentialRampToValueAtTime(0.0001, at + release);
    }
    const idx = this.lfos.indexOf(v.vib);
    if (idx >= 0) this.lfos.splice(idx, 1);
    setTimeout(() => {
      for (const { o } of v.oscs) { try { o.stop(); } catch (e) { /* already stopped */ } }
      try { v.vib.stop(); } catch (e) { /* ignore */ }
      try { v.strEnv.disconnect(); v.choirEnv.disconnect(); } catch (e) { /* ignore */ }
    }, Math.max(0, at - this.ctx.currentTime + release + 0.5) * 1000);
  }

  // one high chord tone, slightly sharp, seven seconds to arrive, eleven to leave, mostly in the room
  shimmer(at, rise = 7, fall = 11, level = 0.08) {
    const pc = this.chordPcs.length ? this.rng.pick(this.chordPcs) : this.p.root % 12;
    const midi = this.pitchInRegister(pc, [19, 30], this.p.root + 24) ?? this.p.root + 24;
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(level * this.p.shimmer, at + rise);
    g.gain.exponentialRampToValueAtTime(0.0001, at + rise + fall);
    g.connect(this.send);
    const dry = this.ctx.createGain();
    dry.gain.value = 0.25;
    g.connect(dry);
    dry.connect(this.mix);
    for (const [mult, amp, det] of [[1, 1, 8], [2, 0.35, -5]]) {
      const o = this.ctx.createOscillator();
      o.type = 'sine';
      o.frequency.value = midiToFreq(midi) * mult;
      o.detune.value = det;
      const ag = this.ctx.createGain();
      ag.gain.value = amp;
      o.connect(ag);
      ag.connect(g);
      o.start(at);
      o.stop(at + rise + fall + 0.5);
    }
  }

  // ---- following the edit ---------------------------------------------------------------------

  setScene(phrase, cue) {
    this.targetIntensity = SCENE[phrase] ?? 0.4;
    const now = this.ctx.currentTime;
    const g = this.scene.gain;
    if (phrase === 'build' && this.degree === 0 && !this.pull) {
      // tension: leave home soon
      this.pull = 'away';
      this.nextChordAt = Math.min(this.nextChordAt, now + this.rng.range(1, 3));
    }
    if (phrase === 'climax') {
      // the swell: rise to the top of the shot, arrive home there, one shimmer reserved for it
      const top = now + Math.min(3, (cue?.dur || 3) * 0.8);
      hold(g, now);
      g.linearRampToValueAtTime(this.p.level * 1.35, top);
      g.setTargetAtTime(this.p.level * 1.15, top, 4);
      this.pull = 'home';
      this.nextChordAt = Math.max(now + 0.4, Math.min(this.nextChordAt, top));
      if (this.p.shimmer > 0) this.shimmer(now, Math.max(1.5, top - now), 12, 0.11);
      this.nextShimmerAt = now + 20;
      this.holdUntil = top + 2;
      this.e.emitOnsetAt(2.0, top);
    } else if (phrase === 'black') {
      // the drop: the bed falls away, the reverb carries, and nothing pulls it back up for a while
      hold(g, now);
      g.exponentialRampToValueAtTime(this.p.level * 0.15, now + 0.4);
      g.setTargetAtTime(this.p.level, now + 0.6, 6);
      this.holdUntil = now + 4;
      this.nextChordAt = Math.max(this.nextChordAt, now + (cue?.dur || 1) + 2);   // no harmony moves in the dark
    } else if (now >= this.holdUntil) {
      hold(g, now);
      g.setTargetAtTime(this.p.level, now, 2.5);
    }
  }

  applyIntensity(immediate = false) {
    const i = this.intensity, b = this.p.brightness;
    const now = this.ctx.currentTime, tc = immediate ? 0.01 : 1.6;
    this.stringsFilter.frequency.setTargetAtTime(420 + (900 + 3200 * b) * Math.pow(i, 1.3), now, tc);
    this.stringsGain.gain.setTargetAtTime((0.2 + 0.36 * i) * this.p.strings, now, tc);
    this.choirGain.gain.setTargetAtTime((0.1 + 0.26 * i) * this.p.choir, now, tc);
    this.airGain.gain.setTargetAtTime((0.05 + 0.15 * i) * this.p.air, now, tc);
    this.subGain.gain.setTargetAtTime((0.05 + 0.05 * (1 - i)) * this.p.sub, now, tc);
    this.send.gain.setTargetAtTime(0.75 + 0.4 * (1 - i), now, tc);
  }

  tick() {
    if (!this.alive) return;
    const now = this.ctx.currentTime;
    this.intensity += (this.targetIntensity - this.intensity) * 0.12;
    this.applyIntensity();
    if (now >= this.nextChordAt - 0.3) {
      // never schedule in the past: after a throttled background tab the clock simply resyncs
      const at = Math.max(this.nextChordAt, now + 0.05);
      this.playChord(at);
      this.nextChordAt = at + this.interval();
    }
    if (now >= this.nextShimmerAt) {
      if (this.p.shimmer > 0 && this.rng.chance(0.25 + 0.5 * this.intensity)) this.shimmer(now + 0.1);
      this.nextShimmerAt = now + this.rng.range(14, 30);
    }
  }

  stop() {
    this.alive = false;
    clearInterval(this.timer);
    const now = this.ctx.currentTime;
    hold(this.breath.gain, now);
    this.breath.gain.exponentialRampToValueAtTime(0.0001, now + 1.8);
    setTimeout(() => {
      for (const v of this.voices) { for (const { o } of v.oscs) { try { o.stop(); } catch (e) { /* ignore */ } } try { v.vib.stop(); } catch (e) { /* ignore */ } }
      for (const o of this.lfos) { try { o.stop(); } catch (e) { /* ignore */ } }
      try { this.noise.stop(); this.subOsc.stop(); } catch (e) { /* ignore */ }
      try { this.breath.disconnect(); this.verbReturn.disconnect(); } catch (e) { /* ignore */ }
    }, 2200);
  }
}
