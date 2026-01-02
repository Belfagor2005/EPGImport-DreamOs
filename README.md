```markdown
# EPG Import – Modded for Dreambox Enigma2

EPG Import plugin modified for Dreambox Enigma2 receivers.  
This version includes fixes, improvements, and custom adaptations based on the original project.

---

## License

Released under the **GPLv2** license.

---

## Overview

The plugin uses XMLTV sources to import EPG data into Enigma2.

Providers can find example XML source files in:

```

/etc/epgimport

````

These files can be used as a reference for creating custom EPG sources.

End users do **not** need to manually edit these files.  
All configuration can be done directly from the Enigma2 plugin menu.

---

## Installation – XML Sources

To install or update the XML source files, run the following shell command:

```sh
wget -q --no-check-certificate "https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer_source.sh?inline=false" -O - | /bin/sh
````

---

## Credits

* **rytec** – XMLTV data provider
* **oudeis**, **arnoldd** – original EPG Import plugin
* **Panagiotis Malakoudis** – UTF-8 support tips
* **PLi Team** – Enigma2 support and development
* **sat4all.com community** – testing and contributions

---

## Modifications

* Modified and maintained by **Lululla**
* Additional changes and fixes by **Belfagor2005**
* Adapted and optimized for Dreambox Enigma2

---

## Disclaimer

This is an unofficial, community-maintained version of the plugin.
Use at your own risk.

```
```
