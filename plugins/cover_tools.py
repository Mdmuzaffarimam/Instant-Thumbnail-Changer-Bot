# CantarellaBots
# Don't Remove Credit
# Telegram Channel @CantarellaBots
# Support group @rexbotschat
from aiogram import Router, types, Bot
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import is_banned, set_thumbnail

router = Router()

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

# ==================== /extract_cover ====================

@router.message(Command("extract_cover"))
async def extract_cover(message: types.Message, bot: Bot):
    """Reply to a video to extract its thumbnail/cover."""
    user_id = message.from_user.id

    if await is_banned(user_id):
        return await message.answer(small_caps("You are banned from using this bot."))

    replied = message.reply_to_message

    # Must reply to a video
    if not replied or not replied.video:
        return await message.answer(
            "❌ <b>Please reply to a video message with this command to extract its cover.</b>",
            parse_mode="HTML"
        )

    video = replied.video

    # Check if video has a thumbnail
    if not video.thumbnail:
        return await message.answer(
            f"<b>❌ {small_caps('No cover found in this video.')}</b>\n\n"
            f"<blockquote>{small_caps('This video does not have an embedded thumbnail.')}</blockquote>",
            parse_mode="HTML"
        )

    thumb_file_id = video.thumbnail.file_id

    kbd = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Set as My Thumbnail", callback_data=f"setextracted_{thumb_file_id}"),
            InlineKeyboardButton(text="❌ Cancel",              callback_data="close_settings")
        ]
    ])

    await bot.send_photo(
        chat_id=message.chat.id,
        photo=thumb_file_id,
        caption=(
            f"<b>✅ {small_caps('Cover extracted successfully!')}</b>\n\n"
            f"<blockquote>{small_caps('Tap below to set this as your thumbnail.')}</blockquote>"
        ),
        parse_mode="HTML",
        reply_markup=kbd
    )

# ==================== Callback: Set extracted thumbnail ====================

from aiogram import F
from aiogram.types import CallbackQuery
from aiogram.exceptions import TelegramBadRequest

@router.callback_query(F.data.startswith("setextracted_"))
async def set_extracted_thumbnail(callback: CallbackQuery):
    file_id = callback.data.replace("setextracted_", "")
    user_id = callback.from_user.id

    await set_thumbnail(user_id, file_id)

    try:
        await callback.message.edit_caption(
            caption=(
                f"<b>✅ {small_caps('Thumbnail set successfully!')}</b>\n\n"
                f"<blockquote>{small_caps('Your videos will now use this cover.')}</blockquote>"
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⚙️ Go to Settings", callback_data="settings")]
            ])
        )
    except TelegramBadRequest:
        pass

    await callback.answer("✅ Thumbnail set!")
