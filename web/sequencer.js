// The editing brain. Produces an endless stream of "cues" (what to show, for how long, at what speed,
// with which treatment) organised into phrases that follow the corecore grammar documented in
// docs/CORECORE.md: slow emotional set-up, acceleration, a crescendo of blisteringly fast cuts,
// a held image, a cut to black. Meaning comes from juxtaposition, so clips are chosen in contrasting pairs.
import { makeRng } from './prng.js';

export const CAPTIONS = [
  "it's all so beautiful", 'we were here', 'look at us', 'are we ok', 'this is fine', 'what did we build',
  'nothing is real', 'everything is real', 'do you remember', 'you are here', 'it will all be over soon',
  'love is real', "i don't know", 'scroll', 'feel something', 'we are so lucky', 'what are we doing',
  'it was always like this', 'look up', 'keep scrolling', 'i miss everything', "it's okay to feel it",
  'the world is so big', 'we made this', 'someone filmed this', 'remember this',
];

export const QUOTES = [
  'you are allowed to begin again', 'the sun will rise and we will try again', 'look how far you have come',
  'it is never too late', 'you have survived every single day so far', 'there is still time', 'be here',
  'everything you love is alive right now', 'keep going', 'somebody is glad you exist', 'this is your life',
  'nobody is coming, and that is okay', 'small things, every day', 'you were loved before you did anything',
];

// Tag pairs the sequencer uses to build meaning by collision. Falls back to pixel-derived tags
// (bright/dark, still/motion, vivid/muted) when a pool has no hand-assigned themes.
export const CONTRAST_PAIRS = [
  ['nature', 'city'], ['nature', 'screens'], ['nature', 'industry'], ['faces', 'crowd'], ['childhood', 'work'],
  ['space', 'city'], ['archive', 'modern'], ['ads', 'war'], ['ocean', 'traffic'], ['animals', 'machines'],
  ['home', 'industry'], ['earth', 'screens'], ['news', 'nature'], ['cctv', 'nature'], ['consumerism', 'nature'],
  ['bright', 'dark'], ['still', 'motion'], ['vivid', 'muted'],
];

export const MODES = {
  corecore: {
    label: 'corecore',
    blurb: 'slow, sad, then too fast. hard cuts, grain, cut to black.',
    music: { root: 57, scale: 'minor', chordSeconds: [7, 11], pluck: 0.3, cutoff: 900 },
    cycle: ['dwell', 'juxtapose', 'build', 'burst', 'climax', 'black'],
    dwell: { clips: [1, 2], dur: [3, 6], speed: [0.6, 1.0], zoom: [1.03, 1.12], text: 0.06, fade: 0 },
    voice: { chance: 0.3, dur: [4, 8], duck: 0.3 },
    juxtapose: { chance: 0.7, pairs: [2, 4], dur: [0.7, 1.4] },
    build: { clips: [5, 9], durStart: [1.4, 2.0], durEnd: [0.4, 0.6], flash: 0.3, speed: [0.9, 1.3] },
    burst: { chance: 0.85, clips: [8, 18], dur: [0.16, 0.34], flashEnd: 0.5, shake: 0.5, speed: [1, 1.6], double: 0.1 },
    climax: { dur: [1.5, 3.0], hold: 0.4, zoom: [1.0, 1.25], text: 0.08, motif: 0.7 },
    black: { chance: 0.8, dur: [0.5, 1.8], silence: 0.3, text: 0.05 },
    fx: { grain: [0.07, 0.14], desat: 0.2, contrast: 1.08, letterbox: 0.15, bw: 0.04 },
    prefer: { brightness: -0.4 },
    textStyle: 'caption', textPool: 'captions',
  },
  hopecore: {
    label: 'hopecore',
    blurb: 'same editing, warmer: light, quotes, no cut to black.',
    music: { root: 60, scale: 'major', chordSeconds: [5, 8], pluck: 0.6, cutoff: 1800 },
    cycle: ['dwell', 'juxtapose', 'build', 'burst', 'climax', 'dwell'],
    dwell: { clips: [1, 3], dur: [3.5, 6.5], speed: [0.7, 1.0], zoom: [1.03, 1.1], text: 0.3, fade: 0.3 },
    voice: { chance: 0.2, dur: [4, 8], duck: 0.4 },
    juxtapose: { chance: 0.5, pairs: [2, 3], dur: [0.9, 1.5] },
    build: { clips: [4, 7], durStart: [1.2, 1.8], durEnd: [0.5, 0.7], flash: 0.5, speed: [0.9, 1.2] },
    burst: { chance: 0.6, clips: [5, 9], dur: [0.3, 0.5], flashEnd: 0.6, shake: 0.1, speed: [1, 1.3], double: 0.05 },
    climax: { dur: [2.5, 4], hold: 0.2, zoom: [1.0, 1.15], text: 0.5, motif: 0.5 },
    black: { chance: 0.15, dur: [0.4, 0.8], silence: 0, text: 0 },
    fx: { grain: [0.04, 0.09], desat: 0.0, contrast: 1.03, letterbox: 0.08, bw: 0 },
    prefer: { brightness: 0.5, saturation: 0.3 },
    textStyle: 'quote', textPool: 'quotes',
  },
  chaos: {
    label: 'chaos (nichetok)',
    blurb: 'the 2023 turn: nonsensical, layered, jarring speeds.',
    music: { root: 62, scale: 'minor', chordSeconds: [3, 5], pluck: 0.8, cutoff: 2500 },
    cycle: ['burst', 'juxtapose', 'build', 'burst', 'climax', 'black'],
    dwell: { clips: [1, 1], dur: [1.5, 3], speed: [0.4, 2.0], zoom: [1.0, 1.2], text: 0.1, fade: 0 },
    voice: { chance: 0.35, dur: [1.5, 4], duck: 0.2 },
    juxtapose: { chance: 0.6, pairs: [2, 5], dur: [0.4, 0.9] },
    build: { clips: [4, 8], durStart: [1.0, 1.4], durEnd: [0.25, 0.4], flash: 0.4, speed: [0.5, 2.0] },
    burst: { chance: 1, clips: [6, 14], dur: [0.2, 0.7], flashEnd: 0.4, shake: 0.6, speed: [0.5, 2.5], double: 0.35 },
    climax: { dur: [0.8, 1.6], hold: 0.6, zoom: [1.0, 1.4], text: 0.15, motif: 0.5 },
    black: { chance: 0.5, dur: [0.2, 0.6], silence: 0.5, text: 0.1 },
    fx: { grain: [0.1, 0.22], desat: 0.1, contrast: 1.15, letterbox: 0.3, bw: 0.1 },
    prefer: {},
    textStyle: 'caption', textPool: 'captions',
  },
  dwell: {
    label: 'dwell',
    blurb: 'long takes, slow push-ins, nothing happens.',
    music: { root: 50, scale: 'minor', chordSeconds: [12, 18], pluck: 0.12, cutoff: 600 },
    cycle: ['dwell', 'dwell', 'black'],
    dwell: { clips: [1, 2], dur: [5, 10], speed: [0.5, 0.8], zoom: [1.04, 1.14], text: 0, fade: 0.6 },
    voice: { chance: 0.15, dur: [6, 10], duck: 0.35 },
    juxtapose: { chance: 0, pairs: [2, 2], dur: [1, 1] },
    build: { clips: [3, 4], durStart: [2, 3], durEnd: [1, 1.5], flash: 0, speed: [0.7, 1] },
    burst: { chance: 0, clips: [4, 4], dur: [0.5, 0.5], flashEnd: 0, shake: 0, speed: [1, 1], double: 0 },
    climax: { dur: [4, 6], hold: 0.3, zoom: [1.0, 1.12], text: 0, motif: 0.5 },
    black: { chance: 0.6, dur: [1, 3], silence: 0.4, text: 0 },
    fx: { grain: [0.05, 0.1], desat: 0.3, contrast: 1.05, letterbox: 0.25, bw: 0.12 },
    prefer: { motion: -0.3 },
    textStyle: 'caption', textPool: 'captions',
  },
};

export class Sequencer {
  constructor({ catalog, seed = 'corecore', mode = 'corecore' }) {
    this.catalog = catalog;
    this.seed = seed;
    this.rng = makeRng(seed);
    this.cycleCount = 0;
    this.stepIndex = 0;
    this.motifs = [];
    this.theme = null;
    this.lastSource = null;
    this.customText = [];
    this.setMode(mode);
  }

  setMode(name) {
    this.mode = MODES[name] ? name : 'corecore';
    this.params = MODES[this.mode];
    this.stepIndex = 0;
  }

  reseed(seed) {
    this.seed = seed;
    this.rng = makeRng(seed);
    this.stepIndex = 0;
    this.motifs = [];
  }

  async nextPhrase() {
    await this.catalog.ensure(40);
    if (this.stepIndex === 0) this.beginCycle();
    const cycle = this.params.cycle;
    const name = cycle[this.stepIndex % cycle.length];
    this.stepIndex = (this.stepIndex + 1) % cycle.length;
    const fn = this[`phrase_${name}`];
    const cues = fn ? fn.call(this) : [];
    for (const c of cues) {
      c.phrase = c.phrase || name;
      c.cycle = this.cycleCount;
    }
    return cues;
  }

  beginCycle() {
    this.cycleCount++;
    const counts = this.catalog.stats.tags || {};
    const avail = Object.keys(counts).filter((t) => counts[t] >= 4);
    const pairs = CONTRAST_PAIRS.filter(([a, b]) => avail.includes(a) && avail.includes(b));
    this.theme = pairs.length ? this.rng.pick(pairs).slice() : null;
    if (this.theme && this.rng.chance(0.5)) this.theme.reverse();
    if (!this.motifs.length || this.rng.chance(0.6)) {
      this.motifs = [];
      for (let i = 0; i < 2; i++) {
        const m = this.catalog.take({ tags: ['faces', 'bright', 'vivid'], prefer: { motion: -0.3 }, minDuration: 2 }, this.rng);
        if (m) this.motifs.push(m);
      }
    }
  }

  themeTags(side) {
    return this.theme ? [this.theme[side]] : [];
  }

  pickClip(filter = {}) {
    const f = Object.assign({}, filter);
    f.prefer = Object.assign({}, this.params.prefer, filter.prefer || {});
    f.sourceAvoid = this.lastSource;
    const c = this.catalog.take(f, this.rng);
    if (c) this.lastSource = c.source_id;
    return c;
  }

  letterbox() {
    const fx = this.params.fx;
    return this.rng.chance(fx.letterbox) ? this.rng.pick(['4:3', 'scope']) : null;
  }

  maybeText(chance) {
    if (!this.rng.chance(chance || 0)) return null;
    const pool = this.customText.length ? this.customText : (this.params.textPool === 'quotes' ? QUOTES : CAPTIONS);
    return { str: this.rng.pick(pool), style: this.params.textStyle };
  }

  cue(clip, dur, opts = {}) {
    const speed = opts.speed ?? 1;
    let d = dur;
    const need = d * speed + 0.05;
    if (clip.duration < need) d = Math.max(0.12, (clip.duration - 0.05) / speed);
    const maxOffset = Math.max(0, clip.duration - d * speed - 0.05);
    const offset = opts.offset ?? this.rng.range(0, maxOffset);
    const fx = this.params.fx;
    return {
      kind: 'clip',
      clip,
      offset,
      dur: d,
      speed,
      zoom: opts.zoom || { from: 1.0, to: 1.0 },
      pan: opts.pan || { x: this.rng.range(-0.35, 0.35), y: this.rng.range(-0.25, 0.25) },
      fx: Object.assign({
        grain: this.rng.range(fx.grain[0], fx.grain[1]),
        vignette: 0.45,
        letterbox: null,
        flash: null,
        shake: 0,
        double: false,
        bw: this.rng.chance(fx.bw),
        hold: false,
      }, opts.fx || {}),
      text: opts.text || null,
      audio: Object.assign({ clip: 0, duck: 1 }, opts.audio || {}),
      snap: !!opts.snap,
      fadeIn: opts.fadeIn || 0,
    };
  }

  // --- phrases -------------------------------------------------------------------------------

  phrase_dwell(allowVoice = true) {
    const p = this.params.dwell;
    const v = this.params.voice;
    if (allowVoice && v && v.chance && (this.catalog.stats.with_audio || 0) > 2 && this.rng.chance(v.chance)) {
      return this.phrase_voice();
    }
    const n = this.rng.int(p.clips[0], p.clips[1]);
    const cues = [];
    const lb = this.letterbox();
    for (let i = 0; i < n; i++) {
      const clip = this.pickClip({ tags: this.themeTags(0), minDuration: 2.5 });
      if (!clip) break;
      const speed = this.rng.range(p.speed[0], p.speed[1]);
      const dur = this.rng.range(p.dur[0], p.dur[1]);
      const z = this.rng.range(p.zoom[0], p.zoom[1]);
      const zoomIn = this.rng.chance(0.75);
      cues.push(this.cue(clip, dur, {
        speed,
        zoom: zoomIn ? { from: 1.0, to: z } : { from: z, to: 1.0 },
        fx: { letterbox: lb, vignette: 0.5 },
        text: this.maybeText(p.text),
        fadeIn: p.fade || 0,
      }));
    }
    return cues;
  }

  // A clip that gets to speak: interview, news, voice-over. Music ducks under it.
  phrase_voice() {
    const v = this.params.voice;
    const clip = this.pickClip({ audio: true, tags: ['voice', 'interview', 'speech', 'news'], minDuration: 3 });
    if (!clip || !clip.has_audio) return this.phrase_dwell(false);
    const dur = Math.min(this.rng.range(v.dur[0], v.dur[1]), Math.max(0.5, clip.duration - 0.1));
    return [this.cue(clip, dur, {
      speed: 1,
      offset: 0,
      zoom: { from: 1.0, to: 1.06 },
      audio: { clip: 1, duck: v.duck },
      fx: { vignette: 0.5, letterbox: this.letterbox() },
      phrase: 'voice',
    })].map((c) => Object.assign(c, { phrase: 'voice' }));
  }

  // A / B / A / B: the collision that makes the point.
  phrase_juxtapose() {
    const p = this.params.juxtapose;
    if (!this.rng.chance(p.chance)) return [];
    const pairs = this.rng.int(p.pairs[0], p.pairs[1]);
    const dur = this.rng.range(p.dur[0], p.dur[1]);
    const cues = [];
    const lb = this.letterbox();
    for (let i = 0; i < pairs; i++) {
      for (const side of [0, 1]) {
        const clip = this.pickClip({
          tags: this.themeTags(side),
          prefer: this.theme ? {} : (side ? { brightness: 0.5 } : { brightness: -0.5 }),
        });
        if (!clip) continue;
        cues.push(this.cue(clip, this.rng.jitter(dur, 0.1), {
          speed: 1,
          zoom: { from: 1.0, to: 1.05 },
          fx: { letterbox: lb },
          snap: true,
        }));
      }
    }
    return cues;
  }

  // Accelerating cuts, zoom creeping in, flashes near the top.
  phrase_build() {
    const p = this.params.build;
    const n = this.rng.int(p.clips[0], p.clips[1]);
    const d0 = this.rng.range(p.durStart[0], p.durStart[1]);
    const d1 = this.rng.range(p.durEnd[0], p.durEnd[1]);
    const cues = [];
    const lb = this.letterbox();
    const motifAt = this.rng.chance(0.35) && this.motifs.length ? this.rng.int(1, Math.max(1, n - 1)) : -1;
    for (let i = 0; i < n; i++) {
      const t = i / Math.max(1, n - 1);
      const dur = d0 + (d1 - d0) * (t * t);
      const clip = i === motifAt ? this.motifs[0] : this.pickClip({ tags: this.rng.chance(0.6) ? this.themeTags(i % 2) : [] });
      if (!clip) continue;
      const z = 1.0 + 0.12 * t + this.rng.range(0, 0.06);
      const flash = i >= n - 2 && this.rng.chance(p.flash) ? { at: 'start', strength: 0.8 } : null;
      cues.push(this.cue(clip, dur, {
        speed: this.rng.range(p.speed[0], p.speed[1]),
        zoom: { from: 1.0, to: z },
        fx: { letterbox: lb, flash, grain: this.rng.range(0.08, 0.16) },
        snap: true,
      }));
    }
    return cues;
  }

  // The crescendo: blisteringly fast, anything goes, flash out.
  phrase_burst() {
    const p = this.params.burst;
    if (!this.rng.chance(p.chance)) return [];
    const n = this.rng.int(p.clips[0], p.clips[1]);
    const base = this.rng.range(p.dur[0], p.dur[1]);
    const cues = [];
    const lb = this.letterbox();
    for (let i = 0; i < n; i++) {
      const clip = this.motifs.length && this.rng.chance(0.12) ? this.rng.pick(this.motifs) : this.pickClip({});
      if (!clip) continue;
      const last = i === n - 1;
      cues.push(this.cue(clip, this.rng.jitter(base, 0.25), {
        speed: this.rng.range(p.speed[0], p.speed[1]),
        zoom: { from: this.rng.range(1.0, 1.15), to: this.rng.range(1.0, 1.2) },
        fx: {
          letterbox: lb,
          shake: this.rng.chance(p.shake) ? this.rng.range(2, 6) : 0,
          double: this.rng.chance(p.double),
          flash: last && this.rng.chance(p.flashEnd) ? { at: 'end', strength: 1 } : null,
          grain: this.rng.range(0.1, 0.2),
        },
        snap: true,
      }));
    }
    return cues;
  }

  // One image, held. Often the motif coming back. Sometimes frozen. Sometimes a line of text.
  phrase_climax() {
    const p = this.params.climax;
    const useMotif = this.motifs.length && this.rng.chance(p.motif);
    const clip = useMotif ? this.motifs[0]
      : this.pickClip({ tags: ['faces', ...this.themeTags(0)], prefer: { motion: -0.3 }, minDuration: 2 });
    if (!clip) return [];
    const dur = this.rng.range(p.dur[0], p.dur[1]);
    return [this.cue(clip, dur, {
      speed: this.rng.range(0.5, 0.8),
      zoom: { from: p.zoom[0], to: p.zoom[1] },
      fx: {
        vignette: 0.8,
        hold: this.rng.chance(p.hold),
        grain: this.rng.range(0.1, 0.18),
        flash: this.rng.chance(0.3) ? { at: 'start', strength: 1 } : null,
      },
      text: this.maybeText(p.text),
      audio: { clip: 0, duck: 1 },
    })];
  }

  phrase_black() {
    const p = this.params.black;
    if (!this.rng.chance(p.chance)) return [];
    return [{
      kind: 'black',
      dur: this.rng.range(p.dur[0], p.dur[1]),
      audio: { clip: 0, duck: this.rng.chance(p.silence) ? 0.0 : 1 },
      text: this.maybeText(p.text),
      fx: { grain: 0.03, vignette: 0 },
      snap: false,
      fadeIn: 0,
    }];
  }
}
