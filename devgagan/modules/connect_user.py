from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID  
from devgagan.core.mongo.db import user_sessions_real  

OWNER_ID = 1970647198
active_connections = {}  
pending_messages = {}  

# ✅ Function to handle /connect_user command (Admin only)
@Client.on_message(filters.command("connect_user") & filters.user(OWNER_ID))
async def connect_user(client, message):
    admin_id = message.chat.id
    await message.reply("Enter the User ID or Username to connect:")

    # Wait for admin response
    user_id_msg = await client.wait_for_message(chat_id=admin_id, timeout=60)
    user_input = user_id_msg.text.strip()

    # ✅ Remove '@' if present in username
    if user_input.startswith("@"):
        user_input = user_input[1:]  # Remove '@' symbol

    # ✅ Create a correct database query
    query = {"username": user_input} if not user_input.isdigit() else {"user_id": int(user_input)}

    user_session = await user_sessions_real.find_one(query)

    if not user_session:
        await message.reply("❌ User not found in the database.")
        return

    user_id = user_session["user_id"]
    user_name = user_session.get("username", "Unknown User")

    # Store the active connection both ways
    active_connections[admin_id] = user_id
    active_connections[user_id] = admin_id  

    # Notify both parties
    await message.reply(f"✅ Connected to {user_name} successfully.")
    await client.send_message(user_id, "⚡ Owner connected with you.")

# ✅ Function to handle /disconnect_user command (Admin only)
@Client.on_message(filters.command("disconnect_user") & filters.user(OWNER_ID))
async def disconnect_user(client, message):
    admin_id = message.chat.id

    if admin_id in active_connections:
        user_id = active_connections.pop(admin_id)  
        active_connections.pop(user_id, None)  

        await message.reply("🛑 Connection Destroyed!")
        await client.send_message(user_id, "🛑 Connection Destroyed!")
    else:
        await message.reply("❌ No active connection found.")

# ✅ Function to confirm message before sending
@Client.on_message(filters.private & filters.user(OWNER_ID))
async def owner_message_handler(client, message):
    admin_id = message.chat.id

    if admin_id not in active_connections:
        return  

    user_id = active_connections[admin_id]  
    msg_text = message.text or "📎 Media Message"

    # Store the message temporarily
    pending_messages[message.id] = msg_text

    # Send confirmation with inline buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Send", callback_data=f"send|{message.id}|{user_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{message.id}")]
    ])
    
    await message.reply("Do you want to send this message?", reply_markup=keyboard)

# ✅ Callback handler for sending message
@Client.on_callback_query(filters.regex("^send\\|"))
async def send_message_callback(client, query):
    _, msg_id, user_id = query.data.split("|")
    user_id = int(user_id)
    msg_id = int(msg_id)

    msg_text = pending_messages.pop(msg_id, "⚠️ Message not found!")

    if msg_text != "⚠️ Message not found!":
        await client.send_message(user_id, f"👤 Owner: {msg_text}")  

    await query.message.edit_text("✅ Message sent successfully!")

# ✅ Callback handler for cancelling message
@Client.on_callback_query(filters.regex("^cancel\\|"))
async def cancel_message_callback(client, query):
    _, msg_id = query.data.split("|")
    msg_id = int(msg_id)

    pending_messages.pop(msg_id, None)
    await query.message.edit_text("❌ Message sending cancelled.")

# ✅ User message handler (sends reply back to owner)
@Client.on_message(filters.private & ~filters.user(OWNER_ID))
async def user_reply_handler(client, message):
    user_id = message.chat.id

    if user_id in active_connections:
        admin_id = active_connections[user_id]  
        msg_text = message.text or "📎 Media Message"

        await client.send_message(admin_id, f"💬 {message.from_user.first_name} says -> {msg_text}")  

# ✅ Register all handlers
def register_handlers(app):
    app.add_handler(connect_user)
    app.add_handler(disconnect_user)
    app.add_handler(owner_message_handler)
    app.add_handler(send_message_callback)
    app.add_handler(cancel_message_callback)
    app.add_handler(user_reply_handler)
    
