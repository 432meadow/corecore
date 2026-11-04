// The client-side clip pool: a sampled window onto the server's catalogue, with feature-aware picking.
export class Catalog {
  constructor({ seed = null } = {}) {
    this.seed = seed;
    this.pool = [];
    this.recent = [];
    this.bad = new Set();
    this.stats = { clips: 0, with_audio: 0, tags: {} };
    this.fetching = null;
    this.generation = 0;
  }

  get size() { return this.pool.length; }

  async refreshStats() {
    const r = await fetch('/api/stats');
    this.stats = await r.json();
    return this.stats;
  }

  // Refill from the server. Recently played clips are excluded first; if that leaves too little
  // (small pools), the exclusion shrinks until something comes back, so the stream never dries up.
  async fill(n = 150) {
    if (this.fetching) return this.fetching;
    this.lastFill = performance.now();
    this.fetching = (async () => {
      const total = this.stats.clips || 0;
      const cap = Math.max(8, Math.min(300, Math.floor(total * 0.5)));
      if (this.recent.length > cap) this.recent.splice(0, this.recent.length - cap);
      const want = Math.min(n, Math.max(4, Math.floor(total * 0.25)));
      for (const recent of [this.recent.slice(-cap), this.recent.slice(-Math.min(6, cap)), []]) {
        const before = this.pool.length;
        await this.fetchInto(n, [...recent, ...this.bad]);
        if (this.pool.length - before >= want) break;
      }
      return this.pool.length;
    })().finally(() => { this.fetching = null; });
    return this.fetching;
  }

  async fetchInto(n, exclude) {
    const params = new URLSearchParams({ n: String(n), exclude: exclude.join(',') });
    if (this.seed != null) params.set('seed', String((this.seed + this.generation++) >>> 0));
    const r = await fetch(`/api/clips/sample?${params}`);
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
    await fetch(`/api/clips/${id}/ban`, { method: 'POST' });
  }
}
