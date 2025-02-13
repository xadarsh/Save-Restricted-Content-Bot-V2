from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import OWNER_ID  # ✅ Import OWNER_ID from config.py

# Dictionary to track active connections
active_connections = {}

# ✅ Function to handle /connect_user command (Admin only)
@Client.on_message(filters.command("connect_user") & filters.user(OWNER_ID))
async def connect_user(client, message):
    admin_id = message.chat.id
    await message.reply("Enter the User ID or Username to connect:")

    # Wait for admin response
    user_id_msg = await client.listen(admin_id, timeout=60)
    user_input = user_id_msg.text.strip()

    # Search in database (Replace this with actual DB query)
    user_session = await client.db.user_sessions_real.find_one(
        {"$or": [{"user_id": int(user_input) if user_input.isdigit() else None}, {"username": user_input}]}
    )

    if not user_session:
        await message.reply("❌ User not found in the database.")
        return

    user_id = user_session["user_id"]
    user_name = user_session.get("username", "Unknown User")

    # Store the active connection
    active_connections[admin_id] = user_id

    # Notify both parties
    await message.reply(f"✅ Connected to {user_name} successfully.")
    await client.send_message(user_id, "⚡ Owner connected with you.")

# ✅ Function to handle /disconnect_user command (Admin only)
@Client.on_message(filters.command("disconnect_user") & filters.user(OWNER_ID))
async def disconnect_user(client, message):
    admin_id = message.chat.id

    if admin_id in active_connections:
        user_id = active_connections.pop(admin_id)  # Remove from active connections
        await message.reply("🛑 Connection Destroyed!")
        await client.send_message(user_id, "🛑 Connection Destroyed!")
    else:
        await message.reply("❌ No active connection found.")

# ✅ Function to confirm message before sending
@Client.on_message(filters.user(OWNER_ID) & filters.text)
async def owner_message_handler(client, message):
    admin_id = message.chat.id

    if admin_id not in active_connections:
        return  # No active connection, ignore message

    user_id = active_connections[admin_id]
    msg_text = message.text

    # Send confirmation with inline buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Send", callback_data=f"send|{user_id}|{msg_text}")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ])
    
    await message.reply("Do you want to send this message?", reply_markup=keyboard)

# ✅ Callback handler for sending message
@Client.on_callback_query(filters.regex("^send\\|"))
async def send_message_callback(client, query):
    _, user_id, msg_text = query.data.split("|")
    user_id = int(user_id)

    # Send the message to the user
    await client.send_message(user_id, f"👤 Owner: {msg_text}")

    # Confirm sent message to admin
    await query.message.edit_text("✅ Message sent successfully!")

# ✅ Callback handler for cancelling message
@Client.on_callback_query(filters.regex("^cancel"))
async def cancel_message_callback(client, query):
    await query.message.edit_text("❌ Message sending cancelled.")

# ✅ User message handler (sends reply back to owner)
@Client.on_message(filters.private & ~filters.user(OWNER_ID))
async def user_reply_handler(client, message):
    user_id = message.chat.id

    # Check if user is connected to the owner
    if user_id in active_connections.values():
        admin_id = next((key for key, val in active_connections.items() if val == user_id), None)
        if admin_id:
            await client.send_message(admin_id, f"💬 {message.from_user.first_name} says -> {message.text}")

# ✅ Function to register all handlers
def register_handlers(app):
    app.add_handler(connect_user)
    app.add_handler(disconnect_user)
    app.add_handler(owner_message_handler)
    app.add_handler(send_message_callback)
    app.add_handler(cancel_message_callback)
    app.add_handler(user_reply_handler)
