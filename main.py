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

# Try to install required packages
required_packages = [
    "discord.py",
    "wavelink",
    "Pillow",
    "aiohttp",
    "aiosqlite"
]

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

# Now import the modules
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

from music_database import MusicDatabase


# Custom emoji configuration
class EmojiConfig:
    def __init__(self):
        self.load_emojis()

    def load_emojis(self):
        """Load emojis from emoji_config.json"""
        try:
            with open('emoji_config.json', 'r', encoding='utf-8') as f:
                emoji_data = json.load(f)

            # Music Control Emojis
            self.PLAY = emoji_data['music_control']['play']
            self.PAUSE = emoji_data['music_control']['pause']
            self.RESUME = emoji_data['music_control']['resume']
            self.STOP = emoji_data['music_control']['stop']
            self.SKIP = emoji_data['music_control']['skip']
            self.PREVIOUS = emoji_data['music_control']['previous']
            self.REPEAT = emoji_data['music_control']['repeat']
            self.REPEAT_ONE = emoji_data['music_control']['repeat_one']
            self.SHUFFLE = emoji_data['music_control']['shuffle']

            # Volume Emojis
            self.VOLUME_UP = emoji_data['volume']['volume_up']
            self.VOLUME_DOWN = emoji_data['volume']['volume_down']
            self.VOLUME_MUTE = emoji_data['volume']['volume_mute']
            self.VOLUME_LOW = emoji_data['volume']['volume_low']
            self.VOLUME_HIGH = emoji_data['volume']['volume_high']

            # Status Emojis
            self.SUCCESS = emoji_data['status']['success']
            self.ERROR = emoji_data['status']['error']
            self.WARNING = emoji_data['status']['warning']
            self.INFO = emoji_data['status']['info']
            self.LOADING = emoji_data['status']['loading']
            self.SEARCH = emoji_data['status']['search']

            # Music Source Emojis
            self.SPOTIFY = emoji_data['music_sources']['spotify']
            self.YOUTUBE = emoji_data['music_sources']['youtube']
            self.SOUNDCLOUD = emoji_data['music_sources']['soundcloud']

            # Feature Emojis
            self.FILTER = emoji_data['features']['filter']
            self.EQUALIZER = emoji_data['features']['equalizer']
            self.HEADPHONES = emoji_data['features']['headphones']
            self.MICROPHONE = emoji_data['features']['microphone']
            self.MUSICAL_NOTE = emoji_data['features']['musical_note']
            self.MUSICAL_NOTES = emoji_data['features']['musical_notes']
            self.RADIO = emoji_data['features']['radio']
            self.STAR = emoji_data['features']['star']
            self.KEY = emoji_data['features']['key']
            self.QUALITY = emoji_data['features']['quality']

            # Platform Emojis
            self.YOUTUBE_PLATFORM = emoji_data['platforms']['youtube_platform']
            self.SOUNDCLOUD_PLATFORM = emoji_data['platforms']['soundcloud_platform']

            # Control Panel Emojis
            self.SETTINGS = emoji_data['control_panel']['settings']
            self.DASHBOARD = emoji_data['control_panel']['dashboard']
            self.QUEUE = emoji_data['control_panel']['queue']
            self.HISTORY = emoji_data['control_panel']['history']

            # Action Emojis
            self.ADD = emoji_data['actions']['add']
            self.REMOVE = emoji_data['actions']['remove']
            self.CLEAR = emoji_data['actions']['clear']
            self.DOWNLOAD = emoji_data['actions']['download']
            self.UPLOAD = emoji_data['actions']['upload']

            # Time Emojis
            self.CLOCK = emoji_data['time']['clock']
            self.HOURGLASS = emoji_data['time']['hourglass']
            self.TIMER = emoji_data['time']['timer']

            print("✅ Emojis loaded from emoji_config.json")
        except FileNotFoundError:
            print("⚠️ emoji_config.json not found, using default emojis")
            self.load_default_emojis()
        except Exception as e:
            print(f"⚠️ Error loading emojis: {e}, using defaults")
            self.load_default_emojis()

    def load_default_emojis(self):
        """Fallback to default Unicode emojis"""
        self.PLAY = "▶️"
        self.PAUSE = "⏸️"
        self.RESUME = "▶️"
        self.STOP = "⏹️"
        self.SKIP = "⏭️"
        self.PREVIOUS = "⏮️"
        self.REPEAT = "🔁"
        self.REPEAT_ONE = "🔂"
        self.SHUFFLE = "🔀"
        self.VOLUME_UP = "🔊"
        self.VOLUME_DOWN = "🔉"
        self.VOLUME_MUTE = "🔇"
        self.VOLUME_LOW = "🔈"
        self.VOLUME_HIGH = "🔊"
        self.SUCCESS = "✅"
        self.ERROR = "❌"
        self.WARNING = "⚠️"
        self.INFO = "ℹ️"
        self.LOADING = "⏳"
        self.SEARCH = "🔍"
        self.SPOTIFY = "🎧"
        self.YOUTUBE = "▶️"
        self.SOUNDCLOUD = "☁️"
        self.FILTER = "🎛️"
        self.EQUALIZER = "🎚️"
        self.HEADPHONES = "🎧"
        self.MICROPHONE = "🎤"
        self.MUSICAL_NOTE = "🎵"
        self.MUSICAL_NOTES = "🎶"
        self.RADIO = "📻"
        self.STAR = "⭐"
        self.KEY = "🔑"
        self.QUALITY = "💎"
        self.YOUTUBE_PLATFORM = "▶️"
        self.SOUNDCLOUD_PLATFORM = "☁️"
        self.SETTINGS = "⚙️"
        self.DASHBOARD = "📊"
        self.QUEUE = "📜"
        self.HISTORY = "📋"
        self.ADD = "➕"
        self.REMOVE = "➖"
        self.CLEAR = "🗑️"
        self.DOWNLOAD = "📥"
        self.UPLOAD = "📤"
        self.CLOCK = "🕒"
        self.HOURGLASS = "⏳"
        self.TIMER = "⏰"


# YouTube API Key Manager
class YouTubeAPIManager:
    def __init__(self, config_file="bot_config.json"):
        self.config_file = config_file
        self.api_key = None
        self.load_api_key()

    def load_api_key(self):
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.api_key = config.get('youtube_api_key') or os.environ.get('YOUTUBE_API_KEY')
        except FileNotFoundError:
            self.api_key = os.environ.get('YOUTUBE_API_KEY')
            if not self.api_key:
                print("⚠️ WARNING: YOUTUBE_API_KEY not set in environment variables")

    def save_config(self, config):
        try:
            existing_config = {}
            try:
                with open(self.config_file, 'r') as f:
                    existing_config = json.load(f)
            except FileNotFoundError:
                pass
            existing_config.update(config)
            with open(self.config_file, 'w') as f:
                json.dump(existing_config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def set_api_key(self, api_key):
        self.api_key = api_key
        self.save_config({'youtube_api_key': api_key})
        return True

    def get_api_key(self):
        return self.api_key

    def has_api_key(self):
        return bool(self.api_key and self.api_key.strip())


# Custom imports with fallbacks
try:
    from utils import Paginator, DescriptionEmbedPaginator
    from core import Cog, axon, Context
    from utils.Tools import *
except ImportError:
    class Paginator:
        def __init__(self, source, ctx):
            self.source = source
            self.ctx = ctx

        async def paginate(self):
            await self.ctx.send("Paginator not available - showing first page only")
            entries = self.source.entries[:10]
            embed = discord.Embed(title=self.source.title, description="\n".join(entries), color=self.source.color)
            await self.ctx.send(embed=embed)

    class DescriptionEmbedPaginator:
        def __init__(self, entries, title, description, per_page, color):
            self.entries = entries
            self.title = title
            self.description = description
            self.per_page = per_page
            self.color = color

    class Cog(commands.Cog):
        pass

    class axon(commands.Bot):
        pass

    class Context(commands.Context):
        pass

    def blacklist_check():
        def predicate(ctx):
            return True
        return commands.check(predicate)

    def ignore_check():
        def predicate(ctx):
            return True
        return commands.check(predicate)


# Initialize track histories and YouTube API manager
track_histories = {}
youtube_api = YouTubeAPIManager()

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
        auth_value = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode('utf-8')).decode('utf-8')
        headers = {"Authorization": f"Basic {auth_value}"}
        data = {"grant_type": "client_credentials"}
        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, headers=headers, data=data) as response:
                text = await response.text()
                if response.status != 200:
                    raise Exception(f"Failed to fetch token: {response.status}, response: {text}")
                result = await response.json()
                self.token = result.get("access_token")

    async def get(self, endpoint, params=None):
        retries = 2
        for attempt in range(retries):
            if not self.token or attempt > 0:
                await self.get_token()

            url = f"{self.BASE_URL}/{endpoint}"
            headers = {"Authorization": f"Bearer {self.token}"}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, params=params) as response:
                    if response.status == 401 and attempt < retries - 1:
                        continue
                    elif response.status != 200:
                        raise Exception(f"Failed to fetch data from Spotify: {response.status}")
                    return await response.json()
        raise Exception("Exceeded max retries to fetch Spotify data")

    async def get_track(self, track_id):
        return await self.get(f"tracks/{track_id}")

    async def get_playlist(self, playlist_id):
        return await self.get(f"playlists/{playlist_id}")


# Load Spotify credentials
try:
    with open('bot_config.json', 'r') as f:
        config = json.load(f)
        spotify_client_id = config.get('spotify_client_id') or os.environ.get("SPOTIFY_CLIENT_ID")
        spotify_client_secret = config.get('spotify_client_secret') or os.environ.get("SPOTIFY_CLIENT_SECRET")
except FileNotFoundError:
    spotify_client_id = os.environ.get("SPOTIFY_CLIENT_ID")
    spotify_client_secret = os.environ.get("SPOTIFY_CLIENT_SECRET")

if not spotify_client_id or not spotify_client_secret:
    print("⚠️ WARNING: SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET not set")
    spotify_api = None
else:
    spotify_api = SpotifyAPI(client_id=spotify_client_id, client_secret=spotify_client_secret)
    print("✅ Spotify API initialized successfully")


# Store active player messages
active_player_messages = {}

# Vote system configuration
OWNER_ID = 1007467674143571988


class UltraAdvancedMusicControlView(View):
    def __init__(self, player, ctx):
        super().__init__(timeout=300)
        self.player = player
        self.ctx = ctx
        self.emoji = EmojiConfig()
        self.setup_buttons()

    def setup_buttons(self):
        # Row 1: Main Playback Controls
        self.add_item(Button(emoji="⏮️", style=discord.ButtonStyle.secondary, custom_id="music_previous", row=0, label="Previous"))
        self.add_item(Button(emoji="⏸️", style=discord.ButtonStyle.primary, custom_id="music_pause_resume", row=0, label="Pause/Resume"))
        self.add_item(Button(emoji="⏹️", style=discord.ButtonStyle.danger, custom_id="music_stop", row=0, label="Stop"))
        self.add_item(Button(emoji="⏭️", style=discord.ButtonStyle.secondary, custom_id="music_skip", row=0, label="Skip"))
        self.add_item(Button(emoji="🔄", style=discord.ButtonStyle.secondary, custom_id="music_replay", row=0, label="Replay"))

        # Row 2: Seek & Speed Controls
        self.add_item(Button(emoji="⏪", style=discord.ButtonStyle.secondary, custom_id="music_rewind", row=1, label="-30s"))
        self.add_item(Button(emoji="🐌", style=discord.ButtonStyle.secondary, custom_id="music_speed_075", row=1, label="0.75x"))
        self.add_item(Button(emoji="⏲️", style=discord.ButtonStyle.primary, custom_id="music_seek_menu", row=1, label="Seek"))
        self.add_item(Button(emoji="⚡", style=discord.ButtonStyle.secondary, custom_id="music_speed_125", row=1, label="1.25x"))
        self.add_item(Button(emoji="⏩", style=discord.ButtonStyle.secondary, custom_id="music_forward", row=1, label="+30s"))

        # Row 3: Volume & Loop Controls
        self.add_item(Button(emoji="🔇", style=discord.ButtonStyle.secondary, custom_id="music_mute", row=2, label="Mute"))
        self.add_item(Button(emoji="🔉", style=discord.ButtonStyle.primary, custom_id="music_vol_down", row=2, label="Vol -"))
        self.add_item(Button(emoji="🔁", style=discord.ButtonStyle.success, custom_id="music_loop", row=2, label="Loop Queue"))
        self.add_item(Button(emoji="🔊", style=discord.ButtonStyle.primary, custom_id="music_vol_up", row=2, label="Vol +"))
        self.add_item(Button(emoji="🔂", style=discord.ButtonStyle.success, custom_id="music_loop_track", row=2, label="Loop Track"))

        # Row 4: Queue Management
        self.add_item(Button(emoji="📜", style=discord.ButtonStyle.secondary, custom_id="music_show_queue", row=3, label="Queue"))
        self.add_item(Button(emoji="🔀", style=discord.ButtonStyle.success, custom_id="music_shuffle", row=3, label="Shuffle"))
        self.add_item(Button(emoji="🎵", style=discord.ButtonStyle.primary, custom_id="music_add_track", row=3, label="Add Track"))
        self.add_item(Button(emoji="💾", style=discord.ButtonStyle.success, custom_id="music_save_playlist", row=3, label="Save"))
        self.add_item(Button(emoji="🗑️", style=discord.ButtonStyle.danger, custom_id="music_clear_queue", row=3, label="Clear"))

        # Row 5: Effects & Info
        self.add_item(Button(emoji="🎛️", style=discord.ButtonStyle.secondary, custom_id="music_filter_menu", row=4, label="Filters"))
        self.add_item(Button(emoji="🧹", style=discord.ButtonStyle.danger, custom_id="music_clear_effects", row=4, label="Clear Effects"))
        self.add_item(Button(emoji="📊", style=discord.ButtonStyle.primary, custom_id="music_stats", row=4, label="Stats"))
        self.add_item(Button(emoji="💎", style=discord.ButtonStyle.success, custom_id="music_quality_info", row=4, label="Quality"))
        self.add_item(Button(emoji="🔧", style=discord.ButtonStyle.secondary, custom_id="music_settings", row=4, label="Settings"))

        # Attach callbacks to all buttons
        for item in self.children:
            if isinstance(item, Button):
                item.callback = self.button_callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not self.ctx.voice_client:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Player Not Active",
                    description="I'm not currently in a voice channel.",
                    color=0xFF0000
                ), ephemeral=True
            )
            return False
        if interaction.user in self.ctx.voice_client.channel.members:
            return True
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.ERROR} Permission Denied",
                description="Only members in the same voice channel can control the player.",
                color=0xFF0000
            ), ephemeral=True
        )
        return False

    async def button_callback(self, interaction: discord.Interaction):
        button_id = interaction.data["custom_id"].replace("music_", "")

        actions = {
            "pause_resume": self.pause_resume,
            "skip": self.skip,
            "previous": self.previous,
            "rewind": self.rewind,
            "forward": self.forward,
            "loop": self.loop,
            "shuffle": self.shuffle,
            "vol_down": self.volume_down,
            "vol_up": self.volume_up,
            "filter_menu": self.filter_menu,
            "show_queue": self.show_queue,
            "clear_queue": self.clear_queue,
            "save_playlist": self.save_playlist,
            "stop": self.stop,
            "speed_075": self.speed_075,
            "speed_125": self.speed_125,
            "loop_track": self.loop_track,
            "replay": self.replay,
            "stats": self.stats,
            "quality_info": self.quality_info,
            "mute": self.mute,
            "seek_menu": self.seek_menu,
            "add_track": self.add_track,
            "settings": self.settings,
            "clear_effects": self.clear_effects
        }

        if button_id in actions:
            try:
                await actions[button_id](interaction)
            except Exception as e:
                print(f"Button callback error ({button_id}): {e}")
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=discord.Embed(
                            title=f"{self.emoji.ERROR} Error",
                            description=f"An error occurred: {str(e)}",
                            color=0xFF0000
                        ), ephemeral=True
                    )

    async def pause_resume(self, interaction: discord.Interaction):
        if not self.player.playing and not self.player.paused:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000
                ), ephemeral=True
            )
            return
        if self.player.paused:
            await self.player.pause(False)
            embed = discord.Embed(
                title=f"{self.emoji.SUCCESS} Playback Resumed",
                description=f"**{self.player.current.title}** has been resumed!",
                color=0x1DB954
            )
        else:
            await self.player.pause(True)
            embed = discord.Embed(
                title=f"{self.emoji.PAUSE} Playback Paused",
                description=f"**{self.player.current.title}** has been paused!",
                color=0xFFA500
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def skip(self, interaction: discord.Interaction):
        if not self.player.playing:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000
                ), ephemeral=True
            )
            return
        await self.player.stop()
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.SKIP} Track Skipped",
                description=f"Skipped by **{interaction.user.display_name}**!",
                color=0x1DB954
            ), ephemeral=True
        )

    async def previous(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        if guild_id in track_histories and track_histories[guild_id]:
            previous_track = track_histories[guild_id].pop()
            await self.player.play(previous_track)
            embed = discord.Embed(
                title=f"{self.emoji.PREVIOUS} Playing Previous Track",
                description=f"**{previous_track.title}**",
                color=0x1DB954
            )
        else:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Previous Track",
                description="There's no previous track in history!",
                color=0xFF0000
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def rewind(self, interaction: discord.Interaction):
        if not self.player.playing:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000
                ), ephemeral=True
            )
            return
        new_position = max(0, self.player.position - 30000)
        await self.player.seek(new_position)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⏪ Rewinded",
                description=f"Rewinded 30 seconds in **{self.player.current.title}**!",
                color=0x1DB954
            ), ephemeral=True
        )

    async def forward(self, interaction: discord.Interaction):
        if not self.player.playing:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000
                ), ephemeral=True
            )
            return
        new_position = min(self.player.current.length, self.player.position + 30000)
        await self.player.seek(new_position)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⏩ Forwarded",
                description=f"Forwarded 30 seconds in **{self.player.current.title}**!",
                color=0x1DB954
            ), ephemeral=True
        )

    async def loop(self, interaction: discord.Interaction):
        self.player.queue.mode = wavelink.QueueMode.loop if self.player.queue.mode != wavelink.QueueMode.loop else wavelink.QueueMode.normal
        mode = "enabled" if self.player.queue.mode == wavelink.QueueMode.loop else "disabled"
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.REPEAT} Loop {mode.title()}",
                description=f"Loop mode has been **{mode}**!",
                color=0x1DB954 if mode == "enabled" else 0xFFA500
            ), ephemeral=True
        )

    async def shuffle(self, interaction: discord.Interaction):
        if self.player.queue and not self.player.queue.is_empty:
            # Convert queue to list, shuffle, then rebuild
            queue_list = list(self.player.queue)
            random.shuffle(queue_list)
            self.player.queue.clear()
            for track in queue_list:
                self.player.queue.put(track)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.SHUFFLE} Queue Shuffled",
                    description=f"Queue has been shuffled!",
                    color=0x1DB954
                ), ephemeral=True
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Queue Empty",
                    description="The queue is currently empty!",
                    color=0xFF0000
                ), ephemeral=True
            )

    async def volume_down(self, interaction: discord.Interaction):
        current_volume = self.player.volume
        new_volume = max(0, current_volume - 20)
        await self.player.set_volume(new_volume)
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.VOLUME_DOWN} Volume Decreased",
                description=f"Volume: `{current_volume}%` → `{new_volume}%`",
                color=0x1DB954
            ), ephemeral=True
        )

    async def volume_up(self, interaction: discord.Interaction):
        current_volume = self.player.volume
        new_volume = min(200, current_volume + 20)
        await self.player.set_volume(new_volume)
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.VOLUME_UP} Volume Increased",
                description=f"Volume: `{current_volume}%` → `{new_volume}%`",
                color=0x1DB954
            ), ephemeral=True
        )

    async def filter_menu(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"{self.emoji.FILTER} Audio Filters",
                description="Select an audio filter to apply:",
                color=0x1DB954
            ),
            view=FilterSelectView(self.player, self.ctx),
            ephemeral=True
        )

    async def show_queue(self, interaction: discord.Interaction):
        if not self.player.queue or self.player.queue.is_empty:
            embed = discord.Embed(
                title=f"{self.emoji.QUEUE} Queue Empty",
                description="The queue is currently empty!",
                color=0xFFA500
            )
        else:
            tracks = list(self.player.queue)[:10]
            queue_text = "\n".join([f"`{i+1}.` **{track.title[:40]}**" for i, track in enumerate(tracks)])
            embed = discord.Embed(
                title=f"{self.emoji.QUEUE} Current Queue",
                description=queue_text,
                color=0x1DB954
            )
            if len(self.player.queue) > 10:
                embed.set_footer(text=f"And {len(self.player.queue) - 10} more tracks...")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def clear_queue(self, interaction: discord.Interaction):
        if self.player.queue.is_empty:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.WARNING} Queue Already Empty",
                    description="The queue is already empty!",
                    color=0xFFA500
                ), ephemeral=True
            )
        else:
            queue_count = len(self.player.queue)
            self.player.queue.clear()
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.CLEAR} Queue Cleared",
                    description=f"Cleared `{queue_count}` tracks!",
                    color=0x1DB954
                ), ephemeral=True
            )

    async def save_playlist(self, interaction: discord.Interaction):
        if self.player.queue.is_empty:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Queue Empty",
                    description="There are no tracks in the queue to save!",
                    color=0xFF0000
                ), ephemeral=True
            )
            return
        await interaction.response.send_message(
            embed=discord.Embed(
                title="💾 Save Playlist",
                description="Save the current queue as a playlist:",
                color=0x1DB954
            ),
            view=PlaylistSaveView(self.player.queue, interaction.user.id),
            ephemeral=True
        )

    async def stop(self, interaction: discord.Interaction):
        if self.player:
            guild_id = interaction.guild.id
            if guild_id in active_player_messages:
                try:
                    await active_player_messages[guild_id].delete()
                    del active_player_messages[guild_id]
                except:
                    pass
            await self.player.disconnect()
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.STOP} Playback Stopped",
                    description="Music playback has been stopped!",
                    color=0x1DB954
                )
            )
        else:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} Not Connected",
                    description="I'm not connected to any voice channel!",
                    color=0xFF0000
                )
            )

    async def speed_075(self, interaction: discord.Interaction):
        filters = wavelink.Filters()
        filters.timescale.set(speed=0.75)
        await self.player.set_filters(filters)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🐌 Playback Speed Set",
                description="Playback speed set to **0.75x**",
                color=0x1DB954
            ), ephemeral=True
        )

    async def speed_125(self, interaction: discord.Interaction):
        filters = wavelink.Filters()
        filters.timescale.set(speed=1.25)
        await self.player.set_filters(filters)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⚡ Playback Speed Set",
                description="Playback speed set to **1.25x**",
                color=0x1DB954
            ), ephemeral=True
        )

    async def clear_effects(self, interaction: discord.Interaction):
        filters = wavelink.Filters()
        await self.player.set_filters(filters)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🧹 All Effects Cleared",
                description="All audio filters and effects have been removed!\nPlayback restored to normal speed and quality.",
                color=0x1DB954
            ), ephemeral=True
        )

    async def loop_track(self, interaction: discord.Interaction):
        self.player.queue.mode = wavelink.QueueMode.loop_all if self.player.queue.mode != wavelink.QueueMode.loop_all else wavelink.QueueMode.normal
        mode = "enabled" if self.player.queue.mode == wavelink.QueueMode.loop_all else "disabled"
        await interaction.response.send_message(
            embed=discord.Embed(
                title=f"🔂 Track Loop {mode.title()}",
                description=f"Current track loop has been **{mode}**!",
                color=0x1DB954 if mode == "enabled" else 0xFFA500
            ), ephemeral=True
        )

    async def replay(self, interaction: discord.Interaction):
        if not self.player.playing:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Music Playing",
                    description="There's no music currently playing!",
                    color=0xFF0000
                ), ephemeral=True
            )
            return
        await self.player.seek(0)
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🔄 Replaying Track",
                description=f"Restarting **{self.player.current.title}**!",
                color=0x1DB954
            ), ephemeral=True
        )

    async def stats(self, interaction: discord.Interaction):
        track = self.player.current
        if not track:
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{self.emoji.ERROR} No Track",
                    description="No track is currently playing!",
                    color=0xFF0000
                ), ephemeral=True
            )
            return
        position = self.player.position / 1000
        length = track.length / 1000
        percentage = (position / length * 100) if length > 0 else 0

        await interaction.response.send_message(
            embed=discord.Embed(
                title="📊 Player Statistics",
                description=f"**Now Playing:** {track.title}\n"
                           f"**Progress:** {percentage:.1f}%\n"
                           f"**Volume:** {self.player.volume}%\n"
                           f"**Queue:** {len(self.player.queue)} tracks\n"
                           f"**Quality:** 384kbps Ultra HD",
                color=0x1DB954
            ), ephemeral=True
        )

    async def quality_info(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="💎 Ultra HD Audio Quality",
                description="**Current Quality:** 384kbps Ultra HD\n"
                           "**Bitrate:** 384 kbps\n"
                           "**Sample Rate:** 48 kHz\n"
                           "**Channels:** Stereo (2.0)\n"
                           "**Codec:** Opus/AAC\n"
                           "**Streaming:** Low Latency",
                color=0x1DB954
            ), ephemeral=True
        )

    async def mute(self, interaction: discord.Interaction):
        if not hasattr(self.player, '_pre_mute_volume'):
            self.player._pre_mute_volume = self.player.volume
            await self.player.set_volume(0)
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔇 Muted",
                    description="Player has been muted!",
                    color=0x1DB954
                ), ephemeral=True
            )
        else:
            await self.player.set_volume(self.player._pre_mute_volume)
            delattr(self.player, '_pre_mute_volume')
            await interaction.response.send_message(
                embed=discord.Embed(
                    title="🔊 Unmuted",
                    description="Player has been unmuted!",
                    color=0x1DB954
                ), ephemeral=True
            )

    async def seek_menu(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="⏲️ Seek Controls",
                description="Use the ⏪ (30s back) and ⏩ (30s forward) buttons to seek!",
                color=0x1DB954
            ), ephemeral=True
        )

    async def add_track(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🎵 Add Track",
                description="Use `/play <song name>` or `x!play <song name>` to add tracks!",
                color=0x1DB954
            ), ephemeral=True
        )

    async def settings(self, interaction: discord.Interaction):
        await interaction.response.send_message(
            embed=discord.Embed(
                title="🔧 Player Settings",
                description="**Current Configuration:**\n"
                           f"• Volume: {self.player.volume}%\n"
                           f"• Loop: {self.player.queue.mode.name}\n"
                           f"• Quality: 384kbps Ultra HD\n"
                           f"• Queue Size: {len(self.player.queue)} tracks",
                color=0x1DB954
            ), ephemeral=True
        )


class FilterSelectView(View):
    def __init__(self, player, ctx):
        super().__init__(timeout=60)
        self.player = player
        self.ctx = ctx
        self.emoji = EmojiConfig()

    @discord.ui.select(
        placeholder="🎛️ Select Audio Filter...",
        options=[
            discord.SelectOption(label="Nightcore", description="Increase pitch and speed", emoji="🎵", value="nightcore"),
            discord.SelectOption(label="Bass Boost", description="Enhance bass frequencies", emoji="🔊", value="bassboost"),
            discord.SelectOption(label="Vaporwave", description="Slow down and pitch down", emoji="🌴", value="vaporwave"),
            discord.SelectOption(label="Karaoke", description="Remove vocal frequencies", emoji="🎤", value="karaoke"),
            discord.SelectOption(label="Tremolo", description="Amplitude modulation effect", emoji="🎛️", value="tremolo"),
            discord.SelectOption(label="Vibrato", description="Pitch modulation effect", emoji="🎶", value="vibrato"),
            discord.SelectOption(label="Rotation", description="3D rotation effect", emoji="🔄", value="rotation"),
            discord.SelectOption(label="Distortion", description="Add distortion effect", emoji="🎸", value="distortion"),
            discord.SelectOption(label="Clear Filters", description="Remove all filters", emoji="🧹", value="clear"),
        ]
    )
    async def select_filter(self, interaction: discord.Interaction, select: Select):
        filter_name = select.values[0]
        filters = wavelink.Filters()

        if filter_name == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.2, rate=1)
            description = "Applied Nightcore filter - increased pitch and speed!"
        elif filter_name == "bassboost":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.8}, {"band": 1, "gain": 0.6}, 
                {"band": 2, "gain": 0.4}, {"band": 3, "gain": 0.2},
                {"band": 4, "gain": 0.1}, {"band": 5, "gain": 0.0}
            ])
            description = "Applied Bass Boost - enhanced low frequencies!"
        elif filter_name == "vaporwave":
            filters.timescale.set(rate=0.8, pitch=0.9)
            description = "Applied Vaporwave filter - slowed down and pitched down!"
        elif filter_name == "karaoke":
            filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
            description = "Applied Karaoke filter - vocal removal enabled!"
        elif filter_name == "tremolo":
            filters.tremolo.set(depth=0.5, frequency=10.0)
            description = "Applied Tremolo effect - amplitude modulation!"
        elif filter_name == "vibrato":
            filters.vibrato.set(depth=0.5, frequency=5.0)
            description = "Applied Vibrato effect - pitch modulation!"
        elif filter_name == "rotation":
            filters.rotation.set(rotation_hz=0.2)
            description = "Applied Rotation effect - 3D audio rotation!"
        elif filter_name == "distortion":
            filters.distortion.set(sin_offset=0.0, sin_scale=1.0, cos_offset=0.0, 
                                   cos_scale=1.0, tan_offset=0.0, tan_scale=1.0, 
                                   offset=0.0, scale=1.0)
            description = "Applied Distortion effect - gritty sound!"
        elif filter_name == "clear":
            filters = wavelink.Filters()
            description = "All audio filters have been cleared!"
        else:
            description = "Unknown filter"

        await self.player.set_filters(filters)

        embed = discord.Embed(
            title=f"{self.emoji.FILTER} Filter Applied",
            description=description,
            color=0x1DB954
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class EqualizerView(View):
    def __init__(self, player, ctx):
        super().__init__(timeout=60)
        self.player = player
        self.ctx = ctx
        self.emoji = EmojiConfig()

    @discord.ui.select(
        placeholder="🎚️ Select Equalizer Preset...",
        options=[
            discord.SelectOption(label="Flat", description="No changes to audio", emoji="📊", value="flat"),
            discord.SelectOption(label="Rock", description="Enhanced for rock music", emoji="🎸", value="rock"),
            discord.SelectOption(label="Pop", description="Optimized for pop music", emoji="🎤", value="pop"),
            discord.SelectOption(label="Classical", description="Classical music preset", emoji="🎻", value="classical"),
            discord.SelectOption(label="Electronic", description="Electronic/EDM preset", emoji="🎹", value="electronic"),
            discord.SelectOption(label="Hip-Hop", description="Hip-hop and rap preset", emoji="🎧", value="hiphop"),
            discord.SelectOption(label="Jazz", description="Jazz music preset", emoji="🎺", value="jazz"),
            discord.SelectOption(label="Metal", description="Heavy metal preset", emoji="⚡", value="metal"),
        ]
    )
    async def select_eq(self, interaction: discord.Interaction, select: Select):
        preset = select.values[0]
        filters = wavelink.Filters()

        if preset == "rock":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.3}, {"band": 1, "gain": 0.2}, {"band": 2, "gain": 0.1},
                {"band": 3, "gain": -0.1}, {"band": 4, "gain": 0.2}, {"band": 5, "gain": 0.3}
            ])
        elif preset == "pop":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": -0.1}, {"band": 1, "gain": 0.2}, {"band": 2, "gain": 0.3},
                {"band": 3, "gain": 0.2}, {"band": 4, "gain": 0.1}, {"band": 5, "gain": -0.1}
            ])
        elif preset == "classical":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.2}, {"band": 1, "gain": 0.1}, {"band": 2, "gain": -0.1},
                {"band": 3, "gain": -0.1}, {"band": 4, "gain": 0.1}, {"band": 5, "gain": 0.2}
            ])
        elif preset == "electronic":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.4}, {"band": 1, "gain": 0.3}, {"band": 2, "gain": 0.1},
                {"band": 3, "gain": 0.2}, {"band": 4, "gain": 0.3}, {"band": 5, "gain": 0.4}
            ])
        elif preset == "hiphop":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.5}, {"band": 1, "gain": 0.3}, {"band": 2, "gain": 0.0},
                {"band": 3, "gain": 0.1}, {"band": 4, "gain": 0.2}, {"band": 5, "gain": 0.3}
            ])
        elif preset == "jazz":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.1}, {"band": 1, "gain": 0.2}, {"band": 2, "gain": 0.1},
                {"band": 3, "gain": 0.2}, {"band": 4, "gain": 0.1}, {"band": 5, "gain": 0.2}
            ])
        elif preset == "metal":
            filters.equalizer.set(bands=[
                {"band": 0, "gain": 0.4}, {"band": 1, "gain": 0.3}, {"band": 2, "gain": 0.2},
                {"band": 3, "gain": 0.1}, {"band": 4, "gain": 0.3}, {"band": 5, "gain": 0.4}
            ])

        await self.player.set_filters(filters)
        embed = discord.Embed(
            title="🎚️ Equalizer Applied",
            description=f"Applied **{preset.title()}** equalizer preset!",
            color=0x1DB954
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Playlist data storage
user_playlists = {}


class PlaylistSaveView(View):
    def __init__(self, queue, user_id):
        super().__init__(timeout=60)
        self.queue = queue
        self.user_id = user_id
        self.emoji = EmojiConfig()

    @discord.ui.button(label="Save Queue as Playlist", style=discord.ButtonStyle.success, emoji="💾")
    async def save_queue(self, interaction: discord.Interaction, button: Button):
        modal = SaveQueueModal(self.queue, self.user_id)
        await interaction.response.send_modal(modal)


class SaveQueueModal(discord.ui.Modal, title="Save Queue as Playlist"):
    name = discord.ui.TextInput(
        label="Playlist Name",
        placeholder="My Queue Playlist",
        required=True,
        max_length=50
    )

    def __init__(self, queue, user_id):
        super().__init__()
        self.queue = queue
        self.user_id = user_id

    async def on_submit(self, interaction: discord.Interaction):
        playlist_name = self.name.value

        if self.user_id not in user_playlists:
            user_playlists[self.user_id] = {}

        queue_tracks = list(self.queue)
        user_playlists[self.user_id][playlist_name] = [
            {'title': track.title, 'uri': track.uri, 'author': track.author}
            for track in queue_tracks
        ]

        embed = discord.Embed(
            title="✅ Playlist Saved",
            description=f"Saved **{len(queue_tracks)}** tracks to **{playlist_name}**!",
            color=0x1DB954
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class PlatformSelectView(View):
    def __init__(self, ctx, query):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.query = query
        self.emoji = EmojiConfig()

        yt_button = Button(label="YouTube", emoji="▶️", style=discord.ButtonStyle.danger)
        yt_button.callback = self.create_callback("ytsearch", "YouTube")
        self.add_item(yt_button)

        sc_button = Button(label="SoundCloud", emoji="☁️", style=discord.ButtonStyle.primary)
        sc_button.callback = self.create_callback("scsearch", "SoundCloud")
        self.add_item(sc_button)

    def create_callback(self, source, platform_name):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                embed = discord.Embed(
                    title=f"{self.emoji.ERROR} Permission Denied",
                    description="Only the command author can select a platform.",
                    color=0xFF0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            embed = discord.Embed(
                title=f"{self.emoji.SEARCH} Searching...",
                description=f"Searching for `{self.query}` on {platform_name}...",
                color=0x1DB954
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            await self.perform_search(source, platform_name)
            try:
                await interaction.message.delete()
            except:
                pass
        return callback

    async def perform_search(self, source, platform_name):
        try:
            results = await wavelink.Playable.search(self.query, source=source)
        except Exception as e:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Search Error",
                description=f"An error occurred: {str(e)}",
                color=0xFF0000
            )
            return await self.ctx.send(embed=embed)

        if not results:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Results Found",
                description=f"No results found for `{self.query}` on {platform_name}.",
                color=0xFF0000
            )
            return await self.ctx.send(embed=embed)

        if isinstance(results, wavelink.Playlist):
            top_results = results.tracks[:5]
        else:
            top_results = results[:5]

        embed = discord.Embed(
            title=f"{self.emoji.SEARCH} Search Results - {platform_name}",
            description=f"Top 5 results for `{self.query}`:",
            color=0x1DB954
        )

        for i, track in enumerate(top_results, 1):
            duration = f"{track.length // 1000 // 60}:{track.length // 1000 % 60:02d}"
            embed.add_field(
                name=f"{i}. {track.title[:50]}",
                value=f"**Artist:** {track.author[:40]}\n**Duration:** {duration}",
                inline=False
            )

        await self.ctx.send(embed=embed, view=SearchResultView(self.ctx, top_results))


class SearchResultView(View):
    def __init__(self, ctx, results):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.results = results
        self.emoji = EmojiConfig()

        for i in range(min(5, len(results))):
            button = Button(label=str(i + 1), style=discord.ButtonStyle.primary)
            button.callback = self.create_callback(i)
            self.add_item(button)

    def create_callback(self, index):
        async def callback(interaction: discord.Interaction):
            if interaction.user != self.ctx.author:
                embed = discord.Embed(
                    title=f"{self.emoji.ERROR} Permission Denied",
                    description="Only the command author can select a track.",
                    color=0xFF0000
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return

            track = self.results[index]
            vc = self.ctx.voice_client

            if not vc:
                if not self.ctx.author.voice:
                    embed = discord.Embed(
                        title=f"{self.emoji.ERROR} Voice Channel Required",
                        description="You need to be in a voice channel to play music.",
                        color=0xFF0000
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                vc = await self.ctx.author.voice.channel.connect(cls=wavelink.Player)
                await vc.set_volume(100)

            vc.ctx = self.ctx

            if not vc.playing:
                await vc.play(track)
                embed = discord.Embed(
                    title=f"{self.emoji.MUSICAL_NOTE} Now Playing",
                    description=f"**{track.title}** by **{track.author}**",
                    color=0x1DB954
                )
                await interaction.response.send_message(embed=embed)
                # Get the music cog and display player
                music_cog = self.ctx.bot.get_cog("Music")
                if music_cog:
                    await music_cog.display_player_embed(vc, track, self.ctx)
            else:
                await vc.queue.put_wait(track)
                embed = discord.Embed(
                    title=f"{self.emoji.ADD} Added to Queue",
                    description=f"**{track.title}** by **{track.author}**",
                    color=0x1DB954
                )
                embed.set_footer(text=f"Position in queue: {len(vc.queue)}")
                await interaction.response.send_message(embed=embed)
        return callback


class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.inactivity_timeout = 120
        self.player_inactivity = {}
        self.emoji = EmojiConfig()

    async def log_track_play(self, ctx, track):
        """Log music play to database"""
        try:
            await self.client.music_db.register_server(ctx.guild.id, ctx.guild.name)
            if ctx.author.voice and ctx.author.voice.channel:
                await self.client.music_db.register_voice_channel(
                    ctx.author.voice.channel.id,
                    ctx.guild.id,
                    ctx.author.voice.channel.name
                )

                source = "youtube"
                if "spotify" in track.uri.lower():
                    source = "spotify"
                elif "soundcloud" in track.uri.lower():
                    source = "soundcloud"

                await self.client.music_db.log_music_play(
                    server_id=ctx.guild.id,
                    channel_id=ctx.author.voice.channel.id,
                    user_id=ctx.author.id,
                    user_name=str(ctx.author),
                    track_title=track.title,
                    track_author=track.author,
                    track_uri=track.uri,
                    track_duration=track.length // 1000,
                    track_source=source
                )
        except Exception as e:
            print(f"❌ Database logging error: {e}")

    async def log_search(self, ctx, query, results_count):
        """Log music search to database"""
        try:
            await self.client.music_db.register_server(ctx.guild.id, ctx.guild.name)
            await self.client.music_db.log_search(
                server_id=ctx.guild.id,
                user_id=ctx.author.id,
                user_name=str(ctx.author),
                search_query=query,
                results_count=results_count
            )
        except Exception as e:
            print(f"❌ Search logging error: {e}")

    async def cog_load(self):
        """Called when the cog is loaded"""
        await self.connect_nodes()
        asyncio.create_task(self.monitor_inactivity())

    async def connect_nodes(self) -> None:
        """Connect to Lavalink nodes"""
        try:
            lavalink_uri = None
            lavalink_password = None

            try:
                with open('bot_config.json', 'r') as f:
                    config = json.load(f)
                    lavalink_uri = config.get('lavalink_uri') or os.environ.get("LAVALINK_URI")
                    lavalink_password = config.get('lavalink_password') or os.environ.get("LAVALINK_PASSWORD")
            except FileNotFoundError:
                lavalink_uri = os.environ.get("LAVALINK_URI")
                lavalink_password = os.environ.get("LAVALINK_PASSWORD")

            if not lavalink_uri or not lavalink_password:
                print("⚠️ WARNING: LAVALINK_URI and LAVALINK_PASSWORD not set")
                print("   Using default Lavalink node (for testing only)")
                lavalink_uri = "https://lava-v4.ajieblogs.eu.org:443/"
                lavalink_password = "https://dsc.gg/ajidevserver"

            nodes = [wavelink.Node(uri=lavalink_uri, password=lavalink_password)]
            await wavelink.Pool.connect(nodes=nodes, client=self.client, cache_capacity=None)
            print("🎵 Successfully connected to Lavalink node")
        except Exception as e:
            print(f"❌ Failed to connect to Lavalink: {e}")

    async def monitor_inactivity(self):
        """Monitor voice channel inactivity"""
        while True:
            await asyncio.sleep(60)
            for guild in self.client.guilds:
                await self.check_inactivity(guild.id)

    async def check_inactivity(self, guild_id):
        """Check for inactivity in a guild"""
        guild = self.client.get_guild(guild_id)
        if not guild:
            return

        player = None
        for vc in self.client.voice_clients:
            if vc.guild.id == guild.id:
                player = vc
                break

        if player and player.playing and len(player.channel.members) == 1:
            await self.inactivity_timer(guild)

    async def inactivity_timer(self, guild):
        """Handle inactivity timeout"""
        await asyncio.sleep(self.inactivity_timeout)

        player = None
        for vc in self.client.voice_clients:
            if vc.guild.id == guild.id:
                player = vc
                break

        if player and len(player.channel.members) == 1:
            ctx = getattr(player, 'ctx', None)
            await player.disconnect(force=True)
            if ctx:
                try:
                    embed = discord.Embed(
                        title=f"{self.emoji.WARNING} Inactivity Timeout",
                        description="I've been disconnected due to inactivity.",
                        color=0xFFA500
                    )
                    await ctx.channel.send(embed=embed)
                except:
                    pass

    async def auto_delete_message(self, message, delay):
        """Auto-deletes a message after a specified delay."""
        await asyncio.sleep(delay)
        try:
            await message.delete()
        except discord.NotFound:
            pass
        except Exception as e:
            print(f"Error deleting message: {e}")

    async def display_player_embed(self, player, track, ctx, autoplay=False):
        """Display the player embed with track information"""
        try:
            # Handle autoplay-only mode
            if hasattr(player, '_autoplay_only') and player._autoplay_only:
                simple_embed = discord.Embed(
                    title=f"{self.emoji.MUSICAL_NOTES} Now Playing - 24/7 Autoplay",
                    description=f"**{track.title}**\nby **{track.author}**",
                    color=0x1DB954
                )
                if track.artwork:
                    simple_embed.set_thumbnail(url=track.artwork)
                simple_embed.set_footer(text="Autoplay Mode - Music plays continuously")
                msg = await ctx.send(embed=simple_embed)
                await asyncio.sleep(10)
                try:
                    await msg.delete()
                except:
                    pass
                return

            # Delete previous player message if exists
            guild_id = ctx.guild.id
            if guild_id in active_player_messages:
                try:
                    await active_player_messages[guild_id].delete()
                except:
                    pass

            # Create enhanced embed
            sec = track.length // 1000
            duration = f"0{sec // 60}:{sec % 60:02d}" if sec < 600 else f"{sec // 60}:{sec % 60:02d}"

            # Determine source emoji
            if "spotify" in track.uri.lower():
                source_emoji = self.emoji.SPOTIFY
                source_name = "Spotify"
            elif "youtube" in track.uri.lower():
                source_emoji = self.emoji.YOUTUBE
                source_name = "YouTube"
            elif "soundcloud" in track.uri.lower():
                source_emoji = self.emoji.SOUNDCLOUD
                source_name = "SoundCloud"
            else:
                source_emoji = self.emoji.MUSICAL_NOTE
                source_name = "Unknown"

            embed = discord.Embed(
                title=f"{self.emoji.MUSICAL_NOTES} Now Playing - Ultra HD 384kbps",
                color=0x1DB954
            )

            embed.add_field(
                name=f"{self.emoji.MUSICAL_NOTE} Track",
                value=f"**{track.title[:60]}**",
                inline=False
            )
            embed.add_field(
                name=f"{self.emoji.MICROPHONE} Artist",
                value=f"**{track.author[:40]}**",
                inline=True
            )
            embed.add_field(
                name=f"{self.emoji.CLOCK} Duration",
                value=f"**{duration}**",
                inline=True
            )
            embed.add_field(
                name=f"{self.emoji.QUALITY} Quality",
                value=f"**384kbps Ultra HD**",
                inline=True
            )
            embed.add_field(
                name=f"{self.emoji.RADIO} Source",
                value=f"{source_emoji} **{source_name}**",
                inline=True
            )
            embed.add_field(
                name=f"{self.emoji.VOLUME_HIGH} Volume",
                value=f"**{player.volume}%**",
                inline=True
            )

            if track.artwork:
                embed.set_image(url=track.artwork)

            requester_text = f"{ctx.author.display_name} ({'Autoplay' if autoplay else 'Requested'})"
            embed.set_footer(
                text=f"Requested by {requester_text}",
                icon_url=ctx.author.display_avatar.url
            )

            message = await ctx.send(embed=embed, view=UltraAdvancedMusicControlView(player, ctx))
            active_player_messages[guild_id] = message

            await self.log_track_play(ctx, track)

        except Exception as e:
            print(f"❌ Error displaying player embed: {e}")
            await self.display_fallback_embed(player, track, ctx, autoplay)

    async def display_fallback_embed(self, player, track, ctx, autoplay=False):
        """Fallback embed without advanced features"""
        sec = track.length // 1000
        duration = f"0{sec // 60}:{sec % 60:02d}" if sec < 600 else f"{sec // 60}:{sec % 60:02d}"

        embed = discord.Embed(
            title=f"{self.emoji.MUSICAL_NOTES} Now Playing",
            description=f"**{track.title}** by **{track.author}**",
            color=0x1DB954
        )
        embed.add_field(name="Duration", value=duration, inline=True)
        embed.add_field(name="Source", value="YouTube", inline=True)

        if track.artwork:
            embed.set_image(url=track.artwork)

        requester_text = "Autoplay" if autoplay else ctx.author.display_name
        embed.set_footer(text=f"Requested by {requester_text}")

        message = await ctx.send(embed=embed, view=UltraAdvancedMusicControlView(player, ctx))
        active_player_messages[ctx.guild.id] = message

    async def on_track_end(self, payload: wavelink.TrackEndEventPayload):
        """Handle track end events"""
        player = payload.player

        if not player:
            return

        # Handle autoplay-only mode
        if hasattr(player, '_autoplay_only') and player._autoplay_only:
            if len(player.queue) < 5:
                autoplay_queries = [
                    "lofi hip hop radio", "lofi study music", "chill lofi beats",
                    "latest hindi songs", "bollywood romantic songs",
                    "sad songs english", "top english songs", "arabic songs"
                ]

                for _ in range(10):
                    random_query = random.choice(autoplay_queries)
                    try:
                        tracks = await wavelink.Playable.search(random_query)
                        if tracks:
                            if isinstance(tracks, wavelink.Playlist):
                                track = tracks.tracks[0]
                            else:
                                track = tracks[0]
                            await player.queue.put_wait(track)
                    except:
                        continue

        # Clear active player message
        if hasattr(player, 'ctx') and player.ctx:
            guild_id = player.ctx.guild.id
            if not (hasattr(player, '_autoplay_only') and player._autoplay_only):
                if guild_id in active_player_messages:
                    try:
                        await active_player_messages[guild_id].delete()
                        del active_player_messages[guild_id]
                    except:
                        pass

        if player.queue and not player.queue.is_empty:
            next_track = await player.queue.get_wait()
            await player.play(next_track)
            if hasattr(player, 'ctx') and player.ctx:
                await self.display_player_embed(player, next_track, player.ctx)
        elif player.autoplay == wavelink.AutoPlayMode.enabled:
            await asyncio.sleep(2)
            if player.current and hasattr(player, 'ctx') and player.ctx:
                await self.display_player_embed(player, player.current, player.ctx, autoplay=True)
        else:
            ctx = getattr(player, 'ctx', None)
            await player.disconnect()
            if ctx:
                embed = discord.Embed(
                    title=f"{self.emoji.STOP} Queue Ended",
                    description="All tracks have been played. I've left the voice channel.",
                    color=0x1DB954
                )
                await ctx.channel.send(embed=embed)

    async def play_source(self, ctx, query):
        """Play music from a query"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Voice Channel Required",
                description="You need to be in a voice channel to play music!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        vc = ctx.voice_client
        if not vc:
            try:
                vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                await vc.set_volume(100)
            except Exception as e:
                embed = discord.Embed(
                    title=f"{self.emoji.ERROR} Connection Failed",
                    description=f"Failed to connect: {str(e)}",
                    color=0xFF0000
                )
                await ctx.send(embed=embed)
                return

        vc.ctx = ctx

        if vc.playing and ctx.voice_client and ctx.voice_client.channel != ctx.author.voice.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description=f"You must be in {ctx.voice_client.channel.mention} to control the music!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        vc.autoplay = wavelink.AutoPlayMode.disabled

        # Check for Spotify links
        if spotify_api and re.match(SPOTIFY_TRACK_REGEX, query):
            await self.handle_spotify_link(ctx, vc, query, "track")
            return
        elif spotify_api and re.match(SPOTIFY_PLAYLIST_REGEX, query):
            await self.handle_spotify_link(ctx, vc, query, "playlist")
            return
        elif spotify_api and re.match(SPOTIFY_ALBUM_REGEX, query):
            await self.handle_spotify_link(ctx, vc, query, "album")
            return

        # Regular search
        embed = discord.Embed(
            title=f"{self.emoji.SEARCH} Searching High Quality Audio...",
            description=f"Searching for `{query}`...",
            color=0x1DB954
        )
        search_msg = await ctx.send(embed=embed)

        try:
            tracks = await wavelink.Playable.search(query)
        except Exception as e:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Search Error",
                description=f"An error occurred while searching: {str(e)}",
                color=0xFF0000
            )
            await search_msg.edit(embed=embed)
            return

        if not tracks:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Results Found",
                description=f"No results found for `{query}`.",
                color=0xFF0000
            )
            await search_msg.edit(embed=embed)
            return

        # Log search
        results_count = len(tracks.tracks) if isinstance(tracks, wavelink.Playlist) else len(tracks)
        await self.log_search(ctx, query, results_count)

        if isinstance(tracks, wavelink.Playlist):
            await vc.queue.put_wait(tracks.tracks)

            total_duration_sec = sum(t.length // 1000 for t in tracks.tracks)
            total_duration = f"{total_duration_sec // 60}:{total_duration_sec % 60:02d}"

            embed = discord.Embed(
                title=f"{self.emoji.ADD} Playlist Added to Queue",
                description=f"**{tracks.name}**",
                color=0x1DB954
            )
            embed.add_field(name=f"{self.emoji.MUSICAL_NOTES} Tracks", value=f"{len(tracks.tracks)} songs", inline=True)
            embed.add_field(name=f"{self.emoji.CLOCK} Total Duration", value=total_duration, inline=True)
            embed.add_field(name=f"{self.emoji.QUALITY} Quality", value="384kbps Ultra HD", inline=True)

            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url            )

            await search_msg.edit(embed=embed)
            asyncio.create_task(self.auto_delete_message(search_msg, 5))

            if not vc.playing and not vc.queue.is_empty:
                next_track = await vc.queue.get_wait()
                await vc.play(next_track)
                await self.display_player_embed(vc, next_track, ctx)
        else:
            track = tracks[0]
            await vc.queue.put_wait(track)

            duration = f"{track.length // 1000 // 60}:{track.length // 1000 % 60:02d}"
            embed = discord.Embed(
                title=f"{self.emoji.ADD} Track Added to Queue",
                description=f"**{track.title}**",
                color=0x1DB954
            )
            embed.add_field(name=f"{self.emoji.MICROPHONE} Artist", value=track.author, inline=True)
            embed.add_field(name=f"{self.emoji.CLOCK} Duration", value=duration, inline=True)
            embed.add_field(name=f"{self.emoji.QUALITY} Quality", value="384kbps Ultra HD", inline=True)

            if track.artwork:
                embed.set_thumbnail(url=track.artwork)

            embed.set_footer(
                text=f"Requested by {ctx.author.display_name}",
                icon_url=ctx.author.display_avatar.url
            )

            await search_msg.edit(embed=embed)
            asyncio.create_task(self.auto_delete_message(search_msg, 5))

            if not vc.playing and not vc.queue.is_empty:
                next_track = await vc.queue.get_wait()
                await vc.play(next_track)
                await self.display_player_embed(vc, next_track, ctx)

    async def handle_spotify_link(self, ctx, vc, link, type_):
        """Handle Spotify links"""
        try:
            if type_ == "track":
                track_id = re.search(SPOTIFY_TRACK_REGEX, link).group(1)
                track_info = await spotify_api.get_track(track_id)

                title = track_info['name']
                author = ', '.join(artist['name'] for artist in track_info['artists'])

                search_query = f"{title} by {author}"
                search_results = await wavelink.Playable.search(search_query)

                if not search_results:
                    embed = discord.Embed(
                        title=f"{self.emoji.ERROR} Track Not Available",
                        description="This Spotify track is not available on YouTube.",
                        color=0xFF0000
                    )
                    await ctx.send(embed=embed)
                    return

                track = search_results[0] if not isinstance(search_results, wavelink.Playlist) else search_results.tracks[0]
                await vc.queue.put_wait(track)

                duration = f"{track.length // 1000 // 60}:{track.length // 1000 % 60:02d}"
                embed = discord.Embed(
                    title=f"{self.emoji.SPOTIFY} Spotify Track Added",
                    description=f"**{track.title}**",
                    color=0x1DB954
                )
                embed.add_field(name=f"{self.emoji.MICROPHONE} Artist", value=track.author, inline=True)
                embed.add_field(name=f"{self.emoji.CLOCK} Duration", value=duration, inline=True)
                embed.add_field(name=f"{self.emoji.QUALITY} Quality", value="384kbps Ultra HD", inline=True)

                if track.artwork:
                    embed.set_thumbnail(url=track.artwork)

                embed.set_footer(
                    text=f"Requested by {ctx.author.display_name}",
                    icon_url=ctx.author.display_avatar.url
                )

                msg = await ctx.send(embed=embed)
                asyncio.create_task(self.auto_delete_message(msg, 5))

                if not vc.playing:
                    await vc.play(track)
                    await self.display_player_embed(vc, track, ctx)

            elif type_ == "playlist":
                embed = discord.Embed(
                    title=f"{self.emoji.LOADING} Processing Playlist",
                    description="Adding tracks from Spotify playlist... This may take a while...",
                    color=0x1DB954
                )
                process_msg = await ctx.send(embed=embed)

                playlist_id = re.search(SPOTIFY_PLAYLIST_REGEX, link).group(1)
                playlist_info = await spotify_api.get(f"playlists/{playlist_id}")
                tracks = playlist_info.get("tracks", {}).get("items", [])
                playlist_length = len(tracks)

                if not tracks:
                    embed = discord.Embed(
                        title=f"{self.emoji.ERROR} Empty Playlist",
                        description="No tracks found in the Spotify playlist.",
                        color=0xFF0000
                    )
                    await process_msg.edit(embed=embed)
                    return

                c = 0
                for track_item in tracks:
                    if track_item.get('track') is None:
                        continue
                    title = track_item['track']['name']
                    author = ', '.join(artist['name'] for artist in track_item['track']['artists'])
                    search_query = f"{title} {author}"

                    try:
                        track_results = await wavelink.Playable.search(search_query)
                        if track_results:
                            track = track_results[0] if not isinstance(track_results, wavelink.Playlist) else track_results.tracks[0]
                            await vc.queue.put_wait(track)
                            c += 1
                    except:
                        continue

                embed = discord.Embed(
                    title=f"{self.emoji.ADD} Spotify Playlist Added",
                    description=f"**{c}** out of **{playlist_length}** tracks from **{playlist_info['name']}** have been added!",
                    color=0x1DB954
                )
                await process_msg.edit(embed=embed)
                asyncio.create_task(self.auto_delete_message(process_msg, 5))

                if not vc.playing and not vc.queue.is_empty:
                    next_track = await vc.queue.get_wait()
                    await vc.play(next_track)
                    await self.display_player_embed(vc, next_track, ctx)

            elif type_ == "album":
                embed = discord.Embed(
                    title=f"{self.emoji.LOADING} Processing Album",
                    description="Adding tracks from Spotify album... Please wait...",
                    color=0x1DB954
                )
                process_msg = await ctx.send(embed=embed)

                album_id = re.search(SPOTIFY_ALBUM_REGEX, link).group(1)
                album_info = await spotify_api.get(f"albums/{album_id}")
                tracks = album_info.get("tracks", {}).get("items", [])

                if not tracks:
                    embed = discord.Embed(
                        title=f"{self.emoji.ERROR} Empty Album",
                        description="No tracks found in the Spotify album.",
                        color=0xFF0000
                    )
                    await process_msg.edit(embed=embed)
                    return

                c = 0
                for track_item in tracks:
                    title = track_item['name']
                    author = ', '.join(artist['name'] for artist in track_item['artists'])
                    search_query = f"{title} {author}"

                    try:
                        track_results = await wavelink.Playable.search(search_query)
                        if track_results:
                            track = track_results[0] if not isinstance(track_results, wavelink.Playlist) else track_results.tracks[0]
                            await vc.queue.put_wait(track)
                            c += 1
                    except:
                        continue

                embed = discord.Embed(
                    title=f"{self.emoji.ADD} Spotify Album Added",
                    description=f"**{c}** tracks from **{album_info['name']}** have been added!",
                    color=0x1DB954
                )
                await process_msg.edit(embed=embed)
                asyncio.create_task(self.auto_delete_message(process_msg, 5))

                if not vc.playing and not vc.queue.is_empty:
                    next_track = await vc.queue.get_wait()
                    await vc.play(next_track)
                    await self.display_player_embed(vc, next_track, ctx)

        except Exception as e:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Spotify Error",
                description=f"An error occurred: {str(e)}",
                color=0xFF0000
            )
            await ctx.send(embed=embed)

    def create_progress_bar(self, completed, total, length=15):
        """Create a visual progress bar"""
        if total == 0:
            return "▬" * length

        percentage = completed / total
        filled_length = int(length * percentage)
        bar = '█' * filled_length + '▬' * (length - filled_length)
        return bar

    @commands.hybrid_command(name="play", aliases=['p'], usage="play <query>", help="Plays a song or playlist.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def play(self, ctx: commands.Context, *, query: str):
        """Play music from YouTube, Spotify, or search query"""
        await self.play_source(ctx, query)

    @commands.hybrid_command(name="search", usage="search <query>", help="Searches music from multiple platforms.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def search2(self, ctx: commands.Context, *, query: str):
        """Search for music across different platforms"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Voice Channel Required",
                description="You need to be in a voice channel to search for music!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"{self.emoji.SEARCH} Select Search Platform",
            description=f"Choose where to search for: **{query}**",
            color=0x1DB954
        )
        embed.add_field(
            name=f"{self.emoji.YOUTUBE} YouTube",
            value="Search on YouTube Music",
            inline=True
        )
        embed.add_field(
            name=f"{self.emoji.SOUNDCLOUD} SoundCloud",
            value="Search on SoundCloud",
            inline=True
        )
        await ctx.send(embed=embed, view=PlatformSelectView(ctx, query))

    @commands.hybrid_command(name="nowplaying", aliases=["np"], usage="nowplaying", help="Shows the info about current playing song.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def nowplaying(self, ctx: commands.Context):
        """Display currently playing track with progress bar"""
        vc = ctx.voice_client
        if not vc or not vc.playing:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Music Playing",
                description="There's no music currently playing!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if not ctx.author.voice or ctx.author.voice.channel.id != vc.channel.id:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        track = vc.current
        if not track:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Track",
                description="No track is currently playing!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        position = vc.position / 1000
        length = track.length / 1000

        progress_bar = self.create_progress_bar(position, length)
        position_str = f"{int(position // 60)}:{int(position % 60):02d}"
        length_str = f"{int(length // 60)}:{int(length % 60):02d}"

        if "spotify" in track.uri:
            source_emoji = self.emoji.SPOTIFY
            source_name = "Spotify"
        elif "youtube" in track.uri:
            source_emoji = self.emoji.YOUTUBE
            source_name = "YouTube"
        elif "soundcloud" in track.uri:
            source_emoji = self.emoji.SOUNDCLOUD
            source_name = "SoundCloud"
        else:
            source_emoji = self.emoji.MUSICAL_NOTE
            source_name = "Unknown"

        embed = discord.Embed(
            title=f"{self.emoji.MUSICAL_NOTES} Now Playing - High Quality",
            color=0x1DB954
        )
        embed.add_field(
            name=f"{self.emoji.MUSICAL_NOTE} Track",
            value=f"[{track.title}]({track.uri})",
            inline=False
        )
        embed.add_field(
            name=f"{self.emoji.MICROPHONE} Artist",
            value=track.author,
            inline=True
        )
        embed.add_field(
            name=f"{self.emoji.QUALITY} Quality",
            value="384kbps",
            inline=True
        )
        embed.add_field(
            name=f"{self.emoji.CLOCK} Progress",
            value=f"`{position_str}` {progress_bar} `{length_str}`",
            inline=False
        )
        embed.add_field(
            name=f"{self.emoji.QUEUE} Queue",
            value=f"`{len(vc.queue)}` tracks waiting",
            inline=True
        )
        embed.add_field(
            name=f"{self.emoji.RADIO} Source",
            value=f"{source_emoji} {source_name}",
            inline=True
        )

        if track.artwork:
            embed.set_image(url=track.artwork)

        embed.set_footer(
            text=f"Requested by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="join", usage="join", help="Joins your voice channel.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def join(self, ctx: commands.Context):
        """Join the voice channel"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Voice Channel Required",
                description="You need to be in a voice channel for me to join!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.voice_client:
            if ctx.voice_client.channel == ctx.author.voice.channel:
                embed = discord.Embed(
                    title=f"{self.emoji.WARNING} Already Connected",
                    description=f"I'm already in {ctx.voice_client.channel.mention}!",
                    color=0xFFA500
                )
                await ctx.send(embed=embed)
                return
            else:
                await ctx.voice_client.move_to(ctx.author.voice.channel)
                embed = discord.Embed(
                    title=f"{self.emoji.SUCCESS} Moved",
                    description=f"Moved to {ctx.author.voice.channel.mention}!",
                    color=0x1DB954
                )
                await ctx.send(embed=embed)
                return

        channel = ctx.author.voice.channel
        try:
            if not wavelink.Pool.nodes:
                embed = discord.Embed(
                    title=f"{self.emoji.ERROR} Lavalink Not Connected",
                    description="Music server is not ready. Please wait a moment and try again.",
                    color=0xFF0000
                )
                await ctx.send(embed=embed)
                return

            vc = await channel.connect(cls=wavelink.Player)
            vc.ctx = ctx
            await vc.set_volume(100)
            vc.autoplay = wavelink.AutoPlayMode.disabled

            embed = discord.Embed(
                title=f"{self.emoji.SUCCESS} Connected",
                description=f"✅ Successfully joined {channel.mention}!\n\n"
                           "🎵 Use `/play` or `x!play` to start playing music",
                color=0x1DB954
            )
            embed.set_footer(text=f"Joined by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
            await ctx.send(embed=embed)

        except Exception as e:
            print(f"Error joining voice channel: {e}")
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Connection Failed",
                description=f"Failed to join voice channel.\nError: {str(e)}",
                color=0xFF0000
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="disconnect", aliases=["dc", "leave"], usage="disconnect", help="Disconnects from voice channel.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def disconnect(self, ctx: commands.Context):
        """Disconnect from voice channel"""
        vc = ctx.voice_client
        if not vc:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Not Connected",
                description="I'm not connected to any voice channel!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        await vc.disconnect()
        embed = discord.Embed(
            title=f"{self.emoji.SUCCESS} Disconnected",
            description="Successfully disconnected from the voice channel!",
            color=0x1DB954
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="pause", usage="pause", help="Pauses the current track.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def pause(self, ctx: commands.Context):
        """Pause the music"""
        vc = ctx.voice_client
        if not vc or not vc.playing:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Music Playing",
                description="There's no music currently playing!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        await vc.pause(True)

        embed = discord.Embed(
            title=f"{self.emoji.PAUSE} Playback Paused",
            description=f"**{vc.current.title}**",
            color=0xFFA500
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="resume", usage="resume", help="Resumes the paused track.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def resume(self, ctx: commands.Context):
        """Resume the music"""
        vc = ctx.voice_client
        if not vc:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Not Connected",
                description="I'm not connected to any voice channel!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if not vc.paused:
            embed = discord.Embed(
                title=f"{self.emoji.WARNING} Already Playing",
                description="The music is already playing!",
                color=0xFFA500
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        await vc.pause(False)

        embed = discord.Embed(
            title=f"{self.emoji.PLAY} Playback Resumed",
            description=f"**{vc.current.title}**",
            color=0x1DB954
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="skip", usage="skip", help="Skips the current track.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def skip(self, ctx: commands.Context):
        """Skip the current track"""
        vc = ctx.voice_client
        if not vc or not vc.playing:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Music Playing",
                description="There's no music currently playing!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        current_track_title = vc.current.title if vc.current else "Unknown"
        await vc.stop()

        embed = discord.Embed(
            title=f"{self.emoji.SKIP} Track Skipped",
            description=f"**{current_track_title}**",
            color=0x1DB954
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="stop", usage="stop", help="Stops playback and clears the queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def stop(self, ctx: commands.Context):
        """Stop playback and clear queue"""
        vc = ctx.voice_client
        if not vc:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Not Connected",
                description="I'm not connected to any voice channel!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        guild_id = ctx.guild.id
        if guild_id in active_player_messages:
            try:
                await active_player_messages[guild_id].delete()
                del active_player_messages[guild_id]
            except:
                pass

        vc.queue.clear()
        await vc.disconnect()
        embed = discord.Embed(
            title=f"{self.emoji.STOP} Playback Stopped",
            description="Music playback has been stopped and queue cleared!",
            color=0x1DB954
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="volume", aliases=["vol"], usage="volume <1-200>", help="Sets the player volume.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def volume(self, ctx: commands.Context, volume: int):
        """Set the player volume"""
        vc = ctx.voice_client
        if not vc:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Not Connected",
                description="I'm not connected to any voice channel!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if not 1 <= volume <= 200:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Invalid Volume",
                description="Volume must be between 1 and 200!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        old_volume = vc.volume
        await vc.set_volume(volume)

        volume_emoji = self.emoji.VOLUME_MUTE if volume == 0 else self.emoji.VOLUME_LOW if volume < 50 else self.emoji.VOLUME_HIGH

        embed = discord.Embed(
            title=f"{volume_emoji} Volume Adjusted",
            description=f"Volume changed from `{old_volume}%` to `{volume}%`",
            color=0x1DB954
        )
        embed.set_footer(
            text=f"Adjusted by {ctx.author.display_name}",
            icon_url=ctx.author.display_avatar.url
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="queue", aliases=["q"], usage="queue", help="Shows the current queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def queue(self, ctx: commands.Context):
        """Show the current queue"""
        vc = ctx.voice_client
        if not vc:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Not Connected",
                description="I'm not connected to any voice channel!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if vc.queue.is_empty:
            embed = discord.Embed(
                title=f"{self.emoji.QUEUE} Queue Empty",
                description="The queue is currently empty!",
                color=0xFFA500
            )
            await ctx.send(embed=embed)
            return

        embed = discord.Embed(
            title=f"{self.emoji.QUEUE} Current Queue",
            description=f"Showing up to 10 tracks in queue",
            color=0x1DB954
        )

        queue_list = list(vc.queue)[:10]
        for i, track in enumerate(queue_list, start=1):
            duration = f"{track.length // 1000 // 60}:{track.length // 1000 % 60:02d}"
            embed.add_field(
                name=f"{i}. {track.title[:50]}",
                value=f"**Artist:** {track.author[:30]} | **Duration:** {duration}",
                inline=False
            )

        if len(vc.queue) > 10:
            embed.set_footer(text=f"And {len(vc.queue) - 10} more tracks in queue...")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="clearqueue", aliases=["cq"], usage="clearqueue", help="Clears the entire queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def clearqueue(self, ctx: commands.Context):
        """Clear the queue"""
        vc = ctx.voice_client
        if not vc:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Not Connected",
                description="I'm not connected to any voice channel!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if vc.queue.is_empty:
            embed = discord.Embed(
                title=f"{self.emoji.WARNING} Queue Already Empty",
                description="The queue is already empty!",
                color=0xFFA500
            )
            await ctx.send(embed=embed)
            return

        queue_count = len(vc.queue)
        vc.queue.clear()
        embed = discord.Embed(
            title=f"{self.emoji.CLEAR} Queue Cleared",
            description=f"Cleared `{queue_count}` tracks from the queue!",
            color=0x1DB954
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="shuffle", usage="shuffle", help="Shuffles the queue.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def shuffle(self, ctx: commands.Context):
        """Shuffle the queue"""
        vc = ctx.voice_client
        if not vc:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Not Connected",
                description="I'm not connected to any voice channel!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if vc.queue.is_empty:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Queue Empty",
                description="The queue is empty, nothing to shuffle!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        queue_list = list(vc.queue)
        random.shuffle(queue_list)
        vc.queue.clear()
        for track in queue_list:
            vc.queue.put(track)

        embed = discord.Embed(
            title=f"{self.emoji.SHUFFLE} Queue Shuffled",
            description=f"Shuffled `{len(queue_list)}` tracks in the queue!",
            color=0x1DB954
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="loop", usage="loop", help="Toggles loop mode.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def loop(self, ctx: commands.Context):
        """Toggle loop mode"""
        vc = ctx.voice_client
        if not vc or not vc.playing:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Music Playing",
                description="There's no music currently playing!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        vc.queue.mode = wavelink.QueueMode.loop if vc.queue.mode != wavelink.QueueMode.loop else wavelink.QueueMode.normal
        mode = "enabled" if vc.queue.mode == wavelink.QueueMode.loop else "disabled"
        embed = discord.Embed(
            title=f"{self.emoji.REPEAT} Loop {mode.title()}",
            description=f"Loop mode has been **{mode}**!",
            color=0x1DB954 if mode == "enabled" else 0xFFA500
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="autoplay", usage="autoplay", help="Start 24/7 autoplay with unlimited random songs")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def autoplay(self, ctx: commands.Context):
        """Start 24/7 autoplay with unlimited random songs"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Voice Channel Required",
                description="You need to be in a voice channel to use autoplay!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        vc = ctx.voice_client
        if not vc:
            try:
                vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
                await vc.set_volume(100)
            except Exception as e:
                embed = discord.Embed(
                    title=f"{self.emoji.ERROR} Connection Failed",
                    description=f"Failed to join voice channel: {str(e)}",
                    color=0xFF0000
                )
                await ctx.send(embed=embed)
                return

        vc.ctx = ctx
        vc.autoplay = wavelink.AutoPlayMode.enabled
        vc._autoplay_only = True

        autoplay_queries = [
            "lofi hip hop radio", "lofi study music", "chill lofi beats",
            "lofi relaxing music", "lofi sleep music", "lofi jazz",
            "latest hindi songs", "bollywood romantic songs", "hindi lofi songs",
            "arijit singh songs", "hindi sad songs", "shreya ghoshal songs",
            "sad songs english", "heartbreak songs", "emotional songs english",
            "top english songs", "pop hits", "indie music", "acoustic songs",
            "arabic songs", "arabic music", "arabic lofi", "arabic romantic songs"
        ]

        embed = discord.Embed(
            title=f"{self.emoji.LOADING} Starting 24/7 Autoplay",
            description="🎵 Loading unlimited random songs...",
            color=0x1DB954
        )
        status_msg = await ctx.send(embed=embed)

        added_count = 0
        for _ in range(20):
            random_query = random.choice(autoplay_queries)
            try:
                tracks = await wavelink.Playable.search(random_query)
                if tracks:
                    track = tracks[0] if not isinstance(tracks, wavelink.Playlist) else tracks.tracks[0]
                    await vc.queue.put_wait(track)
                    added_count += 1
            except:
                continue

        embed = discord.Embed(
            title=f"{self.emoji.SUCCESS} 24/7 Autoplay Started!",
            description=f"✅ **Unlimited music playback activated!**\n\n"
                       f"🎵 **{added_count}** songs loaded initially\n"
                       "🔄 **Auto-queue enabled**\n"
                       "🎶 **Quality:** 384kbps Ultra HD\n\n"
                       f"**Stop with:** `/stop` or `x!stop`",
            color=0x1DB954
        )
        embed.set_footer(text=f"Started by {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
        await status_msg.edit(embed=embed)

        asyncio.create_task(self.auto_delete_message(status_msg, 5))

        if not vc.playing and not vc.queue.is_empty:
            next_track = await vc.queue.get_wait()
            await vc.play(next_track)
            simple_embed = discord.Embed(
                title=f"{self.emoji.MUSICAL_NOTES} Now Playing - 24/7 Autoplay",
                description=f"**{next_track.title}**\nby **{next_track.author}**",
                color=0x1DB954
            )
            if next_track.artwork:
                simple_embed.set_thumbnail(url=next_track.artwork)
            simple_embed.set_footer(text="Autoplay Mode - Music plays continuously")
            msg = await ctx.send(embed=simple_embed)
            asyncio.create_task(self.auto_delete_message(msg, 10))

    @commands.hybrid_command(name="seek", usage="seek <seconds>", help="Seeks to a position in the track.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def seek(self, ctx: commands.Context, seconds: int):
        """Seek to a position in the track"""
        vc = ctx.voice_client
        if not vc or not vc.playing:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Music Playing",
                description="There's no music currently playing!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if seconds < 0 or seconds * 1000 > vc.current.length:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Invalid Position",
                description=f"Position must be between 0 and {vc.current.length // 1000} seconds!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        await vc.seek(seconds * 1000)
        embed = discord.Embed(
            title=f"{self.emoji.CLOCK} Seeked",
            description=f"Seeked to `{seconds // 60}:{seconds % 60:02d}` in **{vc.current.title}**!",
            color=0x1DB954
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="replay", usage="replay", help="Replays the current track.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def replay(self, ctx: commands.Context):
        """Replay the current track"""
        vc = ctx.voice_client
        if not vc or not vc.playing:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Music Playing",
                description="There's no music currently playing!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        await vc.seek(0)
        embed = discord.Embed(
            title=f"{self.emoji.REPEAT} Replaying",
            description=f"Replaying **{vc.current.title}**!",
            color=0x1DB954
        )
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="previous", aliases=["prev"], usage="previous", help="Play the previous track")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def previous(self, ctx: commands.Context):
        """Play the previous track"""
        vc = ctx.voice_client
        if not vc:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Not Connected",
                description="I'm not connected to any voice channel!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        guild_id = ctx.guild.id
        if guild_id in track_histories and track_histories[guild_id]:
            previous_track = track_histories[guild_id].pop()
            await vc.play(previous_track)
            embed = discord.Embed(
                title=f"{self.emoji.PREVIOUS} Playing Previous Track",
                description=f"**{previous_track.title}**",
                color=0x1DB954
            )
            await ctx.send(embed=embed)
            await self.display_player_embed(vc, previous_track, ctx)
        else:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Previous Track",
                description="There's no previous track in history!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)

    @commands.hybrid_command(name="createplaylist", usage="createplaylist <name>", help="Create a new playlist")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def createplaylist(self, ctx: commands.Context, *, name: str):
        """Create a new playlist"""
        user_id = ctx.author.id

        if user_id not in user_playlists:
            user_playlists[user_id] = {}

        if name in user_playlists[user_id]:
            embed = discord.Embed(
                title="❌ Playlist Exists",
                description=f"You already have a playlist named **{name}**!",
                color=0xFF0000
            )
        else:
            user_playlists[user_id][name] = []
            embed = discord.Embed(
                title="✅ Playlist Created",
                description=f"Created playlist **{name}**!",
                color=0x1DB954
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="playlists", usage="playlists", help="View your playlists")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def playlists(self, ctx: commands.Context):
        """View all your playlists"""
        user_id = ctx.author.id
        playlists = user_playlists.get(user_id, {})

        if not playlists:
            embed = discord.Embed(
                title="📂 Your Playlists",
                description="You don't have any playlists yet!\nUse `x!createplaylist <name>` to create one.",
                color=0xFFA500
            )
        else:
            embed = discord.Embed(
                title="📂 Your Playlists",
                description=f"You have {len(playlists)} playlist(s):",
                color=0x1DB954
            )
            for name, tracks in list(playlists.items())[:10]:
                embed.add_field(
                    name=f"📁 {name}",
                    value=f"`{len(tracks)}` tracks",
                    inline=True
                )

            if len(playlists) > 10:
                embed.set_footer(text=f"And {len(playlists) - 10} more playlists...")

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="playplaylist", usage="playplaylist <name>", help="Play a saved playlist")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def playplaylist(self, ctx: commands.Context, *, name: str):
        """Play a saved playlist"""
        if not ctx.author.voice:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Voice Channel Required",
                description="You need to be in a voice channel!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        user_id = ctx.author.id
        playlists = user_playlists.get(user_id, {})

        if name not in playlists:
            embed = discord.Embed(
                title="❌ Playlist Not Found",
                description=f"You don't have a playlist named **{name}**!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        vc = ctx.voice_client
        if not vc:
            vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
            await vc.set_volume(100)

        vc.ctx = ctx

        embed = discord.Embed(
            title=f"{self.emoji.LOADING} Loading Playlist",
            description=f"Loading **{name}**...",
            color=0x1DB954
        )
        msg = await ctx.send(embed=embed)

        tracks_data = playlists[name]
        loaded_count = 0

        for track_data in tracks_data:
            try:
                results = await wavelink.Playable.search(track_data['uri'])
                if results:
                    track = results[0] if not isinstance(results, wavelink.Playlist) else results.tracks[0]
                    await vc.queue.put_wait(track)
                    loaded_count += 1
            except:
                continue

        embed = discord.Embed(
            title="✅ Playlist Loaded",
            description=f"Loaded **{loaded_count}** tracks from **{name}**!",
            color=0x1DB954
        )
        await msg.edit(embed=embed)

        if not vc.playing and not vc.queue.is_empty:
            next_track = await vc.queue.get_wait()
            await vc.play(next_track)
            await self.display_player_embed(vc, next_track, ctx)

    @commands.hybrid_command(name="deleteplaylist", usage="deleteplaylist <name>", help="Delete a playlist")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def deleteplaylist(self, ctx: commands.Context, *, name: str):
        """Delete a playlist"""
        user_id = ctx.author.id
        playlists = user_playlists.get(user_id, {})

        if name not in playlists:
            embed = discord.Embed(
                title="❌ Playlist Not Found",
                description=f"You don't have a playlist named **{name}**!",
                color=0xFF0000
            )
        else:
            del user_playlists[user_id][name]
            embed = discord.Embed(
                title="✅ Playlist Deleted",
                description=f"Deleted playlist **{name}**!",
                color=0x1DB954
            )

        await ctx.send(embed=embed)

    @commands.hybrid_command(name="viewplaylist", usage="viewplaylist <name>", help="View tracks in a playlist")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def viewplaylist(self, ctx: commands.Context, *, name: str):
        """View tracks in a playlist"""
        user_id = ctx.author.id
        playlists = user_playlists.get(user_id, {})

        if name not in playlists:
            embed = discord.Embed(
                title="❌ Playlist Not Found",
                description=f"You don't have a playlist named **{name}**!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        tracks = playlists[name]

        if not tracks:
            embed = discord.Embed(
                title=f"📁 {name}",
                description="This playlist is empty!",
                color=0xFFA500
            )
        else:
            embed = discord.Embed(
                title=f"📁 {name}",
                description=f"{len(tracks)} tracks in this playlist:",
                color=0x1DB954
            )

            for i, track in enumerate(tracks[:10], 1):
                embed.add_field(
                    name=f"{i}. {track['title'][:40]}",
                    value=f"by {track['author'][:30]}",
                    inline=False
                )

            if len(tracks) > 10:
                embed.set_footer(text=f"And {len(tracks) - 10} more tracks...")

        await ctx.send(embed=embed)


class FilterCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_filters = {}
        self.emoji = EmojiConfig()

    @commands.hybrid_group(invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def filter(self, ctx: commands.Context):
        """Audio filter system"""
        embed = discord.Embed(
            title=f"{self.emoji.FILTER} Audio Filters",
            description="Enhance your music experience with various audio effects!",
            color=0x1DB954
        )
        embed.add_field(
            name="Available Commands",
            value="• `filter enable` - Enable audio filters\n• `filter disable` - Disable all filters",
            inline=False
        )
        embed.add_field(
            name="Current Filter",
            value=f"`{self.active_filters.get(ctx.guild.id, 'None')}`",
            inline=True
        )
        await ctx.send(embed=embed)

    @filter.command(help="Enable audio filters.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def enable(self, ctx: commands.Context):
        player = ctx.voice_client
        if not player or not player.playing:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Music Playing",
                description="I'm not playing any music right now!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice is None or ctx.author.voice.channel != player.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        current_filter = self.active_filters.get(ctx.guild.id, "None")
        embed = discord.Embed(
            title=f"{self.emoji.FILTER} Enable Audio Filter",
            description="Choose an audio filter to apply to the current track:",
            color=0x1DB954
        )
        embed.add_field(name="Current Filter", value=f"`{current_filter}`", inline=False)

        await ctx.send(embed=embed, view=FilterSelectView(player, ctx))

    @filter.command(help="Disable all audio filters.")
    @blacklist_check()
    @ignore_check()
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def disable(self, ctx: commands.Context):
        player = ctx.voice_client
        if not player or not player.playing:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} No Music Playing",
                description="I'm not playing any music right now!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        if ctx.author.voice is None or ctx.author.voice.channel != player.channel:
            embed = discord.Embed(
                title=f"{self.emoji.ERROR} Wrong Voice Channel",
                description="You need to be in the same voice channel as me!",
                color=0xFF0000
            )
            await ctx.send(embed=embed)
            return

        filters = wavelink.Filters()
        await player.set_filters(filters)
        self.active_filters.pop(ctx.guild.id, None)

        embed = discord.Embed(
            title=f"{self.emoji.SUCCESS} Filters Disabled",
            description="All audio filters have been removed!",
            color=0x1DB954
        )
        await ctx.send(embed=embed)


class HelpView(View):
    def __init__(self, ctx):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.current_page = 0
        self.pages = self.create_help_pages()
        self.emoji = EmojiConfig()

    def create_help_pages(self):
        pages = []

        # Page 1: Basic Commands
        embed1 = discord.Embed(
            title="🎵 DrakLeafX Music Bot - Help Menu",
            description="**Complete Music System with High Quality Audio**\n\n**Prefixes:** `x!` `/`",
            color=0x1DB954
        )
        embed1.add_field(
            name="🎶 Basic Music Commands",
            value=(
                "`x!play <query>` - Play music from YouTube/Spotify\n"
                "`x!search <query>` - Search music across platforms\n"
                "`x!nowplaying` - Show current track info\n"
                "`x!queue` - Show current queue\n"
                "`x!skip` - Skip current track\n"
                "`x!pause` - Pause playback\n"
                "`x!resume` - Resume playback\n"
                "`x!stop` - Stop playback and clear queue\n"
                "`x!volume <1-200>` - Adjust volume"
            ),
            inline=False
        )
        embed1.set_footer(text="Page 1/4 - Use buttons below to navigate")
        pages.append(embed1)

        # Page 2: Advanced Controls
        embed2 = discord.Embed(
            title="🎛️ Advanced Music Controls",
            description="**Enhanced Music Management Features**",
            color=0x1DB954
        )
        embed2.add_field(
            name="🔧 Player Controls",
            value=(
                "`x!loop` - Toggle loop mode\n"
                "`x!shuffle` - Shuffle queue\n"
                "`x!seek <seconds>` - Seek to position\n"
                "`x!replay` - Replay current track\n"
                "`x!previous` - Play previous track\n"
                "`x!autoplay` - Toggle autoplay\n"
                "`x!clearqueue` - Clear entire queue\n"
                "`x!join` - Join voice channel\n"
                "`x!disconnect` - Leave voice channel"
            ),
            inline=False
        )
        embed2.set_footer(text="Page 2/4 - Use buttons below to navigate")
        pages.append(embed2)

        # Page 3: Playlist & Filters
        embed3 = discord.Embed(
            title="📂 Playlists & Audio Effects",
            description="**Personal Playlists and Audio Enhancement**",
            color=0x1DB954
        )
        embed3.add_field(
            name="📂 Playlist Commands",
            value=(
                "`x!createplaylist <name>` - Create playlist\n"
                "`x!playlists` - View your playlists\n"
                "`x!playplaylist <name>` - Play saved playlist\n"
                "`x!deleteplaylist <name>` - Delete playlist\n"
                "`x!viewplaylist <name>` - View playlist tracks"
            ),
            inline=False
        )
        embed3.add_field(
            name="🎛️ Audio Filters",
            value=(
                "`x!filter enable` - Enable audio filters\n"
                "`x!filter disable` - Disable all filters\n"
                "**Filters:** Nightcore, Bass Boost, Vaporwave, Karaoke, Tremolo, Vibrato, Rotation, Distortion"
            ),
            inline=False
        )
        embed3.set_footer(text="Page 3/4 - Use buttons below to navigate")
        pages.append(embed3)

        # Page 4: Features & Support
        embed4 = discord.Embed(
            title="🌟 Features & Support",
            description="**Advanced Features and Bot Information**",
            color=0x1DB954
        )
        embed4.add_field(
            name="🚀 Premium Features",
            value=(
                "• **High Quality Audio** - 384kbps streaming\n"
                "• **Multi-Platform Support** - YouTube, Spotify, SoundCloud\n"
                "• **Advanced Controls** - Beautiful interactive player\n"
                "• **Audio Filters** - Professional sound effects\n"
                "• **Playlist System** - Personal music collections\n"
                "• **Spotify Integration** - Direct link support\n"
                "• **Auto-Cleanup** - Smart message management"
            ),
            inline=False
        )
        embed4.set_footer(text="Page 4/4 - Thanks for using Me!")
        pages.append(embed4)

        return pages

    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary)
    async def first_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = 0
        await interaction.response.edit_message(embed=self.pages[self.current_page])

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.primary)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = max(0, self.current_page - 1)
        await interaction.response.edit_message(embed=self.pages[self.current_page])

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.primary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = min(len(self.pages) - 1, self.current_page + 1)
        await interaction.response.edit_message(embed=self.pages[self.current_page])

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary)
    async def last_page(self, interaction: discord.Interaction, button: Button):
        self.current_page = len(self.pages) - 1
        await interaction.response.edit_message(embed=self.pages[self.current_page])


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", usage="help", help="Shows all available commands with details.")
    async def help_command(self, ctx: commands.Context):
        """Show comprehensive help menu"""
        view = HelpView(ctx)
        await ctx.send(embed=view.pages[0], view=view)


class _music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji = EmojiConfig()

    def help_custom(self):
        emoji = self.emoji.MUSICAL_NOTES
        label = "Music Commands"
        description = "Complete music system with advanced controls and high quality audio"
        return emoji, label, description


# Bot setup
intents = discord.Intents.all()


def load_bot_token():
    """Load Discord bot token from config or environment"""
    try:
        with open('bot_config.json', 'r') as f:
            config = json.load(f)
            token = config.get('discord_token') or os.environ.get('DISCORD_TOKEN')
            if token and token.strip():
                return token
    except FileNotFoundError:
        pass
    return os.environ.get('DISCORD_TOKEN')


class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=['x!', '/'], intents=intents, help_command=None)
        self.session = None
        self.music_db = MusicDatabase()

    async def setup_hook(self):
        """Called when bot is starting"""
        self.session = aiohttp.ClientSession()
        await self.music_db.connect()
        self.update_presence.start()

        # Load cogs
        await self.add_cog(Music(self))
        await self.add_cog(FilterCog(self))
        await self.add_cog(HelpCog(self))
        await self.add_cog(_music(self))
        print("✅ All cogs loaded successfully!")

        # Sync application commands
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash command(s)")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")

    async def close(self):
        """Called when bot is closing"""
        if self.session:
            await self.session.close()
        if self.music_db:
            await self.music_db.close()
        await super().close()

    @tasks.loop(minutes=5)
    async def update_presence(self):
        """Update bot presence with server stats"""
        try:
            total_members = sum(guild.member_count for guild in self.guilds)

            activity = discord.Activity(
                type=discord.ActivityType.streaming,
                name=f"{len(self.guilds)} Servers | {total_members} Members",
                details="Ultra HD Music Player - 384kbps",
                state="Prefix: x!",
                url="https://twitch.tv/discord"
            )

            await self.change_presence(
                activity=activity,
                status=discord.Status.online
            )
        except Exception as e:
            print(f"❌ Error updating presence: {e}")

    @update_presence.before_loop
    async def before_update_presence(self):
        """Wait until the bot is ready before starting the loop"""
        await self.wait_until_ready()


bot = MusicBot()


def main():
    """Main function to start the bot"""
    token = load_bot_token()

    if not token:
        print("❌ ERROR: Discord bot token not found!")
        print("Please set DISCORD_TOKEN in environment variables or add 'discord_token' to bot_config.json")
        return

    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ ERROR: Invalid Discord token!")
    except Exception as e:
        print(f"❌ ERROR: Failed to start bot: {e}")


if __name__ == "__main__":
    main()
