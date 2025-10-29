from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from ANNIEMUSIC import app
from ANNIEMUSIC.plugins.Manager.autoapprovedb import (
    autoapprove_on, autoapprove_off, is_autoapprove_on,
    manual_on, manual_off, is_manual_on
)

PHOTO_URL = "https://files.catbox.moe/hziqgn.jpg"  # AnnieMusic logo

# -----------------------
# /autoapprove command
# -----------------------
@app.on_message(filters.command("autoapprove") & filters.group)
async def autoapprove_cmd(_, message: Message):
    chat_id = message.chat.id

    auto = await is_autoapprove_on(chat_id)
    manual = await is_manual_on(chat_id)

    if auto:
        status = "**Autoapproval for this chat: Enabled.**"
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("TURN OFF", callback_data="toggle_off"),
                InlineKeyboardButton("MANUAL", callback_data="toggle_manual"),
            ]
        ])
    elif manual:
        status = "**Manual approval for this chat: Enabled.**"
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("AUTO", callback_data="toggle_auto"),
                InlineKeyboardButton("TURN OFF", callback_data="toggle_off"),
            ]
        ])
    else:
        status = "**Autoapproval is currently disabled.**"
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("AUTO", callback_data="toggle_auto"),
                InlineKeyboardButton("MANUAL", callback_data="toggle_manual"),
            ]
        ])

    await message.reply_photo(
        photo=PHOTO_URL,
        caption=f"**{message.from_user.mention}**\n\n{status}",
        reply_markup=buttons
    )

# -----------------------
# Toggle Callback
# -----------------------
@app.on_callback_query(filters.regex("^(toggle_auto|toggle_manual|toggle_off)$"))
async def toggle_autoapprove(_, query: CallbackQuery):
    chat_id = query.message.chat.id
    user_id = query.from_user.id

    # ✅ Check admin or owner
    admins = [
        member.user.id
        async for member in app.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
    ]
    if user_id not in admins:
        return await query.answer("❌ Only admins or group owners can use this!", show_alert=True)

    # 🔁 Handle toggles
    if query.data == "toggle_auto":
        await autoapprove_on(chat_id)
        await query.answer("✅ AutoApproval Enabled", show_alert=True)
    elif query.data == "toggle_manual":
        await manual_on(chat_id)
        await query.answer("⚙️ Manual Mode Enabled", show_alert=True)
    elif query.data == "toggle_off":
        await autoapprove_off(chat_id)
        await manual_off(chat_id)
        await query.answer("❌ Both modes turned off", show_alert=True)

    # 🔄 Update status + buttons
    auto = await is_autoapprove_on(chat_id)
    manual = await is_manual_on(chat_id)

    if auto:
        text = "**Autoapproval for this chat: Enabled.**"
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("TURN OFF", callback_data="toggle_off"),
                InlineKeyboardButton("MANUAL", callback_data="toggle_manual"),
            ]
        ])
    elif manual:
        text = "**Manual approval for this chat: Enabled.**"
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("AUTO", callback_data="toggle_auto"),
                InlineKeyboardButton("TURN OFF", callback_data="toggle_off"),
            ]
        ])
    else:
        text = "**Autoapproval is currently disabled.**"
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("AUTO", callback_data="toggle_auto"),
                InlineKeyboardButton("MANUAL", callback_data="toggle_manual"),
            ]
        ])

    await query.message.edit_caption(
        caption=f"**{query.from_user.mention}**\n\n{text}",
        reply_markup=buttons
    )

# -----------------------
# Handle Join Requests
# -----------------------
@app.on_chat_join_request(filters.group)
async def join_request_handler(_, member):
    chat_id = member.chat.id
    user_id = member.from_user.id

    # 🔹 AutoApprove enabled → approve directly
    if await is_autoapprove_on(chat_id):
        await app.approve_chat_join_request(chat_id, user_id)
        await app.send_message(chat_id, f"✅ {member.from_user.mention} automatically approved!")

    # 🔹 Manual enabled → send Approve / Reject buttons
    elif await is_manual_on(chat_id):
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{user_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{user_id}")
            ]
        ])
        await app.send_message(chat_id, f"👤 Join request from {member.from_user.mention}", reply_markup=buttons)

# -----------------------
# Approve/Reject Callbacks
# -----------------------
@app.on_callback_query(filters.regex(r"^(approve|reject)_\d+$"))
async def approve_reject_handler(_, query: CallbackQuery):
    chat_id = query.message.chat.id
    data = query.data.split("_")
    action, user_id = data[0], int(data[1])

    admins = [
        member.user.id
        async for member in app.get_chat_members(chat_id, filter=enums.ChatMembersFilter.ADMINISTRATORS)
    ]
    if query.from_user.id not in admins:
        return await query.answer("❌ Only admins can approve/reject!", show_alert=True)

    if action == "approve":
        await app.approve_chat_join_request(chat_id, user_id)
        await query.message.edit_text("✅ User approved!")
    else:
        await app.decline_chat_join_request(chat_id, user_id)
        await query.message.edit_text("❌ User rejected!")