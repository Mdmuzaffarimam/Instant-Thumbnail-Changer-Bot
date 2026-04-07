# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat

import re
import os
import aiohttp
import aiofiles
from typing import Optional, Tuple, List
from PIL import Image, ImageFilter

from config import TMDB_API_KEY

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMG_BASE = "https://image.tmdb.org/t/p/w500"

# Cover output size — matches standard 16:9 video thumbnail
COVER_W = 1280
COVER_H = 720

# ==================== FILENAME PARSER ====================

_END_MARKERS = re.compile(
    r"[\.\s_]("
    r"S\d{1,2}E\d{1,3}"
    r"|19\d{2}|20\d{2}"
    r"|480p|720p|1080p|2160p|4[Kk]"
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
    title = re.sub(r"\(\s*(?:19|20)\d{2}\s*\)", "", title)
    title = re.sub(r"\([^)]*\)", "", title)
    title = re.sub(r"\[[^\]]*\]", "", title)
    title = re.sub(r"[\s\-_]+$", "", title)
    title = re.sub(r"^[\s\-_]+", "", title)
    title = re.sub(r"\s{2,}", " ", title)
    return title.strip()

def parse_title_from_filename(filename: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[._]", " ", name)
    name = re.sub(r"\s*-\s*(?=[A-Za-z])", " ", name)
    name = name.strip()

    year_match = re.search(r"[\(\s]*(19\d{2}|20\d{2})[\)\s]", name)
    year = int(year_match.group(1)) if year_match else None

    se_match = re.search(r"\bS(\d{1,2})E(\d{1,3})\b", name, re.IGNORECASE)
    media_type = "tv" if se_match else "movie"

    match = _END_MARKERS.search(name)
    raw_title = name[: match.start()].strip() if match else name.strip()
    title = _clean_title(raw_title)

    return title if title else None, media_type, year


# ==================== TITLE VARIANTS ====================

def _generate_title_variants(title: str) -> List[str]:
    variants = []

    def add(t):
        t = t.strip()
        if t and t not in variants:
            variants.append(t)

    add(title)
    words = title.split()

    for n in range(min(5, len(words) - 1), 1, -1):
        add(" ".join(words[:n]))

    def halve(t):
        return re.sub(r"(.)\1{2,}", r"\1\1", t)

    def dedouble(t):
        return re.sub(r"(.)\1+", r"\1", t)

    simp = halve(title)
    if simp != title:
        add(simp)
        for n in range(min(5, len(simp.split()) - 1), 1, -1):
            add(" ".join(simp.split()[:n]))

    sing = dedouble(title)
    if sing != title:
        add(sing)
        for n in range(min(5, len(sing.split()) - 1), 1, -1):
            add(" ".join(sing.split()[:n]))

    return variants


# ==================== POSTER RESIZE → 16:9 ====================

def make_cover_image(poster_path: str, output_path: str) -> bool:
    """
    Resize a portrait TMDB poster to 1280x720 (16:9) cover image.

    Layout:
    - Background: poster stretched to 1280x720 + heavy Gaussian blur
    - Foreground: poster scaled to fit height (720px), centered
    - Result: professional cover that fills video thumbnail area
    """
    try:
        poster = Image.open(poster_path).convert("RGB")

        # ── Background: stretch + blur ──────────────────────────────
        bg = poster.resize((COVER_W, COVER_H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=40))

        # Darken background slightly so foreground stands out
        bg = bg.point(lambda p: int(p * 0.6))

        # ── Foreground: scale poster to fill height ─────────────────
        scale  = COVER_H / poster.height
        fg_w   = int(poster.width * scale)
        fg_h   = COVER_H
        fg     = poster.resize((fg_w, fg_h), Image.LANCZOS)

        # ── Paste centered ──────────────────────────────────────────
        x = (COVER_W - fg_w) // 2
        bg.paste(fg, (x, 0))

        bg.save(output_path, "JPEG", quality=95)
        return True
    except Exception as e:
        print(f"Cover resize error: {e}")
        return False


# ==================== TMDB SEARCH ====================

async def _search_single(session, query, mtype, year=None):
    params = {
        "api_key":  TMDB_API_KEY,
        "query":    query,
        "language": "en-US",
        "page":     1,
    }
    if year:
        params["first_air_date_year" if mtype == "tv" else "year"] = year

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


async def search_tmdb(title, media_type="tv", year=None):
    if not TMDB_API_KEY:
        return None

    variants   = _generate_title_variants(title)
    alt_type   = "movie" if media_type == "tv" else "tv"
    types_order = [media_type, alt_type]

    async with aiohttp.ClientSession() as session:
        for variant in variants:
            for mtype in types_order:
                if year:
                    r = await _search_single(session, variant, mtype, year)
                    if r:
                        return r
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
    Full pipeline: filename → parse → TMDB search → download → resize to 16:9.
    Returns (cover_path_1280x720, tmdb_result) or (None, None).
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
    safe = re.sub(r"[^\w]", "_", title)[:40]

    # Download original poster
    raw_path  = os.path.join(save_dir, f"tmdb_raw_{safe}.jpg")
    cover_path = os.path.join(save_dir, f"tmdb_cover_{safe}.jpg")

    ok = await download_poster(result["poster_path"], raw_path)
    if not ok:
        return None, None

    # Resize to 16:9 cover
    resized = make_cover_image(raw_path, cover_path)

    # Cleanup raw poster
    if os.path.exists(raw_path):
        os.remove(raw_path)

    if not resized:
        return None, None

    return cover_path, result
