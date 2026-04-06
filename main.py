# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio
from flask import Flask
import threading
import os

from config import API_TOKEN
from database import init_db, close_db
from plugins import start_router, settings_router, video_router, admin_router
from plugins.cover_tools import router as cover_tools_router  # NEW

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

# Register routers
dp.include_router(start_router)
dp.include_router(settings_router)
dp.include_router(video_router)
dp.include_router(admin_router)
dp.include_router(cover_tools_router)  # NEW

# Flask health check server
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot Made By @Mrn_Officialx"

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

async def main():
    await init_db()
    print("🚀 Bot is starting...")
    try:
        await dp.start_polling(bot)
    finally:
        await close_db()

if __name__ == "__main__":
    print(r"""
    ███╗░░░███╗░░░███████╗██████╗░░█████╗░████████╗███████╗
    ████╗░████║░░░╚════██║██╔══██╗██╔══██╗╚══██╔══╝╚════██║
    ██╔████╔██║░░░░░███╔═╝██████╦╝██║░░██║░░░██║░░░░░███╔═╝
    ██║╚██╔╝██║░░░██╔══╝░░██╔══██╗██║░░██║░░░██║░░░██╔══╝░░
    ██║░╚═╝░██║░░░███████╗██████╦╝╚█████╔╝░░░██║░░░███████╗
    ╚═╝░░░░░╚═╝░░░╚══════╝╚═════╝░░╚════╝░░░░╚═╝░░░╚══════╝

      BOT WORKING PROPERLY....
    """)
    print("Starting Bot...")
    threading.Thread(target=run_flask, daemon=True).start()
    asyncio.run(main())
