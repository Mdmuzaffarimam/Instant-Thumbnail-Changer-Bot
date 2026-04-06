# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat
import re
import aiohttp
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import LOG_CHANNEL, TMDB_API_KEY
from database import (
    get_thumbnail, set_thumbnail, remove_thumbnail,
    increment_usage, is_banned, add_user,
    get_caption_style, get_dump_channel, get_dump_fwd, get_auto_poster
)

router = Router()


def small_caps(text: str) -> str:
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


def apply_caption_style(text: str, style: str) -> str:
    """Apply Telegram formatting based on chosen style."""
    if not text:
        return text
    if style == "bold":
        return f"<b>{text}</b>"
    elif style == "italic":
        return f"<i>{text}</i>"
    elif style == "underline":
        return f"<u>{text}</u>"
    elif style == "bold_italic":
        return f"<b><i>{text}</i></b>"
    elif style == "mono":
        return f"<code>{text}</code>"
    else:  # normal
        return text


def extract_title_from_filename(filename: str) -> str:
    """Try to extract a clean title from video filename."""
    if not filename:
        return ""
    # Remove extension
    name = re.sub(r'\.[^.]+$', '', filename)
    # Replace dots/underscores/hyphens with spaces
    name = re.sub(r'[._\-]+', ' ', name)
    # Remove common patterns like S01E01, 720p, 1080p, etc.
    name = re.sub(r'\b(S\d+E\d+|E\d+|\d{3,4}p|WEB|BluRay|HDRip|x264|x265|AAC|DDP|DTS|HEVC|10bit)\b', '', name, flags=re.IGNORECASE)
    return name.strip()


async def fetch_tmdb_poster(title: str) -> str:
    """Fetch poster URL from TMDB for given title."""
    if not TMDB_API_KEY or not title:
        return None
    try:
        async with aiohttp.ClientSession() as session:
            # Try TV show first
            url = f"https://api.themoviedb.org/3/search/tv?api_key={TMDB_API_KEY}&query={title}&page=1"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                data = await resp.json()
                results = data.get("results", [])
                if results and results[0].get("poster_path"):
                    return f"https://image.tmdb.org/t/p/w500{results[0]['poster_path']}"

            # Try Movie
            url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={title}&page=1"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=8)) as resp:
                data = await resp.json()
                results = data.get("results", [])
                if results and results[0].get("poster_path"):
                    return f"https://image.tmdb.org/t/p/w500{results[0]['poster_path']}"
    except Exception:
        pass
    return None


# ==================== ✅ PHOTO HANDLER — Set Thumbnail Instantly ====================

@router.message(F.photo)
async def handle_photo(message: types.Message):
    """User sends a photo → instantly set as thumbnail."""
    user_id = message.from_user.id

    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return

    file_id = message.photo[-1].file_id
    await set_thumbnail(user_id, file_id)

    await message.answer(
        f"<b>✅ {small_caps('Thumbnail Updated!')}</b>\n\n"
        f"<blockquote>{small_caps('Your new cover has been saved. Send a video to use it.')}</blockquote>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
        ])
    )


# ==================== ✅ EXTRACT COVER ====================

@router.message(Command("extract_cover"))
async def extract_cover_cmd(message: types.Message, bot: Bot):
    """Extract thumbnail from a replied video and save it as user's cover."""
    user_id = message.from_user.id

    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return

    if not message.reply_to_message or not message.reply_to_message.video:
        await message.answer(
            f"<b>❌ {small_caps('Please reply to a video message with this command to extract its cover.')}</b>",
            parse_mode="HTML"
        )
        return

    video = message.reply_to_message.video
    thumb = video.thumbnail

    if not thumb:
        await message.answer(
            f"<b>⚠️ {small_caps('This video has no cover/thumbnail to extract.')}</b>",
            parse_mode="HTML"
        )
        return

    await set_thumbnail(user_id, thumb.file_id)

    await message.answer(
        f"<b>✅ {small_caps('Cover Extracted!')}</b>\n\n"
        f"<blockquote>{small_caps('The video cover has been saved as your thumbnail.')}</blockquote>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
        ])
    )


# ==================== ✅ REMOVE COVER ====================

@router.message(Command("remove_cover"))
async def remove_cover_cmd(message: types.Message):
    """Remove the user's saved thumbnail."""
    user_id = message.from_user.id

    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return

    removed = await remove_thumbnail(user_id)

    if removed:
        text = (
            f"<b>🗑️ {small_caps('Cover Removed!')}</b>\n\n"
            f"<blockquote>{small_caps('Your videos will now be sent without a custom cover.')}</blockquote>"
        )
    else:
        text = (
            f"<b>❌ {small_caps('No cover set!')}</b>\n\n"
            f"<blockquote>{small_caps('You have not set any thumbnail yet.')}</blockquote>"
        )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
        ])
    )


# ==================== ✅ VIDEO HANDLER ====================

@router.message(F.video)
async def handle_video(message: types.Message, bot: Bot):
    """Handle incoming video: apply thumbnail, caption style, TMDB poster, dump."""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return

    await add_user(user_id, username, first_name)

    video = message.video
    caption = message.caption or ""

    # Get user settings
    thumb_file_id = await get_thumbnail(user_id)
    style = await get_caption_style(user_id)
    dump_channel = await get_dump_channel(user_id)
    dump_fwd = await get_dump_fwd(user_id)
    auto_poster = await get_auto_poster(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])

    # ✅ TMDB Auto Poster — fetch poster if no thumb set
    tmdb_poster_url = None
    if auto_poster and not thumb_file_id and TMDB_API_KEY:
        title = extract_title_from_filename(video.file_name or caption)
        if title:
            tmdb_poster_url = await fetch_tmdb_poster(title)

    final_thumb = thumb_file_id  # user's saved thumb takes priority

    # ✅ Apply Caption Style
    styled_caption = apply_caption_style(caption, style) if caption else ""

    if final_thumb or tmdb_poster_url:
        await increment_usage(user_id)

        send_kwargs = dict(
            chat_id=message.chat.id,
            video=video.file_id,
            caption=styled_caption if styled_caption else None,
            parse_mode="HTML" if style != "normal" else None,
            reply_markup=keyboard
        )

        if final_thumb:
            send_kwargs["cover"] = final_thumb

        sent_msg = None

        if tmdb_poster_url and not final_thumb:
            # Download TMDB poster and send as cover
            try:
                from aiogram.types import URLInputFile
                send_kwargs["cover"] = URLInputFile(tmdb_poster_url)
                sent_msg = await bot.send_video(**send_kwargs)
                # Inform user TMDB poster was used
                await message.answer(
                    f"<b>🎬 {small_caps('TMDB Poster Used!')}</b>\n"
                    f"<blockquote>{small_caps('No thumbnail set, so TMDB poster was auto-applied.')}</blockquote>",
                    parse_mode="HTML"
                )
            except Exception:
                del send_kwargs["cover"]
                sent_msg = await bot.send_video(**send_kwargs)
        else:
            sent_msg = await bot.send_video(**send_kwargs)

        # ✅ Dump to channel
        if dump_channel and dump_fwd and sent_msg:
            try:
                await bot.copy_message(
                    chat_id=int(dump_channel),
                    from_chat_id=message.chat.id,
                    message_id=sent_msg.message_id
                )
            except Exception as e:
                await message.answer(
                    f"⚠️ <b>Dump failed:</b> <code>{str(e)[:100]}</code>",
                    parse_mode="HTML"
                )

        # Log to log channel
        if LOG_CHANNEL:
            try:
                await bot.send_message(
                    chat_id=LOG_CHANNEL,
                    text=f"📹 <b>ᴠɪᴅᴇᴏ ᴘʀᴏᴄᴇssᴇᴅ</b>\n\n"
                         f"🆔 <code>{user_id}</code>\n"
                         f"👤 {first_name} (@{username or 'N/A'})\n"
                         f"🎨 Style: {style}\n"
                         f"📢 Dumped: {'Yes' if dump_channel and dump_fwd else 'No'}\n"
                         f"📝 {caption[:50] + '...' if len(caption) > 50 else caption or 'No caption'}",
                    parse_mode="HTML"
                )
            except Exception:
                pass

    else:
        # No thumbnail, no TMDB → warn user
        await message.answer(
            f"<b>⚠️ {small_caps('No thumbnail set!')}</b>\n\n"
            f"<blockquote>"
            f"{small_caps('Set a thumbnail by:')}\n"
            f"• {small_caps('Sending a photo anytime')}\n"
            f"• {small_caps('Using /extract_cover on a video')}\n"
            f"• {small_caps('Enabling Auto Poster in Settings (needs TMDB key)')}"
            f"</blockquote>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
