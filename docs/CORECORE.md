# corecore: what the generator is imitating

Research notes behind `web/sequencer.js`. The Wikipedia article was read in full (revision current on
2026-11-04); the press pieces it cites were read through search summaries. Quotes are from the article
unless another source is named. Section 3 is this project's reading of the material as rules a program can
follow; every number there is a parameter in `MODES`.

## 1. What corecore is

- "An Internet aesthetic and artistic movement that developed on social media platforms, particularly
  TikTok, as a way of reflecting on digital culture and post-2020 sensibilities. It typically brings
  together different video clips to highlight the repetitive and overwhelming nature of online content",
  capturing "a sense of information overload and the chaotic environment of contemporary internet
  culture", and "largely associated with Generation Z".
- The name: `#corecore` appeared on Tumblr and Twitter as early as 2020 "solely as a pun on the literal
  definition of core, created out of users' frustrations of the over-saturation with the concept of
  '-cores'" (Chance Townsend, Mashable), such as goblincore or cottagecore.
- Lineage. Predecessor: weirdcore (Rhea Nayyar, Hyperallergic). Sister trend: nichetok, "made up mostly
  of shitposts that reference multiple fandoms, subcultures, and genres". Related terms: chaos edit,
  21st century humor, #pinkcore ("clips of cats and Fortnite mashed together"). Positive offshoot:
  hopecore. John Rising, called the "father" of the genre, credits Nam June Paik's video art as the
  origin of the form. A 2024 "Internet cinema" scene (Dana Dawud, Peter Vack, Angelicism01) is
  described as post-corecore.
- Timeline. 1 January 2021: Mason Noel posts one of the earliest videos, 20 seconds "of melting sea ice,
  Charli D'Amelio, a Black Friday sale, and Patrick Bateman of American Psycho", with critiques of the US
  military, "soundtracked by a somber violin piece", tagged #capitalism and #decay. May 2021: Rising
  starts experimenting with the style. July 2022: first use of the hashtag on TikTok (@heksensabbat).
  November 2022: Kieran Press-Reynolds blogs about it; February 2023: 664 million hashtag views; March
  2023: 2.1 billion. Pioneers named by media: Dylan Cherry, Eddie Hewer, Mason Noel, John Rising.
- Noel on the intent: "the whole point of [corecore] is to create something that can't be categorized,
  commodified, made into clickbait, or moderated".

## 2. Characteristics, as described by the sources

**Material.** "Seemingly unrelated clips" culled from "news footage, social media, films, livestreams,
and memes". Common signifiers: "British football clips, Family Guy, Blade Runner 2049, any clip of Jake
Gyllenhaal screaming" (Townsend); American Psycho (Moises Mendez II, Time); "Joe Rogan, Jordan Peterson,
and Theo Von make frequent appearances", and "lonely, angry, and sometimes violent male protagonists from
blockbusters like American Psycho, Blade Runner 2049, Fight Club, and Joker ... Once in a while, you'll see
a shot from the perspective of a man climbing up a cliff and stepping off" (Isabella Segalovich,
Hyperallergic). Early "real" corecore, per its defenders, was "fiercely environmentalist,
anti-consumerist, and anti-capitalist".

**Editing.** "The clips are edited at various speeds." "Full of intentionally jarring juxtapositions"
(Mendez II). "Crudely edited" (Hannah Ewens, The Guardian). The early popular form was "rapid-fire
15-second montages of surreal memes ... with intense music" that "didn't have much of a discernible
meaning beyond the pleasurable rush of recognizable audiovisual material" (Press-Reynolds). Reads "as an
art school freshman's first found-footage project in Adobe Premiere Pro" (Nayyar). It "mimics the way
using [TikTok] is an overstimulating act of binge-watching a stream of short videos and voices" (Ewens).
Secondary coverage adds hard cuts without transitions, clips "layered on top of each other", and the 2023
drift toward the "nonsensical" (Know Your Meme).

**Audio.** "Usually emotionally rousing, somber, or ambient music"; "a kind of pensive sonic wall"
(Mendez II); "usually a soft piano score or Aphex Twin" (Townsend), whose "QKThr" is singled out as the
repurposed track; "Avril 14th", "aisatsana" and "#3" are named elsewhere (Guardian, i-D). Rap accompanies
some videos; the frenetic early form used "Drain Gang and other internet rap". Noel's first video used a
somber violin piece. Voices are part of the stream: podcast hosts, monologues, interviews.

**Text.** Not described as a defining feature anywhere; the argument is carried by the cut. Hopecore
leans on quotes.

**Themes and tone.** "Capitalism, greed, depression, social status, fear of climate change and
relationships"; "the experience of being a woman in a sexist world"; "the overwhelming, disconnected,
random, oversaturated nature of being a human in the world today" (Mendez II). "Depressing, full of
existential dread and usually on the theme of disconnection and alienation" (Ewens). "Techno-futurism-doom
vibes ... a concern that life has no meaning and technology is alienating us from one another" (Amanda
Silberling, TechCrunch). "A program of yearning and melancholy; of cancelled futures" (Y7, Flash Art).
The characteristic audience response is the comment "real". Many writers compare it to Dada.

**Criticism.** Segalovich argues the coverage overlooked "the terrifying rates of loneliness among young
men and boys" the videos channel, and that corecore "might only make it worse"; "declarations of
meaninglessness and hopelessness often lead to authoritarianism". Others ask whether it is "merely
content or, worse still, content about content" (Ewens). This generator stays on the environmentalist /
anti-consumerist / found-footage side of the genre: public-domain material, no incel iconography.

## 3. Rules the generator follows

The sources describe material, tone, variety of speeds and the ~15-20 second length, not a shot-by-shot
structure. Noel's first video is the closest thing to a template: a slow natural image of decay, an
influencer, a sale, a movie psychopath, violin. The arc below (dwell, juxtapose, build, burst, climax,
black) is this project's reading of that, stretched into a cycle that repeats forever.

| Device | Source basis | Implementation |
| --- | --- | --- |
| Disparate found footage | "seemingly unrelated clips" from news, social media, films, livestreams, memes | clips pooled from Internet Archive, yt-dlp, local files; shot detection chops them into 1.2-8 s pieces |
| Meaning by juxtaposition | "intentionally jarring juxtapositions"; ice / D'Amelio / Black Friday / Bateman | each cycle picks a contrast pair of tags (nature/city, archive/modern, ads/war, consumerism/nature ...); `juxtapose` alternates A/B/A/B |
| Varying, jarring speeds | "edited at various speeds" | per-cue `playbackRate` 0.4-2.5x depending on phrase and mode |
| Slow set-up, then rapid fire | "somber" music against "rapid-fire 15-second montages" | `dwell` 3-6 s shots -> `build` accelerating 1.8 s -> 0.4 s -> `burst` 8-18 cuts of 0.16-0.34 s |
| Crude, hard cuts | "crudely edited", "art school freshman's first found-footage project" | cuts are instantaneous; crossfades only in hopecore/dwell modes |
| Layering | clips "layered on top of each other" (Know Your Meme) | `double` exposure in bursts (chaos mode most of all) |
| Held image, abrupt end | the 15-20 s form | `climax` holds one shot (optionally frozen), then `black` with the music continuing or briefly silenced |
| Faces | Gyllenhaal screaming, Bateman, Rogan, Peterson: the genre cuts to faces | Haar-cascade face tagging; motifs and climaxes prefer `faces` |
| Recurring shot | motif editing in the genre | 1-2 motif clips per cycle, revisited in build/burst/climax |
| Degradation | "crudely edited"; archival material | grain, vignette, slight desaturation and contrast crush, occasional 4:3 pillarbox or scope bars, b/w, shake, flashes |
| Pensive sonic wall | "emotionally rousing, somber, or ambient music", "soft piano score or Aphex Twin" | built-in generative bed: slow minor-key pads, detuned, low-passed, with sparse piano-like plucks; or your own tracks |
| Music-led cutting | music is the spine | spectral-flux onset detector (uploaded tracks) and scheduled onsets (generated bed) can pull a cut forward once 60% of a shot has played |
| A stream of voices | "a stream of short videos and voices"; podcast and interview clips | `voice` phrase: a clip tagged voice/news/interview plays its own audio while the music ducks |
| Slowed + reverb | adjacent sad-edit audio trend | 0.8x with pitch following plus a synthetic 3 s reverb tail, for your own tracks |
| Captions | not core to corecore; central to hopecore | rare lowercase captions in corecore (6%), half of them the source's own title; italic serif quotes in hopecore |
| The 2023 nonsense turn, nichetok | "unintelligible meme dumps", "pleasurable rush", "increasingly chaotic" | `chaos` mode: bursts first, random speeds, 35% layering, more letterboxing and flashes |
| Hopecore | "positive stylistic offshoot" | `hopecore` mode: same phrases, warmer picks, quotes, light flashes, no cut to black |
| Vertical format | TikTok | 9:16 frame option; clips are cover-fitted and panned |
| Everyone watching the same feed | the genre is about the shared scroll | live channel: clock-derived seed, viewers fast-forward to the same cue |

## 4. Sources

Read directly:
- Wikipedia, "Corecore": https://en.wikipedia.org/wiki/Corecore

Via search summaries (cited by the article or covering the same ground):
- Moises Mendez II, Time, "What to Know About the Corecore Aesthetic Taking Over TikTok": https://time.com/6248637/corecore-tiktok-aesthetic/
- Chance Townsend, Mashable, on corecore and its signifiers
- Hannah Ewens, The Guardian, on corecore as commentary on content
- Isabella Segalovich, Hyperallergic, "What Does TikTok's Corecore Have to Do With Dada?": https://hyperallergic.com/what-does-tiktoks-corecore-have-to-do-with-dada/
- Rhea Nayyar, Hyperallergic, on weirdcore and corecore
- Amanda Silberling, TechCrunch, "TikTok's 'corecore' is the latest iteration of absurdist meme art"
- Kieran Press-Reynolds, on the early frenetic form (cited by Time and Mashable)
- Felicity Martin, i-D, on Aphex Twin's Gen Z following: https://i-d.co/article/aphex-twin-gen-z-following-tiktok/
- The Guardian on Aphex Twin as the soundtrack to Gen Z life online (2026)
- Y7 (Declan Colquitt and Hannah Cobb), Flash Art, "A Postmortem of #corecore": https://flash---art.com/article/corecore/
- Vice, "Corecore is the Screaming-Into-Void TikTok Trend We Deserve": https://www.vice.com/en/article/corecore-tiktok-trend-explained/
- NBC News, "#CoreCore videos are becoming more popular on TikTok": https://www.nbcnews.com/pop-culture/pop-culture-news/corecore-videos-tiktok-trend-rcna65515
- Know Your Meme, "Corecore": https://knowyourmeme.com/memes/cultures/corecore
- Nassau Weekly, "Corecore and the Logic of Montage": https://nassauweekly.com/corecore-and-the-logic-of-montage/
- Her Campus and Daily Dot on hopecore (Sinatra, Bob Marley, `#nichetok` tagging)
- GNET, "Corecore: a TikTok Trend as Initiation to Incel Ideology": https://gnet-research.org/2024/08/05/corecore-a-tiktok-trend-as-initiation-to-incel-ideology/
