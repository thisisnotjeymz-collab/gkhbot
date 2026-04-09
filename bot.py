import os
import asyncio
import random
import discord
from discord.ext import commands, tasks

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

@tasks.loop(seconds=10)
async def change_status():
    for status in statuses:
        await bot.change_presence(activity=status)
        await asyncio.sleep(10)

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

@bot.tree.command(name="join", description="Make the bot join the VC")
async def join(interaction: discord.Interaction):
    await connect_to_vc()
    await interaction.response.send_message("Trying to join VC", ephemeral=True)

@bot.tree.command(name="leave", description="Make the bot leave the VC")
async def leave(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("Server only command.", ephemeral=True)
        return

    vc = interaction.guild.voice_client
    if vc and vc.is_connected():
        await vc.disconnect()
        await interaction.response.send_message("Left VC", ephemeral=True)
    else:
        await interaction.response.send_message("Bot is not in a VC", ephemeral=True)

@bot.tree.command(name="ping", description="Check if the bot is online")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("Bot is alive", ephemeral=True)

import os
import asyncio
import random
import discord
from google import genai
from discord.ext import commands, tasks

last_ai_use = {}  # 🔥 ADD THIS

gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if not message.guild:
        return

    content = message.content.lower()

    # 🤖 GEMINI AI reply pag minention ang bot
    if bot.user in message.mentions:
        user_id = message.author.id
        now = asyncio.get_event_loop().time()

        # cooldown
        if user_id in last_ai_use:
            if now - last_ai_use[user_id] < AI_COOLDOWN:
                return

        last_ai_use[user_id] = now

        try:
            prompt = get_ai_prompt(AI_MODE)

            response = gemini_client.models.generate_content(
                model=MODEL_NAME,
                contents=f"""
{prompt}

User message: {message.content}
"""
            )

            reply_text = getattr(response, "text", None)

            if reply_text and reply_text.strip():
                await message.reply(reply_text[:AI_MAX_CHARS])
            else:
                await message.channel.send("di ako makasagot ngayon")

        except Exception as e:
            print(f"Gemini error: {e}")
            await message.channel.send("di ako makasagot ngayon")

        return
    # 🔥 ALL RESPONSES SYSTEM
    responses = {
        "hello": [
            {"text": "hellow"},
            {"url": "https://tenor.com/view/hi-dog-gif-9693408977083628631"}
        ],

        "kupal": [
            {"file": "media/kupal.mp4"}
        ],

        "burat": [
            {"text": "mahilig ka siguro sa burat"}
        ],

        "tangina": [
            {"text": "tanginamo rin 🖕"}
        ],

        "ulol": [
            {"text": "ulol mo blue, balik mo muna utak mo bago ka mag chat"},
            {"file": "media/ulol.mp3"}
        ],

        "eduj": [
            {"text": "bading yan!"}
        ],

        "bisaya": [
            {"text": "ulol, kala mo naman hindi ka bisaya"}
        ],

        "bobo": [
            {"text": "mas bobo ka"},
            {"text": "tangina mo ikaw pinaka bobo dito"}
        ],

        "tanga": [
            {"text": "tangina mo, mas tanga ka"},
            {"text": "tanga ka rin"}
        ]
    }

    # 🔥 LOOP
    for trigger, replies in responses.items():
        if trigger in content:
            choice = random.choice(replies)

            if "text" in choice:
                await message.reply(choice["text"])

            if "file" in choice:
                file = discord.File(choice["file"])
                await message.reply(file=file)

            if "url" in choice:
                await message.channel.send(choice["url"])

            break

    await bot.process_commands(message)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    synced = await bot.tree.sync()
    print(f"Synced {len(synced)} commands")

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
