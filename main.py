from keep_alive import keep_alive
import discord
from discord.ext import commands
import os
import asyncio
import time
import datetime # Cần cho chức năng Timeout (Mute)

# ======================================================
# PHẦN 1: TẢI CẤU HÌNH VÀ DỮ LIỆU
# ======================================================

# BẮT BUỘC: Thay thế bằng ID Discord của bạn (Admin)
ID_ADMIN = 1065648216911122506


# Hàm 1: Đọc danh sách từ cấm
def load_tu_cam(filename="tucam.txt"):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"⚠️ Lỗi: Không tìm thấy file {filename}.")
        return []

# Hàm 2: Đọc danh sách người dùng được phép (Whitelist)
def load_allowed_users(filename="id-user.txt"):
    allowed_ids = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
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
intents.members = True # Cần cho chức năng Timeout
intents.presences = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ======================================================
# PHẦN 2: SỰ KIỆN BOT VÀ CHỨC NĂNG KIỂM DUYỆT
# ======================================================

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
    # Luôn bỏ qua tin nhắn của chính bot này
    if message.author == bot.user:
        return

    # --- ĐỊNH NGHĨA NGOẠI LỆ (Exemptions) ---
    is_exempt = (message.author.bot) or \
                (message.author.id == ID_ADMIN) or \
                (message.author.id in ALLOWED_USER_IDS)

    # --- CHỨC NĂNG 1: TỪ CẤM & MUTE 5 PHÚT ---
    # Chỉ kiểm tra nếu KHÔNG được miễn trừ
    if not is_exempt:
        noi_dung = message.content.lower()
        vi_pham = False
        
        for tu in TU_CAM:
            if tu in noi_dung:
                vi_pham = True
                break
        
        if vi_pham:
            try:
                # 1. Tự động xóa tin nhắn
                await message.delete()

                # 2. Áp dụng Timeout (Mute) 5 phút
                duration = datetime.timedelta(minutes=5)
                await message.author.timeout(duration) 
                
                # 3. Gửi cảnh báo công khai
                warn_msg = await message.channel.send(
                    f"🚫 {message.author.mention}, tin nhắn đã bị xóa và **tạm thời bị cấm chat 5 phút** vì vi phạm từ cấm!")
                
                # 4. Tự xóa cảnh báo sau 5s
                await asyncio.sleep(5)
                await warn_msg.delete()

                # 5. Báo cáo cho Admin
                admin = await bot.fetch_user(ID_ADMIN)
                await admin.send(f"⚠️ **ĐÃ MUTE 5P**: {message.author} đã vi phạm từ cấm. Nội dung: `{message.content}`")
                
            except discord.errors.Forbidden:
                await message.channel.send(f"❌ Bot thiếu quyền **Kiểm duyệt thành viên** để MUTE {message.author.mention}!")
                
            except Exception as e:
                # Xử lý lỗi Rate Limit và lỗi chung
                if isinstance(e, discord.errors.HTTPException) and e.status == 429:
                    print("⚠️ Bị Rate Limit. Đang nghỉ 3 giây...")
                    await asyncio.sleep(3)
                else:
                    print(f"Lỗi xử lý từ cấm (Mute): {e}")
                
            return 

    # --- CHỨC NĂNG 2: CHẶN TAG @EVERYONE ---
    if message.mention_everyone and message.author.id != ID_ADMIN:
        try:
            await message.delete()
            msg = await message.channel.send(f"🚫 {message.author.mention} không được tag all!")
            await asyncio.sleep(5)
            await msg.delete()
        except Exception:
            pass

    await bot.process_commands(message)

# ======================================================
# PHẦN 3: KHỞI ĐỘNG HỆ THỐNG (AUTO-RESTART)
# ======================================================

# 1. Kích hoạt Web Server Keep Alive
keep_alive()

# 2. Vòng lặp bất tử để chạy Bot
if __name__ == "__main__":
    TOKEN = os.environ.get('DISCORD_TOKEN')

    if not TOKEN:
        print("❌ LỖI: Bạn chưa thêm DISCORD_TOKEN vào Environment Variables!")
    else:
        while True:
            try:
                bot.run(TOKEN)
            except Exception as e:
                print(f"\n⚠️ Bot bị crash: {e}. Đang tự động khởi động lại sau 10 giây...")
                time.sleep(10)
