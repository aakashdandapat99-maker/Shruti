# nightmodedb.py
from motor.motor_asyncio import AsyncIOMotorClient

# 🔹 Yahan apna MongoDB URL manually dal do
MONGO_URL = "mongodb+srv://rajkhilchi786:F1uEyWGo9UTeqmTV@cluster0.bug4pqt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = AsyncIOMotorClient(MONGO_URL)
db = client["ANNIEMUSIC"]  # Database name
nightdb = db["nightmode"]   # Collection name

# Enable nightmode for a chat
async def nightmode_on(chat_id: int):
    await nightdb.update_one(
        {"chat_id": chat_id},
        {"$set": {"chat_id": chat_id}},
        upsert=True
    )

# Disable nightmode for a chat
async def nightmode_off(chat_id: int):
    await nightdb.delete_one({"chat_id": chat_id})

# Get all chats with nightmode enabled
async def get_nightchats():
    return await nightdb.find().to_list(length=None)