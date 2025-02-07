#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# This file no longer has a direct link to Enigma2, allowing its use anywhere
# you can supply a similar interface. See plugin.py and OfflineImport.py for
# the contract.

from __future__ import print_function
from . import log

from Components.config import config
from datetime import datetime
from os import statvfs, symlink, unlink
from os.path import exists, getsize, join, split, splitext, isdir, ismount
from socket import getaddrinfo, AF_INET6, has_ipv6
from sys import version_info
from twisted import version
from twisted.internet import reactor, threads
from twisted.web.client import downloadPage
import gzip
import random
import time
import twisted.python.runtime


try:
	pythonVer = version_info.major
except:
	pythonVer = 2


if pythonVer == 2:
	from httplib import HTTPException
	from urllib2 import build_opener, HTTPError, URLError
else:  # python3
	from http.client import HTTPException
	from urllib.error import HTTPError, URLError
	from urllib.request import build_opener


try:
	from urlparse import urlparse
except:
	from urllib.parse import urlparse


# Used to check server validity
HDD_EPG_DAT = '/hdd/epg.dat'
date_format = "%Y-%m-%d"
now = datetime.now()
alloweddelta = 2
CheckFile = "LastUpdate.txt"
ServerStatusList = {}
PARSERS = {'xmltv': 'gen_xmltv', 'genxmltv': 'gen_xmltv'}
sslverify = False
try:
	from twisted.internet._sslverify import ClientTLSOptions
	from twisted.internet import ssl
	sslverify = True
except:
	sslverify = False

if sslverify:

	class SNIFactory(ssl.ClientContextFactory):
		def __init__(self, hostname=None):
			self.hostname = hostname
			# self.hostname = urlparse(hostname).hostname

		def getContext(self):
			ctx = self._contextFactory(self.method)
			if self.hostname:
				ClientTLSOptions(self.hostname, ctx)
			return ctx


def getMountPoints():
	mount_points = []
	try:
		from os import access, W_OK
		with open('/proc/mounts', 'r') as mounts:
			for line in mounts:
				parts = line.split()
				mount_point = parts[1]
				if ismount(mount_point) and access(mount_point, W_OK):
					mount_points.append(mount_point)
	except Exception as e:
		print("[EPGImport] Error reading /proc/mounts:", e)
	return mount_points


mount_points = getMountPoints()
mount_point = None
for mp in mount_points:
	epg_path = join(mp, 'epg.dat')
	if exists(epg_path):
		mount_point = epg_path
		break


if config.misc.epgcache_filename.value:
	HDD_EPG_DAT = config.misc.epgcache_filename.value
else:
	config.misc.epgcache_filename.setValue(HDD_EPG_DAT)


def relImport(name):
	fullname = __name__.split('.')
	fullname[-1] = name
	mod = __import__('.'.join(fullname))
	for n in fullname[1:]:
		mod = getattr(mod, n)
	return mod


def getParser(name):
	module = PARSERS.get(name, name)
	mod = relImport(module)
	return mod.new()


def getTimeFromHourAndMinutes(hour, minute):
	# Check if the hour and minute are within valid ranges
	if not (0 <= hour < 24):
		raise ValueError("Hour must be between 0 and 23")
	if not (0 <= minute < 60):
		raise ValueError("Minute must be between 0 and 59")

	# Get the current local time
	now = time.localtime()

	# Calculate the timestamp for the specified time (today with the given hour and minute)
	begin = int(time.mktime((
		now.tm_year,     # Current year
		now.tm_mon,      # Current month
		now.tm_mday,     # Current day
		hour,            # Specified hour
		minute,          # Specified minute
		0,               # Seconds (set to 0)
		now.tm_wday,     # Day of the week
		now.tm_yday,     # Day of the year
		now.tm_isdst     # Daylight saving time (DST)
	)))
	return begin


def bigStorage(minFree, default, *candidates):
	try:
		diskstat = statvfs(default)
		free = diskstat.f_bfree * diskstat.f_bsize
		if (free > minFree) and (free > 50000000):
			return default
	except Exception as e:
		print("[EPGImport][bigStorage] Failed to stat %s:" % default, str(e))

	# mountpoints = getMountPoints()
	with open('/proc/mounts', 'rb') as f:
		# format: device mountpoint fstype options #
		mountpoints = [x.decode().split(' ', 2)[1] for x in f.readlines()]

	for candidate in candidates:
		if candidate in mountpoints:
			try:
				diskstat = statvfs(candidate)
				free = diskstat.f_bfree * diskstat.f_bsize
				if free > minFree:
					return candidate
			except Exception as e:
				print("[EPGImport][bigStorage] Failed to stat", str(e))
				continue
	return default


class OudeisImporter:
	"""Wrapper to convert original patch to new one that accepts multiple services"""

	def __init__(self, epgcache):
		self.epgcache = epgcache

	# difference with old patch is that services is a list or tuple, this
	# wrapper works around it.

	def importEvents(self, services, events):
		for service in services:
			try:
				self.epgcache.importEvent(service, events)
			except Exception as e:
				import traceback
				traceback.print_exc()
				print("[EPGImport][OudeisImporter][importEvents] ### importEvents exception:", str(e))


def unlink_if_exists(filename):
	try:
		unlink(filename)
	except Exception as e:
		print("[EPGImport] warning: Could not remove '%s' intermediate" % filename, repr(e))


class EPGImport:
	"""Simple Class to import EPGData"""

	def __init__(self, epgcache, channelFilter):
		self.eventCount = None
		self.epgcache = None
		self.storage = None
		self.sources = []
		self.source = None
		self.epgsource = None
		self.fd = None
		self.iterator = None
		self.onDone = None
		self.epgcache = epgcache
		self.channelFilter = channelFilter
		return

	def checkValidServer(self, serverurl):
		print("[EPGImport][checkValidServer]serverurl %s" % serverurl)
		dirname, filename = split(serverurl)
		FullString = dirname + '/' + CheckFile
		req = build_opener()
		req.addheaders = [('User-Agent', 'Twisted Client')]
		dlderror = 0
		if dirname in ServerStatusList:
			# If server is know return its status immediately
			return ServerStatusList[dirname]
		else:
			# Server not in the list so checking it
			try:
				response = req.open(FullString)
			except HTTPError as e:
				print('[EPGImport][checkValidServer] HTTPError in checkValidServer= ' + str(e.code))
				dlderror = 1
			except URLError as e:
				print('[EPGImport][checkValidServer] URLError in checkValidServer= ' + str(e.reason))
				dlderror = 1
			except HTTPException as e:
				print('[EPGImport][checkValidServer] HTTPException in checkValidServer', str(e))
				dlderror = 1
			except Exception:
				print('[EPGImport][checkValidServer] Generic exception in checkValidServer')
				dlderror = 1

		if not dlderror:
			LastTime = response.read().strip('\n')
			if isinstance(LastTime, bytes):
				LastTime = LastTime.decode("utf-8", "ignore").strip('\n')  # Decodifica i bytes in stringa
			try:
				FileDate = datetime.strptime(LastTime, date_format)
			except ValueError:
				print("[EPGImport] checkValidServer wrong date format in file rejecting server %s" % dirname)
				ServerStatusList[dirname] = 0
				response.close()
				return ServerStatusList[dirname]

			delta = (now - FileDate).days
			if delta <= alloweddelta:
				# OK the delta is in the foreseen windows
				ServerStatusList[dirname] = 1
			else:
				# Sorry the delta is higher removing this site
				log.write("[EPGImport] checkValidServer rejected server delta days too high: " + dirname + '\n')
				ServerStatusList[dirname] = 0
				response.close()
				return ServerStatusList[dirname]
		else:
			# We need to exclude this server
			log.write("[EPGImport] checkValidServer rejected server download error for: " + dirname + '\n')
			ServerStatusList[dirname] = 0
		return ServerStatusList[dirname]

	def beginImport(self, longDescUntil=None):
		"""Starts importing using Enigma reactor. Set self.sources before calling this."""
		if hasattr(self.epgcache, 'importEvents'):
			# print('[EPGImport][beginImport] using importEvents.')
			self.storage = self.epgcache
		elif hasattr(self.epgcache, 'importEvent'):
			# print('[EPGImport][beginImport] using importEvent(Oudis).')
			self.storage = OudeisImporter(self.epgcache)
			self.saveEPGCache()  # lululla
		else:
			print('[EPGImport][beginImport] oudeis patch not detected, using using epgdat_importer.epgdatclass/epg.dat instead.')
			from . import epgdat_importer
			self.storage = epgdat_importer.epgdatclass()
		self.eventCount = 0
		if longDescUntil is None:
			# default to 7 days ahead
			self.longDescUntil = time.time() + 24 * 3600 * 7
		else:
			self.longDescUntil = longDescUntil
		self.nextImport()
		return

	def nextImport(self):
		self.closeReader()
		if not self.sources:
			self.closeImport()
			return
		self.source = self.sources.pop()
		self.fetchUrl(self.source.url)

	def fetchUrl(self, filename):
		if isinstance(filename, list):
			if len(filename) > 0:
				filename = filename[0]
			else:
				self.downloadFail("Empty list of alternative URLs", None)
				return

		if filename.startswith('http:') or filename.startswith('https:') or filename.startswith('ftp:'):
			self.urlDownload(filename, self.afterDownload, self.downloadFail)
		else:
			self.afterDownload(None, filename, deleteFile=False)
		return

	def urlDownload(self, sourcefile, afterDownload, downloadFail):
		path = bigStorage(9000000, '/hdd', *mount_points)
		if not path or not isdir(path):
			print("[EPGImport] Invalid path, using '/tmp'")
			path = '/tmp'  # Use fallback /tmp if invalid path, using.
		if "meia" in path:  # mistake ("media != meia)
			path = path.replace("meia", "media")
		filename = join(path, 'epgimport')
		ext = splitext(sourcefile)[1]
		if ext and len(ext) < 6:
			filename += ext.decode("utf-8", "ignore") if isinstance(ext, bytes) else ext
		sourcefile = str(sourcefile)

		print("[EPGImport][urlDownload] Downloading: " + str(sourcefile) + " to local path: " + str(filename))

		ip6 = sourcefile6 = None
		if has_ipv6 and version_info >= (2, 7, 11) and ((version.major == 15 and version.minor >= 5) or version.major >= 16):
			host = sourcefile.split('/')[2]
			# getaddrinfo throws exception on literal IPv4 addresses
			try:
				ip6 = getaddrinfo(host, 0, AF_INET6)
				sourcefile6 = sourcefile.replace(host, '[' + list(ip6)[0][4][0] + ']')
			except Exception as e:
				# print(str(e))
				pass

		if ip6:
			print("[EPGImport][urlDownload] Trying IPv6 first: " + str(sourcefile6))
			if pythonVer == 3:
				sourcefile6 = sourcefile6.encode()
			downloadPage(sourcefile6, filename, headers={'host': host}).addCallback(afterDownload, filename, True).addErrback(self.legacyDownload, afterDownload, downloadFail, sourcefile, filename, True)

		else:
			print("[EPGImport][urlDownload] No IPv6, using IPv4 directly: " + str(sourcefile))
			if sourcefile.startswith("https") and sslverify:
				parsed_uri = urlparse(sourcefile)
				domain = parsed_uri.hostname

				# check for redirects
				try:
					import requests
					r = requests.get(sourcefile, stream=True, timeout=10, verify=False, allow_redirects=True)
					newurl = r.url
					domain = urlparse(newurl).hostname
					newurl = str(newurl)

				except Exception as e:
					print("[EPGImport][urlDownload] Errore durante il controllo dei redirect: " + e)

				sniFactory = SNIFactory(domain)
				if pythonVer == 3:
					newurl = newurl.encode()

				downloadPage(newurl, filename, sniFactory).addCallbacks(afterDownload, downloadFail, callbackArgs=(filename, True))
			else:
				if pythonVer == 3:
					sourcefile = sourcefile.encode()
				downloadPage(sourcefile, filename).addCallbacks(afterDownload, downloadFail, callbackArgs=(filename, True))
		return filename

	def afterDownload(self, result, filename, deleteFile=False):
		print("[EPGImport][afterDownload]filename", filename)
		if not exists(filename):
			self.downloadFail("File not exists")
			return
		try:
			if not getsize(filename):
				raise Exception("[EPGImport][afterDownload] File is empty")
		except Exception as e:
			self.downloadFail(e)
			return

		if self.source.parser == 'epg.dat':
			if twisted.python.runtime.platform.supportsThreads():
				print("[EPGImport][afterDownload] Using twisted thread for DAT file")
				threads.deferToThread(self.readEpgDatFile, filename, deleteFile).addCallback(lambda ignore: self.nextImport())
			else:
				self.readEpgDatFile(filename, deleteFile)
				return

		if filename.endswith('.gz'):
			self.fd = gzip.open(filename, 'rb')
			try:
				self.fd.read(10)
				self.fd.seek(0, 0)
			except Exception as e:
				print("[EPGImport][afterDownload] File downloaded is not a valid gzip file %s" % filename)
				unlink_if_exists(filename)
				self.downloadFail(e)
				return

		elif filename.endswith('.xz') or filename.endswith('.lzma'):
			try:
				import lzma
			except ImportError:
				from backports import lzma
			self.fd = lzma.open(filename, 'rb')
			try:
				self.fd.read(10)
				self.fd.seek(0, 0)
			except Exception as e:
				print("[EPGImport][afterDownload] File downloaded is not a valid xz file", filename)
				try:
					print("[EPGImport][afterDownload] unlink", filename)
					unlink_if_exists(filename)
				except Exception as e:
					print("[EPGImport][afterDownload] warning: Could not remove '%s' intermediate" % filename, str(e))
				self.downloadFail(e)
				return

		else:
			self.fd = open(filename, 'rb')

		if deleteFile and self.source.parser != 'epg.dat':
			try:
				print("[EPGImport][afterDownload] unlink", filename)
				unlink_if_exists(filename)
			except Exception as e:
				print("[EPGImport][afterDownload] warning: Could not remove '%s' intermediate" % filename, str(e))

		self.channelFiles = self.source.channels.downloadables()
		if not self.channelFiles:
			self.afterChannelDownload(None, None)
		else:
			filename = random.choice(self.channelFiles)
			self.channelFiles.remove(filename)
			self.urlDownload(filename, self.afterChannelDownload, self.channelDownloadFail)
		return

	def downloadFail(self, failure):
		# log.write("[EPGImport][downloadFail] download failed:" + failure + '\n')
		if self.source.url in self.source.urls:
			self.source.urls.remove(self.source.url)
		self.source.urls.remove(self.source.url)
		if self.source.urls:
			print("[EPGImport][downloadFail] Attempting alternative URL")
			self.source.url = random.choice(self.source.urls)
			self.fetchUrl(self.source.url)
		else:
			self.nextImport()

	def afterChannelDownload(self, result, filename, deleteFile=True):
		print("[EPGImport][afterChannelDownload] filename", filename)
		if filename:
			try:
				if not getsize(filename):
					raise Exception("File is empty")
			except Exception as e:
				print("[EPGImport][afterChannelDownload] Exception filename", filename)
				self.channelDownloadFail(e)
				return

		if twisted.python.runtime.platform.supportsThreads():
			print("[EPGImport][afterChannelDownload] Using twisted thread")
			threads.deferToThread(self.doThreadRead, filename).addCallback(lambda ignore: self.nextImport())
			deleteFile = False  # Thread will delete it
		else:
			self.iterator = self.createIterator(filename)
			reactor.addReader(self)

		if deleteFile and filename:
			try:
				unlink_if_exists(filename)
			except Exception as e:
				print("[EPGImport][afterChannelDownload] warning: Could not remove '%s' intermediate" % filename, str(e))

	def channelDownloadFail(self, failure):
		log.write("[EPGImport][channelDownloadFail]download channel failed:" + failure + '\n')
		if self.channelFiles:
			filename = random.choice(self.channelFiles)
			if filename in self.channelFiles:
				self.channelFiles.remove(filename)
			print("[EPGImport][channelDownloadFail] File not in list, skipping remove:", filename)
			self.urlDownload(filename, self.afterChannelDownload, self.channelDownloadFail)
		else:
			log.write("[EPGImport][channelDownloadFail]no more alternatives for channels" + '\n')
			self.nextImport()

	def createIterator(self, filename):
		self.source.channels.update(self.channelFilter, filename)
		return getParser(self.source.parser).iterator(self.fd, self.source.channels.items)

	def readEpgDatFile(self, filename, deleteFile=False):
		if not hasattr(self.epgcache, 'load'):
			print("[EPGImport][readEpgDatFile]Cannot load EPG.DAT files on unpatched enigma. Need CrossEPG patch.")
			return

		unlink_if_exists(HDD_EPG_DAT)

		try:
			if filename.endswith('.gz'):
				print("[EPGImport][readEpgDatFile] Uncompressing", filename)
				import shutil
				fd = gzip.open(filename, 'rb')
				epgdat = open(HDD_EPG_DAT, 'wb')
				shutil.copyfileobj(fd, epgdat)
				del fd
				epgdat.close()
				del epgdat

			elif filename != HDD_EPG_DAT:
				symlink(filename, HDD_EPG_DAT)

			print("[EPGImport][readEpgDatFile] Importing", HDD_EPG_DAT)
			self.epgcache.load()

			if deleteFile:
				unlink_if_exists(filename)
		except Exception as e:
			print("[EPGImport][readEpgDatFile] Failed to import %s:%s" % (filename, str(e)))

	def fileno(self):
		if self.fd is not None:
			return self.fd.fileno()
		else:
			return

	def doThreadRead(self, filename):
		"""This is used on PLi with threading"""
		for data in self.createIterator(filename):
			if data is not None:
				self.eventCount += 1
				r, d = data
				if d[0] > self.longDescUntil:
					# Remove long description (save RAM memory)
					d = d[:4] + ('',) + d[5:]
				try:
					self.storage.importEvents(r, (d,))
				except Exception as e:
					print("[EPGImport][doThreadRead] ### importEvents exception:", str(e))

		print("[EPGImport][doThreadRead] ### thread is ready ### Events:", self.eventCount)
		if filename:
			try:
				unlink_if_exists(filename)
			except Exception as e:
				print("[EPGImport][doThreadRead] warning: Could not remove '%s' intermediate" % filename, str(e))

		return

	def doRead(self):
		"""called from reactor to read some data"""
		try:
			data = next(self.iterator)
			if data is not None:
				self.eventCount += 1
				try:
					r, d = data
					if d[0] > self.longDescUntil:
						# Remove long description (save RAM memory)
						d = d[:4] + ('',) + d[5:]
					self.storage.importEvents(r, (d,))
				except Exception as e:
					print("[EPGImport][doRead] importEvents exception:", str(e))

		except StopIteration:
			self.nextImport()

		return

	def connectionLost(self, failure):
		"""called from reactor on lost connection"""
		# This happens because enigma calls us after removeReader
		print("[EPGImport][connectionLost]", failure)

	def closeReader(self):
		if self.fd is not None:
			reactor.removeReader(self)
			self.fd.close()
			self.fd = None
			self.iterator = None
		return

	def closeImport(self):
		self.closeReader()
		self.iterator = None
		self.source = None
		if hasattr(self.storage, 'epgfile'):
			needLoad = self.storage.epgfile
		else:
			needLoad = None

		self.storage = None

		if self.eventCount is not None:
			print("[EPGImport] imported %d events" % self.eventCount)
			reboot = False
			if self.eventCount:
				if needLoad:
					log.write("[EPGImport] no Oudeis patch, load(%s) required" % needLoad + '\n')
					reboot = True
					try:
						if hasattr(self.epgcache, 'load'):
							log.write("[EPGImport] attempt load() patch" + '\n')
							if needLoad != HDD_EPG_DAT:
								symlink(needLoad, HDD_EPG_DAT)
							self.epgcache.load()
							reboot = False
							unlink_if_exists(needLoad)
					except Exception as e:
						log.write("[EPGImport] load() failed:" + str(e) + '\n')

				elif hasattr(self.epgcache, 'save'):
					self.epgcache.save()
			elif hasattr(self.epgcache, 'timeUpdated'):
				self.epgcache.timeUpdated()

			if self.onDone:
				self.onDone(reboot=reboot, epgfile=needLoad)

		self.eventCount = None
		log.write("[EPGImport] #### Finished ####" + '\n')
		return

	def isImportRunning(self):
		return self.source is not None

	def legacyDownload(self, result, afterDownload, downloadFail, sourcefile, filename, deleteFile=True):
		print("[EPGImport] IPv6 download failed, falling back to IPv4: " + str(sourcefile))
		if sourcefile.startswith("https") and sslverify:
			parsed_uri = urlparse(sourcefile)
			domain = parsed_uri.hostname

			# check for redirects
			try:
				import requests
				r = requests.get(sourcefile, stream=True, timeout=10, verify=False, allow_redirects=True)
				newurl = r.url
				domain = urlparse(newurl).hostname
				newurl = str(newurl)

			except Exception as e:
				print(e)

			sniFactory = SNIFactory(domain)

			if pythonVer == 3:
				newurl = newurl.encode()

			downloadPage(newurl, filename, sniFactory).addCallbacks(afterDownload, downloadFail, callbackArgs=(filename, True))
		else:
			if pythonVer == 3:
				sourcefile = sourcefile.encode()
			downloadPage(sourcefile, filename).addCallbacks(afterDownload, downloadFail, callbackArgs=(filename, True))
