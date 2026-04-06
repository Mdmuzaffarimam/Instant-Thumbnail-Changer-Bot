# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat
import os
import random

# Bot Configuration
API_TOKEN = os.environ.get("API_TOKEN", "")

# MongoDB
MONGO_URL = os.environ.get("MONGO_URL", "mongodb+srv://mrnoffice692:PsO4VGHI9heKd7WA@cluster0.e7vboom.mongodb.net/?appName=Cluster0")
DB_NAME = "thumbnail_bot"

# Owner/Admin
OWNER_ID = int(os.environ.get("OWNER_ID", "7473323779"))

# UI URLs
START_PICS = [
    "http://telegraph.controller.bot/files/6630683090/AgACAgUAAxkBAAJgTGmfGX3GCLDYPVsg3Bw4IffcLEmtAAKxD2sbLHz4VLUKKUWrdm-0AQADAgADeQADOgQ",
]

CHANNEL_URL = os.environ.get("CHANNEL_URL", "https://t.me/Mrn_Officialx")
DEV_URL = os.environ.get("DEV_URL", "https://t.me/mimam_officialx")
LOG_CHANNEL = int(os.environ.get("LOG_CHANNEL", "-1002338165303"))

# ✅ TMDB API Key (get from https://www.themoviedb.org/settings/api)
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "2e6744a49a4fb7cc31accf2e067d78ea")

# ✅ Dump Channel ID (channel jahan videos copy honge, e.g. -1001234567890)
DUMP_CHANNEL = os.environ.get("DUMP_CHANNEL", "")  # e.g. "-1001234567890"

# ✅ Dump Forward toggle (True = forward to dump channel)
DUMP_FWD = os.environ.get("DUMP_FWD", "True").lower() == "true"

# ✅ Auto Poster toggle (True = TMDB se poster auto fetch karega)
AUTO_POSTER = os.environ.get("AUTO_POSTER", "True").lower() == "true"


def get_random_pic() -> str:
    """Get a random image from START_PICS."""
    if START_PICS:
        return random.choice(START_PICS)
    return None
