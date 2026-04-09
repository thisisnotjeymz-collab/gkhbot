import os
import asyncio
import random
import discord
from google import genai
from discord.ext import commands, tasks

# ===== GEMINI CONFIG =====
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
AI_MODE = os.getenv("AI_MODE", "normal")
AI_MAX_CHARS = int(os.getenv("AI_MAX_CHARS", "300"))
AI_COOLDOWN = int(os.getenv("AI_COOLDOWN", "3"))
AUTO_REPLY_CHANCE = float(os.getenv("AUTO_REPLY_CHANCE", "0"))
MEMORY_TURNS = int(os.getenv("MEMORY_TURNS", "6"))

last_ai_use = {}
CHAT_MEMORY = {}
USER_PROFILE = {}

def get_ai_prompt(mode):
    if mode == "toxic":
        return "You are the Discord bot of GKH. Reply in short Taglish. Be funny, playful, slightly toxic."
    elif mode == "chill":
        return "You are the Discord bot of GKH. Reply in calm, friendly, casual Taglish."
    elif mode == "admin":
        return "You are the Discord bot of GKH. Reply like a helpful Discord admin. Be clear and direct."
    else:
        return "You are the Discord bot of GKH. Reply in simple Taglish, short, natural, and a little funny."

def get_user_profile(user_id: str):
    if user_id not in USER_PROFILE:
        USER_PROFILE[user_id] = {
            "style": "normal",
            "insult_count": 0,
            "last_insults": []
        }
    return USER_PROFILE[user_id]

def detect_insult(text: str):
    text = text.lower()
    insult_words = ["bobo", "tanga", "ulol", "gago", "kupal", "tangina", "burat"]
    found = [word for word in insult_words if word in text]
    return found

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

    user_id = str(message.author.id)
    now = asyncio.get_event_loop().time()

    should_reply = False

    if bot.user in message.mentions:
        should_reply = True
    elif AUTO_REPLY_CHANCE > 0 and random.random() < AUTO_REPLY_CHANCE:
        should_reply = True

    if not should_reply:
        await bot.process_commands(message)
        return

    if user_id in last_ai_use:
        if now - last_ai_use[user_id] < AI_COOLDOWN:
            return

    last_ai_use[user_id] = now

    if user_id not in CHAT_MEMORY:
        CHAT_MEMORY[user_id] = []

    profile = get_user_profile(user_id)

    found_insults = detect_insult(message.content)
    if found_insults:
        profile["insult_count"] += len(found_insults)
        profile["last_insults"].extend(found_insults)
        profile["last_insults"] = profile["last_insults"][-5:]

    if profile["insult_count"] >= 8:
        profile["style"] = "chaos"
    elif profile["insult_count"] >= 3:
        profile["style"] = "playful"
    else:
        profile["style"] = "normal"

    CHAT_MEMORY[user_id].append(f"User: {message.content}")
    CHAT_MEMORY[user_id] = CHAT_MEMORY[user_id][-MEMORY_TURNS:]

    try:
        async with message.channel.typing():
            base_prompt = get_ai_prompt(AI_MODE)

            if profile["insult_count"] >= 8:
                personality_note = (
                    "This user often teases you. Reply playfully and sarcastically, "
                    "but keep it short and not too aggressive."
                )
            elif profile["insult_count"] >= 3:
                personality_note = (
                    "This user sometimes teases you. Reply with a playful, slightly sarcastic tone."
                )
            else:
                personality_note = "This user is normal. Reply in your default tone."

            recent_insults = ", ".join(profile["last_insults"]) if profile["last_insults"] else "none"
            memory_text = "\n".join(CHAT_MEMORY[user_id])

            prompt = f"""
{base_prompt}

You are chatting in a Discord server called GKH.

User profile:
- current style: {profile["style"]}
- insult count: {profile["insult_count"]}
- recent insults used by the user: {recent_insults}

Behavior rule:
{personality_note}

Recent conversation:
{memory_text}
"""

            models = [
                MODEL_NAME,
                "gemini-2.5-flash-lite",
                "gemini-2.5-flash"
            ]

            reply_text = None

            for model in models:
                try:
                    response = gemini_client.models.generate_content(
                        model=model,
                        contents=f"{prompt}\n\nReply naturally to the latest user message:\n{message.content}"
                    )

                    reply_text = getattr(response, "text", None)

                    if reply_text and reply_text.strip():
                        break

                except Exception as e:
                    print(f"Retry failed ({model}): {e}")
                    await asyncio.sleep(1)

            if reply_text and reply_text.strip():
                reply_text = reply_text[:AI_MAX_CHARS]

                CHAT_MEMORY[user_id].append(f"Bot: {reply_text}")
                CHAT_MEMORY[user_id] = CHAT_MEMORY[user_id][-MEMORY_TURNS:]

                await asyncio.sleep(random.uniform(1, 2))
                await message.reply(reply_text)
            else:
                await message.channel.send("busy si GKH, try mo ulit 😭")

    except Exception as e:
        print(f"Gemini error: {e}")
        await message.channel.send("may topak si GKH ngayon 😭")

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
