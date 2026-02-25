# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, URLInputFile
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
from config import CHANNEL_URL, DEV_URL, get_random_pic, LOG_CHANNEL
from database import add_user, is_banned, get_user
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
router = Router()
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat

def small_caps(text: str) -> str:
    """Convert text to small caps unicode."""
    normal = "abcdefghijklmnopqrstuvwxyz"
    small = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    result = ""
    for char in text:
        if char.lower() in normal:
            idx = normal.index(char.lower())
            result += small[idx]
        else:
            result += char
    return result

# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
@router.message(Command("start"))
async def start_cmd(message: types.Message, bot: Bot):
    """Handle /start command with image and buttons."""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Check if banned
    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return
    
    # Check if new user
    existing_user = await get_user(user_id)
    is_new_user = existing_user is None
    
    # Add/update user in database
    await add_user(user_id, username, first_name)
    
    # Log new user to log channel
    if is_new_user and LOG_CHANNEL:
        try:
            await bot.send_message(
                chat_id=LOG_CHANNEL,
                text=f"👤 <b>ɴᴇᴡ ᴜsᴇʀ</b>\n\n"
                     f"🆔 <code>{user_id}</code>\n"
                     f"👤 {first_name}\n"
                     f"🔗 @{username or 'N/A'}",
                parse_mode="HTML"
            )
        except Exception:
            pass
    
    # Welcome text in small caps with blockquote
    welcome_text = (
        f"<b>{small_caps('Welcome to Thumbnail Bot!')}</b>\n\n"
        f"<b><blockquote>{small_caps('Send me a video and I will add your custom thumbnail to it.')}</blockquote></b>\n\n"
        f"<b>{small_caps('How to use:')}\n"
        f"<blockquote>"
        f"1️ {small_caps('Set your thumbnail in Settings')}\n"
        f"2️ {small_caps('Send any video')}\n"
        f"3️ {small_caps('Get video with your thumbnail!')}"
        f"</blockquote></b>"
    )
    
    # Buttons
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL),
            InlineKeyboardButton(text="👨‍💻 Developer", url=DEV_URL)
        ],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])
    
    # Get random image
    pic_url = get_random_pic()
    
    # Send image with caption
    if pic_url:
        try:
            photo = URLInputFile(pic_url)
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=photo,
                caption=welcome_text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            return
        except Exception:
            pass
    
    # Fallback if image fails or no image
    await message.answer(
        welcome_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
#Supoort group @rexbotschat
