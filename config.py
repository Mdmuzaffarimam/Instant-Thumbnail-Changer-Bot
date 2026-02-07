# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
import os
import random
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# Bot Configuration
API_TOKEN = os.environ.get("API_TOKEN", "")
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# MongoDB
MONGO_URL = os.environ.get("MONGO_URL", "")
DB_NAME = "thumbnail_bot"
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# Owner/Admin
OWNER_ID = int(os.environ.get("OWNER_ID", ""))
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# UI URLs - Multiple images that rotate randomly
# Use DIRECT image URLs (https://i.ibb.co/...) not page URLs (https://ibb.co/...)
START_PICS = [
    "https://i.ibb.co/0jjgxKM4/changli-wuthering-waves-4k-wallpaper-uhdpaper-com-437-2-b.jpg",
    # Add more direct image URLs here
]
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
CHANNEL_URL = os.environ.get("CHANNEL_URL", "https://t.me/cantarellabots")
DEV_URL = os.environ.get("DEV_URL", "https://t.me/cantarella_wuwa")
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat

def get_random_pic() -> str:
    """Get a random image from START_PICS."""
    if START_PICS:
        return random.choice(START_PICS)
    return None
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat

