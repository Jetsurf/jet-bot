import random

class MatchItem():
	def __init__(self, name, abbrevs = None):
		self._name      = name
		self._abbrevs   = abbrevs or []

	def name(self, language = "en-US"):
		if isinstance(self._name, dict):
			return self._name.get(language, self._name.get("en-US"))
		else:
			return self._name

	def abbrev(self):
		return self._abbrevs[0] if len(self._abbrevs) else None

	def abbrevs(self):
		return self._abbrevs

	def format(self, language = "en-US"):
		abbrev = self.abbrev()
		if abbrev:
			return "__" + self.name(language) + "__ (**" + abbrev + "**)"
		else:
			return "__" + self.name(language) + "__"

	def hasAbbrev(self, a):
		return a.lower() in self._abbrevs


class MatchResult():
	def __init__(self, name, query, items):
		self.name  = name
		self.query = query
		self.items = items

	def isValid(self):
		return len(self.items) == 1

	def get(self):
		if self.isValid():
			return self.items[0]
		return None

	def errorMessage(self, listhelp = None):
		l = len(self.items)
		if l == 0:
			msg = "I don't know of any " + self.name + " named '" + self.query + "'."
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


class MatchSet():
	def __init__(self, name, items):
		self.name  = name
		self.items = items
		pass

	def checkAbbrevs(self, set):
		seenAbbrevs = {}
		for item in self.items:
			for abbrev in item.abbrevs():
				if abbrev in seenAbbrevs:
					print("MatchSet: Abbrev '" + abbrev + "' used by both '" + item.name() + "' and '" + seenAbbrevs[abbrev].name() + "'")
				else:
					seenAbbrevs[abbrev] = item

	def append(self, item):
		self.items.append(item)

	def matchItem(self, query, language = "en-US"):
		if len(query) == 0:
			return MatchResult(self.name, query, [])

		query = query.lower()
		items = []

		# Stage 1: Look for exact match on a name or abbreviation
		for item in self.items:
			if item.hasAbbrev(query) or (item.name(language).lower() == query):
				return MatchResult(self.name, query, [item])

		# Stage 2: Substring match of name
		for item in self.items:
			if item.name(language).lower().find(query) != -1:
				items.append(item)

		return MatchResult(self.name, query, items)

	def getItemByName(self, name, language = "en-US"):
		for i in self.items:
			if i.name(language) == name:
				return i
		return None

	def getRandomItem(self):
		return random.choice(self.items)

	def getAllItems(self):
		return self.items
