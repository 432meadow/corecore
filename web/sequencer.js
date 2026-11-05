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

// Lines for contemporary material: sincere, lowercase, no memes. The found titles do most of the talking.
export const CAPTIONS_NOW = [
  'someone filmed this', 'it was a tuesday', 'nothing happened today', 'we are all still here', 'this is the whole world',
  'look at them', 'they do not know', 'it is still going', 'this was yesterday', 'somewhere right now', 'no one is watching',
  'everyone is watching', 'i was there', 'you were there', 'it keeps going', 'this is real', 'all of this at once',
  'the same day everywhere', 'it does not stop', 'we kept filming',
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
  ['ads', 'faces'], ['consumerism', 'earth'], ['fear', 'home'], ['childhood', 'screens'],
  ['dashcam', 'vlog'], ['vlog', 'cctv'], ['asmr', 'traffic'], ['games', 'nature'], ['dashcam', 'home'], ['crowd', 'quiet'],
  ['vlog', 'traffic'], ['animals', 'traffic'], ['home', 'cctv'],
  ['beauty', 'traffic'], ['beauty', 'screens'], ['kind', 'cctv'], ['kind', 'traffic'], ['trailcam', 'city'], ['light', 'dark'],
  ['trailcam', 'screens'], ['beauty', 'consumerism'], ['kind', 'games'], ['nature', 'dashcam'],
  ['bright', 'dark'], ['still', 'motion'], ['vivid', 'muted'],
];

// Colour grades, one per cycle, so a stretch of clips reads as graded film rather than raw uploads.
export const GRADES = {
  neutral: { filter: '', tint: null, tintAlpha: 0, tintBlend: 'soft-light', lift: 0, bloom: 0, grain: 1.0 },
  cold: { filter: 'saturate(0.8) contrast(1.06)', tint: '#1b2a44', tintAlpha: 0.22, tintBlend: 'soft-light', lift: 10, bloom: 0.12, grain: 1.0 },
  warm: { filter: 'saturate(0.9) contrast(1.04) sepia(0.12)', tint: '#5a3a1a', tintAlpha: 0.18, tintBlend: 'soft-light', lift: 8, bloom: 0.1, grain: 0.9 },
  bleach: { filter: 'saturate(0.55) contrast(1.15) brightness(1.04)', tint: '#cfd6dd', tintAlpha: 0.08, tintBlend: 'overlay', lift: 16, bloom: 0.05, grain: 1.3 },
  night: { filter: 'saturate(0.7) contrast(1.12) brightness(0.92)', tint: '#0a1030', tintAlpha: 0.3, tintBlend: 'multiply', lift: 6, bloom: 0.22, grain: 1.2 },
  mono: { filter: 'grayscale(1) contrast(1.1)', tint: '#101418', tintAlpha: 0.1, tintBlend: 'soft-light', lift: 12, bloom: 0.1, grain: 1.4 },
};

// Parameters every mode gets unless it overrides them.
const DEFAULTS = {
  ramp: { dwell: 0.3, climax: 0.4, build: 0.3 },        // chance of a speed ramp per phrase
  stutter: 0.12,                                       // chance a burst cut is repeated 2-3 times
  texture: { pixelate: 0.03, aberration: 0.05 },       // low-res re-upload look, RGB split; rare by default
  grades: { cold: 2, neutral: 2, warm: 1, bleach: 1, mono: 1, night: 1 },
  jumpcut: { chance: 0.25, pieces: [3, 4], dur: [0.7, 1.5], audio: true },
  fitVertical: 'blur',                                 // phone footage: blurred frame instead of a 60% crop
  tail: [0.5, 1.2],                                    // seconds a voice's audio bleeds under the next shot
};

export const MODES = {
  corecore: {
    label: 'corecore',
    blurb: 'slow, sad, then too fast. hard cuts, grain, cut to black.',
    music: { style: 'wash', root: 57, mode: 'aeolian', scale: 'minor', chordSeconds: [20, 36], glide: [4, 8], brightness: 0.35, choir: 0.7, air: 0.6, shimmer: 0.6, pluck: 0.3, cutoff: 900 },
    cycle: ['dwell', 'jumpcut', 'juxtapose', 'build', 'burst', 'climax', 'black'],
    dwell: { clips: [1, 2], dur: [3, 6], speed: [0.6, 1.0], zoom: [1.03, 1.12], text: 0.06, fade: 0 },
    voice: { chance: 0.3, dur: [4, 8], duck: 0.3 },
    juxtapose: { chance: 0.7, pairs: [2, 4], dur: [0.7, 1.4] },
    build: { clips: [5, 9], durStart: [1.4, 2.0], durEnd: [0.4, 0.6], flash: 0.3, speed: [0.9, 1.3] },
    burst: { chance: 0.85, clips: [8, 18], dur: [0.16, 0.34], flashEnd: 0.5, shake: 0.5, speed: [1, 1.6], double: 0.1 },
    climax: { dur: [1.5, 3.0], hold: 0.4, zoom: [1.0, 1.25], text: 0.08, motif: 0.7 },
    black: { chance: 0.8, dur: [0.5, 1.8], silence: 0.3, text: 0.05 },
    fx: { grain: [0.07, 0.14], desat: 0.2, contrast: 1.08, letterbox: 0.15, bw: 0.04 },
    prefer: { brightness: -0.4 },
    textStyle: 'caption', textPool: 'captions', useTitles: true,
  },
  hopecore: {
    label: 'hopecore',
    blurb: 'same editing, warmer: light, quotes, no cut to black.',
    music: { style: 'wash', root: 60, mode: 'lydian', scale: 'major', chordSeconds: [14, 24], glide: [3, 6], brightness: 0.65, choir: 1, air: 0.5, shimmer: 1, pluck: 0.6, cutoff: 1800 },
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
    preferTags: ['beauty', 'kind', 'light', 'trailcam'],
    textStyle: 'quote', textPool: 'quotes', useTitles: false,
    texture: { pixelate: 0, aberration: 0 }, grades: { warm: 4, neutral: 2, bleach: 1 }, stutter: 0.05,
  },
  chaos: {
    label: 'chaos (nichetok)',
    blurb: 'the 2023 turn: nonsensical, layered, jarring speeds.',
    music: { style: 'wash', root: 58, mode: 'phrygian', scale: 'minor', chordSeconds: [6, 12], brightness: 0.5, motion: 0.9, dissonance: 0.35, choir: 0.6, air: 0.9, shimmer: 0.4, pluck: 0.8, cutoff: 2500 },
    cycle: ['burst', 'juxtapose', 'build', 'jumpcut', 'burst', 'climax', 'black'],
    stutter: 0.4, texture: { pixelate: 0.15, aberration: 0.2 }, grades: { cold: 2, night: 2, bleach: 2, mono: 1, neutral: 1 },
    dwell: { clips: [1, 1], dur: [1.5, 3], speed: [0.4, 2.0], zoom: [1.0, 1.2], text: 0.1, fade: 0 },
    voice: { chance: 0.35, dur: [1.5, 4], duck: 0.2 },
    juxtapose: { chance: 0.6, pairs: [2, 5], dur: [0.4, 0.9] },
    build: { clips: [4, 8], durStart: [1.0, 1.4], durEnd: [0.25, 0.4], flash: 0.4, speed: [0.5, 2.0] },
    burst: { chance: 1, clips: [6, 14], dur: [0.2, 0.7], flashEnd: 0.4, shake: 0.6, speed: [0.5, 2.5], double: 0.35 },
    climax: { dur: [0.8, 1.6], hold: 0.6, zoom: [1.0, 1.4], text: 0.15, motif: 0.5 },
    black: { chance: 0.5, dur: [0.2, 0.6], silence: 0.5, text: 0.1 },
    fx: { grain: [0.1, 0.22], desat: 0.1, contrast: 1.15, letterbox: 0.3, bw: 0.1 },
    prefer: {},
    textStyle: 'caption', textPool: 'captions', useTitles: true,
  },
  dwell: {
    label: 'dwell',
    blurb: 'long takes, slow push-ins, nothing happens.',
    music: { style: 'wash', root: 50, mode: 'aeolian', scale: 'minor', chordSeconds: [28, 48], glide: [6, 12], brightness: 0.22, sub: 1, choir: 0.5, air: 0.7, shimmer: 0.3, pluck: 0.12, cutoff: 600 },
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
    textStyle: 'caption', textPool: 'captions', useTitles: true,
    texture: { pixelate: 0, aberration: 0 }, stutter: 0, ramp: { dwell: 0.5, climax: 0.5, build: 0 },
    grades: { cold: 2, mono: 2, night: 2, neutral: 1 },
  },
  online: {
    label: 'online (now)',
    blurb: 'contemporary material, cinematic treatment: slow motion, jump cuts, sound bleeding across cuts.',
    music: { style: 'desk', root: 55, mode: 'dorian', scale: 'minor', chordSeconds: [16, 28], glide: [4, 8], brightness: 0.45, choir: 0.9, air: 0.8, shimmer: 0.8, pluck: 0.5, cutoff: 1200 },
    cycle: ['dwell', 'jumpcut', 'juxtapose', 'build', 'burst', 'climax', 'black'],
    dwell: { clips: [1, 2], dur: [3, 6], speed: [0.5, 1.0], zoom: [1.02, 1.1], text: 0.05, fade: 0 },
    voice: { chance: 0.4, dur: [3, 7], duck: 0.3 },
    jumpcut: { chance: 0.6, pieces: [3, 5], dur: [0.6, 1.6], audio: true },
    juxtapose: { chance: 0.6, pairs: [2, 4], dur: [0.6, 1.3] },
    build: { clips: [5, 9], durStart: [1.3, 1.8], durEnd: [0.35, 0.55], flash: 0.2, speed: [1.0, 1.4] },
    burst: { chance: 0.8, clips: [8, 16], dur: [0.18, 0.36], flashEnd: 0.35, shake: 0.3, speed: [1, 1.8], double: 0.08 },
    climax: { dur: [2, 3.5], hold: 0.3, zoom: [1.0, 1.2], text: 0.08, motif: 0.6 },
    black: { chance: 0.75, dur: [0.5, 1.6], silence: 0.35, text: 0.15 },
    fx: { grain: [0.05, 0.1], desat: 0.1, contrast: 1.05, letterbox: 0.1, bw: 0.03 },
    ramp: { dwell: 0.55, climax: 0.6, build: 0.4 }, stutter: 0.2, texture: { pixelate: 0.06, aberration: 0.1 },
    grades: { cold: 3, night: 3, bleach: 1, mono: 1, warm: 1, neutral: 1 },
    prefer: { brightness: -0.2 }, textStyle: 'caption', textPool: 'now', useTitles: true,
  },
};

// Found text: an archival title ("a date with your family", "design for dreaming") makes a better caption
// than anything we could write. Lowercased, de-bracketed, trimmed to a line.
export function cleanTitle(title) {
  if (!title) return '';
  let t = String(title).replace(/\[[^\]]*\]|\([^)]*\)/g, ' ').replace(/[_|]+/g, ' ')
    .replace(/\b(part|reel|pt\.?)\s*\d+\b/gi, ' ').replace(/\b(19|20)\d\d\b/g, ' ')
    .replace(/[\s.,:;-]+$/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
  if (t.length > 60) t = t.slice(0, 60).replace(/\s+\S*$/, '');
  if (t.length < 4 || /^[\d\s]+$/.test(t)) return '';
  return t;
}

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
    this.params = Object.assign({}, DEFAULTS, MODES[this.mode]);
    this.stepIndex = 0;
    this.nextTail = 0;
  }

  // Everything the next pick depends on goes back to its initial state, so two viewers that reseed to the
  // same value produce the same stream regardless of what they watched before.
  reseed(seed) {
    this.seed = seed;
    this.rng = makeRng(seed);
    this.stepIndex = 0;
    this.cycleCount = 0;
    this.motifs = [];
    this.theme = null;
    this.lastSource = null;
    this.nextTail = 0;
    this.grade = 'neutral';
    this.catalog.reset?.();
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
    const g = this.params.grades || DEFAULTS.grades;
    this.grade = this.rng.weighted(Object.keys(g), (k) => g[k]);
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
    if (this.params.preferTags && !(filter.tags && filter.tags.length)) f.tags = this.params.preferTags;
    f.sourceAvoid = this.lastSource;
    const c = this.catalog.take(f, this.rng);
    if (c) this.lastSource = c.source_id;
    return c;
  }

  letterbox() {
    const fx = this.params.fx;
    return this.rng.chance(fx.letterbox) ? this.rng.pick(['4:3', 'scope']) : null;
  }

  maybeText(chance, clip = null, style = null) {
    if (!this.rng.chance(chance || 0)) return null;
    const st = style || this.params.textStyle;
    const custom = this.customText.length ? this.customText : null;
    if (!custom && this.params.useTitles && clip && clip.source_title && this.rng.chance(0.5)) {
      const t = cleanTitle(clip.source_title);
      if (t) return { str: t, style: st };
    }
    const pools = { quotes: QUOTES, now: CAPTIONS_NOW, captions: CAPTIONS };
    const pool = custom || pools[this.params.textPool] || CAPTIONS;
    return { str: this.rng.pick(pool), style: st };
  }

  takeTail() {
    const t = this.nextTail || 0;
    this.nextTail = 0;
    return t;
  }

  // Speed ramps: cinema's slow motion, with the catch-up before the cut. Motion-heavy clips get the
  // slow-motion treatment; still ones get a gentle drift.
  maybeRamp(kind, clip) {
    const chance = (this.params.ramp || DEFAULTS.ramp)[kind] || 0;
    if (!this.rng.chance(chance)) return null;
    const moving = (clip.motion || 0) > 0.03;
    if (kind === 'climax') return this.rng.chance(0.6) ? { from: 0.8, to: 0.3 } : { from: 0.35, to: 1.0 };
    if (kind === 'build') return { from: 1.0, to: this.rng.range(1.5, 2.0) };
    return moving ? { from: this.rng.range(0.35, 0.5), to: this.rng.range(0.8, 1.0) } : { from: 1.0, to: this.rng.range(0.5, 0.7) };
  }

  cue(clip, dur, opts = {}) {
    const ramp = opts.ramp || null;
    const speed = ramp ? ramp.from : (opts.speed ?? 1);
    const rate = ramp ? (ramp.from + ramp.to) / 2 : speed;   // average source consumption
    let d = dur;
    const avail = (opts.offset != null ? clip.duration - opts.offset : clip.duration) - 0.05;
    if (avail < d * rate) d = Math.max(0.12, avail / rate);
    const maxOffset = Math.max(0, clip.duration - d * rate - 0.05);
    const offset = opts.offset ?? this.rng.range(0, maxOffset);
    const fx = this.params.fx;
    const tex = this.params.texture || DEFAULTS.texture;
    const tall = clip.width && clip.height && clip.height / clip.width > 1.2;
    return {
      kind: 'clip',
      clip,
      offset,
      dur: d,
      speed,
      ramp,
      grade: this.grade || 'neutral',
      fit: tall && (this.params.fitVertical || DEFAULTS.fitVertical) === 'blur' && this.rng.chance(0.85) ? 'blur' : 'cover',
      audioTail: opts.audioTail ?? this.takeTail(),
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
        pixelate: this.rng.chance(tex.pixelate) ? this.rng.int(3, 6) : 0,
        aberration: this.rng.chance(tex.aberration) ? this.rng.range(1.5, 4) : 0,
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
        ramp: this.maybeRamp('dwell', clip),
        zoom: zoomIn ? { from: 1.0, to: z } : { from: z, to: 1.0 },
        fx: { letterbox: lb, vignette: 0.5 },
        text: this.maybeText(p.text, clip),
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
    const tail = this.params.tail || DEFAULTS.tail;
    this.nextTail = this.rng.range(tail[0], tail[1]);
    return [this.cue(clip, dur, {
      speed: 1,
      offset: 0,
      zoom: { from: 1.0, to: 1.06 },
      audio: { clip: 1, duck: v.duck },
      audioTail: 0,
      fx: { vignette: 0.5, letterbox: this.letterbox() },
    })].map((c) => Object.assign(c, { phrase: 'voice' }));
  }

  // Vlog grammar used with intent: one clip, several pieces jumping forward through it, its own sound up.
  phrase_jumpcut() {
    const p = this.params.jumpcut || DEFAULTS.jumpcut;
    if (!this.rng.chance(p.chance)) return [];
    const clip = this.pickClip({ audio: !!p.audio, tags: ['vlog', 'voice', 'asmr', 'dashcam', 'faces'], minDuration: 5 });
    if (!clip || clip.duration < 4) return [];
    const n = this.rng.int(p.pieces[0], p.pieces[1]);
    const piece = this.rng.range(p.dur[0], p.dur[1]);
    const span = clip.duration - 0.1;
    const stride = Math.max(piece + 0.2, (span - piece) / n);
    let offset = this.rng.range(0, Math.max(0, span - n * stride));
    const withAudio = !!(p.audio && clip.has_audio);
    const lb = this.letterbox();
    const cues = [];
    for (let i = 0; i < n; i++) {
      if (offset + piece > clip.duration - 0.05) break;
      cues.push(this.cue(clip, this.rng.jitter(piece, 0.2), {
        speed: 1,
        offset,
        zoom: { from: 1 + 0.02 * i, to: 1 + 0.02 * i + 0.03 },
        fx: { letterbox: lb },
        audio: { clip: withAudio ? 1 : 0, duck: withAudio ? this.params.voice.duck : 1 },
        audioTail: 0,
      }));
      offset += stride;
    }
    if (withAudio && cues.length) {
      const tail = this.params.tail || DEFAULTS.tail;
      this.nextTail = this.rng.range(tail[0], tail[1]);
    }
    return cues;
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
        ramp: i >= n - 2 ? this.maybeRamp('build', clip) : null,
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
      const c = this.cue(clip, this.rng.jitter(base, 0.25), {
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
      });
      cues.push(c);
      // the stutter: the same instant two or three times, a device the feed borrowed from music video
      if (!last && this.rng.chance(this.params.stutter ?? DEFAULTS.stutter)) {
        const times = this.rng.int(1, 2);
        for (let r = 0; r < times; r++) cues.push(Object.assign({}, c, { fx: Object.assign({}, c.fx, { flash: null }), audioTail: 0, snap: false }));
      }
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
      ramp: this.maybeRamp('climax', clip),
      zoom: { from: p.zoom[0], to: p.zoom[1] },
      fx: {
        vignette: 0.8,
        hold: this.rng.chance(p.hold),
        grain: this.rng.range(0.1, 0.18),
        flash: this.rng.chance(0.3) ? { at: 'start', strength: 1 } : null,
      },
      text: this.maybeText(p.text, clip),
      audio: { clip: 0, duck: 1 },
    })];
  }

  phrase_black() {
    const p = this.params.black;
    if (!this.rng.chance(p.chance)) return [];
    const text = this.maybeText(p.text, this.motifs[0] || null, 'title');
    return [{
      kind: 'black',
      dur: this.rng.range(p.dur[0], p.dur[1]) + (text ? 1.0 : 0),
      audio: { clip: 0, duck: this.rng.chance(p.silence) ? 0.0 : 1 },
      text,
      grade: this.grade || 'neutral',
      fx: { grain: 0.03, vignette: 0 },
      snap: false,
      fadeIn: 0,
    }];
  }
}
