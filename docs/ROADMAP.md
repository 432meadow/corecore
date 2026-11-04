# Roadmap

Rough order of usefulness. Nothing here is started.

## Material
- **Automatic tagging with CLIP** (or any image-text embedding): tag each clip with a small vocabulary
  (face, crowd, screen, nature, city, text, animal, child, war, product...) from its thumbnail so the
  contrast pairs work on any pool without hand tags. Store the embedding so the sequencer can also pick
  "visually similar" or "maximally different" follow-ups.
- **Speech detection** (a VAD such as Silero, or whisper-tiny) so `voice` phrases find real talking heads,
  and so captions can quote what is being said, which is a strong corecore device. (Face tagging with a
  Haar cascade is in; a modern detector would cut the false positives on grainy film.)
- **More providers**: Reddit video via OAuth app credentials (r/dashcam, r/oddlyterrifying, r/liminalspace
  are the genre's natural habitat; unauthenticated listings are blocked from datacenters), Wikimedia Commons
  with a registered user agent, Pexels / Pixabay / Coverr APIs (free stock, API key), Vimeo CC search,
  Twitch clips via the Helix API, public DOT traffic-camera HLS streams recorded with ffmpeg.
- **Visual relevance search**: with CLIP embeddings in place, "more like this" across the pool, and
  automatic pairing of a found clip with its most opposite neighbour.
- **Shot quality filter**: drop near-black, near-static or slate/title-card shots; dedupe near-identical
  shots across sources with a perceptual hash of the thumbnail.
- **Curation grid**: a page of thumbnails with tag editing, ban/unban, "more like this".

## Editing
- **Real beat tracking** for uploaded tracks (tempo + downbeat estimate from the onset stream) so builds
  and bursts land on the grid, not just on the next loud transient.
- **Caption sources**: pull captions from the clip's own transcript, the source title, or an LLM given
  the current contrast pair.
- **More treatments**: chromatic aberration, VHS tracking, datamosh-style frame holds, interlacing,
  timestamp overlays for CCTV material, TikTok-style caption boxes. Most want WebGL rather than canvas 2D.
- **Hand-authored cycles**: let a user write a phrase list in JSON and share it with the seed.
- **Audio-reactive zoom** (push in on the music's energy envelope) and sidechain-style ducking on cuts.

## Output
- **Server-side render**: the client already produces a deterministic edit decision list per seed. Post it
  to an endpoint that renders the same list with ffmpeg (concat + zoompan + noise + vignette) to an mp4,
  for sharing without screen recording. WebM from the in-browser recorder is the stopgap.
- **HLS / WebRTC "channel"**: the static live channel syncs viewers by clock and deterministic sequencing;
  a server-rendered stream would make the sync exact and allow music with real transients.
- **Vertical export presets** (TikTok, Reels, Shorts safe areas).

## Operations
- Dockerfile with ffmpeg; docker-compose for app + worker; media on a volume.
- A real queue (Redis/RQ) if more than one worker is ever needed.
- Auth before putting the ingest form on the public internet.
