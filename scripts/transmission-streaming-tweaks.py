#!/usr/bin/env python3
"""
Transmission streaming tweaks — enables sequential download + disables the
incomplete dir so media files are playable WHILE still downloading.

Two settings matter:
  - sequentialDownload: pieces download start-to-finish (not random), so the
    beginning of a movie arrives first and playback can begin quickly.
  - rename-partial-files: false keeps the real .mkv/.mp4 name on the partial
    file so Jellyfin will index and play it mid-download.
  - incomplete-dir-enabled: false sends everything to the main download dir.

Note: if Transmission runs in Docker with a named volume for /config, the
settings.json lives inside that volume:
    /var/lib/docker/volumes/<VOLUME_ID>/_data/settings.json
Find it with: sudo docker inspect transmission | grep -i volume
"""
import json
import os
import sys

path = os.environ.get(
    "TRANSMISSION_SETTINGS",
    "/mnt/media/transmission/config/settings.json",
)

if not os.path.exists(path):
    print(f"ERROR: {path} not found — locate the real settings.json (see docstring).")
    sys.exit(1)

with open(path) as f:
    s = json.load(f)

s["sequentialDownload"] = True
s["rename-partial-files"] = False
s["incomplete-dir-enabled"] = False
s["queue-stalled-enabled"] = False

with open(path, "w") as f:
    json.dump(s, f, indent=2)

print("Transmission settings updated. Restart the container to apply.")
