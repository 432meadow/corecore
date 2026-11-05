"""Starter ingest jobs, in two sets.

ARCHIVAL_JOBS: Internet Archive queries chosen for the material corecore edits lean on. Mostly the
Prelinger Archives (public-domain ephemeral films: ads, suburbs, industry, civil defence, hygiene films),
plus NASA and community uploads. Tags are the sequencer's contrast vocabulary (see CONTRAST_PAIRS in
web/sequencer.js), so each query carries the themes its footage will be cut against.

These are suggestions, not a curated dataset: search results shift, and not every item has an mp4
derivative. `python -m corecore seed` queues them; the CI build runs them within a time budget."""

ARCHIVAL_JOBS = [
    # consumerism / ads / home
    {"provider": "archive", "query": "collection:prelinger AND subject:(television commercials OR advertising)",
     "max_items": 5, "tags": ["archive", "ads", "consumerism"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(shopping OR supermarkets OR department stores)",
     "max_items": 4, "tags": ["archive", "consumerism", "crowd"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(suburbs OR family life OR home)",
     "max_items": 5, "tags": ["archive", "home", "childhood"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(teenagers OR dating OR etiquette)",
     "max_items": 4, "tags": ["archive", "childhood", "faces"]},
    # work / industry / machines
    {"provider": "archive", "query": "collection:prelinger AND subject:(industry OR factories OR manufacturing OR steel)",
     "max_items": 5, "tags": ["archive", "industry", "work", "machines"]},
    {"provider": "archive", "query": "collection:prelinger AND subject:(agriculture OR farming OR food)",
     "max_items": 3, "tags": ["archive", "nature", "work"]},
    # fear / war
    {"provider": "archive", "query": "collection:prelinger AND subject:(civil defense OR atomic OR nuclear)",
     "max_items": 4, "tags": ["archive", "war", "fear"]},
    # city / traffic / crowds
    {"provider": "archive", "query": "collection:prelinger AND subject:(cities OR traffic OR highways OR automobiles)",
     "max_items": 5, "tags": ["archive", "city", "traffic"]},
    # screens / tech / future
    {"provider": "archive", "query": "collection:prelinger AND subject:(computers OR television OR future OR automation)",
     "max_items": 4, "tags": ["archive", "screens", "future"]},
    {"provider": "archive", "query": "collection:computerchronicles", "max_items": 3,
     "tags": ["archive", "screens", "tech", "voice"]},
    # faces / voice
    {"provider": "archive", "query": "collection:prelinger AND subject:(mental health OR psychology OR hygiene)",
     "max_items": 4, "tags": ["archive", "faces", "voice"]},
    {"provider": "archive", "query": "collection:newsandpublicaffairs AND subject:(news)", "max_items": 3,
     "tags": ["news", "voice", "modern"]},
    # space / earth / nature
    {"provider": "archive", "query": "collection:nasa AND (subject:(apollo) OR subject:(earth) OR subject:(shuttle))",
     "max_items": 5, "tags": ["space", "earth"]},
    {"provider": "archive", "query": "collection:opensource_movies AND subject:(nature OR wildlife OR ocean OR forest)",
     "max_items": 5, "tags": ["nature"]},
    {"provider": "archive", "query": "collection:opensource_movies AND subject:(timelapse OR time-lapse)",
     "max_items": 4, "tags": ["city", "time", "modern"]},
    {"provider": "archive", "query": "collection:opensource_movies AND subject:(surveillance OR cctv OR dashcam)",
     "max_items": 3, "tags": ["cctv", "modern"]},
]


# CONTEMPORARY_JOBS: internet-native material. The Internet Archive's `mirrortube` collection holds about two
# million YouTube videos people archived (920k from 2022 on), with H.264 files: dashcams, vlogs, walking tours,
# driving POVs, game clips, pets, raw footage. Queries use quoted phrases (the archive's search treats
# `dash cam` as dash OR cam), newest-first ordering, and the title blocklist in config.py. These are other
# people's uploads: fine for a personal pool, your call for anything you publish.
_MT = "collection:mirrortube AND "
_NEW = " |sort=date desc"
CONTEMPORARY_JOBS = [
    # Mirrored short-form uploads: TikTok (78k items), Instagram reels (11k), Twitter video (142k). Titles are
    # the original captions, so hashtag words work as queries. Short clips: a few shots each, many sources.
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(vlog OR dayinmylife OR \"day in my life\" OR grwm)" + _NEW,
     "max_items": 10, "tags": ["vlog", "faces", "home", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(dashcam OR driving OR roadtrip OR nightdrive)" + _NEW,
     "max_items": 8, "tags": ["dashcam", "traffic", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(asmr OR satisfying OR relaxing OR cleaning)" + _NEW,
     "max_items": 8, "tags": ["asmr", "quiet", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(cat OR dog OR kitten OR puppy)" + _NEW,
     "max_items": 8, "tags": ["animals", "home", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(pov OR \"a day\" OR walk OR city OR night)" + _NEW,
     "max_items": 8, "tags": ["city", "vlog", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:instagram-*" + _NEW, "max_items": 10,
     "tags": ["reels", "modern", "phone"]},
    {"provider": "archive", "query": _MT + 'title:("dash cam" OR dashcam)' + _NEW, "max_items": 6,
     "tags": ["dashcam", "traffic", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(dashcam OR "dash cam") AND title:(russia OR russian OR winter OR snow OR compilation)' + _NEW,
     "max_items": 4, "tags": ["dashcam", "traffic", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("driving pov" OR "drive with me" OR "driving in" OR "night drive")' + _NEW,
     "max_items": 4, "tags": ["traffic", "city", "modern"]},
    {"provider": "archive", "query": _MT + "title:(vlog) AND date:[2022-01-01 TO 2029-12-31]" + _NEW, "max_items": 6,
     "tags": ["vlog", "faces", "home", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("day in my life" OR "day in the life" OR "morning routine" OR "come with me")' + _NEW,
     "max_items": 5, "tags": ["vlog", "home", "faces", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("walking tour" OR "night walk" OR "4k walk" OR "walk in")' + _NEW,
     "max_items": 5, "tags": ["city", "crowd", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("caught on camera" OR "security camera" OR "ring doorbell" OR cctv)' + _NEW,
     "max_items": 4, "tags": ["cctv", "modern", "fear"]},
    {"provider": "archive", "query": _MT + "title:(asmr)" + _NEW, "max_items": 4, "tags": ["asmr", "faces", "quiet", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("time lapse" OR timelapse OR hyperlapse OR "drone footage" OR "drone view" OR "4k drone")' + _NEW,
     "max_items": 4, "tags": ["city", "nature", "time", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(minecraft OR fortnite OR roblox OR "gta 5") AND title:(funny OR moments OR fail OR glitch)' + _NEW,
     "max_items": 4, "tags": ["screens", "games", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(grocery OR supermarket OR walmart OR costco OR "shopping")' + _NEW,
     "max_items": 4, "tags": ["consumerism", "crowd", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("my cat" OR "my dog" OR kitten OR puppy OR "funny animals")' + _NEW,
     "max_items": 4, "tags": ["animals", "home", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("oddly satisfying" OR satisfying OR relaxing OR ambient)' + _NEW,
     "max_items": 4, "tags": ["quiet", "still", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("first day" OR "last day" OR "we moved" OR "moving out" OR goodbye)' + _NEW,
     "max_items": 4, "tags": ["home", "faces", "modern"]},
    # Beauty: kindness, subtle natural poignance, machines watching nature. The pool leans dark without it.
    # Title words on the mirror found games, manga dubs and news ("fox" gave Star Fox, "paid for" gave campaign
    # news, "blossom" gave product reviews), so these go to corners of the archive where the footage is what
    # it says: the park service's own camera work (public domain), Flickr's wildlife clips (CC BY), nature
    # centres' trail cameras, nest cams, a bear cam. The mirrors are kept to phrases junk rarely carries; the
    # short-form mirrors were dropped here, since half of what their wildlife hashtags found was sketches.
    {"provider": "archive", "query": 'identifier:nps-video-* AND creator:("Neal Herbert") AND NOT title:(what OR how OR why OR does OR has OR should OR when OR will OR program OR crowd OR "pre-show" OR fight OR visiting OR managing OR collaring OR "in depth" OR inside OR short OR vendors OR interview OR challenges OR kill OR carcass OR plowing OR webinar OR talk OR musical OR rumor OR equipment OR chase OR discusses OR ranger OR jams) |sort=downloads desc',
     "max_items": 12, "tags": ["nature", "animals", "light", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'identifier:Flickr-* AND mediatype:movies AND title:(deer OR fawn OR fox OR owl OR owlet OR owlets OR heron OR egret OR squirrel OR raccoon OR hummingbird OR chickadee OR nuthatch OR woodpecker OR bluebird OR cardinal OR hedgehog OR badger OR "bird feeder" OR "bird bath" OR "trail camera" OR "game camera" OR "baby birds" OR "backyard birds" OR nestlings OR fledgling OR fledglings OR ducklings OR goslings OR "bird nest" OR "on the nest") AND NOT title:("owl city" OR albatross OR attacks OR prey OR preying OR shredding OR rat OR raid OR injured OR biologists OR "photo credit") |sort=downloads desc',
     "max_items": 12, "tags": ["nature", "animals", "trailcam", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'mediatype:movies AND NOT collection:mirrortube AND title:("trail cam" OR "trail camera" OR "trail cameras" OR trailcam OR "game camera" OR "game cam" OR "wildlife camera" OR "wildlife cam" OR "critter cam" OR "nature cam") AND NOT title:(godot OR petito OR review OR unboxing OR weird OR "fox den" OR volunteers OR "slide show" OR wakefield OR albatross OR switching) |sort=downloads desc',
     "max_items": 10, "tags": ["trailcam", "nature", "animals", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'mediatype:movies AND NOT collection:mirrortube AND title:("eagle cam" OR "osprey cam" OR "owl cam" OR "falcon cam" OR "heron cam" OR "nest cam" OR nestcam OR "nest box" OR "owl box" OR "hummingbird nest" OR "bluebird box" OR "eagle nest" OR "osprey nest" OR eaglets OR owlets OR "feeder cam" OR "hummingbird feeder") AND NOT title:("fox den" OR "bird box" OR news OR episode OR wakefield OR meeting OR council OR review OR challenge OR google OR team OR veranda OR elementary OR puts OR relocation OR plans OR renovations OR nowthis OR wearable OR "how to" OR install OR installing OR build OR prey OR shredding OR greeting OR attack OR attacks OR basketball OR baseball OR "orchard lake" OR "at home" OR "owl box in") |sort=downloads desc',
     "max_items": 8, "tags": ["trailcam", "nature", "animals", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'mediatype:movies AND NOT collection:mirrortube AND title:("Brooks Falls" OR "bear cam" OR bearcam OR (Katmai AND (bear OR bears OR grazer OR cubs))) AND NOT title:(fight OR skirmish OR bulldozes OR runs OR tourists OR school) |sort=date desc',
     "max_items": 6, "tags": ["trailcam", "nature", "animals", "beauty", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("street piano" OR "public piano" OR busker OR "street musician") AND NOT title:(tutorial OR lesson OR cover OR karaoke)' + _NEW,
     "max_items": 5, "tags": ["kind", "crowd", "voice", "beauty", "modern"]},
    {"provider": "archive", "query": 'identifier:Flickr-* AND mediatype:movies AND creator:(USFWS OR "Fish and Wildlife" OR "National Park" OR "Bureau of Land Management") AND NOT title:(drone OR training OR burn OR burning OR fire OR wildfire OR "leave no trace" OR "off-highway" OR ohv OR psa OR meeting OR webinar OR interview OR talk OR ceremony OR press OR announcement OR "how to" OR safety OR hunting OR hunt OR "public lands day" OR volunteers OR video) |sort=downloads desc',
     "max_items": 10, "tags": ["nature", "animals", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'identifier:Flickr-* AND mediatype:movies AND title:(sunrise OR sunset OR "golden hour" OR fog OR mist OR snowfall OR "first snow" OR "falling snow" OR aurora OR "northern lights" OR "milky way" OR dusk OR dawn OR moonrise OR rainbow) AND NOT title:(party OR wedding OR concert OR festival OR drone OR timelapse OR time-lapse) |sort=downloads desc',
     "max_items": 10, "tags": ["light", "nature", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'identifier:Flickr-* AND mediatype:movies AND title:(waves OR surf OR creek OR brook OR stream OR waterfall OR "river" OR forest OR meadow OR "in the wind" OR "rain on" OR "cherry blossom" OR blossoms OR lavender OR "fall colors" OR "autumn leaves" OR "wheat field" OR fireflies) AND NOT title:(party OR wedding OR concert OR festival OR drone OR race OR boat OR jet) |sort=downloads desc',
     "max_items": 10, "tags": ["nature", "weather", "quiet", "beauty", "modern"]},
    {"provider": "archive", "query": 'identifier:Flickr-* AND mediatype:movies AND title:("my dog" OR "my cat" OR "our dog" OR "our cat" OR puppy OR puppies OR kitten OR kittens OR "first steps" OR "first snow" OR grandma OR grandpa OR grandmother OR grandfather OR "snow day" OR sledding OR playground OR bedtime OR "blowing bubbles") AND NOT title:(party OR wedding OR drone OR test) |sort=downloads desc',
     "max_items": 8, "tags": ["kind", "home", "childhood", "animals", "beauty", "modern"]},
    # More of the mundane and the strange: transit, weather, liminal places, work, animals, rituals, crowds.
    {"provider": "archive", "query": _MT + 'title:(train OR subway OR metro OR tram) AND title:(ride OR pov OR window OR "cab view")' + _NEW,
     "max_items": 5, "tags": ["traffic", "city", "modern", "transit"]},
    {"provider": "archive", "query": _MT + 'title:("plane window" OR takeoff OR landing OR "airport") AND title:(view OR pov OR timelapse OR walk)' + _NEW,
     "max_items": 4, "tags": ["traffic", "crowd", "modern", "transit"]},
    {"provider": "archive", "query": _MT + 'title:(rain OR snow OR fog OR thunderstorm OR "heavy rain") AND title:(walk OR drive OR window OR "4k" OR night)' + _NEW,
     "max_items": 5, "tags": ["nature", "quiet", "modern", "weather"]},
    {"provider": "archive", "query": _MT + 'title:(abandoned OR urbex OR liminal OR "empty mall" OR "dead mall")' + _NEW,
     "max_items": 5, "tags": ["liminal", "quiet", "modern", "fear"]},
    {"provider": "archive", "query": _MT + 'title:(laundromat OR "gas station" OR "parking lot" OR "convenience store" OR "24 hours" OR "3am")' + _NEW,
     "max_items": 4, "tags": ["liminal", "city", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(aquarium OR "fish tank" OR jellyfish OR "bird feeder" OR "trail cam")' + _NEW,
     "max_items": 4, "tags": ["animals", "quiet", "modern", "nature"]},
    {"provider": "archive", "query": _MT + 'title:("street food" OR "night market" OR "food stall" OR "what i eat")' + _NEW,
     "max_items": 4, "tags": ["crowd", "consumerism", "modern", "food"]},
    {"provider": "archive", "query": _MT + 'title:(skate OR skateboarding OR parkour OR bmx OR "longboard")' + _NEW,
     "max_items": 4, "tags": ["motion", "city", "modern", "faces"]},
    {"provider": "archive", "query": _MT + 'title:(factory OR "production line" OR "how it\'s made" OR warehouse OR "assembly line")' + _NEW,
     "max_items": 4, "tags": ["industry", "work", "machines", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("day in the life") AND title:(nurse OR driver OR worker OR teacher OR barista OR "delivery")' + _NEW,
     "max_items": 4, "tags": ["work", "vlog", "faces", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(graduation OR wedding OR "first day of school" OR "birthday party" OR "baby")' + _NEW,
     "max_items": 4, "tags": ["home", "childhood", "faces", "modern"]},
    {"provider": "archive", "query": _MT + 'title:(concert OR festival OR "crowd" OR "mosh pit" OR "fireworks")' + _NEW,
     "max_items": 4, "tags": ["crowd", "modern", "noise"]},
    {"provider": "archive", "query": _MT + 'title:(karaoke OR "singing in the car" OR "car karaoke" OR "singing at")' + _NEW,
     "max_items": 3, "tags": ["faces", "voice", "home", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("live cam" OR webcam OR "earth cam" OR "beach cam" OR "harbor cam")' + _NEW,
     "max_items": 4, "tags": ["cctv", "quiet", "modern"]},
    {"provider": "archive", "query": _MT + 'title:("screen recording" OR "desktop" OR "scrolling" OR "typing")' + _NEW,
     "max_items": 3, "tags": ["screens", "modern", "quiet"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(rain OR night OR fog OR snow OR sunset)" + _NEW,
     "max_items": 8, "tags": ["nature", "quiet", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(cooking OR recipe OR \"what i eat\" OR coffee)" + _NEW,
     "max_items": 6, "tags": ["home", "food", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(gym OR workout OR running OR \"morning run\")" + _NEW,
     "max_items": 6, "tags": ["faces", "motion", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(roadtrip OR \"road trip\" OR travel OR airport OR train)" + _NEW,
     "max_items": 6, "tags": ["traffic", "transit", "modern", "phone"]},
    {"provider": "archive", "query": "identifier:tiktok-* AND title:(thrift OR \"thrift store\" OR \"garage sale\" OR \"flea market\")" + _NEW,
     "max_items": 5, "tags": ["consumerism", "modern", "phone"]},
    # Dailymotion search (public API); downloads need yt-dlp's impersonation extra, see README
    {"provider": "dailymotion", "query": "russian dashcam compilation", "max_items": 3, "tags": ["dashcam", "traffic", "modern"]},
    {"provider": "dailymotion", "query": "caught on dashcam", "max_items": 3, "tags": ["dashcam", "traffic", "modern"]},
]

# Queries taken out of the sets because of what they brought in. The audit removes every source they ever
# ingested from the pool, files and all.
RETIRED_QUERIES = [
    # caught-on-camera tweets: an animal kicked in the street, a man beaten to death, deaths, a plane crash,
    # riots, partisan posts; the mirrortube dashcam queries cover the dashcams
    "identifier:twitter-* AND title:(dashcam OR cctv OR \"caught on\" OR doorbell)" + _NEW,
]

BEAUTY_JOBS = [j for j in CONTEMPORARY_JOBS if "beauty" in j["tags"]]
SEED_SETS = {"contemporary": CONTEMPORARY_JOBS, "beauty": BEAUTY_JOBS, "archival": ARCHIVAL_JOBS, "all": CONTEMPORARY_JOBS + ARCHIVAL_JOBS}
STARTER_JOBS = CONTEMPORARY_JOBS  # what `seed` and `build-site` use unless --set says otherwise
