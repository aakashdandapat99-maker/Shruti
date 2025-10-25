# lock.py
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
# LOCK SYSTEM CONFIG
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
# LOAD / SAVE DATA
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
                print(f"✅ Lock data loaded from {LOCK_DATA_FILE}")
                return data
        else:
            print("ℹ️ No lock data file - starting fresh")
            return {}
    except Exception as e:
        print(f"❌ Error loading lock data: {e}")
        return {}

def save_lock_data():
    try:
        with open(LOCK_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(lock_status, f, indent=4, ensure_ascii=False)
        print(f"💾 Lock data saved to {LOCK_DATA_FILE}")
    except Exception as e:
        print(f"❌ Error saving lock data: {e}")

lock_status = load_lock_data()

atexit.register(save_lock_data)

# ------------------------------
# ADMIN CHECKS
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
# COMMANDS
# ------------------------------

@app.on_message(filters.command(["locktypes", "locktypes@anniexrobot"]) & filters.group)
@language
async def locktypes_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 Only Admins / Owner / Bot Owner can use this command!")
    lines = [f"{EMOJI.get(t,'')} {t}" for t in LOCKABLES if t != "all"]
    info = "🔒 **Available Lock Types:**\n\n" + "\n".join(lines)
    info += "\n\nUsage: /lock [type] or /unlock [type]\nQuick: /unlockall to remove all locks\nLockAdmin: /lockadmin on/off"
    await message.reply_text(info)

@app.on_message(filters.command(["lock", "lock@anniexrobot"]) & filters.group)
@language
async def lock_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 Only Admins / Owner / Bot Owner can use this command!")
    try:
        chat_id = str(message.chat.id)
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            return await message.reply_text("❌ Usage: /lock <type>")
        ltype = parts[1].lower()
        if ltype not in LOCKABLES:
            return await message.reply_text("❌ Invalid lock type. Use /locktypes.")
        if ltype == "all":
            for t in LOCKABLES:
                if t != "all":
                    lock_status.setdefault(chat_id, {})[t] = True
            msg = "🚫 All content types locked! Users cannot send anything."
        elif ltype == "media":
            for t in ["photo","video","audio","voice","document","sticker","gif","media"]:
                lock_status.setdefault(chat_id, {})[t] = True
            msg = "🖼️ Media locked! Users cannot send media."
        else:
            lock_status.setdefault(chat_id, {})[ltype] = True
            msg = f"{EMOJI.get(ltype,'🔒')} Locked {ltype} for normal users!"
        lock_status.setdefault(chat_id, {})["_updated"] = datetime.utcnow().isoformat()
        save_lock_data()
        await message.reply_text(msg)
    except Exception as e:
        print(f"❌ LockCmdError: {e}")
        await message.reply_text("❌ Error while locking.")

@app.on_message(filters.command(["unlock", "unlock@anniexrobot"]) & filters.group)
@language
async def unlock_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 Only Admins / Owner / Bot Owner can use this command!")
    try:
        chat_id = str(message.chat.id)
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            return await message.reply_text("❌ Usage: /unlock <type>")
        ltype = parts[1].lower()
        if ltype == "all":
            lock_status.pop(chat_id, None)
            msg = "✅ All content unlocked!"
        elif ltype == "media":
            for t in ["photo","video","audio","voice","document","sticker","gif","media"]:
                if chat_id in lock_status and t in lock_status[chat_id]:
                    lock_status[chat_id].pop(t, None)
            msg = "✅ Media unlocked!"
        else:
            if chat_id in lock_status and ltype in lock_status[chat_id]:
                lock_status[chat_id].pop(ltype, None)
                msg = f"✅ {EMOJI.get(ltype,'🔓')} Unlocked {ltype}"
            else:
                msg = "ℹ️ That type wasn't locked."
        if chat_id in lock_status and not any(k for k in lock_status[chat_id] if not k.startswith("_")):
            lock_status.pop(chat_id, None)
        save_lock_data()
        await message.reply_text(msg)
    except Exception as e:
        print(f"❌ UnlockCmdError: {e}")
        await message.reply_text("❌ Error while unlocking.")

@app.on_message(filters.command(["unlockall", "unlockall@anniexrobot"]) & filters.group)
@language
async def unlockall_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 Only Admins / Owner / Bot Owner can use this command!")
    chat_id = str(message.chat.id)
    if chat_id in lock_status:
        lock_status.pop(chat_id, None)
        save_lock_data()
        await message.reply_text("✅ All locks removed!")
    else:
        await message.reply_text("ℹ️ No active locks found.")

@app.on_message(filters.command(["locks", "locks@anniexrobot"]) & filters.group)
@language
async def locks_cmd(client, message: Message, _):
    if not await check_admin_permission(message):
        return await message.reply_text("🚫 Only Admins / Owner / Bot Owner can use this command!")
    chat_id = str(message.chat.id)
    data = lock_status.get(chat_id, {})
    if not data or not any(v for k,v in data.items() if not str(k).startswith("_")):
        return await message.reply_text("ℹ️ No locks enabled.")
    lines = [f"{EMOJI.get(t,'')} {t} -> {'🔒 LOCKED' if data.get(t) else '🔓 UNLOCKED'}" for t in LOCKABLES if t != "all"]
    await message.reply_text(f"🔐 Current Locks ({sum(1 for v in data.values() if v and not str(v).startswith('_'))} active):\n\n" + "\n".join(lines))

# ------------------------------
# LOCKADMIN COMMAND
# ------------------------------

@app.on_message(filters.command(["lockadmin", "lockadmin@anniexrobot"]) & filters.group)
@language
async def lockadmin_cmd(client, message: Message, _):
    if not await check_lockadmin_permission(message):
        return await message.reply_text("🚫 Only Bot Owner or Group Owner can use this command!")
    chat_id = str(message.chat.id)
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        current = lock_status.get(chat_id, {}).get("_lockadmin", False)
        status = "ON" if current else "OFF"
        return await message.reply_text(f"🔒 LockAdmin Status: {status}\nUsage: /lockadmin on/off")
    mode = parts[1].lower()
    if mode in ["on","yes","true","enable"]:
        lock_status.setdefault(chat_id, {})["_lockadmin"] = True
        save_lock_data()
        await message.reply_text("🔒 LockAdmin ENABLED! Admin media is locked.")
    elif mode in ["off","no","false","disable"]:
        lock_status.setdefault(chat_id, {})["_lockadmin"] = False
        save_lock_data()
        await message.reply_text("✅ LockAdmin DISABLED! Admin media allowed.")
    else:
        await message.reply_text("❌ Invalid mode. Use /lockadmin on/off")

# ------------------------------
# WATCHER - DELETE LOCKED MESSAGES
# ------------------------------

@app.on_message(filters.group, group=5)
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

        # Admin + LockAdmin
        if is_admin and lockadmin_enabled:
            for t in ["photo","video","audio","voice","document","sticker","gif"]:
                if getattr(message, t, None):
                    should_delete, detected_lock = True, t
                    break

        # Normal users
        elif not is_admin:
            if data.get("all"):
                should_delete, detected_lock = True, "all"
            else:
                for t in LOCKABLES:
                    if t == "all": continue
                    attr = getattr(message, t, None)
                    if t in ["messages","text"] and (message.text or message.caption):
                        detected_lock = t
                    elif attr: detected_lock = t
                    if detected_lock and data.get(detected_lock):
                        should_delete = True
                        break

        if should_delete:
            try:
                await asyncio.sleep(0.3)
                await message.delete()
                warn = f"⚠️ {message.from_user.mention}, {detected_lock} is locked!"
                wmsg = await app.send_message(message.chat.id, warn)
                await asyncio.sleep(2)
                try: await wmsg.delete()
                except: pass
            except Exception as e:
                print(f"❌ DeleteError: {e}")
    except Exception as e:
        print(f"❌ WatcherError: {e}")

print("✅ LOCK SYSTEM READY")
print(f"🔹 Data file: {LOCK_DATA_FILE}")
print(f"🔹 Loaded locks for {len(lock_status)} chats")