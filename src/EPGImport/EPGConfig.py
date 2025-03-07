#!/usr/bin/python
# -*- coding: utf-8 -*-

# from .filterCustomChannel import filterCustomChannel

from os import fstat, listdir, remove
from os.path import exists, getmtime, join, split
from time import time
from xml.etree.cElementTree import iterparse
from zipfile import ZipFile
from collections import defaultdict

from gzip import GzipFile
from random import choice
import re
import sys

try:
    import lzma
except ImportError:
    from backports import lzma


try:
    from html import unescape  # Python 3
except ImportError:
    from HTMLParser import HTMLParser  # Python 2
    unescape = HTMLParser().unescape

PY3 = sys.version_info[0] == 3

try:
    from cPickle import dump, load, HIGHEST_PROTOCOL
except ImportError:
    from pickle import dump, load, HIGHEST_PROTOCOL

# User selection stored here, so it goes into a user settings backup
SETTINGS_FILE = '/etc/enigma2/epgimport.conf'
channelCache = {}

global filterCustomChannel


try:
    basestring
except NameError:
    basestring = str


def isLocalFile(filename):
    # we check on a "://" as a silly way to check local file
    return "://" not in filename


def getChannels(path, name):
    global channelCache
    if name in channelCache:
        return channelCache[name]
    dirname, filename = split(path)
    if name:
        channelfile = join(dirname, name) if isLocalFile(name) else name
    else:
        channelfile = join(dirname, filename.split(".", 1)[0] + ".channels.xml")
    try:
        return channelCache[channelfile]
    except KeyError:
        pass
    c = EPGChannel(channelfile)
    channelCache[channelfile] = c
    return c


def enumerateXML(fp, tag=None):
    """Enumerates ElementTree nodes from file object 'fp'"""
    doc = iterparse(fp, events=('start', 'end'))
    _, root = next(doc)  # Ottiene la radice
    depth = 0

    for event, element in doc:
        if element.tag == tag:
            if event == 'start':
                depth += 1
            elif event == 'end':
                if depth == 1:
                    yield element
                    element.clear()
                depth -= 1

        if event == 'end' and element.tag != tag:
            element.clear()

    root.clear()


def xml_unescape(text):
    """
    Unescapes XML/HTML entities in the given text.

    :param text: The text that needs to be unescaped.
    :type text: str
    :rtype: str
        """

    if not isinstance(text, str if PY3 else basestring):
        return ''

    text = text if PY3 else text.encode('utf-8')
    text = text.strip()

    # Custom entity replacements
    entity_map = {
        "&laquo;": "«",
        "&#171;": "«",
        "&raquo;": "»",
        "&#187;": "»",
        "&apos;": "'",
    }

    # First, apply standard unescape
    text = unescape(text)

    # Replace specific entities
    for entity, char in entity_map.items():
        text = text.replace(entity, char)

    # Normalize whitespace (replace `&#160;`, `&nbsp;`, and multiple spaces with a single space)
    text = re.sub(r'&#160;|&nbsp;|\s+', ' ', text)

    return text


def set_channel_id_filter():
    full_filter = ""
    try:
        with open('/etc/epgimport/channel_id_filter.conf', 'r') as channel_id_file:
            for channel_id_line in channel_id_file:
                # Skipping comments in channel_id_filter.conf
                if not channel_id_line.startswith("#"):
                    clean_channel_id_line = channel_id_line.strip()
                    # Blank line in channel_id_filter.conf will produce a full match so we need to skip them.
                    if clean_channel_id_line:
                        try:
                            # We compile indivually every line just to report error
                            full_filter = re.compile(clean_channel_id_line)
                        except re.error:
                            print("[EPGImport] ERROR: " + clean_channel_id_line + " is not a valid regex. It will be ignored.")
                        else:
                            full_filter = full_filter + clean_channel_id_line + "|"
    except IOError:
        print("[EPGImport]set_channel_id_filter: no channel_id_filter.conf file found.")
        # Return a dummy filter (empty line filter) all accepted except empty channel id
        compiled_filter = re.compile("^$")
        return (compiled_filter)
    # Last char is | so remove it
    full_filter = full_filter[:-1]
    # all channel id are matched in lower case so creating the filter in lowercase too
    full_filter = full_filter.lower()
    # channel_id_filter.conf file exist but is empty, it has only comments, or only invalid regex
    if len(full_filter) == 0:
        # full_filter is empty returning dummy filter
        compiled_filter = re.compile("^$")
    else:
        try:
            compiled_filter = re.compile(full_filter)
        except re.error:
            print("[EPGImport]set_channel_id_filter ERROR: final regex " + full_filter + " doesn't compile properly.")
            # Return a dummy filter  (empty line filter) all accepted except empty channel id
            compiled_filter = re.compile("^$")
        else:
            print("[EPGImport]set_channel_id_filter INFO : final regex " + full_filter + " compiled successfully.")

    return (compiled_filter)


class EPGChannel:
    def __init__(self, filename, urls=None):
        self.mtime = None
        self.name = filename
        self.urls = [filename] if urls is None else urls
        self.items = defaultdict(set)

    def openStream(self, filename):
        fd = open(filename, "rb")
        if not fstat(fd.fileno()).st_size:
            raise Exception("File is empty")
        if filename.endswith(".gz"):
            fd = GzipFile(fileobj=fd, mode="rb")
        elif filename.endswith(".xz") or filename.endswith(".lzma"):
            fd = lzma.open(filename, "rb")
        elif filename.endswith(".zip"):
            from io import BytesIO
            zip_obj = ZipFile(filename, "r")
            fd = BytesIO(zip_obj.open(zip_obj.namelist()[0]).read())
        return fd

    def parse(self, filterCallback, downloadedFile):
        print("[EPGImport]EPGChannel Parsing channels from '%s'" % self.name)
        self.items = defaultdict(set)
        try:
            stream = self.openStream(downloadedFile)
            if stream is None:
                print("[EPGImport] Error: Unable to open stream for downloadedFile", downloadedFile)
                return
            # here is a problem in the List of supported formats by iterparse: crash on file corrupt
            # _lzma.LZMAError: Input format not supported by decoder
            supported_formats = ['.xml', '.xml.gz', '.xml.xz']  # fixed
            # Make sure the file is in a compatible format
            if any(downloadedFile.endswith(ext) for ext in supported_formats):
                context = iterparse(stream)
                for event, elem in context:
                    if elem.tag == "channel":
                        channel_id = elem.get("id").lower()
                        ref = str(elem.text or '').strip()
                        if not channel_id or not ref:
                            continue  # Skip empty values
                        if ref and filterCallback(ref):
                            if channel_id in self.items:
                                self.items[channel_id].append(ref)
                                self.items[channel_id] = list(dict.fromkeys(self.items[channel_id]))  # Ensure uniqueness
                            else:
                                self.items[channel_id] = [ref]
                        elem.clear()
        except Exception as e:
            print("[EPGImport]EPGChannel-parse- failed to parse", downloadedFile, "Error:", e)

    def update(self, filterCallback, downloadedFile=None):
        customFile = "/etc/epgimport/custom.channels.xml"
        # Always read custom file since we don't know when it was last updated
        # and we don't have multiple download from server problem since it is always a local file.
        if not exists(customFile):
            customFile = "/etc/epgimport/rytec.channels.xml"
        if exists(customFile):
            print("[EPGImport] Parsing channels from", customFile)
            self.parse(filterCallback, customFile)
            print("[EPGImport] No customFile for Parsing channels: use rytec.channels.xml '%s'" % customFile)
        if downloadedFile is not None:
            self.mtime = time()
            return self.parse(filterCallback, downloadedFile)
        elif (len(self.urls) == 1) and isLocalFile(self.urls[0]):
            mtime = getmtime(self.urls[0])
            if (not self.mtime) or (self.mtime < mtime):
                self.parse(filterCallback, self.urls[0])
                self.mtime = mtime

    def downloadables(self):
        if (len(self.urls) == 1) and isLocalFile(self.urls[0]):
            return None
        else:
            # Check at most once a day
            now = time()
            if (not self.mtime) or (self.mtime + 86400 < now):
                return self.urls
        return None

    def __repr__(self):
        return "EPGChannel(urls=%s, channels=%s, mtime=%s)" % (self.urls, self.items and len(self.items), self.mtime)


class EPGSource:
    def __init__(self, path, elem, category=None):
        self.parser = elem.get('type', 'gen_xmltv')
        self.nocheck = int(elem.get('nocheck', 0))
        self.urls = [e.text.strip() for e in elem.findall('url')]
        self.url = choice(self.urls)
        self.description = elem.findtext('description')
        self.category = category
        if not self.description:
            self.description = self.url
        self.format = elem.get('format', 'xml')
        self.channels = getChannels(path, elem.get('channels'))


def enumSourcesFile(sourcefile, filter=None, categories=False):
    global channelCache
    category = None
    try:
        with open(sourcefile, "rb") as f:
            for event, elem in iterparse(f, events=("start", "end")):
                if event == "end":
                    if elem.tag == "source":
                        s = EPGSource(sourcefile, elem, category)
                        elem.clear()
                        if filter is None or s.description in filter:
                            yield s

                    elif elem.tag == "channel":
                        name = elem.get("name")
                        if name:
                            urls = [e.text.strip() for e in elem.findall("url")]
                            if name in channelCache:
                                channelCache[name].urls = urls
                            else:
                                channelCache[name] = EPGChannel(name, urls)
                        elem.clear()

                    elif elem.tag == "sourcecat":
                        category = None
                        elem.clear()

                elif event == "start" and elem.tag == "sourcecat":
                    category = elem.get("sourcecatname")
                    if categories:
                        yield category
    except Exception as e:
        print("[EPGConfig] EPGConfig enumSourcesFile:", e)


def enumSources(path, filter=None, categories=False):
    try:
        for sourcefile in listdir(path):
            if sourcefile.endswith(".sources.xml"):
                sourcefile = join(path, sourcefile)
                try:
                    for s in enumSourcesFile(sourcefile, filter, categories):
                        yield s
                except Exception as e:
                    print("[EPGImport] failed to open", sourcefile, "Error:", e)
    except Exception as e:
        print("[EPGImport]enumSources failed to list", path, "Error:", e)


# def loadUserSettings(filename=SETTINGS_FILE):
    # try:
        # with open(filename, 'rb') as f:
            # data = load(f)
        # print("[EPGImport] File loaded with success:", data)

        # if "sources" not in data:
            # print("[EPGImport] Errore: 'sources' missing in data!")
            # return {"sources": []}

        # return data
    # except Exception as e:
        # print("[EPGImport] Errore nel caricamento:", e)


# def storeUserSettings(filename=SETTINGS_FILE, sources=None):
    # if sources is None:
        # sources = []
    # container = {"sources": sources}
    # try:
        # with open(filename, 'wb') as f:
            # dump(container, f, HIGHEST_PROTOCOL)
        # print("[EPGImport] Salvataggio completato:", container)
    # except Exception as e:
        # print("[EPGImport] Errore durante il salvataggio:", e)
        # return {"sources": []}


def loadUserSettings(filename=SETTINGS_FILE):
    try:
        return load(open(filename, 'rb'))
    except Exception as e:
        return {"sources": []}


def storeUserSettings(filename=SETTINGS_FILE, sources=None):
    container = {"sources": sources}
    dump(container, open(filename, 'wb'), HIGHEST_PROTOCOL)


if __name__ == "__main__":
    import sys
    SETTINGS_FILE_PKL = "settings.pkl"
    x = []
    ln = []
    path = "."
    if len(sys.argv) > 1:
        path = sys.argv[1]
    for p in enumSources(path):
        t = (p.description, p.urls, p.parser, p.format, p.channels, p.nocheck)
        ln.append(t)
        print(t)
        x.append(p.description)
    storeUserSettings(SETTINGS_FILE_PKL, [1, "twee"])
    assert loadUserSettings(SETTINGS_FILE_PKL) == {"sources": [1, "twee"]}
    remove(SETTINGS_FILE_PKL)
    for p in enumSources(path, x):
        t = (p.description, p.urls, p.parser, p.format, p.channels, p.nocheck)
        assert t in ln
        ln.remove(t)
    assert not ln
    for name, c in channelCache.items():
        print("Update:", name)
        c.update()
        print("# of channels: ", len(c.items))
