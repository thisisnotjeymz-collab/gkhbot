import os
import asyncio
import discord
from google import genai
from discord.ext import commands, tasks

# ===== GEMINI CONFIG =====
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
AI_MODE = os.getenv("AI_MODE", "normal")
AI_MAX_CHARS = int(os.getenv("AI_MAX_CHARS", "300"))
AI_COOLDOWN = int(os.getenv("AI_COOLDOWN", "3"))

last_ai_use = {}

def get_ai_prompt(mode):
    if mode == "toxic":
        return "You are the Discord bot of GKH. Reply in short Taglish. Be funny, playful, slightly toxic."
    elif mode == "chill":
        return "You are the Discord bot of GKH. Reply in calm, friendly, casual Taglish."
    elif mode == "admin":
        return "You are the Discord bot of GKH. Reply like a helpful Discord admin. Be clear and direct."
    else:
        return "You are the Discord bot of GKH. Reply in simple Taglish, short, natural, and a little funny."

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# ===== BOT SETUP =====
statuses = [
    discord.Game("Join GKH Now"),
    discord.Game("GKH #1")
]

TOKEN = os.getenv("DISCORD_TOKEN")
VC_CHANNEL_ID = int(os.getenv("VC_CHANNEL_ID", "0"))

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.messages = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix="!",
    intents=intents,
    activity=discord.Game("GKH #1"),
    status=discord.Status.online
)

# ===== STATUS LOOP =====
@tasks.loop(seconds=10)
async def change_status():
    for status in statuses:
        await bot.change_presence(activity=status)
        await asyncio.sleep(10)

# ===== VC CONNECT =====
async def connect_to_vc():
    if VC_CHANNEL_ID == 0:
        print("VC_CHANNEL_ID is missing.")
        return

    channel = bot.get_channel(VC_CHANNEL_ID)
    if channel is None:
        try:
            channel = await bot.fetch_channel(VC_CHANNEL_ID)
        except Exception as e:
            print(f"Failed to fetch channel: {e}")
            return

    if not isinstance(channel, discord.VoiceChannel):
        print("Selected channel is not a voice channel.")
        return

    voice_client = channel.guild.voice_client

    try:
        if voice_client and voice_client.is_connected():
            if voice_client.channel.id != channel.id:
                await voice_client.move_to(channel)
            return

        await channel.connect()
        print(f"Connected to VC: {channel.name}")

    except Exception as e:
        print(f"Error connecting to VC: {e}")

# ===== AI CHAT =====
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.guild:
        return

    if bot.user in message.mentions:
        user_id = message.author.id
        now = asyncio.get_event_loop().time()

        if user_id in last_ai_use:
            if now - last_ai_use[user_id] < AI_COOLDOWN:
                return

        last_ai_use[user_id] = now

        try:
            async with message.channel.typing():
                prompt = get_ai_prompt(AI_MODE)

                response = gemini_client.models.generate_content(
                    model=MODEL_NAME,
                    contents=f"{prompt}\n\nUser message: {message.content}"
                )

                reply_text = getattr(response, "text", None)

                if reply_text and reply_text.strip():
                    await asyncio.sleep(1.5)
                    await message.reply(reply_text[:AI_MAX_CHARS])
                else:
                    await message.channel.send("di ako makasagot ngayon")

        except Exception as e:
            print(f"Gemini error: {e}")
            await message.channel.send("di ako makasagot ngayon")

        return

    await bot.process_commands(message)

# ===== READY =====
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    if not change_status.is_running():
        change_status.start()

    await connect_to_vc()

    if not keep_vc_alive.is_running():
        keep_vc_alive.start()

@tasks.loop(seconds=60)
async def keep_vc_alive():
    await connect_to_vc()

@bot.event
async def on_voice_state_update(member, before, after):
    if bot.user and member.id == bot.user.id and after.channel is None:
        await asyncio.sleep(3)
        await connect_to_vc()

bot.run(TOKEN)
