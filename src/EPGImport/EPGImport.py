#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import print_function
# This file no longer has a direct link to Enigma2, allowing its use anywhere
# you can supply a similar interface. See plugin.py and OfflineImport.py for
# the contract.
#
# The code is completely modified By Lululla
# The code is modified by iet5 Date Nov 2025
#
# ===============================
# Standard Library
# ===============================
import gzip
from datetime import datetime
from os import statvfs, symlink, unlink
from os.path import exists, getsize, join, split, splitext
from random import choice
from shutil import copy2, copyfileobj
from socket import AF_INET6, getaddrinfo, has_ipv6
from sys import version_info
from time import localtime, mktime, time

# ===============================
# Enigma2 / Components
# ===============================
from Components.config import config

# ===============================
# Third-party Libraries
# ===============================
from requests import Session
from requests.exceptions import HTTPError, RequestException

# ===============================
# Twisted Framework
# ===============================
import twisted.python.runtime
from twisted import version
from twisted.internet import reactor, ssl, threads
from twisted.internet.defer import setDebugging
from twisted.web.client import (
    Agent,
    BrowserLikeRedirectAgent,
    HTTPConnectionPool,
    downloadPage,
    readBody,
)
from twisted.web.http_headers import Headers

# ===============================
# lzma support (fallback for old systems)
# ===============================
try:
    import lzma
except ImportError:
    from backports import lzma

# ===============================
# Local project imports
# ===============================
from . import log
from .EPGConfig import PY3

# Possible paths for EPG files (uses first .dat path as default)
EPG_PATHS = ["/etc/enigma2/epg.db", "/etc/enigma2/epg.dat", "/hdd/epg.dat"]
HDD_EPG_DAT = EPG_PATHS[0]  # Use standard path first

unicode = str
basestring = str
HDD_EPG_DAT = "/hdd/epg.dat"
PARSERS = {"xmltv": "gen_xmltv", "genxmltv": "gen_xmltv"}

if config.misc.epgcache_filename.value:
    HDD_EPG_DAT = config.misc.epgcache_filename.value
else:
    config.misc.epgcache_filename.setValue(HDD_EPG_DAT)


def threadGetPage(url=None, file=None, urlheaders=None, success=None, fail=None, *args, **kwargs):
    # print("[EPGImport][threadGetPage] url, file, args, kwargs", url, "    ", file, "    ", args, "    ", kwargs)
    try:
        s = Session()
        s.headers = {}
        # Use streaming download for large files
        response = s.get(url, verify=False, headers=urlheaders, timeout=60, allow_redirects=True, stream=True)
        response.raise_for_status()

        # Check content-disposition header to extract actual filename
        content_disp = response.headers.get("Content-Disposition", "")
        filename = content_disp.split('filename="')[-1].split('"')[0]
        ext = splitext(file)[1]
        if filename:
            ext = splitext(filename)[1]
            if ext and len(ext) < 6:
                file += ext
        if not ext:
            ext = splitext(response.url)[1]
            if ext and len(ext) < 6:
                file += ext

        # Progressive download for large files
        total_size = int(response.headers.get('content-length', 0))
        downloaded_size = 0
        block_size = 8192  # 8KB chunks

        with open(file, "wb") as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:  # filter out keep-alive chunks
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    # Print progress (optional)
                    if total_size > 0:
                        percent = (downloaded_size / total_size) * 100
                        if percent % 10 == 0:  # Print every 10% to avoid spam
                            print("[EPGImport] Download progress: %.1f%%" % percent)

        print("[EPGImport][threadGetPage] File completed: %s, Size: %d bytes" % (file, downloaded_size))
        success(file, deleteFile=True)

    except HTTPError as httperror:
        print("[EPGImport][threadGetPage] HTTP error: %s" % httperror)
        fail(httperror)

    except RequestException as error:
        print("[EPGImport][threadGetPage] Request error: %s" % error)
        # if fail is not None:
        fail(error)

    except Exception as error:
        print("[EPGImport][threadGetPage] General error: %s" % error)
        fail(error)


# SSL Verification Support
try:
    from twisted.internet import _sslverify
except ImportError:
    _sslverify = None

# HTTPS Context Factory Compatibility
try:
    from twisted.web.client import BrowserLikePolicyForHTTPS as IgnoreHTTPSContextFactory
except ImportError:
    # for twisted < 14 backward compatibility
    from twisted.web.client import WebClientContextFactory as IgnoreHTTPSContextFactory

# Python 2 vs 3 Compatibility Handling
if version_info[0] == 3:
    # Python 3
    import urllib.request as urllib2
    import http.client as httplib
    unicode = str
    basestring = str
else:
    # Python 2
    import urllib2
    import httplib
    # unicode and basestring are built-ins in Py2


# Check for DreamOS
try:
    from enigma import cachestate
    isDreambox = True
except ImportError:
    isDreambox = False


class IgnoreHTTPS(IgnoreHTTPSContextFactory):
    def creatorForNetloc(self, hostname, port):
        options = ssl.CertificateOptions(verify=False)
        if _sslverify:
            return _sslverify.ClientTLSOptions(hostname if PY3 else hostname.encode('utf-8'), options.getContext())
        else:
            # Fallback for older Twisted versions
            return options.getContext()


setDebugging(False)
ISO639_associations = {}

# Use a persistent connection pool.
pool = HTTPConnectionPool(reactor, persistent=True)
pool.maxPersistentPerHost = 1
pool.cachedConnectionTimeout = 600
agent = BrowserLikeRedirectAgent(Agent(reactor, pool=pool, contextFactory=IgnoreHTTPS()))
headers = Headers({'User-Agent': ['Mozilla/5.0 (SmartHub; SMART-TV; U; Linux/SmartTV; Maple2012) AppleWebKit/534.7 (KHTML, like Gecko) SmartTV Safari/534.7']})

# Used to check server validity
date_format = "%Y-%m-%d"
now = datetime.now()
alloweddelta = 2
CheckFile = "LastUpdate.txt"
ServerStatusList = {}

# ISO639 language associations for DreamOS
ISO639_associations = {
    'ar': 'ara', 'bg': 'bul', 'ca': 'cat', 'cs': 'ces', 'da': 'dan',
    'de': 'deu', 'el': 'ell', 'en': 'eng', 'es': 'spa', 'et': 'est',
    'fi': 'fin', 'fr': 'fra', 'he': 'heb', 'hr': 'hrv', 'hu': 'hun',
    'it': 'ita', 'ja': 'jpn', 'ko': 'kor', 'lt': 'lit', 'lv': 'lav',
    'nl': 'nld', 'no': 'nor', 'pl': 'pol', 'pt': 'por', 'ro': 'ron',
    'ru': 'rus', 'sk': 'slk', 'sl': 'slv', 'sr': 'srp', 'sv': 'swe',
    'th': 'tha', 'tr': 'tur', 'uk': 'ukr', 'zh': 'zho'
}


def getISO639(text):
    try:
        decoded_text = text.decode('UTF-8')
    except:
        decoded_text = text

    for line in decoded_text.split('\n'):
        parts = line.split('|')
        if len(parts) > 2 and parts[2]:
            ISO639_associations[parts[2]] = parts[0]


def completed(passthrough):
    if timeoutCall.active():
        timeoutCall.cancel()
    return passthrough


def doRead(response):
    d = readBody(response)
    d.addCallback(getISO639)


# Load ISO639 language codes
# Note: Using explicit bytes for URL as preferred by Twisted Agent
d = agent.request(b'GET', b'http://loc.gov/standards/iso639-2/ISO-639-2_utf-8.txt', headers, None)
d.addCallback(doRead).addErrback(lambda e: print("[EPGImport] Failed to load ISO639 codes: %s" % e))
# Set a 3 min timeout for all requests. If unsuccessfull then call the errback
timeoutCall = reactor.callLater(3 * 60, d.cancel)
d.addBoth(completed)


def relImport(name):
    fullname = __name__.split(".")
    fullname[-1] = name
    mod = __import__(".".join(fullname))
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
    now = localtime()

    # Calculate the timestamp for the specified time (today with the given hour and minute)
    begin = int(mktime((
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
    """
    Find storage with enough free space
    Returns the first candidate with at least minFree bytes free
    """
    try:
        diskstat = statvfs(default)
        free = diskstat.f_bfree * diskstat.f_bsize
        if (free > minFree) and (free > 50000000):
            return default
    except Exception as e:
        print("[EPGImport] Failed to stat %s:" % default, e, file=log)

    # Safe read of mounts for Py3
    try:
        with open('/proc/mounts', 'rb') as f:
            mounts = f.readlines()
    except:
        mounts = []

    # format: device mountpoint fstype options #
    mountpoints = []
    for x in mounts:
        try:
            line = x.decode('utf-8')
        except:
            line = x
        parts = line.split(' ', 2)
        if len(parts) > 1:
            mountpoints.append(parts[1])

    for candidate in candidates:
        if candidate in mountpoints:
            try:
                diskstat = statvfs(candidate)
                free = diskstat.f_bfree * diskstat.f_bsize
                if free > minFree:
                    return candidate
            except:
                pass
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
    """Safely remove file if it exists"""
    if filename.endswith("epg.db"):
        return

    try:
        unlink(filename)
    except Exception as e:
        print("[EPGImport] warning: Could not remove '%s' intermediate" % filename, repr(e))


def safe_lzma_open(filename, mode='rb'):
    """Safely open LZMA files with error handling"""
    try:
        if lzma is None:
            raise ImportError("lzma module is not available")

        fd = lzma.open(filename, mode)

        # Test file integrity
        try:
            current_pos = fd.tell()
            # test_data = fd.read(100)
            fd.seek(current_pos)  # Return to previous position
            return fd
        except Exception as test_error:
            fd.close()
            raise Exception("LZMA file test failed: %s" % test_error)

    except lzma.LZMAError as e:
        raise Exception("LZMA decompression error: %s" % e)
    except Exception as e:
        raise Exception("Error opening LZMA file: %s" % e)


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
        self.startTime = None
        self.epgcache = epgcache
        self.channelFilter = channelFilter
        self.cacheState_conn = None

    def checkValidServer(self, serverurl):
        """Check if server has updated EPG data recently"""
        dirname, filename = split(serverurl)
        FullString = dirname + "/" + CheckFile
        req = urllib2.build_opener()
        req.addheaders = [('User-Agent', 'Twisted Client')]
        dlderror = 0
        if dirname in ServerStatusList:
            # If server is known return its status immediately
            return ServerStatusList[dirname]
        else:
            # Server not in the list so checking it
            try:
                response = req.open(FullString, timeout=10)
            except urllib2.HTTPError as e:
                print('[EPGImport] HTTPError in checkValidServer= ' + str(e.code))
                dlderror = 1
            except urllib2.URLError as e:
                print('[EPGImport] URLError in checkValidServer= ' + str(e.reason))
                dlderror = 1
            except httplib.HTTPException as e:
                print('[EPGImport] HTTPException in checkValidServer' + str(e))
                dlderror = 1
            except Exception:
                import traceback
                print('[EPGImport] Generic exception in checkValidServer: ' + traceback.format_exc())
                dlderror = 1

            if not dlderror:
                try:
                    content = response.read()
                    if version_info[0] >= 3:
                        LastTime = content.decode('utf-8').strip('\n')
                    else:
                        LastTime = content.strip('\n')

                    try:
                        FileDate = datetime.strptime(LastTime, date_format)
                    except ValueError:
                        print("[EPGImport] checkValidServer wrong date format in file rejecting server %s" % dirname, file=log)
                        ServerStatusList[dirname] = 0
                        return ServerStatusList[dirname]

                    delta = (now - FileDate).days
                    if delta <= alloweddelta:
                        # OK the delta is in the foreseen windows
                        ServerStatusList[dirname] = 1
                    else:
                        # Sorry the delta is higher removing this site
                        print("[EPGImport] checkValidServer rejected server delta days too high: %s" % dirname, file=log)
                        ServerStatusList[dirname] = 0
                except Exception as e:
                    print("[EPGImport] checkValidServer failed during read/parse:", e)
                    ServerStatusList[dirname] = 0
            else:
                # We need to exclude this server
                print("[EPGImport] checkValidServer rejected server download error for: %s" % dirname, file=log)
                ServerStatusList[dirname] = 0
        return ServerStatusList[dirname]

    def cacheStateChanged(self, state):
        """Handle EPG cache state changes"""
        # started, stopped, aborted, deferred, load_finished, save_finished
        if state.state == cachestate.save_finished:
            print("[EPGImport] EPGCache save finished")
            self.startImport()
        elif state.state == cachestate.load_finished:
            print("[EPGImport] EPGCache load finished")
            print("[EPGImport] #### Finished ####")
            del self.cacheState_conn

    def saveEPGCache(self):
        """Save EPG cache to file"""
        if isDreambox:
            self.cacheState_conn = self.epgcache.cacheState.connect(self.cacheStateChanged)
        print("[EPGImport] Save the EPG cache to database file %s ..." % config.misc.epgcache_filename.value)
        self.epgcache.save()

    def beginImport(self, longDescUntil=None):
        """Starts importing using Enigma reactor. Set self.sources before calling this."""
        if hasattr(self.epgcache, "importEvents"):
            print("[EPGImport][beginImport] using importEvents.")
            self.storage = self.epgcache
        elif hasattr(self.epgcache, "importEvent"):
            print("[EPGImport][beginImport] using importEvent(Oudis).")
            self.storage = OudeisImporter(self.epgcache)
        else:
            print("[EPGImport][beginImport] oudeis patch not detected, using using epgdat_importer.epgdatclass/epg.dat instead.")
            try:
                from . import epgdat_importer
                self.storage = epgdat_importer.epgdatclass()
            except ImportError as e:
                print("[EPGImport] Failed to import epgdat_importer:", e)
                self.storage = None

        self.eventCount = 0
        if longDescUntil is None:
            # default to 7 days ahead
            self.longDescUntil = time() + 24 * 3600 * 7
        else:
            self.longDescUntil = longDescUntil

        self.startTime = datetime.now()
        self.nextImport()
        return

    def startImport(self):
        """Start the import process"""
        self.eventCount = 0
        self.startTime = datetime.now()
        self.nextImport()

    def nextImport(self):
        """Process next import source"""
        self.closeReader()
        if not self.sources:
            self.closeImport()
            return

        self.source = self.sources.pop()
        print("[EPGImport] nextImport, source=", self.source.description, file=log)
        self.fetchUrl(self.source.url)

    def fetchUrl(self, filename):
        """Fetch URL or local file"""
        if filename.startswith('http:') or filename.startswith('ftp:'):
            self.do_download(filename, self.afterDownload, self.downloadFail)
        else:
            self.afterDownload(None, filename, deleteFile=False)

    def getContent(self, response, *args):
        if response.code != 200:
            raise Exception("Invalid server response code received: %s" % response.code)

        d = readBody(response)
        d.addCallback(self.writeFile if len(args) < 4 else self.checkValidServer, *args)
        d.addErrback(lambda e: args[-1](repr(e)))
        return d

    def writeFile(self, data, filename, afterDownload, downloadFail):
        try:
            with open(filename, 'wb') as fd:
                fd.write(data)
        except Exception as e:
            raise Exception("unable write data to %s: %s" % (filename, repr(e)))
        else:
            afterDownload(None, filename, True)

    def do_download(self, sourcefile, afterDownload, downloadFail):
        """Download file from source"""
        path = bigStorage(9000000, '/tmp', '/media/DOMExtender', '/media/cf', '/media/mmc', '/media/usb', '/media/hdd')
        filename = join(path, 'epgimport')
        ext = splitext(sourcefile)[1]
        # Keep sensible extension, in particular the compression type
        if ext and len(ext) < 6:
            filename += ext

        if version_info[0] >= 3:
            sourcefile = sourcefile
        else:
            # Ensure utf-8 encoding for Py2
            if isinstance(sourcefile, unicode):
                sourcefile = sourcefile.encode('utf-8')

        print("[EPGImport] Downloading: " + sourcefile + " to local path: " + filename, file=log)

        ip6 = None
        sourcefile6 = None

        if has_ipv6 and version_info >= (2, 7, 11) and ((version.major == 15 and version.minor >= 5) or version.major >= 16):
            try:
                host = sourcefile.split("/")[2]
                # getaddrinfo throws exception on literal IPv4 addresses
                try:
                    ip6 = getaddrinfo(host, 0, AF_INET6)
                    sourcefile6 = sourcefile.replace(host, "[" + list(ip6)[0][4][0] + "]")
                except:
                    pass
            except:
                pass

        if ip6 and sourcefile6:
            print("[EPGImport] Trying IPv6 first: " + sourcefile6, file=log)
            downloadPage(sourcefile6, filename, headers={'host': host}).addCallback(afterDownload, filename, True).addErrback(self.legacyDownload, afterDownload, downloadFail, sourcefile, filename, True)
        else:
            print("[EPGImport] No IPv6, using IPv4 directly: " + sourcefile, file=log)
            downloadPage(sourcefile, filename).addCallbacks(afterDownload, downloadFail, callbackArgs=(filename, True))
        return filename

    def afterDownload(self, result, filename, deleteFile=False):
        """Callback after download completion"""
        print("[EPGImport][afterDownload] afterDownload %s" % filename, file=log)

        try:
            # Check file exists and has size
            if not exists(filename):
                raise Exception("[EPGImport][afterDownload] File does not exist: %s" % filename)

            file_size = getsize(filename)
            if not file_size:
                raise Exception("[EPGImport][afterDownload] File is empty")

            print("[EPGImport][afterDownload] File size: %d bytes" % file_size)

        except Exception as e:
            print("[EPGImport][afterDownload] Error: %s" % e)
            self.downloadFail(e)
            return

        print("[EPGImport] File size: %d, testing integrity..." % getsize(filename))
        try:
            with open(filename, 'rb') as f:
                header = f.read(10)
                print("[EPGImport] File header: %s" % repr(header))
        except Exception as e:
            print("[EPGImport] File test failed: %s" % str(e))

        if self.source.parser == 'epg.dat':
            if twisted.python.runtime.platform.supportsThreads():
                print("[EPGImport][afterDownload] Using twisted thread for DAT file", file=log)
                threads.deferToThread(self.readEpgDatFile, filename, deleteFile).addCallback(lambda ignore: self.nextImport())
            else:
                self.readEpgDatFile(filename, deleteFile)
                return

        # Handle compressed files with improved XZ support
        if filename.endswith('.xz') or filename.endswith('.lzma'):
            print("[EPGImport] Processing XZ/LZMA file with enhanced timeout handling...")
            if lzma is None:
                error_msg = "lzma module not available"
                print("[EPGImport][afterDownload] %s" % error_msg, file=log)
                self.downloadFail(Exception(error_msg))
                return

            try:
                # Use safe LZMA file opening
                self.fd = safe_lzma_open(filename, 'rb')
                print("[EPGImport][afterDownload] XZ file successfully opened and validated")

            except Exception as e:
                print("[EPGImport][afterDownload] Failed to process XZ file: %s" % e)
                try:
                    if exists(filename):
                        unlink_if_exists(filename)
                        print("[EPGImport][afterDownload] Removed corrupted file: %s" % filename)
                except:
                    pass
                self.downloadFail(e)
                return

        elif filename.endswith('.gz'):
            self.fd = gzip.open(filename, 'rb')
            try:  # read a bit to make sure it's a gzip file
                self.fd.read(10)
                self.fd.seek(0, 0)
            except Exception as e:
                print("[EPGImport][afterDownload] File downloaded is not a valid gzip file %s" % filename)
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
                print("[EPGImport][afterDownload] unlink", filename, file=log)
                if not filename.endswith("epg.db"):
                    unlink_if_exists(filename)
            except Exception as e:
                print("[EPGImport][afterDownload] warning: Could not remove '%s' intermediate" % filename, e, file=log)

        self.channelFiles = self.source.channels.downloadables()
        if not self.channelFiles:
            self.afterChannelDownload(None, None)
        else:
            filename = choice(self.channelFiles)
            self.channelFiles.remove(filename)
            self.do_download(filename, self.afterChannelDownload, self.channelDownloadFail)
        return

    def downloadFail(self, failure):
        print("[EPGImport] download failed:", failure, file=log)
        if hasattr(self, 'source') and self.source and hasattr(self.source, 'urls'):
            if self.source.url in self.source.urls:
                self.source.urls.remove(self.source.url)
            if self.source.urls:
                print("[EPGImport] Attempting alternative URL", file=log)
                self.source.url = choice(self.source.urls)
                self.fetchUrl(self.source.url)
            else:
                self.nextImport()
        else:
            self.nextImport()

    def afterChannelDownload(self, result, filename, deleteFile=True):
        """Callback after channel download completion"""
        print("[EPGImport] afterChannelDownload", filename, file=log)
        if filename:
            try:
                if not getsize(filename):
                    raise Exception("File is empty")
            except Exception as e:
                print("[EPGImport][afterChannelDownload] Exception filename", filename)
                self.channelDownloadFail(e)
                return

        if twisted.python.runtime.platform.supportsThreads():
            print("[EPGImport][afterChannelDownload] Using twisted thread", file=log)
            threads.deferToThread(self.doThreadRead, filename).addCallback(lambda ignore: self.nextImport())
            deleteFile = False  # Thread will delete it
        else:
            self.iterator = self.createIterator(filename)
            reactor.addReader(self)

        if deleteFile and filename:
            try:
                if not filename.endswith("epg.db"):
                    unlink_if_exists(filename)
            except Exception as e:
                print("[EPGImport][afterChannelDownload] warning: Could not remove '%s' intermediate" % filename, e, file=log)

    def channelDownloadFail(self, failure):
        print("[EPGImport][channelDownloadFail] download channel failed:", failure, file=log)
        if self.channelFiles:
            filename = choice(self.channelFiles)
            self.channelFiles.remove(filename)
            self.do_download(filename, self.afterChannelDownload, self.channelDownloadFail)
        else:
            print("[EPGImport][channelDownloadFail] no more alternatives for channels", file=log)
            self.nextImport()

    def createIterator(self, filename):
        """Create iterator for parsing EPG data with validation"""
        self.source.channels.update(self.channelFilter, filename)
        iterator = getParser(self.source.parser).iterator(self.fd, self.source.channels.items)
        
        # Add data validation wrapper
        def validated_iterator():
            for data in iterator:
                if data and len(data) == 2:  # Must be (channel, event_data)
                    channel_ref, event_data = data
                    # Validate EPG event structure
                    if len(event_data) >= 5:  # Minimum required fields
                        yield data
                    else:
                        print("[EPGImport] Skipping invalid event for " + str(channel_ref) + ": insufficient data fields")
                else:
                    print("[EPGImport] Skipping malformed data: " + str(data))
        
        return validated_iterator()

    # def createIterator(self, filename):
        # """Create iterator for parsing EPG data"""
        # self.source.channels.update(self.channelFilter, filename)
        # return getParser(self.source.parser).iterator(self.fd, self.source.channels.items)

    def readEpgDatFile(self, filename, deleteFile=False):
        """Read and import EPG.DAT file"""
        if not hasattr(self.epgcache, "load"):
            print("[EPGImport][readEpgDatFile] Cannot load EPG.DAT files on unpatched enigma. Need CrossEPG patch.", file=log)
            return

        unlink_if_exists(HDD_EPG_DAT)
        try:
            if filename.endswith('.gz'):
                print("[EPGImport][readEpgDatFile] Uncompressing", filename, file=log)
                fd = gzip.open(filename, 'rb')
                epgdat = open(HDD_EPG_DAT, 'wb')
                copyfileobj(fd, epgdat)
                del fd
                epgdat.close()
                del epgdat
            elif filename != HDD_EPG_DAT:
                try:
                    symlink(filename, HDD_EPG_DAT)
                except:
                    copy2(filename, HDD_EPG_DAT)

            print("[EPGImport][readEpgDatFile] Importing", HDD_EPG_DAT, file=log)
            self.epgcache.load()
            if deleteFile:
                unlink_if_exists(filename)
        except Exception as e:
            print("[EPGImport][readEpgDatFile] Failed to import %s:%s" % (filename, str(e)))

    def fileno(self):
        """Return file descriptor for reactor"""
        if self.fd is not None:
            return self.fd.fileno()
        return -1

    def doThreadRead(self, filename):
        'This is used on PLi with threading'
        for data in self.createIterator(filename):
            if data is not None:
                self.eventCount += 1
                try:
                    r, d = data
                    # FIX: Validate tuple structure before processing
                    if len(d) >= 5:  # Minimum required fields for EPG event
                        if d[0] > self.longDescUntil:
                            # Remove long description (save RAM memory)
                            d = d[:4] + ("",) + d[5:]
                        try:
                            self.storage.importEvents(r, (d,))
                        except Exception as e:
                            print("[EPGImport][doThreadRead] ### importEvents exception:", str(e))
                    else:
                        print("[EPGImport][doThreadRead] ### Invalid data tuple length, skipping event. Data: " + str(len(d)))
                        # Log the problematic data for debugging
                        print("[EPGImport][doThreadRead] ### Channel: " + str(r) + " Data length: " + str(len(d)))
                except ValueError as e:
                    print("[EPGImport][doThreadRead] ### Data unpacking error: " + str(e))
                    print("[EPGImport][doThreadRead] ### Problematic data: " + str(data))
                except Exception as e:
                    print("[EPGImport][doThreadRead] ### General error: " + str(e))
        
        print("[EPGImport][doThreadRead] ### thread is ready ### Events: " + str(self.eventCount))
        
        # Cleanup
        if filename:
            try:
                if not filename.endswith("epg.db"):
                    unlink_if_exists(filename)
            except Exception as e:
                print("[EPGImport][doThreadRead] warning: Could not remove '%s' intermediate" % filename, e, file=log)
        return

    def doRead(self):
        'called from reactor to read some data'
        try:
            # returns tuple (ref, data) or None when nothing available yet.
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
                    print("[EPGImport][doRead] importEvents exception:", e, file=log)
        except StopIteration:
            self.nextImport()
        except Exception as e:
            print("[EPGImport] Error in doRead:", e, file=log)
            self.nextImport()

    def connectionLost(self, failure):
        'called from reactor on lost connection'
        # This happens because enigma calls us after removeReader
        print("[EPGImport][connectionLost]", failure, file=log)

    def closeReader(self):
        if self.fd is not None:
            try:
                reactor.removeReader(self)
            except:
                pass
            self.fd.close()
            self.fd = None
            self.iterator = None
        return

    def closeImport(self):
        """Close import and clean up resources"""
        self.closeReader()
        self.iterator = None
        self.source = None
        if hasattr(self.storage, 'epgfile'):
            needLoad = self.storage.epgfile
        else:
            needLoad = None

        self.storage = None
        if self.eventCount is not None:
            print("[EPGImport] imported %d events" % self.eventCount, file=log)
            reboot = False
            if self.eventCount:
                if needLoad:
                    print("[EPGImport] no Oudeis patch, load(%s) required" % needLoad, file=log)
                    reboot = True
                    try:
                        if hasattr(self.epgcache, 'load'):
                            print("[EPGImport] attempt load() patch", file=log)
                            if needLoad != HDD_EPG_DAT:
                                try:
                                    symlink(needLoad, HDD_EPG_DAT)
                                except:
                                    copy2(needLoad, HDD_EPG_DAT)
                            self.epgcache.load()
                            reboot = False
                            unlink_if_exists(needLoad)
                    except Exception as e:
                        print("[EPGImport] load() failed:", e, file=log)

                elif hasattr(self.epgcache, 'save'):
                    self.epgcache.save()

            elif hasattr(self.epgcache, 'timeUpdated'):
                self.epgcache.timeUpdated()
            if self.onDone:
                self.onDone(reboot=reboot, epgfile=needLoad)
        self.eventCount = None
        print("[EPGImport] #### Finished ####", file=log)

    def isImportRunning(self):
        return self.source is not None

    def legacyDownload(self, result, afterDownload, downloadFail, sourcefile, filename, deleteFile=True):
        print("[EPGImport] IPv6 download failed, falling back to IPv4: " + sourcefile, file=log)
        downloadPage(sourcefile, filename).addCallbacks(afterDownload, downloadFail, callbackArgs=(filename, True))
