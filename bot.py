import os
import asyncio
import discord
from discord.ext import commands
import wavelink
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from flask import Flask
from threading import Thread

# ---------- CONFIG ----------
TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_URL = os.getenv("LAVALINK_URL", "https://lavalink-server1.onrender.com")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
SPOTIFY_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.5"))

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- KEEP-ALIVE FOR RENDER ----------
app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running and connected!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_web).start()

# ---------- LAVALINK SETUP ----------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await connect_lavalink()
    print("🎵 Lavalink connected and ready!")

async def connect_lavalink():
    try:
        node: wavelink.Node = wavelink.Node(
            uri=LAVALINK_URL,
            password=LAVALINK_PASSWORD,
            identifier="MAIN"
        )
        await wavelink.Pool.connect(nodes=[node], client=bot)
        print("🎧 Connected to Lavalink successfully!")
    except Exception as e:
        print(f"❌ Lavalink connection failed: {e}")

# ---------- HELPER ----------
async def get_player(ctx: commands.Context) -> wavelink.Player:
    if not ctx.author.voice:
        await ctx.send("You must join a voice channel first.")
        return None
    channel = ctx.author.voice.channel
    if not ctx.voice_client:
        vc: wavelink.Player = await channel.connect(cls=wavelink.Player)
    else:
        vc: wavelink.Player = ctx.voice_client
        if vc.channel != channel:
            await vc.move_to(channel)
    return vc

# ---------- COMMANDS ----------
@bot.command()
async def join(ctx):
    """Join your voice channel."""
    vc = await get_player(ctx)
    if vc:
        await ctx.send(f"Joined **{vc.channel.name}** ✅")

@bot.command()
async def play(ctx, *, query: str):
    """Play a song from YouTube, Spotify, etc."""
    vc = await get_player(ctx)
    if not vc:
        return

    tracks = []
    if "spotify.com" in query and SPOTIFY_ID and SPOTIFY_SECRET:
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_ID, client_secret=SPOTIFY_SECRET))
        if "track/" in query:
            tid = query.split("track/")[-1].split("?")[0]
            t = sp.track(tid)
            name = f"{t['name']} - {', '.join(a['name'] for a in t['artists'])}"
            search = await wavelink.Playable.search(name)
            if search:
                tracks.append(search[0])
        elif "playlist/" in query:
            pid = query.split("playlist/")[-1].split("?")[0]
            res = sp.playlist_items(pid)
            for i in res["items"]:
                t = i["track"]
                name = f"{t['name']} - {', '.join(a['name'] for a in t['artists'])}"
                search = await wavelink.Playable.search(name)
                if search:
                    tracks.append(search[0])
    else:
        tracks = await wavelink.Playable.search(query)

    if not tracks:
        await ctx.send("❌ No results found.")
        return

    track = tracks[0]
    await vc.play(track)
    await vc.set_volume(int(DEFAULT_VOLUME * 100))
    await ctx.send(f"🎶 Now playing: **{track.title}**")

@bot.command()
async def pause(ctx):
    """Pause current song."""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        await vc.pause()
        await ctx.send("⏸️ Paused.")
    else:
        await ctx.send("Nothing is playing.")

@bot.command()
async def resume(ctx):
    """Resume paused song."""
    vc = ctx.voice_client
    if vc and vc.paused:
        await vc.resume()
        await ctx.send("▶️ Resumed.")
    else:
        await ctx.send("Nothing is paused.")

@bot.command()
async def skip(ctx):
    """Skip current track."""
    vc = ctx.voice_client
    if vc and vc.is_playing():
        await vc.stop()
        await ctx.send("⏭️ Skipped.")
    else:
        await ctx.send("Nothing to skip.")

@bot.command()
async def leave(ctx):
    """Disconnect the bot."""
    vc = ctx.voice_client
    if vc:
        await vc.disconnect()
        await ctx.send("👋 Left the channel.")
    else:
        await ctx.send("I'm not connected.")

# ---------- RUN BOT ----------
if not TOKEN:
    raise SystemExit("❌ DISCORD_TOKEN not set in environment.")
bot.run(TOKEN)
