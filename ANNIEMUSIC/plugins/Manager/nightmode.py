import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import filters, enums
from pyrogram.enums import MessageEntityType
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions, CallbackQuery, Message
from ANNIEMUSIC import app
from ANNIEMUSIC.plugins.Manager.nightmodedb import nightdb, nightmode_on, nightmode_off, get_nightchats
from datetime import datetime
import pytz
from pytz import timezone

IST = pytz.timezone("Asia/Kolkata")

# ---------------------------
# ⚙️ Chat permission presets
CLOSE_CHAT = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=False,
    can_send_polls=False,
    can_change_info=False,
    can_add_web_page_previews=False,
    can_pin_messages=False,
    can_invite_users=False,
)

OPEN_CHAT = ChatPermissions(
    can_send_messages=True,
    can_send_media_messages=True,
    can_send_polls=True,
    can_change_info=True,
    can_add_web_page_previews=True,
    can_pin_messages=True,
    can_invite_users=True,
)

# ---------------------------
# 🌙 Inline Buttons
buttons = InlineKeyboardMarkup(
    [[
        InlineKeyboardButton("🌜 𝐄ɴᴀʙʟᴇ", callback_data="add_night"),
        InlineKeyboardButton("🌞 𝐃ɪsᴀʙʟᴇ", callback_data="rm_night")
    ]]
)

# ---------------------------
# ✨ /nightmode Command
@app.on_message(filters.command("nightmode") & filters.group)
async def _nightmode(_, message: Message):
    try:
        await message.reply_photo(
            photo="https://telegra.ph//file/06649d4d0bbf4285238ee.jpg",
            caption=(
                "🌙 **NɪɢʜᴛMᴏᴅᴇ Cᴏɴᴛʀᴏʟ Pᴀɴᴇʟ** 🌙\n\n"
                "╰➤ Click below to **ᴇɴᴀʙʟᴇ/ᴅɪsᴀʙʟᴇ** NightMode for this chat.\n"
                "╰➤ Default Time: **10 PM – 7 AM (IST)**\n"
                "╰➤ ᴍᴇᴅɪᴀ, sᴛɪᴄᴋᴇʀ & ʟɪɴᴋs ❌\n"
                "╰➤ ᴛᴇxᴛ & ᴄᴏᴍᴍᴀɴᴅs ✅"
            ),
            reply_markup=buttons
        )
    except Exception as e:
        print(f"[nightmode_cmd_error] {e}")

# ---------------------------
# 💫 Callback Handler
@app.on_callback_query(filters.regex("^(add_night|rm_night)$"))
async def nightcb(_, query: CallbackQuery):
    data = query.data
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    admins = [m.user.id async for m in app.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS)]
    if user_id not in admins:
        return await query.answer("🚫 Only group admins can control NightMode.", show_alert=True)

    check_night = await nightdb.find_one({"chat_id": chat_id})

    try:
        if data == "add_night":
            if check_night:
                await query.message.edit_caption("🌙 **NɪɢʜᴛMᴏᴅᴇ ᴀʟʀᴇᴀᴅʏ ᴇɴᴀʙʟᴇᴅ!**")
            else:
                await nightmode_on(chat_id)
                await query.message.edit_caption(
                    "🌜 **NɪɢʜᴛMᴏᴅᴇ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!**\n\n"
                    "🕙 Active Between: **10 PM – 7 AM (IST)**\n"
                    "❌ Media, Stickers & Links\n✅ Text + Commands allowed!"
                )
        elif data == "rm_night":
            if check_night:
                await nightmode_off(chat_id)
                await query.message.edit_caption("🌞 **DᴀʏMᴏᴅᴇ: NɪɢʜᴛMᴏᴅᴇ Dɪsᴀʙʟᴇᴅ!**")
            else:
                await query.message.edit_caption("🌞 **Already Disabled!**")
    except Exception as e:
        print(f"[nightmode_toggle_error] {e}")

# ---------------------------
# 🕛 Message Filter During Night
@app.on_message(filters.group & (filters.media | filters.sticker | filters.text), group=99)
async def delete_night_messages(_, message: Message):
    try:
        chat_id = message.chat.id
        check_night = await nightdb.find_one({"chat_id": chat_id})
        if not check_night:
            return

        now = datetime.now(IST)
        hour = now.hour
        start_hour, end_hour = 22, 7
        is_night = hour >= start_hour or hour < end_hour

        if not is_night:
            return

        # Allow Commands
        is_command = False
        if message.entities:
            for ent in message.entities:
                ent_type = getattr(ent, "type", None)
                if (ent_type == "bot_command" or ent_type == MessageEntityType.BOT_COMMAND) and getattr(ent, "offset", 0) == 0:
                    is_command = True
                    break
        if message.text and message.text.startswith("/"):
            is_command = True

        if is_command:
            return

        # Delete Media, Sticker or Link
        if (
            message.sticker or message.photo or message.video or message.animation or
            message.audio or message.voice or message.video_note or
            (message.text and ("http://" in message.text or "https://" in message.text))
        ):
            try:
                await message.delete()
                warn = await message.reply_text(
                    "🌙 *NɪɢʜᴛMᴏᴅᴇ Aᴄᴛɪᴠᴇ (10ᴘᴍ – 7ᴀᴍ)*\n"
                    "❌ Media, stickers & links are not allowed right now!"
                )
                await asyncio.sleep(4)
                await warn.delete()
            except Exception as e:
                print(f"[nightmode_delete_error] {e}")
    except Exception as e:
        print(f"[nightmode_delete_outer_error] {e}")

# ---------------------------
# ⏰ NightMode Start Job
async def start_nightmode():
    try:
        schats = await get_nightchats()
        chats = [int(chat["chat_id"]) for chat in schats] if schats else []
        for add_chat in chats:
            try:
                await app.send_photo(
                    add_chat,
                    photo="https://telegra.ph//file/06649d4d0bbf4285238ee.jpg",
                    caption="🌙 **NɪɢʜᴛMᴏᴅᴇ Aᴄᴛɪᴠᴇ:**\n"
                            "⏰ 10 PM – 7 AM IST\n"
                            "💬 Text & Commands allowed\n"
                            "📵 Media, Stickers & Links restricted!"
                )
                await app.set_chat_permissions(add_chat, CLOSE_CHAT)
            except Exception as e:
                print(f"[nightmode_notify_error] {add_chat} - {e}")
    except Exception as e:
        print(f"[start_nightmode_error] {e}")

# ---------------------------
# 🌞 DayMode Close Job
async def close_nightmode():
    try:
        schats = await get_nightchats()
        chats = [int(chat["chat_id"]) for chat in schats] if schats else []
        for rm_chat in chats:
            try:
                await app.send_photo(
                    rm_chat,
                    photo="https://telegra.ph//file/14ec9c3ff42b59867040a.jpg",
                    caption="🌞 **DᴀʏMᴏᴅᴇ:** NɪɢʜᴛMᴏᴅᴇ ᴇɴᴅᴇᴅ.\n"
                            "🎉 Yᴏᴜ ᴄᴀɴ ɴᴏᴡ sᴇɴᴅ ᴀʟʟ ᴍᴇssᴀɢᴇ ᴛʏᴘᴇs ғʀᴇᴇʟʏ!"
                )
                await app.set_chat_permissions(rm_chat, OPEN_CHAT)
            except Exception as e:
                print(f"[nightmode_notify_error] {rm_chat} - {e}")
    except Exception as e:
        print(f"[close_nightmode_error] {e}")

# ---------------------------
# 🧭 Scheduler Init (One-Time)
_scheduler_started = False

async def _start_scheduler_task():
    global _scheduler_started
    if _scheduler_started:
        return
    _scheduler_started = True

    scheduler = AsyncIOScheduler(timezone=timezone("Asia/Kolkata"))
    scheduler.add_job(start_nightmode, trigger="cron", hour=22, minute=0)
    scheduler.add_job(close_nightmode, trigger="cron", hour=7, minute=0)
    scheduler.start()
    print("🌙 NightMode Scheduler Started (Asia/Kolkata) — Annie ✘ Music")

# 🔄 Start scheduler safely
asyncio.create_task(_start_scheduler_task())