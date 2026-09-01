"""Newgrounds audio integration — resolve a Newgrounds audio-portal ID to its
direct MP3 file, the same way Geometry Dash lets creators pick a "Newgrounds
Song" for a level instead of a built-in track.

Only a numeric ID is accepted (e.g. 1605982, from newgrounds.com/audio/listen/1605982) —
we build the listen-page URL ourselves. Newgrounds exposes the direct audio file and
title as standard Open Graph meta tags (og:audio / og:title) on that page, which is
public embed metadata intended for exactly this kind of linking/sharing use.
"""

import re
import html
import requests

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PolygonRush/1.0"
REQUEST_TIMEOUT = 15
DOWNLOAD_TIMEOUT = 30


class NewgroundsError(Exception):
    pass


def fetch_song_info(song_id):
    """Given a numeric Newgrounds audio ID, download the track and return
    (mp3_bytes, title). Raises NewgroundsError with a user-facing message on failure."""
    song_id = str(song_id).strip()
    if not song_id.isdigit():
        raise NewgroundsError("Newgrounds ID must be a number (e.g. 1605982).")

    headers = {"User-Agent": USER_AGENT}
    page_url = f"https://www.newgrounds.com/audio/listen/{song_id}"
    try:
        resp = requests.get(page_url, headers=headers, timeout=REQUEST_TIMEOUT)
    except requests.RequestException as e:
        raise NewgroundsError(f"Couldn't reach Newgrounds: {e}")

    if resp.status_code == 404:
        raise NewgroundsError(f"No Newgrounds song found with ID {song_id}.")
    if resp.status_code != 200:
        raise NewgroundsError(f"Newgrounds returned HTTP {resp.status_code}.")

    audio_match = re.search(r'<meta property="og:audio" content="([^"]+)"', resp.text)
    if not audio_match:
        raise NewgroundsError("That ID doesn't have a playable song (it may be private, age-restricted, or removed).")
    audio_url = html.unescape(audio_match.group(1))

    title_match = re.search(r'<meta property="og:title" content="([^"]+)"', resp.text)
    title = html.unescape(title_match.group(1)) if title_match else f"NG Song {song_id}"

    try:
        audio_resp = requests.get(audio_url, headers=headers, timeout=DOWNLOAD_TIMEOUT)
    except requests.RequestException as e:
        raise NewgroundsError(f"Couldn't download the audio file: {e}")
    if audio_resp.status_code != 200:
        raise NewgroundsError(f"Failed to download the audio file (HTTP {audio_resp.status_code}).")

    return audio_resp.content, title


def safe_filename(song_id, title):
    """Build a filesystem-safe .mp3 filename for a downloaded NG song."""
    slug = re.sub(r"[^A-Za-z0-9._ -]", "", title).strip().replace(" ", "_")[:40]
    slug = slug or "song"
    return f"ng_{song_id}_{slug}.mp3"
