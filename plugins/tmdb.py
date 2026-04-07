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

TMDB_BASE_URL    = "https://api.themoviedb.org/3"
TMDB_BACKDROP    = "https://image.tmdb.org/t/p/w1280"   # 16:9 landscape ← PRIMARY
TMDB_POSTER      = "https://image.tmdb.org/t/p/w500"    # portrait       ← FALLBACK

COVER_W = 1280
COVER_H = 720

# ==================== FILENAME PARSER ====================

_END_MARKERS = re.compile(
    r"[\.\s_]("
    r"S\d{1,2}E\d{1,3}"
    r"|19\d{2}|20\d{2}"
    r"|480p|720p|1080p|2160p|4[Kk]|240p|360p"
    r"|WEB[.\-]?DL|WEBRip|BluRay|BRRip|BDRip|HDTV|AMZN|NF|ZEE5|JHS"
    r"|SONY|HOTSTAR|VOOT|JIOCINEMA|HULU|DSNP|ATVP|ZWN|OTT"
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

    se_match   = re.search(r"\bS(\d{1,2})E(\d{1,3})\b", name, re.IGNORECASE)
    media_type = "tv" if se_match else "movie"

    match     = _END_MARKERS.search(name)
    raw_title = name[: match.start()].strip() if match else name.strip()
    title     = _clean_title(raw_title)

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

    def halve(t):    return re.sub(r"(.)\1{2,}", r"\1\1", t)
    def dedouble(t): return re.sub(r"(.)\1+",    r"\1",   t)

    for fn in [halve, dedouble]:
        s = fn(title)
        if s != title:
            add(s)
            for n in range(min(5, len(s.split()) - 1), 1, -1):
                add(" ".join(s.split()[:n]))

    return variants


# ==================== TMDB SEARCH ====================

async def _search_single(session, query, mtype, year=None) -> Optional[dict]:
    params = {
        "api_key":  TMDB_API_KEY,
        "query":    query,
        "language": "en-US",
        "page":     1,
    }
    if year:
        params["first_air_date_year" if mtype == "tv" else "year"] = year

    try:
        async with session.get(
            f"{TMDB_BASE_URL}/search/{mtype}",
            params=params,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            for r in data.get("results", []):
                # Accept result if it has backdrop OR poster
                if r.get("backdrop_path") or r.get("poster_path"):
                    r["_media_type"] = mtype
                    return r
    except Exception:
        pass
    return None


async def search_tmdb(title, media_type="tv", year=None) -> Optional[dict]:
    if not TMDB_API_KEY:
        return None

    variants    = _generate_title_variants(title)
    alt_type    = "movie" if media_type == "tv" else "tv"
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


# ==================== IMAGE DOWNLOAD ====================

async def _download_image(url: str, save_path: str) -> bool:
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


# ==================== IMAGE PROCESSING ====================

def _resize_backdrop(img_path: str, out_path: str) -> bool:
    """Backdrop is already ~16:9 — just resize to 1280x720."""
    try:
        img = Image.open(img_path).convert("RGB")
        img = img.resize((COVER_W, COVER_H), Image.LANCZOS)
        img.save(out_path, "JPEG", quality=95)
        return True
    except Exception as e:
        print(f"Backdrop resize error: {e}")
        return False

def _portrait_to_cover(img_path: str, out_path: str) -> bool:
    """
    Convert portrait poster to 1280x720:
    Blurred+darkened bg + sharp poster centered.
    """
    try:
        poster = Image.open(img_path).convert("RGB")
        bg = poster.resize((COVER_W, COVER_H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=40))
        bg = bg.point(lambda p: int(p * 0.55))

        scale = COVER_H / poster.height
        fg_w  = int(poster.width * scale)
        fg    = poster.resize((fg_w, COVER_H), Image.LANCZOS)

        x = (COVER_W - fg_w) // 2
        bg.paste(fg, (x, 0))
        bg.save(out_path, "JPEG", quality=95)
        return True
    except Exception as e:
        print(f"Portrait resize error: {e}")
        return False


# ==================== MAIN ENTRY ====================

async def get_tmdb_poster(filename: str, save_dir: str = "/tmp") -> Tuple[Optional[str], Optional[dict]]:
    """
    Full pipeline:
      filename → parse → TMDB search → 
      prefer backdrop (16:9) → fallback portrait poster →
      resize → return cover path
    """
    if not TMDB_API_KEY:
        return None, None

    title, media_type, year = parse_title_from_filename(filename)
    if not title:
        return None, None

    result = await search_tmdb(title, media_type, year)
    if not result:
        return None, None

    os.makedirs(save_dir, exist_ok=True)
    safe = re.sub(r"[^\w]", "_", title)[:40]

    backdrop_path = result.get("backdrop_path")
    poster_path   = result.get("poster_path")

    raw_path   = os.path.join(save_dir, f"tmdb_raw_{safe}.jpg")
    cover_path = os.path.join(save_dir, f"tmdb_cover_{safe}.jpg")

    # ── Try backdrop first (landscape 16:9) ──────────────────────────
    if backdrop_path:
        ok = await _download_image(f"{TMDB_BACKDROP}{backdrop_path}", raw_path)
        if ok:
            resized = _resize_backdrop(raw_path, cover_path)
            if os.path.exists(raw_path):
                os.remove(raw_path)
            if resized:
                return cover_path, result

    # ── Fallback: portrait poster with blurred bg ─────────────────────
    if poster_path:
        ok = await _download_image(f"{TMDB_POSTER}{poster_path}", raw_path)
        if ok:
            resized = _portrait_to_cover(raw_path, cover_path)
            if os.path.exists(raw_path):
                os.remove(raw_path)
            if resized:
                return cover_path, result

    return None, None
