import os
import json
import asyncio
import discord
from discord import app_commands
from discord.ext import commands
import wavelink
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

# -------- CONFIG --------
# Matches your Render environment variable names
TOKEN = os.getenv("DISCORD_TOKEN")
LAVALINK_URL = os.getenv("URL", "http://lavalink:2333")
LAVALINK_PASSWORD = os.getenv("PASSWORD", "youshallnotpass")
SPOTIFY_ID = os.getenv("CLIENT_ID")
SPOTIFY_SECRET = os.getenv("CLIENT_SECRET")
DJ_ROLE_NAME = os.getenv("DJ_ROLE_NAME", "DJ")
DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.5"))

intents = discord.Intents.default()
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), intents=intents)

# -------- LAVALINK SETUP --------
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await connect_nodes()
    await bot.tree.sync()
    print("Slash commands synced and Lavalink ready.")

async def connect_nodes():
    if not wavelink.Pool.nodes:
        node = wavelink.Node(
            uri=LAVALINK_URL,
            password=LAVALINK_PASSWORD,
            identifier="MAIN"
        )
        await wavelink.Pool.connect(nodes=[node], client=bot)
        print("🎧 Connected to Lavalink.")

# -------- HELPERS --------
def is_dj(member: discord.Member) -> bool:
    return any(r.name == DJ_ROLE_NAME for r in member.roles) or member.guild_permissions.manage_guild

async def get_player(inter: discord.Interaction) -> wavelink.Player:
    if not inter.user or not inter.user.voice:
        raise commands.CommandError("You must join a voice channel first.")
    channel = inter.user.voice.channel
    if not inter.guild.voice_client:
        vc: wavelink.Player = await channel.connect(cls=wavelink.Player)
    else:
        vc: wavelink.Player = inter.guild.voice_client
        if vc.channel != channel:
            await vc.move_to(channel)
    return vc

async def spotify_to_tracks(query: str) -> list[wavelink.Playable]:
    """Convert Spotify tracks/playlists/albums to playable tracks via search."""
    sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIFY_ID, client_secret=SPOTIFY_SECRET))
    tracks = []
    def fmt(track):
        artists = ", ".join(a["name"] for a in track["artists"])
        return f"{track['name']} - {artists}"
    if "track/" in query:
        tid = query.split("track/")[-1].split("?")[0]
        t = sp.track(tid)
        search = await wavelink.Playable.search(fmt(t))
        if search: tracks.append(search[0])
    elif "playlist/" in query:
        pid = query.split("playlist/")[-1].split("?")[0]
        res = sp.playlist_items(pid)
        for i in res["items"]:
            t = i.get("track")
            if t:
                search = await wavelink.Playable.search(fmt(t))
                if search: tracks.append(search[0])
    elif "album/" in query:
        aid = query.split("album/")[-1].split("?")[0]
        res = sp.album_tracks(aid)
        for t in res["items"]:
            search = await wavelink.Playable.search(fmt(t))
            if search: tracks.append(search[0])
    return tracks

# -------- COMMANDS --------
@bot.tree.command(name="join", description="Join your voice channel.")
async def join(inter: discord.Interaction):
    await inter.response.defer(ephemeral=True)
    vc = await get_player(inter)
    await inter.followup.send(f"Joined **{vc.channel.name}**")

@bot.tree.command(name="play", description="Play a song or playlist from any link (YouTube, Spotify, SoundCloud, etc.)")
async def play(inter: discord.Interaction, query: str):
    await inter.response.defer()
    vc = await get_player(inter)
    if "spotify.com" in query and SPOTIFY_ID and SPOTIFY_SECRET:
        results = await spotify_to_tracks(query)
    else:
        results = await wavelink.Playable.search(query)
    if not results:
        await inter.followup.send("❌ Nothing found.")
        return
    track = results[0]
    await vc.play(track)
    vc.autoplay = wavelink.AutoPlayMode.enabled
    await vc.set_volume(int(DEFAULT_VOLUME * 100))
    await inter.followup.send(f"🎶 Now playing: **{track.title}**")

@bot.tree.command(name="pause", description="Pause playback.")
async def pause(inter: discord.Interaction):
    await inter.response.defer(ephemeral=True)
    vc = inter.guild.voice_client
    if vc and vc.is_playing():
        await vc.pause(True)
        await inter.followup.send("⏸️ Paused.")
    else:
        await inter.followup.send("Not playing anything.")

@bot.tree.command(name="resume", description="Resume playback.")
async def resume(inter: discord.Interaction):
    await inter.response.defer(ephemeral=True)
    vc = inter.guild.voice_client
    if vc and vc.paused:
        await vc.pause(False)
        await inter.followup.send("▶️ Resumed.")
    else:
        await inter.followup.send("Not paused.")

@bot.tree.command(name="skip", description="Skip current track.")
async def skip(inter: discord.Interaction):
    await inter.response.defer(ephemeral=True)
    vc = inter.guild.voice_client
    if vc and vc.is_playing():
        await vc.stop()
        await inter.followup.send("⏭️ Skipped.")
    else:
        await inter.followup.send("Nothing to skip.")

@bot.tree.command(name="leave", description="Disconnect the bot.")
async def leave(inter: discord.Interaction):
    await inter.response.defer(ephemeral=True)
    vc = inter.guild.voice_client
    if vc:
        await vc.disconnect()
        await inter.followup.send("👋 Left the voice channel.")
    else:
        await inter.followup.send("I'm not connected.")

# -------- RUN --------
if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("❌ DISCORD_TOKEN not set in environment.")
    bot.run(DISCORD_TOKEN)
