# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat

import os
import asyncio
from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import LOG_CHANNEL
from database import (
    get_thumbnail, increment_usage, is_banned, add_user,
    get_caption_style, get_dump_channel, get_auto_poster, get_dump_fwd,
    get_cached_poster, set_cached_poster
)
from plugins.tmdb import get_tmdb_poster, parse_title_from_filename

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
    return STYLE_MAP.get(style, STYLE_MAP["bold"])(text)

SETTINGS_KBD = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
])

# ==================== VIDEO HANDLER ====================

@router.message(F.video)
async def handle_video(message: types.Message, bot: Bot):
    user_id    = message.from_user.id
    username   = message.from_user.username
    first_name = message.from_user.first_name

    # ── Quick ban check ──────────────────────────────────────────────
    if await is_banned(user_id):
        return await message.answer(small_caps("You are banned from using this bot."))

    # ── Fetch ALL user settings in ONE parallel call ─────────────────
    # Instead of 5 separate DB round-trips, fetch everything at once
    add_user_task  = asyncio.create_task(add_user(user_id, username, first_name))
    settings_task  = asyncio.create_task(_get_user_settings(user_id))

    await add_user_task
    thumb, style, auto_post, dump_fwd_on, dump_ch = await settings_task

    video       = message.video
    filename    = video.file_name or ""
    raw_caption = message.caption or ""
    caption     = apply_caption_style(raw_caption, style) if raw_caption else ""

    # ── Auto Poster OFF → use manual thumb only ───────────────────────
    if not auto_post:
        if not thumb:
            return await message.answer(
                f"<b>⚠️ {small_caps('No thumbnail set!')}</b>\n\n"
                f"<blockquote>{small_caps('Please set a thumbnail first using Settings.')}</blockquote>",
                parse_mode="HTML",
                reply_markup=SETTINGS_KBD
            )
        await _send_video(bot, message, video, caption, thumb, dump_fwd_on, dump_ch, user_id)
        await _log(bot, user_id, first_name, username, style, dump_ch, raw_caption, "manual_thumb")
        return

    # ── Auto Poster ON → try TMDB ────────────────────────────────────
    cover_file_id = None
    tmdb_result   = None
    used_source   = "manual_thumb"

    if filename:
        # Parse title for cache key lookup
        title, _, _, _ = parse_title_from_filename(filename)

        if title:
            # ── Check cache first (instant, no download) ────────────
            cover_file_id = await get_cached_poster(title)

            if cover_file_id:
                used_source = "tmdb_cached"
            else:
                # ── Cache miss → fetch from TMDB ───────────────────
                poster_path, tmdb_result = await get_tmdb_poster(filename)

                if poster_path and os.path.exists(poster_path):
                    used_source = "tmdb_fresh"
                    try:
                        # Upload poster → get file_id → cache it
                        uploaded = await bot.send_photo(
                            chat_id=message.chat.id,
                            photo=types.FSInputFile(poster_path),
                            disable_notification=True
                        )
                        cover_file_id = uploaded.photo[-1].file_id
                        # Delete the upload silently + cache file_id
                        await asyncio.gather(
                            bot.delete_message(message.chat.id, uploaded.message_id),
                            set_cached_poster(title, cover_file_id)
                        )
                    except Exception:
                        cover_file_id = None
                    finally:
                        if os.path.exists(poster_path):
                            os.remove(poster_path)

    # ── Decide which cover to use ─────────────────────────────────────
    if not cover_file_id:
        if thumb:
            cover_file_id = thumb
            used_source   = "manual_thumb_fallback"
            await message.answer(
                "ℹ️ <i>No TMDB poster found. Used your saved thumbnail.</i>",
                parse_mode="HTML"
            )
        else:
            # No cover at all — send without cover
            await bot.send_video(
                chat_id=message.chat.id,
                video=video.file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=SETTINGS_KBD
            )
            await message.answer(
                "✅ <i>VIDEO COPIED DIRECTLY TO CHANNEL (NO TMDB POSTER FOUND).</i>",
                parse_mode="HTML"
            )
            return

    # ── Send final video with cover ───────────────────────────────────
    await _send_video(bot, message, video, caption, cover_file_id, dump_fwd_on, dump_ch, user_id)
    await _log(bot, user_id, first_name, username, style, dump_ch, raw_caption, used_source, tmdb_result)


# ==================== HELPER FUNCTIONS ====================

async def _get_user_settings(user_id: int):
    """Fetch all user settings in parallel — one round-trip per field but concurrent."""
    thumb, style, auto_post, dump_fwd_on, dump_ch = await asyncio.gather(
        get_thumbnail(user_id),
        get_caption_style(user_id),
        get_auto_poster(user_id),
        get_dump_fwd(user_id),
        get_dump_channel(user_id),
    )
    return thumb, style, auto_post, dump_fwd_on, dump_ch


async def _send_video(bot: Bot, message, video, caption, cover_file_id, dump_fwd_on, dump_ch, user_id):
    """Send video with cover + optionally forward to dump channel."""
    await increment_usage(user_id)

    sent = await bot.send_video(
        chat_id=message.chat.id,
        video=video.file_id,
        caption=caption,
        parse_mode="HTML",
        cover=cover_file_id,
        reply_markup=SETTINGS_KBD
    )

    if dump_fwd_on and dump_ch:
        try:
            await bot.forward_message(
                chat_id=dump_ch,
                from_chat_id=message.chat.id,
                message_id=sent.message_id
            )
        except Exception:
            pass


async def _log(bot: Bot, user_id, first_name, username, style, dump_ch,
               caption, source, tmdb_result=None):
    if not LOG_CHANNEL:
        return
    try:
        tmdb_info = ""
        if tmdb_result:
            t = tmdb_result.get("title") or tmdb_result.get("name") or "N/A"
            m = tmdb_result.get("_media_type", "?").upper()
            tmdb_info = f"\n🎬 TMDB: {t} [{m}]"

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
