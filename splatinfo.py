import random

class SplatMatchItem():
	def __init__(self, name, abbrevs):
		self._name      = name
		self._abbrevs   = abbrevs or []

	def name(self):
		return self._name

	def abbrev(self):
		return self._abbrevs[0] if len(self._abbrevs) else None

	def abbrevs(self):
		return self._abbrevs

	def format(self):
		return "__" + self._name + "__ (**" + self.abbrev() + "**)"

	def hasAbbrev(self, a):
		return a.lower() in self._abbrevs

class SplatMode(SplatMatchItem):
	pass

class SplatMap(SplatMatchItem):
	def __init__(self, name, shortname, abbrevs, id):
		self._shortname = shortname
		self._id	= id

		super().__init__(name, abbrevs)

	def shortname(self):
		return self._shortname

	def id(self):
		return self._id

class SplatSubweapon(SplatMatchItem):
	pass

class SplatSpecial(SplatMatchItem):
	pass

class SplatWeapon(SplatMatchItem):
	def __init__(self, name, abbrevs, sub, special, level, id, dupid):
		self._sub     = sub
		self._special = special
		self._level   = level
		self._id      = id
		self._dupid   = dupid
		super().__init__(name, abbrevs)

	def id(self):
		return self._id

	# Exact duplicates will have a dupid pointing to the original weapon
	def dupid(self):
		return self._dupid

class SplatMatchResult():
	def __init__(self, type, query, items):
		self.type  = type
		self.query = query
		self.items = items

	def isValid(self):
		return len(self.items) == 1

	def get(self):
		if self.isValid():
			return self.items[0]
		return None

	def errorMessage(self):
		l = len(self.items)
		if l == 0:
			return "I don't know of any " + self.type + " named '" + self.query + "'. Try command '" + self.type + "s list' for a list."
		elif l == 1:
			return None
		elif l == 2:
			return "Did you mean " + self.items[0].format() + " or " + self.items[1].format() + "?"
		elif l < 8:
			str = "Did you mean " + ", ".join(map(lambda item: item.format(), self.items[0:l - 1]))
			str += ", or " + self.items[l - 1].format() + "?"
			return str

		return "Try command '" + self.type + "s list' for a list of " + self.type + "s."


class SplatInfo():
	def __init__(self):
		self.initModes()
		self.initMaps()
		self.initSubweapons()
		self.initSpecials()
		self.initWeapons()

		self.checkSet(self.modes)
		self.checkSet(self.maps)
		self.checkSet(self.subweapons)
		self.checkSet(self.specials)
		self.checkSet(self.weapons)

	def checkSet(self, set):
		seenAbbrevs = {}
		for item in set:
			for abbrev in item.abbrevs():
				if abbrev in seenAbbrevs:
					print("SplatInfo: Abbrev '" + abbrev + "' used by both '" + item.name() + "' and '" + seenAbbrevs[abbrev].name() + "'")
				else:
					seenAbbrevs[abbrev] = item

	def initModes(self):
		self.modes = [
			SplatMode("Splat Zones", ["sz"]),
			SplatMode("Rainmaker", ["rm"]),
			SplatMode("Tower Control", ["tc"]),
			SplatMode("Clam Blitz", ["cb"]),
			SplatMode("Turf War", ["tw"]),
		]

	def initMaps(self):
		self.maps = [
			SplatMap("The Reef",              "Reef",        ["r", "tr"],          0),
			SplatMap("Musselforge Fitness",   "Musselforge", ["mf"],               1),
			SplatMap("Starfish Mainstage",    "Starfish",    ["sfm", "sm"],        2),
			SplatMap("Humpback Pump Track",   "Humpback",    ["hb", "hbpt", "hp"], 5),
			SplatMap("Inkblot Art Academy",   "Inkblot",     ["ia", "iac"],        4),
			SplatMap("Sturgeon Shipyard",     "Sturgeon",    ["ss"],               3),
			SplatMap("Moray Towers",          "Moray",       ["mt"],               8),
			SplatMap("Port Mackerel",         "Port Mac",    ["pm"],               7),
			SplatMap("Manta Maria",           "Manta",       ["mam"],              6),  # "mm" conflicts with Mako Mart
			SplatMap("Kelp Dome",             "Kelp",        ["kd"],               10),
			SplatMap("Snapper Canal",         "Snapper",     ["sc"],               9),
			SplatMap("Blackbelly Skatepark",  "Blackbelly",  ["bb", "bbsp", "bsp", "bs"], 11),
			SplatMap("MakoMart",              "Mako",        ["mkm"],              13),  # "mm" conflicts with Manta Maria
			SplatMap("Walleye Warehouse",     "Walleye",     ["wwh"],              14),  # "ww" conflicts with Wahoo World
			SplatMap("Shellendorf Institute", "Shellendorf", ["si"],               12),
			SplatMap("Arowana Mall",          "Arowana",     ["am"],               15),
			SplatMap("Goby Arena",            "Goby",        ["ga"],               18),
			SplatMap("Piranha Pit",           "Piranha",     ["pp"],               17),
			SplatMap("Camp Triggerfish",      "Triggerfish", ["ct", "ctf"],        16),
			SplatMap("Wahoo World",           "Wahoo",       ["whw"],              20),  # "ww" conflicts with Walleye Warehouse
			SplatMap("New Albacore Hotel",    "Albacore",    ["nah", "ah"],        19),
			SplatMap("Ancho-V Games",         "Ancho-V",     ["av", "avg", "ag"],  21),
			SplatMap("Skipper Pavilion",      "Skipper",     ["sp"],               22)
		]

	def initSubweapons(self):
		self.subweapons = [
			SplatSubweapon("Splat Bomb",   ["spb", "triangle"]),
			SplatSubweapon("Suction Bomb", ["sub", "suck", "succ"]),
			SplatSubweapon("Burst Bomb",   ["bb", "bub"]),
			SplatSubweapon("Curling Bomb", ["cb", "cub"]),
			SplatSubweapon("Autobomb",     ["ab", "aub"]),
			SplatSubweapon("Ink Mine",     ["im"]),
			SplatSubweapon("Toxic Mist",   ["tm", "fart"]),
			SplatSubweapon("Point Sensor", ["ps"]),
			SplatSubweapon("Splash Wall",  ["sw"]),
			SplatSubweapon("Sprinkler",    ["s"]),
			SplatSubweapon("Squid Beakon", ["sb", "beacon"]),
			SplatSubweapon("Fizzy Bomb",   ["fb", "fib"]),
			SplatSubweapon("Torpedo",      ["t"])
		]

	def initSpecials(self):
		self.specials = [
			SplatSpecial("Autobomb Launcher",     ["aubl"]),
			SplatSpecial("Burst Bomb Launcher",   ["bubl"]),
			SplatSpecial("Curling Bomb Launcher", ["cubl"]),
			SplatSpecial("Splat Bomb Launcher",   ["spbl", "triangle"]),
			SplatSpecial("Suction Bomb Launcher", ["subl", "suck", "succ"]),
			SplatSpecial("Baller",                ["b"]),
			SplatSpecial("Booyah Bomb",           ["byb"]),             # "bb" conflicts with Bubble Blower
			SplatSpecial("Bubble Blower",         ["bub", "bubbles"]),  # "bb" conflicts with Booyah Bomb
			SplatSpecial("Ink Armor",             ["ia", "armour", "ink armour"]),
			SplatSpecial("Ink Storm",             ["is", "rain"]),
			SplatSpecial("Inkjet",                ["ij"]),
			SplatSpecial("Splashdown",            ["sd"]),
			SplatSpecial("Sting Ray",             ["sr"]),
			SplatSpecial("Tenta Missiles",        ["tm"]),
			SplatSpecial("Ultra Stamp",           ["us", "hammer"]),
		]

	def initWeapons(self):
		data = [
			[".52 Gal",       ["52g"],  "Splat Bomb",   "Baller",     14,	50],
			[".52 Gal Deco",  ["52gd"], "Curling Bomb", "Sting Ray",  22,   51],
			["Kensa .52 Gal", ["k52g"], "Splash Wall", "Booyah Bomb", 25,	52],

			[".96 Gal",      ["96g"],  "Sprinkler",    "Ink Armor",  21,	80],
			[".96 Gal Deco", ["96gd"], "Splash Wall",  "Splashdown", 26,	81],

			["Aerospray MG", ["amg", "aeromg"], "Suction Bomb", "Curling Bomb Launcher", 6, 	30],
			["Aerospray RG", ["arg", "aerorg"], "Sprinkler",    "Baller",                28, 	31],
			["Aerospray PG", ["apg", "aeropg"], "Burst Bomb",   "Booyah Bomb",           29,	32],

			["Ballpoint Splatling",         ["bp", "bps"],   "Toxic Mist",   "Inkjet",    25, 4030],
			["Ballpoint Splatling Nouveau", ["bpn", "bpsn"], "Squid Beakon", "Ink Storm", 28, 4031],

			["Bamboozler 14 Mk I",   ["bb1", "bamboo1", "boozler1"], "Curling Bomb", "Tenta Missiles",      18, 2050],
			["Bamboozler 14 Mk II",  ["bb2", "bamboo2", "boozler2"], "Toxic Mist",   "Burst Bomb Launcher", 21, 2051],
			["Bamboozler 14 Mk III", ["bb3", "bamboo3", "boozler3"], "Fizzy Bomb",   "Bubble Blower",       27, 2052],

			["Blaster",        ["b"],   "Toxic Mist", "Splashdown", 5,  210],
			["Custom Blaster", ["cub"], "Autobomb",   "Inkjet",     27, 211],

			["Bloblobber",      ["bl"],  "Splash Wall", "Ink Storm",             11,	3030],
			["Bloblobber Deco", ["bld"], "Sprinkler",   "Suction Bomb Launcher", 20,	3031],

			["Carbon Roller",      ["cr"],   "Autobomb",   "Ink Storm",         7,	1000],
			["Carbon Roller Deco", ["crd"],  "Burst Bomb", "Autobomb Launcher", 10,	1001],

			["Clash Blaster",     ["cb", "trash blaster"],      "Splat Bomb",   "Stingray",       30, 	230],
			["Clash Blaster Neo", ["cbn", "trash blaster neo"], "Curling Bomb", "Tenta Missiles", 30,	231],

			["Dapple Dualies",         ["dd", "red dapples"],               "Squid Beakon", "Suction Bomb Launcher", 26,	5000],
			["Dapple Dualies Nouveau", ["ddn", "blue dapples"],             "Toxic Mist",   "Ink Storm",             29,	5001],
			["Clear Dapple Dualies",   ["cdd", "clear dapples", "clappes"], "Torpedo",      "Splashdown",            30,	5002],

			["Dualie Squelchers",        ["ds", "squelchies"],         "Point Sensor", "Tenta Missiles", 12, 5030],
			["Custom Dualie Squelchers", ["cds", "custom squelchies"], "Splat Bomb",   "Ink Storm",      28, 5031],

			["Dynamo Roller",       ["dr"],  "Ink Mine",   "String Ray",  20,	1020],
			["Gold Dynamo Roller",  ["gdr"], "Splat Bomb", "Ink Armor",   25,	1021],
			["Kensa Dynamo Roller", ["kdr"], "Sprinkler",  "Booyah Bomb", 29,	1022],

			["E-liter 4K",              ["el", "el4k"],     "Ink Mine", "Ink Storm",         20, 2030],
			["Custom E-liter 4K",       ["cel", "cel4k"],   "Squid Beakon", "Bubble Blower", 26, 2031],

			["E-liter 4K Scope",        ["els", "el4ks"],   "Ink Mine",     "Ink Storm",     30, 2040],
			["Custom E-liter 4K Scope", ["cels", "cel4ks"], "Squid Beakon", "Bubble Blower", 30, 2041],

			["Explosher",        ["xp"],  "Sprinkler",    "Bubble Blower", 18,	3040],
			["Custom Explosher", ["cxp"], "Point Sensor"," Baller",        22,	3041],

			["Flingza Roller",      ["fr"],  "Splash Wall",  "Splat Bomb Launcher", 24, 1030],
			["Foil Flingza Roller", ["ffr"], "Suction Bomb", "Tenta Missiles",      28, 1031],

			["Glooga Dualies",       ["gd", "ggd"],   "Ink Mine",    "Inkjet",    17, 5020],
			["Glooga Dualies Deco",  ["gdd", "ggdd"], "Splash Wall", "Baller",    24, 5021],
			["Kensa Glooga Dualies", ["kgd", "kggd"], "Fizzy Bomb",  "Ink Armor", 27, 5022],

			["Goo Tuber",        ["gt"],  "Suction Bomb", "Splashdown", 22,	2060],
			["Custom Goo Tuber", ["cgt"], "Curling Bomb", "Inkjet",     28, 2061],

			["Heavy Splatling",       ["hs"],  "Sprinkler",    "Sting Ray",     8,	4010],
			["Heavy Splatling Deco",  ["hsd"], "Splash Wall",  "Bubble Blower", 12, 4011],
			["Heavy Splatling Remix", ["hsr"], "Point Sensor", "Booyah Bomb",   19,	4012],

			["H-3 Nozzlenose",        ["h3"],  "Point Sensor", "Tenta Missiles", 29, 310],
			["H-3 Nozzlenose D",      ["h3d"], "Suction Bomb", "Ink Armor",      30, 311],
			["Cherry H-3 Nozzlenose", ["ch3"], "Splash Wall",  "Bubble Blower",  30, 312],

			["Hydra Splatling",        ["hys"],            "Autobomb", "Splashdown", 27,	4020],
			["Custom Hydra Splatling", ["chys", "chydra"], "Ink Mine", "Ink Armor",  29,	4021],

			["Inkbrush",           ["ib"],  "Splat Bomb", "Splashdown", 5,  1100],
			["Inkbrush Nouveau",   ["ibn"], "Ink Mine",   "Baller",     7,  1101],
			["Permanent Inkbrush", ["pib"], "Sprinkler",  "Ink Armor",  12, 1102],

			["Jet Squelcher",        ["js"],  "Toxic Mist", "Tenta Missiles", 17,	90],
			["Custom Jet Squelcher", ["cjs"], "Burst Bomb", "Sting Ray",      27, 	91],

			["L-3 Nozzlenose",       ["l3"],  "Curling Bomb", "Baller",      18, 300],
			["L-3 Nozzlenose D",     ["l3d"], "Burst Bomb",   "Inkjet",      23, 301],
			["Kensa L-3 Nozzlenose", ["kl3"], "Splash Wall",  "Ultra Stamp", 27, 302],

			["Luna Blaster",       ["lb"],  "Splat Bomb", "Baller",                19, 200],
			["Luna Blaster Neo",   ["lbn"], "Ink Mine",   "Suction Bomb Launcher", 24, 201],
			["Kensa Luna Blaster", ["klb"], "Fizzy Bomb", "Ink Storm",             26, 202],

			["Nautilus 47", ["n47"], "Point Sensor", "Baller", 26, 4040],
			["Nautilus 79", ["n79"], "Suction Bomb", "Inkjet", 30, 4041],

			["N-Zap 85", ["nz85"], "Suction Bomb", "Ink Armor",      9,  60],
			["N-Zap 89", ["nz89"], "Autobomb",     "Tenta Missiles", 11, 61],
			["N-Zap 83", ["nz83"], "Sprinkler",    "Ink Storm",      19, 62],

			["Octobrush",         ["ob"],  "Autobomb",     "Inkjet",         10,	1110],
			["Octobrush Nouveau", ["obn"], "Squid Beakon", "Tenta Missiles", 15,	1111],
			["Kensa Octobrush",   ["kob"], "Suction Bomb", "Ultra Stamp",    20,	1112],

			["Mini Splatling",       ["ms"],          "Burst Bomb",   "Tenta Missiles", 23, 4000],
			["Zink Mini Splatling",  ["zms", "zini"], "Curling Bomb", "Ink Storm",      26, 4001],
			["Kensa Mini Splatling", ["kms", "kini"], "Toxic Mist",   "Ulta Stamp",     29, 4002],

			["Range Blaster",        ["rngb"],  "Suction Bomb", "Ink Storm",      14, 220],
			["Custom Range Blaster", ["crngb"], "Curling Bomb", "Bubble Blower",  18, 221],
			["Grim Range Blaster",   ["grngb"], "Burst Bomb",   "Tenta Missiles", 23, 222],

			["Rapid Blaster",       ["rapb"],            "Ink Mine",     "Splat Bomb Launcher", 13,	240],
			["Rapid Blaster Deco",  ["rapbd"],           "Suction Bomb", "Inkjet",              16,	241],
			["Kensa Rapid Blaster", ["krapb", "krapid"], "Torpedo",      "Baller",              21,	242],

			["Rapid Blaster Pro",       ["rapbp"],            "Toxic Mist",     "Ink Storm",	22,	250],
			["Rapid Blaster Pro Deco",  ["rapbpd"],           "Splash Wall",	"Ink Armor",	24,	251],

			["Slosher",      ["slosh"],               "Suction Bomb", "Tenta Missiles",      5,  3000],
			["Slosher Deco", ["sloshd", "sloshdeco"], "Sprinkler",    "Baller",              8,  3001],
			["Soda Slosher", ["sslosh", "sodaslosh"], "Splat Bomb",   "Burst Bomb Launcher", 16, 3002],

			["Sloshing Machine",       ["sm", "sloshine"],                  "Autobomb",     "Sting Ray",           13, 3020],
			["Sloshing Machine Neo",   ["smn", "sloshine neo"],             "Point Sensor", "Splat Bomb Launcher", 19, 3021],
			["Kensa Sloshing Machine", ["ksm", "kslosh", "kensa sloshine"], "Fizzy Bomb",   "Splashdown",          21, 3022],

			["Splash-o-matic",     ["splasho"],               "Toxic Mist", "Inkjet",                25, 20],
			["Neo Splash-o-matic", ["nsplasho", "neosplash"], "Burst Bomb", "Suction Bomb Launcher", 27, 21],

			["Sploosh-o-matic",     ["sploosh", "sploosho"],   "Curling Bomb", "Splashdown",     10, 0],
			["Neo Sploosh-o-matic", ["nsploosh", "nsploosho"], "Squid Beakon", "Tenta Missiles", 18, 1],
			["Sploosh-o-matic 7",   ["sploosh7", "sploosho7"], "Splat Bomb",   "Ultra Stamp",    23, 2],

			["Splat Charger",         ["sc"],          "Splat Bomb",  "Sting Ray",             3,  2010],
			["Firefin Splat Charger", ["fsc", "ffsc"], "Splash Wall", "Suction Bomb Launcher", 16, 2011],
			["Kensa Charger",         ["kc", "ksc"],   "Sprinkler",   "Baller",                19, 2012],

			["Splatterscope",         ["ssc"],                 "Splat Bomb",  "Sting Ray",             15, 2020],
			["Firefin Splatterscope", ["fssc", "fss", "ffss"], "Splash Wall", "Suction Bomb Launcher", 25, 2021],
			["Kensa Splatterscope",   ["kssc"],                "Sprinkler",   "Baller",                28, 2022],

			["Splat Brella",   ["sb"],  "Sprinkler", "Ink Storm",           9,  6000],
			["Sorella Brella", ["srb"], "Autobomb",  "Splat Bomb Launcher", 15, 6001],

			["Splat Dualies",         ["sd"],  "Burst Bomb",   "Tenta Missiles", 4,		5010],
			["Enperry Splat Dualies", ["esd"], "Curling Bomb", "Inkjet",         11,	5011],
			["Kensa Splat Dualies",   ["ksd"], "Suction Bomb", "Baller",         16,	5012],

			["Splat Roller",         ["sr"],   "Curling Bomb", "Splashdown",     3,		1010],
			["Krak-On Splat Roller", ["kosr"], "Squid Beakon", "Baller",         12,	1011],
			["Kensa Splat Roller",   ["ksr"],  "Splat Bomb",   "Bubbler Blower", 14,	1012],

			["Splattershot",          ["ss"],           "Burst Bomb",   "Splashdown",     2, 40],
			["Tentatek Splattershot", ["ttss", "ttek"], "Splat Bomb",   "Inkjet",         4, 41],
			["Kensa Splattershot",    ["kss"],          "Suction Bomb", "Tenta Missiles", 6, 42],

			["Splattershot Jr",        ["ssj", "ssjr", ], "Splat Bomb", "Ink Armor",     1,	10],
			["Custom Splattershot Jr", ["cssj", "cssjr"], "Autobomb",   "Ink Storm",     4,	11],
			["Kensa Splattershot Jr",  ["kssj", "kssjr"], "Torpedo",    "Bubble Blower", 9,	12],

			["Splattershot Pro",       ["ssp", "sspro"],           "Point Sensor", "Ink Storm",     10,	70],
			["Forge Splattershot Pro", ["fssp", "fsspro"],         "Suction Bomb", "Bubble Blower", 20,	71],
			["Kensa Splattershot Pro", ["kssp", "ksspro", "kpro"], "Splat Bomb",   "Booyah Bomb",   23,	72],

			["Squeezer",      ["sq"],  "Splash Wall", "Sting Ray",     16, 400],
			["Foil Squeezer", ["fsq"], "Splat Bomb",  "Bubble Blower", 25, 401],

			["Classic Squiffer", ["csq"],  "Point Sensor", "Ink Armor", 12, 2000],
			["New Squiffer",     ["nsq"],  "Autobomb",     "Baller",    17,	2001],
			["Fresh Squiffer",   ["frsq"], "Suction Bomb", "Inkjet",    24, 2002],

			["Tenta Brella",         ["tb"],  "Squid Beakon", "Bubbler Blower",        23, 6010],
			["Tenta Sorella Brella", ["tsb"], "Splash Wall",  "Curling Bomb Launcher", 28, 6011],
			["Tenta Camo Brella",    ["tcb"], "Ink Mine",     "Ultra Stamp",           28, 6012],

			["Dark Tetra Dualies",  ["dtd"], "Autobomb",  "Splashdown",        14,	5040],
			["Light Tetra Dualies", ["ltd"], "Sprinkler", "Autobomb Launcher", 21,	5041],

			["Tri-Slosher",         ["ts"],  "Burst Bomb", "Ink Armor", 15,	3010],
			["Tri-Slosher Nouveau", ["tsn"], "Splat Bomb", "Ink Storm", 17,	3011],

			["Undercover Brella",         ["ub"],  "Ink Mine",   "Splashdown", 13,	6020],
			["Undercover Sorella Brella", ["usb"], "Splat Bomb", "Baller",     19,	6021],
			["Kensa Undercover Brella",   ["kub"], "Torpedo",    "Ink Armor",  24,	6022],

			# === Duplicate weapons
			["Hero Blaster Replica",   ["herob", "heroblaster"],     "Toxic Mist",   "Splashdown",     5,  215,  210],
			["Hero Brella Replica",    ["herosb", "herobrella"],     "Sprinkler",    "Ink Storm",      9,  6005, 6000],
			["Hero Charger Replica",   ["herosc", "herocharger"],    "Splat Bomb",   "Sting Ray",      3,  2015, 2010],
			["Hero Dualie Replicas",   ["herosd", "herodualies"],    "Burst Bomb",   "Tenta Missiles", 4,  5015, 5010],
			["Hero Roller Replica",    ["herosr", "heroroller"],     "Curling Bomb", "Splashdown",     3,  1015, 1010],
			["Hero Shot Replica",      ["heross", "heroshot"],       "Burst Bomb",   "Splashdown",     2,  45,   40],
			["Hero Slosher Replica",   ["heroslosh", "heroslosher"], "Suction Bomb", "Tenta Missiles", 5,  3005, 3000],
			["Hero Splatling Replica", ["herohs", "herosplatling"],  "Sprinkler",    "Sting Ray",      8,  4015, 4010],
			["Herobrush Replica",      ["heroib", "herobrush"],      "Autobomb",     "Inkjet",         10, 1115, 1100],
			["Octo Shot Replica",      ["octoss", "octoshot"],       "Splat Bomb",   "Inkjet",         1,  46,   41]
		]

		self.weapons = []
		for w in data:
			name    = w[0]
			abbrevs = w[1]
			sub     = w[2]
			special = w[3]
			level   = w[4]
			id      = w[5]
			dupid   = w[6] if (len(w) >= 7) else None
			self.weapons.append(SplatWeapon(name, abbrevs, self.getSubweaponByName(sub), self.getSpecialByName(special), level, id, dupid))

	def matchItems(self, type, set, query):
		if len(query) == 0:
			return SplatMatchResult(type, query, [])

		query = query.lower()
		items = []

		# Stage 1: Look for exact match on a name or abbreviation
		for item in set:
			if item.hasAbbrev(query) or (item.name().lower() == query):
				return SplatMatchResult(type, query, [item])

		# Stage 2: Substring match of name
		for item in set:
			if item.name().lower().find(query) != -1:
				items.append(item)

		return SplatMatchResult(type, query, items)


	def matchMaps(self, query):
		return self.matchItems("map", self.maps, query)

	def getItemByName(self, set, name):
		for i in set:
			if i.name() == name:
				return i
		return None

	def getMapByName(self, name):
		return self.getItemByName(self.maps, name)

	def getSubweaponByName(self, name):
		return self.getItemByName(self.subweapons, name)

	def getWeaponByName(self, name):
		return self.getItemByName(self.weapons, name)

	def getSpecialByName(self, name):
		return self.getItemByName(self.specials, name)

	def getRandomMap(self):
		return random.choice(self.maps)

	def getRandomWeapon(self):
		weapons = list(filter(lambda w: w.dupid() == None, self.weapons))  # Get only non-duplicate weapons
		return random.choice(weapons)



