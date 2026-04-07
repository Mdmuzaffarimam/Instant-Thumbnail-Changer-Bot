# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat

import os
from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import LOG_CHANNEL
from database import (
    get_thumbnail, increment_usage, is_banned, add_user,
    get_caption_style, get_dump_channel, get_auto_poster, get_dump_fwd
)
from plugins.tmdb import get_tmdb_poster

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
    if not text:
        return text
    fn = STYLE_MAP.get(style, STYLE_MAP["bold"])
    return fn(text)

# ==================== VIDEO HANDLER ====================

@router.message(F.video)
async def handle_video(message: types.Message, bot: Bot):
    user_id    = message.from_user.id
    username   = message.from_user.username
    first_name = message.from_user.first_name

    # ── Ban check ────────────────────────────────────────────────────
    if await is_banned(user_id):
        return await message.answer(small_caps("You are banned from using this bot."))

    await add_user(user_id, username, first_name)

    video       = message.video
    filename    = video.file_name or ""
    raw_caption = message.caption or ""

    # ── Caption style ────────────────────────────────────────────────
    style   = await get_caption_style(user_id)
    caption = apply_caption_style(raw_caption, style) if raw_caption else ""

    # ── Settings ─────────────────────────────────────────────────────
    auto_post  = await get_auto_poster(user_id)
    dump_fwd_on = await get_dump_fwd(user_id)
    dump_ch    = await get_dump_channel(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])

    # ── If Auto Poster is OFF → just send as-is ───────────────────────
    if not auto_post:
        user_thumb = await get_thumbnail(user_id)
        if not user_thumb:
            return await message.answer(
                f"<b>⚠️ {small_caps('No thumbnail set!')}</b>\n\n"
                f"<blockquote>{small_caps('Please set a thumbnail first using Settings.')}</blockquote>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        await increment_usage(user_id)
        sent = await bot.send_video(
            chat_id=message.chat.id,
            video=video.file_id,
            caption=caption,
            parse_mode="HTML",
            cover=user_thumb,
            reply_markup=keyboard
        )
        await _maybe_dump(bot, sent, dump_fwd_on, dump_ch, message.chat.id)
        await _log(bot, user_id, first_name, username, style, dump_ch, raw_caption, "manual_thumb")
        return

    # ── Auto Poster is ON → try TMDB first ────────────────────────────
    poster_path = None
    tmdb_result = None
    used_source = "manual_thumb"  # for logging

    if filename:
        poster_path, tmdb_result = await get_tmdb_poster(filename)

    if poster_path and os.path.exists(poster_path):
        # ── TMDB poster found ─────────────────────────────────────────
        used_source = "tmdb"
        try:
            # Upload poster as photo to get a file_id
            uploaded = await bot.send_photo(
                chat_id=message.chat.id,
                photo=types.FSInputFile(poster_path),
                disable_notification=True
            )
            cover_file_id = uploaded.photo[-1].file_id
            # Delete the temp upload silently
            await bot.delete_message(message.chat.id, uploaded.message_id)

            await increment_usage(user_id)
            sent = await bot.send_video(
                chat_id=message.chat.id,
                video=video.file_id,
                caption=caption,
                parse_mode="HTML",
                cover=cover_file_id,
                reply_markup=keyboard
            )
            await _maybe_dump(bot, sent, dump_fwd_on, dump_ch, message.chat.id)
            await _log(bot, user_id, first_name, username, style, dump_ch, raw_caption, used_source, tmdb_result)
        except Exception as e:
            # TMDB upload failed — fall back to manual thumb or notify
            await _fallback(bot, message, video, caption, keyboard, dump_fwd_on, dump_ch,
                            user_id, first_name, username, style, raw_caption)
        finally:
            if os.path.exists(poster_path):
                os.remove(poster_path)

    else:
        # ── TMDB poster NOT found ─────────────────────────────────────
        user_thumb = await get_thumbnail(user_id)

        if user_thumb:
            # Use manual thumbnail as fallback
            used_source = "manual_thumb_fallback"
            await increment_usage(user_id)
            sent = await bot.send_video(
                chat_id=message.chat.id,
                video=video.file_id,
                caption=caption,
                parse_mode="HTML",
                cover=user_thumb,
                reply_markup=keyboard
            )
            # Notify user TMDB not found
            await message.answer(
                f"<b>ℹ️ {small_caps('No TMDB poster found.')}</b>\n"
                f"<blockquote>{small_caps('Used your saved thumbnail instead.')}</blockquote>",
                parse_mode="HTML"
            )
            await _maybe_dump(bot, sent, dump_fwd_on, dump_ch, message.chat.id)
            await _log(bot, user_id, first_name, username, style, dump_ch, raw_caption, used_source)

        else:
            # No TMDB + no manual thumb → copy video directly
            await bot.send_video(
                chat_id=message.chat.id,
                video=video.file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=keyboard
            )
            await message.answer(
                f"✅ <i>VIDEO COPIED DIRECTLY TO CHANNEL (NO TMDB POSTER FOUND).</i>",
                parse_mode="HTML"
            )


# ==================== FALLBACK (TMDB upload failed) ====================

async def _fallback(bot, message, video, caption, keyboard,
                    dump_fwd_on, dump_ch, user_id, first_name, username, style, raw_caption):
    user_thumb = await get_thumbnail(user_id)
    if user_thumb:
        await increment_usage(user_id)
        sent = await bot.send_video(
            chat_id=message.chat.id,
            video=video.file_id,
            caption=caption,
            parse_mode="HTML",
            cover=user_thumb,
            reply_markup=keyboard
        )
        await _maybe_dump(bot, sent, dump_fwd_on, dump_ch, message.chat.id)
        await _log(bot, user_id, first_name, username, style, dump_ch, raw_caption, "fallback_manual")
    else:
        await bot.send_video(
            chat_id=message.chat.id,
            video=video.file_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await message.answer(
            "✅ <i>VIDEO COPIED DIRECTLY TO CHANNEL (NO TMDB POSTER FOUND).</i>",
            parse_mode="HTML"
        )


# ==================== HELPERS ====================

async def _maybe_dump(bot: Bot, sent_msg, dump_fwd_on: bool, dump_ch, chat_id):
    """Forward sent video to dump channel if enabled."""
    if dump_fwd_on and dump_ch:
        try:
            await bot.forward_message(
                chat_id=dump_ch,
                from_chat_id=chat_id,
                message_id=sent_msg.message_id
            )
        except Exception:
            pass


async def _log(bot: Bot, user_id, first_name, username, style, dump_ch, caption, source, tmdb_result=None):
    """Send log to LOG_CHANNEL."""
    if not LOG_CHANNEL:
        return
    try:
        tmdb_info = ""
        if tmdb_result:
            title = tmdb_result.get("title") or tmdb_result.get("name") or "N/A"
            mtype = tmdb_result.get("_media_type", "?").upper()
            tmdb_info = f"\n🎬 TMDB: {title} [{mtype}]"

        await bot.send_message(
            chat_id=LOG_CHANNEL,
            text=(
                f"📹 <b>ᴠɪᴅᴇᴏ ᴘʀᴏᴄᴇssᴇᴅ</b>\n\n"
                f"🆔 <code>{user_id}</code>\n"
                f"👤 {first_name} (@{username or 'N/A'})\n"
                f"✏️ Style: {style.upper()}\n"
                f"🖼 Source: {source}\n"
                f"📁 Dump: {dump_ch or 'Not set'}"
                f"{tmdb_info}\n"
                f"📝 {caption[:50] + '...' if len(caption) > 50 else caption or 'No caption'}"
            ),
            parse_mode="HTML"
        )
    except Exception:
        pass
