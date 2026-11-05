// The wash: an emotive ambient bed with almost no notes. Layers of detuned strings, a formant choir, a
// breath of filtered noise, a sub and an occasional shimmer, moving through slow suspended harmony with
// a home (the tonic) and colours away from it. Voices live in registers and are led by pitch class: small
// moves glide, big ones crossfade like a section changing bow. The reverb is fed after the scene gain, so a
// drop leaves only the decaying room (and the sub, which lives outside the drop). The player tells the bed
// which phrase is on screen: tension is put in place before a build, harmony freezes under the build and
// the burst, the climax arrives (home, or deceptively, or hollow) at the top of its swell with the motif
// tone, and the cut to black lets the bed fall away; one black in five is a cold open of sub and air.

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

// Where the harmony lives: a home degree, the colours it drifts to (weighted), the deceptive arrival,
// and which recipes sit well on each degree.
const PLAN = {
  minor: {
    away: { 5: 1.5, 3: 1.2, 2: 1.0, 6: 0.8, 4: 0.5 }, deceptive: 5,
    recipes: { 0: ['sus2', 'add9', 'm9', 'm11', 'open9', '5+9'], 5: ['add9', 'm7', 'sus2', 'open9'], 2: ['sus2', 'add9', 'm7'],
               3: ['sus2', 'sus4', 'm9', 'm11'], 6: ['sus4', 'sus2', 'add9'], 4: ['sus4', 'm7'] },
  },
  dorian: {
    away: { 3: 1.5, 1: 1.0, 2: 0.9, 6: 0.8 }, deceptive: 3,
    recipes: { 0: ['sus2', 'add9', 'm9', 'm11', 'open9', '5+9'], 3: ['add9', 'sus2', 'm7'], 1: ['sus2', 'm7', 'add9'],
               2: ['sus2', 'add9'], 6: ['sus4', 'sus2', 'add9'] },
  },
  major: {
    away: { 3: 1.4, 5: 1.2, 1: 1.0, 4: 0.9 }, deceptive: 5,
    recipes: { 0: ['add9', 'sus2', '5+9', 'm9', 'open9'], 3: ['add9', 'sus2', 'm7'], 5: ['m7', 'm9', 'sus2'],
               1: ['sus2', 'm7', 'add9'], 4: ['sus4', 'add9', 'sus2'] },
  },
};

// Voice registers as semitone windows relative to the palette root (bass to top); every window spans a
// full octave so every pitch class can be found in it.
const REGISTERS = [[-17, -6], [-7, 4], [-2, 9], [3, 14], [8, 19]];

// Scene intensities: one big step at the build, a hold under the burst, the last half octave at the climax.
const SCENE = { dwell: 0.28, voice: 0.2, jumpcut: 0.3, juxtapose: 0.32, build: 0.7, burst: 0.72, climax: 1.0, black: 0.12, empty: 0.2, wait: 0.3 };

// Cancel pending automation at t and anchor the current value explicitly, so the next ramp starts from
// where the parameter really is (cancelAndHoldAtTime alone inserts nothing once a ramp has finished).
function hold(param, t, now, floor = 0.0001) {
  const v = Math.max(floor, param.value);
  if (param.cancelAndHoldAtTime) {
    param.cancelAndHoldAtTime(t);
    param.setValueAtTime(v, Math.max(now, t));
  } else {
    param.cancelScheduledValues(now);
    param.setValueAtTime(v, now);
    if (t > now) param.setValueAtTime(v, t);
  }
}

export class WashGenerator {
  constructor(engine, params = {}, rng) {
    this.e = engine;
    this.ctx = engine.ctx;
    this.rng = rng;
    this.p = Object.assign({
      root: 57, mode: 'aeolian', chordSeconds: [20, 36], glide: [4, 8], level: 0.3, brightness: 0.35,
      motion: 0.4, strings: 1, choir: 0.7, air: 0.6, sub: 0.8, shimmer: 0.6, dissonance: 0.0, voices: 4,
    }, params);
    this.scale = MODES_SCALES[this.p.mode] || MODES_SCALES.aeolian;
    this.plan = this.p.mode === 'dorian' ? PLAN.dorian : MAJOR_FAMILY.has(this.p.mode) ? PLAN.major : PLAN.minor;
    this.tonic = ((this.p.root % 12) + 12) % 12;
    this.voices = [];
    this.alive = false;
    this.intensity = 0.3;
    this.targetIntensity = 0.3;
    this.degree = 0;
    this.pull = null;          // 'away' (tension), 'home' or 'deceptive' (arrival), set by the edit
    this.chordPcs = [];
    this.nextChordAt = 0;
    this.nextShimmerAt = 0;
    this.holdUntil = 0;        // the scene gain is left alone until then (a drop needs its silence)
    this.riserUntil = 0;
    this.phrase = null;
    this.lastClimax = null;
    this.lastCold = -9;
    this.timer = null;
    this.sources = [];         // every oscillator and buffer source, stopped on the audio clock in stop()
  }

  // ---- graph ----------------------------------------------------------------------------------

  start() {
    const ctx = this.ctx, now = ctx.currentTime;
    this.alive = true;
    // mix -> compressor -> scene gain (swell/drop) -> breath (slow LFO) -> out (fade stage) -> music bus
    this.mix = ctx.createGain();
    this.comp = ctx.createDynamicsCompressor();
    this.comp.threshold.value = -14;
    this.comp.knee.value = 8;
    this.comp.ratio.value = 2;
    this.comp.attack.value = 0.3;
    this.comp.release.value = 2.0;
    this.scene = ctx.createGain();
    this.scene.gain.value = this.p.level;
    this.breath = ctx.createGain();
    this.breath.gain.value = 1;
    this.out = ctx.createGain();
    this.out.gain.value = 0.0001;
    this.mix.connect(this.comp);
    this.comp.connect(this.scene);
    this.scene.connect(this.breath);
    this.breath.connect(this.out);
    this.out.connect(this.e.musicBus);

    // long reverb, fed after the scene gain so swells and drops reach the room; highpassed send,
    // pre-delay, exponential 10 s tail that darkens
    this.send = ctx.createGain();
    this.send.gain.value = 0.8;
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
    this.verbReturn.gain.value = 1;
    this.scene.connect(this.send);
    this.send.connect(this.sendHp);
    this.sendHp.connect(this.predelay);
    this.predelay.connect(this.verb);
    this.verb.connect(this.verbTone);
    this.verbTone.connect(this.verbReturn);
    this.verbReturn.connect(this.breath);

    // strings bus: highpass under the sub, a lowpass that opens with intensity and wanders, a little drift
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
    this.panned(this.stringsGain, 0.023, 0.06);
    this.lfo(this.stringsFilter.frequency, 0.045 * (0.6 + this.p.motion), 160);

    // choir bus: three wide formant bands in parallel, drifting the other way
    this.choirIn = ctx.createGain();
    this.choirGain = ctx.createGain();
    this.choirGain.gain.value = 0.0001;
    for (const [f, q, g] of [[720, 1.5, 1], [1150, 2, 0.8], [2500, 2, 0.65]]) {
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
    this.panned(this.choirGain, 0.019, 0.08);

    // air: filtered noise, a wandering band; most of it dry, a little straight into the room so the
    // dark keeps breathing
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
    this.airDirect = ctx.createGain();
    this.airDirect.gain.value = 1.2;
    this.airGain.connect(this.airDirect);
    this.airDirect.connect(this.mix);
    this.airRoom = ctx.createGain();
    this.airRoom.gain.value = 0.4;
    this.airGain.connect(this.airRoom);
    this.airRoom.connect(this.sendHp);
    this.lfo(this.airBand.frequency, 0.017, 1100);
    this.noise.start(now);
    this.sources.push(this.noise);

    // sub: one sine under the root, outside the scene gain so it is the floor in the dark
    this.subOsc = ctx.createOscillator();
    this.subOsc.type = 'sine';
    this.subOsc.frequency.value = midiToFreq(this.p.root - (this.p.root >= 55 ? 24 : 12));
    this.subGain = ctx.createGain();
    this.subGain.gain.value = 0.0001;
    this.subLfo = ctx.createGain();
    this.subLfo.gain.value = 1;
    this.subOsc.connect(this.subGain);
    this.subGain.connect(this.subLfo);
    this.subLfo.connect(this.breath);
    this.subOsc.start(now);
    this.sources.push(this.subOsc);
    this.lfo(this.subLfo.gain, 0.021, 0.08);

    // breathing: slower than the edit's cycle, about a decibel either way
    this.lfo(this.breath.gain, 0.012, 0.12);
    this.out.gain.setTargetAtTime(1, now, 4);

    this.playChord(now + 0.05, { first: true });
    this.nextChordAt = now + this.interval();
    this.nextShimmerAt = now + this.rng.range(8, 16);
    this.applyIntensity(true);
    this.timer = setInterval(() => this.tick(), 250);
  }

  panned(node, hz, depth) {
    if (!this.ctx.createStereoPanner) { node.connect(this.mix); return node; }
    const pan = this.ctx.createStereoPanner();
    node.connect(pan);
    pan.connect(this.mix);
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
    this.sources.push(o);
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
    if (this.pull === 'deceptive') return this.plan.deceptive;
    if (this.pull === 'away') return pickAway();
    if (this.degree === 0) return this.rng.chance(0.7) ? pickAway() : 0;
    return this.rng.chance(0.55) ? 0 : pickAway();
  }

  // absolute pitch classes of the chord, most important first (root, colours, third, fifth)
  chordClasses(degree, prefer = null) {
    const names = this.plan.recipes[degree] || Object.keys(RECIPES);
    const name = prefer && names.includes(prefer) ? prefer : this.rng.pick(names);
    const pcs = [];
    for (const t of RECIPES[name]) {
      const d = degree + t;
      const pc = ((this.p.root + this.scale[d % 7]) % 12 + 12) % 12;
      if (!pcs.includes(pc)) pcs.push(pc);
    }
    if (this.p.dissonance > 0 && this.rng.chance(this.p.dissonance)) {
      const sigh = ((this.p.root + this.scale[5] + (this.plan === PLAN.major ? 1 : 0)) % 12 + 12) % 12;   // the b6 (a b7 in major)
      if (!pcs.includes(sigh)) pcs.splice(1, 0, sigh);
    }
    return { name, pcs };
  }

  // the pitch of this class inside a register window nearest to a reference pitch
  pitchInRegister(pc, register, from) {
    const [lo, hi] = [this.p.root + register[0], this.p.root + register[1]];
    let best = null;
    for (let m = lo; m <= hi; m++) {
      if (((m % 12) + 12) % 12 !== pc) continue;
      if (best === null || Math.abs(m - from) < Math.abs(best - from)) best = m;
    }
    return best;
  }

  // deadline: seconds in which the new chord must be audibly there (a climax top, a build pull)
  playChord(at, { first = false, deadline = null, prefer = null, hollow = false } = {}) {
    this.degree = this.nextDegree();
    this.pull = null;
    const { name, pcs } = this.chordClasses(this.degree, prefer);
    this.chordName = name;
    this.chordPcs = pcs;
    const want = hollow ? 3 : this.p.voices + (this.intensity > 0.6 ? 1 : 0);
    const n = Math.max(3, Math.min(REGISTERS.length, want, pcs.length + 1));
    const glide = first ? 0 : deadline != null ? Math.max(1.0, Math.min(2.4, deadline)) : this.rng.range(this.p.glide[0], this.p.glide[1]);
    const cross = first ? 6 : glide + (deadline != null ? 1.2 : 2.5);
    const kept = [];
    for (let i = 0; i < n; i++) {
      const pc = pcs[i % pcs.length];
      const v = this.voices.find((x) => x.register === i && !x.dying);
      const from = v ? v.midi : this.p.root + (REGISTERS[i][0] + REGISTERS[i][1]) / 2;
      const target = this.pitchInRegister(pc, REGISTERS[i], from);
      if (v && Math.abs(target - v.midi) <= 5) {
        this.glideVoice(v, target, at, glide);            // a small move: the section slides
        kept.push(v);
      } else if (v) {
        this.releaseVoice(v, at, cross, 'cross');         // a big move: one voice fades as another arrives
        kept.push(this.makeVoice(target, i, at, cross, 'cross'));
      } else {
        kept.push(this.makeVoice(target, i, at, first ? 6 : cross, 'fade'));
      }
    }
    for (const v of this.voices) if (!kept.includes(v) && !v.dying) this.releaseVoice(v, at, cross, 'fade');
    this.voices = kept;
    this.e.emitOnsetAt(1.3, at + glide * 0.8);
  }

  makeVoice(midi, register, at, attack, shape) {
    const ctx = this.ctx;
    const f = midiToFreq(midi);
    const strEnv = ctx.createGain();
    const choirEnv = ctx.createGain();
    for (const env of [strEnv, choirEnv]) {
      if (shape === 'cross') {
        env.gain.setValueAtTime(0, at);
        env.gain.linearRampToValueAtTime(1, at + attack);
      } else {
        env.gain.setValueAtTime(0.0001, at);
        env.gain.exponentialRampToValueAtTime(1, at + attack);
      }
    }
    const oscs = [];
    // strings: two gently detuned saws beating across the stereo field, a triangle for body
    for (const [type, det, amp, pan] of [['sawtooth', -4.5, 0.15, -0.35], ['sawtooth', 4, 0.15, 0.35], ['triangle', 0, 0.14, 0]]) {
      const o = ctx.createOscillator();
      o.type = type;
      o.frequency.value = f;
      o.detune.value = det + this.rng.range(-2, 2);
      const g = ctx.createGain();
      g.gain.value = amp * this.p.strings;
      o.connect(g);
      if (pan && ctx.createStereoPanner) {
        const pn = ctx.createStereoPanner();
        pn.pan.value = pan;
        g.connect(pn);
        pn.connect(strEnv);
      } else {
        g.connect(strEnv);
      }
      o.start(at);
      oscs.push({ o, mult: 1 });
    }
    // choir: four sine partials with slow vibrato into the formant bank
    const vib = ctx.createOscillator();
    vib.type = 'sine';
    vib.frequency.value = 4.6 + this.rng.range(0, 1.2);
    const vibDepth = ctx.createGain();
    vibDepth.gain.setValueAtTime(0, at);
    vibDepth.gain.linearRampToValueAtTime(7, at + attack * 1.5);
    vib.connect(vibDepth);
    vib.start(at);
    for (const [mult, amp] of [[1, 0.5], [2, 0.3], [3, 0.18], [4, 0.08]]) {
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
    const voice = { midi, register, strEnv, choirEnv, oscs, vib, startAt: at, dying: false };
    this.sources.push(vib, ...oscs.map((x) => x.o));
    return voice;
  }

  glideVoice(v, midi, at, glide) {
    if (v.midi === midi) return;
    const now = this.ctx.currentTime;
    for (const { o, mult } of v.oscs) {
      hold(o.frequency, at, now, 1);
      o.frequency.exponentialRampToValueAtTime(midiToFreq(midi) * mult, at + Math.max(0.05, glide));
    }
    v.midi = midi;
  }

  releaseVoice(v, at, release, shape) {
    v.dying = true;
    const now = this.ctx.currentTime;
    const end = at + release;
    if (at <= v.startAt + 0.05) {
      // never started: silence it before it begins
      for (const env of [v.strEnv, v.choirEnv]) { env.gain.cancelScheduledValues(0); env.gain.setValueAtTime(0.0001, now); }
    } else {
      for (const env of [v.strEnv, v.choirEnv]) {
        hold(env.gain, at, now);
        if (shape === 'cross') env.gain.linearRampToValueAtTime(0, end);
        else env.gain.exponentialRampToValueAtTime(0.0001, end);
      }
    }
    const stopAt = Math.max(end, v.startAt) + 0.5;
    for (const { o } of v.oscs) { try { o.stop(stopAt); } catch (e) { /* already scheduled */ } }
    try { v.vib.stop(stopAt); } catch (e) { /* ignore */ }
    v.oscs[0].o.onended = () => { try { v.strEnv.disconnect(); v.choirEnv.disconnect(); } catch (e) { /* ignore */ } };
  }

  // one high tone, usually the tonic two octaves up (the motif), slightly sharp, slow to arrive, mostly
  // in the room
  shimmer(at, rise = 7, fall = 11, level = 0.08, motif = false) {
    const pc = motif || this.rng.chance(0.75) ? this.tonic : (this.chordPcs.length ? this.rng.pick(this.chordPcs) : this.tonic);
    const midi = this.pitchInRegister(pc, [19, 30], this.p.root + 24) ?? this.p.root + 24;
    const g = this.ctx.createGain();
    g.gain.setValueAtTime(0.0001, at);
    g.gain.exponentialRampToValueAtTime(level * this.p.shimmer, at + rise);
    g.gain.exponentialRampToValueAtTime(0.0001, at + rise + fall);
    const room = this.ctx.createGain();
    room.gain.value = 0.7;
    g.connect(room);
    room.connect(this.sendHp);
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
    const prev = this.phrase;
    this.phrase = phrase;

    // tension is put in place as the edit starts moving, so the colour chord is there when the build hits
    if ((phrase === 'jumpcut' || phrase === 'juxtapose' || phrase === 'build') && this.degree === 0 && !this.pull) {
      this.pull = 'away';
      this.nextChordAt = Math.min(this.nextChordAt, now + this.rng.range(1, 3));
    }
    // and nothing moves harmonically under the build and the burst
    if ((phrase === 'build' || phrase === 'burst') && !this.pull) this.nextChordAt = Math.max(this.nextChordAt, now + 5);
    if (phrase === 'build' && prev !== 'build') this.riserUntil = now + 8;

    if (phrase === 'climax') {
      const top = now + Math.min(3, (cue?.dur || 3) * 0.8);
      const r = this.rng.next();
      let kind = r < 0.55 ? 'full' : r < 0.8 ? 'deceptive' : 'hollow';
      if (kind === 'hollow' && this.lastClimax === 'hollow') kind = 'full';
      this.lastClimax = kind;
      hold(g, now, now);
      if (kind === 'hollow') {
        // the swell withheld: the bed thins to three voices and the motif alone rises
        g.setTargetAtTime(this.p.level * 0.85, now, 1.5);
        this.intensity = Math.min(this.intensity, 0.45);
        this.pull = 'home';
        this.playChord(now + 0.05, { deadline: Math.max(1.0, top - now - 0.2), prefer: 'open9', hollow: true });
      } else {
        g.linearRampToValueAtTime(this.p.level * (kind === 'full' ? 1.35 : 1.2), top);
        g.setTargetAtTime(this.p.level * 1.15, top, 4);
        this.intensity = Math.max(this.intensity, 0.85);
        this.pull = kind === 'full' ? 'home' : 'deceptive';
        this.playChord(now + 0.05, { deadline: Math.max(1.0, top - now - 0.2) });
      }
      this.nextChordAt = top + this.interval();
      if (this.p.shimmer > 0) this.shimmer(now, Math.max(1.5, top - now), 12, 0.11, true);
      this.nextShimmerAt = now + 20;
      this.holdUntil = top + 2;
      this.e.emitOnsetAt(2.0, top);
      this.riserUntil = 0;
    } else if (phrase === 'black') {
      // the drop: the bed falls away, the room and the sub carry; the texture resets for the dwell after
      const cyc = cue?.cycle ?? 0;
      const silent = (cue?.audio?.duck ?? 1) === 0;
      const cold = cyc - this.lastCold >= 4 && this.rng.chance(0.2);
      hold(g, now, now);
      this.intensity = Math.min(this.intensity, 0.35);
      this.riserUntil = 0;
      if (cold) {
        // the cold open: ten to sixteen seconds of sub and air, then the bed returns slowly on the tonic
        this.lastCold = cyc;
        g.exponentialRampToValueAtTime(this.p.level * 0.02, now + 0.6);
        this.holdUntil = now + this.rng.range(10, 16);
        g.setTargetAtTime(this.p.level, this.holdUntil, 5);
        this.pull = 'home';
        this.nextChordAt = Math.max(this.nextChordAt, this.holdUntil + 3);
      } else if (silent) {
        g.exponentialRampToValueAtTime(this.p.level * 0.02, now + 0.4);
        const back = now + (cue?.dur || 1);
        g.setTargetAtTime(this.p.level, back, 8);
        this.holdUntil = back + 6;
        this.nextChordAt = Math.max(this.nextChordAt, back + 2);
      } else {
        g.exponentialRampToValueAtTime(this.p.level * 0.15, now + 0.4);
        g.setTargetAtTime(this.p.level, now + 0.6, 6);
        this.holdUntil = now + 4;
        this.nextChordAt = Math.max(this.nextChordAt, now + (cue?.dur || 1) + 2);
      }
    } else if (now >= this.holdUntil) {
      hold(g, now, now);
      if (prev === 'voice' && phrase !== 'voice') {
        // after someone has spoken the bed comes back at half and fills in
        g.linearRampToValueAtTime(this.p.level * 0.5, now + 0.1);
        g.setTargetAtTime(this.p.level, now + 0.1, 3);
      } else {
        g.setTargetAtTime(this.p.level, now, 2.5);
      }
    }
  }

  applyIntensity(immediate = false) {
    const i = this.intensity, b = this.p.brightness;
    const now = this.ctx.currentTime, tc = immediate ? 0.01 : 1.6;
    const riser = now < this.riserUntil ? 1 + 0.5 * (1 - (this.riserUntil - now) / 8) : 1;   // the build opens further on its own
    this.stringsFilter.frequency.setTargetAtTime((420 + (900 + 3200 * b) * Math.pow(i, 1.3)) * riser, now, tc);
    this.stringsGain.gain.setTargetAtTime((0.2 + 0.36 * i) * this.p.strings, now, tc);
    this.choirGain.gain.setTargetAtTime((0.16 + 0.34 * i) * this.p.choir, now, tc);
    this.airGain.gain.setTargetAtTime((0.05 + 0.15 * i) * this.p.air, now, tc);
    this.subGain.gain.setTargetAtTime((0.045 + 0.025 * (1 - i)) * this.p.sub * this.p.level, now, tc);
    this.send.gain.setTargetAtTime(0.6 + 0.3 * (1 - i), now, tc);
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
    hold(this.out.gain, now, now);
    this.out.gain.exponentialRampToValueAtTime(0.0001, now + 1.8);
    for (const s of this.sources) { try { s.stop(now + 2.2); } catch (e) { /* already stopped */ } }
    this.noise.onended = () => { try { this.out.disconnect(); } catch (e) { /* ignore */ } };
  }
}
