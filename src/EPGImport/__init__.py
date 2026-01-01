#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
# ===============================
# Standard Library
# ===============================
# import os
from os import environ  #, path
from os.path import exists
from gettext import bindtextdomain, dgettext, gettext

# ===============================
# Enigma2 / Components
# ===============================
# Commented: from enigma import addFont, getDesktop
# Commented: from enigma import addFont
from Components.Language import language

# ===============================
# Tools / Enigma2 Utilities
# ===============================
from Tools.Directories import resolveFilename, SCOPE_PLUGINS


try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


PluginLanguageDomain = "EPGImport"
PluginLanguagePath = "Extensions/EPGImport/locale"


isDreambox = False
if exists("/usr/bin/apt-get"):
    isDreambox = True

# ===============================
# SKIN LOADING - COMMENTED
# ===============================
"""
try:
    ScreenWidth = getDesktop(0).size().width()
except:
    ScreenWidth = 720
ScreenWidth = '1080' if ScreenWidth >= 1920 else '720'

def getFullPath(fname):
    return resolveFilename(SCOPE_PLUGINS, path.join('Extensions', PluginLanguageDomain, fname))

try:
    plugin_skin = ET.parse(getFullPath('skin/%s.xml' % ScreenWidth)).getroot()
except Exception as e:
    print("[EPGImport] Error loading skin: %s" % str(e))
    plugin_skin = None


def getSkin(skinName):
    if plugin_skin is not None:
        try:
            skin_element = plugin_skin.find('.//screen[@name="%s"]' % skinName)
            if skin_element is not None:
                return ET.tostring(skin_element, encoding='utf8', method='xml')
        except Exception as e:
            print("[EPGImport] Error getting skin %s: %s" % (skinName, str(e)))
    return ''
"""


def _(txt):
    return gettext.dgettext(PluginLanguageDomain, txt) if txt else ''


# ===============================
# FONT ADDING - COMMENTED
# ===============================
"""
try:
    addFont(getFullPath('skin/%s' % 'epgimport.ttf'), 'EPGImport', 100, False)
except Exception as e:
    print("[EPGImport] Error adding font: %s" % str(e))
    try:
        # Fallback for openPLI-based images
        addFont(getFullPath('skin/%s' % 'epgimport.ttf'), 'EPGImport', 100, False, 0)
    except Exception as e2:
        print("[EPGImport] Error adding font (fallback): %s" % str(e2))
"""


def localeInit():
    if isDreambox:
        lang = language.getLanguage()[:2]
        environ["LANGUAGE"] = lang
    bindtextdomain(PluginLanguageDomain, resolveFilename(SCOPE_PLUGINS, PluginLanguagePath))


if isDreambox:
    def _(txt):
        return dgettext(PluginLanguageDomain, txt) if txt else ""
else:
    def _(txt):
        translated = dgettext(PluginLanguageDomain, txt)
        if translated:
            return translated
        else:
            print(("[%s] fallback to default translation for %s" % (PluginLanguageDomain, txt)))
            return gettext(txt)

localeInit()
language.addCallback(localeInit)
