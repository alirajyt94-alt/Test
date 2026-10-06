import os
import sys
import subprocess

def install_package(package):
    """Install a package if not available"""
    try:
        __import__(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

required_packages = ["discord.py", "wavelink", "Pillow", "aiohttp", "aiosqlite"]

for package in required_packages:
    if package == "discord.py":
        try:
            import discord
        except ImportError:
            install_package("discord.py")
    elif package == "Pillow":
        try:
            import PIL
        except ImportError:
            install_package("Pillow")
    else:
        install_package(package)

import discord
from discord.ext import commands, tasks
import random
import datetime
from discord.ui import Button, View, Select
import wavelink
import io
import aiohttp
from typing import cast, Optional, List
import asyncio
import base64
import re
import json

try:
    from music_database import MusicDatabase
except ImportError:
    class MusicDatabase:
        async def connect(self): pass
        async def close(self): pass
        async def register_server(self, *args, **kwargs): pass
        async def register_voice_channel(self, *args, **kwargs): pass
        async def log_music_play(self, *args, **kwargs): pass
        async def log_search(self, *args, **kwargs): pass


# ---------------- EMOJI CONFIG ----------------
class EmojiConfig:
    def __init__(self):
        self.load_emojis()

    def load_emojis(self):
        try:
            with open('emoji_config.json', 'r', encoding='utf-8') as f:
                e = json.load(f)
            self.PLAY = e['music_control']['play']
            self.PAUSE = e['music_control']['pause']
            self.RESUME = e['music_control']['resume']
            self.STOP = e['music_control']['stop']
            self.SKIP = e['music_control']['skip']
            self.PREVIOUS = e['music_control']['previous']
            self.REPEAT = e['music_control']['repeat']
            self.SHUFFLE = e['music_control']['shuffle']
            self.VOLUME_UP = e['volume']['volume_up']
            self.VOLUME_DOWN = e['volume']['volume_down']
            self.VOLUME_MUTE = e['volume']['volume_mute']
            self.VOLUME_LOW = e['volume']['volume_low']
            self.VOLUME_HIGH = e['volume']['volume_high']
            self.SUCCESS = e['status']['success']
            self.ERROR = e['status']['error']
            self.WARNING = e['status']['warning']
            self.INFO = e['status']['info']
            self.LOADING = e['status']['loading']
            self.SEARCH = e['status']['search']
            self.SPOTIFY = e['music_sources']['spotify']
            self.YOUTUBE = e['music_sources']['youtube']
            self.SOUNDCLOUD = e['music_sources']['soundcloud']
            self.FILTER = e['features']['filter']
            self.MICROPHONE = e['features']['microphone']
            self.MUSICAL_NOTE = e['features']['musical_note']
            self.MUSICAL_NOTES = e['features']['musical_notes']
            self.RADIO = e['features']['radio']
            self.QUALITY = e['features']['quality']
            self.QUEUE = e['control_panel']['queue']
            self.CLEAR = e['actions']['clear']
            self.ADD = e['actions']['add']
            self.CLOCK = e['time']['clock']
            print("✅ Emojis loaded from emoji_config.json")
        except Exception as ex:
            print(f"⚠️ Emoji load failed ({ex}), using defaults")
            self.load_default_emojis()

    def load_default_emojis(self):
        self.PLAY = "▶️"; self.PAUSE = "⏸️"; self.RESUME = "▶️"; self.STOP = "⏹️"
        self.SKIP = "⏭️"; self.PREVIOUS = "⏮️"; self.REPEAT = "🔁"; self.SHUFFLE = "🔀"
        self.VOLUME_UP = "🔊"; self.VOLUME_DOWN = "🔉"; self.VOLUME_MUTE = "🔇"
        self.VOLUME_LOW = "🔈"; self.VOLUME_HIGH = "🔊"
        self.SUCCESS = "✅"; self.ERROR = "❌"; self.WARNING = "⚠️"
        self.INFO = "ℹ️"; self.LOADING = "⏳"; self.SEARCH = "🔍"
        self.SPOTIFY = "🎧"; self.YOUTUBE = "▶️"; self.SOUNDCLOUD = "☁️"
        self.FILTER = "🎛️"; self.MICROPHONE = "🎤"; self.MUSICAL_NOTE = "🎵"
        self.MUSICAL_NOTES = "🎶"; self.RADIO = "📻"; self.QUALITY = "💎"
        self.QUEUE = "📜"; self.CLEAR = "🗑️"; self.ADD = "➕"; self.CLOCK = "🕒"


# ---------------- SPOTIFY ----------------
SPOTIFY_TRACK_REGEX = r"https?://open\.spotify\.com/track/([a-zA-Z0-9]+)"
SPOTIFY_PLAYLIST_REGEX = r"https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
SPOTIFY_ALBUM_REGEX = r"https?://open\.spotify\.com/album/([a-zA-Z0-9]+)"


class SpotifyAPI:
    BASE_URL = "https://api.spotify.com/v1"

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None

    async def get_token(self):
        auth_url = "https://accounts.spotify.com/api/token"
        auth_value = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {auth_value}"}
        data = {"grant_type": "client_credentials"}
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, headers=headers, data=data) as resp:
                if resp.status != 200:
                    raise Exception(f"Spotify token error {resp.status}")
                self.token = (await resp.json()).get("access_token")

    async def get(self, endpoint, params=None):
        for attempt in range(2):
            if not self.token or attempt > 0:
                await self.get_token()
            url = f"{self.BASE_URL}/{endpoint}"
            headers = {"Authorization": f"Bearer {self.token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 401 and attempt == 0:
                        continue
                    if resp.status != 200:
                        raise Exception(f"Spotify fetch error {resp.status}")
                    return await resp.json()
        raise Exception("Spotify max retries")

    async def get_track(self, tid): return await self.get(f"tracks/{tid}")
    async def get_playlist(self, pid): return await self.get(f"playlists/{pid}")


try:
    with open('bot_config.json', 'r') as f:
        cfg = json.load(f)
        spotify_client_id = cfg.get('spotify_client_id') or os.environ.get("SPOTIFY_CLIENT_ID")
        spotify_client_secret = cfg.get('spotify_client_secret') or os.environ.get("SPOTIFY_CLIENT_SECRET")
except FileNotFoundError:
    spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

spotify_api = None
if spotify_client_id and spotify_client_secret:
    spotify_api = SpotifyAPI(spotify_client_id, spotify_client_secret)
    print("✅ Spotify API initialized")
else:
    print("⚠️ Spotify credentials not set")


# ---------------- GLOBAL STATE ----------------
active_player_messages = {}
track_histories = {}
user_playlists = {}
blacklist_check = lambda: commands.check(lambda ctx: True)
ignore_check = lambda: commands.check(lambda ctx: True)


# ---------------- FILTER SELECT ----------------
class FilterSelectView(View):
    def __init__(self, player, ctx):
        super().__init__(timeout=60)
        self.player = player
        self.ctx = ctx
        self.emoji = EmojiConfig()

    @discord.ui.select(
        placeholder="🎛️ Select Audio Filter...",
        options=[
            discord.SelectOption(label="Nightcore", value="nightcore", emoji="🎵"),
            discord.SelectOption(label="Bass Boost", value="bassboost", emoji="🔊"),
            discord.SelectOption(label="Vaporwave", value="vaporwave", emoji="🌴"),
            discord.SelectOption(label="Karaoke", value="karaoke", emoji="🎤"),
            discord.SelectOption(label="Tremolo", value="tremolo", emoji="🎛️"),
            discord.SelectOption(label="Vibrato", value="vibrato", emoji="🎶"),
            discord.SelectOption(label="Rotation", value="rotation", emoji="🔄"),
            discord.SelectOption(label="Distortion", value="distortion", emoji="🎸"),
            discord.SelectOption(label="Clear Filters", value="clear", emoji="🧹"),
        ]
    )
    async def select_filter(self, interaction: discord.Interaction, select: Select):
        name = select.values[0]
        filters = wavelink.Filters()
        desc = "Unknown filter"

        if name == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.2, rate=1)
            desc = "Nightcore applied"
        elif name == "bassboost":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.8}, {"band": 1, "gain": 0.6},
                {"band": 2, "gain": 0.4}, {"band": 3, "gain": 0.2},
                {"band": 4, "gain": 0.1}, {"band": 5, "gain": 0.0},
            ])
            desc = "Bass Boost applied"
        elif name == "vaporwave":
            filters.timescale.set(rate=0.8, pitch=0.9)
            desc = "Vaporwave applied"
        elif name == "karaoke":
            filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
            desc = "Karaoke applied"
        elif name == "tremolo":
            filters.tremolo.set(depth=0.5, frequency=10.0)
            desc = "Tremolo applied"
        elif name == "vibrato":
            filters.vibrato.set(depth=0.5, frequency=5.0)
            desc = "Vibrato applied"
        elif name == "rotation":
            filters.rotation.set(rotation_hz=0.2)
            desc = "Rotation applied"
        elif name == "distortion":
            filters.distortion.set(sin_offset=0.0, sin_scale=1.0, cos_offset=0.0,
                                    cos_scale=1.0, tan_offset=0.0, tan_scale=1.0,
                                    offset=0.0, scale=1.0)
            desc = "Distortion applied"
        elif name == "clear":
            filters = wavelink.Filters()
            desc = "All filters cleared"

        await self.player.set_filters(filters)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{self.emoji.FILTER} Filter", description=desc, color=0x1DB954),
            ephemeral=True
        )


# ---------------- MAIN CONTROL VIEW (SIMPLIFIED) ----------------
class MusicControlView(View):
    """Simplified control view: Previous, Pause/Resume, Stop, Skip, Replay,
    Mute, Vol-, Vol+, Queue, Clear, Filters."""

    def __init__(self, player, ctx):
        super().__init__(timeout=None)  # persistent within session
        self.player = player
        self.ctx = ctx
        self.emoji = EmojiConfig()
        self._setup()

    def _setup(self):
        # Row 0: Playback
        self.add_item(Button(emoji="⏮️", style=discord.ButtonStyle.secondary,
                             custom_id="mc_previous", row=0, label="Previous"))
        self.add_item(Button(emoji="⏸️", style=discord.ButtonStyle.primary,
                             custom_id="mc_pause_resume", row=0, label="Pause/Resume"))
        self.add_item(Button(emoji="⏹️", style=discord.ButtonStyle.danger,
                             custom_id="mc_stop", row=0, label="Stop"))
        self.add_item(Button(emoji="⏭️", style=discord.ButtonStyle.secondary,
                             custom_id="mc_skip", row=0, label="Skip"))
        self.add_item(Button(emoji="🔄", style=discord.ButtonStyle.secondary,
                             custom_id="mc_replay", row=0, label="Replay"))

        # Row 1: Volume + Mute
        self.add_item(Button(emoji="🔇", style=discord.ButtonStyle.secondary,
                             custom_id="mc_mute", row=1, label="Mute"))
        self.add_item(Button(emoji="🔉", style=discord.ButtonStyle.primary,
                             custom_id="mc_vol_down", row=1, label="Vol -"))
        self.add_item(Button(emoji="🔊", style=discord.ButtonStyle.primary,
                             custom_id="mc_vol_up", row=1, label="Vol +"))

        # Row 2: Queue & Filters
        self.add_item(Button(emoji="📜", style=discord.ButtonStyle.secondary,
                             custom_id="mc_show_queue", row=2, label="Queue"))
        self.add_item(Button(emoji="🗑️", style=discord.ButtonStyle.danger,
                             custom_id="mc_clear_queue", row=2, label="Clear"))
        self.add_item(Button(emoji="🎛️", style=discord.ButtonStyle.success,
                             custom_id="mc_filter_menu", row=2, label="Filters"))

        for child in self.children:
            if isinstance(child, Button):
                child.callback = self._dispatch

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        vc = interaction.guild.voice_client
        if not vc:
            await interaction.response.send_message(
                embed=discord.Embed(title=f"{self.emoji.ERROR} Not Connected",
                                    description="I'm not in a voice channel.", color=0xFF0000),
                ephemeral=True)
            return False
        if interaction.user not in vc.channel.members:
            await interaction.response.send_message(
                embed=discord.Embed(title=f"{self.emoji.ERROR} Wrong Channel",
                                    description="Join my voice channel to control playback.",
                                    color=0xFF0000),
                ephemeral=True)
            return False
        return True

    async def _dispatch(self, interaction: discord.Interaction):
        cid = interaction.data["custom_id"].replace("mc_", "")
        handlers = {
            "previous": self._previous,
            "pause_resume": self._pause_resume,
            "stop": self._stop,
            "skip": self._skip,
            "replay": self._replay,
            "mute": self._mute,
            "vol_down": self._vol_down,
            "vol_up": self._vol_up,
            "show_queue": self._show_queue,
            "clear_queue": self._clear_queue,
            "filter_menu": self._filter_menu,
        }
        handler = handlers.get(cid)
        if not handler:
            if not interaction.response.is_done():
                await interaction.response.send_message("Unknown action.", ephemeral=True)
            return
        try:
            await handler(interaction)
        except Exception as e:
            print(f"[Button:{cid}] {e}")
            if not interaction.response.is_done():
                try:
                    await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
                except Exception:
                    pass

    # -------- handlers --------
    async def _previous(self, interaction):
        vc = interaction.guild.voice_client
        hist = track_histories.get(interaction.guild.id, [])
        if not hist:
            return await interaction.response.send_message(
                embed=discord.Embed(title="❌ No History", color=0xFF0000), ephemeral=True)
        prev = hist.pop()
        if len(hist) > 1:
            hist.pop()  # drop current
        await vc.play(prev)
        await interaction.response.send_message(
            embed=discord.Embed(title="⏮️ Previous", description=f"**{prev.title}**", color=0x1DB954),
            ephemeral=True)

    async def _pause_resume(self, interaction):
        vc = interaction.guild.voice_client
        if not vc or (not vc.playing and not vc.paused):
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        if vc.paused:
            await vc.pause(False)
            await interaction.response.send_message("▶️ Resumed.", ephemeral=True)
        else:
            await vc.pause(True)
            await interaction.response.send_message("⏸️ Paused.", ephemeral=True)

    async def _stop(self, interaction):
        vc = interaction.guild.voice_client
        gid = interaction.guild.id
        msg = active_player_messages.pop(gid, None)
        if msg:
            try: await msg.delete()
            except Exception: pass
        if vc:
            vc.queue.clear()
            await vc.disconnect()
        await interaction.response.send_message("⏹️ Stopped.", ephemeral=True)

    async def _skip(self, interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.playing:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        await vc.stop()
        await interaction.response.send_message("⏭️ Skipped.", ephemeral=True)

    async def _replay(self, interaction):
        vc = interaction.guild.voice_client
        if not vc or not vc.playing:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        await vc.seek(0)
        await interaction.response.send_message("🔄 Replaying.", ephemeral=True)

    async def _mute(self, interaction):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Not connected.", ephemeral=True)
        if not hasattr(vc, "_pre_mute_vol"):
            vc._pre_mute_vol = vc.volume
            await vc.set_volume(0)
            await interaction.response.send_message("🔇 Muted.", ephemeral=True)
        else:
            await vc.set_volume(vc._pre_mute_vol)
            delattr(vc, "_pre_mute_vol")
            await interaction.response.send_message("🔊 Unmuted.", ephemeral=True)

    async def _vol_down(self, interaction):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Not connected.", ephemeral=True)
        new = max(0, vc.volume - 20)
        await vc.set_volume(new)
        await interaction.response.send_message(f"🔉 Volume: {new}%", ephemeral=True)

    async def _vol_up(self, interaction):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Not connected.", ephemeral=True)
        new = min(200, vc.volume + 20)
        await vc.set_volume(new)
        await interaction.response.send_message(f"🔊 Volume: {new}%", ephemeral=True)

    async def _show_queue(self, interaction):
        vc = interaction.guild.voice_client
        if not vc or vc.queue.is_empty:
            return await interaction.response.send_message("📜 Queue empty.", ephemeral=True)
        tracks = list(vc.queue)[:10]
        txt = "\n".join(f"`{i+1}.` **{t.title[:45]}**" for i, t in enumerate(tracks))
        embed = discord.Embed(title="📜 Queue", description=txt, color=0x1DB954)
        if len(vc.queue) > 10:
            embed.set_footer(text=f"+{len(vc.queue)-10} more")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _clear_queue(self, interaction):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Not connected.", ephemeral=True)
        n = len(vc.queue)
        vc.queue.clear()
        await interaction.response.send_message(f"🗑️ Cleared {n} tracks.", ephemeral=True)

    async def _filter_menu(self, interaction):
        vc = interaction.guild.voice_client
        if not vc:
            return await interaction.response.send_message("❌ Not connected.", ephemeral=True)
        await interaction.response.send_message(
            embed=discord.Embed(title="🎛️ Audio Filters", description="Pick a filter:", color=0x1DB954),
            view=FilterSelectView(vc, self.ctx),
            ephemeral=True)


# ---------------- MUSIC COG ----------------
class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.emoji = EmojiConfig()
        self.inactivity_timeout = 120

    async def cog_load(self):
        await self.connect_nodes()
        asyncio.create_task(self.monitor_inactivity())

    async def connect_nodes(self):
        try:
            uri = pwd = None
            try:
                with open('bot_config.json', 'r') as f:
                    cfg = json.load(f)
                    uri = cfg.get('lavalink_uri') or os.environ.get("LAVALINK_URI")
                    pwd = cfg.get('lavalink_password') or os.environ.get("LAVALINK_PASSWORD")
            except FileNotFoundError:
                uri = os.environ.get("LAVALINK_URI")
                pwd = os.environ.get("LAVALINK_PASSWORD")

            if not uri or not pwd:
                print("⚠️ Using default Lavalink node")
                uri = "https://lava-v4.ajieblogs.eu.org:443/"
                pwd = "https://dsc.gg/ajidevserver"

            nodes = [wavelink.Node(uri=uri, password=pwd)]
            await wavelink.Pool.connect(nodes=nodes, client=self.client, cache_capacity=None)
            print("🎵 Lavalink connected")
        except Exception as e:
            print(f"❌ Lavalink failed: {e}")

    async def monitor_inactivity(self):
        while True:
            await asyncio.sleep(60)

    async def auto_delete(self, msg, delay):
        await asyncio.sleep(delay)
        try:
            await msg.delete()
        except Exception:
            pass

    async def log_track_play(self, ctx, track):
        try:
            await self.client.music_db.register_server(ctx.guild.id, ctx.guild.name)
            if ctx.author.voice and ctx.author.voice.channel:
                await self.client.music_db.register_voice_channel(
                    ctx.author.voice.channel.id, ctx.guild.id, ctx.author.voice.channel.name)
                src = "youtube"
                if "spotify" in track.uri.lower(): src = "spotify"
                elif "soundcloud" in track.uri.lower(): src = "soundcloud"
                await self.client.music_db.log_music_play(
                    server_id=ctx.guild.id,
                    channel_id=ctx.author.voice.channel.id,
                    user_id=ctx.author.id, user_name=str(ctx.author),
                    track_title=track.title, track_author=track.author,
                    track_uri=track.uri, track_duration=track.length // 1000,
                    track_source=src)
        except Exception as e:
            print(f"DB log err: {e}")

    async def log_search(self, ctx, query, count):
        try:
            await self.client.music_db.register_server(ctx.guild.id, ctx.guild.name)
            await self.client.music_db.log_search(
                server_id=ctx.guild.id, user_id=ctx.author.id,
                user_name=str(ctx.author), search_query=query, results_count=count)
        except Exception as e:
            print(f"DB search err: {e}")

    # ---------- PLAYER EMBED ----------
    async def display_player_embed(self, player, track, ctx, autoplay=False):
        try:
            gid = ctx.guild.id
            old = active_player_messages.pop(gid, None)
            if old:
                try: await old.delete()
                except Exception: pass

            sec = track.length // 1000
            duration = f"0{sec // 60}:{sec % 60:02d}" if sec < 600 else f"{sec // 60}:{sec % 60:02d}"

            if "spotify" in track.uri.lower():
                src_emoji, src_name = self.emoji.SPOTIFY, "Spotify"
            elif "youtube" in track.uri.lower():
                src_emoji, src_name = self.emoji.YOUTUBE, "YouTube"
            elif "soundcloud" in track.uri.lower():
                src_emoji, src_name = self.emoji.SOUNDCLOUD, "SoundCloud"
            else:
                src_emoji, src_name = self.emoji.MUSICAL_NOTE, "Unknown"

            embed = discord.Embed(
                title=f"{self.emoji.MUSICAL_NOTES} Now Playing",
                color=0x1DB954)
            embed.add_field(name=f"{self.emoji.MUSICAL_NOTE} Track",
                            value=f"**{track.title[:60]}**", inline=False)
            embed.add_field(name=f"{self.emoji.MICROPHONE} Artist",
                            value=f"**{track.author[:40]}**", inline=True)
            embed.add_field(name=f"{self.emoji.CLOCK} Duration",
                            value=f"**{duration}**", inline=True)
            embed.add_field(name=f"{self.emoji.QUALITY} Quality",
                            value="**384kbps**", inline=True)
            embed.add_field(name=f"{self.emoji.RADIO} Source",
                            value=f"{src_emoji} **{src_name}**", inline=True)
            embed.add_field(name=f"{self.emoji.VOLUME_HIGH} Volume",
                            value=f"**{player.volume}%**", inline=True)

            if track.artwork:
                embed.set_image(url=track.artwork)

            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url)

            msg = await ctx.send(embed=embed, view=MusicControlView(player, ctx))
            active_player_messages[gid] = msg
            await self.log_track_play(ctx, track)
        except Exception as e:
            print(f"display_player_embed err: {e}")

    # ---------- PLAY SOURCE ----------
    async def play_source(self, ctx, query):
        if not ctx.author.voice:
            return await ctx.send(embed=discord.Embed(
                title=f"{self.emoji.ERROR} Voice Required",
                description="Join a voice channel first.", color=0xFF0000))

        vc = ctx.voice_client
        if not vc:
            try:
                vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                await vc.set_volume(100)
            except Exception as e:
                return await ctx.send(embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Join Failed",
                    description=str(e), color=0xFF0000))

        vc.ctx = ctx

        if vc.playing and vc.channel != ctx.author.voice.channel:
            return await ctx.send(embed=discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Channel",
                description=f"Join {vc.channel.mention} to control music.", color=0xFF0000))

        if spotify_api and re.match(SPOTIFY_TRACK_REGEX, query):
            return await self._handle_spotify(ctx, vc, query, "track")
        if spotify_api and re.match(SPOTIFY_PLAYLIST_REGEX, query):
            return await self._handle_spotify(ctx, vc, query, "playlist")
        if spotify_api and re.match(SPOTIFY_ALBUM_REGEX, query):
            return await self._handle_spotify(ctx, vc, query, "album")

        search_msg = await ctx.send(embed=discord.Embed(
            title=f"{self.emoji.SEARCH} Searching...",
            description=f"`{query}`", color=0x1DB954))

        try:
            tracks = await wavelink.Playable.search(query)
        except Exception as e:
            return await search_msg.edit(embed=discord.Embed(
                title=f"{self.emoji.ERROR} Search Error",
                description=str(e), color=0xFF0000))

        if not tracks:
            return await search_msg.edit(embed=discord.Embed(
                title=f"{self.emoji.ERROR} No Results",
                description=f"Nothing found for `{query}`.", color=0xFF0000))

        count = len(tracks.tracks) if isinstance(tracks, wavelink.Playlist) else len(tracks)
        await self.log_search(ctx, query, count)

        if isinstance(tracks, wavelink.Playlist):
            await vc.queue.put_wait(tracks.tracks)
            embed = discord.Embed(
                title=f"{self.emoji.ADD} Playlist Queued",
                description=f"**{tracks.name}** — {len(tracks.tracks)} tracks",
                color=0x1DB954)
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await search_msg.edit(embed=embed)
            asyncio.create_task(self.auto_delete(search_msg, 5))
        else:
            track = tracks[0]
            await vc.queue.put_wait(track)
            embed = discord.Embed(
                title=f"{self.emoji.ADD} Added to Queue",
                description=f"**{track.title}**", color=0x1DB954)
            if track.artwork:
                embed.set_thumbnail(url=track.artwork)
            embed.set_footer(text=f"Requested by {ctx.author.display_name}")
            await search_msg.edit(embed=embed)
            asyncio.create_task(self.auto_delete(search_msg, 5))

        if not vc.playing and not vc.queue.is_empty:
            next_track = await vc.queue.get_wait()
            await vc.play(next_track)
            await self.display_player_embed(vc, next_track, ctx)

    async def _handle_spotify(self, ctx, vc, link, kind):
        try:
            if kind == "track":
                tid = re.search(SPOTIFY_TRACK_REGEX, link).group(1)
                info = await spotify_api.get_track(tid)
                title = info['name']
                author = ', '.join(a['name'] for a in info['artists'])
                results = await wavelink.Playable.search(f"{title} by {author}")
                if not results:
                    return await ctx.send("❌ Not available on YouTube.")
                track = results[0] if not isinstance(results, wavelink.Playlist) else results.tracks[0]
                await vc.queue.put_wait(track)
                if not vc.playing:
                    nt = await vc.queue.get_wait()
                    await vc.play(nt)
                    await self.display_player_embed(vc, nt, ctx)
                else:
                    await ctx.send(embed=discord.Embed(
                        title="🎧 Spotify Track Queued",
                        description=f"**{track.title}**", color=0x1DB954))

            elif kind in ("playlist", "album"):
                msg = await ctx.send("⏳ Loading Spotify content...")
                if kind == "playlist":
                    pid = re.search(SPOTIFY_PLAYLIST_REGEX, link).group(1)
                    data = await spotify_api.get_playlist(pid)
                    items = data.get("tracks", {}).get("items", [])
                    name = data.get("name", "Playlist")
                else:
                    aid = re.search(SPOTIFY_ALBUM_REGEX, link).group(1)
                    data = await spotify_api.get(f"albums/{aid}")
                    items = data.get("tracks", {}).get("items", [])
                    name = data.get("name", "Album")

                added = 0
                for it in items:
                    entry = it.get("track") or it
                    if not entry: continue
                    t = entry.get("name", "")
                    a = ', '.join(x['name'] for x in entry.get('artists', []))
                    try:
                        res = await wavelink.Playable.search(f"{t} {a}")
                        if res:
                            tr = res[0] if not isinstance(res, wavelink.Playlist) else res.tracks[0]
                            await vc.queue.put_wait(tr)
                            added += 1
                    except Exception:
                        continue
                await msg.edit(content=f"✅ Added **{added}** tracks from **{name}**")
                asyncio.create_task(self.auto_delete(msg, 5))
                if not vc.playing and not vc.queue.is_empty:
                    nt = await vc.queue.get_wait()
                    await vc.play(nt)
                    await self.display_player_embed(vc, nt, ctx)
        except Exception as e:
            await ctx.send(f"❌ Spotify error: {e}")

    # ---------- PREFIX COMMANDS ----------
    @commands.command(name="play", aliases=["p"])
    async def play(self, ctx, *, query: str):
        await self.play_source(ctx, query)

    @commands.command(name="join")
    async def join(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("❌ Join a voice channel first.")
        if ctx.voice_client:
            if ctx.voice_client.channel == ctx.author.voice.channel:
                return await ctx.send("✅ Already in your channel.")
            await ctx.voice_client.move_to(ctx.author.voice.channel)
            return await ctx.send(f"✅ Moved to {ctx.author.voice.channel.mention}")
        vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        vc.ctx = ctx
        await vc.set_volume(100)
        await ctx.send(f"✅ Joined {ctx.author.voice.channel.mention}")

    @commands.command(name="disconnect", aliases=["dc", "leave"])
    async def disconnect(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ Not connected.")
        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            return await ctx.send("❌ You must be in my voice channel.")
        await vc.disconnect()
        await ctx.send("👋 Disconnected.")

    @commands.command(name="pause")
    async def pause(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send("❌ Nothing playing.")
        await vc.pause(True)
        await ctx.send("⏸️ Paused.")

    @commands.command(name="resume")
    async def resume(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.paused:
            return await ctx.send("❌ Nothing paused.")
        await vc.pause(False)
        await ctx.send("▶️ Resumed.")

    @commands.command(name="skip")
    async def skip(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send("❌ Nothing playing.")
        await vc.stop()
        await ctx.send("⏭️ Skipped.")

    @commands.command(name="stop")
    async def stop(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ Not connected.")
        gid = ctx.guild.id
        msg = active_player_messages.pop(gid, None)
        if msg:
            try: await msg.delete()
            except Exception: pass
        vc.queue.clear()
        await vc.disconnect()
        await ctx.send("⏹️ Stopped and disconnected.")

    @commands.command(name="volume", aliases=["vol"])
    async def volume(self, ctx, vol: int):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ Not connected.")
        if not 1 <= vol <= 200:
            return await ctx.send("❌ Volume must be 1-200.")
        await vc.set_volume(vol)
        await ctx.send(f"🔊 Volume: **{vol}%**")

    @commands.command(name="queue", aliases=["q"])
    async def queue(self, ctx):
        vc = ctx.voice_client
        if not vc or vc.queue.is_empty:
            return await ctx.send("📜 Queue is empty.")
        tracks = list(vc.queue)[:10]
        embed = discord.Embed(title="📜 Queue", color=0x1DB954)
        for i, t in enumerate(tracks, 1):
            d = f"{t.length // 1000 // 60}:{t.length // 1000 % 60:02d}"
            embed.add_field(name=f"{i}. {t.title[:45]}",
                            value=f"**Artist:** {t.author[:30]} | **Duration:** {d}",
                            inline=False)
        if len(vc.queue) > 10:
            embed.set_footer(text=f"+{len(vc.queue) - 10} more")
        await ctx.send(embed=embed)

    @commands.command(name="clearqueue", aliases=["cq"])
    async def clearqueue(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ Not connected.")
        n = len(vc.queue)
        vc.queue.clear()
        await ctx.send(f"🗑️ Cleared **{n}** tracks.")

    @commands.command(name="shuffle")
    async def shuffle(self, ctx):
        vc = ctx.voice_client
        if not vc or vc.queue.is_empty:
            return await ctx.send("❌ Queue is empty.")
        q = list(vc.queue)
        random.shuffle(q)
        vc.queue.clear()
        for t in q:
            vc.queue.put(t)
        await ctx.send(f"🔀 Shuffled **{len(q)}** tracks.")

    @commands.command(name="loop")
    async def loop(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send("❌ Nothing playing.")
        vc.queue.mode = (wavelink.QueueMode.loop
                         if vc.queue.mode != wavelink.QueueMode.loop
                         else wavelink.QueueMode.normal)
        state = "enabled" if vc.queue.mode == wavelink.QueueMode.loop else "disabled"
        await ctx.send(f"🔁 Loop **{state}**")

    @commands.command(name="nowplaying", aliases=["np"])
    async def nowplaying(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send("❌ Nothing playing.")
        t = vc.current
        pos = vc.position / 1000
        length = t.length / 1000
        bar_len = 15
        fill = int(bar_len * (pos / length)) if length else 0
        bar = "█" * fill + "▬" * (bar_len - fill)
        embed = discord.Embed(title="🎶 Now Playing", color=0x1DB954)
        embed.add_field(name="Track", value=f"**{t.title}**", inline=False)
        embed.add_field(name="Artist", value=t.author, inline=True)
        embed.add_field(name="Progress",
                        value=f"`{int(pos // 60)}:{int(pos % 60):02d}` {bar} `{int(length // 60)}:{int(length % 60):02d}`",
                        inline=False)
        embed.add_field(name="Queue", value=f"`{len(vc.queue)}` tracks", inline=True)
        if t.artwork:
            embed.set_thumbnail(url=t.artwork)
        await ctx.send(embed=embed)

    @commands.command(name="seek")
    async def seek(self, ctx, seconds: int):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send("❌ Nothing playing.")
        if seconds < 0 or seconds * 1000 > vc.current.length:
            return await ctx.send("❌ Invalid position.")
        await vc.seek(seconds * 1000)
        await ctx.send(f"⏩ Seeked to {seconds}s.")

    @commands.command(name="replay")
    async def replay(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send("❌ Nothing playing.")
        await vc.seek(0)
        await ctx.send("🔄 Replaying.")

    @commands.command(name="previous", aliases=["prev"])
    async def previous(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send("❌ Not connected.")
        hist = track_histories.get(ctx.guild.id, [])
        if not hist:
            return await ctx.send("❌ No history.")
        prev = hist.pop()
        if len(hist) > 1:
            hist.pop()
        await vc.play(prev)
        await ctx.send(f"⏮️ Playing **{prev.title}**")

    @commands.command(name="autoplay")
    async def autoplay(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("❌ Join a voice channel.")
        vc = ctx.voice_client or await ctx.author.voice.channel.connect(cls=wavelink.Player)
        vc.ctx = ctx
        await vc.set_volume(100)
        vc._autoplay_only = True

        queries = ["lofi hip hop radio", "lofi study music", "chill lofi beats",
                   "latest hindi songs", "arijit singh songs", "sad songs english",
                   "top english songs", "arabic songs"]
        msg = await ctx.send("⏳ Loading autoplay queue...")
        added = 0
        for _ in range(20):
            try:
                r = await wavelink.Playable.search(random.choice(queries))
                if r:
                    tr = r[0] if not isinstance(r, wavelink.Playlist) else r.tracks[0]
                    await vc.queue.put_wait(tr)
                    added += 1
            except Exception:
                continue
        await msg.edit(content=f"✅ Autoplay started with **{added}** tracks.\nStop with `x!stop`.")
        if not vc.playing and not vc.queue.is_empty:
            nt = await vc.queue.get_wait()
            await vc.play(nt)

    @commands.command(name="filter")
    async def filter_cmd(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send("❌ Nothing playing.")
        await ctx.send(embed=discord.Embed(
            title="🎛️ Audio Filters", description="Choose a filter below:", color=0x1DB954),
            view=FilterSelectView(vc, ctx))

    # ---------- PLAYLISTS (user storage) ----------
    @commands.command(name="createplaylist")
    async def createplaylist(self, ctx, *, name: str):
        uid = ctx.author.id
        user_playlists.setdefault(uid, {})
        if name in user_playlists[uid]:
            return await ctx.send(f"❌ Playlist **{name}** already exists.")
        user_playlists[uid][name] = []
        await ctx.send(f"✅ Created playlist **{name}**")

    @commands.command(name="playlists")
    async def playlists(self, ctx):
        pls = user_playlists.get(ctx.author.id, {})
        if not pls:
            return await ctx.send("📂 You have no playlists.")
        embed = discord.Embed(title="📂 Your Playlists", color=0x1DB954)
        for n, t in list(pls.items())[:10]:
            embed.add_field(name=f"📁 {n}", value=f"`{len(t)}` tracks", inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="viewplaylist")
    async def viewplaylist(self, ctx, *, name: str):
        pls = user_playlists.get(ctx.author.id, {})
        if name not in pls:
            return await ctx.send("❌ Playlist not found.")
        tracks = pls[name]
        embed = discord.Embed(title=f"📁 {name}", color=0x1DB954)
        if not tracks:
            embed.description = "Empty playlist."
        else:
            for i, t in enumerate(tracks[:10], 1):
                embed.add_field(name=f"{i}. {t['title'][:40]}",
                                value=f"by {t['author'][:30]}", inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="deleteplaylist")
    async def deleteplaylist(self, ctx, *, name: str):
        pls = user_playlists.get(ctx.author.id, {})
        if name not in pls:
            return await ctx.send("❌ Playlist not found.")
        del pls[name]
        await ctx.send(f"✅ Deleted **{name}**")

    @commands.command(name="savequeue")
    async def savequeue(self, ctx, *, name: str):
        vc = ctx.voice_client
        if not vc or vc.queue.is_empty:
            return await ctx.send("❌ Queue is empty.")
        uid = ctx.author.id
        user_playlists.setdefault(uid, {})
        user_playlists[uid][name] = [
            {"title": t.title, "uri": t.uri, "author": t.author} for t in vc.queue]
        await ctx.send(f"✅ Saved **{len(vc.queue)}** tracks to **{name}**")

    @commands.command(name="playplaylist")
    async def playplaylist(self, ctx, *, name: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Join a voice channel.")
        pls = user_playlists.get(ctx.author.id, {})
        if name not in pls:
            return await ctx.send("❌ Playlist not found.")
        vc = ctx.voice_client or await ctx.author.voice.channel.connect(cls=wavelink.Player)
        vc.ctx = ctx
        await vc.set_volume(100)
        msg = await ctx.send(f"⏳ Loading **{name}**...")
        loaded = 0
        for entry in pls[name]:
            try:
                r = await wavelink.Playable.search(entry["uri"])
                if r:
                    tr = r[0] if not isinstance(r, wavelink.Playlist) else r.tracks[0]
                    await vc.queue.put_wait(tr)
                    loaded += 1
            except Exception:
                continue
        await msg.edit(content=f"✅ Loaded **{loaded}** tracks from **{name}**")
        if not vc.playing and not vc.queue.is_empty:
            nt = await vc.queue.get_wait()
            await vc.play(nt)
            await self.display_player_embed(vc, nt, ctx)

    @commands.command(name="search")
    async def search_cmd(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send("❌ Join a voice channel.")
        results = await wavelink.Playable.search(query, source="ytsearch")
        if not results:
            return await ctx.send("❌ No results.")
        top = results[:5] if not isinstance(results, wavelink.Playlist) else results.tracks[:5]
        embed = discord.Embed(title="🔍 Search Results", color=0x1DB954)
        for i, t in enumerate(top, 1):
            d = f"{t.length // 1000 // 60}:{t.length // 1000 % 60:02d}"
            embed.add_field(name=f"{i}. {t.title[:50]}",
                            value=f"**{t.author[:35]}** | {d}", inline=False)
        embed.set_footer(text="Use x!play <song> to play one")
        await ctx.send(embed=embed)

    # ---------- LISTENERS ----------
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        p, t = payload.player, payload.track
        if not p or not t:
            return
        track_histories.setdefault(p.guild.id, []).append(t)
        if len(track_histories[p.guild.id]) > 20:
            track_histories[p.guild.id].pop(0)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player:
            return

        # autoplay refill
        if getattr(player, "_autoplay_only", False) and len(player.queue) < 5:
            queries = ["lofi hip hop radio", "lofi study music", "chill lofi beats",
                       "latest hindi songs", "sad songs english", "top english songs"]
            for _ in range(10):
                try:
                    r = await wavelink.Playable.search(random.choice(queries))
                    if r:
                        tr = r[0] if not isinstance(r, wavelink.Playlist) else r.tracks[0]
                        await player.queue.put_wait(tr)
                except Exception:
                    continue

        # clear old embed
        if hasattr(player, "ctx") and player.ctx:
            gid = player.ctx.guild.id
            if not getattr(player, "_autoplay_only", False):
                old = active_player_messages.pop(gid, None)
                if old:
                    try: await old.delete()
                    except Exception: pass

        if not player.queue.is_empty:
            nxt = await player.queue.get_wait()
            await player.play(nxt)
            if hasattr(player, "ctx") and player.ctx:
                cog = player.client.get_cog("Music")
                if cog and not getattr(player, "_autoplay_only", False):
                    await cog.display_player_embed(player, nxt, player.ctx)
        else:
            ctx = getattr(player, "ctx", None)
            try:
                await player.disconnect()
            except Exception:
                pass
            if ctx:
                try:
                    await ctx.channel.send(embed=discord.Embed(
                        title="⏹️ Queue Ended",
                        description="All tracks finished.", color=0x1DB954))
                except Exception:
                    pass


# ---------------- HELP ----------------
class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = EmojiConfig()

    @commands.command(name="help", aliases=["h"])
    async def help_cmd(self, ctx):
        e = self.emoji
        embed = discord.Embed(
            title=f"{e.MUSICAL_NOTES} Music Bot Help",
            description="**Prefix:** `x!`",
            color=0x1DB954)
        embed.add_field(
            name="🎶 Playback",
            value=("`x!play <song/link>` - Play from YouTube/Spotify/SoundCloud\n"
                   "`x!search <query>` - Search YouTube\n"
                   "`x!pause` / `x!resume` - Pause/resume\n"
                   "`x!skip` - Skip current\n"
                   "`x!stop` - Stop and disconnect\n"
                   "`x!previous` - Play previous track\n"
                   "`x!replay` - Restart current track\n"
                   "`x!seek <seconds>` - Seek\n"
                   "`x!nowplaying` - Current track info"),
            inline=False)
        embed.add_field(
            name="🔊 Volume & Queue",
            value=("`x!volume <1-200>` - Set volume\n"
                   "`x!queue` - Show queue\n"
                   "`x!clearqueue` - Clear queue\n"
                   "`x!shuffle` - Shuffle queue\n"
                   "`x!loop` - Toggle loop"),
            inline=False)
        embed.add_field(
            name="🎛️ Filters & Playlists",
            value=("`x!filter` - Open filter menu\n"
                   "`x!autoplay` - 24/7 autoplay\n"
                   "`x!createplaylist <name>`\n"
                   "`x!savequeue <name>`\n"
                   "`x!playplaylist <name>`\n"
                   "`x!viewplaylist <name>`\n"
                   "`x!deleteplaylist <name>`\n"
                   "`x!playlists`"),
            inline=False)
        embed.add_field(
            name="🚪 Voice",
            value="`x!join` - Join your channel\n`x!disconnect` - Leave",
            inline=False)
        embed.set_footer(text="Enjoy the music! 🎵")
        await ctx.send(embed=embed)


# ---------------- BOT ----------------
intents = discord.Intents.all()


def load_bot_token():
    try:
        with open('bot_config.json', 'r') as f:
            cfg = json.load(f)
            tok = cfg.get('discord_token') or os.environ.get('DISCORD_TOKEN')
            if tok and tok.strip():
                return tok
    except FileNotFoundError:
        pass
    return os.environ.get('DISCORD_TOKEN')


class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="x!", intents=intents, help_command=None)
        self.session = None
        self.music_db = MusicDatabase()

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        try:
            await self.music_db.connect()
        except Exception as e:
            print(f"DB connect: {e}")

        await self.add_cog(Music(self))
        await self.add_cog(HelpCog(self))
        print("✅ Cogs loaded")

    async def close(self):
        if self.session:
            await self.session.close()
        try:
            await self.music_db.close()
        except Exception:
            pass
        await super().close()

    async def on_ready(self):
        print(f"✅ Logged in as {self.user} ({self.user.id})")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening,
                                      name="x!help | Music"),
            status=discord.Status.online)


bot = MusicBot()


def main():
    token = load_bot_token()
    if not token:
        print("❌ DISCORD_TOKEN not set (env or bot_config.json)")
        return
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Invalid token")
    except Exception as e:
        print(f"❌ Startup error: {e}")


if __name__ == "__main__":
    main()
