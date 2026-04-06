# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat
import re
import io
import aiohttp
from aiogram import Router, types, F, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile

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
    else:
        return text


def extract_title_from_filename(filename: str) -> str:
    if not filename:
        return ""
    name = re.sub(r'\.[^.]+$', '', filename)
    name = re.sub(r'[._\-]+', ' ', name)
    match = re.search(r'\bS\d{1,4}E\d{1,4}\b', name, flags=re.IGNORECASE)
    if match:
        name = name[:match.start()]
    name = re.sub(
        r'\b(\d{3,4}p|WEB DL|WEB|BluRay|HDRip|BRRip|DVDRip|HDCAM|x264|x265|'
        r'AAC|DDP|DTS|HEVC|10bit|JSTAR|Hindi|English|Tamil|Telugu|Multi|'
        r'Dubbed|mkv|mp4|avi|AMZN|NF|DSNP|Mrn Officialx|Mrn_Officialx)\b.*',
        '', name, flags=re.IGNORECASE
    )
    name = re.sub(r'\s+', ' ', name).strip()
    return name


async def download_file_id(bot: Bot, file_id: str) -> BufferedInputFile:
    """
    KEY FIX: Telegram file_id ko download karke BufferedInputFile banao.
    Aiogram 3.x mein thumbnail=string nahi chalta, InputFile object chahiye.
    """
    file = await bot.get_file(file_id)
    bot_token = bot.token
    url = f"https://api.telegram.org/file/bot{bot_token}/{file.file_path}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
            data = await resp.read()
    return BufferedInputFile(data, filename="thumbnail.jpg")


async def fetch_tmdb_poster_bytes(title: str):
    if not TMDB_API_KEY or not title:
        return None, None
    try:
        async with aiohttp.ClientSession() as session:
            for media_type in ["tv", "movie"]:
                url = f"https://api.themoviedb.org/3/search/{media_type}?api_key={TMDB_API_KEY}&query={title}&page=1"
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    data = await resp.json()
                    results = data.get("results", [])
                    if results and results[0].get("poster_path"):
                        img_url = f"https://image.tmdb.org/t/p/w500{results[0]['poster_path']}"
                        async with session.get(img_url, timeout=aiohttp.ClientTimeout(total=10)) as img_resp:
                            if img_resp.status == 200:
                                return await img_resp.read(), "poster.jpg"
    except Exception as e:
        print(f"TMDB error: {e}")
    return None, None


@router.message(F.photo)
async def handle_photo(message: types.Message):
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


@router.message(Command("extract_cover"))
async def extract_cover_cmd(message: types.Message, bot: Bot):
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


@router.message(Command("remove_cover"))
async def remove_cover_cmd(message: types.Message):
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return
    removed = await remove_thumbnail(user_id)
    text = (
        f"<b>🗑️ {small_caps('Cover Removed!')}</b>\n\n"
        f"<blockquote>{small_caps('Your videos will now be sent without a custom cover.')}</blockquote>"
        if removed else
        f"<b>❌ {small_caps('No cover set!')}</b>\n\n"
        f"<blockquote>{small_caps('You have not set any thumbnail yet.')}</blockquote>"
    )
    await message.answer(text, parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
        ])
    )


@router.message(F.video)
async def handle_video(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name

    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return

    await add_user(user_id, username, first_name)

    video = message.video
    caption = message.caption or ""

    thumb_file_id = await get_thumbnail(user_id)
    style = await get_caption_style(user_id)
    dump_channel = await get_dump_channel(user_id)
    dump_fwd = await get_dump_fwd(user_id)
    auto_poster = await get_auto_poster(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])

    styled_caption = apply_caption_style(caption, style) if caption else None
    parse_mode = "HTML" if style != "normal" and styled_caption else None

    # CASE 1: User ka saved thumbnail hai
    if thumb_file_id:
        await increment_usage(user_id)
        try:
            # ✅ FIX: file_id string ko BufferedInputFile mein convert karo
            thumb_input = await download_file_id(bot, thumb_file_id)
            sent_msg = await bot.send_video(
                chat_id=message.chat.id,
                video=video.file_id,
                caption=styled_caption,
                parse_mode=parse_mode,
                thumbnail=thumb_input,
                reply_markup=keyboard
            )
            await _dump_and_log(bot, message, sent_msg, user_id, first_name, username, caption, style, dump_channel, dump_fwd)
        except Exception as e:
            await message.answer(f"❌ Error: <code>{str(e)[:200]}</code>", parse_mode="HTML")
        return

    # CASE 2: TMDB Auto Poster
    if auto_poster and TMDB_API_KEY:
        title = extract_title_from_filename(video.file_name or caption)
        if title:
            processing_msg = await message.answer(
                f"<b>🔍 {small_caps('Fetching TMDB poster for: ' + title)}</b>",
                parse_mode="HTML"
            )
            poster_bytes, fname = await fetch_tmdb_poster_bytes(title)
            try:
                await processing_msg.delete()
            except Exception:
                pass

            if poster_bytes:
                await increment_usage(user_id)
                try:
                    thumb_input = BufferedInputFile(poster_bytes, filename=fname)
                    sent_msg = await bot.send_video(
                        chat_id=message.chat.id,
                        video=video.file_id,
                        caption=styled_caption,
                        parse_mode=parse_mode,
                        thumbnail=thumb_input,
                        reply_markup=keyboard
                    )
                    await message.answer(
                        f"<b>🎬 {small_caps('TMDB Poster Auto Applied!')}</b>\n"
                        f"<blockquote>{small_caps('Show: ' + title)}</blockquote>",
                        parse_mode="HTML"
                    )
                    await _dump_and_log(bot, message, sent_msg, user_id, first_name, username, caption, style, dump_channel, dump_fwd)
                except Exception as e:
                    await message.answer(f"❌ Error: <code>{str(e)[:200]}</code>", parse_mode="HTML")
                return
            else:
                await message.answer(
                    f"<b>⚠️ {small_caps('TMDB poster not found!')}</b>\n\n"
                    f"<blockquote>{small_caps('Please set a thumbnail manually.')}</blockquote>",
                    parse_mode="HTML", reply_markup=keyboard
                )
                return

    # CASE 3: Kuch nahi
    await message.answer(
        f"<b>⚠️ {small_caps('No thumbnail set!')}</b>\n\n"
        f"<blockquote>"
        f"{small_caps('Set a thumbnail by:')}\n"
        f"• {small_caps('Sending a photo anytime')}\n"
        f"• {small_caps('Using /extract_cover on a video')}\n"
        f"• {small_caps('Enabling Auto Poster in Settings (needs TMDB key)')}"
        f"</blockquote>",
        parse_mode="HTML", reply_markup=keyboard
    )


async def _dump_and_log(bot, message, sent_msg, user_id, first_name, username, caption, style, dump_channel, dump_fwd):
    if dump_channel and dump_fwd and sent_msg:
        try:
            await bot.copy_message(
                chat_id=int(dump_channel),
                from_chat_id=message.chat.id,
                message_id=sent_msg.message_id
            )
        except Exception as e:
            await message.answer(f"⚠️ <b>Dump failed:</b> <code>{str(e)[:100]}</code>", parse_mode="HTML")

    if LOG_CHANNEL:
        try:
            await bot.send_message(
                chat_id=LOG_CHANNEL,
                text=f"📹 <b>ᴠɪᴅᴇᴏ ᴘʀᴏᴄᴇssᴇᴅ</b>\n\n"
                     f"🆔 <code>{user_id}</code>\n"
                     f"👤 {first_name} (@{username or 'N/A'})\n"
                     f"🎨 Style: {style}\n"
                     f"📢 Dumped: {'✅' if dump_channel and dump_fwd else '❌'}\n"
                     f"📝 {caption[:50] + '...' if len(caption) > 50 else caption or 'No caption'}",
                parse_mode="HTML"
            )
        except Exception:
            pass
