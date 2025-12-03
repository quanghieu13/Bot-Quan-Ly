from keep_alive import keep_alive
import discord
from discord import app_commands
from discord.ext import commands
import os
import asyncio
import time
import datetime
import json

# ======================================================
# PHẦN 1: CẤU HÌNH
# ======================================================

# --- CÁC ID QUAN TRỌNG ---
ID_ADMIN = 1065648216911122506              # ID Admin
MUTE_LOG_CHANNEL_ID = 1444909829469634590   # ID Kênh Log (Cũ)
WELCOME_CHANNEL_ID = 1371768187342815293    # ID Kênh Chào Mừng
AUTO_ROLE_ID = 1445736048117157971          # ID Role Thành Viên
WARN_CHANNEL_ID = 1445761128222163006       # ID Kênh thông báo Warn (MỚI)

WARNING_FILE = "warnings.json"
TU_CAM_FILE = "tucam.txt"
WHITELIST_FILE = "id-user.txt"

# --- HÀM LOAD FILE AN TOÀN ---
def load_warnings():
    try:
        with open(WARNING_FILE, "r") as f:
            content = f.read().strip()
            if not content: return {}
            return json.loads(content)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_warnings(data):
    try:
        with open(WARNING_FILE, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Lỗi lưu file: {e}")

def load_list_from_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def load_allowed_users(filename=WHITELIST_FILE):
    allowed_ids = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().isdigit():
                    allowed_ids.append(int(line.strip()))
        return allowed_ids
    except FileNotFoundError:
        return []

TU_CAM = load_list_from_file(TU_CAM_FILE)
ALLOWED_USER_IDS = load_allowed_users()

# Setup Bot
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ======================================================
# PHẦN 2: BẮT LỖI & SỰ KIỆN
# ======================================================

@bot.tree.error
async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Bạn không có quyền dùng lệnh này!", ephemeral=True)
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message("❌ Bot thiếu quyền! Hãy kiểm tra Role của Bot.", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ Lỗi hệ thống: `{error}`", ephemeral=True)
        print(f"⚠️ LỖI SLASH COMMAND: {error}")

@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"✅ Đã đồng bộ {len(synced)} lệnh Slash.")
    except Exception as e:
        print(f"❌ Lỗi đồng bộ lệnh: {e}")
    
    await bot.change_presence(activity=discord.Activity(name="Dev Quang Hiếu", type=discord.ActivityType.watching))
    print(f'🤖 Bot online: {bot.user} | Admin: {ID_ADMIN}')

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(title="🎉 Chào mừng!", description=f"Xin chào {member.mention}!", color=discord.Color.green())
        embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
        await channel.send(embed=embed)
    
    role = member.guild.get_role(AUTO_ROLE_ID)
    if role:
        try: await member.add_roles(role)
        except: print(f"❌ Lỗi cấp role cho {member.name}")

@bot.event
async def on_member_remove(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel: await channel.send(f"😢 **{member.display_name}** đã rời server.")

# ======================================================
# PHẦN 3: CÁC LỆNH (COMMANDS)
# ======================================================

@bot.tree.command(name="ping", description="Xem độ trễ")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f'Pong! {round(bot.latency * 1000)}ms')

# --- KICK & BAN & CLEAR ---
@bot.tree.command(name="kick", description="Kick thành viên (Admin)")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "Không"):
    if interaction.user.id != ID_ADMIN: return await interaction.response.send_message("❌ Chỉ Admin được dùng!", ephemeral=True)
    try:
        await member.kick(reason=reason)
        await interaction.response.send_message(f"👞 Đã kick **{member.name}**.")
    except Exception as e: await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

@bot.tree.command(name="ban", description="Ban thành viên (Admin)")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "Không"):
    if interaction.user.id != ID_ADMIN: return await interaction.response.send_message("❌ Chỉ Admin được dùng!", ephemeral=True)
    try:
        await member.ban(reason=reason)
        await interaction.response.send_message(f"🔨 Đã ban **{member.name}**.")
    except Exception as e: await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

@bot.tree.command(name="clear", description="Xóa tin nhắn (Admin)")
async def clear(interaction: discord.Interaction, amount: int):
    if interaction.user.id != ID_ADMIN: return await interaction.response.send_message("❌ Chỉ Admin được dùng!", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Đã xóa {len(deleted)} tin.")

# --- HÀM XỬ LÝ WARN CHUNG (Dùng cho cả lệnh /warn và tự động warn) ---
async def process_warning(member: discord.Member, reason: str, moderator_name: str, guild):
    warnings = load_warnings()
    uid = str(member.id)
    if uid not in warnings: warnings[uid] = []
    
    warnings[uid].append({"reason": reason, "mod": moderator_name, "time": str(datetime.datetime.now())})
    save_warnings(warnings)
    
    # Tạo Embed thông báo
    embed = discord.Embed(title="⚠️ CẢNH CÁO VI PHẠM", color=discord.Color.orange())
    embed.add_field(name="Thành viên", value=member.mention, inline=False)
    embed.add_field(name="Lý do", value=reason, inline=False)
    embed.add_field(name="Số lần vi phạm", value=f"{len(warnings[uid])}/3", inline=True)
    
    # Gửi vào kênh WARN_CHANNEL_ID
    warn_channel = guild.get_channel(WARN_CHANNEL_ID)
    if warn_channel:
        await warn_channel.send(embed=embed)
    
    # Kiểm tra phạt Mute nếu đủ 3 lần
    if len(warnings[uid]) >= 3:
         try:
            await member.timeout(datetime.timedelta(hours=1))
            if warn_channel:
                await warn_channel.send(f"🚫 **{member.name}** đã bị Mute 1 tiếng do đủ 3 warning!")
         except Exception as e:
            if warn_channel:
                await warn_channel.send(f"⚠️ Đủ 3 warn nhưng không Mute được (Lỗi quyền hoặc Admin): {e}")
    
    return embed # Trả về embed để dùng cho slash command nếu cần

# --- LỆNH WARN (Gõ tay) ---
@bot.tree.command(name="warn", description="Cảnh cáo thành viên")
@app_commands.checks.has_permissions(manage_messages=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if member.bot or member.id == interaction.user.id:
        return await interaction.response.send_message("❌ Không thể warn người này!", ephemeral=True)

    # Gọi hàm xử lý chung
    embed = await process_warning(member, reason, interaction.user.name, interaction.guild)
    await interaction.response.send_message(f"✅ Đã cảnh cáo {member.mention}", ephemeral=True) # Chỉ báo nhẹ cho người dùng lệnh

@bot.tree.command(name="unwarn", description="Xóa cảnh cáo")
@app_commands.checks.has_permissions(manage_messages=True)
async def unwarn(interaction: discord.Interaction, member: discord.Member, index: int = None):
    warnings = load_warnings()
    uid = str(member.id)

    if uid not in warnings or not warnings[uid]:
        return await interaction.response.send_message(f"✅ **{member.name}** không có cảnh cáo nào.", ephemeral=True)

    try:
        if index is None:
            removed = warnings[uid].pop()
            msg = f"✅ Đã xóa warn mới nhất: `{removed['reason']}`"
        else:
            if index <= 0 or index > len(warnings[uid]):
                return await interaction.response.send_message("❌ Số thứ tự không đúng.", ephemeral=True)
            removed = warnings[uid].pop(index - 1)
            msg = f"✅ Đã xóa warn số {index}: `{removed['reason']}`"
        
        save_warnings(warnings)
        await interaction.response.send_message(msg)
    except Exception as e:
        await interaction.response.send_message(f"❌ Lỗi: {e}", ephemeral=True)

@bot.tree.command(name="checkwarn", description="Xem cảnh cáo")
async def checkwarn(interaction: discord.Interaction, member: discord.Member):
    warnings = load_warnings()
    uid = str(member.id)
    if uid not in warnings or not warnings[uid]:
        return await interaction.response.send_message(f"✅ **{member.name}** sạch sẽ.", ephemeral=True)

    embed = discord.Embed(title=f"Lịch sử Warn: {member.name}", color=discord.Color.red())
    for i, w in enumerate(warnings[uid], 1):
        embed.add_field(name=f"Warn {i}", value=f"Lý do: {w['reason']}\nMod: {w['mod']}", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="userinfo", description="Xem thông tin")
async def userinfo(interaction: discord.Interaction, member: discord.Member):
    embed = discord.Embed(color=member.color)
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    embed.add_field(name="Tên", value=member.name)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Ngày tạo", value=member.created_at.strftime("%d/%m/%Y"))
    embed.add_field(name="Ngày vào", value=member.joined_at.strftime("%d/%m/%Y"))
    await interaction.response.send_message(embed=embed)

# ======================================================
# PHẦN 4: XỬ LÝ TIN NHẮN (AUTO WARN TỪ CẤM)
# ======================================================
@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    # Check Admin/Whitelist
    is_exempt = (message.author.bot) or (message.author.id == ID_ADMIN) or (message.author.id in ALLOWED_USER_IDS)

    # --- KIỂM TRA TỪ CẤM ---
    if not is_exempt:
        content = message.content.lower()
        # Tìm xem có từ cấm nào trong tin nhắn không
        bad_words = [w for w in TU_CAM if w in content]
        
        if bad_words:
            try:
                # 1. Xóa tin nhắn vi phạm
                await message.delete()
                
                # 2. Tự động WARN thay vì Mute
                reason_msg = "m đã dùng từ cấm"
                await process_warning(message.author, reason_msg, "Hệ thống (Auto)", message.guild)
                
                # 3. Gửi tin nhắn nhắc nhở nhẹ tại kênh chat (Tự xóa sau 5s)
                temp = await message.channel.send(f"🚫 {message.author.mention} đã bị cảnh cáo vì dùng từ cấm!")
                await asyncio.sleep(5)
                await temp.delete()
                
            except Exception as e:
                print(f"Lỗi xử lý từ cấm: {e}")
            return

    # Tag all
    if message.mention_everyone and message.author.id != ID_ADMIN:
        try:
            await message.delete()
            temp = await message.channel.send(f"🚫 {message.author.mention} đừng tag all!")
            await asyncio.sleep(5)
            await temp.delete()
        except: pass

    await bot.process_commands(message)

# Run
keep_alive()
if __name__ == "__main__":
    TOKEN = os.environ.get('DISCORD_TOKEN')
    if not TOKEN: print("❌ Thiếu Token!")
    else: bot.run(TOKEN)
