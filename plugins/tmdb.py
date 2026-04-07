# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat

import re
import os
import aiohttp
import aiofiles
from typing import Optional, Tuple

TMDB_API_KEY  = os.environ.get("TMDB_API_KEY", "")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"

# ==================== FILENAME PARSER ====================

# Patterns that mark where the real title ends in a filename
_END_MARKERS = re.compile(
    r"""
    [\.\s]          # separator
    (
        S\d{1,2}E\d{1,2}   |  # S01E01
        \d{4}               |  # year like 2024
        480p | 720p | 1080p | 2160p | 4k  |
        WEB[.\-]?DL | WEBRip | BluRay | HDTV | AMZN | NF | ZEE5 |
        AAC | AAC2\.0 | x264 | x265 | H\.264 | H264 | HEVC |
        DVDRip | BRRip | HDRip
    )
    """,
    re.IGNORECASE | re.VERBOSE
)

def parse_title_from_filename(filename: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Parse a video filename and return (title, media_type, year).

    Examples:
      Tumm.Se.Tumm.Tak.S01E263...mp4  → ("Tumm Se Tumm Tak", "tv",    None)
      Oppenheimer.2023.1080p...mp4    → ("Oppenheimer",       "movie", 2023)
      The.Boys.2019.S04E01...mp4      → ("The Boys",          "tv",    2019)
    """
    # Strip extension
    name = os.path.splitext(filename)[0]
    # Replace dots/underscores/hyphens with spaces
    name = re.sub(r"[._-]", " ", name).strip()

    # Detect year
    year_match = re.search(r"\b(19\d{2}|20\d{2})\b", name)
    year = int(year_match.group(1)) if year_match else None

    # Detect season/episode → it's a TV show
    se_match = re.search(r"\bS(\d{1,2})E(\d{1,2})\b", name, re.IGNORECASE)
    media_type = "tv" if se_match else "movie"

    # Cut the name at the first end-marker
    match = _END_MARKERS.search(name)
    if match:
        title = name[: match.start()].strip()
    else:
        title = name.strip()

    # Clean leftover brackets / extra spaces
    title = re.sub(r"\s{2,}", " ", title).strip()

    return title if title else None, media_type, year


# ==================== TMDB SEARCH ====================

async def search_tmdb(title: str, media_type: str = "tv", year: int = None) -> Optional[dict]:
    """
    Search TMDB for title. Returns first result dict or None.
    Tries TV first for series, then movie as fallback (and vice versa).
    """
    if not TMDB_API_KEY:
        return None

    async with aiohttp.ClientSession() as session:
        for mtype in ([media_type, "movie" if media_type == "tv" else "tv"]):
            params = {
                "api_key": TMDB_API_KEY,
                "query":   title,
                "language": "en-US",
                "page":    1,
            }
            if year:
                params["first_air_date_year" if mtype == "tv" else "year"] = year

            url = f"{TMDB_BASE_URL}/search/{mtype}"
            try:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    results = data.get("results", [])
                    if results:
                        # Pick first result that has a poster
                        for r in results:
                            if r.get("poster_path"):
                                r["_media_type"] = mtype
                                return r
            except Exception:
                continue

    return None


# ==================== POSTER DOWNLOADER ====================

async def download_poster(poster_path: str, save_path: str) -> bool:
    """Download a TMDB poster image to save_path. Returns True on success."""
    url = f"{TMDB_IMG_BASE}{poster_path}"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return False
                async with aiofiles.open(save_path, "wb") as f:
                    await f.write(await resp.read())
        return True
    except Exception:
        return False


# ==================== MAIN ENTRY POINT ====================

async def get_tmdb_poster(filename: str, save_dir: str = "/tmp") -> Tuple[Optional[str], Optional[dict]]:
    """
    Full pipeline: filename → parse → TMDB search → download poster.

    Returns:
        (local_poster_path, tmdb_result)  on success
        (None, None)                      on failure / not found
    """
    if not TMDB_API_KEY:
        return None, None

    title, media_type, year = parse_title_from_filename(filename)
    if not title:
        return None, None

    result = await search_tmdb(title, media_type, year)
    if not result or not result.get("poster_path"):
        return None, None

    os.makedirs(save_dir, exist_ok=True)
    safe_title = re.sub(r"[^\w]", "_", title)[:40]
    save_path  = os.path.join(save_dir, f"tmdb_{safe_title}.jpg")

    success = await download_poster(result["poster_path"], save_path)
    if not success:
        return None, None

    return save_path, result
