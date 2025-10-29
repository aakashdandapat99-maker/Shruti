from pyrogram import filters
from pyrogram.types import Message, MessageEntity
from pyrogram.enums import ChatType, MessageEntityType
from ANNIEMUSIC import app
from ANNIEMUSIC.utils.decorators.language import language
import asyncio
import json
import os
import atexit
from datetime import datetime

# ------------------------------
# 🎯 ʟᴏᴄᴋ ꜱʏꜱᴛᴇᴍ ᴄᴏɴꜰɪɢ
# ------------------------------

LOCK_DATA_FILE = "lock_data.json"

LOCKABLES = [
    "all", "audio", "bots", "button", "contact", "document",
    "egame", "forward", "game", "gif", "info", "inline",
    "invite", "location", "media", "messages", "other",
    "photo", "pin", "poll", "previews", "rtl", "sticker",
    "url", "username", "video", "voice", "text"
]

BOT_OWNER_ID = 7147401720

# Emojis for each type
EMOJI = {
    "all": "🛑", "audio": "🎵", "bots": "🤖", "button": "🔘", "contact": "📇",
    "document": "📄", "forward": "📤", "gif": "🎬", "invite": "✉️", "location": "📍",
    "media": "🖼️", "messages": "💬", "photo": "📷", "poll": "📊", "sticker": "🏷️",
    "url": "🔗", "username": "🆔", "video": "📹", "voice": "🎤", "text": "📝"
}

# ------------------------------
# 📥 ʟᴏᴀᴅ / ꜱᴀᴠᴇ ᴅᴀᴛᴀ
# ------------------------------

def _normalize_keys(d: dict) -> dict:
    if not isinstance(d, dict):
        return {}
    return {str(k): v for k, v in d.items()}

def load_lock_data():
    try:
        if os.path.exists(LOCK_DATA_FILE):
            with open(LOCK_DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                data = _normalize_keys(data)
                print(f"✅ ʟᴏᴄᴋ ᴅᴀᴛᴀ ʟᴏᴀᴅᴇᴅ ꜰʀᴏᴍ {LOCK_DATA_FILE}")
                return data
        else:
            print("ℹ️ ɴᴏ ʟᴏᴄᴋ ᴅᴀᴛᴀ ꜰɪʟᴇ - ꜱᴛᴀʀᴛɪɴɢ ꜰʀᴇꜱʜ")
            return {}
    except Exception as e:
        print(f"❌ ᴇʀʀᴏʀ ʟᴏᴀᴅɪɴɢ ʟᴏᴄᴋ ᴅᴀᴛᴀ: {e}")
        return {}

def save_lock_data():
    try:
        with open(LOCK_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(lock_status, f, indent=4, ensure_ascii=False)
        print(f"💾 ʟᴏᴄᴋ ᴅᴀᴛᴀ ꜱᴀᴠᴇᴅ ᴛᴏ {LOCK_DATA_FILE}")
    except Exception as e:
        print(f"❌ ᴇʀʀᴏʀ ꜱᴀᴠɪɴɢ ʟᴏᴄᴋ ᴅᴀᴛᴀ: {e}")

lock_status = load_lock_data()

atexit.register(save_lock_data)

# ------------------------------
# 🛠️ ʜᴇʟᴘꜰᴜʟ ᴜᴛɪʟɪᴛɪᴇꜱ & ᴀᴜᴛᴏ-ʙᴀᴄᴋᴜᴘ
# ------------------------------
def format_datetime(dt_iso: str) -> str:
    try:
        dt = datetime.fromisoformat(dt_iso)
        return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
    except:
        return str(dt_iso or "")

async def _auto_backup_task():
    """
    ᴀᴜᴛᴏ ʙᴀᴄᴋᴜᴘ ʟᴏᴄᴋ_ꜱᴛᴀᴛᴜꜱ ᴛᴏ ʟᴏᴄᴋ_ᴅᴀᴛᴀ_ʙᴀᴄᴋᴜᴘ.ᴊꜱᴏɴ ᴇᴠᴇʀʏ 5 ᴍɪɴᴜᴛᴇꜱ.
    """
    while True:
        try:
            await asyncio.sleep(300)  # 5 ᴍɪɴᴜᴛᴇꜱ
            with open("lock_data_backup.json", "w", encoding="utf-8") as bf:
                json.dump(lock_status, bf, indent=4, ensure_ascii=False)
            print("💾 ʟᴏᴄᴋ_ᴅᴀᴛᴀ ʙᴀᴄᴋᴜᴘ ꜱᴀᴠᴇᴅ.")
        except Exception as e:
            print(f"❌ ᴀᴜᴛᴏ-ʙᴀᴄᴋᴜᴘ ᴇʀʀᴏʀ: {e}")

# ꜱᴛᴀʀᴛ ʙᴀᴄᴋᴜᴘ ᴛᴀꜱᴋ ꜱᴀꜰᴇʟʏ (ᴍᴀʏ ꜰᴀɪʟ ɪɴ ꜱᴏᴍᴇ ɪᴍᴘᴏʀᴛ ᴄᴏɴᴛᴇxᴛꜱ)
try:
    asyncio.create_task(_auto_backup_task())
except Exception as e:
    print(f"ℹ️ ᴀᴜᴛᴏ-ʙᴀᴄᴋᴜᴘ ᴛᴀꜱᴋ ɴᴏᴛ ꜱᴛᴀʀᴛᴇᴅ ᴀᴜᴛᴏᴍᴀᴛɪᴄᴀʟʟʏ: {e}")

# ------------------------------
# 👮 ᴀᴅᴍɪɴ ᴄʜᴇᴄᴋꜱ
# ------------------------------

async def check_admin_permission(message: Message) -> bool:
    try:
        user = message.from_user
        chat = message.chat
        if not user:
            return False
        if chat.type == ChatType.PRIVATE or user.id == BOT_OWNER_ID:
            return True
        member = await app.get_chat_member(chat.id, user.id)
        status = str(getattr(member, "status", "")).lower()
        return "administrator" in status or "creator" in status or "owner" in status
    except:
        return False

async def check_lockadmin_permission(message: Message) -> bool:
    user = message.from_user
    chat = message.chat
    if not user:
        return False
    if user.id == BOT_OWNER_ID:
        return True
    if chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        try:
            member = await app.get_chat_member(chat.id, user.id)
            status = str(getattr(member, "status", "")).lower()
            return "creator" in status or "owner" in status
        except:
            return False
    return False

# ------------------------------
# 🎯 ᴄᴏᴍᴍᴀɴᴅꜱ
# ------------------------------

@app.on_message(filters.command(["locktypes", "locktypes@anniexrobot"]) & filters.group)
@language
async def locktypes_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 ᴏɴʟʏ ᴀᴅᴍɪɴꜱ / ᴏᴡɴᴇʀ / ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ!")
    
    title = "🔒 **ᴀᴠᴀɪʟᴀʙʟᴇ ʟᴏᴄᴋ ᴛʏᴘᴇꜱ** 🔒\n"
    divider = "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # ꜰɪx: ꜱʜᴏᴡ 'ᴀʟʟ' ᴏɴ ᴛᴏᴘ, ᴋᴇᴇᴘ ʀᴇꜱᴛ ꜱᴀᴍᴇ
    lines = [f"{EMOJI.get('all','')} **ᴀʟʟ**"] + [f"{EMOJI.get(t,'')} **{t}**" for t in LOCKABLES if t != "all"]
    info = title + divider + "\n".join(lines)
    info += "\n\n📖 **ᴜꜱᴀɢᴇ:**\n`/ʟᴏᴄᴋ [ᴛʏᴘᴇ]` ᴏʀ `/ᴜɴʟᴏᴄᴋ [ᴛʏᴘᴇ]`\n⚡ **ǫᴜɪᴄᴋ:** `/ᴜɴʟᴏᴄᴋᴀʟʟ` ᴛᴏ ʀᴇᴍᴏᴠᴇ ᴀʟʟ ʟᴏᴄᴋꜱ\n👑 **ʟᴏᴄᴋᴀᴅᴍɪɴ:** `/ʟᴏᴄᴋᴀᴅᴍɪɴ ᴏɴ/ᴏꜰꜰ`"
    await message.reply_text(info)

@app.on_message(filters.command(["lock", "lock@anniexrobot"]) & filters.group)
@language
async def lock_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 ᴏɴʟʏ ᴀᴅᴍɪɴꜱ / ᴏᴡɴᴇʀ / ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ!")
    try:
        chat_id = str(message.chat.id)
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            return await message.reply_text("❌ **ᴜꜱᴀɢᴇ:** `/ʟᴏᴄᴋ <ᴛʏᴘᴇ>`")
        ltype = parts[1].lower()
        if ltype not in LOCKABLES:
            return await message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ʟᴏᴄᴋ ᴛʏᴘᴇ. ᴜꜱᴇ `/ʟᴏᴄᴋᴛʏᴘᴇꜱ`.")
        if ltype == "all":
            for t in LOCKABLES:
                if t != "all":
                    lock_status.setdefault(chat_id, {})[t] = True
            msg = "🛑 **ᴀʟʟ ᴄᴏɴᴛᴇɴᴛ ᴛʏᴘᴇꜱ ʟᴏᴄᴋᴇᴅ!**\nᴜꜱᴇʀꜱ ᴄᴀɴɴᴏᴛ ꜱᴇɴᴅ ᴀɴʏᴛʜɪɴɢ."
        elif ltype == "media":
            for t in ["photo","video","audio","voice","document","sticker","gif","media"]:
                lock_status.setdefault(chat_id, {})[t] = True
            msg = "🖼️ **ᴍᴇᴅɪᴀ ʟᴏᴄᴋᴇᴅ!**\nᴜꜱᴇʀꜱ ᴄᴀɴɴᴏᴛ ꜱᴇɴᴅ ᴍᴇᴅɪᴀ."
        else:
            lock_status.setdefault(chat_id, {})[ltype] = True
            msg = f"{EMOJI.get(ltype,'🔒')} **ʟᴏᴄᴋᴇᴅ {ʟᴛʏᴘᴇ}** ꜰᴏʀ ɴᴏʀᴍᴀʟ ᴜꜱᴇʀꜱ!"
        # ᴍᴇᴛᴀᴅᴀᴛᴀ: ᴡʜᴏ ᴜᴘᴅᴀᴛᴇᴅ ᴀɴᴅ ᴡʜᴇɴ
        lock_status.setdefault(chat_id, {})["_updated"] = datetime.utcnow().isoformat()
        lock_status.setdefault(chat_id, {})["_updated_by"] = message.from_user.username or message.from_user.first_name or str(message.from_user.id)
        lock_status.setdefault(chat_id, {})["_updated_at"] = datetime.utcnow().isoformat()
        save_lock_data()
        await message.reply_text(msg)
    except Exception as e:
        print(f"❌ ʟᴏᴄᴋᴄᴍᴅᴇʀʀᴏʀ: {e}")
        await message.reply_text("❌ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ʟᴏᴄᴋɪɴɢ.")

@app.on_message(filters.command(["unlock", "unlock@anniexrobot"]) & filters.group)
@language
async def unlock_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 ᴏɴʟʏ ᴀᴅᴍɪɴꜱ / ᴏᴡɴᴇʀ / ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ!")
    try:
        chat_id = str(message.chat.id)
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            return await message.reply_text("❌ **ᴜꜱᴀɢᴇ:** `/ᴜɴʟᴏᴄᴋ <ᴛʏᴘᴇ>`")
        ltype = parts[1].lower()
        if ltype == "all":
            lock_status.pop(chat_id, None)
            msg = "✅ **ᴀʟʟ ᴄᴏɴᴛᴇɴᴛ ᴜɴʟᴏᴄᴋᴇᴅ!**"
        elif ltype == "media":
            for t in ["photo","video","audio","voice","document","sticker","gif","media"]:
                if chat_id in lock_status and t in lock_status[chat_id]:
                    lock_status[chat_id].pop(t, None)
            msg = "✅ **ᴍᴇᴅɪᴀ ᴜɴʟᴏᴄᴋᴇᴅ!**"
        else:
            if chat_id in lock_status and ltype in lock_status[chat_id]:
                lock_status[chat_id].pop(ltype, None)
                msg = f"✅ {EMOJI.get(ltype,'🔓')} **ᴜɴʟᴏᴄᴋᴇᴅ {ʟᴛʏᴘᴇ}**"
            else:
                msg = "ℹ️ ᴛʜᴀᴛ ᴛʏᴘᴇ ᴡᴀꜱɴ'ᴛ ʟᴏᴄᴋᴇᴅ."
        if chat_id in lock_status and not any(k for k in lock_status[chat_id] if not k.startswith("_")):
            lock_status.pop(chat_id, None)
        # ᴍᴇᴛᴀᴅᴀᴛᴀ: ᴡʜᴏ ᴜᴘᴅᴀᴛᴇᴅ ᴀɴᴅ ᴡʜᴇɴ
        lock_status.setdefault(chat_id, {})["_updated_by"] = message.from_user.username or message.from_user.first_name or str(message.from_user.id)
        lock_status.setdefault(chat_id, {})["_updated_at"] = datetime.utcnow().isoformat()
        save_lock_data()
        await message.reply_text(msg)
    except Exception as e:
        print(f"❌ ᴜɴʟᴏᴄᴋᴄᴍᴅᴇʀʀᴏʀ: {e}")
        await message.reply_text("❌ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ᴜɴʟᴏᴄᴋɪɴɢ.")

@app.on_message(filters.command(["unlockall", "unlockall@anniexrobot"]) & filters.group)
@language
async def unlockall_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 ᴏɴʟʏ ᴀᴅᴍɪɴꜱ / ᴏᴡɴᴇʀ / ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ!")
    chat_id = str(message.chat.id)
    if chat_id in lock_status:
        lock_status.pop(chat_id, None)
        save_lock_data()
        await message.reply_text("✅ **ᴀʟʟ ʟᴏᴄᴋꜱ ʀᴇᴍᴏᴠᴇᴅ!**")
    else:
        await message.reply_text("ℹ️ ɴᴏ ᴀᴄᴛɪᴠᴇ ʟᴏᴄᴋꜱ ꜰᴏᴜɴᴅ.")

@app.on_message(filters.command(["locks", "locks@anniexrobot"]) & filters.group)
@language
async def locks_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 ᴏɴʟʏ ᴀᴅᴍɪɴꜱ / ᴏᴡɴᴇʀ / ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ!")
    chat_id = str(message.chat.id)
    data = lock_status.get(chat_id, {})
    if not data or not any(v for k,v in data.items() if not str(k).startswith("_")):
        return await message.reply_text("ℹ️ ɴᴏ ʟᴏᴄᴋꜱ ᴇɴᴀʙʟᴇᴅ.")
    
    title = f"🔐 **ᴄᴜʀʀᴇɴᴛ ʟᴏᴄᴋꜱ** ({sum(1 for v in data.values() if v and not str(v).startswith('_'))} ᴀᴄᴛɪᴠᴇ)\n"
    divider = "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    lines = [f"{EMOJI.get(t,'')} **{t}** → {'🔒 ʟᴏᴄᴋᴇᴅ' if data.get(t) else '🔓 ᴜɴʟᴏᴄᴋᴇᴅ'}" for t in LOCKABLES if t != "all"]
    await message.reply_text(title + divider + "\n".join(lines))

# ------------------------------
# 👑 ʟᴏᴄᴋᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅ
# ------------------------------

@app.on_message(filters.command(["lockadmin", "lockadmin@anniexrobot"]) & filters.group)
@language
async def lockadmin_cmd(client, message: Message, _):
    if not await check_lockadmin_permission(message):
        return await message.reply_text("🚫 ᴏɴʟʏ ʙᴏᴛ ᴏᴡɴᴇʀ ᴏʀ ɢʀᴏᴜᴘ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ!")
    chat_id = str(message.chat.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        current = lock_status.get(chat_id, {}).get("_lockadmin", False)
        status = "🟢 **ᴏɴ**" if current else "🔴 **ᴏꜰꜰ**"
        return await message.reply_text(f"👑 **ʟᴏᴄᴋᴀᴅᴍɪɴ ꜱᴛᴀᴛᴜꜱ:** {status}\n📖 **ᴜꜱᴀɢᴇ:** `/ʟᴏᴄᴋᴀᴅᴍɪɴ ᴏɴ/ᴏꜰꜰ`")
    mode = parts[1].lower()
    if mode in ["on","yes","true","enable"]:
        lock_status.setdefault(chat_id, {})["_lockadmin"] = True
        save_lock_data()
        await message.reply_text("👑 **ʟᴏᴄᴋᴀᴅᴍɪɴ ᴇɴᴀʙʟᴇᴅ!**\nᴀᴅᴍɪɴ ᴍᴇᴅɪᴀ ɪꜱ ʟᴏᴄᴋᴇᴅ.")
    elif mode in ["off","no","false","disable"]:
        lock_status.setdefault(chat_id, {})["_lockadmin"] = False
        save_lock_data()
        await message.reply_text("✅ **ʟᴏᴄᴋᴀᴅᴍɪɴ ᴅɪꜱᴀʙʟᴇᴅ!**\nᴀᴅᴍɪɴ ᴍᴇᴅɪᴀ ᴀʟʟᴏᴡᴇᴅ.")
    else:
        await message.reply_text("❌ ɪɴᴠᴀʟɪᴅ ᴍᴏᴅᴇ. ᴜꜱᴇ `/ʟᴏᴄᴋᴀᴅᴍɪɴ ᴏɴ/ᴏꜰꜰ`")

# ------------------------------
# 🤫 ꜱɪʟᴇɴᴛ ᴍᴏᴅᴇ ᴛᴏɢɢʟᴇ
# ------------------------------
@app.on_message(filters.command(["locksilent", "locksilent@anniexrobot"]) & filters.group)
@language
async def locksilent_cmd(client, message: Message, _):
    if not await check_lockadmin_permission(message):
        return await message.reply_text("🚫 ᴏɴʟʏ ʙᴏᴛ ᴏᴡɴᴇʀ ᴏʀ ɢʀᴏᴜᴘ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ!")
    chat_id = str(message.chat.id)
    parts = message.text.split(maxsplit=1)
    mode = parts[1].lower() if len(parts) > 1 else None
    data = lock_status.setdefault(chat_id, {})
    if mode in ["on", "yes", "true", "enable"]:
        data["_silent"] = True
        data["_updated_by"] = message.from_user.username or message.from_user.first_name or str(message.from_user.id)
        data["_updated_at"] = datetime.utcnow().isoformat()
        save_lock_data()
        await message.reply_text("🤫 **ꜱɪʟᴇɴᴛ ᴍᴏᴅᴇ ᴇɴᴀʙʟᴇᴅ**\nᴡᴀʀɴɪɴɢ ᴍᴇꜱꜱᴀɢᴇꜱ ᴡɪʟʟ ʙᴇ ꜱᴜᴘᴘʀᴇꜱꜱᴇᴅ.")
    elif mode in ["off", "no", "false", "disable"]:
        data["_silent"] = False
        data["_updated_by"] = message.from_user.username or message.from_user.first_name or str(message.from_user.id)
        data["_updated_at"] = datetime.utcnow().isoformat()
        save_lock_data()
        await message.reply_text("🔔 **ꜱɪʟᴇɴᴛ ᴍᴏᴅᴇ ᴅɪꜱᴀʙʟᴇᴅ**\nᴡᴀʀɴɪɴɢ ᴍᴇꜱꜱᴀɢᴇꜱ ᴡɪʟʟ ʙᴇ ꜱʜᴏᴡɴ.")
    else:
        status = "🟢 **ᴏɴ**" if data.get("_silent") else "🔴 **ᴏꜰꜰ**"
        await message.reply_text(f"⚙️ **ꜱɪʟᴇɴᴛ ᴍᴏᴅᴇ:** {status}\n📖 **ᴜꜱᴀɢᴇ:** `/ʟᴏᴄᴋꜱɪʟᴇɴᴛ ᴏɴ/ᴏꜰꜰ`")

# ------------------------------
# 📊 ʟᴏᴄᴋꜱᴛᴀᴛᴜꜱ ᴄᴏᴍᴍᴀɴᴅ
# ------------------------------
@app.on_message(filters.command(["lockstatus", "lockstatus@anniexrobot"]) & filters.group)
@language
async def lockstatus_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 ᴏɴʟʏ ᴀᴅᴍɪɴꜱ / ᴏᴡɴᴇʀ / ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ!")
    chat_id = str(message.chat.id)
    data = lock_status.get(chat_id, {})
    if not data or not any(v for k,v in data.items() if not str(k).startswith("_")):
        return await message.reply_text("ℹ️ ɴᴏ ʟᴏᴄᴋꜱ ᴇɴᴀʙʟᴇᴅ.")

    title = "🔐 **ᴄᴜʀʀᴇɴᴛ ʟᴏᴄᴋꜱ**\n"
    divider = "━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    lines = []
    # ꜱʜᴏᴡ 'ᴀʟʟ' ꜰɪʀꜱᴛ
    lines.append(f"{EMOJI.get('all','🛑')} **ᴀʟʟ** → {'🔒 ʟᴏᴄᴋᴇᴅ' if data.get('all') else '🔓 ᴜɴʟᴏᴄᴋᴇᴅ'}")
    for t in LOCKABLES:
        if t == "all" or t.startswith("_"):
            continue
        state = "🔒 ʟᴏᴄᴋᴇᴅ" if data.get(t) else "🔓 ᴜɴʟᴏᴄᴋᴇᴅ"
        lines.append(f"{EMOJI.get(t,'')} **{t}** → {state}")

    text = title + divider + "\n".join(lines)
    # ᴍᴇᴛᴀᴅᴀᴛᴀ
    if data.get("_updated_by") or data.get("_updated_at"):
        text += "\n\n📝 **ᴜᴘᴅᴀᴛᴇ ɪɴꜰᴏ:**\n"
        if data.get("_updated_by"):
            text += f"👤 **ʙʏ:** {data.get('_updated_by')}\n"
        if data.get("_updated_at"):
            text += f"🕒 **ᴀᴛ:** {format_datetime(data.get('_updated_at'))}\n"
    # ꜱɪʟᴇɴᴛ ᴍᴏᴅᴇ ɪɴꜰᴏ
    text += f"\n🤫 **ꜱɪʟᴇɴᴛ ᴍᴏᴅᴇ:** {'🟢 ᴏɴ' if data.get('_silent') else '🔴 ᴏꜰꜰ'}"

    await message.reply_text(text)

# ------------------------------
# 🆘 ʟᴏᴄᴋ ʜᴇʟᴘ ᴄᴏᴍᴍᴀɴᴅ
# ------------------------------

@app.on_message(filters.command(["lockhelp", "lockhelp@anniexrobot"]) & filters.group)
@language
async def lockhelp_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text(
            "🚫 ᴏɴʟʏ ᴀᴅᴍɪɴꜱ / ᴏᴡɴᴇʀ / ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ᴛʜɪꜱ ᴄᴏᴍᴍᴀɴᴅ!"
        )

    title = "🎛️ **ʟᴏᴄᴋ ꜱʏꜱᴛᴇᴍ ᴄᴏᴍᴍᴀɴᴅꜱ** 🎛️\n"
    divider = "━━━━━━━━━━━━━━━━━━━━━━━\n"

    cmds = [
        "🔒 **/lock [type]** — ʟᴏᴄᴋ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ᴄᴏɴᴛᴇɴᴛ ᴛʏᴘᴇ.",
        "🔓 **/unlock [type]** — ᴜɴʟᴏᴄᴋ ᴀ ꜱᴘᴇᴄɪꜰɪᴄ ᴄᴏɴᴛᴇɴᴛ ᴛʏᴘᴇ.",
        "🛑 **/lock all** — ʟᴏᴄᴋ ᴇᴠᴇʀʏᴛʜɪɴɢ.",
        "✅ **/unlock all** — ᴜɴʟᴏᴄᴋ ᴀʟʟ ᴄᴏɴᴛᴇɴᴛ.",
        "📋 **/locktypes** — ꜱʜᴏᴡ ᴀʟʟ ᴀᴠᴀɪʟᴀʙʟᴇ ʟᴏᴄᴋ ᴛʏᴘᴇꜱ.",
        "🔐 **/locks** — ᴠɪᴇᴡ ᴄᴜʀʀᴇɴᴛ ᴀᴄᴛɪᴠᴇ ʟᴏᴄᴋꜱ.",
        "📊 **/lockstatus** — ᴅᴇᴛᴀɪʟᴇᴅ ʟᴏᴄᴋ ꜱᴛᴀᴛᴜꜱ + ᴜᴘᴅᴀᴛᴇ ɪɴꜰᴏ.",
        "👑 **/lockadmin on/off** — ᴛᴏɢɢʟᴇ ᴀᴅᴍɪɴ ᴍᴇᴅɪᴀ ʟᴏᴄᴋ.",
        "🤫 **/locksilent on/off** — ꜱɪʟᴇɴᴛ ᴍᴏᴅᴇ (ɴᴏ ᴡᴀʀɴɪɴɢ ᴍꜱɢ).",
        "🆘 **/lockhelp** — ꜱʜᴏᴡ ᴛʜɪꜱ ʜᴇʟᴘ ᴍᴇɴᴜ.",
    ]

    examples = [
        "🔹 `/lock photo` → ʟᴏᴄᴋ ɪᴍᴀɢᴇꜱ",
        "🔹 `/unlock video` → ᴜɴʟᴏᴄᴋ ᴠɪᴅᴇᴏꜱ",
        "🔹 `/lock all` → ꜰᴜʟʟ ɢʀᴏᴜᴘ ʟᴏᴄᴋ",
        "🔹 `/unlock all` → ʀᴇꜱᴇᴛ ᴀʟʟ ʟᴏᴄᴋꜱ"
    ]

    text = (
        title
        + divider
        + "\n".join(cmds)
        + "\n\n✨ **ᴇxᴀᴍᴘʟᴇꜱ:**\n"
        + "\n".join(examples)
        + "\n\n🧠 ᴜꜱᴇ `/locktypes` ᴛᴏ ꜱᴇᴇ ᴀʟʟ ᴀᴠᴀɪʟᴀʙʟᴇ ʟᴏᴄᴋ ᴛʏᴘᴇꜱ."
        + "\n🔐 ᴏɴʟʏ ᴀᴅᴍɪɴꜱ ᴀɴᴅ ʙᴏᴛ ᴏᴡɴᴇʀ ᴄᴀɴ ᴜꜱᴇ ʟᴏᴄᴋ ꜰᴇᴀᴛᴜʀᴇꜱ."
    )

    await message.reply_text(text, disable_web_page_preview=True)

# ------------------------------
# 👀 ᴡᴀᴛᴄʜᴇʀ - ᴅᴇʟᴇᴛᴇ ʟᴏᴄᴋᴇᴅ ᴍᴇꜱꜱᴀɢᴇꜱ (ꜰɪɴᴀʟ ꜰɪx)
# ------------------------------

@app.on_message(filters.group, group=69)  # ɪɴᴄʀᴇᴀꜱᴇᴅ ᴘʀɪᴏʀɪᴛʏ ᴛᴏ ᴀᴠᴏɪᴅ ʙᴇɪɴɢ ꜱᴋɪᴘᴘᴇᴅ
async def lock_watcher(client, message: Message):
    try:
        if not message.from_user or message.from_user.is_bot:
            return
        chat_id = str(message.chat.id)
        data = lock_status.get(chat_id, {})
        if not data:
            return

        is_admin = await check_admin_permission(message)
        lockadmin_enabled = data.get("_lockadmin", False)

        should_delete = False
        detected_lock = ""

        # ᴀᴅᴍɪɴ + ʟᴏᴄᴋᴀᴅᴍɪɴ: ɪꜰ ʟᴏᴄᴋᴀᴅᴍɪɴ ᴇɴᴀʙʟᴇᴅ, ʀᴇꜱᴛʀɪᴄᴛ ᴀᴅᴍɪɴꜱ ᴛᴏᴏ ꜰᴏʀ ᴍᴇᴅɪᴀ
        if is_admin and lockadmin_enabled:
            for t in ["photo","video","audio","voice","document","sticker","gif"]:
                if getattr(message, t, None):
                    should_delete, detected_lock = True, t
                    break

        # ɴᴏʀᴍᴀʟ ᴜꜱᴇʀꜱ (ꜰᴜʟʟ ꜰɪx)
        elif not is_admin:
            # ɪꜰ "ᴀʟʟ" ɪꜱ ᴇɴᴀʙʟᴇᴅ — ᴅᴇʟᴇᴛᴇ ᴀɴʏ ᴋɪɴᴅ ᴏꜰ ᴜꜱᴇʀ ᴄᴏɴᴛᴇɴᴛ ɪɴᴄʟᴜᴅɪɴɢ ᴛᴇxᴛ/ᴄᴀᴘᴛɪᴏɴ
            if data.get("all"):
                if (
                    message.text
                    or message.caption
                    or message.photo
                    or message.video
                    or message.sticker
                    or message.document
                    or message.animation
                    or message.voice
                    or message.audio
                    or message.poll
                ):
                    should_delete, detected_lock = True, "all"

            elif (message.text or message.caption) and (data.get("text") or data.get("messages")):
                should_delete, detected_lock = True, "text"

            else:
                for t in LOCKABLES:
                    if t in ["all", "text", "messages"]:
                        continue
                    attr = getattr(message, t, None)
                    if attr and data.get(t):
                        should_delete, detected_lock = True, t
                        break

        if should_delete:
            try:
                await asyncio.sleep(0.3)
                await message.delete()
                warn = f"⚠️ {message.from_user.mention}, **{detected_lock}** ɪꜱ ʟᴏᴄᴋᴇᴅ!"
                # ʀᴇꜱᴘᴇᴄᴛ ꜱɪʟᴇɴᴛ ᴍᴏᴅᴇ: ɪꜰ _ꜱɪʟᴇɴᴛ ᴛʀᴜᴇ ᴛʜᴇɴ ꜱᴋɪᴘ ꜱᴇɴᴅɪɴɢ ᴡᴀʀɴ
                if not data.get("_silent"):
                    try:
                        wmsg = await app.send_message(message.chat.id, warn)
                        await asyncio.sleep(2)
                        try:
                            await wmsg.delete()
                        except:
                            pass
                    except Exception as e:
                        print(f"❌ ᴡᴀʀɴɪɴɢ ꜱᴇɴᴅ ᴇʀʀᴏʀ: {e}")
            except Exception as e:
                print(f"❌ ᴅᴇʟᴇᴛᴇᴇʀʀᴏʀ: {e}")
    except Exception as e:
        print(f"❌ ᴡᴀᴛᴄʜᴇʀᴇʀʀᴏʀ: {e}")

print("✅ ʟᴏᴄᴋ ꜱʏꜱᴛᴇᴍ ʀᴇᴀᴅʏ")
print(f"🔹 ᴅᴀᴛᴀ ꜰɪʟᴇ: {LOCK_DATA_FILE}")
print(f"🔹 ʟᴏᴀᴅᴇᴅ ʟᴏᴄᴋꜱ ꜰᴏʀ {len(lock_status)} ᴄʜᴀᴛꜱ")