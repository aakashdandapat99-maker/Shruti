from motor.motor_asyncio import AsyncIOMotorClient

# 🔹 Apna MongoDB URL yahan daalein
MONGO_URL = "mongodb+srv://rajkhilchi786:F1uEyWGo9UTeqmTV@cluster0.bug4pqt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = AsyncIOMotorClient(MONGO_URL)
db = client["ANNIEMUSIC"]
autoapprove_db = db["autoapprove"]

# -----------------------
# AutoApprove functions
async def autoapprove_on(chat_id: int):
    await autoapprove_db.update_one(
        {"chat_id": chat_id},
        {"$set": {"auto": True, "manual": False}},
        upsert=True
    )

async def autoapprove_off(chat_id: int):
    await autoapprove_db.update_one(
        {"chat_id": chat_id},
        {"$set": {"auto": False}},
        upsert=True
    )

async def is_autoapprove_on(chat_id: int) -> bool:
    doc = await autoapprove_db.find_one({"chat_id": chat_id})
    return doc.get("auto", False) if doc else False

# -----------------------
# Manual Approve functions
async def manual_on(chat_id: int):
    await autoapprove_db.update_one(
        {"chat_id": chat_id},
        {"$set": {"manual": True, "auto": False}},
        upsert=True
    )

async def manual_off(chat_id: int):
    await autoapprove_db.update_one(
        {"chat_id": chat_id},
        {"$set": {"manual": False}},
        upsert=True
    )

async def is_manual_on(chat_id: int) -> bool:
    doc = await autoapprove_db.find_one({"chat_id": chat_id})
    return doc.get("manual", False) if doc else False