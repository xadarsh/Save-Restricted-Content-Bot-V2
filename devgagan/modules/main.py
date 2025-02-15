# ---------------------------------------------------
# File Name: main.py
# Description: A Pyrogram bot for downloading files from Telegram channels or groups 
#              and uploading them back to Telegram.
# Author: Gagan
# GitHub: https://github.com/devgaganin/
# Telegram: https://t.me/team_spy_pro
# YouTube: https://youtube.com/@dev_gagan
# Created: 2025-01-11
# Last Modified: 2025-01-11
# Version: 2.0.5
# License: MIT License
# More readable 
# ---------------------------------------------------

import time
import random
import string
import asyncio
from pyrogram import filters, Client
from devgagan import app
from config import API_ID, API_HASH, FREEMIUM_LIMIT, PREMIUM_LIMIT, OWNER_ID
from devgagan.core.get_func import get_msg
from devgagan.core.func import *
from devgagan.core.mongo import db
from pyrogram.errors import FloodWait
from datetime import datetime, timedelta
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from devgagan.core.mongo.db import user_sessions_real
import subprocess
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
'''
from devgagan.modules.connect_user import (
    connect_user, 
    disconnect_user, 
    owner_message_handler, 
    user_reply_handler, 
    send_message_callback, 
    cancel_message_callback,
    active_connections
)
'''
#import devgagan.modules.connectUser  # Correct import path
#from devgagan.modules.connectUser import register_handlers  # Import register function
from devgagan.modules.shrink import is_user_verified
async def generate_random_name(length=8):
    return ''.join(random.choices(string.ascii_lowercase, k=length))

users_loop = {}
interval_set = {}
batch_mode = {}
#register_handlers(app)
'''
# Create a separate instance for connectUser.py handlers
connect_app = Client("connect_user_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Register handlers with the new instance
register_handlers(connect_app)

# Start the new instance separately
connect_app.run()

'''
async def process_and_upload_link(userbot, user_id, msg_id, link, retry_count, message):
    try:
        await get_msg(userbot, user_id, msg_id, link, retry_count, message)
        await asyncio.sleep(15)
    finally:
        pass

# Function to check if the user can proceed
async def check_interval(user_id, freecheck):
    if freecheck != 1 or await is_user_verified(user_id):  # Premium or owner users can always proceed
        return True, None

    now = datetime.now()

    # Check if the user is on cooldown
    if user_id in interval_set:
        cooldown_end = interval_set[user_id]
        if now < cooldown_end:
            remaining_time = (cooldown_end - now).seconds
            return False, f"Please wait {remaining_time} seconds(s) before sending another link. Alternatively, purchase premium for instant access.\n\n>"
        else:
            del interval_set[user_id]  # Cooldown expired, remove user from interval set

    return True, None

async def set_interval(user_id, interval_minutes=45):
    now = datetime.now()
    # Set the cooldown interval for the user
    interval_set[user_id] = now + timedelta(seconds=interval_minutes)
    

@app.on_message(
    filters.regex(r'https?://(?:www\.)?t\.me/[^\s]+|tg://openmessage\?user_id=\w+&message_id=\d+')
    & filters.private
)
async def single_link(_, message):
    user_id = message.chat.id

    # Check subscription and batch mode
    if await subscribe(_, message) == 1 or user_id in batch_mode:
        return

    # Check if user is already in a loop
    if users_loop.get(user_id, False):
        await message.reply(
            "You already have an ongoing process. Please wait for it to finish or cancel it with /cancel."
        )
        return

    # Check freemium limits
    if await chk_user(message, user_id) == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        await message.reply("Freemium service is currently not available. Upgrade to premium for access.")
        return

    # Check cooldown
    can_proceed, response_message = await check_interval(user_id, await chk_user(message, user_id))
    if not can_proceed:
        await message.reply(response_message)
        return

    # Add user to the loop
    users_loop[user_id] = True

    link = message.text if "tg://openmessage" in message.text else get_link(message.text)
    msg = await message.reply("Processing...")
    userbot = await initialize_userbot(user_id)

    try:
        if await is_normal_tg_link(link):
            # Pass userbot if available; handle normal Telegram links
            await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
            await set_interval(user_id, interval_minutes=45)
        else:
            # Handle special Telegram links
            await process_special_links(userbot, user_id, msg, link)
            
    except FloodWait as fw:
        await msg.edit_text(f'Try again after {fw.x} seconds due to floodwait from Telegram.')
    except Exception as e:
        await msg.edit_text(f"Link: `{link}`\n\n**Error:** {str(e)}")
    finally:
        users_loop[user_id] = False
        if userbot:
            await userbot.stop()
        try:
            await msg.delete()
        except Exception:
            pass


from pyrogram import Client, filters

async def initialize_userbot(user_id): # this ensure the single startup .. even if logged in or not
    """Initialize the userbot session for the given user."""
    data = await db.get_data(user_id)
    if data and data.get("session"):
        try:
            device = 'iPhone 16 Pro' # added gareebi text
            userbot = Client(
                "userbot",
                api_id=API_ID,
                api_hash=API_HASH,
                device_model=device,
                session_string=data.get("session")
            )
            await userbot.start()
            return userbot
        except Exception:
            return None
    return None


async def is_normal_tg_link(link: str) -> bool:
    """Check if the link is a standard Telegram link."""
    special_identifiers = ['t.me/+', 't.me/c/', 't.me/b/', 'tg://openmessage']
    return 't.me/' in link and not any(x in link for x in special_identifiers)
    
async def process_special_links(userbot, user_id, msg, link):
    """Handle special Telegram links."""
    if 't.me/+' in link:
        result = await userbot_join(userbot, link)
        await msg.edit_text(result)
    elif any(sub in link for sub in ['t.me/c/', 't.me/b/', '/s/', 'tg://openmessage']):
        await process_and_upload_link(userbot, user_id, msg.id, link, 0, msg)
        await set_interval(user_id, interval_minutes=45)
    else:
        await msg.edit_text("Invalid link format.")


@app.on_message(filters.command("batch") & filters.private)
async def batch_link(_, message):
    join = await subscribe(_, message)
    if join == 1:
        return
    user_id = message.chat.id
    # Check if a batch process is already running
    if users_loop.get(user_id, False):
        await app.send_message(
            message.chat.id,
            "You already have a batch process running. Please wait for it to complete."
        )
        return

    freecheck = await chk_user(message, user_id)
    if freecheck == 1 and FREEMIUM_LIMIT == 0 and user_id not in OWNER_ID and not await is_user_verified(user_id):
        await message.reply("Freemium service is currently not available. Upgrade to premium for access.")
        return

    max_batch_size = FREEMIUM_LIMIT if freecheck == 1 else PREMIUM_LIMIT

    # Start link input
    for attempt in range(3):
        start = await app.ask(message.chat.id, "Please send the start link.\n\n> Maximum tries 3")
        start_id = start.text.strip()
        s = start_id.split("/")[-1]
        if s.isdigit():
            cs = int(s)
            break
        await app.send_message(message.chat.id, "Invalid link. Please send again ...")
    else:
        await app.send_message(message.chat.id, "Maximum attempts exceeded. Try later.")
        return

    # Number of messages input
    for attempt in range(3):
        num_messages = await app.ask(message.chat.id, f"How many messages do you want to process?\n> Max limit {max_batch_size}")
        try:
            cl = int(num_messages.text.strip())
            if 1 <= cl <= max_batch_size:
                break
            raise ValueError()
        except ValueError:
            await app.send_message(
                message.chat.id, 
                f"Invalid number. Please enter a number between 1 and {max_batch_size}."
            )
    else:
        await app.send_message(message.chat.id, "Maximum attempts exceeded. Try later.")
        return

    # Validate and interval check
    can_proceed, response_message = await check_interval(user_id, freecheck)
    if not can_proceed:
        await message.reply(response_message)
        return
        
    join_button = InlineKeyboardButton("Join Channel", url="https://t.me/+9FZJh0WMZnE4YWRk")
    keyboard = InlineKeyboardMarkup([[join_button]])
    pin_msg = await app.send_message(
        user_id,
        f"Batch process started ⚡\nProcessing: 0/{cl}\n\n****",
        reply_markup=keyboard
    )
    await pin_msg.pin(both_sides=True)

    users_loop[user_id] = True
    try:
        normal_links_handled = False
        userbot = await initialize_userbot(user_id)
        # Handle normal links first
        for i in range(cs, cs + cl):
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                # Process t.me links (normal) without userbot
                if 't.me/' in link and not any(x in link for x in ['t.me/b/', 't.me/c/', 'tg://openmessage']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    await pin_msg.edit_text(
                        f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}\n\n****",
                        reply_markup=keyboard
                    )
                    normal_links_handled = True
        if normal_links_handled:
            await set_interval(user_id, interval_minutes=300)
            await pin_msg.edit_text(
                f"Batch completed successfully for {cl} messages 🎉\n\n****",
                reply_markup=keyboard
            )
            await app.send_message(message.chat.id, "Batch completed successfully! 🎉")
            return
            
        # Handle special links with userbot
        for i in range(cs, cs + cl):
            if not userbot:
                await app.send_message(message.chat.id, "Login in bot first ...")
                users_loop[user_id] = False
                return
            if user_id in users_loop and users_loop[user_id]:
                url = f"{'/'.join(start_id.split('/')[:-1])}/{i}"
                link = get_link(url)
                if any(x in link for x in ['t.me/b/', 't.me/c/']):
                    msg = await app.send_message(message.chat.id, f"Processing...")
                    await process_and_upload_link(userbot, user_id, msg.id, link, 0, message)
                    await pin_msg.edit_text(
                        f"Batch process started ⚡\nProcessing: {i - cs + 1}/{cl}\n\n****",
                        reply_markup=keyboard
                    )

        await set_interval(user_id, interval_minutes=300)
        await pin_msg.edit_text(
            f"Batch completed successfully for {cl} messages 🎉\n\n****",
            reply_markup=keyboard
        )
        await app.send_message(message.chat.id, "Batch completed successfully! 🎉")

    except Exception as e:
        await app.send_message(message.chat.id, f"Error: {e}")
    finally:
        users_loop.pop(user_id, None)

@app.on_message(filters.command("cancel"))
async def stop_batch(_, message):
    user_id = message.chat.id

    # Check if there is an active batch process for the user
    if user_id in users_loop and users_loop[user_id]:
        users_loop[user_id] = False  # Set the loop status to False
        await app.send_message(
            message.chat.id, 
            "Batch processing has been stopped successfully. You can start a new batch now if you want."
        )
    elif user_id in users_loop and not users_loop[user_id]:
        await app.send_message(
            message.chat.id, 
            "The batch process was already stopped. No active batch to cancel."
        )
    else:
        await app.send_message(
            message.chat.id, 
            "No active batch processing is running to cancel."
        )
























#OWNER_ID = 1970647198
active_connections = {}  
pending_messages = {}  # ✅ Store messages per admin

# ✅ Function to handle /connect_user command (Admin only)
@app.on_message(filters.command("connect_user") & filters.user(OWNER_ID))
async def connect_user(app, message):
    admin_id = message.chat.id
    # ✅ Check if the owner is already connected to a user
    if admin_id in active_connections:
        current_user_id = active_connections[admin_id]
        current_user = await user_sessions_real.find_one({"user_id": current_user_id})
        current_user_name = current_user.get("username", "Unknown User") 
        await message.reply(f"❌ You are already connected with {current_user_name}.To connect with another user, disconnect the current user using /disconnect_user .")
        return  # ✅ Stop execution here if already connected
    
    
    await message.reply("Enter the User ID or Username to connect:")
    try:
        # ✅ Wait for admin response (Handle Timeout)
        user_id_msg = await app.listen(admin_id, timeout=60)
        user_input = user_id_msg.text.strip()
    except asyncio.TimeoutError:  # ✅ Catch timeout error properly
        await message.reply("❌ Timeout! You took too long to respond. Please enter the command again.")
        return

    # ✅ Remove '@' if present in username
    if user_input.startswith("@"): 
        user_input = user_input[1:]

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
    await app.send_message(user_id, "⚡ Owner connected with you.")

# ✅ Function to handle /disconnect_user command (Admin only)
@app.on_message(filters.command("disconnect_user") & filters.user(OWNER_ID))
async def disconnect_user(app, message):
    admin_id = message.chat.id
    user_id = active_connections.get(admin_id)  # ✅ Get user ID safely

    if user_id:
        active_connections.pop(admin_id, None)  # ✅ Remove safely
        active_connections.pop(user_id, None)

        await message.reply("🛑 Connection Destroyed!")
        await app.send_message(user_id, "🛑 Connection Destroyed!")
    else:
        await message.reply("❌ No active connection found.")

# ✅ Function to confirm message before sending
@app.on_message(filters.private & filters.user(OWNER_ID)
async def owner_message_handler(app, message):
    admin_id = message.chat.id
    if admin_id not in active_connections:
        return  

    user_id = active_connections[admin_id]  
    msg_text = message.text or "📎 Media Message"

    # ✅ Store message per admin (Fix ID conflict issue)
    if admin_id not in pending_messages:
        pending_messages[admin_id] = {}
    pending_messages[admin_id][message.id] = msg_text  

    # Send confirmation with inline buttons
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Send", callback_data=f"send|{message.id}|{admin_id}")],
        [InlineKeyboardButton("❌ Cancel", callback_data=f"cancel|{message.id}|{admin_id}")]
    ])
    
    await message.reply("Do you want to send this message?", reply_markup=keyboard)

# ✅ Callback handler for sending message
@app.on_callback_query(filters.regex("^send\\|"))
async def send_message_callback(app, query):
    _, msg_id, user_id = query.data.split("|")
    user_id = int(user_id)
    msg_id = int(msg_id)
    admin_id = query.from_user.id  

    # ✅ Retrieve message correctly from nested dictionary
    msg_text = pending_messages.get(admin_id, {}).pop(msg_id, None) or "⚠️ Message not found!"

    if msg_text != "⚠️ Message not found!":
        await app.send_message(user_id, f"👤 Owner: {msg_text}")  

    # ✅ Cleanup: Remove admin entry if no pending messages left
    if admin_id in pending_messages and not pending_messages[admin_id]:
        del pending_messages[admin_id]
    # ✅ Delete the original confirmation message
    await query.message.delete()
    await app.send_message(admin_id, "✅ Message sent successfully!")

# ✅ Callback handler for cancelling message
@app.on_callback_query(filters.regex("^cancel\\|"))
async def cancel_message_callback(app, query):
    _, admin_id, msg_id = query.data.split("|")
    admin_id = int(admin_id)
    msg_id = int(msg_id)

    # ✅ Remove message correctly
    if admin_id in pending_messages:
        pending_messages[admin_id].pop(msg_id, None)
        
        # ✅ Cleanup if admin has no more pending messages
        if not pending_messages[admin_id]:
            del pending_messages[admin_id]
    # ✅ Delete the original confirmation message
    await query.message.delete()
    await app.send_message(admin_id, "❌ Message sending cancelled.")

# ✅ User message handler (sends reply back to owner)
@app.on_message(filters.private & ~filters.user(OWNER_ID))
async def user_reply_handler(app, message):
    user_id = message.chat.id

    if user_id in active_connections:
        admin_id = active_connections[user_id]  
        msg_text = message.text or "📎 Media Message"

        await app.send_message(admin_id, f"💬 {message.from_user.first_name} : {msg_text}")

# ✅ Register all handlers
def register_handlers(app):
    app.add_handler(MessageHandler(connect_user, filters.command("connect_user") & filters.user(OWNER_ID)))
    app.add_handler(MessageHandler(disconnect_user, filters.command("disconnect_user") & filters.user(OWNER_ID)))
    app.add_handler(MessageHandler(owner_message_handler, filters.private & filters.user(OWNER_ID)))
    app.add_handler(MessageHandler(user_reply_handler, filters.private & ~filters.user(OWNER_ID)))
    app.add_handler(CallbackQueryHandler(send_message_callback, filters.regex("^send\\|")))
    app.add_handler(CallbackQueryHandler(cancel_message_callback, filters.regex("^cancel\\|")))

register_handlers(app)  # ✅ Call the function to register handlers

