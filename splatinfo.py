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
		return "`" + self._name + "` (" + self.abbrev() + ")"

	def hasAbbrev(self, a):
		return a.lower() in self._abbrevs

class SplatMode(SplatMatchItem):
	pass

class SplatMap(SplatMatchItem):
	def __init__(self, name, shortname, abbrevs):
		self._shortname = shortname
		super().__init__(name, abbrevs)

	def shortname(self):
		return self._shortname

class SplatSubweapon(SplatMatchItem):
	pass

class SplatSpecial(SplatMatchItem):
	pass

class SplatWeapon(SplatMatchItem):
	def __init__(self, name, abbrevs, sub, special, level):
		self._sub     = sub
		self._special = special
		self._level   = level
		super().__init__(name, abbrevs)

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
			SplatMap("The Reef",              "Reef", ["r", "tr"]),
			SplatMap("Musselforge Fitness",   "Musselforge", ["mf"]),
			SplatMap("Starfish Mainstage",    "Starfish", ["sfm", "sm"]),
			SplatMap("Humpback Pump Track",   "Humpback", ["hb", "hbpt", "hp"]),
			SplatMap("Inkblot Art Academy",   "Inkblot", ["ia", "iac"]),
			SplatMap("Sturgeon Shipyard",     "Sturgeon", ["ss"]),
			SplatMap("Moray Towers",          "Moray", ["mt"]),
			SplatMap("Port Mackerel",         "Port Mac", ["pm"]),
			SplatMap("Manta Maria",           "Manta", ["mam"]),  # "mm" conflicts with Mako Mart
			SplatMap("Kelp Dome",             "Kelp", ["kd"]),
			SplatMap("Snapper Canal",         "Snapper", ["sc"]),
			SplatMap("Blackbelly Skatepark",  "Blackbelly", ["bb", "bbsp", "bsp", "bs"]),
			SplatMap("MakoMart",              "Mako", ["mkm"]),  # "mm" conflicts with Manta Maria
			SplatMap("Walleye Warehouse",     "Walleye", ["wwh"]),  # "ww" conflicts with Wahoo World
			SplatMap("Shellendorf Institute", "Shellendorf", ["si"]),
			SplatMap("Arowana Mall",          "Arowana", ["am"]),
			SplatMap("Goby Arena",            "Goby", ["ga"]),
			SplatMap("Piranha Pit",           "Piranha", ["pp"]),
			SplatMap("Camp Triggerfish",      "Triggerfish", ["ct", "ctf"]),
			SplatMap("Wahoo World",           "Wahoo", ["whw"]),  # "ww" conflicts with Walleye Warehouse
			SplatMap("New Albacore Hotel",    "Albacore", ["nah", "ah"]),
			SplatMap("Ancho-V Games",         "Ancho-V", ["av", "avg", "ag"]),
			SplatMap("Skipper Pavilion",      "Skipper", ["sp"])
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
			[".52 Gal",       ["52g"],  "Splat Bomb",   "Baller",     14],
			[".52 Gal Deco",  ["52gd"], "Curling Bomb", "Sting Ray",  22],
			["Kensa .52 Gal", ["k52g"], "Splash Wall", "Booyah Bomb", 25],

			[".96 Gal",      ["96g"],  "Sprinkler",    "Ink Armor",  21],
			[".96 Gal Deco", ["96gd"], "Splash Wall",  "Splashdown", 26],

			["Aerospray MG", ["amg", "aeromg"], "Suction Bomb", "Curling Bomb Launcher", 6],
			["Aerospray PG", ["apg", "aeropg"], "Burst Bomb",   "Booyah Bomb",           29],
			["Aerospray RG", ["arg", "aerorg"], "Sprinkler",    "Baller",                28],

			["Ballpoint Splatling",         ["bp", "bps"],   "Toxic Mist",   "Inkjet",    25],
			["Ballpoint Splatling Nouveau", ["bpn", "bpsn"], "Squid Beakon", "Ink Storm", 28],

			["Bamboozler 14 Mk I",   ["bb1", "bamboo1", "boozler1"], "Curling Bomb", "Tenta Missiles",      18],
			["Bamboozler 14 Mk II",  ["bb2", "bamboo2", "boozler2"], "Toxic Mist",   "Burst Bomb Launcher", 21],
			["Bamboozler 14 Mk III", ["bb3", "bamboo3", "boozler3"], "Fizzy Bomb",   "Bubble Blower",       27],

			["Blaster",        ["b"],   "Toxic Mist", "Splashdown", 5],
			["Custom Blaster", ["cub"], "Autobomb",   "Inkjet",     27],

			["Bloblobber",      ["bl"],  "Splash Wall", "Ink Storm",             11],
			["Bloblobber Deco", ["bld"], "Sprinkler",   "Suction Bomb Launcher", 20],

			["Carbon Roller",      ["cr"],   "Autobomb",   "Ink Storm",         7],
			["Carbon Roller Deco", ["crd"],  "Burst Bomb", "Autobomb Launcher", 10],

			["Clash Blaster",     ["cb", "trash blaster"],      "Splat Bomb",   "Stingray",       30],
			["Clash Blaster Neo", ["cbn", "trash blaster neo"], "Curling Bomb", "Tenta Missiles", 30],

			["Dapple Dualies",         ["dd", "red dapples"],               "Squid Beakon", "Suction Bomb Launcher", 26],
			["Dapple Dualies Nouveau", ["ddn", "blue dapples"],             "Toxic Mist",   "Ink Storm",             29],
			["Clear Dapple Dualies",   ["cdd", "clear dapples", "clappes"], "Torpedo",      "Splashdown",            30],

			["Dualie Squelchers",        ["ds", "squelchies"],         "Point Sensor", "Tenta Missiles", 12],
			["Custom Dualie Squelchers", ["cds", "custom squelchies"], "Splat Bomb",   "Ink Storm", 28],

			["Dynamo Roller",       ["dr"],  "Ink Mine",   "String Ray",  20],
			["Gold Dynamo Roller",  ["gdr"], "Splat Bomb", "Ink Armor",   25],
			["Kensa Dynamo Roller", ["kdr"], "Sprinkler",  "Booyah Bomb", 29],

			["E-liter 4K",              ["el", "el4k"],     "Ink Mine", "Ink Storm", 20],
			["E-liter 4K Scope",        ["els", "el4ks"],   "Ink Mine", "Ink Storm", 30],
			["Custom E-liter 4K",       ["cel", "cel4k"],   "Squid Beakon", "Bubble Blower", 26],
			["Custom E-liter 4K Scope", ["cels", "cel4ks"], "Squid Beakon", "Bubble Blower", 30],

			["Explosher",        ["xp"],  "Sprinkler",    "Bubble Blower", 18],
			["Custom Explosher", ["cxp"], "Point Sensor", "Baller",        22],

			["Flingza Roller",      ["fr"],  "Splash Wall",  "Splat Bomb Launcher", 24],
			["Foil Flingza Roller", ["ffr"], "Suction Bomb", "Tenta Missiles",      28],

			["Glooga Dualies",       ["gd", "ggd"],   "Ink Mine",    "Inkjet",    17],
			["Glooga Dualies Deco",  ["gdd", "ggdd"], "Splash Wall", "Baller",    24],
			["Kensa Glooga Dualies", ["kgd", "kggd"], "Fizzy Bomb",  "Ink Armor", 27],

			["Goo Tuber",        ["gt"],  "Suction Bomb", "Splashdown", 22],
			["Custom Goo Tuber", ["cgt"], "Curling Bomb", "Inkjet",     28],

			["Heavy Splatling",       ["hs"],  "Sprinkler",    "Sting Ray",     8],
			["Heavy Splatling Deco",  ["hsd"], "Splash Wall",  "Bubble Blower", 12],
			["Heavy Splatling Remix", ["hsr"], "Point Sensor", "Booyah Bomb",   19],

			["H-3 Nozzlenose",        ["h3"],  "Point Sensor", "Tenta Missiles", 29],
			["H-3 Nozzlenose D",      ["h3d"], "Suction Bomb", "Ink Armor",      30],
			["Cherry H-3 Nozzlenose", ["ch3"], "Splash Wall",  "Bubble Blower",  30],

			["Hydra Splatling",        ["hys"],            "Autobomb", "Splashdown", 27],
			["Custom Hydra Splatling", ["chys", "chydra"], "Ink Mine", "Ink Armor",  29],

			["Inkbrush",           ["ib"],  "Splat Bomb", "Splashdown", 5],
			["Inkbrush Nouveau",   ["ibn"], "Ink Mine",   "Baller",     7],
			["Permanent Inkbrush", ["pib"], "Sprinkler",  "Ink Armor",  12],

			["Jet Squelcher",        ["js"],  "Toxic Mist", "Tenta Missiles", 17],
			["Custom Jet Squelcher", ["cjs"], "Burst Bomb", "Sting Ray",      27],

			["L-3 Nozzlenose",       ["l3"],  "Curling Bomb", "Baller", 18],
			["L-3 Nozzlenose D",     ["l3d"], "Burst Bomb",   "Inkjet", 23],
			["Kensa L-3 Nozzlenose", ["kl3"], "Splash Wall",  "Ultra Stamp", 27],

			["Luna Blaster",       ["lb"],  "Splat Bomb", "Baller",                19],
			["Luna Blaster Neo",   ["lbn"], "Ink Mine",   "Suction Bomb Launcher", 24],
			["Kensa Luna Blaster", ["klb"], "Fizzy Bomb", "Ink Storm",             26],

			["Nautilus 47", ["n47"], "Point Sensor", "Baller", 26],
			["Nautilus 79", ["n79"], "Suction Bomb", "Inkjet", 30],

			["N-Zap 85", ["nz85"], "Suction Bomb", "Ink Armor",      9],
			["N-Zap 89", ["nz89"], "Autobomb",     "Tenta Missiles", 11],
			["N-Zap 83", ["nz83"], "Sprinkler",    "Ink Storm",      19],

			["Octobrush",         ["ob"],  "Autobomb",     "Inkjet",         10],
			["Octobrush Nouveau", ["obn"], "Squid Beakon", "Tenta Missiles", 15],
			["Kensa Octobrush",   ["kob"], "Suction Bomb", "Ultra Stamp",    20],

			["Mini Splatling",       ["ms"],          "Burst Bomb",   "Tenta Missiles", 23],
			["Zink Mini Splatling",  ["zms", "zini"], "Curling Bomb", "Ink Storm",      26],
			["Kensa Mini Splatling", ["kms", "kini"], "Toxic Mist",   "Ulta Stamp",     29],

			["Range Blaster",        ["rngb"],  "Suction Bomb", "Ink Storm",      14],
			["Custom Range Blaster", ["crngb"], "Curling Bomb", "Bubble Blower",  18],
			["Grim Range Blaster",   ["grngb"], "Burst Bomb",   "Tenta Missiles", 23],

			["Rapid Blaster",       ["rapb"],            "Ink Mine",     "Splat Bomb Launcher", 13],
			["Rapid Blaster Deco",  ["rapbd"],           "Suction Bomb", "Inkjet",              16],
			["Kensa Rapid Blaster", ["krapb", "krapid"], "Torpedo",      "Baller",              21],

			["Slosher",      ["slosh"],               "Suction Bomb", "Tenta Missiles",      5],
			["Slosher Deco", ["sloshd", "sloshdeco"], "Sprinkler",    "Baller",              8],
			["Soda Slosher", ["sslosh", "sodaslosh"], "Splat Bomb",   "Burst Bomb Launcher", 16],

			["Sloshing Machine",       ["sm", "sloshine"],                  "Autobomb",     "Sting Ray",           13],
			["Sloshing Machine Neo",   ["smn", "sloshine neo"],             "Point Sensor", "Splat Bomb Launcher", 19],
			["Kensa Sloshing Machine", ["ksm", "kslosh", "kensa sloshine"], "Fizzy Bomb",   "Splashdown",          21],

			["Splash-o-matic",     ["splasho"],               "Toxic Mist", "Inkjet",                25],
			["Neo Splash-o-matic", ["nsplasho", "neosplash"], "Burst Bomb", "Suction Bomb Launcher", 27],

			["Sploosh-o-matic",     ["sploosh", "sploosho"],   "Curling Bomb", "Splashdown",     10],
			["Neo Sploosh-o-matic", ["nsploosh", "nsploosho"], "Squid Beakon", "Tenta Missiles", 18],
			["Sploosh-o-matic 7",   ["sploosh7", "sploosho7"], "Splat Bomb",   "Ultra Stamp",    23],

			["Splat Charger",         ["sc"],          "Splat Bomb",  "Sting Ray",             3],
			["Firefin Splat Charger", ["fsc", "ffsc"], "Splash Wall", "Suction Bomb Launcher", 16],
			["Kensa Charger",         ["kc", "ksc"],   "Sprinkler",   "Baller",                19],

			["Splatterscope",         ["ssc"],                 "Splat Bomb",  "Sting Ray",             15],
			["Firefin Splatterscope", ["fssc", "fss", "ffss"], "Splash Wall", "Suction Bomb Launcher", 25],
			["Kensa Splatterscope",   ["kssc"],                "Sprinkler",   "Baller",                28],

			["Splat Brella",   ["sb"],  "Sprinkler", "Ink Storm",           9],
			["Sorella Brella", ["srb"], "Autobomb",  "Splat Bomb Launcher", 15],

			["Splat Dualies",         ["sd"],  "Burst Bomb",   "Tenta Missiles", 4],
			["Enperry Splat Dualies", ["esd"], "Curling Bomb", "Inkjet",         11],
			["Kensa Splat Dualies",   ["ksd"], "Suction Bomb", "Baller",         16],

			["Splat Roller",         ["sr"],   "Curling Bomb", "Splashdown",     3],
			["Krak-On Splat Roller", ["kosr"], "Squid Beakon", "Baller",         12],
			["Kensa Splat Roller",   ["ksr"],  "Splat Bomb",   "Bubbler Blower", 14],

			["Splattershot",          ["ss"],           "Burst Bomb",   "Splashdown",     2],
			["Tentatek Splattershot", ["ttss", "ttek"], "Splat Bomb",   "Inkjet",         4],
			["Kensa Splattershot",    ["kss"],          "Suction Bomb", "Tenta Missiles", 6],

			["Splattershot Jr",        ["ssj", "ssjr", ], "Splat Bomb", "Ink Armor",     1],
			["Custom Splattershot Jr", ["cssj", "cssjr"], "Autobomb",   "Ink Storm",     4],
			["Kensa Splattershot Jr",  ["kssj", "kssjr"], "Torpedo",    "Bubble Blower", 9],

			["Splattershot Pro",       ["ssp", "sspro"],           "Point Sensor", "Ink Storm",     10],
			["Forge Splattershot Pro", ["fssp", "fsspro"],         "Suction Bomb", "Bubble Blower", 20],
			["Kensa Splattershot Pro", ["kssp", "ksspro", "kpro"], "Splat Bomb",   "Booyah Bomb",   23],

			["Squeezer",      ["sq"],  "Splash Wall", "Sting Ray", 16],
			["Foil Squeezer", ["fsq"], "Splat Bomb",  "Bubble Blower", 25],

			["Classic Squiffer", ["csq"],  "Point Sensor", "Ink Armor", 12],
			["Fresh Squiffer",   ["frsq"], "Suction Bomb", "Inkjet",    24],
			["New Squiffer",     ["nsq"],  "Autobomb",     "Baller",    17],

			["Tenta Brella",         ["tb"],  "Squid Beakon", "Bubbler Blower",        23],
			["Tenta Camo Brella",    ["tcb"], "Ink Mine",     "Ultra Stamp",           28],
			["Tenta Sorella Brella", ["tsb"], "Splash Wall",  "Curling Bomb Launcher", 28],

			["Dark Tetra Dualies",  ["dtd"], "Autobomb",  "Splashdown",        14],
			["Light Tetra Dualies", ["ltd"], "Sprinkler", "Autobomb Launcher", 21],

			["Tri-Slosher",         ["ts"],  "Burst Bomb", "Ink Armor", 15],
			["Tri-Slosher Nouveau", ["tsn"], "Splat Bomb", "Ink Storm", 17],

			["Undercover Brella",         ["ub"],  "Ink Mine",   "Splashdown", 13],
			["Undercover Sorella Brella", ["usb"], "Splat Bomb", "Baller",     19],
			["Kensa Undercover Brella",   ["kub"], "Torpedo",    "Ink Armor",  24]
		]

		self.weapons = []
		for w in data:
			self.weapons.append(SplatWeapon(w[0], w[1], self.getSubweaponByName(w[2]), self.getSpecialByName(w[3]), w[4]))


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

	def getRandomItem(self, set):
		l = len(set)
		return set[random.randint(0, l - 1)]

	def getRandomMap(self):
		return self.getRandomItem(self.maps)

	def getRandomWeapon(self):
		return self.getRandomItem(self.weapons)



