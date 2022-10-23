import json

abilitiesData = [
	['Intensify Action' , 'Action_Up'                 ],
	['Comeback'         , 'ComeBack'                  ],
	['Haunt'            , 'DeathMarking'              ],
	['Last-Ditch Effort', 'EndAllUp'                  ],
	['Ability Doubler'  , 'ExSkillDouble'             ],
	['Respawn Punisher' , 'Exorcist'                  ],
	['Run Speed Up'     , 'HumanMove_Up'              ],
	['Ink Recovery Up'  , 'InkRecovery_Up'            ],
	['Quick Super Jump' , 'JumpTime_Save'             ],
	['Ink Saver (Main)' , 'MainInk_Save'              ],
	['Tenacity'         , 'MinorityUp'                ],
	['Object Shredder'  , 'ObjectEffect_Up'           ],
	['Ink Resistance Up', 'OpInkEffect_Reduction'     ],
	['Special Saver'    , 'RespawnSpecialGauge_Save'  ],
	['Quick Respawn'    , 'RespawnTime_Save'          ],
	['Drop Roller'      , 'SomersaultLanding'         ],
	['Special Charge Up', 'SpecialIncrease_Up'        ],
	['Special Power Up' , 'SpecialSpec_Up'            ],
	['Ninja Squid'      , 'SquidMoveSpatter_Reduction'],
	['Swim Speed Up'    , 'SquidMove_Up'              ],
	['Opening Gambit'   , 'StartAllUp'                ],
	['Sub Resistance Up', 'SubEffect_Reduction'       ],
	['Ink Saver (Sub)'  , 'SubInk_Save'               ],
	['Sub Power Up'     , 'SubSpec_Up'                ],
	['Stealth Jump'     , 'SuperJumpSign_Hide'        ],
	['Thermal Ink'      , 'ThermalInk'                ],
]

brandsData = [
	['SquidForce'   , 'B00', 'Ink Resistance Up' , 'Ink Saver (Main)'  ],
	['Zink'         , 'B01', 'Quick Super Jump'  , 'Quick Respawn'     ],
	['Krak-On'      , 'B02', 'Swim Speed Up'     , 'Sub Resistance Up' ],
	['Rockenberg'   , 'B03', 'Run Speed Up'      , 'Swim Speed Up'     ],
	['Zekko'        , 'B04', 'Special Saver'     , 'Special Charge Up' ],
	['Forge'        , 'B05', 'Special Power Up'  , 'Ink Saver (Sub)'   ],
	['Firefin'      , 'B06', 'Ink Saver (Sub)'   , 'Ink Recovery Up'   ],
	['Skalop'       , 'B07', 'Quick Respawn'     , 'Special Saver'     ],
	['Splash Mob'   , 'B08', 'Ink Saver (Main)'  , 'Run Speed Up'      ],
	['Inkline'      , 'B09', 'Sub Resistance Up' , 'Intensify Action'  ],
	['Tentatek'     , 'B10', 'Ink Recovery Up'   , 'Quick Super Jump'  ],
	['Takoroka'     , 'B11', 'Special Charge Up' , 'Special Power Up'  ],
	['Annaki'       , 'B15', 'Ink Saver (Sub)'   , 'Special Saver'     ],
	['Enperry'      , 'B16', 'Sub Power Up'      , 'Ink Resistance Up' ],
	['Toni Kensa'   , 'B17', 'Ink Saver (Main)'  , 'Sub Power Up'      ],
	['Barazushi'    , 'B19', 'Intensify Action'  , 'Sub Power Up'      ],
	['Emberz'       , 'B20', 'Intensify Action'  , 'Special Charge Up' ],
	['Grizzco'      , 'B97', None                , None                ],
	['Cuttlegear'   , 'B98', None                , None                ],
	['Amiibo'       , 'B99', None                , None                ],
]

mapsData = [
	['Scorch Gorge',         ['sg']],
	['Eeltail Alley',        ['ea', 'eta']],
	['Undertow Spillway',    ['us', 'uts']],
	['Mincemeat Metalworks', ['mmm']],
	['Hagglefish Market',    ['hm', 'hfm']],
	['Museum d\'Alfonsino',  ['ma', 'mda']],
	['Hammerhead Bridge',    ['hhb']],
	['Mahi-Mahi Resort',     ['mmr']],
	['Inkblot Art Academy',  ['iaa']],
	['Sturgeon Shipyard',    ['ss']],
	['MakoMart',             ['mm']],
	['Wahoo World',          ['ww']]
]

modesData = [
	["Splat Zones",   ['sz']],
	["Rainmaker",     ['rm']],
	["Tower Control", ['tc']],
	["Clam Blitz",    ['cb']],
	["Turf War",      ['tw']]
]

import gameinfo.matchset

class Splat3Map(gameinfo.matchset.MatchItem):
	pass

class Splat3Mode(gameinfo.matchset.MatchItem):
	pass

class Splat3Subweapon(gameinfo.matchset.MatchItem):
	pass

class Splat3Special(gameinfo.matchset.MatchItem):
	pass

class Splat3Ability(gameinfo.matchset.MatchItem):
	def __init__(self, id, name, abbrevs):
		self._id   = id
		super().__init__(name, abbrevs)

	def id(self):
		return self._id

class Splat3Brand(gameinfo.matchset.MatchItem):
	def __init__(self, id, name, common, uncommon):
		self._id       = id
		self._common   = common
		self._uncommon = uncommon
		super().__init__(name, [])

	def id(self):
		return self._id

	def commonAbility(self):
		return self._common

	def uncommonAbility(self):
		return self._uncommon

class Splat3WeaponType(gameinfo.matchset.MatchItem):
	def __init__(self, name, pluralName, abbrevs):
		self._pluralname = pluralName

		super().__init__(name, abbrevs)

	def pluralname(self):
		return self._pluralName

class Splat3Weapon(gameinfo.matchset.MatchItem):
	def __init__(self, id, name, abbrevs, type, sub, special, specpts, price, level):
		self._id      = id
		self._type    = type
		self._sub     = sub
		self._special = special
		self._specpts = specpts
		self._price   = price
		self._level   = level
		super().__init__(name, abbrevs)

	def id(self):
		return self._id

	def type(self):
		return self._type

	def sub(self):
		return self._sub

	def special(self):
		return self._special

	def specpts(self):
		return self._specpts

	def price(self):
		return self._price

	def level(self):
		return self._level

class Splat3Gear(gameinfo.matchset.MatchItem):
	def __init__(self, id, name, intName, price, brand, rarity, season, ability):
		self._id	= id
		self._intName	= intName
		self._price	= price
		self._brand	= brand
		self._rarity	= rarity
		self._season	= season
		self._ability	= ability
		super().__init__(name, [])

	def id(self):
		return self._id

	def price(self):
		return self._price

	def brand(self):
		return self._brand

	def rarity(self):
		return self._rarity

	def ability(self):
		return self._ability

class Splat3():
	def __init__(self, datadir):
		data = self.loadJSON(datadir)

		self.initMaps()
		self.initModes()
		self.initSubweapons(data)
		self.initSpecials(data)
		self.initWeaponTypes()
		self.initWeapons(data)
		self.initAbilities()
		self.initBrands()
		self.initGear(data)

	def loadJSON(self, datadir):
		path = f"{datadir}/splat3.json"
		with open(path, 'r') as f:
	                return json.load(f)

	def initMaps(self):
		self.maps = gameinfo.matchset.MatchSet('map', [])
		for m in mapsData:
			name    = m[0]
			abbrevs = m[1]
			self.maps.append(Splat3Map(name, abbrevs))

	def initModes(self):
		self.modes = gameinfo.matchset.MatchSet('mode', [])
		for m in modesData:
			name    = m[0]
			abbrevs = m[1]
			self.modes.append(Splat3Mode(name, abbrevs))

	def initSubweapons(self, data):
		self.subweapons = gameinfo.matchset.MatchSet('subweapon', [])
		for sw in data['subweapons']:
			self.subweapons.append(Splat3Subweapon(sw['names'], sw['abbrevs']))

	def initSpecials(self, data):
		self.specials = gameinfo.matchset.MatchSet('special', [])
		for s in data['specials']:
			self.specials.append(Splat3Special(s['names'], s['abbrevs']))

	def initWeaponTypes(self):
		self.weaponTypes = gameinfo.matchset.MatchSet('weapon type', [
			Splat3WeaponType("Shooter",   "Shooters",   ["s"]),
			Splat3WeaponType("Blaster",   "Blasters",   ["bl"]),
			Splat3WeaponType("Roller",    "Rollers",    ["r"]),
			Splat3WeaponType("Charger",   "Chargers",   ["c", "sniper"]),
			Splat3WeaponType("Slosher",   "Sloshers",   ["sl", "bucket"]),
			Splat3WeaponType("Splatling", "Splatlings", ["sp", "gatling"]),
			Splat3WeaponType("Dualies",   "Dualies",    ["d"]),
			Splat3WeaponType("Brella",    "Brellas",    ["bre", "u", "umbrella", "brolly"]),
			Splat3WeaponType("Brush",     "Brushes",    ["bru"]),
			Splat3WeaponType("Stringer",  "Stringers",  ["str", "bow"]),
			Splat3WeaponType("Splatana",  "Splatanas",  ["sna", "saber", "sword"])
                ])

	def initWeapons(self, data):
		self.weapons = gameinfo.matchset.MatchSet('weapon', [])
		for w in data['weapons']:
			type = self.weaponTypes.getItemByName(w['type'])
			if type is None:
				raise Exception(f"No such weapon type '{w['type']}'")

			sub = self.subweapons.getItemByName(w['sub'])
			if sub is None:
				raise Exception(f"No such subweapon '{w['sub']}'")

			special = self.specials.getItemByName(w['special'])
			if special is None:
				raise Exception(f"No such special '{w['special']}'")

			abbrevs = []  # TODO
			self.weapons.append(Splat3Weapon(w['id'], w['names'], abbrevs, type, sub, special, w['specialPoints'], w['price'], w['level']))

	def initAbilities(self):
		self.abilities = gameinfo.matchset.MatchSet('ability', [])
		for a in abilitiesData:
			name    = a[0]
			id      = a[1]
			abbrevs = []  # TODO
			self.abilities.append(Splat3Ability(id, name, abbrevs))

	def initBrands(self):
		self.brands = gameinfo.matchset.MatchSet('brand', [])
		for b in brandsData:
			name     = b[0]
			id       = b[1]
			common   = b[2]
			uncommon = b[3]
			self.brands.append(Splat3Brand(id, name, self.abilities.getItemByName(common), self.abilities.getItemByName(uncommon)))

	def initGearSet(self, name, gear):
		set = gameinfo.matchset.MatchSet(name, [])
		for g in gear:
			brand = self.getBrandById(g['brand'])
			if brand is None:
				raise Exception(f"No such brand '{g['brand']}'")

			ability = self.abilities.getItemByName(g['ability'])
			if ability is None:
				raise Exception(f"No such ability '{g['ability']}'")

			set.append(Splat3Gear(g['id'], g['names'], g['internalName'], g['price'], brand, g['rarity'], g['season'], ability))

		return set

	def initGear(self, data):
		self.hats    = self.initGearSet('hats', data['hats'])
		self.clothes = self.initGearSet('clothes', data['clothes'])
		self.shoes   = self.initGearSet('shoes', data['shoes'])

		# Superset of all gear
		self.gear    = gameinfo.matchset.MatchSet('gear', [*self.hats.getAllItems(), *self.clothes.getAllItems(), *self.shoes.getAllItems()])

	def getSpecialNames(self, language = "en-US"):
		return [ s.name(language) for s in self.specials.getAllItems() ]

	def getSubweaponNames(self, language = "en-US"):
		return [ s.name(language) for s in self.subweapons.getAllItems() ]

	def getWeaponsBySpecial(self, special):
		return list(filter(lambda w: w.special() == special, self.weapons.getAllItems()))

	def getWeaponsBySubweapon(self, subweapon):
		return list(filter(lambda w: w.sub() == subweapon, self.weapons.getAllItems()))

	def getBrandById(self, id):
		return list(filter(lambda b: b.id() == id, self.brands.getAllItems()))
