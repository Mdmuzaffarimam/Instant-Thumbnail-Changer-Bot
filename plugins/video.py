# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat
from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import LOG_CHANNEL
from database import get_thumbnail, increment_usage, is_banned, add_user, get_caption_style

router = Router()

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

def format_caption(text, style):
    if style == "bold":
        return f"<b>{text}</b>"
    if style == "italic":
        return f"<i>{text}</i>"
    if style == "mono":
        return f"<code>{text}</code>"
    if style == "bold_italic":
        return f"<b><i>{text}</i></b>"
    return text

@router.message(F.video)
async def handle_video(message: types.Message, bot: Bot):
    """Handle incoming video and send it back with user's thumbnail as cover."""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Check if banned
    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return
    
    # Add/update user
    await add_user(user_id, username, first_name)
    
    video = message.video
    
    # --- Yahan add kiya hai aapka code ---
    caption_text = message.caption or ""
    style = await get_caption_style(user_id) # database style call
    caption = format_caption(caption_text, style) # formatting call
    # ------------------------------------
    
    # Get user's thumbnail
    thumb_file_id = await get_thumbnail(user_id)
    
    # Build keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])
    
    if thumb_file_id:
        # Increment usage count
        await increment_usage(user_id)
        
        # Send video with custom cover and new caption
        await bot.send_video(
            chat_id=message.chat.id,
            video=video.file_id,
            caption=caption,
            parse_mode="HTML",
            cover=thumb_file_id,
            reply_markup=keyboard
        )
        
        # Log video
        if LOG_CHANNEL:
            try:
                await bot.send_message(
                    chat_id=LOG_CHANNEL,
                    text=f"📹 <b>ᴠɪᴅᴇᴏ ᴘʀᴏᴄᴇssᴇᴅ</b>\n\n🆔 <code>{user_id}</code>\n👤 {first_name}",
                    parse_mode="HTML"
                )
            except Exception:
                pass
    else:
        await message.answer(
            f"<b>⚠️ {small_caps('No thumbnail set!')}</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
