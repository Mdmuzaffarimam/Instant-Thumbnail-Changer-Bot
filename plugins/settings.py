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
    get_dump_channel, set_dump_channel, remove_dump_channel,
    get_auto_poster, set_auto_poster,
    get_dump_fwd, set_dump_fwd,
)

router = Router()


# ── Small Caps Helper ──────────────────────────────────────────────────────────

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


# ── States ─────────────────────────────────────────────────────────────────────

class ThumbnailState(StatesGroup):
    waiting_for_thumbnail = State()

class DumpChannelState(StatesGroup):
    waiting_for_channel = State()


# ── Caption Style Map ──────────────────────────────────────────────────────────

CAPTION_STYLES = {
    "normal":     "Normal",
    "bold":       "Bold",
    "italic":     "Italic",
    "underline":  "Underline",
    "bolditalic": "Bold Italic",
    "mono":       "Mono",
}

def apply_caption_style(text: str, style: str) -> str:
    if style == "bold":
        return f"<b>{text}</b>"
    elif style == "italic":
        return f"<i>{text}</i>"
    elif style == "underline":
        return f"<u>{text}</u>"
    elif style == "bolditalic":
        return f"<b><i>{text}</i></b>"
    elif style == "mono":
        return f"<code>{text}</code>"
    else:
        return text  # normal


# ── Keyboards ──────────────────────────────────────────────────────────────────

def get_settings_keyboard(thumb_set: bool, auto_poster: bool, dump_fwd: bool, dump_channel: str) -> InlineKeyboardMarkup:
    dump_status = "✅ SET" if dump_channel else "❌ NOT SET"
    auto_status = "✨ ON"  if auto_poster  else "❌ OFF"
    fwd_status  = "🟢 ON" if dump_fwd     else "🔴 OFF"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼️ Update Thumbnail",   callback_data="update_thumb")],
        [InlineKeyboardButton(text="👁️ View Thumbnail",     callback_data="view_thumb")],
        [InlineKeyboardButton(text="🗑️ Remove Thumbnail",   callback_data="remove_thumb")],
        [InlineKeyboardButton(text="📁 Add Dump Channel",   callback_data="add_dump")],
        [InlineKeyboardButton(text="📝 Caption Style",      callback_data="caption_style_menu")],
        [InlineKeyboardButton(text=f"✨ Auto Poster: {'ON' if auto_poster else 'OFF'}", callback_data="toggle_auto_poster")],
        [InlineKeyboardButton(text=f"🟢 Dump Fwd: {'ON' if dump_fwd else 'OFF'}",      callback_data="toggle_dump_fwd")],
        [InlineKeyboardButton(text="🔙 Back",               callback_data="back_to_start")],
        [InlineKeyboardButton(text="❌ Close",              callback_data="close_settings")],
    ])


def get_caption_style_keyboard(current_style: str) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for key, label in CAPTION_STYLES.items():
        tick = "✅ " if key == current_style else ""
        row.append(InlineKeyboardButton(text=f"{tick}{label}", callback_data=f"setstyle_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="🔙 Back to Settings", callback_data="settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# ── Helper: show settings menu ─────────────────────────────────────────────────

async def send_settings_menu(bot: Bot, chat_id: int, user_id: int):
    thumb       = await get_thumbnail(user_id)
    auto_poster = await get_auto_poster(user_id)
    dump_fwd    = await get_dump_fwd(user_id)
    dump_ch     = await get_dump_channel(user_id)
    style       = await get_caption_style(user_id)

    thumb_status = f"✅ {small_caps('SET')}" if thumb else f"❌ {small_caps('NOT SET')}"
    dump_status  = f"✅ {small_caps('SET')}" if dump_ch else f"❌ {small_caps('NOT SET')}"
    auto_status  = f"✨ {small_caps('ON')}" if auto_poster else f"❌ {small_caps('OFF')}"
    fwd_status   = f"🟢 {small_caps('ON')}" if dump_fwd else f"🔴 {small_caps('OFF')}"
    style_label  = CAPTION_STYLES.get(style, "Bold").upper()

    text = (
        f"<b>⚙️ {small_caps('BOT SETTINGS')}</b>\n\n"
        f"<blockquote>"
        f"🖼 THUMBNAIL: {thumb_status}\n"
        f"📁 DUMP CHANNEL: {dump_status}\n"
        f"🎬 AUTO POSTER: {auto_status}\n"
        f"🚀 DUMP FWD: {fwd_status}\n"
        f"✏️ STYLE: {style_label}"
        f"</blockquote>\n\n"
        f"💡 <i>{small_caps('SEND A PHOTO ANYTIME TO UPDATE COVER.')}</i>"
    )

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode="HTML",
        reply_markup=get_settings_keyboard(bool(thumb), auto_poster, dump_fwd, dump_ch)
    )


# ── /settings command ──────────────────────────────────────────────────────────

@router.message(F.text == "/settings")
async def settings_command(message: types.Message, bot: Bot):
    user_id = message.from_user.id
    if await is_banned(user_id):
        await message.answer(small_caps("You are banned from using this bot."))
        return
    await send_settings_menu(bot, message.chat.id, user_id)


# ── Callback: open settings ────────────────────────────────────────────────────

@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if await is_banned(user_id):
        await callback.answer(small_caps("You are banned!"), show_alert=True)
        return
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await send_settings_menu(bot, callback.message.chat.id, user_id)
    await callback.answer()


# ── Callback: back to start ────────────────────────────────────────────────────

@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, bot: Bot):
    welcome_text = (
        f"<b>{small_caps('Welcome to Thumbnail Bot!')}</b>\n\n"
        f"<blockquote>{small_caps('Send me a video and I will add your custom thumbnail to it.')}</blockquote>\n\n"
        f"<b>{small_caps('How to use:')}</b>\n"
        f"<blockquote>"
        f"1️⃣ {small_caps('Set your thumbnail in Settings')}\n"
        f"2️⃣ {small_caps('Send any video')}\n"
        f"3️⃣ {small_caps('Get video with your thumbnail!')}"
        f"</blockquote>"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_URL),
            InlineKeyboardButton(text="👨‍💻 Developer",   url=DEV_URL)
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


# ── Callback: update thumbnail ─────────────────────────────────────────────────

@router.callback_query(F.data == "update_thumb")
async def update_thumbnail_prompt(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = callback.from_user.id
    if await is_banned(user_id):
        await callback.answer(small_caps("You are banned!"), show_alert=True)
        return
    await state.set_state(ThumbnailState.waiting_for_thumbnail)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_update")]
    ])
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"<b>📸 {small_caps('Send me a photo')}</b>\n\n"
             f"<blockquote>{small_caps('This image will be used as the cover for your videos.')}</blockquote>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_update")
async def cancel_update(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await send_settings_menu(bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@router.message(ThumbnailState.waiting_for_thumbnail, F.photo)
async def receive_thumbnail(message: types.Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    file_id = message.photo[-1].file_id
    await set_thumbnail(user_id, file_id)
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
    ])
    await message.answer(
        f"<b>✅ {small_caps('Thumbnail saved!')}</b>\n\n"
        f"<blockquote>{small_caps('Your videos will now use this cover image.')}</blockquote>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ── Callback: view thumbnail ───────────────────────────────────────────────────

@router.callback_query(F.data == "view_thumb")
async def view_thumbnail(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    thumb   = await get_thumbnail(user_id)
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
                 f"<blockquote>{small_caps('Use Update Thumbnail to set one.')}</blockquote>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    await callback.answer()


# ── Callback: remove thumbnail ─────────────────────────────────────────────────

@router.callback_query(F.data == "remove_thumb")
async def remove_thumbnail_handler(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    removed = await remove_thumbnail(user_id)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
    ])
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    text = (
        f"<b>🗑️ {small_caps('Thumbnail Removed')}</b>\n\n"
        f"<blockquote>{small_caps('Your videos will now be sent without a custom cover.')}</blockquote>"
    ) if removed else (
        f"<b>❌ {small_caps('No thumbnail to remove')}</b>\n\n"
        f"<blockquote>{small_caps('You have not set a thumbnail yet.')}</blockquote>"
    )
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


# ── Callback: caption style menu ──────────────────────────────────────────────

@router.callback_query(F.data == "caption_style_menu")
async def caption_style_menu(callback: CallbackQuery, bot: Bot):
    user_id       = callback.from_user.id
    current_style = await get_caption_style(user_id)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            f"<b>📝 {small_caps('CHOOSE CAPTION STYLE')}</b>\n\n"
            f"<blockquote>{small_caps('Select how you want your video captions to look.')}</blockquote>"
        ),
        parse_mode="HTML",
        reply_markup=get_caption_style_keyboard(current_style)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("setstyle_"))
async def set_style_callback(callback: CallbackQuery, bot: Bot):
    style = callback.data.replace("setstyle_", "")
    if style not in CAPTION_STYLES:
        return await callback.answer("❌ Invalid style!", show_alert=True)
    await set_caption_style(callback.from_user.id, style)
    # Refresh keyboard to show tick
    await callback.message.edit_reply_markup(
        reply_markup=get_caption_style_keyboard(style)
    )
    await callback.answer(f"✅ Style set to {CAPTION_STYLES[style]}!")


# ── Callback: add dump channel ─────────────────────────────────────────────────

@router.callback_query(F.data == "add_dump")
async def add_dump_prompt(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.set_state(DumpChannelState.waiting_for_channel)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_dump")]
    ])
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=(
            f"<b>📁 {small_caps('ADD DUMP CHANNEL')}</b>\n\n"
            f"<blockquote>"
            f"{small_caps('Send the channel ID or username.')}\n\n"
            f"Example: <code>-1001234567890</code>\n"
            f"Or: <code>@mychannel</code>\n\n"
            f"⚠️ {small_caps('Make sure bot is admin in that channel!')}"
            f"</blockquote>"
        ),
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_dump")
async def cancel_dump(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await send_settings_menu(bot, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@router.message(DumpChannelState.waiting_for_channel, F.text)
async def receive_dump_channel(message: types.Message, state: FSMContext, bot: Bot):
    channel = message.text.strip()
    user_id = message.from_user.id
    await set_dump_channel(user_id, channel)
    await state.clear()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Back to Settings", callback_data="settings")]
    ])
    await message.answer(
        f"<b>✅ {small_caps('Dump channel saved!')}</b>\n\n"
        f"<blockquote>Channel: <code>{channel}</code></blockquote>",
        parse_mode="HTML",
        reply_markup=keyboard
    )


# ── Callback: toggle auto poster ──────────────────────────────────────────────

@router.callback_query(F.data == "toggle_auto_poster")
async def toggle_auto_poster(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    current = await get_auto_poster(user_id)
    new_val = not current
    await set_auto_poster(user_id, new_val)
    status  = "ON ✨" if new_val else "OFF ❌"
    await callback.answer(f"Auto Poster: {status}", show_alert=False)
    # Refresh settings menu
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await send_settings_menu(bot, callback.message.chat.id, user_id)


# ── Callback: toggle dump fwd ─────────────────────────────────────────────────

@router.callback_query(F.data == "toggle_dump_fwd")
async def toggle_dump_fwd(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    current = await get_dump_fwd(user_id)
    new_val = not current
    await set_dump_fwd(user_id, new_val)
    status  = "ON 🟢" if new_val else "OFF 🔴"
    await callback.answer(f"Dump Fwd: {status}", show_alert=False)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await send_settings_menu(bot, callback.message.chat.id, user_id)


# ── Callback: close settings ──────────────────────────────────────────────────

@router.callback_query(F.data == "close_settings")
async def close_settings(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer(small_caps("Settings closed"))
