from keep_alive import keep_alive
import discord
from discord.ext import commands
import os
import asyncio
import time

# ======================================================
# PHẦN 1: CẤU HÌNH VÀ CODE BOT DISCORD
# ======================================================

# BẮT BUỘC: Thay thế bằng ID Discord của bạn (Admin chính)
ID_ADMIN = 1065648216911122506

# --- HÀM 1: Đọc danh sách từ cấm ---
def load_tu_cam(filename="tucam.txt"):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"⚠️ Lỗi: Không tìm thấy file {filename}.")
        return []

# --- HÀM 2: Đọc danh sách người dùng được phép (Whitelist) ---
def load_allowed_users(filename="id-user.txt"):
    allowed_ids = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Chỉ lấy những dòng là số (ID Discord là số)
                if line.isdigit():
                    allowed_ids.append(int(line))
        return allowed_ids
    except FileNotFoundError:
        print(f"⚠️ Lỗi: Không tìm thấy file {filename}. Không ai được miễn trừ.")
        return []

# Tải dữ liệu khi khởi động
TU_CAM = load_tu_cam()
ALLOWED_USER_IDS = load_allowed_users()

# Thiết lập Intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print('----------------------------------')
    print(f'🤖 Bot đã đăng nhập: {bot.user}')
    print(f'🛡️ Admin ID: {ID_ADMIN}')
    print(f'🚫 Số lượng từ cấm: {len(TU_CAM)}')
    print(f'✅ Số người dùng được miễn trừ: {len(ALLOWED_USER_IDS)}')
    print('----------------------------------')

@bot.command()
async def ping(ctx):
    await ctx.send(f'Pong! Độ trễ: {round(bot.latency * 1000)}ms')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Kiểm tra xem người dùng có nằm trong danh sách được phép không
    # Nếu là Admin hoặc có
