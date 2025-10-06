import discord
from discord.ext import commands
import wavelink
import os
import asyncio

# ---------- Bot Setup ----------
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix='!', intents=intents)

# ---------- Lavalink Connection ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")

    if not wavelink.Pool.is_connected():
        node = wavelink.Node(
            identifier="MAIN",
            uri=os.getenv("LAVALINK_URL"),  # e.g. https://lavalink-server1.onrender.com
            password=os.getenv("LAVALINK_PASSWORD"),  # e.g. youshallnotpass
            secure=True
        )
        await wavelink.Pool.connect(nodes=[node], client=bot)
        print("🎶 Lavalink node connected successfully!")

# ---------- Music Player ----------
@bot.command()
async def join(ctx):
    """Join the user's voice channel."""
    if not ctx.author.voice:
        return await ctx.send("❌ You must be in a voice channel to summon me.")
    channel = ctx.author.voice.channel
    vc = await channel.connect(cls=wavelink.Player)
    await ctx.send(f"✅ Joined **{channel}**")

@bot.command()
async def play(ctx, *, query: str):
    """Play a song by name or URL."""
    if not ctx.voice_client:
        await join(ctx)

    vc: wavelink.Player = ctx.voice_client

    tracks = await wavelink.YouTubeTrack.search(query=query)
    if not tracks:
        return await ctx.send("❌ No results found.")
    
    track = tracks[0]
    await vc.play(track)
    await ctx.send(f"🎵 Now playing: **{track.title}**")

@bot.command()
async def stop(ctx):
    """Stop playing and disconnect."""
    vc: wavelink.Player = ctx.voice_client
    if not vc:
        return await ctx.send("❌ I’m not connected to any voice channel.")
    await vc.stop()
    await vc.disconnect()
    await ctx.send("🛑 Stopped and disconnected.")

@bot.command()
async def skip(ctx):
    """Skip the current track."""
    vc: wavelink.Player = ctx.voice_client
    if not vc or not vc.is_playing():
        return await ctx.send("❌ Nothing is playing right now.")
    await vc.stop()
    await ctx.send("⏭️ Skipped the current song.")

# ---------- Run the bot ----------
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)
