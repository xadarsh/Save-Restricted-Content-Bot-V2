# ---------------------------------------------------
# File Name: speedtest.py
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

from time import time
from speedtest import Speedtest
from telethon import events
from telethon.tl.custom import Button
from devgagan import sex as gagan
from devgagan import botStartTime  

SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']

def get_readable_time(seconds: int) -> str:
    result = ''
    (days, remainder) = divmod(seconds, 86400)
    days = int(days)
    if days != 0:
        result += f'{days}d '
    (hours, remainder) = divmod(remainder, 3600)
    hours = int(hours)
    if hours != 0:
        result += f'{hours}h '
    (minutes, seconds) = divmod(remainder, 60)
    minutes = int(minutes)
    if minutes != 0:
        result += f'{minutes}m '
    seconds = int(seconds)
    result += f'{seconds}s'
    return result

def get_readable_file_size(size_in_bytes) -> str:
    if size_in_bytes is None:
        return '0B'
    index = 0
    while size_in_bytes >= 1024:
        size_in_bytes /= 1024
        index += 1
    try:
        return f'{round(size_in_bytes, 2)}{SIZE_UNITS[index]}'
    except IndexError:
        return 'File too large'

def speed_convert(size, byte=True):
    if not byte:
        size = size / 8
    power = 2 ** 10
    zero = 0
    units = {0: "B/s", 1: "KB/s", 2: "MB/s", 3: "GB/s", 4: "TB/s"}
    while size > power:
        size /= power
        zero += 1
    return f"{round(size, 2)} {units[zero]}"

# ✅ Define Buttons Globally (Keeping "Report Issue")
buttons = [[Button.url("🐛 Report Bug", "https://t.me/Contact_xbot")]]

@gagan.on(events.NewMessage(incoming=True, pattern='/speedtest'))
async def speedtest(event):
    speed = await event.reply("🚀 Running Speed Test... Please wait.")

    test = Speedtest()
    test.get_best_server()
    test.download()
    test.upload()
    test.results.share()
    
    result = test.results.dict()
    path = (result['share'])  # Get the speed test image URL
    current_time = get_readable_time(time() - botStartTime)

    string_speed = f'''
╭──《 🚀 <b>SPEEDTEST RESULTS</b> 》
├ <b>📡 Upload:</b> {speed_convert(result['upload'], False)}
├ <b>📥 Download:</b>  {speed_convert(result['download'], False)}
├ <b>📍 Ping:</b> {result['ping']} ms
├ <b>⏳ Time:</b> {result['timestamp']}
├ <b>📊 Data Sent:</b> {get_readable_file_size(int(result['bytes_sent']))}
╰ <b>📩 Data Received:</b> {get_readable_file_size(int(result['bytes_received']))}

╭──《 🌍 <b>SPEEDTEST SERVER</b> 》
├ <b>🏛 Name:</b> {result['server']['name']}
├ <b>🌍 Country:</b> {result['server']['country']}, {result['server']['cc']}
├ <b>🔰 Sponsor:</b> {result['server']['sponsor']}
├ <b>📡 Latency:</b> {result['server']['latency']}
├ <b>📍 Latitude:</b> {result['server']['lat']}
╰ <b>📍 Longitude:</b> {result['server']['lon']}

╭──《 👤 <b>CLIENT DETAILS</b> 》
├ <b>🔎 IP Address:</b> {result['client']['ip']}
├ <b>📍 Latitude:</b> {result['client']['lat']}
├ <b>📍 Longitude:</b> {result['client']['lon']}
├ <b>🌏 Country:</b> {result['client']['country']}
├ <b>💼 ISP:</b> {result['client']['isp']}
╰ <b>⭐ ISP Rating:</b> {result['client']['isprating']}
'''

    try:
        # ✅ Send the Speed Test Image as a New Message with Caption
        await event.reply(string_speed,file=path, buttons=buttons, parse_mode='html')
        await speed.delete()
    except Exception as e:
        await speed.delete()
        await event.reply(string_speed, buttons=buttons, parse_mode='html')
       # await event.reply("⚠️ Failed to send speed test image.", parse_mode='html')
        
