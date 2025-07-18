# main.py

import discord
from discord.ext import commands
from discord import app_commands, Interaction
from discord.ui import View, Button
from dotenv import load_dotenv
import os
import json
import datetime

load_dotenv()
TOKEN = os.getenv("MTM5MzkxMjc0NzY4NjYyOTQ2Ng.G1t4qJ.3VY_rns4vMhjfeQAlW8Gspu1FTEHI-7tUhTIsk")

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# 파일 경로
DATA_FILE = "data.json"
ROLE_FILE = "role.json"
SHOP_FILE = "shop.json"
CHAT_LOG_FILE = "chat_log.json"
LOG_CHANNEL_FILE = "log_channel.json"
WARNING_FILE = "warnings.json"

# 파일 로딩 함수
def load_json(file):
    if not os.path.exists(file):
        with open(file, 'w') as f:
            json.dump({}, f)
    with open(file, 'r') as f:
        return json.load(f)

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f, indent=4)

data = load_json(DATA_FILE)
roles = load_json(ROLE_FILE)
shop = load_json(SHOP_FILE)
warnings = load_json(WARNING_FILE)
chat_log = load_json(CHAT_LOG_FILE)
log_channels = load_json(LOG_CHANNEL_FILE)

# 필수 보조 함수
def get_user_data(user_id):
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {"chat": 0, "att": 0, "buy": 0, "items": []}
    return data[user_id]

def save_all():
    save_json(DATA_FILE, data)
    save_json(WARNING_FILE, warnings)

def get_total_points(user_data):
    return user_data["chat"] + user_data["att"] + user_data["buy"]

def deduct_points(user_data, amount):
    for key in ["chat", "att", "buy"]:
        deduct = min(user_data[key], amount)
        user_data[key] -= deduct
        amount -= deduct
        if amount <= 0:
            break
    return amount == 0

# 봇 실행 메시지
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ 봇 실행됨: {bot.user} ")

# 역할 확인
def has_allowed_role(member):
    allowed_roles = roles.get(str(member.guild.id), [])
    return any(role.id in allowed_roles for role in member.roles)

# ───────────────────────────── 일반 유저 명령어 ─────────────────────────────

@tree.command(name="출석", description="출석체크하고 포인트를 받습니다.")
async def 출석(interaction: Interaction):
    if not has_allowed_role(interaction.user):
        return await interaction.response.send_message("명령어를 사용할 권한이 없습니다.", ephemeral=True)

    user_data = get_user_data(interaction.user.id)
    user_data["att"] += 10
    save_all()
    await interaction.response.send_message("✅ 출석 완료! 출석 포인트 +10")

@tree.command(name="포인트", description="보유 포인트를 확인합니다.")
async def 포인트(interaction: Interaction):
    if not has_allowed_role(interaction.user):
        return await interaction.response.send_message("명령어를 사용할 수 없습니다.", ephemeral=True)

    user_data = get_user_data(interaction.user.id)
    embed = discord.Embed(title="💰 보유 포인트", color=discord.Color.green())
    embed.add_field(name="채팅 포인트", value=user_data["chat"])
    embed.add_field(name="출석 포인트", value=user_data["att"])
    embed.add_field(name="구매 포인트", value=user_data["buy"])
    embed.add_field(name="총 합계", value=get_total_points(user_data))
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="유저정보", description="유저 정보를 확인합니다.")
async def 유저정보(interaction: Interaction, user: discord.Member = None):
    if not has_allowed_role(interaction.user):
        return await interaction.response.send_message("명령어를 사용할 수 없습니다.", ephemeral=True)
    
    user = user or interaction.user
    user_data = get_user_data(user.id)
    embed = discord.Embed(title=f"{user.name} 님의 정보", color=discord.Color.blue())
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="총 포인트", value=get_total_points(user_data), inline=False)
    embed.add_field(name="채팅", value=user_data["chat"])
    embed.add_field(name="출석", value=user_data["att"])
    embed.add_field(name="구매", value=user_data["buy"])
    await interaction.response.send_message(embed=embed)

@tree.command(name="내아이템", description="내가 구매한 아이템을 확인합니다.")
async def 내아이템(interaction: Interaction):
    if not has_allowed_role(interaction.user):
        return await interaction.response.send_message("명령어를 사용할 수 없습니다.", ephemeral=True)

    user_data = get_user_data(interaction.user.id)
    items = user_data.get("items", [])
    if not items:
        await interaction.response.send_message("구매한 아이템이 없습니다.")
    else:
        await interaction.response.send_message("📦 보유 아이템:\n" + "\n".join(items))

@tree.command(name="상점", description="상점에서 아이템을 구매합니다.")
async def 상점(interaction: Interaction):
    if not has_allowed_role(interaction.user):
        return await interaction.response.send_message("명령어를 사용할 수 없습니다.", ephemeral=True)

    class ShopView(View):
        def __init__(self):
            super().__init__(timeout=30)
            for item, price in shop.items():
                self.add_item(Button(label=f"{item} - {price}P", custom_id=item))

        @discord.ui.button(label="닫기", style=discord.ButtonStyle.danger)
        async def close(self, interaction: Interaction, button: Button):
            await interaction.message.delete()

        async def interaction_check(self, interaction: Interaction):
            user_data = get_user_data(interaction.user.id)
            item = interaction.data["custom_id"]
            price = shop.get(item)
            if not price:
                return True
            if get_total_points(user_data) < price:
                await interaction.response.send_message("포인트가 부족합니다.", ephemeral=True)
                return False
            deducted = deduct_points(user_data, price)
            if deducted:
                user_data["items"].append(item)
                save_all()
                await interaction.response.send_message(f"✅ '{item}' 구매 완료!", ephemeral=True)
            return True

    await interaction.response.send_message("🛒 상점 아이템:", view=ShopView(), ephemeral=True)

# ───────────────────────────── 관리자 명령어 ─────────────────────────────

@tree.command(name="공지", description="공지사항을 보냅니다. (관리자 전용)")
@app_commands.describe(title="제목", content="내용", image_url="이미지 URL", mention_all="전체 멘션 여부")
async def 공지(interaction: Interaction, title: str, content: str, image_url: str = None, mention_all: bool = False):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("권한이 없습니다.", ephemeral=True)

    embed = discord.Embed(title=title, description=content, color=discord.Color.gold())
    if image_url:
        embed.set_image(url=image_url)
    content = "@everyone" if mention_all else None
    await interaction.channel.send(content, embed=embed)
    await interaction.response.send_message("✅ 공지 전송 완료!", ephemeral=True)

@tree.command(name="경고", description="유저에게 경고를 부여합니다. (관리자 전용)")
async def 경고(interaction: Interaction, user: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("권한이 없습니다.", ephemeral=True)

    uid = str(user.id)
    warnings[uid] = warnings.get(uid, 0) + 1
    if warnings[uid] >= 3:
        user_data = get_user_data(uid)
        deduct_points(user_data, 10)
    save_all()
    await interaction.response.send_message(f"⚠️ {user.name}님에게 경고를 부여했습니다. (총 {warnings[uid]}회)")

@tree.command(name="경고제거", description="유저의 경고를 제거합니다. (관리자 전용)")
async def 경고제거(interaction: Interaction, user: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("권한이 없습니다.", ephemeral=True)

    uid = str(user.id)
    if uid in warnings:
        warnings[uid] = max(0, warnings[uid] - 1)
        save_all()
        await interaction.response.send_message(f"✅ {user.name}님의 경고가 제거되었습니다. (남은 경고: {warnings[uid]})")
    else:
        await interaction.response.send_message("해당 유저에게는 경고가 없습니다.")

@tree.command(name="채팅로그활성화", description="지정된 채널의 채팅 로그를 기록합니다.")
async def 채팅로그활성화(interaction: Interaction):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("권한이 없습니다.", ephemeral=True)

    chat_log[str(interaction.channel.id)] = True
    save_json(CHAT_LOG_FILE, chat_log)
    await interaction.response.send_message("✅ 채팅 로그가 활성화되었습니다.", ephemeral=True)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    cid = str(message.channel.id)
    if chat_log.get(cid):
        log_entry = {
            "author": message.author.name,
            "content": message.content,
            "attachments": [a.url for a in message.attachments],
            "timestamp": str(message.created_at)
        }
        log_path = f"chat_logs_{cid}.json"
        logs = load_json(log_path)
        logs[str(message.id)] = log_entry
        save_json(log_path, logs)

@tree.command(name="로그채널설정", description="로그를 보낼 채널을 설정합니다.")
async def 로그채널설정(interaction: Interaction, channel: discord.TextChannel):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("권한이 없습니다.", ephemeral=True)

    log_channels[str(interaction.guild.id)] = channel.id
    save_json(LOG_CHANNEL_FILE, log_channels)
    await interaction.response.send_message(f"✅ 로그 채널이 {channel.mention} 으로 설정되었습니다.", ephemeral=True)

@tree.command(name="포인트지급", description="포인트를 지급합니다.")
async def 포인트지급(interaction: Interaction, user: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
    
    user_data = get_user_data(user.id)
    user_data["chat"] += amount
    save_all()
    await interaction.response.send_message(f"✅ {user.mention}님에게 {amount} 포인트 지급 완료!")

@tree.command(name="포인트회수", description="포인트를 회수합니다.")
async def 포인트회수(interaction: Interaction, user: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("권한이 없습니다.", ephemeral=True)
    
    user_data = get_user_data(user.id)
    success = deduct_points(user_data, amount)
    if success:
        save_all()
        await interaction.response.send_message(f"🔻 {user.mention}님에게서 {amount} 포인트 회수 완료!")
    else:
        await interaction.response.send_message("해당 유저의 보유 포인트가 부족합니다.")

#유저명령어역할설정
@tree.command(name="유저명령어역할설정", description="일반 명령어 사용이 가능한 역할들을 설정합니다. (최대 5개까지)")
@app_commands.describe(
    역할1="첫 번째 역할 (선택)",
    역할2="두 번째 역할 (선택)",
    역할3="세 번째 역할 (선택)",
    역할4="네 번째 역할 (선택)",
    역할5="다섯 번째 역할 (선택)"
)
async def 유저명령어역할설정(
    interaction: Interaction,
    역할1: discord.Role = None,
    역할2: discord.Role = None,
    역할3: discord.Role = None,
    역할4: discord.Role = None,
    역할5: discord.Role = None,
):
    if not interaction.user.guild_permissions.administrator:
        return await interaction.response.send_message("🚫 관리자만 사용할 수 있는 명령어입니다.", ephemeral=True)

    guild_id = str(interaction.guild.id)
    role_ids = roles.get(guild_id, [])
    
    입력된_역할 = [r for r in [역할1, 역할2, 역할3, 역할4, 역할5] if r is not None]
    추가된_역할 = []

    for role in 입력된_역할:
        if role.id not in role_ids:
            role_ids.append(role.id)
            추가된_역할.append(role.name)

    roles[guild_id] = role_ids
    save_json(ROLE_FILE, roles)

    if 추가된_역할:
        await interaction.response.send_message(f"✅ 다음 역할들이 추가되었습니다:\n**{', '.join(추가된_역할)}**", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ 추가된 역할이 없습니다.", ephemeral=True)
# ───────────────────────────── 봇 실행 ─────────────────────────────
bot.run("MTM5MzkxMjc0NzY4NjYyOTQ2Ng.G1t4qJ.3VY_rns4vMhjfeQAlW8Gspu1FTEHI-7tUhTIsk")
