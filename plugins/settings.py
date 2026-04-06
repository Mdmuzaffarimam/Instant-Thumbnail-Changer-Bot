# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat
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
    get_dump_fwd, set_dump_fwd,
    get_auto_poster, set_auto_poster
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


class SettingsState(StatesGroup):
    waiting_for_thumbnail = State()
    waiting_for_dump_channel = State()


# ==================== SETTINGS MENU ====================

async def get_settings_text_and_keyboard(user_id: int):
    """Build settings menu dynamically based on user settings."""
    thumb = await get_thumbnail(user_id)
    style = await get_caption_style(user_id)
    dump_ch = await get_dump_channel(user_id)
    dump_fwd = await get_dump_fwd(user_id)
    auto_poster = await get_auto_poster(user_id)

    thumb_status = "✅ SET" if thumb else "❌ NOT SET"
    dump_status = "✅ SET" if dump_ch else "❌ NOT SET"
    fwd_status = "🟢 ON" if dump_fwd else "🔴 OFF"
    poster_status = "✨ ON" if auto_poster else "🔴 OFF"
    style_display = style.upper().replace("_", " ")

    text = (
        f"<b>⚙️ BOT SETTINGS</b>\n\n"
        f"🖼️ THUMBNAIL: <b>{thumb_status}</b>\n"
        f"📢 DUMP CHANNEL: <b>{dump_status}</b>\n"
        f"🎬 AUTO POSTER: <b>{poster_status}</b>\n"
        f"🚀 DUMP FWD: <b>{fwd_status}</b>\n"
        f"✏️ STYLE: <b>{style_display}</b>\n\n"
        f"<i>💡 SEND A PHOTO OR LINK ANYTIME TO UPDATE COVER.</i>"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Add Dump", callback_data="add_dump")],
        [InlineKeyboardButton(text="✏️ Caption Style", callback_data="caption_style")],
        [InlineKeyboardButton(
            text=f"{'✨ Auto Poster: ON' if auto_poster else '🔴 Auto Poster: OFF'}",
            callback_data="toggle_auto_poster"
        )],
        [InlineKeyboardButton(
            text=f"{'🟢 Dump Fwd: ON' if dump_fwd else '🔴 Dump Fwd: OFF'}",
            callback_data="toggle_dump_fwd"
        )],
        [InlineKeyboardButton(text="👁️ View Thumbnail", callback_data="view_thumb")],
        [InlineKeyboardButton(text="🗑️ Remove Thumbnail", callback_data="remove_thumb")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_start")],
    ])

    return text, keyboard


@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id

    if await is_banned(user_id):
        await callback.answer(small_caps("You are banned!"), show_alert=True)
        return

    text, keyboard = await get_settings_text_and_keyboard(user_id)

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


# ==================== ✅ CAPTION STYLE ====================

def get_caption_style_keyboard(current_style: str):
    styles = [
        ("Normal", "normal"),
        ("Bold", "bold"),
        ("Italic", "italic"),
        ("Underline", "underline"),
        ("Bold Italic", "bold_italic"),
        ("Mono", "mono"),
    ]
    buttons = []
    row = []
    for label, value in styles:
        tick = "✅ " if current_style == value else ""
        row.append(InlineKeyboardButton(text=f"{tick}{label}", callback_data=f"set_style_{value}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Back", callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.callback_query(F.data == "caption_style")
async def show_caption_style(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    current_style = await get_caption_style(user_id)

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text="<b>✏️ CHOOSE CAPTION STYLE</b>\n\n"
             "<blockquote>SELECT HOW YOU WANT YOUR VIDEO CAPTIONS TO LOOK.</blockquote>",
        parse_mode="HTML",
        reply_markup=get_caption_style_keyboard(current_style)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("set_style_"))
async def set_style_handler(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    style = callback.data.replace("set_style_", "")
    await set_caption_style(user_id, style)
    await callback.answer(f"✅ Style set to {style.upper().replace('_', ' ')}!", show_alert=True)
    # Refresh style menu
    current_style = await get_caption_style(user_id)
    try:
        await callback.message.edit_reply_markup(reply_markup=get_caption_style_keyboard(current_style))
    except TelegramBadRequest:
        pass


# ==================== ✅ DUMP CHANNEL ====================

@router.callback_query(F.data == "add_dump")
async def add_dump_prompt(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    current = await get_dump_channel(user_id)

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    current_text = f"\n\n<b>Current:</b> <code>{current}</code>" if current else ""

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"<b>📢 ADD DUMP CHANNEL</b>\n\n"
             f"<blockquote>Bot ko apne channel ka admin banao, phir channel ID bhejo.\n"
             f"Example: <code>-1001234567890</code></blockquote>"
             f"{current_text}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Cancel", callback_data="settings")]
        ])
    )
    await state.set_state(SettingsState.waiting_for_dump_channel)
    await callback.answer()


@router.message(SettingsState.waiting_for_dump_channel)
async def receive_dump_channel(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    if not (text.startswith("-100") and text[4:].isdigit()):
        await message.answer(
            "❌ <b>Invalid Channel ID!</b>\n\n"
            "<blockquote>Channel ID ka format hona chahiye: <code>-1001234567890</code></blockquote>",
            parse_mode="HTML"
        )
        return

    await set_dump_channel(user_id, text)
    await state.clear()

    await message.answer(
        f"✅ <b>Dump Channel Set!</b>\n\n"
        f"<blockquote>Channel: <code>{text}</code></blockquote>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
        ])
    )


# ==================== ✅ TOGGLE AUTO POSTER ====================

@router.callback_query(F.data == "toggle_auto_poster")
async def toggle_auto_poster(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    current = await get_auto_poster(user_id)
    await set_auto_poster(user_id, not current)
    status = "ON ✨" if not current else "OFF 🔴"
    await callback.answer(f"Auto Poster: {status}", show_alert=True)
    # Refresh settings
    text, keyboard = await get_settings_text_and_keyboard(user_id)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except TelegramBadRequest:
        pass


# ==================== ✅ TOGGLE DUMP FWD ====================

@router.callback_query(F.data == "toggle_dump_fwd")
async def toggle_dump_fwd(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    current = await get_dump_fwd(user_id)
    await set_dump_fwd(user_id, not current)
    status = "ON 🟢" if not current else "OFF 🔴"
    await callback.answer(f"Dump Fwd: {status}", show_alert=True)
    text, keyboard = await get_settings_text_and_keyboard(user_id)
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    except TelegramBadRequest:
        pass


# ==================== VIEW / REMOVE THUMBNAIL ====================

@router.callback_query(F.data == "view_thumb")
async def view_thumbnail(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    thumb = await get_thumbnail(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
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
            reply_markup=keyboard
        )
    else:
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=f"<b>❌ {small_caps('No thumbnail set')}</b>\n\n"
                 f"<blockquote>{small_caps('Send a photo anytime to set your cover.')}</blockquote>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    await callback.answer()


@router.callback_query(F.data == "remove_thumb")
async def remove_thumbnail_handler(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    removed = await remove_thumbnail(user_id)

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
    ])

    text = (
        f"<b>🗑️ {small_caps('Thumbnail Removed')}</b>\n\n"
        f"<blockquote>{small_caps('Your videos will now be sent without a custom cover.')}</blockquote>"
        if removed else
        f"<b>❌ {small_caps('No thumbnail to remove')}</b>\n\n"
        f"<blockquote>{small_caps('You have not set a thumbnail yet.')}</blockquote>"
    )

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


# ==================== BACK TO START ====================

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, bot: Bot):
    welcome_text = (
        f"<b>{small_caps('Welcome to Thumbnail Bot!')}\n\n"
        f"<blockquote>{small_caps('Send me a video and I will add your custom thumbnail to it.')}</blockquote>\n\n"
        f"{small_caps('How to use:')}\n"
        f"<blockquote>"
        f"1️ {small_caps('Send a photo anytime to set your cover')}\n"
        f"2️ {small_caps('Send any video')}\n"
        f"3️ {small_caps('Get video with your thumbnail!')}"
        f"</blockquote></b>"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL),
            InlineKeyboardButton(text="👨‍💻 Developer", url=DEV_URL)
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
