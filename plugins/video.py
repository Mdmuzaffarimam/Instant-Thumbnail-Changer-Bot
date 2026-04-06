# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat
from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import LOG_CHANNEL
from database import (
    get_thumbnail, increment_usage, is_banned, add_user,
    get_caption_style, get_dump_channel, get_auto_poster, get_dump_fwd
)

router = Router()

# ==================== HELPERS ====================

def small_caps(text: str) -> str:
    normal = "abcdefghijklmnopqrstuvwxyz"
    small  = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    result = ""
    for char in text:
        if char.lower() in normal:
            result += small[normal.index(char.lower())]
        else:
            result += char
    return result

STYLE_MAP = {
    "normal":     lambda t: t,
    "bold":       lambda t: f"<b>{t}</b>",
    "italic":     lambda t: f"<i>{t}</i>",
    "underline":  lambda t: f"<u>{t}</u>",
    "bolditalic": lambda t: f"<b><i>{t}</i></b>",
    "mono":       lambda t: f"<code>{t}</code>",
}

def apply_caption_style(text: str, style: str) -> str:
    """Wrap caption text in HTML tags based on chosen style."""
    if not text:
        return text
    fn = STYLE_MAP.get(style, STYLE_MAP["bold"])
    return fn(text)

# ==================== VIDEO HANDLER ====================

@router.message(F.video)
async def handle_video(message: types.Message, bot: Bot):
    """Handle incoming video — apply thumbnail + caption style + dump forward."""
    user_id    = message.from_user.id
    username   = message.from_user.username
    first_name = message.from_user.first_name

    # Ban check
    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return

    await add_user(user_id, username, first_name)

    video = message.video

    # --- Caption Style ---
    raw_caption = message.caption or ""
    style       = await get_caption_style(user_id)
    caption     = apply_caption_style(raw_caption, style) if raw_caption else ""

    # --- Thumbnail ---
    thumb_file_id = await get_thumbnail(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])

    if not thumb_file_id:
        await message.answer(
            f"<b>⚠️ {small_caps('No thumbnail set!')}</b>\n\n"
            f"<blockquote>{small_caps('Please set a thumbnail first using Settings.')}</blockquote>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        return

    # --- Auto Poster check ---
    auto_post = await get_auto_poster(user_id)
    if not auto_post:
        # Just forward as-is without applying thumbnail
        await message.forward(chat_id=message.chat.id)
        return

    await increment_usage(user_id)

    # --- Send video with custom cover ---
    sent = await bot.send_video(
        chat_id=message.chat.id,
        video=video.file_id,
        caption=caption,
        parse_mode="HTML",
        cover=thumb_file_id,
        reply_markup=keyboard
    )

    # --- Dump Forward ---
    dump_fwd_on = await get_dump_fwd(user_id)
    dump_ch     = await get_dump_channel(user_id)

    if dump_fwd_on and dump_ch:
        try:
            await bot.forward_message(
                chat_id=dump_ch,
                from_chat_id=message.chat.id,
                message_id=sent.message_id
            )
        except Exception as e:
            # Silently fail — channel might be wrong or bot not admin
            pass

    # --- Log ---
    if LOG_CHANNEL:
        try:
            await bot.send_message(
                chat_id=LOG_CHANNEL,
                text=(
                    f"📹 <b>ᴠɪᴅᴇᴏ ᴘʀᴏᴄᴇssᴇᴅ</b>\n\n"
                    f"🆔 <code>{user_id}</code>\n"
                    f"👤 {first_name} (@{username or 'N/A'})\n"
                    f"✏️ Style: {style.upper()}\n"
                    f"📁 Dump: {dump_ch or 'Not set'}\n"
                    f"📝 {raw_caption[:50] + '...' if len(raw_caption) > 50 else raw_caption or 'No caption'}"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass
