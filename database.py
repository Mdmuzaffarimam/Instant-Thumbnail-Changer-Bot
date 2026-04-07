# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from config import MONGO_URL, DB_NAME, OWNER_ID

client: AsyncIOMotorClient = None
db = None

async def init_db():
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    await db.users.create_index("user_id", unique=True)
    await db.admins.create_index("user_id", unique=True)
    # TTL index: auto-delete poster cache after 7 days
    await db.poster_cache.create_index("created_at", expireAfterSeconds=604800)
    await db.poster_cache.create_index("cache_key", unique=True)
    await add_admin(OWNER_ID)
    print("✅ MongoDB connected")

async def close_db():
    global client
    if client:
        client.close()

# ==================== USER FUNCTIONS ====================

async def add_user(user_id: int, username: str = None, first_name: str = None):
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {"username": username, "first_name": first_name},
            "$setOnInsert": {
                "user_id": user_id,
                "thumbnail_file_id": None,
                "usage_count": 0,
                "banned": False,
                "caption_style": "bold",
                "dump_channel": None,
                "auto_poster": True,
                "dump_fwd": True,
            }
        },
        upsert=True
    )

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    return await db.users.find_one({"user_id": user_id})

async def get_all_users() -> List[Dict[str, Any]]:
    return await db.users.find().to_list(length=None)

async def get_user_count() -> int:
    return await db.users.count_documents({})

# ==================== THUMBNAIL FUNCTIONS ====================

async def set_thumbnail(user_id: int, file_id: str):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"thumbnail_file_id": file_id}}
    )

async def get_thumbnail(user_id: int) -> Optional[str]:
    user = await db.users.find_one({"user_id": user_id})
    return user.get("thumbnail_file_id") if user else None

async def remove_thumbnail(user_id: int) -> bool:
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"thumbnail_file_id": None}}
    )
    return result.modified_count > 0

# ==================== USAGE TRACKING ====================

async def increment_usage(user_id: int):
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"usage_count": 1}}
    )

async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    return await db.users.find(
        {"usage_count": {"$gt": 0}}
    ).sort("usage_count", -1).limit(limit).to_list(length=limit)

# ==================== BAN FUNCTIONS ====================

async def ban_user(user_id: int) -> bool:
    result = await db.users.update_one({"user_id": user_id}, {"$set": {"banned": True}})
    return result.modified_count > 0

async def unban_user(user_id: int) -> bool:
    result = await db.users.update_one({"user_id": user_id}, {"$set": {"banned": False}})
    return result.modified_count > 0

async def is_banned(user_id: int) -> bool:
    user = await db.users.find_one({"user_id": user_id})
    return user.get("banned", False) if user else False

# ==================== ADMIN FUNCTIONS ====================

async def add_admin(user_id: int):
    await db.admins.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )

async def remove_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return False
    result = await db.admins.delete_one({"user_id": user_id})
    return result.deleted_count > 0

async def is_admin(user_id: int) -> bool:
    if user_id == OWNER_ID:
        return True
    return await db.admins.find_one({"user_id": user_id}) is not None

async def get_all_admins() -> List[int]:
    admins = await db.admins.find().to_list(length=None)
    return [a["user_id"] for a in admins]

# ==================== CAPTION STYLE ====================

async def get_caption_style(user_id: int) -> str:
    user = await db.users.find_one({"user_id": user_id})
    return user.get("caption_style", "bold") if user else "bold"

async def set_caption_style(user_id: int, style: str):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"caption_style": style}},
        upsert=True
    )

# ==================== DUMP CHANNEL ====================

async def get_dump_channel(user_id: int) -> Optional[str]:
    user = await db.users.find_one({"user_id": user_id})
    return user.get("dump_channel") if user else None

async def set_dump_channel(user_id: int, channel_id: str):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"dump_channel": channel_id}},
        upsert=True
    )

# ==================== AUTO POSTER ====================

async def get_auto_poster(user_id: int) -> bool:
    user = await db.users.find_one({"user_id": user_id})
    return user.get("auto_poster", True) if user else True

async def set_auto_poster(user_id: int, value: bool):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"auto_poster": value}},
        upsert=True
    )

# ==================== DUMP FWD ====================

async def get_dump_fwd(user_id: int) -> bool:
    user = await db.users.find_one({"user_id": user_id})
    return user.get("dump_fwd", True) if user else True

async def set_dump_fwd(user_id: int, value: bool):
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"dump_fwd": value}},
        upsert=True
    )

# ==================== TMDB POSTER CACHE ====================
# Cache stores Telegram file_id of already-uploaded poster images.
# Key = show title (normalized). Avoids re-downloading + re-uploading same poster.

import re
from datetime import datetime, timezone

def _normalize_key(title: str) -> str:
    """Normalize title to a stable cache key."""
    return re.sub(r"[^\w]", "_", title.lower().strip())[:80]

async def get_cached_poster(title: str) -> Optional[str]:
    """Return cached Telegram file_id for this title, or None."""
    key = _normalize_key(title)
    doc = await db.poster_cache.find_one({"cache_key": key})
    return doc.get("file_id") if doc else None

async def set_cached_poster(title: str, file_id: str):
    """Store Telegram file_id for this title in cache."""
    key = _normalize_key(title)
    await db.poster_cache.update_one(
        {"cache_key": key},
        {
            "$set": {
                "cache_key": key,
                "file_id":   file_id,
                "title":     title,
                "created_at": datetime.now(timezone.utc)
            }
        },
        upsert=True
    )
