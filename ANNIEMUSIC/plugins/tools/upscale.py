import os
import aiohttp
import aiofiles
import base64
from config import DEEP_API
from ANNIEMUSIC import app
from pyrogram import filters
from pyrogram.types import Message

PIXABAY_API = os.getenv("PIXABAY_API")
HF_API_KEY = os.getenv("HF_API_KEY")

# -----------------------------
# 📥 Download helper
async def download_from_url(path: str, url: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                async with aiofiles.open(path, mode="wb") as f:
                    await f.write(await resp.read())
                return path
    return None


# -----------------------------
# 📤 Safe JSON fetcher
async def fetch_json(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            try:
                return await resp.json()
            except Exception:
                text = await resp.text()
                raise Exception(f"Invalid JSON response: {resp.status}, {text[:200]}")


# ======================================================
# 🎨 /getdraw — AI Art (Lexica + Pixabay)
# ======================================================
@app.on_message(filters.command("getdraw"))
async def draw_image(_, message: Message):
    reply = message.reply_to_message
    query = None

    if reply and reply.text:
        query = reply.text
    elif len(message.command) > 1:
        query = message.text.split(None, 1)[1]

    if not query:
        return await message.reply_text("💬 Please reply or provide text.")

    status = await message.reply_text("🎨 Generating image... please wait")

    user_id = message.from_user.id
    chat_id = message.chat.id
    temp_path = f"cache/{user_id}_{chat_id}_{message.id}.jpg"

    try:
        # Try Lexica (AI art)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://lexica.art/api/v1/search?q={query}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("images"):
                        image_url = data["images"][0]["src"]
                        final_path = await download_from_url(temp_path, image_url)
                        await status.delete()
                        return await message.reply_photo(final_path, caption=f"🖼️ `{query}` (Lexica)")

        # Fallback: Pixabay
        if PIXABAY_API:
            url = f"https://pixabay.com/api/?key={PIXABAY_API}&q={query}&image_type=photo"
            data = await fetch_json(url)
            if data.get("hits"):
                image_url = data["hits"][0]["largeImageURL"]
                final_path = await download_from_url(temp_path, image_url)
                await status.delete()
                return await message.reply_photo(final_path, caption=f"🖼️ `{query}` (Pixabay)")

        await status.edit("❌ No image found from Lexica or Pixabay.")

    except Exception as e:
        await status.edit(f"⚠️ Error: {e}")


# ======================================================
# 🚀 /upscale — Hugging Face Real-ESRGAN (Fixed + Public Model)
# ======================================================
@app.on_message(filters.command("upscale"))
async def upscale_image(_, message: Message):
    if not HF_API_KEY:
        return await message.reply_text("🚫 Missing `HF_API_KEY` in .env file.")

    reply = message.reply_to_message
    if not reply or not reply.photo:
        return await message.reply_text("📎 Please reply to an image to upscale.")

    status = await message.reply_text("🔄 Upscaling image... please wait")

    try:
        # Download the image
        local_path = await reply.download()
        with open(local_path, "rb") as f:
            image_bytes = f.read()

        # Send to Hugging Face (Real-ESRGAN)
        async with aiohttp.ClientSession() as session:
            response = await session.post(
                "https://api-inference.huggingface.co/models/Xenova/Real-ESRGAN",
                headers={
                    "Authorization": f"Bearer {HF_API_KEY}",
                    "Content-Type": "application/octet-stream"
                },
                data=image_bytes
            )

            if response.status != 200:
                text = await response.text()
                raise Exception(f"API Error {response.status}: {text[:200]}")

            result = await response.read()

        # Save enhanced image
        output_path = f"cache/upscaled_{message.id}.png"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        async with aiofiles.open(output_path, "wb") as f:
            await f.write(result)

        await status.delete()
        await message.reply_document(output_path, caption="✨ Image upscaled successfully using Real-ESRGAN")

    except Exception as e:
        await status.edit(f"⚠️ Error: {e}")