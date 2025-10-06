import discord
from discord.ext import commands
import wavelink
import asyncio
import os
from spotipy import Spotify
from spotipy.oauth2 import SpotifyClientCredentials

# Load environment variables
TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_URL = os.getenv("LAVALINK_URL")
LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Spotify Setup
spotify = Spotify(auth_manager=SpotifyClientCredentials(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET
))

@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} (ID: {bot.user.id})")

    # Connect to Lavalink
    if not wavelink.Pool.get_nodes():
        try:
            node: wavelink.Node = await wavelink.Pool.connect(
                client=bot,
                nodes=[
                    wavelink.Node(
                        identifier="MAIN",
                        uri=LAVALINK_URL,
                        password=LAVALINK_PASSWORD
                    )
                ]
            )
            print("🎵 Lavalink connected successfully!")
        except Exception as e:
            print(f"❌ Lavalink connection failed: {e}")
    else:
        print("Lavalink already connected.")

# Music Play Command
@bot.command(name="play")
async def play(ctx, *, query: str):
    if not ctx.author.voice:
        return await ctx.send("❌ You must be in a voice channel to use this command.")

    channel = ctx.author.voice.channel
    vc: wavelink.Player = ctx.voice_client or await channel.connect(cls=wavelink.Player)

    # Check Lavalink connection
    if not wavelink.Pool.get_node():
        return await ctx.send("⚠️ Lavalink is not connected!")

    # If it's a Spotify link
    if "spotify" in query:
        track_info = spotify.track(query)
        query = f"{track_info['artists'][0]['name']} - {track_info['name']}"

    tracks = await wavelink.Playable.search(query)
    if not tracks:
        return await ctx.send("❌ No results found.")

    track = tracks[0]
    await vc.play(track)
    await ctx.send(f"▶️ Now playing: **{track.title}**")

# Stop Command
@bot.command(name="stop")
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("🛑 Disconnected.")
    else:
        await ctx.send("❌ I'm not connected to a voice channel.")

# Pause Command
@bot.command(name="pause")
async def pause(ctx):
    vc: wavelink.Player = ctx.voice_client
    if vc and vc.is_playing():
        await vc.pause()
        await ctx.send("⏸️ Paused.")
    else:
        await ctx.send("❌ Nothing is playing.")

# Resume Command
@bot.command(name="resume")
async def resume(ctx):
    vc: wavelink.Player = ctx.voice_client
    if vc and vc.is_paused():
        await vc.resume()
        await ctx.send("▶️ Resumed.")
    else:
        await ctx.send("❌ Nothing is paused.")

# Volume Command
@bot.command(name="volume")
async def volume(ctx, vol: int):
    vc: wavelink.Player = ctx.voice_client
    if not vc:
        return await ctx.send("❌ I'm not connected to a voice channel.")
    await vc.set_volume(vol)
    await ctx.send(f"🔊 Volume set to {vol}%")

bot.run(TOKEN)
