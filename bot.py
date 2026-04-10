import os
import asyncio
import random
import discord
from google import genai
from openai import OpenAI
from discord.ext import commands, tasks
from discord import app_commands
from dotenv import load_dotenv

load_dotenv()

# ===== CONFIG =====
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
AI_MODE = os.getenv("AI_MODE", "normal")
AI_MAX_CHARS = int(os.getenv("AI_MAX_CHARS", "300"))
AI_COOLDOWN = int(os.getenv("AI_COOLDOWN", "3"))
AUTO_REPLY_CHANCE = float(os.getenv("AUTO_REPLY_CHANCE", "0"))
MEMORY_TURNS = int(os.getenv("MEMORY_TURNS", "6"))

OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")

last_ai_use = {}
CHAT_MEMORY = {}
USER_PROFILE = {}

# ===== AI STYLE =====
def get_ai_prompt(mode):
    if mode == "toxic":
        return "Reply in short Taglish. Medyo toxic pero funny."
    return "Reply in simple Taglish, short and natural."

def get_user_profile(user_id):
    if user_id not in USER_PROFILE:
        USER_PROFILE[user_id] = {"insult_count": 0}
    return USER_PROFILE[user_id]

def detect_insult(text):
    words = ["bobo", "tanga", "ulol", "gago", "kupal", "tangina"]
    return [w for w in words if w in text.lower()]

# ===== AI CLIENTS =====
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

openrouter_client = None
if os.getenv("OPENROUTER_API_KEY"):
    openrouter_client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url="https://openrouter.ai/api/v1"
    )

# ===== BOT =====
TOKEN = os.getenv("DISCORD_TOKEN")
VC_CHANNEL_ID = int(os.getenv("VC_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===== STATUS =====
@tasks.loop(seconds=10)
async def change_status():
    await bot.change_presence(activity=discord.Game(random.choice(["Join GKH", "Veloriax 〆"])))

# ===== VC =====
async def connect_to_vc():
    if VC_CHANNEL_ID == 0:
        return
    try:
        channel = bot.get_channel(VC_CHANNEL_ID)
        if channel and isinstance(channel, discord.VoiceChannel):
            if not channel.guild.voice_client:
                await channel.connect()
    except:
        pass

# ===== ANNOUNCE COMMAND =====
@bot.tree.command(name="announce", description="Send announcement")
@app_commands.describe(message="Message", channel="Channel")
async def announce(interaction: discord.Interaction, message: str, channel: discord.TextChannel = None):

    if not interaction.user.guild_permissions.manage_messages:
        await interaction.response.send_message("wala kang perms tanga", ephemeral=True)
        return

    target = channel or interaction.channel

    embed = discord.Embed(
        title="📢 Announcement",
        description=message,
        color=discord.Color.blurple()
    )
    embed.set_footer(text=f"By {interaction.user}")

    await target.send(embed=embed)
    await interaction.response.send_message("sent na boss", ephemeral=True)

# ===== AI RESPONSE =====
async def try_gemini(prompt):
    try:
        res = gemini_client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt
        )
        return getattr(res, "text", None)
    except:
        return None

async def try_openrouter(prompt):
    if not openrouter_client:
        return None
    try:
        res = openrouter_client.chat.completions.create(
            model=OPENROUTER_MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return res.choices[0].message.content
    except:
        return None

# ===== MESSAGE EVENT =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = str(message.author.id)
    now = asyncio.get_event_loop().time()

    if bot.user not in message.mentions:
        await bot.process_commands(message)
        return

    if user_id in last_ai_use and now - last_ai_use[user_id] < AI_COOLDOWN:
        return

    last_ai_use[user_id] = now

    profile = get_user_profile(user_id)
    insults = detect_insult(message.content)

    if insults:
        profile["insult_count"] += len(insults)

    prompt = f"{get_ai_prompt(AI_MODE)}\nUser: {message.content}"

    async with message.channel.typing():
        reply = await try_gemini(prompt)
        if not reply:
            reply = await try_openrouter(prompt)

        if reply:
            await message.reply(reply[:AI_MAX_CHARS])
        else:
            await message.reply("busy ako ngayon 😭")

    await bot.process_commands(message)

# ===== READY =====
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e:
        print(e)

    if not change_status.is_running():
        change_status.start()

    await connect_to_vc()

bot.run(TOKEN)
