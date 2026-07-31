#!/usr/bin/env python3
"""
Jellyseerr password fix — updates the User table with a fresh bcrypt hash.

Why this exists: the Jellyseerr setup wizard can fail to create a usable
admin account. This inserts/updates the admin user directly in SQLite.

Generate the bcrypt hash inside the container (host has no Node):
    sudo docker exec jellyseerr node -e \
      "const bcrypt = require('bcrypt'); console.log(bcrypt.hashSync('mypassword', 10));"

Then run:
    JELLYSEERR_DB=/mnt/media/jellyseerr/db/db.sqlite3 \
    JELLYSEERR_EMAIL=me@local \
    JELLYSEERR_BCRYPT='$2b$10$...' \
    python3 jellyseerr-fix-password.py

CRITICAL pitfall: never pass the hash through a shell that interprets `$`
(sshpass, double quotes, etc.) — it silently strips `$2b$10$` and corrupts
the hash. Write it via env var or a Python file copied with scp.
"""
import os
import sqlite3
import sys

DB = os.environ.get("JELLYSEERR_DB", "/mnt/media/jellyseerr/db/db.sqlite3")
EMAIL = os.environ.get("JELLYSEERR_EMAIL", "admin@local")
BCRYPT_HASH = os.environ.get("JELLYSEERR_BCRYPT", "")

if not BCRYPT_HASH.startswith("$2"):
    print("ERROR: JELLYSEERR_BCRYPT must start with $2 (bcrypt). Check for shell $ stripping.")
    sys.exit(1)

conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute("UPDATE 'User' SET password = ? WHERE email = ?", [BCRYPT_HASH, EMAIL])
print(f"Updated: {c.rowcount} rows")
conn.commit()
conn.close()
