import gettext
import re
import contextvars
import builtins

class Translate:
	DOMAIN = 'jet-bot'

	LANGS = {
		'en_US': {'name': 'English',  'country': 'USA'},
		'fr_FR': {'name': 'Français', 'country': 'France'},
	}

	# Breaks down a locale code into fields. There are two supported styles, POSIX and IETF.
	@classmethod
	def parse_locale_code(cls, code):
		if m := re.match(r'^([a-z]{2})(?:_([a-zA-Z]+))?(?:[.]([^@]+))?(?:@(.*))?$', code):  # POSIX
			return {'language': m[1], 'territory': m[2], 'charset': m[3], 'modifier': m[4]}
		elif re.match(r'^([a-zA-Z]{1,8})(?:-([a-zA-Z]))*$', code):  # IETF
			data = {}
			parts = code.split("-")

			if len(parts[0]) == 2:  # Two letters in first position is ISO 639 language code
				data['language'] = parts[0].lower()

			if len(parts[1]) == 2:  # Two letters in second position is ISO 3166 alpha-2 country code
				data['territory'] = parts[1].upper()

			data['extra'] = parts[2:]

			return data

		return None

	# POSIX-style locale defined in ISO/IEC 15897 uses underscore separator.
	@classmethod
	def posix_locale_code(cls, code):
		parsed = cls.parse_locale_code(code)
		if parsed is None:
			return None
		return f"{parsed[language]}_{parsed[territory]}"

	# IETF-style locale defined in RFC 1766 uses hyphen separator.
	@classmethod
	def ietf_locale_code(cls, code):
		parsed = cls.parse_locale_code(code)
		if parsed is None:
			return None
		return f"{parsed[language]}-{parsed[territory]}"

	def __init__(self, path):
		self.translations = {}
		self.lang = contextvars.ContextVar('lang')

		gettext.install(self.DOMAIN, localedir = path)

		for k in self.LANGS.keys():
			if k == 'en_US':
				continue  # Don't try to translate default language
			self.translations[k] = gettext.translation(self.DOMAIN, localedir = path, languages = [k])

		builtins.__dict__['_'] = self.translate

	def select(self, lang):
		if (lang != 'en_US') and (not lang in self.translations):
			print(f"Cannot select language '{lang}'")
			return

		self.lang.set(lang)  # Save to contextvar

	def translate(self, message):
		lang = self.lang.get('en_US')  # Read from contextvar
		if (lang == 'en_US') or (not lang in self.translations):
			return message

		return self.translations[lang].gettext(message)

	def get_lang_ietf(self):
		lang = self.lang.get('en_US')  # Read from contextvar
		return lang.replace("_", "-")
