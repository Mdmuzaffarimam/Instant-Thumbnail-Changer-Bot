# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat

import os
import aiohttp
import aiofiles
from aiogram import Router, types, F, Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.exceptions import TelegramBadRequest

from config import CHANNEL_URL, DEV_URL
from database import (
    get_thumbnail, set_thumbnail, remove_thumbnail, is_banned,
    get_caption_style, set_caption_style,
    get_dump_channel, set_dump_channel,
    get_auto_poster, set_auto_poster,
    get_dump_fwd, set_dump_fwd,
    add_user
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
    if not text:
        return text
    return STYLE_MAP.get(style, STYLE_MAP["bold"])(text)

# ==================== FSM STATES ====================

class SettingsState(StatesGroup):
    waiting_for_dump_channel = State()

# ==================== KEYBOARDS ====================

async def get_main_settings_keyboard(user_id: int) -> InlineKeyboardMarkup:
    thumb      = await get_thumbnail(user_id)
    dump_ch    = await get_dump_channel(user_id)
    auto_post  = await get_auto_poster(user_id)
    dump_fwd_v = await get_dump_fwd(user_id)

    auto_label = "✨ ON" if auto_post  else "❌ OFF"
    fwd_label  = "🟢 ON" if dump_fwd_v else "🔴 OFF"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📁 Add Dump Channel",              callback_data="add_dump")],
        [InlineKeyboardButton(text="📝 Caption Style",                 callback_data="caption_style_menu")],
        [InlineKeyboardButton(text=f"✨ Auto Poster: {auto_label}",   callback_data="toggle_auto_poster")],
        [InlineKeyboardButton(text=f"🟢 Dump Fwd: {fwd_label}",      callback_data="toggle_dump_fwd")],
        [InlineKeyboardButton(text="👁️ View Thumbnail",               callback_data="view_thumb")],
        [InlineKeyboardButton(text="🗑️ Remove Thumbnail",             callback_data="remove_thumb")],
        [InlineKeyboardButton(text="🔙 Back",                          callback_data="back_to_start")],
        [InlineKeyboardButton(text="❌ Close",                         callback_data="close_settings")],
    ])

async def get_settings_text(user_id: int) -> str:
    thumb      = await get_thumbnail(user_id)
    dump_ch    = await get_dump_channel(user_id)
    auto_post  = await get_auto_poster(user_id)
    dump_fwd_v = await get_dump_fwd(user_id)
    style      = await get_caption_style(user_id)

    return (
        "<b>⚙️ BOT SETTINGS</b>\n\n"
        f"🖼 THUMBNAIL: {'✅ SET' if thumb else '❌ NOT SET'}\n"
        f"📁 DUMP CHANNEL: {'✅ SET' if dump_ch else '❌ NOT SET'}\n"
        f"🎬 AUTO POSTER: {'✨ ON' if auto_post else '❌ OFF'}\n"
        f"🚀 DUMP FWD: {'🟢 ON' if dump_fwd_v else '🔴 OFF'}\n"
        f"✏️ STYLE: {style.upper()}\n\n"
        "💡 <i>SEND A PHOTO OR IMAGE URL ANYTIME TO UPDATE COVER.</i>"
    )

def get_caption_style_keyboard(current_style: str) -> InlineKeyboardMarkup:
    styles = [
        ("normal",     "Normal"),
        ("bold",       "Bold"),
        ("italic",     "Italic"),
        ("underline",  "Underline"),
        ("bolditalic", "Bold Italic"),
        ("mono",       "Mono"),
    ]
    rows = []
    row  = []
    for key, label in styles:
        tick = "✅ " if key == current_style else ""
        row.append(InlineKeyboardButton(text=f"{tick}{label}", callback_data=f"setstyle_{key}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="🔙 Back", callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

# ==================== DIRECT PHOTO HANDLER ====================
# User sends photo directly → auto set as thumbnail (no menu needed)

@router.message(F.photo)
async def direct_photo_thumbnail(message: types.Message, bot: Bot):
    """
    Any photo sent directly to bot → instantly set as thumbnail.
    Shows success message like the reference bot.
    """
    user_id = message.from_user.id

    if await is_banned(user_id):
        return await message.answer(small_caps("You are banned from using this bot."))

    await add_user(user_id, message.from_user.username, message.from_user.first_name)

    file_id = message.photo[-1].file_id
    await set_thumbnail(user_id, file_id)

    await message.answer(
        "✅ <b>COVER SET SUCCESSFULLY!</b>\n"
        "NOW WHEN YOU SEND VIDEOS, THIS COVER WILL BE USED AUTOMATICALLY",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
        ])
    )

# ==================== DIRECT URL HANDLER ====================
# User sends image URL → download → set as thumbnail

@router.message(F.text & F.text.regexp(r"https?://\S+\.(jpg|jpeg|png|webp)(\?.*)?$"))
async def direct_url_thumbnail(message: types.Message, bot: Bot):
    """
    User sends a direct image URL → download it → set as thumbnail.
    """
    user_id = message.from_user.id

    if await is_banned(user_id):
        return await message.answer(small_caps("You are banned from using this bot."))

    await add_user(user_id, message.from_user.username, message.from_user.first_name)

    url = message.text.strip()
    status = await message.answer("⏳ <i>Downloading image...</i>", parse_mode="HTML")

    tmp_path = f"/tmp/url_thumb_{user_id}.jpg"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    await status.edit_text("❌ <b>Failed to download image. Check the URL.</b>", parse_mode="HTML")
                    return
                async with aiofiles.open(tmp_path, "wb") as f:
                    await f.write(await resp.read())

        # Upload to Telegram to get file_id
        uploaded = await bot.send_photo(
            chat_id=message.chat.id,
            photo=types.FSInputFile(tmp_path),
            disable_notification=True
        )
        file_id = uploaded.photo[-1].file_id
        await bot.delete_message(message.chat.id, uploaded.message_id)

        await set_thumbnail(user_id, file_id)
        await status.edit_text(
            "✅ <b>COVER SET SUCCESSFULLY!</b>\n"
            "NOW WHEN YOU SEND VIDEOS, THIS COVER WILL BE USED AUTOMATICALLY",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
            ])
        )

    except Exception as e:
        await status.edit_text(f"❌ <b>Error:</b> <code>{e}</code>", parse_mode="HTML")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# ==================== SETTINGS MENU ====================

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if await is_banned(user_id):
        return await callback.answer(small_caps("You are banned!"), show_alert=True)

    text = await get_settings_text(user_id)
    kbd  = await get_main_settings_keyboard(user_id)

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        parse_mode="HTML",
        reply_markup=kbd
    )
    await callback.answer()

# ==================== CAPTION STYLE ====================

@router.callback_query(F.data == "caption_style_menu")
async def caption_style_menu(callback: CallbackQuery, bot: Bot):
    style = await get_caption_style(callback.from_user.id)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text="<b>📝 CHOOSE CAPTION STYLE</b>\n\nSelect how you want your video captions to look. 〝〞",
        parse_mode="HTML",
        reply_markup=get_caption_style_keyboard(style)
    )
    await callback.answer()

@router.callback_query(F.data.startswith("setstyle_"))
async def set_style(callback: CallbackQuery):
    style = callback.data.replace("setstyle_", "")
    if style not in ["normal", "bold", "italic", "underline", "bolditalic", "mono"]:
        return await callback.answer("Invalid style!", show_alert=True)
    await set_caption_style(callback.from_user.id, style)
    await callback.message.edit_reply_markup(reply_markup=get_caption_style_keyboard(style))
    await callback.answer(f"✅ Style set to {style.upper()}!")

# ==================== TOGGLES ====================

@router.callback_query(F.data == "toggle_auto_poster")
async def toggle_auto_poster(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    current = await get_auto_poster(user_id)
    await set_auto_poster(user_id, not current)
    await callback.answer(f"Auto Poster: {'✨ ON' if not current else '❌ OFF'}")
    text = await get_settings_text(user_id)
    kbd  = await get_main_settings_keyboard(user_id)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kbd)
    except TelegramBadRequest:
        pass

@router.callback_query(F.data == "toggle_dump_fwd")
async def toggle_dump_fwd(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    current = await get_dump_fwd(user_id)
    await set_dump_fwd(user_id, not current)
    await callback.answer(f"Dump Fwd: {'🟢 ON' if not current else '🔴 OFF'}")
    text = await get_settings_text(user_id)
    kbd  = await get_main_settings_keyboard(user_id)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kbd)
    except TelegramBadRequest:
        pass

# ==================== DUMP CHANNEL ====================

@router.callback_query(F.data == "add_dump")
async def add_dump_prompt(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    if await is_banned(user_id):
        return await callback.answer(small_caps("You are banned!"), show_alert=True)

    await state.set_state(SettingsState.waiting_for_dump_channel)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            "<b>📁 ADD DUMP CHANNEL</b>\n\n"
            "Send the <b>Channel ID</b> where videos will be forwarded.\n\n"
            "Example: <code>-1001234567890</code>\n\n"
            "<i>⚠️ Make sure this bot is admin in that channel!</i>"
        ),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_dump")]
        ])
    )
    await callback.answer()

@router.callback_query(F.data == "cancel_dump")
async def cancel_dump(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await show_settings(callback, bot)

@router.message(SettingsState.waiting_for_dump_channel)
async def receive_dump_channel(message: types.Message, state: FSMContext):
    channel_id = message.text.strip() if message.text else ""
    if not (channel_id.startswith("-100") or channel_id.startswith("@")):
        return await message.answer(
            "❌ <b>Invalid format!</b>\n\nSend a valid Channel ID like <code>-1001234567890</code>",
            parse_mode="HTML"
        )
    await set_dump_channel(message.from_user.id, channel_id)
    await state.clear()
    await message.answer(
        f"✅ <b>Dump channel set!</b>\n\n<code>{channel_id}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
        ])
    )

# ==================== VIEW / REMOVE THUMBNAIL ====================

@router.callback_query(F.data == "view_thumb")
async def view_thumbnail(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    thumb   = await get_thumbnail(user_id)
    kbd = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
    ])
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    if thumb:
        await bot.send_photo(
            chat_id=callback.message.chat.id,
            photo=thumb,
            caption=f"<b>🖼️ {small_caps('Your Current Thumbnail')}</b>",
            parse_mode="HTML",
            reply_markup=kbd
        )
    else:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=(
                f"<b>❌ {small_caps('No thumbnail set')}</b>\n\n"
                f"<blockquote>{small_caps('Send any photo to set your thumbnail!')}</blockquote>"
            ),
            parse_mode="HTML",
            reply_markup=kbd
        )
    await callback.answer()

@router.callback_query(F.data == "remove_thumb")
async def remove_thumbnail_handler(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    removed = await remove_thumbnail(user_id)
    kbd = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
    ])
    text = (
        f"<b>🗑️ {small_caps('Thumbnail Removed')}</b>\n\n"
        f"<blockquote>{small_caps('Your videos will now be sent without a custom cover.')}</blockquote>"
    ) if removed else (
        f"<b>❌ {small_caps('No thumbnail to remove')}</b>"
    )
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        parse_mode="HTML",
        reply_markup=kbd
    )
    await callback.answer()

# ==================== BACK / CLOSE ====================

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, bot: Bot):
    welcome_text = (
        f"<b>{small_caps('Welcome to Thumbnail Bot!')}\n\n"
        f"<blockquote>{small_caps('Send me a video and I will add your custom thumbnail to it.')}</blockquote>\n\n"
        f"{small_caps('How to use:')}\n"
        f"<blockquote>"
        f"1️ {small_caps('Send any photo to set thumbnail')}\n"
        f"2️ {small_caps('Send any video')}\n"
        f"3️ {small_caps('Get video with your thumbnail!')}"
        f"</blockquote></b>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL),
            InlineKeyboardButton(text="👨‍💻 Developer",  url=DEV_URL)
        ],
        [InlineKeyboardButton(text="⚙️ Settings", callback_data="settings")]
    ])
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=welcome_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data == "close_settings")
async def close_settings(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer(small_caps("Settings closed"))
