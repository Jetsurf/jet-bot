import random

class SplatMatchItem():
	def __init__(self, name, abbrevs = []):
		self._name      = name
		self._abbrevs   = abbrevs

	def name(self):
		return self._name

	def abbrev(self):
		return self._abbrevs[0] if len(self._abbrevs) else None

	def abbrevs(self):
		return self._abbrevs

	def format(self):
		abbrev = self.abbrev()
		if abbrev:
			return "__" + self._name + "__ (**" + abbrev + "**)"
		else:
			return "__" + self._name + "__"

	def hasAbbrev(self, a):
		return a.lower() in self._abbrevs

class SplatStoreMerch(SplatMatchItem):
        def __init__(self, name, index, merchid):
                self._merchid = merchid

                super().__init__(name, [str(index)])

        def merchid(self):
                return self._merchid

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

class SplatWeaponType(SplatMatchItem):
	def __init__(self, name, pluralname, abbrevs):
		self._pluralname = pluralname

		super().__init__(name, abbrevs)

	def pluralname(self):
		return self._pluralname

class SplatWeapon(SplatMatchItem):
	def __init__(self, name, abbrevs, type, sub, special, specpts, level, id, dupid):
		self._type    = type
		self._sub     = sub
		self._special = special
		self.level    = level
		self.specpts  = specpts
		self._id      = id
		self._dupid   = dupid
		super().__init__(name, abbrevs)

	def sub(self):
		return self._sub

	def id(self):
		return self._id

	def type(self):
		return self._type

	def special(self):
		return self._special

	def sub(self):
		return self._sub

	def specpts(self):
		return self.specpts

	def level(self):
		return self.level

	# Exact duplicates will have a dupid pointing to the original weapon
	def dupid(self):
		return self._dupid

class SplatSlot(SplatMatchItem):
	pass

class SplatAbility(SplatMatchItem):
	def __init__(self, name, abbrevs, slot):
		self._slot = slot
		super().__init__(name, abbrevs)

	def slot(self):
		return self._slot


class SplatBrand(SplatMatchItem):
	def __init__(self, name, abbrevs, common, uncommon):
		self._common = common
		self._uncommon = uncommon
		super().__init__(name, abbrevs)

	def commonAbility(self):
		return self._common

	def uncommonAbility(self):
		return self._uncommon

class SplatGear(SplatMatchItem):
	def __init__(self, name, brand, slot, price, main, subcount, source):
		self._brand    = brand
		self._slot     = slot
		self._price    = price
		self._main     = main
		self._subcount = subcount
		self._source   = source
		super().__init__(name, None)

	def brand(self):
		return self._brand

	def slot(self):
		return self._slot

	def price(self):
		return self._price

	def mainAbility(self):
		return self._main

	def subCount(self):
		return self._subcount

	def source(self):
		return self._source

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

	def errorMessage(self, listhelp):
		l = len(self.items)
		if l == 0:
			msg = "I don't know of any " + self.type + " named '" + self.query + "'."
			if listhelp:
				msg += " " + listhelp
			return msg
		elif l == 1:
			return None
		elif l == 2:
			return "Did you mean " + self.items[0].format() + " or " + self.items[1].format() + "?"
		elif l < 8:
			str = "Did you mean " + ", ".join(map(lambda item: item.format(), self.items[0:l - 1]))
			str += ", or " + self.items[l - 1].format() + "?"
			return str

		msg = "What is '" + self.query + "'?"
		if listhelp:
			msg += " " + listhelp
		return msg


class SplatInfo():
	def __init__(self):
		self.initModes()
		self.initMaps()
		self.initSubweapons()
		self.initSpecials()
		self.initWeaponTypes()
		self.initWeapons()
		self.initSlots()
		self.initAbilities()
		self.initBrands()
		self.initGear()

		self.checkAbbrevs(self.modes)
		self.checkAbbrevs(self.maps)
		self.checkAbbrevs(self.subweapons)
		self.checkAbbrevs(self.specials)
		self.checkAbbrevs(self.weapontypes)
		self.checkAbbrevs(self.weapons)
		self.checkAbbrevs(self.slots)
		self.checkAbbrevs(self.abilities)
		self.checkAbbrevs(self.brands)

	def checkAbbrevs(self, set):
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
			SplatSubweapon("Autobomb",     ["ab", "aub", "chicken", "chickens"]),
			SplatSubweapon("Ink Mine",     ["im", "mines"]),
			SplatSubweapon("Toxic Mist",   ["tm", "fart"]),
			SplatSubweapon("Point Sensor", ["ps"]),
			SplatSubweapon("Splash Wall",  ["sw"]),
			SplatSubweapon("Sprinkler",    ["s"]),
			SplatSubweapon("Squid Beakon", ["sb", "beacon"]),
			SplatSubweapon("Fizzy Bomb",   ["fb", "fib", "soda"]),
			SplatSubweapon("Torpedo",      ["t"])
		]

	def initSpecials(self):
		self.specials = [
			SplatSpecial("Autobomb Launcher",     ["aubl", "chicken", "chickens"]),
			SplatSpecial("Burst Bomb Launcher",   ["bubl"]),
			SplatSpecial("Curling Bomb Launcher", ["cubl"]),
			SplatSpecial("Splat Bomb Launcher",   ["spbl", "triangle"]),
			SplatSpecial("Suction Bomb Launcher", ["subl", "suck", "succ"]),
			SplatSpecial("Baller",                ["b"]),
			SplatSpecial("Booyah Bomb",           ["byb", "spirit bomb"]),	# "bb" conflicts with Bubble Blower
			SplatSpecial("Bubble Blower",         ["bub", "bubbles"]),	# "bb" conflicts with Booyah Bomb
			SplatSpecial("Ink Armor",             ["ia", "armour", "ink armour"]),
			SplatSpecial("Ink Storm",             ["is", "rain"]),
			SplatSpecial("Inkjet",                ["ij", "jet", "jetpack"]),
			SplatSpecial("Splashdown",            ["sd", "splash"]),
			SplatSpecial("Sting Ray",             ["sr"]),
			SplatSpecial("Tenta Missiles",        ["tm"]),
			SplatSpecial("Ultra Stamp",           ["us", "hammer"]),
		]

	def initWeaponTypes(self):
		self.weapontypes = [
			SplatWeaponType("Shooter",   "Shooters",   ["s"]),
			SplatWeaponType("Blaster",   "Blasters",   ["bl"]),
			SplatWeaponType("Roller",    "Rollers",    ["r"]),
			SplatWeaponType("Charger",   "Chargers",   ["c", "sniper"]),
			SplatWeaponType("Slosher",   "Sloshers",   ["sl", "bucket"]),
			SplatWeaponType("Splatling", "Splatlings", ["sp", "gatling"]),
			SplatWeaponType("Dualies",   "Dualies",    ["d"]),
			SplatWeaponType("Brella",    "Brellas",    ["bre", "u", "umbrella", "brolly"]),
			SplatWeaponType("Brush",     "Brushes",    ["bru"]),
		]

	def initWeapons(self):
		data = [
			[".52 Gal",       ["52g"],  "Shooter", "Splat Bomb",   "Baller",		190,    14,	50],
			[".52 Gal Deco",  ["52gd"], "Shooter", "Curling Bomb", "Sting Ray",  	190,	22,	51],
			["Kensa .52 Gal", ["k52g"], "Shooter", "Splash Wall", "Booyah Bomb", 	180,	25,	52],

			[".96 Gal",      ["96g"],  "Shooter", "Sprinkler",    "Ink Armor", 	200,	21,	80],
			[".96 Gal Deco", ["96gd"], "Shooter", "Splash Wall",  "Splashdown",	190,	26,	81],

			["Aerospray MG", ["amg", "aeromg"], "Shooter", "Suction Bomb", "Curling Bomb Launcher",	160,	6, 	30],
			["Aerospray RG", ["arg", "aerorg"], "Shooter", "Sprinkler",    "Baller",                	170,	28,	31],
			["Aerospray PG", ["apg", "aeropg"], "Shooter", "Burst Bomb",   "Booyah Bomb",           	180,	29,	32],

			["Ballpoint Splatling",         ["bp", "bps"],   "Splatling",   "Toxic Mist",   "Inkjet",    200,	25, 4030],
			["Ballpoint Splatling Nouveau", ["bpn", "bpsn"], "Splatling", "Squid Beakon", "Ink Storm", 190,	28, 4031],

			["Bamboozler 14 Mk I",   ["bb1", "bamboo1", "boozler1"], "Charger", "Curling Bomb", "Tenta Missiles",      180,	18, 2050],
			["Bamboozler 14 Mk II",  ["bb2", "bamboo2", "boozler2"], "Charger", "Toxic Mist",   "Burst Bomb Launcher", 160,	21, 2051],
			["Bamboozler 14 Mk III", ["bb3", "bamboo3", "boozler3"], "Charger", "Fizzy Bomb",   "Bubble Blower",       190,	27, 2052],

			["Blaster",        ["b"],   "Blaster", "Toxic Mist", "Splashdown", 170,	5,  210],
			["Custom Blaster", ["cub"], "Blaster", "Autobomb",   "Inkjet",     180,	27, 211],

			["Bloblobber",      ["bl", "tub", "kwads tub"], "Slosher", "Splash Wall", "Ink Storm",             180,	11,	3030],
			["Bloblobber Deco", ["bld"],                    "Slosher", "Sprinkler",   "Suction Bomb Launcher", 180,	20,	3031],

			["Carbon Roller",      ["cr"],  "Roller", "Autobomb",   "Ink Storm",         160,	7,	1000],
			["Carbon Roller Deco", ["crd"], "Roller", "Burst Bomb", "Autobomb Launcher", 190,	10,	1001],

			["Clash Blaster",     ["cb", "trash blaster"],      "Blaster", "Splat Bomb",   "Sting Ray",       170,	30,	230],
			["Clash Blaster Neo", ["cbn", "trash blaster neo"], "Blaster", "Curling Bomb", "Tenta Missiles", 180,	30,	231],

			["Dapple Dualies",         ["dd", "red dapples"],               "Dualies", "Squid Beakon", "Suction Bomb Launcher", 180,	26,	5000],
			["Dapple Dualies Nouveau", ["ddn", "blue dapples"],             "Dualies", "Toxic Mist",   "Ink Storm",             170,	29,	5001],
			["Clear Dapple Dualies",   ["cdd", "clear dapples", "clappes"], "Dualies", "Torpedo",      "Splashdown",            170,	30,	5002],

			["Dualie Squelchers",        ["ds", "squelchies"],         "Dualies", "Point Sensor", "Tenta Missiles", 190,	12, 5030],
			["Custom Dualie Squelchers", ["cds", "custom squelchies"], "Dualies", "Splat Bomb",   "Ink Storm",      190,	28, 5031],

			["Dynamo Roller",       ["dr"],                           "Roller", "Ink Mine",   "Sting Ray",  180,	20,	1020],
			["Gold Dynamo Roller",  ["gdr"],                          "Roller", "Splat Bomb", "Ink Armor",   200,	25,	1021],
			["Kensa Dynamo Roller", ["kdr",  "buns wrecking roller"], "Roller", "Sprinkler",  "Booyah Bomb", 180,	29,	1022],

			["E-liter 4K",        ["el", "el4k"],   "Charger", "Ink Mine", "Ink Storm",         170,	20, 2030],
			["Custom E-liter 4K", ["cel", "cel4k"], "Charger", "Squid Beakon", "Bubble Blower", 180,	26, 2031],

			["E-liter 4K Scope",        ["els", "el4ks"],   "Charger", "Ink Mine",     "Ink Storm",     170,	30, 2040],
			["Custom E-liter 4K Scope", ["cels", "cel4ks"], "Charger", "Squid Beakon", "Bubble Blower", 180,	30, 2041],

			["Explosher",        ["xp"],  "Slosher", "Sprinkler",    "Bubble Blower", 190,	18,	3040],
			["Custom Explosher", ["cxp"], "Slosher", "Point Sensor", "Baller",        190,	22,	3041],

			["Flingza Roller",      ["fr"],  "Roller", "Splash Wall",  "Splat Bomb Launcher", 180,	24, 1030],
			["Foil Flingza Roller", ["ffr"], "Roller", "Suction Bomb", "Tenta Missiles",      180,	28, 1031],

			["Glooga Dualies",       ["gd", "ggd"],   "Dualies", "Ink Mine",    "Inkjet",    180,	17, 5020],
			["Glooga Dualies Deco",  ["gdd", "ggdd"], "Dualies", "Splash Wall", "Baller",    180,	24, 5021],
			["Kensa Glooga Dualies", ["kgd", "kggd"], "Dualies", "Fizzy Bomb",  "Ink Armor", 190,	27, 5022],

			["Goo Tuber",        ["gt"],  "Charger", "Suction Bomb", "Splashdown", 160,	22,	2060],
			["Custom Goo Tuber", ["cgt"], "Charger", "Curling Bomb", "Inkjet",     170,	28, 2061],

			["Heavy Splatling",       ["hs"],  "Splatling", "Sprinkler",    "Sting Ray",     180,	8,	4010],
			["Heavy Splatling Deco",  ["hsd"], "Splatling", "Splash Wall",  "Bubble Blower", 180,	12, 4011],
			["Heavy Splatling Remix", ["hsr"], "Splatling", "Point Sensor", "Booyah Bomb",   180,	19,	4012],

			["H-3 Nozzlenose",        ["h3"],  "Shooter", "Point Sensor", "Tenta Missiles", 180,	29, 310],
			["H-3 Nozzlenose D",      ["h3d"], "Shooter", "Suction Bomb", "Ink Armor",      190,	30, 311],
			["Cherry H-3 Nozzlenose", ["ch3"], "Shooter", "Splash Wall",  "Bubble Blower",  190,	30, 312],

			["Hydra Splatling",        ["hys", "hydra"],   "Splatling", "Autobomb", "Splashdown", 180,	27,	4020],
			["Custom Hydra Splatling", ["chys", "chydra"], "Splatling", "Ink Mine", "Ink Armor",  180,	29,	4021],

			["Inkbrush",           ["ib"],  "Brush", "Splat Bomb", "Splashdown", 160,	5,  1100],
			["Inkbrush Nouveau",   ["ibn"], "Brush", "Ink Mine",   "Baller",     180,	7,  1101],
			["Permanent Inkbrush", ["pib"], "Brush", "Sprinkler",  "Ink Armor",  180,	12, 1102],

			["Jet Squelcher",        ["js"],                          "Shooter", "Toxic Mist", "Tenta Missiles", 180, 17, 90],
			["Custom Jet Squelcher", ["cjs", "andys lemon squeezer"], "Shooter", "Burst Bomb", "Sting Ray",      180, 27, 91],

			["L-3 Nozzlenose",       ["l3"],  "Shooter", "Curling Bomb", "Baller",      180,	18, 300],
			["L-3 Nozzlenose D",     ["l3d"], "Shooter", "Burst Bomb",   "Inkjet",      180,	23, 301],
			["Kensa L-3 Nozzlenose", ["kl3"], "Shooter", "Splash Wall",  "Ultra Stamp", 180,	27, 302],

			["Luna Blaster",       ["lb"],  "Blaster", "Splat Bomb", "Baller",                180,	19, 200],
			["Luna Blaster Neo",   ["lbn"], "Blaster", "Ink Mine",   "Suction Bomb Launcher", 180,	24, 201],
			["Kensa Luna Blaster", ["klb"], "Blaster", "Fizzy Bomb", "Ink Storm",             180,	26, 202],

			["Nautilus 47", ["n47"], "Splatling", "Point Sensor", "Baller", 180,	26, 4040],
			["Nautilus 79", ["n79"], "Splatling", "Suction Bomb", "Inkjet", 180,	30, 4041],

			["N-Zap 85", ["nz85"], "Shooter", "Suction Bomb", "Ink Armor",      190,	9,  60],
			["N-Zap 89", ["nz89"], "Shooter", "Autobomb",     "Tenta Missiles", 190,	11, 61],
			["N-Zap 83", ["nz83"], "Shooter", "Sprinkler",    "Ink Storm",      180,	19, 62],

			["Octobrush",         ["ob", "weeb machine"],  "Brush", "Autobomb",     "Inkjet",         180,	10,	1110],
			["Octobrush Nouveau", ["obn"],                 "Brush", "Squid Beakon", "Tenta Missiles", 170,	15,	1111],
			["Kensa Octobrush",   ["kob"],                 "Brush", "Suction Bomb", "Ultra Stamp",    180,	20,	1112],

			["Mini Splatling",       ["ms"],          "Splatling", "Burst Bomb",   "Tenta Missiles", 180,	23, 4000],
			["Zink Mini Splatling",  ["zms", "zini"], "Splatling", "Curling Bomb", "Ink Storm",      200,	26, 4001],
			["Kensa Mini Splatling", ["kms", "kini"], "Splatling", "Toxic Mist",   "Ultra Stamp",     180,	29, 4002],

			["Range Blaster",        ["rngb"],  "Blaster", "Suction Bomb", "Ink Storm",      180,	14, 220],
			["Custom Range Blaster", ["crngb"], "Blaster", "Curling Bomb", "Bubble Blower",  180,	18, 221],
			["Grim Range Blaster",   ["grngb"], "Blaster", "Burst Bomb",   "Tenta Missiles", 190,	23, 222],

			["Rapid Blaster",       ["rapb"],            "Blaster", "Ink Mine",     "Splat Bomb Launcher", 210,	13,	240],
			["Rapid Blaster Deco",  ["rapbd"],           "Blaster", "Suction Bomb", "Inkjet",              180,	16,	241],
			["Kensa Rapid Blaster", ["krapb", "krapid"], "Blaster", "Torpedo",      "Baller",              200,	21,	242],

			["Rapid Blaster Pro",       ["rapbp"],  "Blaster", "Toxic Mist",     "Ink Storm",	180,	22,	250],
			["Rapid Blaster Pro Deco",  ["rapbpd"], "Blaster", "Splash Wall",	"Ink Armor",	180,	24,	251],

			["Slosher",      ["slosh"],               "Slosher", "Suction Bomb", "Tenta Missiles",      180,	5,  3000],
			["Slosher Deco", ["sloshd", "sloshdeco"], "Slosher", "Sprinkler",    "Baller",              190,	8,  3001],
			["Soda Slosher", ["sslosh", "sodaslosh"], "Slosher", "Splat Bomb",   "Burst Bomb Launcher", 200,	16, 3002],

			["Sloshing Machine",       ["sm", "sloshine"],                  "Slosher", "Autobomb",     "Sting Ray",           190,	13, 3020],
			["Sloshing Machine Neo",   ["smn", "sloshine neo"],             "Slosher", "Point Sensor", "Splat Bomb Launcher", 180,	19, 3021],
			["Kensa Sloshing Machine", ["ksm", "kslosh", "kensa sloshine"], "Slosher", "Fizzy Bomb",   "Splashdown",          170,	21, 3022],

			["Splash-o-matic",     ["splasho"],               "Shooter", "Toxic Mist", "Inkjet",                170,	25, 20],
			["Neo Splash-o-matic", ["nsplasho", "neosplash"], "Shooter", "Burst Bomb", "Suction Bomb Launcher", 200,	27, 21],

			["Sploosh-o-matic",     ["sploosh", "sploosho"],   "Shooter", "Curling Bomb", "Splashdown",     170,	10, 0],
			["Neo Sploosh-o-matic", ["nsploosh", "nsploosho"], "Shooter", "Squid Beakon", "Tenta Missiles", 170,	18, 1],
			["Sploosh-o-matic 7",   ["sploosh7", "sploosho7"], "Shooter", "Splat Bomb",   "Ultra Stamp",    180,	23, 2],

			["Splat Charger",         ["sc"],          "Charger", "Splat Bomb",  "Sting Ray",             210,	3,  2010],
			["Firefin Splat Charger", ["fsc", "ffsc"], "Charger", "Splash Wall", "Suction Bomb Launcher", 190,	16, 2011],
			["Kensa Charger",         ["kc", "ksc"],   "Charger", "Sprinkler",   "Baller",                190,	19, 2012],

			["Splatterscope",         ["ssc"],                 "Charger", "Splat Bomb",  "Sting Ray",             210,	15, 2020],
			["Firefin Splatterscope", ["fssc", "fss", "ffss"], "Charger", "Splash Wall", "Suction Bomb Launcher", 190,	25, 2021],
			["Kensa Splatterscope",   ["kssc"],                "Charger", "Sprinkler",   "Baller",                190,	28, 2022],

			["Splat Brella",   ["sb"],  "Brella", "Sprinkler", "Ink Storm",           180,	9,  6000],
			["Sorella Brella", ["srb"], "Brella", "Autobomb",  "Splat Bomb Launcher", 180,	15, 6001],

			["Splat Dualies",         ["sd"],  "Dualies", "Burst Bomb",   "Tenta Missiles", 180,	4,		5010],
			["Enperry Splat Dualies", ["esd"], "Dualies", "Curling Bomb", "Inkjet",         180,	11,	5011],
			["Kensa Splat Dualies",   ["ksd"], "Dualies", "Suction Bomb", "Baller",         210,	16,	5012],

			["Splat Roller",         ["sr"],   "Roller", "Curling Bomb", "Splashdown",     170,	3,		1010],
			["Krak-On Splat Roller", ["kosr"], "Roller", "Squid Beakon", "Baller",         180,	12,	1011],
			["Kensa Splat Roller",   ["ksr"],  "Roller", "Splat Bomb",   "Bubble Blower", 180,	14,	1012],

			["Splattershot",          ["ss"],           "Shooter", "Burst Bomb",   "Splashdown",     190,	2, 40],
			["Tentatek Splattershot", ["ttss", "ttek"], "Shooter", "Splat Bomb",   "Inkjet",         210,	4, 41],
			["Kensa Splattershot",    ["kss"],          "Shooter", "Suction Bomb", "Tenta Missiles", 180,	6, 42],

			["Splattershot Jr",        ["ssj", "ssjr", ], "Shooter", "Splat Bomb", "Ink Armor",     180,	1,	10],
			["Custom Splattershot Jr", ["cssj", "cssjr"], "Shooter", "Autobomb",   "Ink Storm",     190,	4,	11],
			["Kensa Splattershot Jr",  ["kssj", "kssjr"], "Shooter", "Torpedo",    "Bubble Blower", 200,	9,	12],

			["Splattershot Pro",       ["ssp", "sspro"],           "Shooter", "Point Sensor", "Ink Storm",     170,	10,	70],
			["Forge Splattershot Pro", ["fssp", "fsspro"],         "Shooter", "Suction Bomb", "Bubble Blower", 180,	20,	71],
			["Kensa Splattershot Pro", ["kssp", "ksspro", "kpro"], "Shooter", "Splat Bomb",   "Booyah Bomb",   180,	23,	72],

			["Squeezer",      ["sq"],  "Shooter", "Splash Wall", "Sting Ray",     180,	16, 400],
			["Foil Squeezer", ["fsq"], "Shooter", "Splat Bomb",  "Bubble Blower", 180,	25, 401],

			["Classic Squiffer", ["csq"],  "Charger", "Point Sensor", "Ink Armor", 180,	12, 2000],
			["New Squiffer",     ["nsq"],  "Charger", "Autobomb",     "Baller",    180,	17,	2001],
			["Fresh Squiffer",   ["frsq"], "Charger", "Suction Bomb", "Inkjet",    190,	24, 2002],

			["Tenta Brella",         ["tb"],  "Brella", "Squid Beakon", "Bubble Blower",        180,	23, 6010],
			["Tenta Sorella Brella", ["tsb"], "Brella", "Splash Wall",  "Curling Bomb Launcher", 180,	28, 6011],
			["Tenta Camo Brella",    ["tcb"], "Brella", "Ink Mine",     "Ultra Stamp",           190,	28, 6012],

			["Dark Tetra Dualies",  ["dtd"], "Dualies", "Autobomb",  "Splashdown",        170,	14,	5040],
			["Light Tetra Dualies", ["ltd"], "Dualies", "Sprinkler", "Autobomb Launcher", 200,	21,	5041],

			["Tri-Slosher",         ["ts", "bucket", "jets beer"],  "Slosher", "Burst Bomb", "Ink Armor", 210,	15,	3010],
			["Tri-Slosher Nouveau", ["tsn"],                        "Slosher", "Splat Bomb", "Ink Storm", 180,	17,	3011],

			["Undercover Brella",         ["ub"],  "Brella", "Ink Mine",   "Splashdown", 160,	13,	6020],
			["Undercover Sorella Brella", ["usb"], "Brella", "Splat Bomb", "Baller",     180,	19,	6021],
			["Kensa Undercover Brella",   ["kub"], "Brella", "Torpedo",    "Ink Armor",  180,	24,	6022],

			# === Duplicate weapons
			["Hero Blaster Replica",   ["herob", "heroblaster"],     "Blaster",   "Toxic Mist",   "Splashdown",     170,	5,  215,  210],
			["Hero Brella Replica",    ["herosb", "herobrella"],     "Brella",    "Sprinkler",    "Ink Storm",      180,	9,  6005, 6000],
			["Hero Charger Replica",   ["herosc", "herocharger"],    "Charger",   "Splat Bomb",   "Sting Ray",      210,	3,  2015, 2010],
			["Hero Dualie Replicas",   ["herosd", "herodualies"],    "Dualies",   "Burst Bomb",   "Tenta Missiles", 180,	4,  5015, 5010],
			["Hero Roller Replica",    ["herosr", "heroroller"],     "Roller",    "Curling Bomb", "Splashdown",     170,	3,  1015, 1010],
			["Hero Shot Replica",      ["heross", "heroshot"],       "Shooter",   "Burst Bomb",   "Splashdown",     190,	2,  45,   40],
			["Hero Slosher Replica",   ["heroslosh", "heroslosher"], "Slosher",   "Suction Bomb", "Tenta Missiles", 180,	5,  3005, 3000],
			["Hero Splatling Replica", ["herohs", "herosplatling"],  "Splatling", "Sprinkler",    "Sting Ray",      180,	8,  4015, 4010],
			["Herobrush Replica",      ["heroib", "herobrush"],      "Brush",     "Autobomb",     "Inkjet",         180,	10, 1115, 1100],
			["Octo Shot Replica",      ["octoss", "octoshot"],       "Shooter",   "Splat Bomb",   "Inkjet",         210,	1,  46,   41]
		]

		self.weapons = []
		for w in data:
			name    = w[0]
			abbrevs = w[1]
			type    = w[2]
			sub     = w[3]
			special = w[4]
			specpts = w[5]
			level   = w[6]
			id      = w[7]
			dupid   = w[8] if (len(w) >= 9) else None
			self.weapons.append(SplatWeapon(name, abbrevs, self.getWeaponTypeByName(type), self.getSubweaponByName(sub), self.getSpecialByName(special), specpts, level, id, dupid))

	def initSlots(self):
		self.slots = [
			SplatSlot("Headgear", ["hat"]),
			SplatSlot("Clothing", ["shirt", "clothes"]),
			SplatSlot("Footwear", ["feet", "shoe", "shoes"]),
		]

	def initAbilities(self):
		data = [
			# Headgear-only
			["Comeback",           ["cb"],        "Headgear"],
			["Last-Ditch Effort",  ["lde"],       "Headgear"],
			["Opening Gambit",     ["og"],        "Headgear"],
			["Tenacity",           ["tcy", "10"], "Headgear"],

			# Clothing-only
			["Ability Doubler",    ["ad", "2x"],  "Clothing"],
			["Haunt",              ["h"],         "Clothing"],
			["Ninja Squid",        ["ns"],        "Clothing"],
			["Respawn Punisher",   ["rp"],        "Clothing"],
			["Thermal Ink",        ["ti"],        "Clothing"],

			# Footwear-only
			["Drop Roller",        ["dr"],        "Footwear"],
			["Object Shredder",    ["os"],        "Footwear"],
			["Stealth Jump",       ["sj"],        "Footwear"],

			# Any slot
			["Bomb Defense Up DX", ["bdu", "dx"],              None],
			["Ink Recovery Up",    ["irec"],                   None],
			["Ink Resistance Up",  ["ires"],                   None],
			["Ink Saver (Main)",   ["ism", "ink saver main"],  None],
			["Ink Saver (Sub)",    ["iss", "ink saver sub"],   None],
			["Main Power Up",      ["mpu", "main"],            None],
			["Quick Respawn",      ["qr"],                     None],
			["Quick Super Jump",   ["qsj", "quick superjump"], None],
			["Run Speed Up",       ["rsu"],                    None],
			["Special Charge Up",  ["scu"],                    None],
			["Special Power Up",   ["spu"],                    None],
			["Special Saver",      ["ss"],                     None],
			["Sub Power Up",       ["sub", "sub up"],          None],
			["Swim Speed Up",      ["ssu"],                    None]
		]

		self.abilities = []
		for a in data:
			name    = a[0]
			abbrevs = a[1]
			slot    = a[2]
			self.abilities.append(SplatAbility(name, abbrevs, self.getSlotByName(slot)))

	def initBrands(self):
		data = [
			["amiibo",     [],                    None,                 None],
			["Annaki",     ["a"],                 "Main Power Up",      "Special Saver"],
			["Cuttlegear", ["cg"],                None,                 None],
			["Enperry",    ["ep"],                "Sub Power Up",       "Ink Resistance Up"],
			["Firefin",    ["ff"],                "Ink Saver (Sub)",    "Ink Recovery Up"],
			["Forge",      ["f"],                 "Special Power Up",   "Ink Saver (Sub)"],
			["Grizzco",    [],                    None,                 None],
			["Inkline",    ["il"],                "Bomb Defense Up DX", "Main Power Up"],
			["Krak-On",    ["ko", "krakon"],      "Swim Speed Up",      "Bomb Defense Up DX"],
			["Rockenberg", ["r"],                 "Run Speed Up",       "Swim Speed Up"],
			["Skalop",     ["s"],                 "Quick Respawn",      "Special Saver"],
			["Splash Mob", ["sm"],                "Ink Saver (Main)",   "Run Speed Up"],
			["SquidForce", ["sf", "squid force"], "Ink Resistance Up",  "Ink Saver (Main)"],
			["Takoroka",   ["tr"],                "Special Charge Up",  "Special Power Up"],
			["Tentatek",   ["tt", "ttek"],        "Ink Recovery Up",    "Quick Super Jump"],
			["Toni Kensa", ["tk", "tony kensa"],  "Main Power Up",      "Sub Power Up"],
			["Zekko",      ["zo"],                "Special Saver",      "Special Charge Up"],
			["Zink",       ["z", "zk"],           "Quick Super Jump",   "Quick Respawn"]
		]

		self.brands = []
		for b in data:
			name     = b[0]
			abbrevs  = b[1]
			common   = b[2] and self.getAbilityByName(b[2])
			uncommon = b[3] and self.getAbilityByName(b[3])
			self.brands.append(SplatBrand(name, abbrevs, common, uncommon))

	def initGear(self):
		data = [
			# Headgear
			[ "18K Aviators" , "Rockenberg" , "Headgear" , 12000 , "Last-Ditch Effort" , 3 , None ],
			[ "Anglerfish Mask" , "SquidForce" , "Headgear" , 0 , "Ink Saver (Main)" , 3 , "Splatoween" ],
			[ "Annaki Beret" , "Annaki" , "Headgear" , 11500 , "Ink Resistance Up" , 3 , None ],
			[ "Annaki Beret & Glasses" , "Annaki" , "Headgear" , 7850 , "Ink Saver (Main)" , 3 , None ],
			[ "Annaki Mask" , "Annaki" , "Headgear" , 3600 , "Opening Gambit" , 2 , None ],
			[ "Armor Helmet Replica" , "Cuttlegear" , "Headgear" , 0 , "Tenacity" , 2 , "Marie" ],
			[ "Backwards Cap" , "Zekko" , "Headgear" , 700 , "Quick Respawn" , 1 , None ],
			[ "Bamboo Hat" , "Inkline" , "Headgear" , 2200 , "Ink Saver (Main)" , 2 , None ],
			[ "B-ball Headband" , "Zink" , "Headgear" , 300 , "Opening Gambit" , 1 , None ],
			[ "Beekeeper Hat" , "Grizzco" , "Headgear" , 0 , None , 3 , "Salmon Run" ],
			[ "Bike Helmet" , "Skalop" , "Headgear" , 4800 , "Ink Recovery Up" , 2 , None ],
			[ "Black Arrowbands" , "Zekko" , "Headgear" , 2800 , "Tenacity" , 2 , None ],
			[ "Black FishFry Bandana" , "Firefin" , "Headgear" , 1250 , "Bomb Defense Up DX" , 1 , None ],
			[ "Blowfish Bell Hat" , "Firefin" , "Headgear" , 850 , "Ink Recovery Up" , 1 , None ],
			[ "Blowfish Newsie" , "Firefin" , "Headgear" , 4200 , "Quick Super Jump" , 2 , None ],
			[ "Bobble Hat" , "Splash Mob" , "Headgear" , 2000 , "Quick Super Jump" , 2 , None ],
			[ "Bucket Hat" , "SquidForce" , "Headgear" , 400 , "Special Saver" , 1 , None ],
			[ "Camo Mesh" , "Firefin" , "Headgear" , 1400 , "Swim Speed Up" , 1 , None ],
			[ "Camping Hat" , "Inkline" , "Headgear" , 800 , "Special Power Up" , 1 , None ],
			[ "Cap of Legend" , "Grizzco" , "Headgear" , 0 , None , 3 , "Salmon Run" ],
			[ "Classic Straw Boater" , "Skalop" , "Headgear" , 1500 , "Special Power Up" , 2 , None ],
			[ "Conductor Cap" , "Cuttlegear" , "Headgear" , 0 , "Sub Power Up" , 2 , "Octo Expansion" ],
			[ "Cycle King Cap" , "Tentatek" , "Headgear" , 2400 , "Bomb Defense Up DX" , 2 , None ],
			[ "Cycling Cap" , "Zink" , "Headgear" , 800 , "Sub Power Up" , 1 , None ],
			[ "Deca Tackle Visor Helmet" , "Forge" , "Headgear" , 10100 , "Sub Power Up" , 3 , None ],
			[ "Designer Headphones" , "Forge" , "Headgear" , 2500 , "Ink Saver (Sub)" , 2 , None ],
			[ "Digi-Camo Forge Mask" , "Forge" , "Headgear" , 1800 , "Swim Speed Up" , 2 , None ],
			[ "Do-Rag, Cap, & Glasses" , "Skalop" , "Headgear" , 9500 , "Main Power Up" , 3 , None ],
			[ "Double Egg Shades" , "Zekko" , "Headgear" , 2200 , "Run Speed Up" , 2 , None ],
			[ "Dust Blocker 2000" , "Grizzco" , "Headgear" , 0 , None , 3 , "Salmon Run" ],
			[ "Eel-Cake Hat" , "SquidForce" , "Headgear" , 0 , "Quick Respawn" , 3 , "FrostyFest" ],
			[ "Eminence Cuff" , "Enperry" , "Headgear" , 0 , "Ink Saver (Main)" , 3 , "CoroCoro" ],
			[ "Eye of Justice" , "SquidForce" , "Headgear" , 0 , "Special Charge Up" , 3 , "FinalFest" ],
			[ "Face Visor" , "Toni Kensa" , "Headgear" , 10300 , "Bomb Defense Up DX" , 3 , None ],
			[ "Fake Contacts" , "Tentatek" , "Headgear" , 2000 , "Special Charge Up" , 2 , None ],
			[ "Festive Party Cone" , "SquidForce" , "Headgear" , 0 , "Main Power Up" , 3 , "FrostyFest" ],
			[ "Fierce Fishskull" , "SquidForce" , "Headgear" , 0 , "Swim Speed Up" , 3 , "FinalFest" ],
			[ "Firefin Facemask" , "Firefin" , "Headgear" , 650 , "Run Speed Up" , 1 , None ],
			[ "FishFry Biscuit Bandana" , "Firefin" , "Headgear" , 1250 , "Special Power Up" , 1 , None ],
			[ "FishFry Visor" , "Firefin" , "Headgear" , 500 , "Special Charge Up" , 1 , None ],
			[ "Five-Panel Cap" , "Zekko" , "Headgear" , 1800 , "Comeback" , 2 , None ],
			[ "Forge Mask" , "Forge" , "Headgear" , 1400 , "Main Power Up" , 1 , None ],
			[ "Fugu Bell Hat" , "Firefin" , "Headgear" , 1700 , "Quick Respawn" , 2 , None ],
			[ "Full Moon Glasses" , "Krak-On" , "Headgear" , 600 , "Quick Super Jump" , 1 , None ],
			[ "Gas Mask" , "Forge" , "Headgear" , 11000 , "Tenacity" , 3 , None ],
			[ "Golden Toothpick" , "Cuttlegear" , "Headgear" , 0 , "Special Charge Up" , 3 , "Octo Expansion" ],
			[ "Green Novelty Visor" , "Tentatek" , "Headgear" , 0 , "Special Saver" , 3 , "SpringFest" ],
			[ "Golf Visor" , "Zink" , "Headgear" , 400 , "Run Speed Up" , 1 , None ],
			[ "Half-Rim Glasses" , "Splash Mob" , "Headgear" , 4100 , "Special Power Up" , 2 , None ],
			[ "Headlamp Helmet" , "Grizzco" , "Headgear" , 0 , None , 3 , "Salmon Run" ],
			[ "Hero Headphones Replica" , "Cuttlegear" , "Headgear" , 0 , "Special Saver" , 2 , "Octo Canyon" ],
			[ "Hero Headset Replica" , "Cuttlegear" , "Headgear" , 0 , "Run Speed Up" , 2 , "Callie" ],
			[ "Hickory Work Cap" , "Krak-On" , "Headgear" , 8700 , "Special Power Up" , 3 , None ],
			[ "Hivemind Antenna" , "SquidForce" , "Headgear" , 0 , "Comeback" , 3 , "FinalFest" ],
			[ "Hockey Helmet" , "Forge" , "Headgear" , 9900 , "Main Power Up" , 3 , None ],
			[ "Hockey Mask" , "SquidForce" , "Headgear" , 0 , "Ink Recovery Up" , 3 , "Splatoween" ],
			[ "Hothouse Hat" , "Skalop" , "Headgear" , 3680 , "Ink Resistance Up" , 2 , None ],
			[ "House-Tag Denim Cap" , "Splash Mob" , "Headgear" , 5200 , "Special Charge Up" , 2 , None ],
			[ "Ink-Guard Goggles" , "Toni Kensa" , "Headgear" , 9600 , "Run Speed Up" , 3 , None ],
			[ "Jellyvader Cap" , "Skalop" , "Headgear" , 10000 , "Ink Saver (Sub)" , 3 , None ],
			[ "Jetflame Crest" , "SquidForce" , "Headgear" , 0 , "Run Speed Up" , 3 , "FinalFest" ],
			[ "Jet Cap" , "Firefin" , "Headgear" , 700 , "Special Saver" , 1 , None ],
			[ "Jogging Headband" , "Zekko" , "Headgear" , 400 , "Ink Saver (Sub)" , 1 , None ],
			[ "Jungle Hat" , "Firefin" , "Headgear" , 9000 , "Ink Saver (Main)" , 3 , None ],
			[ "King Facemask" , "Enperry" , "Headgear" , 500 , "Ink Saver (Sub)" , 1 , None ],
			[ "King Flip Mesh" , "Enperry" , "Headgear" , 3200 , "Run Speed Up" , 2 , None ],
			[ "Knitted Hat" , "Firefin" , "Headgear" , 1400 , "Ink Resistance Up" , 1 , None ],
			[ "Kyonshi Hat" , "SquidForce" , "Headgear" , 0 , "Run Speed Up" , 3 , "Splatoween" ],
			[ "Lightweight Cap" , "Inkline" , "Headgear" , 800 , "Swim Speed Up" , 1 , None ],
			[ "Li'l Devil Horns" , "SquidForce" , "Headgear" , 0 , "Ink Saver (Sub)" , 3 , "Splatoween" ],
			[ "Long-Billed Cap" , "Krak-On" , "Headgear" , 9800 , "Ink Recovery Up" , 3 , None ],
			[ "Marinated Headphones" , "amiibo" , "Headgear" , 0 , "Special Saver" , 2 , "Marina" ],
			[ "Matte Bike Helmet" , "Zekko" , "Headgear" , 10000 , "Sub Power Up" , 3 , None ],
			[ "Moist Ghillie Helmet" , "Forge" , "Headgear" , 8500 , "Run Speed Up" , 3 , None ],
			[ "Motocross Nose Guard" , "Forge" , "Headgear" , 7600 , "Special Charge Up" , 3 , None ],
			[ "Mountie Hat" , "Inkline" , "Headgear" , 13000 , "Special Charge Up" , 3 , None ],
			[ "MTB Helmet" , "Zekko" , "Headgear" , 10500 , "Tenacity" , 3 , None ],
			[ "New Year's Glasses DX" , "SquidForce" , "Headgear" , 0 , "Special Charge Up" , 3 , "FrostyFest" ],
			[ "Noise Cancelers" , "Forge" , "Headgear" , 9200 , "Quick Respawn" , 3 , None ],
			[ "Null Visor Replica" , "Cuttlegear" , "Headgear" , 0 , "Special Power Up" , 2 , "Octo Expansion" ],
			[ "Oceanic Hard Hat" , "Grizzco" , "Headgear" , 0 , None , 3 , "Salmon Run" ],
			[ "Octo Tackle Helmet Deco" , "Forge" , "Headgear" , 8888 , "Bomb Defense Up DX" , 3 , None ],
			[ "Octoglasses" , "Firefin" , "Headgear" , 8800 , "Last-Ditch Effort" , 3 , None ],
			[ "Octoking Facemask" , "Enperry" , "Headgear" , 1450 , "Tenacity" , 1 , None ],
			[ "Octoleet Goggles" , "Grizzco" , "Headgear" , 0 , None , 3 , "Salmon Run" ],
			[ "Octoling Shades" , "Cuttlegear" , "Headgear" , 0 , "Last-Ditch Effort" , 2 , "Octo Expansion" ],
			[ "Old-Timey Hat" , "Cuttlegear" , "Headgear" , 0 , "Comeback" , 2 , "Octo Expansion" ],
			[ "Orange Novelty Visor" , "Tentatek" , "Headgear" , 0 , "Last-Ditch Effort" , 3 , "SpringFest" ],
			[ "Paintball Mask" , "Forge" , "Headgear" , 10000 , "Comeback" , 3 , None ],
			[ "Painter's Mask" , "SquidForce" , "Headgear" , 4500 , "Main Power Up" , 2 , None ],
			[ "Paisley Bandana" , "Krak-On" , "Headgear" , 750 , "Ink Saver (Sub)" , 1 , None ],
			[ "Patched Hat" , "Skalop" , "Headgear" , 3600 , "Main Power Up" , 2 , None ],
			[ "Pearlescent Crown" , "amiibo" , "Headgear" , 0 , "Bomb Defense Up DX" , 2 , "Pearl" ],
			[ "Pilot Goggles" , "Forge" , "Headgear" , 5500 , "Sub Power Up" , 2 , None ],
			[ "Pilot Hat" , "Splash Mob" , "Headgear" , 11500 , "Ink Resistance Up" , 3 , None ],
			[ "Pink Novelty Visor" , "Tentatek" , "Headgear" , 0 , "Tenacity" , 3 , "SpringFest" ],
			[ "Power Mask" , "amiibo" , "Headgear" , 0 , "Bomb Defense Up DX" , 2 , "Inkling Squid" ],
			[ "Power Mask Mk I" , "amiibo" , "Headgear" , 0 , "Ink Resistance Up" , 2 , "Inkling Squid" ],
			[ "Purple Novelty Visor" , "Tentatek" , "Headgear" , 0 , "Ink Resistance Up" , 3 , "SpringFest" ],
			[ "Retro Specs" , "Splash Mob" , "Headgear" , 500 , "Quick Respawn" , 1 , None ],
			[ "Safari Hat" , "Forge" , "Headgear" , 2300 , "Last-Ditch Effort" , 2 , None ],
			[ "Sailor Cap" , "Grizzco" , "Headgear" , 0 , None , 3 , "Salmon Run" ],
			[ "Samurai Helmet" , "amiibo" , "Headgear" , 0 , "Quick Super Jump" , 2 , "Inkling Boy" ],
			[ "Seashell Bamboo Hat" , "Inkline" , "Headgear" , 3200 , "Quick Respawn" , 2 , None ],
			[ "Sennyu Bon Bon Beanie" , "Splash Mob" , "Headgear" , 0 , "Ink Saver (Sub)" , 3 , "CoroCoro" ],
			[ "Sennyu Goggles" , "Forge" , "Headgear" , 0 , "Ink Resistance Up" , 3 , "CoroCoro" ],
			[ "Sennyu Headphones" , "Forge" , "Headgear" , 0 , "Ink Saver (Main)" , 3 , "CoroCoro" ],
			[ "Sennyu Specs" , "Splash Mob" , "Headgear" , 0 , "Swim Speed Up" , 3 , "CoroCoro" ],
			[ "Short Beanie" , "Inkline" , "Headgear" , 600 , "Ink Saver (Main)" , 1 , None ],
			[ "Skate Helmet" , "Skalop" , "Headgear" , 2500 , "Special Saver" , 2 , None ],
			[ "Skull Bandana" , "Forge" , "Headgear" , 7800 , "Special Saver" , 3 , None ],
			[ "Sneaky Beanie" , "Skalop" , "Headgear" , 3000 , "Swim Speed Up" , 2 , None ],
			[ "Snorkel Mask" , "Forge" , "Headgear" , 3000 , "Ink Saver (Sub)" , 2 , None ],
			[ "Soccer Headband" , "Tentatek" , "Headgear" , 3000 , "Tenacity" , 2 , None ],
			[ "Special Forces Beret" , "Forge" , "Headgear" , 9700 , "Opening Gambit" , 3 , None ],
			[ "Splash Goggles" , "Forge" , "Headgear" , 2800 , "Bomb Defense Up DX" , 2 , None ],
			[ "Sporty Bobble Hat" , "Skalop" , "Headgear" , 800 , "Tenacity" , 1 , None ],
			[ "Squash Headband" , "Zink" , "Headgear" , 400 , "Special Saver" , 1 , None ],
			[ "Squid Clip-Ons" , "amiibo" , "Headgear" , 0 , "Opening Gambit" , 2 , "Inkling Girl" ],
			[ "Squid Facemask" , "SquidForce" , "Headgear" , 300 , "Ink Saver (Main)" , 1 , None ],
			[ "Squid Hairclip" , "amiibo" , "Headgear" , 0 , "Swim Speed Up" , 2 , "Inkling Girl" ],
			[ "Squid Nordic" , "Skalop" , "Headgear" , 9500 , "Comeback" , 3 , None ],
			[ "Squidfin Hook Cans" , "Forge" , "Headgear" , 3800 , "Ink Resistance Up" , 2 , None ],
			[ "Squidlife Headphones" , "Forge" , "Headgear" , 7070 , "Ink Recovery Up" , 3 , None ],
			[ "Squid-Stitch Cap" , "Skalop" , "Headgear" , 8500 , "Opening Gambit" , 3 , None ],
			[ "Squidvader Cap" , "Skalop" , "Headgear" , 1300 , "Special Charge Up" , 1 , None ],
			[ "Squinja Mask" , "amiibo" , "Headgear" , 0 , "Quick Respawn" , 2 , "Inkling Boy" ],
			[ "Stealth Goggles" , "Forge" , "Headgear" , 9800 , "Swim Speed Up" , 3 , None ],
			[ "Straw Boater" , "Skalop" , "Headgear" , 550 , "Quick Super Jump" , 1 , None ],
			[ "Streetstyle Cap" , "Skalop" , "Headgear" , 600 , "Ink Saver (Sub)" , 1 , None ],
			[ "Striped Beanie" , "Splash Mob" , "Headgear" , 900 , "Opening Gambit" , 1 , None ],
			[ "Studio Headphones" , "Forge" , "Headgear" , 2800 , "Ink Saver (Main)" , 2 , None ],
			[ "Studio Octophones" , "Cuttlegear" , "Headgear" , 0 , "Ink Recovery Up" , 3 , "Octo Expansion" ],
			[ "Sun Visor" , "Tentatek" , "Headgear" , 2600 , "Sub Power Up" , 2 , None ],
			[ "SV925 Circle Shades" , "Rockenberg" , "Headgear" , 11000 , "Swim Speed Up" , 3 , None ],
			[ "Swim Goggles" , "Zink" , "Headgear" , 100 , "Last-Ditch Effort" , 1 , None ],
			[ "Takoroka Mesh" , "Takoroka" , "Headgear" , 400 , "Bomb Defense Up DX" , 1 , None ],
			[ "Takoroka Visor" , "Takoroka" , "Headgear" , 7500 , "Quick Super Jump" , 3 , None ],
			[ "Tennis Headband" , "Tentatek" , "Headgear" , 300 , "Comeback" , 1 , None ],
			[ "Tinted Shades" , "Zekko" , "Headgear" , 350 , "Last-Ditch Effort" , 1 , None ],
			[ "Toni Kensa Goggles" , "Toni Kensa" , "Headgear" , 200 , "Comeback" , 1 , None ],
			[ "Treasure Hunter" , "Forge" , "Headgear" , 3000 , "Ink Recovery Up" , 2 , None ],
			[ "Tulip Parasol" , "Inkline" , "Headgear" , 1280 , "Ink Resistance Up" , 1 , None ],
			[ "Twisty Headband" , "SquidForce" , "Headgear" , 0 , "Special Power Up" , 3 , "FrostyFest" ],
			[ "Two-Stripe Mesh" , "Krak-On" , "Headgear" , 700 , "Special Saver" , 1 , None ],
			[ "Urchins Cap" , "Skalop" , "Headgear" , 600 , "Sub Power Up" , 1 , None ],
			[ "Visor Skate Helmet" , "Skalop" , "Headgear" , 8000 , "Last-Ditch Effort" , 3 , None ],
			[ "Welding Mask" , "Grizzco" , "Headgear" , 0 , None , 3 , "Salmon Run" ],
			[ "White Arrowbands" , "Zekko" , "Headgear" , 8000 , "Special Power Up" , 3 , None ],
			[ "White Headband" , "SquidForce" , "Headgear" , 0 , "Ink Recovery Up" , 1 , "Starter Item" ],
			[ "Woolly Urchins Classic" , "Krak-On" , "Headgear" , 3800 , "Comeback" , 2 , None ],
			[ "Worker's Cap" , "Grizzco" , "Headgear" , 0 , None , 3 , "Salmon Run" ],
			[ "Worker's Head Towel" , "Grizzco" , "Headgear" , 0 , None , 3 , "Salmon Run" ],
			[ "Yamagiri Beanie" , "Inkline" , "Headgear" , 1280 , "Main Power Up" , 1 , None ],
			[ "Zekko Cap" , "Zekko" , "Headgear" , 2700 , "Opening Gambit" , 2 , None ],
			[ "Zekko Mesh" , "Zekko" , "Headgear" , 500 , "Quick Super Jump" , 1 , None ],

			# Clothing
			[ "Aloha Shirt" , "Forge" , "Clothing" , 700 , "Ink Recovery Up" , 1 , None ],
			[ "Anchor Life Vest" , "Grizzco" , "Clothing" , 0 , None , 3 , "Salmon Run" ],
			[ "Anchor Sweat" , "SquidForce" , "Clothing" , 2800 , "Main Power Up" , 2 , None ],
			[ "Annaki Blue Cuff" , "Annaki" , "Clothing" , 4800 , "Special Saver" , 2 , None ],
			[ "Annaki Drive Tee" , "Annaki" , "Clothing" , 5500 , "Thermal Ink" , 2 , None ],
			[ "Annaki Evolution Tee" , "Annaki" , "Clothing" , 8800 , "Respawn Punisher" , 3 , None ],
			[ "Annaki Flannel Hoodie" , "Annaki" , "Clothing" , 9999 , "Bomb Defense Up DX" , 3 , None ],
			[ "Annaki Polpo-Pic Tee" , "Annaki" , "Clothing" , 6660 , "Run Speed Up" , 3 , None ],
			[ "Annaki Red Cuff" , "Annaki" , "Clothing" , 4800 , "Haunt" , 2 , None ],
			[ "Annaki Yellow Cuff" , "Annaki" , "Clothing" , 4800 , "Quick Respawn" , 2 , None ],
			[ "Armor Jacket Replica" , "Cuttlegear" , "Clothing" , 0 , "Special Charge Up" , 2 , "Marie" ],
			[ "Baby-Jelly Shirt" , "Splash Mob" , "Clothing" , 1350 , "Bomb Defense Up DX" , 1 , None ],
			[ "Baby-Jelly Shirt & Tie" , "Splash Mob" , "Clothing" , 3800 , "Main Power Up" , 2 , None ],
			[ "Baseball Jersey" , "Firefin" , "Clothing" , 10000 , "Special Charge Up" , 3 , None ],
			[ "Basic Tee" , "SquidForce" , "Clothing" , 0 , "Quick Respawn" , 1 , "Starter Item" ],
			[ "B-ball Jersey (Away)" , "Zink" , "Clothing" , 800 , "Ink Saver (Sub)" , 1 , None ],
			[ "B-ball Jersey (Home)" , "Zink" , "Clothing" , 2300 , "Special Saver" , 2 , None ],
			[ "Berry Ski Jacket" , "Inkline" , "Clothing" , 3900 , "Special Power Up" , 2 , None ],
			[ "Birded Corduroy Jacket" , "Zekko" , "Clothing" , 10400 , "Run Speed Up" , 3 , None ],
			[ "Black 8-Bit FishFry" , "Firefin" , "Clothing" , 600 , "Bomb Defense Up DX" , 1 , None ],
			[ "Black Anchor Tee" , "SquidForce" , "Clothing" , 2800 , "Respawn Punisher" , 2 , None ],
			[ "Black Baseball LS" , "Rockenberg" , "Clothing" , 800 , "Swim Speed Up" , 1 , None ],
			[ "Black Cuttlegear LS" , "Cuttlegear" , "Clothing" , 5800 , "Swim Speed Up" , 2 , None ],
			[ "Black Hoodie" , "Skalop" , "Clothing" , 2900 , "Ink Resistance Up" , 2 , None ],
			[ "Black Inky Rider" , "Rockenberg" , "Clothing" , 12100 , "Sub Power Up" , 3 , None ],
			[ "Black Layered LS" , "SquidForce" , "Clothing" , 500 , "Ink Saver (Main)" , 1 , None ],
			[ "Black LS" , "Zekko" , "Clothing" , 3000 , "Quick Super Jump" , 2 , None ],
			[ "Black Polo" , "Zekko" , "Clothing" , 500 , "Ninja Squid" , 1 , None ],
			[ "Black Squideye" , "Tentatek" , "Clothing" , 500 , "Run Speed Up" , 1 , None ],
			[ "Black Tee" , "SquidForce" , "Clothing" , 400 , "Special Power Up" , 1 , None ],
			[ "Black Urchin Rock Tee" , "Rockenberg" , "Clothing" , 850 , "Ink Recovery Up" , 1 , None ],
			[ "Black Velour Octoking Tee" , "Enperry" , "Clothing" , 2950 , "Main Power Up" , 2 , None ],
			[ "Black V-Neck Tee" , "SquidForce" , "Clothing" , 3800 , "Thermal Ink" , 2 , None ],
			[ "Blue 16-Bit FishFry" , "Firefin" , "Clothing" , 3750 , "Special Saver" , 2 , None ],
			[ "Blue Peaks Tee" , "Inkline" , "Clothing" , 400 , "Ink Saver (Sub)" , 1 , None ],
			[ "Blue Sailor Suit" , "Forge" , "Clothing" , 11000 , "Sub Power Up" , 3 , None ],
			[ "Blue Tentatek Tee" , "Tentatek" , "Clothing" , 3100 , "Quick Respawn" , 2 , None ],
			[ "Brown FA-11 Bomber" , "Forge" , "Clothing" , 7/11 , "Bomb Defense Up DX" , 2 , None ],
			[ "Camo Layered LS" , "SquidForce" , "Clothing" , 600 , "Special Charge Up" , 1 , None ],
			[ "Camo Zip Hoodie" , "Firefin" , "Clothing" , 9000 , "Quick Respawn" , 3 , None ],
			[ "Carnivore Tee" , "Firefin" , "Clothing" , 500 , "Bomb Defense Up DX" , 1 , None ],
			[ "Chili Octo Aloha" , "Krak-On" , "Clothing" , 4850 , "Bomb Defense Up DX" , 2 , None ],
			[ "Chili-Pepper Ski Jacket" , "Inkline" , "Clothing" , 7800 , "Ink Resistance Up" , 3 , None ],
			[ "Chilly Mountain Coat" , "Inkline" , "Clothing" , 7900 , "Swim Speed Up" , 3 , None ],
			[ "Chirpy Chips Band Tee" , "Rockenberg" , "Clothing" , 900 , "Main Power Up" , 1 , None ],
			[ "Choco Layered LS" , "Takoroka" , "Clothing" , 1400 , "Ink Saver (Sub)" , 1 , None ],
			[ "Crimson Parashooter" , "Annaki" , "Clothing" , 9200 , "Special Charge Up" , 3 , None ],
			[ "Crustwear XXL" , "Grizzco" , "Clothing" , 0 , None , 3 , "Salmon Run" ],
			[ "Custom Painted F-3" , "Forge" , "Clothing" , 9700 , "Ink Resistance Up" , 3 , None ],
			[ "Cycle King Jersey" , "Tentatek" , "Clothing" , 8900 , "Bomb Defense Up DX" , 3 , None ],
			[ "Cycling Shirt" , "Zink" , "Clothing" , 2900 , "Main Power Up" , 2 , None ],
			[ "Dakro Golden Tee" , "Zink" , "Clothing" , 1010 , "Thermal Ink" , 1 , None ],
			[ "Dakro Nana Tee" , "Zink" , "Clothing" , 1010 , "Quick Respawn" , 1 , None ],
			[ "Dark Bomber Jacket" , "Toni Kensa" , "Clothing" , 12800 , "Special Power Up" , 3 , None ],
			[ "Dark Urban Vest" , "Firefin" , "Clothing" , 10000 , "Main Power Up" , 3 , None ],
			[ "Deep-Octo Satin Jacket" , "Zekko" , "Clothing" , 12300 , "Main Power Up" , 3 , None ],
			[ "Dev Uniform" , "Grizzco" , "Clothing" , 0 , None , 3 , "Salmon Run" ],
			[ "Dots-On-Dots Shirt" , "Skalop" , "Clothing" , 7650 , "Quick Super Jump" , 3 , None ],
			[ "Eggplant Mountain Coat" , "Inkline" , "Clothing" , 7600 , "Special Saver" , 3 , None ],
			[ "FA-01 Jacket" , "Forge" , "Clothing" , 10100 , "Ink Recovery Up" , 3 , None ],
			[ "FA-01 Reversed" , "Forge" , "Clothing" , 10100 , "Quick Super Jump" , 3 , None ],
			[ "FC Albacore" , "Takoroka" , "Clothing" , 1200 , "Respawn Punisher" , 1 , None ],
			[ "Firefin Navy Sweat" , "Firefin" , "Clothing" , 2500 , "Sub Power Up" , 2 , None ],
			[ "Firewave Tee" , "Skalop" , "Clothing" , 1250 , "Special Charge Up" , 1 , None ],
			[ "Fishing Vest" , "Inkline" , "Clothing" , 4200 , "Quick Respawn" , 2 , None ],
			[ "Forest Vest" , "Inkline" , "Clothing" , 11000 , "Ink Recovery Up" , 3 , None ],
			[ "Forge Inkling Parka" , "Forge" , "Clothing" , 2900 , "Run Speed Up" , 2 , None ],
			[ "Forge Octarian Jacket" , "Forge" , "Clothing" , 2700 , "Haunt" , 2 , None ],
			[ "Fresh Octo Tee" , "Cuttlegear" , "Clothing" , 0 , "Ink Saver (Sub)" , 1 , "Octo Expansion" ],
			[ "Friend Tee" , "SquidForce" , "Clothing" , 1200 , "Thermal Ink" , 1 , None ],
			[ "Front Zip Vest" , "Toni Kensa" , "Clothing" , 5500 , "Ink Resistance Up" , 2 , None ],
			[ "Fugu Tee" , "Firefin" , "Clothing" , 750 , "Swim Speed Up" , 1 , None ],
			[ "Garden Gear" , "Grizzco" , "Clothing" , 0 , None , 3 , "Salmon Run" ],
			[ "Grape Hoodie" , "Enperry" , "Clothing" , 1100 , "Quick Respawn" , 1 , None ],
			[ "Grape Tee" , "Skalop" , "Clothing" , 400 , "Ink Recovery Up" , 1 , None ],
			[ "Gray 8-Bit FishFry" , "Firefin" , "Clothing" , 800 , "Special Charge Up" , 1 , None ],
			[ "Gray College Sweat" , "Splash Mob" , "Clothing" , 800 , "Swim Speed Up" , 1 , None ],
			[ "Gray FA-11 Bomber" , "Forge" , "Clothing" , 7/11 , "Main Power Up" , 2 , None ],
			[ "Gray Hoodie" , "Skalop" , "Clothing" , 1900 , "Sub Power Up" , 2 , None ],
			[ "Gray Mixed Shirt" , "Zekko" , "Clothing" , 2800 , "Quick Super Jump" , 2 , None ],
			[ "Gray Vector Tee" , "Takoroka" , "Clothing" , 500 , "Quick Super Jump" , 1 , None ],
			[ "Green Cardigan" , "Splash Mob" , "Clothing" , 1700 , "Ink Saver (Sub)" , 2 , None ],
			[ "Green Striped LS" , "Inkline" , "Clothing" , 700 , "Ninja Squid" , 1 , None ],
			[ "Green Tee" , "Forge" , "Clothing" , 1200 , "Special Saver" , 1 , None ],
			[ "Green Velour Octoking Tee" , "Enperry" , "Clothing" , 1450 , "Special Saver" , 1 , None ],
			[ "Green V-Neck Limited Tee" , "SquidForce" , "Clothing" , 7/11 , "Quick Super Jump" , 2 , None ],
			[ "Green Zip Hoodie" , "Firefin" , "Clothing" , 2800 , "Special Power Up" , 2 , None ],
			[ "Green-Check Shirt" , "Zekko" , "Clothing" , 2000 , "Sub Power Up" , 2 , None ],
			[ "Half-Sleeve Sweater" , "Toni Kensa" , "Clothing" , 4100 , "Ink Saver (Sub)" , 2 , None ],
			[ "Herbivore Tee" , "Firefin" , "Clothing" , 500 , "Ninja Squid" , 1 , None ],
			[ "Hero Hoodie Replica" , "Cuttlegear" , "Clothing" , 0 , "Ink Recovery Up" , 2 , "Octo Canyon" ],
			[ "Hero Jacket Replica" , "Cuttlegear" , "Clothing" , 0 , "Swim Speed Up" , 2 , "Callie" ],
			[ "Hightide Era Band Tee" , "Rockenberg" , "Clothing" , 900 , "Thermal Ink" , 1 , None ],
			[ "Hothouse Hoodie" , "Skalop" , "Clothing" , 3800 , "Run Speed Up" , 2 , None ],
			[ "Hula Punk Shirt" , "Annaki" , "Clothing" , 5000 , "Ink Saver (Main)" , 2 , None ],
			[ "Icewave Tee" , "Skalop" , "Clothing" , 1250 , "Ninja Squid" , 1 , None ],
			[ "Inkfall Shirt" , "Toni Kensa" , "Clothing" , 4900 , "Special Charge Up" , 2 , None ],
			[ "Inkopolis Squaps Jersey" , "Zink" , "Clothing" , 1250 , "Main Power Up" , 1 , None ],
			[ "Ink-Wash Shirt" , "Toni Kensa" , "Clothing" , 4900 , "Ink Recovery Up" , 2 , None ],
			[ "Ivory Peaks Tee" , "Inkline" , "Clothing" , 400 , "Haunt" , 1 , None ],
			[ "Juice Parka" , "Grizzco" , "Clothing" , 0 , None , 3 , "Salmon Run" ],
			[ "Kensa Coat" , "Toni Kensa" , "Clothing" , 12800 , "Respawn Punisher" , 3 , None ],
			[ "Khaki 16-Bit FishFry" , "Firefin" , "Clothing" , 3750 , "Ink Recovery Up" , 2 , None ],
			[ "King Jersey" , "Enperry" , "Clothing" , 3100 , "Respawn Punisher" , 2 , None ],
			[ "Krak-On 528" , "Krak-On" , "Clothing" , 800 , "Run Speed Up" , 1 , None ],
			[ "Kung-Fu Zip-Up" , "Toni Kensa" , "Clothing" , 10280 , "Ninja Squid" , 3 , None ],
			[ "Layered Anchor LS" , "SquidForce" , "Clothing" , 4000 , "Run Speed Up" , 2 , None ],
			[ "Layered Vector LS" , "Takoroka" , "Clothing" , 1200 , "Special Saver" , 1 , None ],
			[ "League Tee" , "SquidForce" , "Clothing" , 3800 , "Special Power Up" , 2 , None ],
			[ "Light Bomber Jacket" , "Toni Kensa" , "Clothing" , 12800 , "Quick Super Jump" , 3 , None ],
			[ "Lime Easy-Stripe Shirt" , "Splash Mob" , "Clothing" , 3800 , "Ink Resistance Up" , 2 , None ],
			[ "Linen Shirt" , "Splash Mob" , "Clothing" , 700 , "Sub Power Up" , 1 , None ],
			[ "Lob-Stars Jersey" , "Tentatek" , "Clothing" , 4650 , "Sub Power Up" , 2 , None ],
			[ "Logo Aloha Shirt" , "Zekko" , "Clothing" , 2900 , "Ink Recovery Up" , 2 , None ],
			[ "Lumberjack Shirt" , "Rockenberg" , "Clothing" , 800 , "Ink Saver (Main)" , 1 , None ],
			[ "Marinated Top" , "amiibo" , "Clothing" , 0 , "Special Power Up" , 2 , "Marina" ],
			[ "Matcha Down Jacket" , "Inkline" , "Clothing" , 9100 , "Ninja Squid" , 3 , None ],
			[ "Milky Eminence Jacket" , "Enperry" , "Clothing" , 0 , "Run Speed Up" , 3 , "CoroCoro" ],
			[ "Mint Tee" , "Skalop" , "Clothing" , 400 , "Bomb Defense Up DX" , 1 , None ],
			[ "Missus Shrug Tee" , "Krak-On" , "Clothing" , 9200 , "Ink Saver (Sub)" , 3 , None ],
			[ "Mister Shrug Tee" , "Krak-On" , "Clothing" , 9200 , "Ink Resistance Up" , 3 , None ],
			[ "Moist Ghillie Suit" , "Forge" , "Clothing" , 8500 , "Ink Saver (Sub)" , 3 , None ],
			[ "Mountain Vest" , "Inkline" , "Clothing" , 11000 , "Swim Speed Up" , 3 , None ],
			[ "Navy College Sweat" , "Splash Mob" , "Clothing" , 800 , "Ink Resistance Up" , 1 , None ],
			[ "Navy Deca Logo Tee" , "Zink" , "Clothing" , 1200 , "Ink Saver (Main)" , 1 , None ],
			[ "Navy Eminence Jacket" , "Enperry" , "Clothing" , 10500 , "Ink Saver (Main)" , 3 , None ],
			[ "Navy King Tank" , "Enperry" , "Clothing" , 600 , "Ink Resistance Up" , 1 , None ],
			[ "Navy Striped LS" , "Splash Mob" , "Clothing" , 1050 , "Ink Recovery Up" , 1 , None ],
			[ "Negative Longcuff Sweater" , "Toni Kensa" , "Clothing" , 11800 , "Haunt" , 3 , None ],
			[ "Neo Octoling Armor" , "Cuttlegear" , "Clothing" , 0 , "Haunt" , 2 , "Octo Expansion" ],
			[ "North-Country Parka" , "Grizzco" , "Clothing" , 0 , None , 3 , "Salmon Run" ],
			[ "N-Pacer Sweat" , "Enperry" , "Clothing" , 7800 , "Thermal Ink" , 3 , None ],
			[ "Null Armor Replica" , "Cuttlegear" , "Clothing" , 0 , "Ink Resistance Up" , 2 , "Octo Expansion" ],
			[ "Octarian Retro" , "Cuttlegear" , "Clothing" , 5000 , "Respawn Punisher" , 2 , None ],
			[ "Octo Layered LS" , "Cuttlegear" , "Clothing" , 0 , "Ink Saver (Main)" , 3 , "Octo Expansion" ],
			[ "Octo Tee" , "Cuttlegear" , "Clothing" , 8888 , "Haunt" , 3 , None ],
			[ "Octobowler Shirt" , "Krak-On" , "Clothing" , 2100 , "Ink Saver (Main)" , 2 , None ],
			[ "Octoking HK Jersey" , "Enperry" , "Clothing" , 5800 , "Special Charge Up" , 2 , None ],
			[ "Office Attire" , "Grizzco" , "Clothing" , 0 , None , 3 , "Salmon Run" ],
			[ "Old-Timey Clothes" , "Cuttlegear" , "Clothing" , 0 , "Thermal Ink" , 2 , "Octo Expansion" ],
			[ "Olive Ski Jacket" , "Inkline" , "Clothing" , 11000 , "Run Speed Up" , 3 , None ],
			[ "Olive Zekko Parka" , "Zekko" , "Clothing" , 3800 , "Swim Speed Up" , 2 , None ],
			[ "Online Jersey" , "Grizzco" , "Clothing" , 0 , "Swim Speed Up" , 3 , "Nintendo Online Subscription" ],
			[ "Orange Cardigan" , "Splash Mob" , "Clothing" , 700 , "Special Charge Up" , 1 , None ],
			[ "Panda Kung-Fu Zip-Up" , "Toni Kensa" , "Clothing" , 10280 , "Sub Power Up" , 3 , None ],
			[ "Part-Time Pirate" , "Tentatek" , "Clothing" , 800 , "Respawn Punisher" , 1 , None ],
			[ "Pearl Tee" , "Skalop" , "Clothing" , 400 , "Ink Saver (Sub)" , 1 , None ],
			[ "Pearlescent Hoodie" , "amiibo" , "Clothing" , 0 , "Respawn Punisher" , 2 , "Pearl" ],
			[ "Pink Easy-Stripe Shirt" , "Splash Mob" , "Clothing" , 3800 , "Quick Super Jump" , 2 , None ],
			[ "Pink Hoodie" , "Splash Mob" , "Clothing" , 3400 , "Bomb Defense Up DX" , 2 , None ],
			[ "Pirate-Stripe Tee" , "Splash Mob" , "Clothing" , 700 , "Special Power Up" , 1 , None ],
			[ "Positive Longcuff Sweater" , "Toni Kensa" , "Clothing" , 10800 , "Swim Speed Up" , 3 , None ],
			[ "Power Armor" , "amiibo" , "Clothing" , 0 , "Quick Respawn" , 2 , "Inkling Squid" ],
			[ "Power Armor Mk I" , "amiibo" , "Clothing" , 0 , "Ink Resistance Up" , 2 , "Inkling Squid" ],
			[ "Prune Parashooter" , "Annaki" , "Clothing" , 7800 , "Ninja Squid" , 3 , None ],
			[ "Pullover Coat" , "Toni Kensa" , "Clothing" , 13200 , "Thermal Ink" , 3 , None ],
			[ "Purple Camo LS" , "Takoroka" , "Clothing" , 600 , "Sub Power Up" , 1 , None ],
			[ "Rainy-Day Tee" , "Krak-On" , "Clothing" , 300 , "Ink Saver (Main)" , 1 , None ],
			[ "Record Shop Look EP" , "Grizzco" , "Clothing" , 0 , None , 3 , "Salmon Run" ],
			[ "Red Cuttlegear LS" , "Cuttlegear" , "Clothing" , 5800 , "Bomb Defense Up DX" , 2 , None ],
			[ "Red Hula Punk with Tie" , "Annaki" , "Clothing" , 9000 , "Ink Resistance Up" , 3 , None ],
			[ "Red Tentatek Tee" , "Tentatek" , "Clothing" , 3100 , "Swim Speed Up" , 2 , None ],
			[ "Red Vector Tee" , "Takoroka" , "Clothing" , 500 , "Ink Saver (Main)" , 1 , None ],
			[ "Red V-Neck Limited Tee" , "SquidForce" , "Clothing" , 7/11 , "Quick Respawn" , 2 , None ],
			[ "Red-Check Shirt" , "Zekko" , "Clothing" , 2000 , "Ink Saver (Main)" , 2 , None ],
			[ "Reel Sweat" , "Zekko" , "Clothing" , 900 , "Special Power Up" , 1 , None ],
			[ "Reggae Tee" , "Skalop" , "Clothing" , 8200 , "Special Saver" , 3 , None ],
			[ "Retro Gamer Jersey" , "Zink" , "Clothing" , 9000 , "Quick Respawn" , 3 , None ],
			[ "Retro Sweat" , "SquidForce" , "Clothing" , 9000 , "Bomb Defense Up DX" , 3 , None ],
			[ "Rockenberg Black" , "Rockenberg" , "Clothing" , 800 , "Respawn Punisher" , 1 , None ],
			[ "Rockenberg White" , "Rockenberg" , "Clothing" , 2500 , "Ink Recovery Up" , 2 , None ],
			[ "Rockin' Leather Jacket" , "Annaki" , "Clothing" , 10666 , "Sub Power Up" , 3 , None ],
			[ "Rodeo Shirt" , "Krak-On" , "Clothing" , 750 , "Quick Super Jump" , 1 , None ],
			[ "Round-Collar Shirt" , "Rockenberg" , "Clothing" , 1600 , "Ink Saver (Sub)" , 2 , None ],
			[ "Sage Polo" , "Splash Mob" , "Clothing" , 400 , "Main Power Up" , 1 , None ],
			[ "Sailor-Stripe Tee" , "Splash Mob" , "Clothing" , 700 , "Run Speed Up" , 1 , None ],
			[ "Samurai Jacket" , "amiibo" , "Clothing" , 0 , "Special Charge Up" , 2 , "Inkling Boy" ],
			[ "School Cardigan" , "amiibo" , "Clothing" , 0 , "Run Speed Up" , 2 , "Inkling Girl" ],
			[ "School Jersey" , "Zink" , "Clothing" , 3000 , "Ninja Squid" , 2 , None ],
			[ "School Uniform" , "amiibo" , "Clothing" , 0 , "Ink Recovery Up" , 2 , "Inkling Girl" ],
			[ "Sennyu Suit" , "Cuttlegear" , "Clothing" , 0 , "Ninja Squid" , 3 , "CoroCoro" ],
			[ "Shirt & Tie" , "Splash Mob" , "Clothing" , 8400 , "Special Saver" , 3 , None ],
			[ "Shirt with Blue Hoodie" , "Splash Mob" , "Clothing" , 2900 , "Special Power Up" , 2 , None ],
			[ "Short Knit Layers" , "Toni Kensa" , "Clothing" , 9850 , "Ink Saver (Main)" , 3 , None ],
			[ "Shrimp-Pink Polo" , "Splash Mob" , "Clothing" , 550 , "Ninja Squid" , 1 , None ],
			[ "Silver Tentatek Vest" , "Tentatek" , "Clothing" , 6200 , "Thermal Ink" , 2 , None ],
			[ "Sky-Blue Squideye" , "Tentatek" , "Clothing" , 500 , "Main Power Up" , 1 , None ],
			[ "Slash King Tank" , "Enperry" , "Clothing" , 450 , "Thermal Ink" , 1 , None ],
			[ "Slipstream United" , "Takoroka" , "Clothing" , 1800 , "Bomb Defense Up DX" , 2 , None ],
			[ "Splatfest Tee Replica" , "SquidForce" , "Clothing" , 0 , "Ability Doubler" , 3 , "Splatfest" ],
			[ "Squid Satin Jacket" , "Zekko" , "Clothing" , 9200 , "Quick Respawn" , 3 , None ],
			[ "Squid Squad Band Tee" , "Rockenberg" , "Clothing" , 900 , "Ink Resistance Up" , 1 , None ],
			[ "Squid Yellow Layered LS" , "SquidForce" , "Clothing" , 4010 , "Swim Speed Up" , 2 , None ],
			[ "Squiddor Polo" , "Grizzco" , "Clothing" , 0 , None , 3 , "Salmon Run" ],
			[ "Squidmark LS" , "SquidForce" , "Clothing" , 600 , "Haunt" , 1 , None ],
			[ "Squidmark Sweat" , "SquidForce" , "Clothing" , 800 , "Sub Power Up" , 1 , None ],
			[ "Squid-Pattern Waistcoat" , "Krak-On" , "Clothing" , 800 , "Special Power Up" , 1 , None ],
			[ "Squidstar Waistcoat" , "Krak-On" , "Clothing" , 650 , "Main Power Up" , 1 , None ],
			[ "Squid-Stitch Tee" , "Skalop" , "Clothing" , 400 , "Swim Speed Up" , 1 , None ],
			[ "Squinja Suit" , "amiibo" , "Clothing" , 0 , "Special Saver" , 2 , "Inkling Boy" ],
			[ "SRL Coat" , "Grizzco" , "Clothing" , 0 , None , 3 , "Salmon Run" ],
			[ "Striped Peaks LS" , "Inkline" , "Clothing" , 700 , "Quick Super Jump" , 1 , None ],
			[ "Striped Rugby" , "Takoroka" , "Clothing" , 2300 , "Run Speed Up" , 2 , None ],
			[ "Striped Shirt" , "Splash Mob" , "Clothing" , 2200 , "Quick Super Jump" , 2 , None ],
			[ "Sunny-Day Tee" , "Krak-On" , "Clothing" , 300 , "Special Charge Up" , 1 , None ],
			[ "SWC Logo Tee" , "SquidForce" , "Clothing" , 0 , "Swim Speed Up" , 3 , "SWC" ],
			[ "Takoroka Crazy Baseball LS" , "Takoroka" , "Clothing" , 4200 , "Ninja Squid" , 2 , None ],
			[ "Takoroka Galactic Tie Dye" , "Takoroka" , "Clothing" , 850 , "Thermal Ink" , 1 , None ],
			[ "Takoroka Jersey" , "Takoroka" , "Clothing" , 8960 , "Special Power Up" , 3 , None ],
			[ "Takoroka Nylon Vintage" , "Takoroka" , "Clothing" , 9500 , "Thermal Ink" , 3 , None ],
			[ "Takoroka Rainbow Tie Dye" , "Takoroka" , "Clothing" , 850 , "Quick Super Jump" , 1 , None ],
			[ "Takoroka Windcrusher" , "Takoroka" , "Clothing" , 8500 , "Main Power Up" , 3 , None ],
			[ "Tentatek Slogan Tee" , "Tentatek" , "Clothing" , 1600 , "Special Charge Up" , 2 , None ],
			[ "Toni K. Baseball Jersey" , "Toni Kensa" , "Clothing" , 9650 , "Special Charge Up" , 3 , None ],
			[ "Tricolor Rugby" , "Takoroka" , "Clothing" , 700 , "Quick Respawn" , 1 , None ],
			[ "Tumeric Zekko Coat" , "Zekko" , "Clothing" , 4600 , "Thermal Ink" , 2 , None ],
			[ "Urchins Jersey" , "Zink" , "Clothing" , 700 , "Run Speed Up" , 1 , None ],
			[ "Varsity Baseball LS" , "Splash Mob" , "Clothing" , 700 , "Haunt" , 1 , None ],
			[ "Varsity Jacket" , "Zekko" , "Clothing" , 11500 , "Ink Saver (Sub)" , 3 , None ],
			[ "Vintage Check Shirt" , "Rockenberg" , "Clothing" , 9000 , "Haunt" , 3 , None ],
			[ "Wet Floor Band Tee" , "Rockenberg" , "Clothing" , 900 , "Swim Speed Up" , 1 , None ],
			[ "Whale-Knit Sweater" , "Splash Mob" , "Clothing" , 9650 , "Run Speed Up" , 3 , None ],
			[ "White 8-Bit FishFry" , "Firefin" , "Clothing" , 800 , "Sub Power Up" , 1 , None ],
			[ "White Anchor Tee" , "SquidForce" , "Clothing" , 2800 , "Ninja Squid" , 2 , None ],
			[ "White Baseball LS" , "Rockenberg" , "Clothing" , 800 , "Quick Super Jump" , 1 , None ],
			[ "White Deca Logo Tee" , "Zink" , "Clothing" , 1200 , "Ink Resistance Up" , 1 , None ],
			[ "White Inky Rider" , "Rockenberg" , "Clothing" , 12800 , "Special Power Up" , 3 , None ],
			[ "White King Tank" , "Enperry" , "Clothing" , 600 , "Haunt" , 1 , None ],
			[ "White Layered LS" , "SquidForce" , "Clothing" , 500 , "Special Saver" , 1 , None ],
			[ "White Leather F-3" , "Forge" , "Clothing" , 8900 , "Respawn Punisher" , 3 , None ],
			[ "White LS" , "SquidForce" , "Clothing" , 600 , "Ink Recovery Up" , 1 , None ],
			[ "White Sailor Suit" , "Forge" , "Clothing" , 3000 , "Ink Saver (Main)" , 2 , None ],
			[ "White Shirt" , "Splash Mob" , "Clothing" , 7500 , "Ink Recovery Up" , 3 , None ],
			[ "White Striped LS" , "Splash Mob" , "Clothing" , 2300 , "Quick Respawn" , 2 , None ],
			[ "White Tee" , "SquidForce" , "Clothing" , 400 , "Ink Saver (Sub)" , 1 , None ],
			[ "White Urchin Rock Tee" , "Rockenberg" , "Clothing" , 850 , "Ink Saver (Main)" , 1 , None ],
			[ "White V-Neck Tee" , "SquidForce" , "Clothing" , 3800 , "Special Saver" , 2 , None ],
			[ "Yellow Layered LS" , "SquidForce" , "Clothing" , 500 , "Quick Super Jump" , 1 , None ],
			[ "Yellow Urban Vest" , "Firefin" , "Clothing" , 4100 , "Haunt" , 2 , None ],
			[ "Zapfish Satin Jacket" , "Zekko" , "Clothing" , 2900 , "Special Charge Up" , 2 , None ],
			[ "Zekko Baseball LS" , "Zekko" , "Clothing" , 800 , "Bomb Defense Up DX" , 1 , None ],
			[ "Zekko Hoodie" , "Zekko" , "Clothing" , 2800 , "Ninja Squid" , 2 , None ],
			[ "Zekko Jade Coat" , "Zekko" , "Clothing" , 3600 , "Respawn Punisher" , 2 , None ],
			[ "Zekko Long Carrot Tee" , "Zekko" , "Clothing" , 1800 , "Ink Resistance Up" , 2 , None ],
			[ "Zekko Long Radish Tee" , "Zekko" , "Clothing" , 1450 , "Haunt" , 1 , None ],
			[ "Zekko Redleaf Coat" , "Zekko" , "Clothing" , 2600 , "Haunt" , 2 , None ],
			[ "Zink Layered LS" , "Zink" , "Clothing" , 600 , "Respawn Punisher" , 1 , None ],
			[ "Zink LS" , "Zink" , "Clothing" , 500 , "Special Power Up" , 1 , None ],
			[ "ω-3 Tee" , "Firefin" , "Clothing" , 1200 , "Respawn Punisher" , 1 , None ],

			# Footwear
			[ "Acerola Rain Boots" , "Inkline" , "Footwear" , 600 , "Run Speed Up" , 1 , None ],
			[ "Amber Sea Slug Hi-Tops" , "Tentatek" , "Footwear" , 11000 , "Drop Roller" , 3 , None ],
			[ "Angry Rain Boots" , "Grizzco" , "Footwear" , 0 , None , 3 , "Salmon Run" ],
			[ "Annaki Arachno Boots" , "Annaki" , "Footwear" , 9696 , "Swim Speed Up" , 3 , None ],
			[ "Annaki Habaneros" , "Annaki" , "Footwear" , 8800 , "Sub Power Up" , 3 , None ],
			[ "Annaki Tigers" , "Annaki" , "Footwear" , 9990 , "Special Power Up" , 3 , None ],
			[ "Armor Boot Replicas" , "Cuttlegear" , "Footwear" , 0 , "Ink Saver (Main)" , 2 , "Marie" ],
			[ "Arrow Pull-Ons" , "Toni Kensa" , "Footwear" , 10000 , "Drop Roller" , 3 , None ],
			[ "Athletic Arrows" , "Takoroka" , "Footwear" , 1200 , "Object Shredder" , 1 , None ],
			[ "Banana Basics" , "Krak-On" , "Footwear" , 400 , "Bomb Defense Up DX" , 1 , None ],
			[ "Birch Climbing Shoes" , "Inkline" , "Footwear" , 1200 , "Special Charge Up" , 1 , None ],
			[ "Black & Blue Squidkid V" , "Enperry" , "Footwear" , 12800 , "Special Saver" , 3 , None ],
			[ "Black Dakroniks" , "Zink" , "Footwear" , 1500 , "Main Power Up" , 2 , None ],
			[ "Black Flip-Flops" , "Zekko" , "Footwear" , 300 , "Object Shredder" , 1 , None ],
			[ "Black Norimaki 750s" , "Tentatek" , "Footwear" , 9800 , "Special Charge Up" , 3 , None ],
			[ "Black Seahorses" , "Zink" , "Footwear" , 2000 , "Swim Speed Up" , 2 , None ],
			[ "Black Trainers" , "Tentatek" , "Footwear" , 500 , "Quick Respawn" , 1 , None ],
			[ "Blue & Black Squidkid IV" , "Enperry" , "Footwear" , 11000 , "Quick Super Jump" , 3 , None ],
			[ "Blue Iromaki 750s" , "Tentatek" , "Footwear" , 1050 , "Ink Saver (Main)" , 1 , None ],
			[ "Blue Laceless Dakroniks" , "Zink" , "Footwear" , 1400 , "Stealth Jump" , 1 , None ],
			[ "Blue Lo-Tops" , "Zekko" , "Footwear" , 800 , "Bomb Defense Up DX" , 1 , None ],
			[ "Blue Moto Boots" , "Rockenberg" , "Footwear" , 10800 , "Ink Resistance Up" , 3 , None ],
			[ "Blue Power Stripes" , "Takoroka" , "Footwear" , 4880 , "Quick Respawn" , 2 , None ],
			[ "Blue Sea Slugs" , "Tentatek" , "Footwear" , 800 , "Special Charge Up" , 1 , None ],
			[ "Blue Slip-Ons" , "Krak-On" , "Footwear" , 400 , "Sub Power Up" , 1 , None ],
			[ "Blueberry Casuals" , "Krak-On" , "Footwear" , 700 , "Ink Saver (Sub)" , 1 , None ],
			[ "Bubble Rain Boots" , "Inkline" , "Footwear" , 450 , "Drop Roller" , 1 , None ],
			[ "Canary Trainers" , "Tentatek" , "Footwear" , 900 , "Quick Super Jump" , 1 , None ],
			[ "Cherry Kicks" , "Rockenberg" , "Footwear" , 2400 , "Stealth Jump" , 2 , None ],
			[ "Choco Clogs" , "Krak-On" , "Footwear" , 1800 , "Quick Respawn" , 2 , None ],
			[ "Chocolate Dakroniks" , "Zink" , "Footwear" , 1700 , "Ink Resistance Up" , 2 , None ],
			[ "Clownfish Basics" , "Krak-On" , "Footwear" , 500 , "Special Charge Up" , 1 , None ],
			[ "Crazy Arrows" , "Takoroka" , "Footwear" , 4500 , "Stealth Jump" , 2 , None ],
			[ "Cream Basics" , "Krak-On" , "Footwear" , 0 , "Special Saver" , 1 , "Starter Item" ],
			[ "Cream Hi-Tops" , "Krak-On" , "Footwear" , 500 , "Stealth Jump" , 1 , None ],
			[ "Custom Trail Boots" , "Inkline" , "Footwear" , 3000 , "Special Power Up" , 2 , None ],
			[ "Cyan Trainers" , "Tentatek" , "Footwear" , 700 , "Stealth Jump" , 1 , None ],
			[ "Deepsea Leather Boots" , "Rockenberg" , "Footwear" , 12000 , "Ink Saver (Sub)" , 3 , None ],
			[ "Flipper Floppers" , "Grizzco" , "Footwear" , 0 , None , 3 , "Salmon Run" ],
			[ "Fringed Loafers" , "amiibo" , "Footwear" , 0 , "Main Power Up" , 2 , "Inkling Girl 2" ],
			[ "Friendship Bracelet" , "Grizzco" , "Footwear" , 0 , None , 3 , "Salmon Run" ],
			[ "Gold Hi-Horses" , "Zink" , "Footwear" , 7000 , "Run Speed Up" , 3 , None ],
			[ "Gray Sea-Slug Hi-Tops" , "Tentatek" , "Footwear" , 8500 , "Bomb Defense Up DX" , 3 , None ],
			[ "Gray Yellow-Soled Wingtips" , "Rockenberg" , "Footwear" , 4600 , "Quick Super Jump" , 2 , None ],
			[ "Green Iromaki 750s" , "Tentatek" , "Footwear" , 1050 , "Special Power Up" , 1 , None ],
			[ "Green Laceups" , "Splash Mob" , "Footwear" , 1300 , "Main Power Up" , 1 , None ],
			[ "Green Rain Boots" , "Inkline" , "Footwear" , 1600 , "Stealth Jump" , 2 , None ],
			[ "Hero Runner Replicas" , "Cuttlegear" , "Footwear" , 0 , "Quick Super Jump" , 2 , "Callie" ],
			[ "Hero Snowboots Replicas" , "Cuttlegear" , "Footwear" , 0 , "Ink Saver (Sub)" , 2 , "Octo Canyon" ],
			[ "Honey & Orange Squidkid V" , "Enperry" , "Footwear" , 5800 , "Ink Saver (Sub)" , 2 , None ],
			[ "Hunter Hi-Tops" , "Krak-On" , "Footwear" , 500 , "Ink Recovery Up" , 1 , None ],
			[ "Hunting Boots" , "Splash Mob" , "Footwear" , 11500 , "Bomb Defense Up DX" , 3 , None ],
			[ "Icy Down Boots" , "Tentatek" , "Footwear" , 8200 , "Stealth Jump" , 3 , None ],
			[ "Inky Kid Clams" , "Rockenberg" , "Footwear" , 10500 , "Ink Recovery Up" , 3 , None ],
			[ "Kid Clams" , "Rockenberg" , "Footwear" , 9500 , "Special Power Up" , 3 , None ],
			[ "LE Lo-Tops" , "Zekko" , "Footwear" , 8000 , "Ink Saver (Sub)" , 3 , None ],
			[ "LE Soccer Shoes" , "Takoroka" , "Footwear" , 7500 , "Ink Resistance Up" , 3 , None ],
			[ "Luminous Delta Straps" , "Inkline" , "Footwear" , 5000 , "Main Power Up" , 2 , None ],
			[ "Marinated Slip-Ons" , "amiibo" , "Footwear" , 0 , "Ink Recovery Up" , 2 , "Marina" ],
			[ "Marination Lace-Ups" , "Zekko" , "Footwear" , 0 , "Special Power Up" , 3 , "SpringFest" ],
			[ "Mawcasins" , "Splash Mob" , "Footwear" , 2400 , "Ink Recovery Up" , 2 , None ],
			[ "Midnight Slip-Ons" , "Krak-On" , "Footwear" , 0 , "Object Shredder" , 3 , "SpringFest" ],
			[ "Milky Enperrials" , "Enperry" , "Footwear" , 0 , "Swim Speed Up" , 3 , "CoroCoro" ],
			[ "Mint Dakroniks" , "Zink" , "Footwear" , 1200 , "Drop Roller" , 1 , None ],
			[ "Moist Ghillie Boots" , "Forge" , "Footwear" , 8500 , "Object Shredder" , 3 , None ],
			[ "Moto Boots" , "Rockenberg" , "Footwear" , 3800 , "Quick Respawn" , 2 , None ],
			[ "Musselforge Flip-Flops" , "Inkline" , "Footwear" , 280 , "Ink Saver (Sub)" , 1 , None ],
			[ "Navy Enperrials" , "Enperry" , "Footwear" , 11000 , "Ink Saver (Main)" , 3 , None ],
			[ "Navy Red-Soled Wingtips" , "Rockenberg" , "Footwear" , 4600 , "Ink Saver (Main)" , 2 , None ],
			[ "Neo Octoling Boots" , "Cuttlegear" , "Footwear" , 0 , "Object Shredder" , 2 , "Octo Expansion" ],
			[ "Neon Delta Straps" , "Inkline" , "Footwear" , 4800 , "Sub Power Up" , 2 , None ],
			[ "Neon Sea Slugs" , "Tentatek" , "Footwear" , 700 , "Ink Resistance Up" , 1 , None ],
			[ "New-Day Arrows" , "Takoroka" , "Footwear" , 0 , "Ink Recovery Up" , 3 , "SpringFest" ],
			[ "New-Leaf Leather Boots" , "Rockenberg" , "Footwear" , 5000 , "Drop Roller" , 2 , None ],
			[ "Non-slip Senseis" , "Grizzco" , "Footwear" , 0 , None , 3 , "Salmon Run" ],
			[ "N-Pacer Ag" , "Enperry" , "Footwear" , 4900 , "Ink Recovery Up" , 2 , None ],
			[ "N-Pacer Au" , "Enperry" , "Footwear" , 8900 , "Quick Respawn" , 3 , None ],
			[ "N-Pacer CaO" , "Enperry" , "Footwear" , 3900 , "Object Shredder" , 2 , None ],
			[ "Null Boots Replica" , "Cuttlegear" , "Footwear" , 0 , "Drop Roller" , 2 , "Octo Expansion" ],
			[ "Old-Timey Shoes" , "Cuttlegear" , "Footwear" , 0 , "Run Speed Up" , 2 , "Octo Expansion" ],
			[ "Online Squidkid V" , "Enperry" , "Footwear" , 0 , "Stealth Jump" , 3 , "Nintendo Online Subscription" ],
			[ "Orange Arrows" , "Takoroka" , "Footwear" , 1100 , "Ink Saver (Main)" , 1 , None ],
			[ "Orange Iromaki 750s" , "Tentatek" , "Footwear" , 1050 , "Drop Roller" , 1 , None ],
			[ "Orange Lo-Tops" , "Zekko" , "Footwear" , 800 , "Swim Speed Up" , 1 , None ],
			[ "Orca Hi-Tops" , "Takoroka" , "Footwear" , 2800 , "Special Saver" , 2 , None ],
			[ "Orca Passion Hi-Tops" , "Takoroka" , "Footwear" , 2780 , "Quick Super Jump" , 2 , None ],
			[ "Orca Woven Hi-Tops" , "Takoroka" , "Footwear" , 3600 , "Ink Saver (Sub)" , 2 , None ],
			[ "Oyster Clogs" , "Krak-On" , "Footwear" , 600 , "Run Speed Up" , 1 , None ],
			[ "Pearlescent Kicks" , "amiibo" , "Footwear" , 0 , "Special Charge Up" , 2 , "Pearl" ],
			[ "Pearlescent Squidkid IV" , "Enperry" , "Footwear" , 0 , "Drop Roller" , 3 , "SpringFest" ],
			[ "Pearl Punk Crowns" , "Rockenberg" , "Footwear" , 0 , "Ink Saver (Main)" , 3 , "SpringFest" ],
			[ "Pearl-Scout Lace-Ups" , "Zekko" , "Footwear" , 0 , "Quick Super Jump" , 3 , "SpringFest" ],
			[ "Pink Trainers" , "Tentatek" , "Footwear" , 500 , "Sub Power Up" , 1 , None ],
			[ "Piranha Moccasins" , "Splash Mob" , "Footwear" , 9400 , "Stealth Jump" , 3 , None ],
			[ "Plum Casuals" , "Krak-On" , "Footwear" , 2000 , "Object Shredder" , 2 , None ],
			[ "Polka-dot Slip-Ons" , "Krak-On" , "Footwear" , 1500 , "Drop Roller" , 2 , None ],
			[ "Power Boots" , "amiibo" , "Footwear" , 0 , "Ink Saver (Main)" , 2 , "Inkling Squid" ],
			[ "Power Boots Mk I" , "amiibo" , "Footwear" , 0 , "Bomb Defense Up DX" , 2 , "Inkling Squid 2" ],
			[ "Pro Trail Boots" , "Inkline" , "Footwear" , 9800 , "Ink Resistance Up" , 3 , None ],
			[ "Punk Blacks" , "Rockenberg" , "Footwear" , 8800 , "Main Power Up" , 3 , None ],
			[ "Punk Cherries" , "Rockenberg" , "Footwear" , 9000 , "Bomb Defense Up DX" , 3 , None ],
			[ "Punk Whites" , "Rockenberg" , "Footwear" , 3800 , "Special Charge Up" , 2 , None ],
			[ "Punk Yellows" , "Rockenberg" , "Footwear" , 3000 , "Special Saver" , 2 , None ],
			[ "Purple Hi-Horses" , "Zink" , "Footwear" , 1000 , "Special Power Up" , 1 , None ],
			[ "Purple Iromaki 750s" , "Tentatek" , "Footwear" , 1050 , "Swim Speed Up" , 1 , None ],
			[ "Purple Sea Slugs" , "Tentatek" , "Footwear" , 1800 , "Run Speed Up" , 2 , None ],
			[ "Red & Black Squidkid IV" , "Enperry" , "Footwear" , 11000 , "Special Charge Up" , 3 , None ],
			[ "Red & White Squidkid V" , "Enperry" , "Footwear" , 12800 , "Run Speed Up" , 3 , None ],
			[ "Red FishFry Sandals" , "Firefin" , "Footwear" , 2880 , "Object Shredder" , 2 , None ],
			[ "Red Hi-Horses" , "Zink" , "Footwear" , 800 , "Ink Saver (Main)" , 1 , None ],
			[ "Red Hi-Tops" , "Krak-On" , "Footwear" , 1800 , "Ink Resistance Up" , 2 , None ],
			[ "Red Iromaki 750s" , "Tentatek" , "Footwear" , 1050 , "Ink Saver (Sub)" , 1 , None ],
			[ "Red Power Stripes" , "Takoroka" , "Footwear" , 5880 , "Run Speed Up" , 2 , None ],
			[ "Red Sea Slugs" , "Tentatek" , "Footwear" , 8000 , "Special Saver" , 3 , None ],
			[ "Red Slip-Ons" , "Krak-On" , "Footwear" , 300 , "Quick Super Jump" , 1 , None ],
			[ "Red Work Boots" , "Rockenberg" , "Footwear" , 11000 , "Quick Super Jump" , 3 , None ],
			[ "Red-Mesh Sneakers" , "Tentatek" , "Footwear" , 1700 , "Special Power Up" , 2 , None ],
			[ "Rina Squidkid IV" , "Enperry" , "Footwear" , 0 , "Bomb Defense Up DX" , 3 , "SpringFest" ],
			[ "Roasted Brogues" , "Rockenberg" , "Footwear" , 1200 , "Bomb Defense Up DX" , 1 , None ],
			[ "Samurai Shoes" , "amiibo" , "Footwear" , 0 , "Special Power Up" , 2 , "Inkling Boy" ],
			[ "School Shoes" , "amiibo" , "Footwear" , 0 , "Ink Saver (Sub)" , 2 , "Inkling Girl" ],
			[ "Sea Slug Volt 95s" , "Tentatek" , "Footwear" , 3260 , "Ink Saver (Sub)" , 2 , None ],
			[ "Sennyu Inksoles" , "Rockenberg" , "Footwear" , 0 , "Stealth Jump" , 3 , "CoroCoro" ],
			[ "Sesame Salt 270s" , "Tentatek" , "Footwear" , 3260 , "Quick Super Jump" , 2 , None ],
			[ "Shark Moccasins" , "Splash Mob" , "Footwear" , 800 , "Sub Power Up" , 1 , None ],
			[ "Smoky Wingtips" , "Rockenberg" , "Footwear" , 8600 , "Object Shredder" , 3 , None ],
			[ "Snow Delta Straps" , "Inkline" , "Footwear" , 8800 , "Swim Speed Up" , 3 , None ],
			[ "Snowy Down Boots" , "Tentatek" , "Footwear" , 8000 , "Quick Super Jump" , 3 , None ],
			[ "Soccer Shoes" , "Takoroka" , "Footwear" , 9600 , "Bomb Defense Up DX" , 3 , None ],
			[ "Squid-Stitch Slip-Ons" , "Krak-On" , "Footwear" , 1500 , "Bomb Defense Up DX" , 2 , None ],
			[ "Squinja Boots" , "amiibo" , "Footwear" , 0 , "Swim Speed Up" , 2 , "Inkling Boy 2" ],
			[ "Squink Wingtips" , "Rockenberg" , "Footwear" , 800 , "Quick Respawn" , 1 , None ],
			[ "Strapping Reds" , "Splash Mob" , "Footwear" , 1400 , "Ink Resistance Up" , 1 , None ],
			[ "Strapping Whites" , "Splash Mob" , "Footwear" , 8700 , "Ink Saver (Sub)" , 3 , None ],
			[ "Suede Gray Lace-Ups" , "Zekko" , "Footwear" , 1200 , "Ink Recovery Up" , 1 , None ],
			[ "Suede Marine Lace-Ups" , "Zekko" , "Footwear" , 1200 , "Ink Resistance Up" , 1 , None ],
			[ "Suede Nation Lace-Ups" , "Zekko" , "Footwear" , 4200 , "Ink Saver (Main)" , 2 , None ],
			[ "Sun & Shade Squidkid IV" , "Enperry" , "Footwear" , 13000 , "Main Power Up" , 3 , None ],
			[ "Sunny Climbing Shoes" , "Inkline" , "Footwear" , 3200 , "Special Saver" , 2 , None ],
			[ "Sunset Orca Hi-Tops" , "Takoroka" , "Footwear" , 3800 , "Drop Roller" , 2 , None ],
			[ "Tan Work Boots" , "Rockenberg" , "Footwear" , 3000 , "Sub Power Up" , 2 , None ],
			[ "Tea-Green Hunting Boots" , "Splash Mob" , "Footwear" , 11500 , "Quick Respawn" , 3 , None ],
			[ "Toni Kensa Black Hi-Tops" , "Toni Kensa" , "Footwear" , 9880 , "Sub Power Up" , 3 , None ],
			[ "Toni Kensa Soccer Shoes" , "Toni Kensa" , "Footwear" , 10500 , "Ink Saver (Main)" , 3 , None ],
			[ "Trail Boots" , "Inkline" , "Footwear" , 7500 , "Ink Recovery Up" , 3 , None ],
			[ "Trooper Power Stripes" , "Takoroka" , "Footwear" , 0 , "Sub Power Up" , 3 , "SpringFest" ],
			[ "Truffle Canvas Hi-Tops" , "Krak-On" , "Footwear" , 1350 , "Special Power Up" , 1 , None ],
			[ "Turquoise Kicks" , "Rockenberg" , "Footwear" , 2800 , "Special Charge Up" , 2 , None ],
			[ "Violet Trainers" , "Tentatek" , "Footwear" , 1000 , "Object Shredder" , 1 , None ],
			[ "White Arrows" , "Takoroka" , "Footwear" , 2500 , "Special Power Up" , 2 , None ],
			[ "White Kicks" , "Rockenberg" , "Footwear" , 1400 , "Swim Speed Up" , 1 , None ],
			[ "White Laceless Dakroniks" , "Zink" , "Footwear" , 1800 , "Run Speed Up" , 2 , None ],
			[ "White Norimaki 750s" , "Tentatek" , "Footwear" , 3800 , "Swim Speed Up" , 2 , None ],
			[ "White Seahorses" , "Zink" , "Footwear" , 600 , "Ink Recovery Up" , 1 , None ],
			[ "Wooden Sandals" , "Grizzco" , "Footwear" , 0 , None , 3 , "Salmon Run" ],
			[ "Yellow FishFry Sandals" , "Firefin" , "Footwear" , 2880 , "Main Power Up" , 2 , None ],
			[ "Yellow Iromaki 750s" , "Tentatek" , "Footwear" , 1050 , "Special Saver" , 1 , None ],
			[ "Yellow Seahorses" , "Zink" , "Footwear" , 1500 , "Bomb Defense Up DX" , 2 , None ],
			[ "Yellow-Mesh Sneakers" , "Tentatek" , "Footwear" , 1300 , "Main Power Up" , 1 , None ],
			[ "Zombie Hi-Horses" , "Zink" , "Footwear" , 800 , "Special Charge Up" , 1 , None ]
		]

		self.gear = []
		for g in data:
			name     = g[0]
			brand    = self.getBrandByName(g[1])
			slot     = self.getSlotByName(g[2])
			price    = g[3]
			main     = g[4] and self.getAbilityByName(g[4])
			subcount = g[5]
			source   = g[6]

			if not brand:
				raise Exception(f"Unknown brand '{g[1]}' on gear '{name}'.")
			elif not slot:
				raise Exception(f"Unknown slot '{g[2]}' on gear '{name}'.")
			elif g[4] and not main:
				raise Exception(f"Unknown main ability '{g[4]}' on gear '{name}'.")

			self.gear.append(SplatGear(name, brand, slot, price, main, subcount, source))

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

	def matchWeaponType(self, query):
		return self.matchItems("weapontype", self.weapontypes, query)

	def matchWeapons(self, query):
		return self.matchItems("weapon", self.weapons, query)

	def matchSpecials(self, query):
		return self.matchItems("special", self.specials, query)

	def matchSubweapons(self, query):
		return self.matchItems("subweapon", self.subweapons, query)

	def matchSlots(self, query):
		return self.matchItems("slot", self.slots, query)

	def matchAbilities(self, query):
		return self.matchItems("ability", self.abilities, query)

	def matchBrands(self, query):
		return self.matchItems("brand", self.brands, query)

	def matchGear(self, query):
		return self.matchItems("gear", self.gear, query)

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

	def getWeaponTypeByName(self, name):
		return self.getItemByName(self.weapontypes, name)

	def getWeaponsBySpecial(self, special):
		return list(filter(lambda w: w.special() == special, self.weapons))

	def getWeaponsBySub(self, sub):
		return list(filter(lambda w: w.sub() == sub, self.weapons))

	def getWeaponsByType(self, type):
		return list(filter(lambda w: w.type() == type, self.weapons))

	def getSpecialByName(self, name):
		return self.getItemByName(self.specials, name)

	def getSlotByName(self, name):
		return self.getItemByName(self.slots, name)

	def getAbilityByName(self, name):
		return self.getItemByName(self.abilities, name)

	def getBrandByName(self, name):
		return self.getItemByName(self.brands, name)

	def getGearByName(self, name):
		return self.getItemByName(self.gear, name)

	def getRandomMap(self):
		return random.choice(self.maps)

	def getRandomWeapon(self):
		weapons = list(filter(lambda w: w.dupid() == None, self.weapons))  # Get only non-duplicate weapons
		return random.choice(weapons)

	def getAllSpecials(self):
		return self.specials

	def getAllSubweapons(self):
		return self.subweapons

	def getAllWeapons(self):
		return self.weapons

	def getAllWeaponTypes(self):
		return self.weapontypes

	def getAllMaps(self):
		return self.maps

	def getAllAbilities(self):
		return self.abilities

	def getAllBrands(self):
		return self.brands

	def getAllGear(self):
		return self.gear
