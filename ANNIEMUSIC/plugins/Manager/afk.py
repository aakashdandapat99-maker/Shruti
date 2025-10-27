from datetime import datetime, timedelta
from pyrogram import filters
from pyrogram.types import Message
from ANNIEMUSIC import app
from motor.motor_asyncio import AsyncIOMotorClient
import os

# 🧠 MongoDB setup
MONGO_URL = os.getenv("MONGO_DB_URL", "mongodb+srv://rajkhilchi786:F1uEyWGo9UTeqmTV@cluster0.bug4pqt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
mongo = AsyncIOMotorClient(MONGO_URL)
db = mongo["ANNIEMUSIC"]
afk_collection = db["afk_users"]


# ================== SET AFK ==================
@app.on_message(filters.command("afk") & (filters.group | filters.private))
async def set_afk(_, message: Message):
    user = message.from_user
    if not user:
        return await message.reply_text("❌ User not found.")

    user_id = user.id
    name = user.first_name
    reason = " ".join(message.command[1:]) if len(message.command) > 1 else "No reason provided"
    time_now = datetime.utcnow()

    await afk_collection.update_one(
        {"user_id": user_id},
        {"$set": {"reason": reason, "time": time_now, "name": name}},
        upsert=True
    )

    await message.reply_text(
        f"😴 {name} is now AFK!\n\n"
        f"🕒 Reason: {reason}\n"
        f"💤 I'll let others know you're away."
    )


# ================== REPLY WHEN MENTIONED ==================
@app.on_message(filters.text & ~filters.bot)
async def check_afk_mentions(_, message: Message):
    if not message.entities:
        return

    for entity in message.entities:
        if entity.type == "mention":
            username = message.text[entity.offset + 1 : entity.offset + entity.length]
            try:
                user = await app.get_users(username)
                afk_user = await afk_collection.find_one({"user_id": user.id})
                if afk_user:
                    since = datetime.utcnow() - afk_user["time"]
                    time_afk = str(timedelta(seconds=int(since.total_seconds())))
                    await message.reply_text(
                        f"💤 {afk_user['name']} is currently AFK.\n"
                        f"🕒 Since: {time_afk} ago\n"
                        f"📄 Reason: {afk_user['reason']}"
                    )
            except Exception:
                continue


# ================== REMOVE AFK WHEN USER RETURNS ==================
@app.on_message(filters.text & filters.me)
async def remove_afk(_, message: Message):
    user_id = message.from_user.id
    afk_user = await afk_collection.find_one({"user_id": user_id})

    if afk_user:
        since = datetime.utcnow() - afk_user["time"]
        time_afk = str(timedelta(seconds=int(since.total_seconds())))
        await afk_collection.delete_one({"user_id": user_id})
        await message.reply_text(
            f"✅ Welcome back {afk_user['name']}!\n"
            f"🕒 You were away for: {time_afk}\n"
            f"📄 Reason: {afk_user['reason']}"
        )


print("✅ afk.py successfully loaded")