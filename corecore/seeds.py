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
    # Kindness, home and weather, each query scouted through the provider and re-rated by an independent
    # reader before it went in; the 1930s-60s home movies they also found are archival, so they stay out.
    # buskers and the people who stop, outside the YouTube mirror (rated 28/30 good of 104)
    {"provider": "archive", "query": "mediatype:movies AND NOT collection:(mirrortube OR movie_trailers OR roguetv) AND NOT identifier:tiktok-* AND title:(busker OR buskers OR busking OR \"street performer\" OR \"street performers\" OR \"street musician\" OR \"street musicians\" OR \"street piano\" OR \"public piano\") AND NOT title:(interview OR interviews OR documentary OR \"Tonight Show\" OR \"Stray Kids\" OR \"Scam School\" OR committee OR meeting OR regulations OR \"Happy Hour\" OR VOD OR stream OR Muslim OR LondonIsOpen OR Auditioning OR \"Picture Box\" OR Blobby OR Kickoff OR \"Opening Concert\" OR \"Lunch Concert\" OR Installations OR \"Hong Kong\" OR Disney OR Worst OR \"Text To Speech\" OR request OR Routine OR \"Shout Out\" OR \"Peek Bytes\" OR Happening OR \"In Your Neighborhood\" OR \"Blues Buskers\" OR Tribute OR \"Busker Hunt\" OR \"Human Transformer\" OR Lifestyle OR CityStream OR harmonious OR mission OR cover OR Gift OR panning OR Project OR y2mate OR Iran OR Fearless OR \"open mic\" OR Balladeer OR \"BBC Archive\") AND NOT creator:(\"Mayor of London\" OR \"Achievement Hunter\" OR \"Rooster Teeth\" OR \"Middle East Eye\" OR OpenPublica OR \"Let Me Explain Studios\" OR \"Revision 3\" OR WCCA OR \"Terry Love\" OR \"City of Seattle\" OR \"Boston City TV\") |sort=downloads desc",
     "max_items": 4, "tags": ["kind", "voice", "crowd", "beauty", "modern"]},
    # the 2005-06 camcorder years: first steps, birthdays, grandparents, a sleeping dog (rated 26/30 good of 118)
    {"provider": "archive", "query": "collection:ourmedia AND mediatype:movies AND title:(\"my grandmother\" OR \"my grandfather\" OR grandma OR grandpa OR oma OR \"my garden\" OR \"our garden\" OR \"the garden\" OR \"my dog\" OR \"my cat\" OR \"our dog\" OR \"our cat\" OR \"new puppy\" OR \"new kitten\" OR \"my son\" OR \"my daughter\" OR \"our baby\" OR \"baby's first\" OR \"laughing baby\" OR \"first birthday\" OR \"first steps\" OR \"learning to walk\" OR \"kids at play\" OR \"kids playing\" OR \"children playing\" OR \"playing in the snow\" OR \"in the snow\" OR \"at the beach\" OR \"at the park\" OR \"in the pool\" OR \"in the leaves\" OR \"bath time\" OR \"on the swing\" OR \"flying a kite\" OR \"christmas morning\" OR \"opening presents\" OR \"pumpkin patch\" OR \"feeding the ducks\" OR chickens) AND NOT title:(speech OR lobbyist OR myspace OR shares OR \"home movies\" OR \"show it\" OR \"he's\" OR atv OR trailer OR teaser OR interview OR conversations OR music OR song OR remix OR mv OR huggies OR frosty OR exile OR angels OR robot OR victoria OR \"how to\" OR irrigation OR \"mad city\" OR tribute OR remembering OR test OR househunting OR service OR sermon OR crew OR productions OR \"in common\" OR episode OR ppv OR nightmare OR wrestling) |sort=downloads desc",
     "max_items": 6, "tags": ["home", "childhood", "kind", "beauty", "modern"]},
    # back gardens, bees, hens, mowing the lawn, cows (rated 26/30 good of 124)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(garden OR allotment OR backyard OR \"back yard\" OR porch OR lawn OR \"bird bath\" OR greenhouse OR orchard OR chickens OR hens OR rooster OR goats OR lambs OR piglets OR pigs OR farm OR cows OR calf OR donkey OR pony OR beehive OR bees) AND NOT title:(drone OR training OR slideshow OR mountain OR \"dall sheep\" OR eden OR disco OR library OR hotel OR dead OR \"wind farm\" OR attack OR explains OR battle OR theatre OR burning OR barge OR cemetery OR memorial OR engines OR smoldering OR \"farm bill\" OR tribute OR truffled OR barrel) |sort=downloads desc",
     "max_items": 6, "tags": ["home", "nature", "animals", "beauty", "modern"]},
    # kids in puddles and surf, family walks and dinners (rated 25/30 good of 81)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(kids OR children OR family OR mom OR dad OR \"my son\" OR \"my daughter\" OR birthday OR \"christmas morning\" OR xmas OR toddler OR boys OR girls) AND NOT title:(party OR wedding OR drone OR test OR concert OR festival OR interviewing OR interview OR dead OR fire OR robot OR ribbon OR rescue OR service OR voicemail OR live OR show OR museum OR burn OR clockwork OR coral OR corals OR slug OR slugs OR beetle OR larva OR \"sea cucumber\" OR rat OR pigeon OR tech OR queen OR sky OR \"beach boys\" OR berkhof OR muslim OR photographed OR memorial OR cemetery OR calder OR statefairtx OR invitational) |sort=downloads desc",
     "max_items": 6, "tags": ["childhood", "home", "kind", "beauty", "modern"]},
    # pets at home and at the park (rated 25/30 good of 39)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(dog OR dogs OR doggy OR cat OR cats OR kitty OR bunny OR rabbit OR parrot OR budgie OR cockatiel OR tortoise OR goldfish OR hamster OR \"guinea pig\" OR pets OR pony OR horse OR horses) AND NOT title:(\"my dog\" OR \"my cat\" OR puppy OR kitten OR show OR race OR racing OR rodeo OR police OR parade OR drone OR test OR wild OR scan OR banksy OR animatronic OR botulism OR paints OR gather OR roundup OR fish OR \"prairie dog\" OR \"dog-faced\" OR snake OR \"sea\" OR hotdog OR \"hot dog\" OR tick OR fight OR summit) |sort=downloads desc",
     "max_items": 4, "tags": ["animals", "home", "beauty", "modern"]},
    # rain, storms seen from balconies, hail, wind (rated 24/30 good of 243)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(rain OR raining OR rainy OR raindrops OR drizzle OR downpour OR puddle OR puddles OR umbrella OR umbrellas OR \"rain shower\" OR rainstorm OR \"rain storm\" OR thunderstorm OR thunderstorms OR \"summer storm\" OR \"storm clouds\" OR hail OR hailstorm OR windy OR breeze OR swaying OR \"wind chimes\" OR \"wind in the trees\") AND NOT title:(dance OR dancing OR \"rain on\" OR \"in the wind\" OR concert OR festival OR party OR wedding OR game OR race OR racing OR flood OR flooding OR damage OR drone OR rainforest OR \"rain forest\" OR sprinkler OR \"purple rain\" OR stevie OR sinatra OR song OR chasing OR chaser OR gamma OR disco OR \"hail mary\" OR sailing OR kite OR kiteboarding OR surfing OR windsurfing OR turbine OR turbines OR trial OR test OR skeleton OR performs OR tournament OR challenge OR exhibit OR \"rain check\" OR kingdom) AND NOT creator:(NASA) |sort=downloads desc",
     "max_items": 6, "tags": ["weather", "quiet", "nature", "beauty", "modern"]},
    # snow falling on streets and yards, from train windows (rated 26/30 good of 69)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(snowing OR snowflakes OR \"snow falling\" OR \"snowy night\" OR \"snowy day\" OR \"snowy street\" OR blizzard OR \"snow storm\" OR snowstorm OR \"heavy snow\" OR \"lake effect\" OR \"let it snow\" OR \"winter wonderland\" OR icicles OR \"winter night\" OR \"snow at night\") AND NOT title:(\"first snow\" OR \"falling snow\" OR snowfall OR \"snow day\" OR owl OR sledding OR skiing OR snowboard OR snowmobile OR plow OR plowing OR crash OR party OR concert OR game OR pictures OR slideshow OR nokia OR canon OR \"ice storm\") |sort=downloads desc",
     "max_items": 6, "tags": ["weather", "quiet", "beauty", "modern"]},
    # lighthouses, moonlight, street lights, views from windows (rated 23/30 good of 54)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(lighthouse OR \"city lights\" OR \"street lights\" OR streetlights OR \"night lights\" OR \"harbor lights\" OR lanterns OR moonlight OR moonlit OR \"full moon\" OR \"christmas lights\" OR \"city at night\" OR twilight OR \"blue hour\" OR nightfall OR \"night falls\" OR \"after dark\" OR \"evening light\" OR \"my window\" OR \"out the window\" OR \"office window\" OR \"bedroom window\" OR \"kitchen window\" OR \"apartment window\" OR \"hotel window\" OR \"cabin window\" OR \"plane window\" OR \"train window\" OR \"from the train\" OR \"night drive\") AND NOT title:(\"friday night\" OR antique OR gallery OR frame OR concert OR festival OR party OR wedding OR parade OR race OR club OR show OR drone OR \"milky way\" OR test OR trial OR \"stained glass\" OR \"twilight zone\" OR saga OR skeleton) AND NOT creator:(\"Comrade King\") |sort=downloads desc",
     "max_items": 5, "tags": ["light", "quiet", "transit", "beauty", "modern"]},
    # the park service's soundscapes and weather time-lapses (rated 25/30 good of 36)
    {"provider": "archive", "query": "identifier:nps-video-* AND NOT creator:(\"Neal Herbert\") AND title:(\"b-roll\" OR \"b roll\" OR broll OR soundscape OR soundscapes OR timelapse OR \"time-lapse\" OR \"time lapse\" OR \"static shot\" OR \"bear byte\" OR \"sound byte\") AND title:(snow OR winter OR rain OR storm OR clouds OR fog OR mist OR sunrise OR sunset OR night OR stars OR weather OR lightning OR tides OR moon OR forest OR wind OR spring OR autumn OR fall OR summer OR dusk OR dawn OR water OR river OR creek OR lake) AND NOT title:(package OR installation OR installing OR panels OR construction OR crew OR \"re-vegetating\" OR battlefield OR fort OR memorial OR church OR mission OR climbers OR fire OR burn OR chats OR talk OR program) |sort=downloads desc",
     "max_items": 5, "tags": ["nature", "weather", "quiet", "beauty", "modern"]},
    # a Virginia videographer: fog, creeks, barns in rain, cows (rated 25/30 good of 484)
    {"provider": "archive", "query": "creator:(\"C. E. Price\") AND NOT title:(\"Harvest Of Death\" OR western OR montage OR \"Henry VIII\" OR CGI OR exercise OR projector OR phooning OR inspirations OR god OR lord OR blessed OR brethren OR \"wise men\" OR patience OR wisdom OR victory OR thine OR \"his breath\" OR contentment OR razors OR hart OR existing OR \"the kids\" OR \"higher than\" OR \"earthly peace\" OR faith OR jitney OR flatiron OR \"nature of things\" OR \"sing a song\" OR halloween OR hamburger OR TVA OR \"heating oil\" OR lonely OR intersection OR traffic OR vehicles) |sort=downloads desc",
     "max_items": 6, "tags": ["nature", "weather", "quiet", "beauty", "modern"]},
    # Grand Canyon b-roll: rafts, falls, sunrise, cloud inversions (rated 24/30 good of 143)
    {"provider": "archive", "query": "identifier:nps-video-* AND creator:(Blum OR Quinn OR \"Richard Burton\") AND NOT title:(\"visitor center\" OR director OR experiment OR store) |sort=downloads desc",
     "max_items": 6, "tags": ["nature", "light", "quiet", "beauty", "modern"]},
    # Pixabay nature clips: rain on a window at night, a fog forest, swans (rated 27/30 good of 85)
    {"provider": "archive", "query": "identifier:pixabay-* AND title:(bird OR birds OR swan OR duck OR robin OR hummingbird OR sunset OR sunrise OR sea OR ocean OR waves OR beach OR forest OR nature OR river OR lake OR waterfall OR flowers OR flower OR meadow OR field OR rain OR snow OR clouds OR sky OR mountains OR landscape OR cows OR horse OR dog OR cat OR leaves OR tree OR trees) AND NOT title:(render OR abstract OR background OR backgrounds OR loop OR animation OR particles OR space OR galaxy OR cosmos OR plexus OR neon OR explosion OR fire OR wormhole OR fractal OR digital OR \"3d\" OR snowflake OR \"jet ski\") |sort=downloads desc",
     "max_items": 5, "tags": ["nature", "weather", "light", "beauty", "modern"]},
    # long quiet tanks: jellies, sea dragons, a kelp forest (rated 23/30 good of 126)
    {"provider": "archive", "query": "identifier:Flickr-* AND mediatype:movies AND title:(aquarium OR jellyfish OR jellies OR \"sea dragon\" OR seahorse OR seahorses OR \"kelp forest\" OR \"fish tank\" OR \"sea otter\" OR \"sea otters\" OR penguins OR \"manta ray\" OR \"sea turtle\" OR \"coral reef\") AND NOT title:(laser OR mapping OR mating OR watching) |sort=downloads desc",
     "max_items": 5, "tags": ["animals", "quiet", "nature", "beauty", "modern"]},
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

# Sources taken out and then put back by the owner of the piece ("I will flag if something feels off"). Their
# files were deleted with them, so a build fetches each one again by its address until it is in the pool.
REINSTATED = [
    {"provider": "archive", "url": "https://archive.org/details/" + ident, "max_items": 1, "tags": tags}
    for ident, tags in (
        ("Instagram-DdeICa9AIqS", ["reels", "modern", "phone"]),
        ("youtube-FtWXWKUK6rg", ["dashcam", "traffic", "modern"]),
        ("youtube-hCU65_u4poM", ["liminal", "city", "modern"]),
        ("TikTok-7147085836130094382", ["nature", "animals", "modern", "phone"]),
        ("youtube-IWbXnhcdIfU", ["animals", "quiet", "modern", "nature"]),
        ("youtube-Zg-4zw7EcTY", ["home", "faces", "modern"]),
        ("youtube-__yfsYoKoNE", ["dashcam", "traffic", "modern"]),
        ("youtube-4YtwK9dGWrY", ["dashcam", "traffic", "modern"]),
    )
]

BEAUTY_JOBS = [j for j in CONTEMPORARY_JOBS if "beauty" in j["tags"]]
SEED_SETS = {"contemporary": CONTEMPORARY_JOBS, "beauty": BEAUTY_JOBS, "archival": ARCHIVAL_JOBS, "all": CONTEMPORARY_JOBS + ARCHIVAL_JOBS}
STARTER_JOBS = CONTEMPORARY_JOBS  # what `seed` and `build-site` use unless --set says otherwise
