#!/usr/bin/env python3
"""
Jellyfin network config fix — sets PublishedServerUriBySubnet so clients
on the LAN can discover/connect properly.

Usage:
    JELLYFIN_SUBNET='192.168.0.0/24=http://192.168.0.10:8096' \
    python3 jellyfin-fix-network.py
"""
import os
import xml.etree.ElementTree as ET  # local trusted config file — no external XML input, safe without defusedxml

path = os.environ.get("JELLYFIN_NETWORK_XML", "/mnt/media/jellyfin/config/config/network.xml")
subnet_uri = os.environ.get("JELLYFIN_SUBNET", "")

tree = ET.parse(path)
root = tree.getroot()

if subnet_uri:
    for e in root.findall("PublishedServerUriBySubnet"):
        root.remove(e)
    subnet = ET.SubElement(root, "PublishedServerUriBySubnet")
    subnet.text = subnet_uri

addr = root.find("LocalNetworkAddresses")
if addr is not None:
    addr.text = "0.0.0.0"

tree.write(path, xml_declaration=True, encoding="utf-8")
print("Done")
