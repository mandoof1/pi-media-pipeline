#!/usr/bin/env python3
"""
Jellyfin admin user bootstrap (10.10.x) — creates or updates the admin
user + permissions directly in the Jellyfin SQLite DB.

Password hashing in Jellyfin 10.10.x = PBKDF2-SHA512, HEX encoded:
    $PBKDF2-SHA512$iterations=210000$<SALT_HEX>$<HASH_HEX>
(10.11.x switched to base64 — incompatible, and 10.11.x auth is broken anyway.)

Usage:
    JELLYFIN_USER=admin JELLYFIN_PASSWORD=secret python3 jellyfin-bootstrap-user.py
"""
import hashlib
import os
import sqlite3
import sys
import uuid

DB = os.environ.get("JELLYFIN_DB", "/mnt/media/jellyfin/config/data/jellyfin.db")
USERNAME = os.environ.get("JELLYFIN_USER", "admin")
PASSWORD = os.environ.get("JELLYFIN_PASSWORD", "")

if not PASSWORD:
    print("ERROR: JELLYFIN_PASSWORD not set")
    sys.exit(1)

conn = sqlite3.connect(DB)
c = conn.cursor()

# PBKDF2-SHA512 hex hash (10.10.x format)
salt = os.urandom(16)
dk = hashlib.pbkdf2_hmac("sha512", PASSWORD.encode(), salt, 210000)
hash_str = f"$PBKDF2-SHA512$iterations=210000${salt.hex().upper()}${dk.hex().upper()}"

c.execute("SELECT Id FROM Users WHERE Username = ?", (USERNAME,))
existing = c.fetchone()
if existing:
    uid = existing[0]
    c.execute("UPDATE Users SET Password = ? WHERE Id = ?", (hash_str, uid))
    print(f"Updating existing user: {uid}")
else:
    uid = str(uuid.uuid4()).upper()
    c.execute("SELECT COALESCE(MAX(InternalId), 0) + 1 FROM Users")
    internal_id = c.fetchone()[0]
    c.execute(
        """INSERT INTO Users (
            Id, Username, Password,
            AuthenticationProviderId, PasswordResetProviderId,
            MustUpdatePassword, EnableAutoLogin,
            DisplayCollectionsView, DisplayMissingEpisodes,
            EnableLocalPassword, EnableNextEpisodeAutoPlay,
            EnableUserPreferenceAccess, HidePlayedInLatest,
            InternalId, InvalidLoginAttemptCount,
            LoginAttemptsBeforeLockout, MaxActiveSessions,
            MaxParentalAgeRating, PlayDefaultAudioTrack,
            RememberAudioSelections, RememberSubtitleSelections,
            RemoteClientBitrateLimit, RowVersion,
            SubtitleLanguagePreference, SubtitleMode, SyncPlayAccess
        ) VALUES (
            ?, ?, ?,
            'Jellyfin.Server.Implementations.Users.DefaultAuthenticationProvider',
            'Jellyfin.Server.Implementations.Users.DefaultPasswordResetProvider',
            0, 0, 0, 0, 0, 0, 0, 0, ?, 0, 0, 0, 0, 0, 0, 0, 1, '', 2, 0
        )""",
        (uid, USERNAME, hash_str, internal_id),
    )
    print(f"Created user: {uid}")

# Admin permissions (Kind=0 is IsAdministrator)
c.execute("DELETE FROM Permissions WHERE UserId = ?", (uid,))
c.execute("SELECT COALESCE(MAX(Id), 0) + 1 FROM Permissions")
next_id = c.fetchone()[0]
admin_permissions = [
    (0, 1),  # IsAdministrator
    (1, 1),  # EnableContentDeletion
    (2, 0),  # EnableRemoteControlOfOtherUsers
    (3, 1),  # EnableSharedDeviceControl
    (4, 1),  # EnableRemoteAccess
    (5, 0),  # EnableLiveTvManagement
    (6, 1),  # EnableLiveTvAccess
    (7, 1),  # EnableMediaPlayback
    (8, 1),  # EnableAudioPlaybackTranscoding
    (9, 1),  # EnableVideoPlaybackTranscoding
    (10, 1),  # EnablePlaybackRemuxing
    (11, 1),  # EnableContentDeletionFromFolders
    (12, 1),  # EnableContentDownloading
    (13, 1),  # EnableSyncTranscoding
    (14, 1),  # EnableMediaConversion
    (15, 1),  # EnableAllDevices
    (16, 1),  # EnableAllChannels
    (17, 1),  # EnableAllFolders
    (18, 1),  # EnablePublicSharing
    (19, 1),  # Access schedules
    (20, 0),  # Blocked tags
    (21, 0),  # Blocked channels
    (22, 0),  # RemoteClientBitrateLimit
    (23, 0),  # AuthenticationProviderId
]
for kind, value in admin_permissions:
    c.execute(
        "INSERT INTO Permissions (Id, Kind, Value, RowVersion, UserId) VALUES (?, ?, ?, 1, ?)",
        (next_id, kind, value, uid),
    )
    next_id += 1

conn.commit()
conn.close()
print("Done!")
