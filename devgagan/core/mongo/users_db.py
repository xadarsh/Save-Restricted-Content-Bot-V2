# ---------------------------------------------------
# File Name: users_db.py
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

from config import MONGO_DB
from motor.motor_asyncio import AsyncIOMotorClient as MongoCli


mongo = MongoCli(MONGO_DB)
db = mongo.users
db = db.users_db

#Collection for storing user sessions
user_sessions_real = db.user_sessions_real  # Added this collection

async def get_users():
  user_list = []
  async for user in db.users.find({"user": {"$gt": 0}}):
    user_list.append(user['user'])
  return user_list


async def get_user(user):
  users = await get_users()
  if user in users:
    return True
  else:
    return False

async def add_user(user):
  users = await get_users()
  if user in users:
    return
  else:
    await db.users.insert_one({"user": user})


async def del_user(user):
  users = await get_users()
  if not user in users:
    return
  else:
    await db.users.delete_one({"user": user})

# ------------------------- User Session Management -------------------------

async def get_session(user_id):
    """Fetch user session by ID."""
    return await user_sessions_real.find_one({"user_id": user_id})

async def add_session(user_id, session_data):
    """Add a new user session."""
    existing_session = await get_session(user_id)
    if not existing_session:
        await user_sessions_real.insert_one({"user_id": user_id, "session": session_data})

async def delete_session(user_id):
    """Delete a user session."""
    await user_sessions_real.delete_one({"user_id": user_id})
    


