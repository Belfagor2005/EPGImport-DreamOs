# XMLTV Importer

This software is released under the **GPLv2 license**.

## Overview

XMLTV Importer allows importing EPG data from XMLTV sources into Enigma2.

- **Providers** can check the `.xml` files located in the `/etc/epgimport` directory to learn how to create custom sources.
- **End users** do not need to read or edit these files manually: everything can be configured directly from the plugin interface.

## Credits

Special thanks go to:

- **rytec** – for providing the XMLTV data  
- **oudeis** and **arnoldd** – for the initial plugin development  
- **Panagiotis Malakoudis** – for UTF-8 related tips  
- **The PLi team** – for their patience and support  
- **sat4all.com community** – for their contributions  

## Installation of Source XML Files

To install the source XML files, use the following command:

```sh
wget -q --no-check-certificate "https://raw.githubusercontent.com/Belfagor2005/EPGImport-99/main/installer_source.sh?inline=false" -O - | /bin/sh
```


