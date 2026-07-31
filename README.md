# Pi Media Pipeline

Raspberry Pi 5 (4GB) media automation pipeline — **Jellyfin** + **Jellyseerr** + **Radarr** + **Sonarr** + **Transmission** + **Prowlarr** running in Docker.

End-to-end: request a movie/series in Jellyseerr → Radarr/Sonarr grabs releases from indexers via Prowlarr → pushes to Transmission → imports and organizes → Jellyfin serves it. All on a Pi 5.

---

## Hardware

| Component | Detail |
|-----------|--------|
| Board | Raspberry Pi 5, 4GB |
| OS | Debian aarch64 |
| Storage | External HDD, NTFS, 465GB |
| Mount | `/mnt/media` (`/dev/sda1` UUID=AE8E1A3B8E19FD11) |
| Network | Pi-hole DHCP + DNS (Cloudflare upstream) |
| Location | N/A (no VPN needed for torrenting) |

---

## Architecture

```
User ──► Jellyseerr (5055) ──► Radarr (7878) ──► Prowlarr (9696) ──► Indexers
                │                   │                                          
                │                   └──► Transmission (9091) ──► Downloads    
                │                                                              
                └──► Jellyfin (8096) ◄── Media Import
```

**Docker network:** All containers on `media` network (172.18.0.0/16) for internal DNS resolution.

---

## Services

### Jellyfin (8096)
- **Image:** `jellyfin/jellyfin:10.10.3` (NOT 10.11.11 — auth is broken in that version)
- **Volume mounts:** `/mnt/media/jellyfin/config`, `/mnt/media/jellyfin/cache`, `/mnt/media` (read-only)
- **Libraries:** Movies (`/media/movies`), TV (`/media/tv`)
- **Admin user:** `<user>` (password set via wizard)
- **Network fix:** `PublishedServerUriBySubnet` set to LAN broadcast range

### Jellyseerr (5055)
- **Image:** `fallenbagel/jellyseerr:latest`
- **Volume:** `/mnt/media/jellyseerr` → `/app/config`
- **Auth:** Local-only (`mediaServerLogin: false`, `localLogin: true`)
- **Login:** `admin@local` / `<password>`
- **Connected to:** Radarr + Sonarr

### Radarr (7878)
- **Image:** `linuxserver/radarr:latest`
- **Volume:** `/mnt/media` → `/media`
- **Quality profile:** HD-720p (for small file sizes)
- **Download client:** Transmission

### Sonarr (8989)
- **Image:** `linuxserver/sonarr:latest`
- **Volume:** `/mnt/media` → `/media`
- **Quality profile:** HD-720p
- **Download client:** Transmission

### Transmission (9091)
- **Image:** `linuxserver/transmission:latest`
- **Auth:** <user> / <password>
- **Sequential download:** ON (enables streaming partial files)
- **rename-partial-files:** OFF (files keep `.mkv`/`.mp4` while downloading)
- **Paths:** `/downloads/complete` (no separate incomplete dir)
- **IMPORTANT:** Sequential download makes files playable from the start. First pieces download first, so Jellyfin can begin playback within seconds of adding a torrent.

### Prowlarr (9696)
- **Image:** `linuxserver/prowlarr:latest`
- **Indexers:** 4 direct Torznab (no FlareSolverr needed — minimal Cloudflare blocking where deployed)
- **Sync:** Pushes to Radarr + Sonarr

---

## Quality Profiles

### Radarr
- **Primary:** HD-720p — grabs 720p x264 encodes (1-3GB per movie)
- **Per-request override:** 1080p available in Jellyseerr for specific movies

### Why 720p?
- Pi 5 transcodes 1080p fine, but 720p saves disk space and transfer time
- 720p at good bitrate looks identical to 1080p on most screens (phone, laptop, small TV)
- Sequential 720p downloads fill your disk slower

---

## Streaming While Downloading

Transmission is configured for **sequential download** — pieces download from start to finish rather than randomly scattered. Combined with `rename-partial-files: false`, the file keeps its original extension (`.mkv`/`.mp4`) from the moment Transmission starts writing.

**Result:** Jellyfin sees the file immediately and can begin serving the first chunk within seconds. Normal sequential playback works. Seeking to un-downloaded parts waits for the data.

---

## Custom Scripts

This repo contains the actual scripts used to build/fix this stack (sanitized — all credentials come from env vars):

| Script | Purpose |
|--------|---------|
| `scripts/jellyfin-bootstrap-user.py` | Creates/updates Jellyfin admin user + permissions directly in SQLite (PBKDF2-SHA512 hex format for 10.10.x) |
| `scripts/jellyfin-fix-network.py` | Sets `PublishedServerUriBySubnet` so LAN clients can connect |
| `scripts/jellyfin-add-libraries.py` | Adds Movies/TV libraries via API (query-param POST required on 10.10.x) |
| `scripts/jellyseerr-fix-password.py` | Fixes Jellyseerr admin password hash in SQLite (bcrypt via container Node) |
| `scripts/transmission-streaming-tweaks.py` | Enables sequential download + disables incomplete dir for mid-download streaming |

Run any with `python3 <script>.py` and the env vars documented in each file's docstring.

---

## Setup Steps (condensed)

1. Format HDD to NTFS, mount at `/mnt/media`
2. Install Docker + Docker Compose
3. Create directories: `movies/`, `tv/`, `downloads/` (split into `complete/` and `incomplete/` originally)
4. Deploy containers on `media` network
5. Configure Prowlarr indexers
6. Configure Radarr quality profile + download client
7. Configure Sonarr quality profile + download client
8. Run Jellyfin setup wizard (create admin user, add libraries)
9. Run Jellyseerr setup — bypassed via SQLite (`INSERT INTO User`) + `settings.json` patching
10. Connect Jellyseerr to Radarr + Sonarr

---

## Jellyfin Version Note

**Do NOT use jellyfin/jellyfin:latest (10.11.11).** The `AuthenticateByName` endpoint is broken — throws `Value cannot be null. (Parameter 'request.App')`. Pin to `jellyfin/jellyfin:10.10.3`.

Password hashing in 10.10.x uses hex-encoded PBKDF2-SHA512:
```
$PBKDF2-SHA512$iterations=210000$<SALT_HEX>$<HASH_HEX>
```
10.11.x changed to base64 — incompatible formats.

---

## Jellyseerr Local Auth Bypass

When the setup wizard fails or local auth needs manual setup:

```bash
# Generate bcrypt hash inside the container
sudo docker exec jellyseerr node -e \
  "const bcrypt = require('bcrypt'); console.log(bcrypt.hashSync('password', 10));"

# Insert user into SQLite DB
sqlite3 /mnt/media/jellyseerr/db/db.sqlite3 \
  "INSERT INTO User (email, username, password, permissions, avatar, userType, createdAt, updatedAt)
   VALUES ('user@local', 'username', '\$2b\$10\$...', 2, '/assets/avatars/red.png', 1, datetime('now'), datetime('now'));"

# Set settings
python3 -c "
import json
s = json.load(open('/mnt/media/jellyseerr/settings.json'))
s['public']['initialized'] = True
s['main']['localLogin'] = True
s['main']['mediaServerLogin'] = False
json.dump(s, open('/mnt/media/jellyseerr/settings.json','w'), indent=2)
"
```

---

## Useful Commands

```bash
# Check all containers
sudo docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# Jellyfin logs
sudo docker logs jellyfin --tail 50

# Jellyseerr logs
sudo docker logs jellyseerr --tail 50

# Radarr API
curl -s http://localhost:7878/api/v3/movie?apiKey=<KEY> | python3 -m json.tool

# Transmission status
curl -s -u '<user>:<password>' http://localhost:9091/transmission/rpc \
  -H 'X-Transmission-Session-Id: <SID>' \
  -d '{"method":"torrent-get","arguments":{"fields":["name","percentDone","status","downloadDir"]}}'
```

---

## Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| Jellyfin | `http://<server-ip>:8096` | <user> / <password> |
| Jellyseerr | `http://<server-ip>:5055` | admin@local / <password> |
| Radarr | `http://<server-ip>:7878` | API key |
| Sonarr | `http://<server-ip>:8989` | API key |
| Transmission | `http://<server-ip>:9091` | <user> / <password> |
| Prowlarr | `http://<server-ip>:9696` | API key |
