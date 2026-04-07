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
TMDB_POSTER   = "https://image.tmdb.org/t/p/w780"
TMDB_BACKDROP = "https://image.tmdb.org/t/p/w1280"

COVER_W = 1280
COVER_H = 720

# ==================== JUNK PREFIX REMOVAL ====================

_JUNK_PREFIX = re.compile(
    r"^(THE\s+PROFESSOR|PROFESSOR|PAHE|YIFY|RARBG|EZTV|FGT|DEFLATE"
    r"|PSA|ION10|ETHD|MkvCinemas|ExtraFlix|HDHub4u|HDHub"
    r"|OTT[_\s]?Downloader[_\s]?Bot|Mrn[_\s]?Officialx"
    r"|Yamraaj|Pahe|Strange|TamilMV|MoviesVerse|Telly|Bolly)\s+",
    re.IGNORECASE
)

# ==================== FILENAME PARSER ====================

_END_MARKERS = re.compile(
    r"[\.\s_]("
    r"S\d{1,2}[\s.]?E\d{1,3}|S\d{1,2}(?=\s|$|\.|_)"
    r"|E\d{2}-\d{2}|COMBINED|COMPLETE|SEASON"
    r"|19\d{2}|20\d{2}"
    r"|480p|720p|1080p|2160p|4[Kk]|240p|360p"
    r"|WEB[.\-]?DL|WEBRip|BluRay|BRRip|BDRip|HDTV"
    r"|AMZN|NF|ZEE5|JHS|JSTAR|ZWN|OTT|Netflix|DSNP|HULU|ATVP|SLIV"
    r"|AAC[\d.]*|DDP[\d.]*|DD[\d.]+|DTS|FLAC|MP3|AC3"
    r"|x264|x265|H\.?264|H\.?265|HEVC|AVC|XviD"
    r"|DVDRip|HDRip|CAMRip|DVDScr"
    r"|Hindi|English|Tamil|Telugu|Malayalam|Bengali|Punjabi|Dual|Multi|MULTi|MSubs|iNT"
    r"|REPACK|PROPER|EXTENDED|UNRATED|THEATRICAL|10Bit|10bit"
    r")",
    re.IGNORECASE
)

def _clean_title(title: str) -> str:
    title = re.sub(r"\(\s*(?:19|20)\d{2}\s*\)", "", title)
    title = re.sub(r"\([^)]*\)", "", title)
    title = re.sub(r"\[[^\]]*\]", "", title)
    title = re.sub(r"[\s\-_~]+$", "", title)
    title = re.sub(r"^[\s\-_~]+", "", title)
    title = re.sub(r"\s{2,}", " ", title)
    return title.strip()

def parse_title_from_filename(filename: str) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
    name = os.path.splitext(filename)[0]
    name = re.sub(r"[._]", " ", name)
    name = re.sub(r"\s*-\s*(?=[A-Za-z])", " ", name)
    name = name.strip()
    name = _JUNK_PREFIX.sub("", name).strip()

    year_match = re.search(r"[\(\s]*(19\d{2}|20\d{2})[\)\s]", name)
    year = int(year_match.group(1)) if year_match else None

    se_match = re.search(r"\bS(\d{1,2})E(\d{1,3})\b", name, re.IGNORECASE)
    s_only   = re.search(r"\bS(\d{1,2})\b(?!\s*E)", name, re.IGNORECASE) if not se_match else None
    season     = int(se_match.group(1)) if se_match else (int(s_only.group(1)) if s_only else None)
    media_type = "tv" if (se_match or s_only) else "movie"

    match     = _END_MARKERS.search(name)
    raw_title = name[: match.start()].strip() if match else name.strip()
    title     = _clean_title(raw_title)

    return title if title else None, media_type, year, season


# ==================== TITLE SIMILARITY CHECK ====================

_STOPWORDS = {"the", "a", "an", "of", "in", "on", "at", "to", "and", "or",
              "is", "are", "was", "were", "be", "been"}

def _normalize(t: str) -> str:
    return re.sub(r"[^\w\s]", "", t.lower()).strip()

def _sig_words(t: str) -> List[str]:
    return [w for w in _normalize(t).split() if w not in _STOPWORDS]

def title_matches(searched: str, returned: str) -> bool:
    """
    Returns True only if returned title is the same show as searched.

    Rules:
    - All significant words of searched must appear in returned (in order)
    - Returned may have up to 2 extra significant words (for subtitles)
    - This blocks "The Boys" → "The Boys from Brazil" (3 extra sig words)
    """
    if _normalize(searched) == _normalize(returned):
        return True

    s_sig = _sig_words(searched)
    r_sig = _sig_words(returned)

    if not s_sig:
        return _normalize(returned).startswith(_normalize(searched))

    # Match all searched sig words in order in returned
    j = 0
    for word in s_sig:
        found = False
        while j < len(r_sig):
            if r_sig[j] == word:
                j += 1
                found = True
                break
            j += 1
        if not found:
            return False

    # Allow at most 2 extra significant words in returned
    extra = len(r_sig) - len(s_sig)
    return extra <= 2


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

async def _search_single(session, query: str, mtype: str, year=None) -> Optional[dict]:
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
                if not (r.get("poster_path") or r.get("backdrop_path")):
                    continue
                # ── Strict title check ────────────────────────────────
                returned_name = r.get("name") or r.get("title") or ""
                if not title_matches(query, returned_name):
                    continue   # wrong show — skip
                r["_media_type"] = mtype
                return r
    except Exception:
        pass
    return None


async def _get_season_poster(session, tmdb_id: int, season: int) -> Optional[str]:
    try:
        async with session.get(
            f"{TMDB_BASE_URL}/tv/{tmdb_id}/season/{season}",
            params={"api_key": TMDB_API_KEY, "language": "en-US"},
            timeout=aiohttp.ClientTimeout(total=8)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("poster_path")
    except Exception:
        pass
    return None


async def search_tmdb(title: str, media_type: str = "tv", year: int = None,
                      season: int = None) -> Tuple[Optional[dict], Optional[str]]:
    if not TMDB_API_KEY:
        return None, None

    variants    = _generate_title_variants(title)
    alt_type    = "movie" if media_type == "tv" else "tv"
    types_order = [media_type, alt_type]

    async with aiohttp.ClientSession() as session:
        result = None
        for variant in variants:
            for mtype in types_order:
                if year:
                    r = await _search_single(session, variant, mtype, year)
                    if r:
                        result = r
                        break
                r = await _search_single(session, variant, mtype, None)
                if r:
                    result = r
                    break
            if result:
                break

        if not result:
            return None, None

        season_poster = None
        if season and result.get("_media_type") == "tv" and result.get("id"):
            season_poster = await _get_season_poster(session, result["id"], season)

        return result, season_poster


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

def _portrait_to_cover(img_path: str, out_path: str) -> bool:
    try:
        poster = Image.open(img_path).convert("RGB")
        bg = poster.resize((COVER_W, COVER_H), Image.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=45))
        bg = bg.point(lambda p: int(p * 0.5))
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

def _backdrop_to_cover(img_path: str, out_path: str) -> bool:
    try:
        img = Image.open(img_path).convert("RGB")
        img = img.resize((COVER_W, COVER_H), Image.LANCZOS)
        img.save(out_path, "JPEG", quality=95)
        return True
    except Exception as e:
        print(f"Backdrop resize error: {e}")
        return False


# ==================== MAIN ENTRY ====================

async def get_tmdb_poster(filename: str, save_dir: str = "/tmp") -> Tuple[Optional[str], Optional[dict]]:
    if not TMDB_API_KEY:
        return None, None

    title, media_type, year, season = parse_title_from_filename(filename)
    if not title:
        return None, None

    result, season_poster = await search_tmdb(title, media_type, year, season)
    if not result:
        return None, None

    os.makedirs(save_dir, exist_ok=True)
    safe       = re.sub(r"[^\w]", "_", title)[:40]
    raw_path   = os.path.join(save_dir, f"tmdb_raw_{safe}.jpg")
    cover_path = os.path.join(save_dir, f"tmdb_cover_{safe}.jpg")

    # Priority 1: Backdrop (full 16:9 landscape) ✅
    if result.get("backdrop_path"):
        ok = await _download_image(f"{TMDB_BACKDROP}{result['backdrop_path']}", raw_path)
        if ok:
            resized = _backdrop_to_cover(raw_path, cover_path)
            if os.path.exists(raw_path): os.remove(raw_path)
            if resized:
                return cover_path, result

    # Priority 2: Season-specific poster (fallback)
    if season_poster:
        ok = await _download_image(f"{TMDB_POSTER}{season_poster}", raw_path)
        if ok:
            resized = _portrait_to_cover(raw_path, cover_path)
            if os.path.exists(raw_path): os.remove(raw_path)
            if resized:
                return cover_path, result

    # Priority 3: Main poster (last fallback)
    if result.get("poster_path"):
        ok = await _download_image(f"{TMDB_POSTER}{result['poster_path']}", raw_path)
        if ok:
            resized = _portrait_to_cover(raw_path, cover_path)
            if os.path.exists(raw_path): os.remove(raw_path)
            if resized:
                return cover_path, result

    return None, None
