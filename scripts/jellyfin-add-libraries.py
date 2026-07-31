#!/usr/bin/env python3
"""
Jellyfin library bootstrapper — adds Movies/TV libraries via the API.

Usage:
    JELLYFIN_TOKEN=<api-token> python3 jellyfin-add-libraries.py

NOTE: the POST body must NOT use JSON for the VirtualFolders endpoint on
10.10.x — it 400s with "The name field is required." Use query params:
    POST /Library/VirtualFolders?name=Movies&collectionType=movies&paths=/media/movies
"""
import os
import requests

TOKEN = os.environ.get("JELLYFIN_TOKEN", "")
BASE = os.environ.get("JELLYFIN_BASE", "http://localhost:8096")
HEADERS = {"X-Emby-Token": TOKEN}


def add_library(name, collection_type, path):
    r = requests.post(
        f"{BASE}/Library/VirtualFolders",
        params={
            "name": name,
            "collectionType": collection_type,
            "paths": path,
            "refreshLibrary": "false",
        },
        headers=HEADERS,
    )
    print(f"{name} library: {r.status_code} {r.text.strip()}")


if __name__ == "__main__":
    add_library("Movies", "movies", "/media/movies")
    add_library("TV", "tvshows", "/media/tv")

    r = requests.get(f"{BASE}/Library/VirtualFolders", headers=HEADERS)
    for lib in r.json():
        print(f"  {lib['Name']}: {lib.get('Locations', ['?'])[0]}")
