// The client-side clip pool: a sampled window onto the server's catalogue, with feature-aware picking.
// StaticCatalog (below) is the same thing fed by an exported manifest.json, for static hosting.
import { makeRng } from './prng.js';

// The footage the stream draws on: 'all', the main mix, or 'sunset', the clips scraped for the sunset
// variation (tagged sunset, published within a budget of their own). The main mix leaves them out.
export const SUNSET = 'sunset';
export const FOOTAGE = ['all', SUNSET];

export class Catalog {
  constructor({ seed = null, tags = [], footage = 'all' } = {}) {
    this.seed = seed;
    this.tags = tags;          // when set, only clips carrying one of these tags are played
    this.footage = footage;
    this.sunsets = null;       // how many sunset clips the pool holds, once known
    this.pool = [];
    this.recent = [];
    this.bad = new Set();
    this.stats = { clips: 0, with_audio: 0, tags: {} };
    this.fetching = null;
    this.generation = 0;
  }

  get size() { return this.pool.length; }

  // sunsets asked for and none in the pool: the main mix plays meanwhile
  get footageEmpty() { return this.footage === SUNSET && this.sunsets === 0; }

  async refreshStats() {
    const r = await fetch('api/stats');
    this.stats = await r.json();
    this.sunsets = this.stats.tags?.[SUNSET] || 0;
    if (this.tags.length || this.sunsets) {   // restrict the sequencer's view of the pool to what plays
      const r2 = await fetch(`api/clips/sample?${this.filterParams(new URLSearchParams({ n: '500' }))}`);
      const j = await r2.json();
      this.stats = Object.assign({}, this.stats, computeStats(j.clips || []));
    }
    return this.stats;
  }

  // the chosen tags (any of them) and the footage (the sunsets alone, or the main mix without them)
  filterParams(params) {
    if (this.tags.length) params.set('tags', this.tags.join(','));
    if (this.footage === SUNSET && !this.footageEmpty) params.set('only', SUNSET);
    else params.set('without', SUNSET);
    return params;
  }

  setTags(tags) {
    this.tags = tags;
    this.pool = [];
    this.recent = [];
    this.generation = 0;
  }

  setFootage(footage) {
    this.footage = FOOTAGE.includes(footage) ? footage : 'all';
    this.setTags(this.tags);
  }

  // Refill from the server. Recently played clips are excluded first; if that leaves too little
  // (small pools), the exclusion shrinks until something comes back, so the stream never dries up.
  async fill(n = 150) {
    if (this.fetching) return this.fetching;
    if (this.backoffUntil && performance.now() < this.backoffUntil) return this.pool.length;
    this.lastFill = performance.now();
    this.fetching = (async () => {
      const total = this.stats.clips || 0;
      const cap = Math.max(8, Math.min(300, Math.floor(total * 0.5)));
      if (this.recent.length > cap) this.recent.splice(0, this.recent.length - cap);
      const want = Math.min(n, Math.max(4, Math.floor(total * 0.25)));
      const start = this.pool.length;
      for (const recent of [this.recent.slice(-cap), this.recent.slice(-Math.min(6, cap)), []]) {
        const before = this.pool.length;
        await this.fetchInto(n, [...recent, ...this.bad]);
        if (this.pool.length - before >= want) break;
      }
      this.backoffUntil = this.pool.length === start ? performance.now() + 3000 : 0;
      return this.pool.length;
    })().catch((err) => { this.backoffUntil = performance.now() + 3000; throw err; })
      .finally(() => { this.fetching = null; });
    return this.fetching;
  }

  // Forget play history so a reseed replays the same decisions (the live channel depends on it).
  reset() {
    this.recent = [];
    this.generation = 0;
    this.backoffUntil = 0;
  }

  async fetchInto(n, exclude) {
    const params = new URLSearchParams({ n: String(n), exclude: exclude.join(',') });
    if (this.seed != null) params.set('seed', String((this.seed + this.generation++) >>> 0));
    this.filterParams(params);
    const r = await fetch(`api/clips/sample?${params}`);
    if (!r.ok) throw new Error(`sample failed: ${r.status}`);
    const j = await r.json();
    const have = new Set(this.pool.map((c) => c.id));
    for (const c of j.clips || []) {
      if (!have.has(c.id) && !this.bad.has(c.id)) this.pool.push(c);
    }
  }

  async ensure(min = 40) {
    if (this.pool.length < min) await this.fill();
  }

  hasTag(tag, min = 1) {
    return (this.stats.tags?.[tag] || 0) >= min;
  }

  // Score a clip against a filter. Multiplicative weights, never hard exclusions, so the
  // sequencer always gets *something* and the stream never stalls on a sparse pool.
  score(c, f) {
    let s = 1;
    if (f.tags && f.tags.length) {
      const hit = f.tags.some((t) => c.tags.includes(t));
      s *= hit ? 5 : 1;
    }
    if (f.not && f.not.length && f.not.some((t) => c.tags.includes(t))) s *= 0.15;
    if (f.audio) s *= c.has_audio ? 6 : 0.05;
    if (f.prefer) {
      for (const [k, dir] of Object.entries(f.prefer)) {
        const v = c[k];
        if (typeof v === 'number' && dir) s *= Math.exp(dir * (v - 0.4) * 3);
      }
    }
    if (f.minDuration && c.duration < f.minDuration) s *= 0.25;
    if (f.sourceAvoid != null && c.source_id === f.sourceAvoid) s *= 0.2;
    return s;
  }

  take(filter = {}, rng) {
    if (!this.pool.length) {
      this.fill().catch(() => {});
      return null;
    }
    const pick = rng ? rng.weighted(this.pool, (c) => this.score(c, filter))
      : this.pool[Math.floor(Math.random() * this.pool.length)];
    this.pool.splice(this.pool.indexOf(pick), 1);
    this.recent.push(pick.id);
    if (this.recent.length > 300) this.recent.splice(0, this.recent.length - 300);
    const stale = !this.lastFill || performance.now() - this.lastFill > 1500;
    if (this.pool.length === 0 || (this.pool.length < 40 && stale)) this.fill().catch(() => {});
    return pick;
  }

  markBad(id) {
    this.bad.add(id);
    this.pool = this.pool.filter((c) => c.id !== id);
  }

  async ban(id) {
    this.markBad(id);
    await fetch(`api/clips/${id}/ban`, { method: 'POST' });
  }

  banLines() { return null; }   // here a ban goes straight into the pool: nothing to copy
}

export function computeStats(clips) {
  const tags = {};
  const sources = new Set();
  let withAudio = 0;
  let seconds = 0;
  for (const c of clips) {
    sources.add(c.source_id);
    if (c.has_audio) withAudio++;
    seconds += c.duration || 0;
    for (const t of c.tags || []) tags[t] = (tags[t] || 0) + 1;
  }
  const sorted = Object.fromEntries(Object.entries(tags).sort((a, b) => b[1] - a[1]));
  return { clips: clips.length, banned: 0, sources: sources.size, seconds: Math.round(seconds * 10) / 10, with_audio: withAudio, tags: sorted };
}

// Static edition: the whole pool is in memory, picks are deterministic for a given seed and sequence of
// calls (no timing-dependent refills), which is what makes the synchronized live channel possible.
export class StaticCatalog extends Catalog {
  constructor({ seed = null, manifestUrl = 'manifest.json', tags = [], footage = 'all' } = {}) {
    super({ seed, tags, footage });
    this.manifestUrl = manifestUrl;
    this.all = null;
    this.everything = null;
    this.manifest = null;
    this.banned = new Set();   // the bans made in this browser (this.bad also holds clips that failed to load)
  }

  setTags(tags) {
    this.tags = tags;
    this.recent = [];
    if (this.everything) { this.all = this.filtered(); this.recomputeStats(); }
  }

  // The footage first: the sunsets alone, or the main mix without them (until sunsets are published, the
  // main mix, and footageEmpty says so). Then the chosen tags within it, if any clip there carries one.
  filtered() {
    const sun = this.everything.filter((c) => c.tags.includes(SUNSET));
    const main = this.everything.filter((c) => !c.tags.includes(SUNSET));
    this.sunsets = sun.length;
    const base = this.footage === SUNSET && sun.length ? sun : (main.length ? main : this.everything);
    if (!this.tags.length) return base;
    const want = new Set(this.tags);
    const subset = base.filter((c) => c.tags.some((t) => want.has(t)));
    return subset.length ? subset : base;
  }

  get size() { return this.all ? this.all.reduce((n, c) => n + (this.bad.has(c.id) ? 0 : 1), 0) : 0; }

  async load() {
    if (this.all) return this.all;
    const r = await fetch(this.manifestUrl, { cache: 'no-cache' });
    if (!r.ok) throw new Error(`manifest ${r.status}`);
    const m = await r.json();
    const base = this.manifestUrl.replace(/[^/]*$/, '');
    const sources = new Map((m.sources || []).map((s) => [s.id, s]));
    this.all = (m.clips || []).map((c) => {
      const s = sources.get(c.source_id) || {};
      return {
        ...c,
        tags: c.tags || [],
        url: base + c.file,
        thumb_url: c.thumb ? base + c.thumb : null,
        source_title: s.title || '',
        source_uploader: s.uploader || '',
        source_url: s.url || '',
        source_key: s.key || '',
        provider: s.provider || '',
        license: s.license || '',
      };
    });
    this.manifest = m;
    this.everything = this.all;
    this.all = this.filtered();
    try {
      for (const id of JSON.parse(localStorage.getItem('corecore.banned') || '[]')) { this.bad.add(id); this.banned.add(id); }
    } catch (e) { /* no storage */ }
    this.recomputeStats();
    return this.all;
  }

  recomputeStats() {
    this.stats = computeStats(this.all.filter((c) => !this.bad.has(c.id)));
  }

  async refreshStats() { await this.load(); return this.stats; }
  async ensure() { await this.load(); }
  async fill() { await this.load(); return this.size; }

  recentCap() {
    const total = this.stats.clips || 0;
    return Math.max(8, Math.min(300, Math.floor(total * 0.5)));
  }

  take(filter = {}, rng) {
    if (!this.all) return null;
    const recent = new Set(this.recent.slice(-this.recentCap()));
    let cands = this.all.filter((c) => !this.bad.has(c.id) && !recent.has(c.id));
    if (!cands.length) cands = this.all.filter((c) => !this.bad.has(c.id));
    if (!cands.length) return null;
    const pick = rng ? rng.weighted(cands, (c) => this.score(c, filter)) : cands[0];
    this.recent.push(pick.id);
    if (this.recent.length > 600) this.recent.splice(0, 300);
    return pick;
  }

  async ban(id) {
    this.markBad(id);
    this.banned.add(id);
    if (this.all) this.recomputeStats();
    try { localStorage.setItem('corecore.banned', JSON.stringify([...this.banned])); } catch (e) { /* no storage */ }
  }

  // This browser's bans as lines for bans.txt in the repository: pasted there, the next build leaves those
  // clips out for everyone. A clip is named by its source and where it starts in it, which outlives the pool.
  banLines() {
    const byId = new Map((this.everything || []).map((c) => [c.id, c]));
    return [...this.banned].map((id) => byId.get(id)).filter((c) => c && c.source_key && c.start != null)
      .map((c) => `${c.source_key}@${c.start}   # ${(c.source_title || '').replace(/\s+/g, ' ').slice(0, 90)}`);
  }
}
