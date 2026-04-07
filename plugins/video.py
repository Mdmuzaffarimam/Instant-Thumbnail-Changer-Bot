# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat
import asyncio
import subprocess
import os
from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import LOG_CHANNEL
from database import (
    get_thumbnail, increment_usage, is_banned, add_user,
    get_caption_style, get_auto_poster, get_dump_fwd, get_dump_channel,
)
from plugins.settings import apply_caption_style

router = Router()

THUMB_DIR = "thumbnails"
os.makedirs(THUMB_DIR, exist_ok=True)


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


# ── /extract_cover command ─────────────────────────────────────────────────────

@router.message(F.text == "/extract_cover")
async def extract_cover(message: types.Message, bot: Bot):
    """Reply to a video with /extract_cover to extract its thumbnail."""
    replied = message.reply_to_message

    if not replied or not (replied.video or replied.document):
        await message.answer(
            f"<b>❌ {small_caps('Please reply to a video message with this command to extract its cover.')}</b>",
            parse_mode="HTML"
        )
        return

    media = replied.video or replied.document

    # Check if media has an inline thumbnail
    if media.thumbnail:
        thumb_file_id = media.thumbnail.file_id
        await bot.send_photo(
            chat_id=message.chat.id,
            photo=thumb_file_id,
            caption=(
                f"<b>✅ {small_caps('Cover extracted successfully!')}</b>\n\n"
                f"<blockquote>{small_caps('You can send this image to set it as your thumbnail.')}</blockquote>"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
            ])
        )
        return

    # Fallback: download video and extract frame with ffmpeg
    status_msg = await message.answer(f"⏳ {small_caps('Extracting cover, please wait...')}", parse_mode="HTML")

    file = await bot.get_file(media.file_id)
    video_path = os.path.join(THUMB_DIR, f"{message.from_user.id}_video.mp4")
    thumb_path = os.path.join(THUMB_DIR, f"{message.from_user.id}_extracted.jpg")

    try:
        await bot.download_file(file.file_path, destination=video_path)
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-i", video_path,
            "-ss", "00:00:01", "-vframes", "1", thumb_path,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()

        if os.path.exists(thumb_path):
            await status_msg.delete()
            await bot.send_photo(
                chat_id=message.chat.id,
                photo=types.FSInputFile(thumb_path),
                caption=(
                    f"<b>✅ {small_caps('Cover extracted successfully!')}</b>\n\n"
                    f"<blockquote>{small_caps('You can send this image to set it as your thumbnail.')}</blockquote>"
                ),
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
                ])
            )
        else:
            await status_msg.edit_text(f"<b>❌ {small_caps('Failed to extract cover from this video.')}</b>", parse_mode="HTML")

    except Exception as e:
        await status_msg.edit_text(f"<b>❌ Error: <code>{e}</code></b>", parse_mode="HTML")

    finally:
        for path in [video_path, thumb_path]:
            if os.path.exists(path):
                os.remove(path)


# ── Video handler ──────────────────────────────────────────────────────────────

@router.message(F.video)
async def handle_video(message: types.Message, bot: Bot):
    """Handle incoming video: apply thumbnail, caption style, dump forward."""
    user_id    = message.from_user.id
    username   = message.from_user.username
    first_name = message.from_user.first_name

    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return

    await add_user(user_id, username, first_name)

    video        = message.video
    raw_caption  = message.caption or ""
    thumb_file_id = await get_thumbnail(user_id)
    auto_poster  = await get_auto_poster(user_id)
    dump_fwd     = await get_dump_fwd(user_id)
    dump_channel = await get_dump_channel(user_id)
    style        = await get_caption_style(user_id)

    # Apply caption style if caption exists
    caption = apply_caption_style(raw_caption, style) if raw_caption else ""

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

    # Auto Poster OFF → send video without thumbnail
    if not auto_poster:
        await bot.send_video(
            chat_id=message.chat.id,
            video=video.file_id,
            caption=caption or raw_caption,
            parse_mode="HTML" if caption else None,
            reply_markup=keyboard
        )
        return

    # Send video WITH custom cover
    await increment_usage(user_id)

    sent = await bot.send_video(
        chat_id=message.chat.id,
        video=video.file_id,
        caption=caption,
        parse_mode="HTML" if caption else None,
        cover=thumb_file_id,
        reply_markup=keyboard
    )

    # Dump Forward → forward to dump channel if set and enabled
    if dump_fwd and dump_channel:
        try:
            await bot.forward_message(
                chat_id=dump_channel,
                from_chat_id=message.chat.id,
                message_id=sent.message_id
            )
        except Exception:
            pass  # Silently fail if forward fails

    # Log to log channel
    if LOG_CHANNEL:
        try:
            short_cap = raw_caption[:50] + "..." if len(raw_caption) > 50 else raw_caption or "No caption"
            await bot.send_message(
                chat_id=LOG_CHANNEL,
                text=(
                    f"📹 <b>ᴠɪᴅᴇᴏ ᴘʀᴏᴄᴇssᴇᴅ</b>\n\n"
                    f"🆔 <code>{user_id}</code>\n"
                    f"👤 {first_name} (@{username or 'N/A'})\n"
                    f"📝 {short_cap}"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass
