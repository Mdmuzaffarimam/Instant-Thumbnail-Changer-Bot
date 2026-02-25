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
    get_thumbnail,
    set_thumbnail,
    remove_thumbnail,
    is_banned,
    get_caption_style,
    set_caption_style
)

router = Router()


# ================= SMALL CAPS =================
def small_caps(text: str) -> str:
    normal = "abcdefghijklmnopqrstuvwxyz"
    small = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
    result = ""
    for char in text:
        if char.lower() in normal:
            result += small[normal.index(char.lower())]
        else:
            result += char
    return result


# ================= FSM =================
class ThumbnailState(StatesGroup):
    waiting_for_thumbnail = State()


# ================= SETTINGS KEYBOARD =================
def get_settings_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🖼️ Update Thumbnail", callback_data="update_thumb")],
        [InlineKeyboardButton(text="👁️ View Thumbnail", callback_data="view_thumb")],
        [InlineKeyboardButton(text="🗑️ Remove Thumbnail", callback_data="remove_thumb")],
        [InlineKeyboardButton(text="📝 Caption Style", callback_data="caption_style")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_start")],
        [InlineKeyboardButton(text="❌ Close", callback_data="close_settings")]
    ])


# ================= CAPTION STYLE KEYBOARD =================
def get_caption_style_keyboard(current: str):
    def btn(name, value):
        tick = "✅ " if current == value else ""
        return InlineKeyboardButton(
            text=f"{tick}{name}",
            callback_data=f"set_caption_style:{value}"
        )

    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("Normal", "normal")],
        [btn("Bold", "bold")],
        [btn("Italic", "italic")],
        [btn("Mono", "mono")],
        [btn("Bold Italic", "bold_italic")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="settings")]
    ])


# ================= SHOW SETTINGS =================
@router.callback_query(F.data == "settings")
async def show_settings(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id

    if await is_banned(user_id):
        await callback.answer(small_caps("you are banned"), show_alert=True)
        return

    thumb = await get_thumbnail(user_id)
    status = (
        f"✅ {small_caps('thumbnail is set')}"
        if thumb else
        f"❌ {small_caps('no thumbnail set')}"
    )

    text = (
        f"<b>⚙️ {small_caps('thumbnail settings')}</b>\n\n"
        f"<blockquote>{status}</blockquote>\n\n"
        f"{small_caps('choose an option below:')}"
    )

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=text,
        parse_mode="HTML",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()


# ================= CAPTION STYLE MENU =================
@router.callback_query(F.data == "caption_style")
async def caption_style_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    current = await get_caption_style(user_id)

    text = (
        f"<b>📝 {small_caps('caption style settings')}</b>\n\n"
        f"{small_caps('select your preferred caption style:')}\n\n"
        f"<blockquote>"
        f"• Normal\n"
        f"• Bold\n"
        f"• Italic\n"
        f"• Mono\n"
        f"• Bold Italic\n"
        f"</blockquote>\n"
        f"{small_caps('this style will be applied automatically.')}"
    )

    await callback.message.edit_text(
        text=text,
        parse_mode="HTML",
        reply_markup=get_caption_style_keyboard(current)
    )
    await callback.answer()


# ================= SAVE CAPTION STYLE =================
@router.callback_query(F.data.startswith("set_caption_style:"))
async def save_caption_style_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    style = callback.data.split(":")[1]

    await set_caption_style(user_id, style)

    await callback.answer(
        small_caps(f"caption style set to {style.replace('_',' ')}"),
        show_alert=True
    )

    await callback.message.edit_reply_markup(
        reply_markup=get_caption_style_keyboard(style)
    )


# ================= BACK TO START =================
@router.callback_query(F.data == "back_to_start")
async def back_to_start(callback: CallbackQuery, bot: Bot):
    welcome_text = (
        f"<b>{small_caps('welcome to thumbnail bot!')}</b>\n\n"
        f"<blockquote>{small_caps('send me a video and i will add your custom thumbnail to it.')}</blockquote>\n\n"
        f"<b>{small_caps('how to use:')}</b>\n"
        f"<blockquote>"
        f"1 {small_caps('set your thumbnail in settings')}\n"
        f"2 {small_caps('send any video')}\n"
        f"3 {small_caps('get video with your thumbnail!')}"
        f"</blockquote>"
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


# ================= UPDATE / VIEW / REMOVE THUMBNAIL =================
@router.callback_query(F.data == "update_thumb")
async def update_thumbnail_prompt(callback: CallbackQuery, state: FSMContext, bot: Bot):
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
        text=f"<b>📸 {small_caps('send me a photo')}</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_update")
async def cancel_update(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await state.clear()
    await show_settings(callback, bot)


@router.message(ThumbnailState.waiting_for_thumbnail, F.photo)
async def receive_thumbnail(message: types.Message, state: FSMContext):
    await set_thumbnail(message.from_user.id, message.photo[-1].file_id)
    await state.clear()

    await message.answer(
        f"<b>✅ {small_caps('thumbnail saved')}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton("⚙️ Back to Settings", callback_data="settings")]]
        )
    )


@router.callback_query(F.data == "view_thumb")
async def view_thumbnail(callback: CallbackQuery, bot: Bot):
    thumb = await get_thumbnail(callback.from_user.id)

    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass

    if thumb:
        await bot.send_photo(
            callback.message.chat.id,
            thumb,
            caption=f"<b>🖼️ {small_caps('your current thumbnail')}</b>",
            parse_mode="HTML"
        )
    else:
        await bot.send_message(
            callback.message.chat.id,
            f"<b>❌ {small_caps('no thumbnail set')}</b>",
            parse_mode="HTML"
        )
    await callback.answer()


@router.callback_query(F.data == "remove_thumb")
async def remove_thumbnail_handler(callback: CallbackQuery, bot: Bot):
    await remove_thumbnail(callback.from_user.id)
    await show_settings(callback, bot)


@router.callback_query(F.data == "close_settings")
async def close_settings(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    await callback.answer(small_caps("settings closed"))
