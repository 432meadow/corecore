# corecore: what the generator is imitating

Research notes behind `web/sequencer.js`. Direct page fetches were blocked from the build environment, so
the Wikipedia article and the press coverage were read through web-search summaries; quoted phrases below
are as reported by those summaries. Treat the "rules" section as an interpretation to tune by eye, not as
settled fact.

## 1. What corecore is

- An internet aesthetic and "art movement" that grew on TikTok as a way of reflecting on digital culture
  after 2020, mostly associated with Gen Z (Wikipedia).
- The name is a sarcastic jab at the proliferation of `-core` labels (cottagecore, goblincore, ...):
  a "core" made of "the collective consciousness of all cores" (Know Your Meme).
- Timeline (sources disagree on details): `#corecore` seen on Tumblr in 2020; early TikTok examples around
  1 January 2021 (a montage of melting ice caps, floods and deforestation over sad violin music by
  @masonoelle); creator John Rising (@HighEnquiries) often credited as a father of the style, from May 2021;
  the hashtag used explicitly on TikTok from July 2022; mainstream coverage in early 2023; 2.1 billion
  hashtag views by March 2023 (Wikipedia, Vice, NBC, Time).
- Early videos were called **nichetok**, treated by writers as a sister trend; **hopecore** began as a
  positive offshoot (Wikipedia).
- Critics compare it to Dada and to found-footage/appropriation film (Mark Leckey, Arthur Jafa), and to the
  Soviet-montage idea that meaning is produced by the collision of shots (Nassau Weekly, Hyperallergic,
  Domus).

## 2. Characteristics, as described by the sources

**Material.** Clips spliced from "news, social media, films, livestreams, and memes" (Wikipedia);
"memes, news segments, celebrity interviews, film scenes" (Vice); "memes, headlines, movie and television
clips" (NBC). Signifiers a critic lists: British football clips, *Family Guy*, *Blade Runner 2049*, "any
clip of Jake Gyllenhaal screaming", melancholic music (Wikipedia); also *American Psycho* and Mark
Zuckerberg interview footage. Famous juxtapositions: TikToks of women describing their flaws cut against
Margot Robbie crying in *I, Tonya*; a Matthew Perry interview about lost love cut against Billie Eilish.

**Editing.** "Seemingly random clips edited together at various speeds as somber music plays in the
background" (Time). "Crammed into a surreal 15-seconds" (Vice). No complicated transitions or filler;
hard cuts. An "amateurish, unpolished aesthetic, with blisteringly fast cuts"; clips "often layered on top
of each other, edited at jarring speeds, and designed to evoke a feeling rather than communicate a specific
message". Going into 2023 the videos "became more nonsensical" and "increasingly chaotic" (Know Your Meme).

**Audio.** "Somber, ambient, or emotional music" (Wikipedia); "emotionally-rousing lo-fi" (Vice);
"sad slideshow audios", with sped-up remixes and nightcore for the chaotic variants (Know Your Meme).
Aphex Twin's "Avril 14th", "aisatsana [102]" and "#3" are repeatedly named as corecore soundtracks
(Guardian, i-D). The adjacent slowed + reverb trend runs tracks at roughly 0.78 to 0.85x with heavy echo.
Speech from interviews is part of the material, so the clip's own audio sometimes surfaces.

**Text.** None of the sources describe on-screen captions as a defining feature; the message, if any, is
in the edit (and in the TikTok caption below it). Hopecore leans on quotes and affirmations.

**Themes and tone.** Information overload, "online chaos", capitalism, depression, alienation, loneliness,
feeling unattractive, environmental dread; early videos "often carried an anti-capitalist or environmentalist
message" (Wikipedia). "A sheen of smoothness and detachment, but it's like people are screaming underneath"
(researcher quoted by Vice). "An essay with no thesis." Hopecore keeps the editing and flips the affect:
"the same essence as corecore, only happier", often soundtracked by Sinatra's "My Way" or Bob Marley.

## 3. Rules the generator follows

The sources describe material, tone, pacing variety and length but not a shot-by-shot structure. The arc
below (dwell, juxtapose, build, burst, climax, black) is this project's reading of the canonical
~15-second edit, stretched into a cycle that can repeat forever. Every number is a parameter in
`MODES` in `web/sequencer.js`.

| Device | Source basis | Implementation |
| --- | --- | --- |
| Disparate found footage | all sources | clips pooled from Internet Archive, yt-dlp, local files; shot detection chops them into 1.2-8 s pieces |
| Meaning by juxtaposition | montage reading (Nassau Weekly), the I, Tonya / Perry examples | each cycle picks a contrast pair of tags (nature/city, archive/modern, ads/war, bright/dark ...); `juxtapose` alternates A/B/A/B |
| Varying, jarring speeds | Time, Wikipedia | per-cue `playbackRate` 0.4-2.5x depending on phrase and mode |
| Slow sad set-up, then too fast | "somber music", "blisteringly fast cuts" | `dwell` 3-6 s shots -> `build` accelerating 1.8 s -> 0.4 s -> `burst` 8-18 cuts of 0.16-0.34 s |
| Hard cuts, no transitions | Vice, explainer coverage | cuts are instantaneous; crossfades only exist in hopecore/dwell modes |
| Layering | "layered on top of each other" | `double` exposure in bursts (chaos mode most of all) |
| Held image, abrupt end | the ~15 s form, sad slideshow lineage | `climax` holds one shot (optionally frozen), then `black` with the music continuing or briefly silenced |
| Recurring shot | motif editing in the genre | 1-2 motif clips per cycle, revisited in build/burst/climax |
| Degradation / amateurishness | "amateurish, unpolished" | grain, vignette, slight desaturation and contrast crush, occasional 4:3 pillarbox or scope bars, b/w, shake, flashes |
| Music-led cutting | music is the spine | spectral-flux onset detector (uploaded tracks) and scheduled onsets (generated bed) can pull a cut forward once 60% of a shot has played |
| Interview audio surfacing | celebrity interviews, news segments | `voice` phrase: a clip tagged voice/news/interview plays its own audio while the music ducks |
| Slowed + reverb | adjacent audio trend | 0.8x with pitch following plus a synthetic 3 s reverb tail, for your own tracks |
| Captions | not core to corecore; central to hopecore | rare lowercase captions in corecore (6%), italic serif quotes in hopecore (30-50%) |
| 2023 nonsense turn | Know Your Meme | `chaos` mode: bursts first, random speeds, 35% layering, more letterboxing and flashes |
| Vertical format | TikTok | 9:16 frame option; clips are cover-fitted and panned |

## 4. Sources consulted (via search summaries)

- Wikipedia, "Corecore": https://en.wikipedia.org/wiki/Corecore
- Wikipedia, "-core": https://en.wikipedia.org/wiki/-core
- Wikipedia, "Internet aesthetic": https://en.wikipedia.org/wiki/Internet_aesthetic
- Know Your Meme, "Corecore": https://knowyourmeme.com/memes/cultures/corecore
- Know Your Meme guide: https://knowyourmeme.com/editorials/guides/what-does-corecore-mean-on-tiktok-the-video-aesthetic-explained
- Time, "What to Know About the Corecore Aesthetic Taking Over TikTok": https://time.com/6248637/corecore-tiktok-aesthetic/
- Vice, "Corecore is the Screaming-Into-Void TikTok Trend We Deserve": https://www.vice.com/en/article/corecore-tiktok-trend-explained/
- NBC News, "#CoreCore videos are becoming more popular on TikTok": https://www.nbcnews.com/pop-culture/pop-culture-news/corecore-videos-tiktok-trend-rcna65515
- The Guardian, on Aphex Twin as Gen Z soundtrack (corecore and "Avril 14th"): https://www.theguardian.com/music/2026/jan/27/aphex-twin-taylor-swift-soundtrack-to-gen-z-life-online-tiktok
- i-D, "How Aphex Twin built a cult Gen Z following": https://i-d.co/article/aphex-twin-gen-z-following-tiktok/
- Nassau Weekly, "Corecore and the Logic of Montage": https://nassauweekly.com/corecore-and-the-logic-of-montage/
- Hyperallergic, "What Does TikTok's Corecore Have to Do With Dada?": https://hyperallergic.com/what-does-tiktoks-corecore-have-to-do-with-dada/
- Domus, "What is corecore, TikTok's latest aesthetic obsession?": https://www.domusweb.it/en/news/2023/02/22/what-is-corecore-tiktoks-latest-aesthetic-obsession.html
- F Newsmagazine, "The Jarring World of Corecore": https://fnewsmagazine.com/2023/02/the-jarring-world-of-corecore/
- Michigan Daily, "Nichetok/Corecore: TikTok's trendy nihilistic echo chamber": https://www.michigandaily.com/arts/digital-culture/nichetok-corecore-tiktoks-trendy-nihilistic-echo-chamber/
- Her Campus and Daily Dot on hopecore (Sinatra, Bob Marley, `#nichetok` tagging)
- GNET, "Corecore: a TikTok Trend as Initiation to Incel Ideology" (on how the format carries narratives without argument): https://gnet-research.org/2024/08/05/corecore-a-tiktok-trend-as-initiation-to-incel-ideology/
