from __future__ import print_function

from . filterCustomChannel import get_xml_string, get_xml_rating_string
from xml.etree.cElementTree import iterparse
from calendar import timegm
from time import strptime, struct_time


try:
	basestring
except NameError:
	basestring = str


def quickptime(date_str):
	return struct_time(
		(
			int(date_str[0:4]),     # Year
			int(date_str[4:6]),     # Month
			int(date_str[6:8]),     # Day
			int(date_str[8:10]),    # Hour
			int(date_str[10:12]),   # Minute
			0,                      # Second (set to 0)
			-1,                     # Weekday (set to -1 as unknown)
			-1,                     # Julian day (set to -1 as unknown)
			0                       # DST (Daylight Saving Time, set to 0 as unknown)
		)
	)


def get_time_utc(timestring, fdateparse):
	try:
		values = timestring.split(" ")
		if len(values) < 2:
			raise ValueError("Invalid timestring format, missing offset")
		tm = fdateparse(values[0])
		time_gm = timegm(tm)
		time_gm -= (3600 * int(values[1]) // 100)
		return time_gm
	except Exception as e:
		print("[XMLTVConverter] get_time_utc error:", e)
		return 0


def get_xml_language(elem, name):
	r = ''
	try:
		for node in elem.findall(name):
			lang = node.get('lang', None)
			if not r:
				# ugly, I know ...
				if lang == 'en':
					r = 'eng'
				elif lang == 'de':
					r = 'deu'
				elif lang == 'da':
					r = 'den'
				elif lang == 'dk':
					r = 'den'
				elif lang == 'fr':
					r = 'fra'
				elif lang == 'es':
					r = 'spa'
				elif lang == 'it':
					r = 'ita'
				elif lang == 'nl':
					r = 'dut'
				elif lang == 'ro':
					r = 'rum'
				elif lang == 'sr':
					r = 'srp'
				elif lang == 'hr':
					r = 'hrv'
				elif lang == 'pl':
					r = 'pol'
				elif lang == 'cs':
					r = 'cze'
				elif lang == 'he':
					r = 'heb'
				elif lang == 'pt':
					r = 'por'
				elif lang == 'sk':
					r = 'slo'
				elif lang == 'ar':
					r = 'ara'
				elif lang == 'hu':
					r = 'hun'
				elif lang == 'ja':
					r = 'jpn'
				elif lang == 'da':
					r = 'dan'
				elif lang == 'et':
					r = 'est'
				elif lang == 'fi':
					r = 'fin'
				elif lang == 'el':
					r = 'gre'
				elif lang == 'is':
					r = 'ice'
				elif lang == 'lb':
					r = 'ltz'
				elif lang == 'lt':
					r = 'lit'
				elif lang == 'lv':
					r = 'lav'
				elif lang == 'no':
					r = 'nor'
				elif lang == 'nb':
					r = 'nor'
				elif lang == 'pt':
					r = 'por'
				elif lang == 'ru':
					r = 'rus'
				elif lang == 'sv':
					r = 'swe'
				elif lang == 'se':
					r = 'swe'
				elif lang == 'tr':
					r = 'tur'
				elif lang == 'uk':
					r = 'ukr'
				#
				# continue list here ...
				#
				else:
					print("[XMLTVConverter] unmapped language:", lang)
					r = 'eng'
	except Exception as e:
		print("[XMLTVConverter] get_xml_string error:", e)
	return r.decode() if isinstance(r, bytes) else r


def enumerateProgrammes(fp):
	"""Enumerates programme ElementTree nodes from file object 'fp'"""
	for event, elem in iterparse(fp):
		try:
			if elem.tag == "programme":
				yield elem
				elem.clear()
			elif elem.tag == "channel":
				# Throw away channel elements, save memory
				elem.clear()
		except Exception as e:
			print("[XMLTVConverter] enumerateProgrammes error:", e)


class XMLTVConverter:
	def __init__(self, channels_dict, category_dict, dateformat="%Y%m%d%H%M%S %Z"):
		self.channels = channels_dict
		self.categories = category_dict
		if dateformat.startswith("%Y%m%d%H%M%S"):
			self.dateParser = quickptime
		else:
			self.dateParser = lambda x: strptime(x, dateformat)

	def enumFile(self, fileobj):
		print("[XMLTVConverter] Enumerating event information")
		lastUnknown = None
		# there is nothing no enumerate if there are no channels loaded
		if not self.channels:
			return
		for elem in enumerateProgrammes(fileobj):
			channel = elem.get("channel")
			channel = channel.lower()
			if channel not in self.channels:
				if lastUnknown != channel:
					print("Unknown channel: ", channel)
					lastUnknown = channel
				# return a None object to give up time to the reactor.
				yield None
				continue
			try:
				services = self.channels[channel]
				start = get_time_utc(elem.get("start"), self.dateParser) + self.offset
				stop = get_time_utc(elem.get("stop"), self.dateParser) + self.offset
				title = get_xml_string(elem, "title")
				# try/except for EPG XML files with program entries containing <sub-title ... />
				try:
					subtitle = get_xml_string(elem, "sub-title")
				except:
					subtitle = ""
				# try/except for EPG XML files with program entries containing <desc ... />
				try:
					description = get_xml_string(elem, "desc")
				except:
					description = ""
				category = get_xml_string(elem, "category")
				cat_nr = self.get_category(category, stop - start)

				try:
					rating_str = get_xml_rating_string(elem)
					# hardcode country as ENG since there is no handling for parental certification systems per country yet
					# also we support currently only number like values like "12+" since the epgcache works only with bytes right now
					rating = [("eng", int(rating_str) - 3)]
				except:
					rating = None

				# data_tuple = (data.start, data.duration, data.title, data.short_description, data.long_description, data.type)
				if not stop or not start or (stop <= start):
					print("[XMLTVConverter] Bad start/stop time: %s (%s) - %s (%s) [%s]" % (elem.get('start'), start, elem.get('stop'), stop, title))
				if rating:
					yield (services, (start, stop - start, title, subtitle, description, cat_nr, 0, rating))
				else:
					yield (services, (start, stop - start, title, subtitle, description, cat_nr))
			except Exception as e:
				print("[XMLTVConverter] parsing event error:", e)

	def get_category(self, cat, duration):
		if (not cat) or (not isinstance(cat, type('str'))):
			return 0
		if cat in self.categories:
			category = self.categories[cat]
			if len(category) > 1:
				if duration > 60 * category[1]:
					return category[0]
			elif len(category) > 0:
				return category
		return 0
