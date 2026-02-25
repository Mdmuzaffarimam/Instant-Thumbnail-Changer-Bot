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
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://mrnoffice692:PsO4VGHI9heKd7WA@cluster0.e7vboom.mongodb.net/?appName=Cluster0")
DB_NAME = "thumbnail_bot"
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# Owner/Admin
OWNER_ID = int(os.environ.get("OWNER_ID", "8512604416"))
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
# UI URLs - Multiple images that rotate randomly
# Use DIRECT image URLs (https://i.ibb.co/...) not page URLs (https://ibb.co/...)
START_PICS = [
    "http://telegraph.controller.bot/files/6630683090/AgACAgUAAxkBAAJgTGmfGX3GCLDYPVsg3Bw4IffcLEmtAAKxD2sbLHz4VLUKKUWrdm-0AQADAgADeQADOgQ",
    # Add more direct image URLs here
]
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
CHANNEL_URL = os.environ.get("CHANNEL_URL", "https://t.me/Mrn_Officialx")
DEV_URL = os.environ.get("DEV_URL", "https://t.me/mimam_officialx")
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1002338165303"))  # e.g., -100xxxxxxxxxxxx
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

