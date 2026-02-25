# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional, List, Dict, Any
from config import MONGO_URL, DB_NAME, OWNER_ID
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# MongoDB client (initialized in main.py)
client: AsyncIOMotorClient = None
db = None
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat

async def init_db():
    """Initialize MongoDB connection."""
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Create indexes
    await db.users.create_index("user_id", unique=True)
    await db.admins.create_index("user_id", unique=True)
    
    # Add owner as admin by default
    await add_admin(OWNER_ID)
    print("✅ MongoDB connected")

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
async def close_db():
    """Close MongoDB connection."""
    global client
    if client:
        client.close()

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# ==================== CAPTION STYLE FUNCTIONS ====================

async def set_caption_style(user_id: int, style: str):
    """Set user's custom caption style."""
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"caption_style": style}},
        upsert=True
    )

async def get_caption_style(user_id: int) -> str:
    """Get user's caption style, defaults to 'normal'."""
    user = await db.users.find_one({"user_id": user_id})
    if user:
        return user.get("caption_style", "normal")
    return "normal"

# ==================== THUMBNAIL FUNCTIONS ====================

async def add_user(user_id: int, username: str = None, first_name: str = None):
    """Add or update a user."""
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "username": username,
                "first_name": first_name
            },
            "$setOnInsert": {
                "user_id": user_id,
                "thumbnail_file_id": None,
                "usage_count": 0,
                "banned": False
            }
        },
        upsert=True
    )
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Get user data."""
    return await db.users.find_one({"user_id": user_id})

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
async def get_all_users() -> List[Dict[str, Any]]:
    """Get all users."""
    return await db.users.find().to_list(length=None)
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat

async def get_user_count() -> int:
    """Get total user count."""
    return await db.users.count_documents({})

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# ==================== THUMBNAIL FUNCTIONS ====================

async def set_thumbnail(user_id: int, file_id: str):
    """Set user's thumbnail."""
    await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"thumbnail_file_id": file_id}}
    )

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
async def get_thumbnail(user_id: int) -> Optional[str]:
    """Get user's thumbnail file_id."""
    user = await db.users.find_one({"user_id": user_id})
    return user.get("thumbnail_file_id") if user else None
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschats

async def remove_thumbnail(user_id: int) -> bool:
    """Remove user's thumbnail."""
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"thumbnail_file_id": None}}
    )
    return result.modified_count > 0
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat

# ==================== USAGE TRACKING ====================

async def increment_usage(user_id: int):
    """Increment user's usage count."""
    await db.users.update_one(
        {"user_id": user_id},
        {"$inc": {"usage_count": 1}}
    )

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
async def get_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top users by usage count."""
    return await db.users.find(
        {"usage_count": {"$gt": 0}}
    ).sort("usage_count", -1).limit(limit).to_list(length=limit)

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# ==================== BAN FUNCTIONS ====================

async def ban_user(user_id: int) -> bool:
    """Ban a user."""
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"banned": True}}
    )
    return result.modified_count > 0

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschats
async def unban_user(user_id: int) -> bool:
    """Unban a user."""
    result = await db.users.update_one(
        {"user_id": user_id},
        {"$set": {"banned": False}}
    )
    return result.modified_count > 0

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschats
async def is_banned(user_id: int) -> bool:
    """Check if user is banned."""
    user = await db.users.find_one({"user_id": user_id})
    return user.get("banned", False) if user else False

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# ==================== ADMIN FUNCTIONS ====================

async def add_admin(user_id: int):
    """Add an admin."""
    await db.admins.update_one(
        {"user_id": user_id},
        {"$set": {"user_id": user_id}},
        upsert=True
    )

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
async def remove_admin(user_id: int) -> bool:
    """Remove an admin."""
    if user_id == OWNER_ID:
        return False  # Cannot remove owner
    result = await db.admins.delete_one({"user_id": user_id})
    return result.deleted_count > 0
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat

async def is_admin(user_id: int) -> bool:
    """Check if user is admin."""
    if user_id == OWNER_ID:
        return True
    admin = await db.admins.find_one({"user_id": user_id})
    return admin is not None

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
async def get_all_admins() -> List[int]:
    """Get all admin IDs."""
    admins = await db.admins.find().to_list(length=None)
    return [a["user_id"] for a in admins]
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
