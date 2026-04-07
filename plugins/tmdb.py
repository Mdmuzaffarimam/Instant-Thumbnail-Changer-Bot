# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat

import re
import os
import aiohttp
import aiofiles
from typing import Optional, Tuple, List

from config import TMDB_API_KEY

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"

# ==================== FILENAME PARSER ====================

_END_MARKERS = re.compile(
    r"[\.\s_]("
    r"S\d{1,2}E\d{1,3}"                                                  # S01E01
    r"|19\d{2}|20\d{2}"                                                   # year
    r"|480p|720p|1080p|2160p|4[Kk]"                                       # quality
    r"|WEB[.\-]?DL|WEBRip|BluRay|BRRip|BDRip|HDTV|AMZN|NF|ZEE5"
    r"|SONY|HOTSTAR|VOOT|JIOCINEMA|HULU|DSNP|ATVP"
    r"|AAC[\d.]*|DDP[\d.]*|DD[\d.]+|DTS|FLAC|MP3|AC3"
    r"|x264|x265|H\.?264|H\.?265|HEVC|AVC|XviD"
    r"|DVDRip|HDRip|CAMRip|DVDScr"
    r"|Hindi|English|Tamil|Telugu|Malayalam|Bengali|Punjabi|Dual|Multi"
    r"|REPACK|PROPER|EXTENDED|UNRATED|THEATRICAL"
    r")",
    re.IGNORECASE
)

def _clean_title(title: str) -> str:
    """
    Clean extracted title:
    - Remove (YEAR) e.g. "Anemone (2025)" → "Anemone"
    - Remove [anything] e.g. "Movie [Extended]" → "Movie"
    - Remove trailing punctuation / extra spaces
    """
    # Remove (YEAR) pattern
    title = re.sub(r"\(\s*(?:19|20)\d{2}\s*\)", "", title)
    # Remove any remaining (...) and [...]
    title = re.sub(r"\([^)]*\)", "", title)
    title = re.sub(r"\[[^\]]*\]", "", title)
    # Remove trailing/leading separators
    title = re.sub(r"[\s\-_]+$", "", title)
    title = re.sub(r"^[\s\-_]+", "", title)
    # Collapse multiple spaces
    title = re.sub(r"\s{2,}", " ", title)
    return title.strip()

def parse_title_from_filename(filename: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """
    Parse filename → (title, media_type, year)

    Examples:
      Anemone (2025) 1080p BluRay...mkv          → ("Anemone", "movie", 2025)
      Feel.My.Voice.2026.720p.NF...mkv           → ("Feel My Voice", "movie", 2026)
      Tumm.Se.Tumm.Tak.S01E271...mp4             → ("Tumm Se Tumm Tak", "tv", None)
      Bhabhiji.Ghar.Par.Hain.Fun...2026...mkv    → ("Bhabhiji Ghar Par Hain Fun On The Run", "movie", 2026)
    """
    name = os.path.splitext(filename)[0]

    # Replace dots and underscores with spaces (but NOT inside parentheses numbers)
    name = re.sub(r"[._]", " ", name)
    # Replace hyphen between words (not inside numbers like DD5.1)
    name = re.sub(r"\s*-\s*(?=[A-Za-z])", " ", name)
    name = name.strip()

    # Detect year (including inside parentheses like "(2025)")
    year_match = re.search(r"[\(\s]*(19\d{2}|20\d{2})[\)\s]", name)
    year = int(year_match.group(1)) if year_match else None

    # Detect TV show (SxxExx)
    se_match = re.search(r"\bS(\d{1,2})E(\d{1,3})\b", name, re.IGNORECASE)
    media_type = "tv" if se_match else "movie"

    # Find where title ends at first end-marker
    match = _END_MARKERS.search(name)
    raw_title = name[: match.start()].strip() if match else name.strip()

    # Clean title (remove years in parens, brackets, etc.)
    title = _clean_title(raw_title)

    return title if title else None, media_type, year


# ==================== TITLE VARIANTS ====================

def _generate_title_variants(title: str) -> List[str]:
    """
    Generate search variants:
    1. Full title
    2. Progressively shorter (fewer words)
    3. Simplified (double letters → single): "Tumm" → "Tum"
    """
    variants = []

    def add(t):
        t = t.strip()
        if t and t not in variants:
            variants.append(t)

    add(title)
    words = title.split()

    # Shorter variants: drop words from the end
    for n in range(min(5, len(words) - 1), 1, -1):
        add(" ".join(words[:n]))

    # Simplify doubled letters: "Tumm" → "Tum", "Bhabhiji" → "Bhabiji"
    def dedouble(t):
        return re.sub(r"(.)\1+", r"\1", t)

    def halve(t):
        # collapse 3+ same chars → 2
        return re.sub(r"(.)\1{2,}", r"\1\1", t)

    simp = halve(title)
    if simp != title:
        add(simp)
        simp_words = simp.split()
        for n in range(min(5, len(simp_words) - 1), 1, -1):
            add(" ".join(simp_words[:n]))

    sing = dedouble(title)
    if sing != title:
        add(sing)
        sing_words = sing.split()
        for n in range(min(5, len(sing_words) - 1), 1, -1):
            add(" ".join(sing_words[:n]))

    return variants


# ==================== TMDB SEARCH ====================

async def _search_single(
    session: aiohttp.ClientSession,
    query: str,
    mtype: str,
    year: int = None
) -> Optional[dict]:
    params = {
        "api_key":  TMDB_API_KEY,
        "query":    query,
        "language": "en-US",
        "page":     1,
    }
    if year:
        key = "first_air_date_year" if mtype == "tv" else "year"
        params[key] = year

    url = f"{TMDB_BASE_URL}/search/{mtype}"
    try:
        async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            for r in data.get("results", []):
                if r.get("poster_path"):
                    r["_media_type"] = mtype
                    return r
    except Exception:
        pass
    return None


async def search_tmdb(title: str, media_type: str = "tv", year: int = None) -> Optional[dict]:
    """
    Multi-strategy search:
    For each title variant:
      - Try primary media type with year
      - Try primary media type without year       ← KEY FIX for 2026 movies
      - Try alternate media type with year
      - Try alternate media type without year
    """
    if not TMDB_API_KEY:
        return None

    variants    = _generate_title_variants(title)
    alt_type    = "movie" if media_type == "tv" else "tv"
    types_order = [media_type, alt_type]

    async with aiohttp.ClientSession() as session:
        for variant in variants:
            for mtype in types_order:
                # With year
                if year:
                    r = await _search_single(session, variant, mtype, year)
                    if r:
                        return r
                # Without year  ← catches recent/unreleased titles like 2026 movies
                r = await _search_single(session, variant, mtype, None)
                if r:
                    return r

    return None


# ==================== POSTER DOWNLOAD ====================

async def download_poster(poster_path: str, save_path: str) -> bool:
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


# ==================== MAIN ENTRY ====================

async def get_tmdb_poster(filename: str, save_dir: str = "/tmp") -> Tuple[Optional[str], Optional[dict]]:
    """
    Full pipeline: filename → parse → TMDB search → download poster.
    Returns (local_path, tmdb_result) or (None, None).
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
    safe      = re.sub(r"[^\w]", "_", title)[:40]
    save_path = os.path.join(save_dir, f"tmdb_{safe}.jpg")

    ok = await download_poster(result["poster_path"], save_path)
    if not ok:
        return None, None

    return save_path, result
