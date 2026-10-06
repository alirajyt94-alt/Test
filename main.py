import os
import sys
import json
import re
import io
import base64
import random
import asyncio
import datetime
import subprocess
from typing import Optional, List, cast

# ---------------- AUTO INSTALL ----------------
def _ensure(pkg, import_name=None):
    try:
        __import__(import_name or pkg)
    except ImportError:
        print(f"Installing {pkg}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

for p, i in [("discord.py", "discord"), ("wavelink", "wavelink"),
             ("Pillow", "PIL"), ("aiohttp", "aiohttp"), ("aiosqlite", "aiosqlite")]:
    _ensure(p, i)

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View, Select
import wavelink
import aiohttp

# ---------------- EMOJI ----------------
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
            print("✅ Emojis loaded")
        except Exception as ex:
            print(f"⚠️ Emoji load failed ({ex}), using defaults")
            self._defaults()

    def _defaults(self):
        self.PLAY="▶️"; self.PAUSE="⏸️"; self.RESUME="▶️"; self.STOP="⏹️"
        self.SKIP="⏭️"; self.PREVIOUS="⏮️"; self.REPEAT="🔁"; self.SHUFFLE="🔀"
        self.VOLUME_UP="🔊"; self.VOLUME_DOWN="🔉"; self.VOLUME_MUTE="🔇"
        self.VOLUME_LOW="🔈"; self.VOLUME_HIGH="🔊"
        self.SUCCESS="✅"; self.ERROR="❌"; self.WARNING="⚠️"
        self.INFO="ℹ️"; self.LOADING="⏳"; self.SEARCH="🔍"
        self.SPOTIFY="🎧"; self.YOUTUBE="▶️"; self.SOUNDCLOUD="☁️"
        self.FILTER="🎛️"; self.MICROPHONE="🎤"; self.MUSICAL_NOTE="🎵"
        self.MUSICAL_NOTES="🎶"; self.RADIO="📻"; self.QUALITY="💎"
        self.QUEUE="📜"; self.CLEAR="🗑️"; self.ADD="➕"; self.CLOCK="🕒"


EMOJI = EmojiConfig()

# ---------------- CONFIG ----------------
def _load_cfg():
    cfg = {}
    try:
        with open('bot_config.json', 'r') as f:
            cfg = json.load(f)
    except FileNotFoundError:
        pass
    return {
        "token": cfg.get("discord_token") or os.environ.get("DISCORD_TOKEN"),
        "lavalink_uri": cfg.get("lavalink_uri") or os.environ.get("LAVALINK_URI") or "https://lava-v4.ajieblogs.eu.org:443/",
        "lavalink_password": cfg.get("lavalink_password") or os.environ.get("LAVALINK_PASSWORD") or "https://dsc.gg/ajidevserver",
        "spotify_id": cfg.get("spotify_client_id") or os.environ.get("SPOTIFY_CLIENT_ID"),
        "spotify_secret": cfg.get("spotify_client_secret") or os.environ.get("SPOTIFY_CLIENT_SECRET"),
    }

CFG = _load_cfg()

# ---------------- SPOTIFY ----------------
SPOTIFY_TRACK_RE = re.compile(r"https?://open\.spotify\.com/track/([a-zA-Z0-9]+)")
SPOTIFY_PLAYLIST_RE = re.compile(r"https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)")
SPOTIFY_ALBUM_RE = re.compile(r"https?://open\.spotify\.com/album/([a-zA-Z0-9]+)")

class SpotifyAPI:
    BASE = "https://api.spotify.com/v1"
    def __init__(self, cid, csec):
        self.cid, self.csec = cid, csec
        self.token = None

    async def get_token(self):
        url = "https://accounts.spotify.com/api/token"
        auth = base64.b64encode(f"{self.cid}:{self.csec}".encode()).decode()
        headers = {"Authorization": f"Basic {auth}"}
        data = {"grant_type": "client_credentials"}
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers=headers, data=data) as r:
                if r.status != 200:
                    raise Exception(f"Spotify auth {r.status}")
                self.token = (await r.json()).get("access_token")

    async def get(self, endpoint):
        for attempt in range(2):
            if not self.token or attempt:
                await self.get_token()
            headers = {"Authorization": f"Bearer {self.token}"}
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{self.BASE}/{endpoint}", headers=headers) as r:
                    if r.status == 401 and attempt == 0:
                        continue
                    if r.status != 200:
                        raise Exception(f"Spotify {r.status}")
                    return await r.json()
        raise Exception("Spotify retries failed")

    async def track(self, tid): return await self.get(f"tracks/{tid}")
    async def playlist(self, pid): return await self.get(f"playlists/{pid}")
    async def album(self, aid): return await self.get(f"albums/{aid}")

spotify_api = None
if CFG["spotify_id"] and CFG["spotify_secret"]:
    spotify_api = SpotifyAPI(CFG["spotify_id"], CFG["spotify_secret"])
    print("✅ Spotify ready")
else:
    print("⚠️ Spotify not configured")

# ---------------- GLOBAL STATE ----------------
active_player_messages = {}   # guild_id -> discord.Message
track_histories = {}          # guild_id -> list of wavelink.Playable
pre_mute_volume = {}          # guild_id -> int


# ============================================================
# FILTER SELECT
# ============================================================
class FilterSelectView(View):
    def __init__(self, player: wavelink.Player):
        super().__init__(timeout=120)
        self.player = player

    @discord.ui.select(
        placeholder="🎛️ Choose an audio filter...",
        options=[
            discord.SelectOption(label="Nightcore", value="nightcore", emoji="🎵"),
            discord.SelectOption(label="Bass Boost", value="bassboost", emoji="🔊"),
            discord.SelectOption(label="Vaporwave", value="vaporwave", emoji="🌴"),
            discord.SelectOption(label="Karaoke", value="karaoke", emoji="🎤"),
            discord.SelectOption(label="Tremolo", value="tremolo", emoji="🎛️"),
            discord.SelectOption(label="Vibrato", value="vibrato", emoji="🎶"),
            discord.SelectOption(label="Rotation", value="rotation", emoji="🔄"),
            discord.SelectOption(label="Distortion", value="distortion", emoji="🎸"),
            discord.SelectOption(label="Clear All Filters", value="clear", emoji="🧹"),
        ]
    )
    async def select_filter(self, interaction: discord.Interaction, select: Select):
        name = select.values[0]
        filters = wavelink.Filters()
        desc = "Unknown filter"
        try:
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
                embed=discord.Embed(title=f"{EMOJI.FILTER} Filter", description=desc, color=0x1DB954),
                ephemeral=True
            )
        except Exception as e:
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ Filter error: {e}", ephemeral=True)


# ============================================================
# MUSIC CONTROL VIEW — fully working buttons
# ============================================================
class MusicControlView(View):
    """Persistent music control panel. Every button is a real @discord.ui.button."""

    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)  # persistent
        self.bot = bot

    async def _get_player(self, interaction: discord.Interaction) -> Optional[wavelink.Player]:
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player):
            await interaction.response.send_message(
                embed=discord.Embed(title=f"{EMOJI.ERROR} Not Connected",
                                    description="I'm not playing anything right now.",
                                    color=0xFF0000),
                ephemeral=True)
            return None
        return player

    async def _ensure_same_vc(self, interaction: discord.Interaction, player: wavelink.Player) -> bool:
        user_vc = interaction.user.voice.channel if interaction.user.voice else None
        if not user_vc or user_vc != player.channel:
            await interaction.response.send_message(
                embed=discord.Embed(title=f"{EMOJI.ERROR} Wrong Voice Channel",
                                    description="Join my voice channel to control playback.",
                                    color=0xFF0000),
                ephemeral=True)
            return False
        return True

    # ---------- ROW 0 ----------
    @discord.ui.button(emoji="⏮️", style=discord.ButtonStyle.secondary,
                       custom_id="mc_previous", row=0)
    async def previous_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        if not await self._ensure_same_vc(interaction, player): return
        hist = track_histories.get(interaction.guild.id, [])
        if len(hist) < 2:
            return await interaction.response.send_message(
                embed=discord.Embed(title=f"{EMOJI.ERROR} No History", color=0xFF0000),
                ephemeral=True)
        # hist[-1] is current, we want the one before it
        prev_track = hist[-2]
        hist.pop()  # drop current from history
        await player.play(prev_track)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.PREVIOUS} Previous",
                                description=f"**{prev_track.title}**", color=0x1DB954),
            ephemeral=True)

    @discord.ui.button(emoji="⏸️", style=discord.ButtonStyle.primary,
                       custom_id="mc_pause_resume", row=0)
    async def pause_resume_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        if not await self._ensure_same_vc(interaction, player): return
        if not player.playing and not player.paused:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        if player.paused:
            await player.pause(False)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"{EMOJI.PLAY} Resumed", color=0x1DB954), ephemeral=True)
        else:
            await player.pause(True)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"{EMOJI.PAUSE} Paused", color=0x1DB954), ephemeral=True)

    @discord.ui.button(emoji="⏹️", style=discord.ButtonStyle.danger,
                       custom_id="mc_stop", row=0)
    async def stop_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        if not await self._ensure_same_vc(interaction, player): return

        # remove NP message
        msg = active_player_messages.pop(interaction.guild.id, None)
        if msg:
            try: await msg.delete()
            except Exception: pass

        player.queue.clear()
        await player.disconnect()
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.STOP} Stopped",
                                description="Playback stopped and disconnected.",
                                color=0x1DB954),
            ephemeral=True)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.secondary,
                       custom_id="mc_skip", row=0)
    async def skip_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        if not await self._ensure_same_vc(interaction, player): return
        if not player.playing:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        await player.skip(force=True)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.SKIP} Skipped", color=0x1DB954), ephemeral=True)

    @discord.ui.button(emoji="🔄", style=discord.ButtonStyle.secondary,
                       custom_id="mc_replay", row=0)
    async def replay_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        if not await self._ensure_same_vc(interaction, player): return
        if not player.current:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        await player.seek(0)
        await interaction.response.send_message(
            embed=discord.Embed(title="🔄 Replaying", color=0x1DB954), ephemeral=True)

    # ---------- ROW 1 ----------
    @discord.ui.button(emoji="🔇", style=discord.ButtonStyle.secondary,
                       custom_id="mc_mute", row=1)
    async def mute_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        if not await self._ensure_same_vc(interaction, player): return
        gid = interaction.guild.id
        if gid in pre_mute_volume:
            await player.set_volume(pre_mute_volume.pop(gid))
            await interaction.response.send_message(
                embed=discord.Embed(title=f"{EMOJI.VOLUME_HIGH} Unmuted",
                                    description=f"Volume: **{player.volume}%**",
                                    color=0x1DB954),
                ephemeral=True)
        else:
            pre_mute_volume[gid] = player.volume
            await player.set_volume(0)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"{EMOJI.VOLUME_MUTE} Muted", color=0x1DB954),
                ephemeral=True)

    @discord.ui.button(emoji="🔉", style=discord.ButtonStyle.primary,
                       custom_id="mc_vol_down", row=1)
    async def vol_down_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        if not await self._ensure_same_vc(interaction, player): return
        new_vol = max(0, player.volume - 10)
        await player.set_volume(new_vol)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.VOLUME_DOWN} Volume Down",
                                description=f"**{new_vol}%**", color=0x1DB954),
            ephemeral=True)

    @discord.ui.button(emoji="🔊", style=discord.ButtonStyle.primary,
                       custom_id="mc_vol_up", row=1)
    async def vol_up_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        if not await self._ensure_same_vc(interaction, player): return
        new_vol = min(200, player.volume + 10)
        await player.set_volume(new_vol)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.VOLUME_UP} Volume Up",
                                description=f"**{new_vol}%**", color=0x1DB954),
            ephemeral=True)

    # ---------- ROW 2 ----------
    @discord.ui.button(emoji="📜", style=discord.ButtonStyle.secondary,
                       custom_id="mc_show_queue", row=2, label="Queue")
    async def queue_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        embed = _build_queue_embed(player)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(emoji="🔀", style=discord.ButtonStyle.secondary,
                       custom_id="mc_shuffle", row=2)
    async def shuffle_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        if not await self._ensure_same_vc(interaction, player): return
        if player.queue.is_empty:
            return await interaction.response.send_message("❌ Queue empty.", ephemeral=True)
        current = player.queue[0]  # keep first as next
        rest = list(player.queue)[1:]
        random.shuffle(rest)
        player.queue.clear()
        for t in [current] + rest:
            player.queue.put(t)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.SHUFFLE} Shuffled",
                                description=f"Shuffled **{len(rest)}** upcoming tracks.",
                                color=0x1DB954),
            ephemeral=True)

    @discord.ui.button(emoji="🎛️", style=discord.ButtonStyle.success,
                       custom_id="mc_filters", row=2, label="Filters")
    async def filters_btn(self, interaction: discord.Interaction, button: Button):
        player = await self._get_player(interaction)
        if not player: return
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.FILTER} Audio Filters",
                                description="Select a filter below:",
                                color=0x1DB954),
            view=FilterSelectView(player),
            ephemeral=True)


# ============================================================
# QUEUE EMBED BUILDER
# ============================================================
def _build_queue_embed(player: wavelink.Player) -> discord.Embed:
    embed = discord.Embed(title=f"{EMOJI.QUEUE} Music Queue", color=0x1DB954)
    if player.current:
        cur = player.current
        d = f"{cur.length // 60000}:{(cur.length // 1000) % 60:02d}"
        embed.add_field(name="🎵 Now Playing",
                        value=f"**{cur.title[:60]}**\nby *{cur.author[:40]}* `[{d}]`",
                        inline=False)
    if player.queue.is_empty:
        embed.add_field(name="Up Next", value="*Queue is empty*", inline=False)
        return embed

    upcoming = list(player.queue)[:10]
    lines = []
    for i, t in enumerate(upcoming, 1):
        d = f"{t.length // 60000}:{(t.length // 1000) % 60:02d}"
        lines.append(f"`{i:>2}.` **{t.title[:45]}** — *{t.author[:25]}* `[{d}]`")
    embed.add_field(name=f"Up Next ({len(player.queue)} tracks)",
                    value="\n".join(lines), inline=False)
    if len(player.queue) > 10:
        embed.set_footer(text=f"+{len(player.queue) - 10} more tracks")
    else:
        total = sum(t.length for t in player.queue)
        embed.set_footer(text=f"Total queue time: {total // 60000}:{(total // 1000) % 60:02d}")
    return embed


# ============================================================
# MUSIC COG
# ============================================================
class Music(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        await self._connect_nodes()

    async def _connect_nodes(self):
        try:
            node = wavelink.Node(uri=CFG["lavalink_uri"], password=CFG["lavalink_password"])
            await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=None)
            print("🎵 Lavalink connected")
        except Exception as e:
            print(f"❌ Lavalink failed: {e}")

    # ---------------- Helper methods ----------------
    async def _ensure_voice(self, interaction: discord.Interaction) -> Optional[wavelink.Player]:
        """Ensure bot is connected to user's VC, return player."""
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send(
                embed=discord.Embed(title=f"{EMOJI.ERROR} Voice Required",
                                    description="Join a voice channel first.",
                                    color=0xFF0000),
                ephemeral=True)
            return None

        user_channel = interaction.user.voice.channel
        player = interaction.guild.voice_client
        if not player:
            try:
                player = await user_channel.connect(cls=wavelink.Player, self_deaf=True)
                await player.set_volume(100)
            except Exception as e:
                await interaction.followup.send(f"❌ Join failed: {e}", ephemeral=True)
                return None
        elif player.channel != user_channel:
            await player.move_to(user_channel)
        return player

    async def _play_next_from_queue(self, player: wavelink.Player, interaction: Optional[discord.Interaction] = None):
        """Play the next track in queue."""
        if player.queue.is_empty:
            return
        track = player.queue.get()
        await player.play(track)
        # send new now-playing embed
        if interaction:
            await self._send_now_playing(interaction, track)
        else:
            # track ended automatically — reuse stored ctx/channel
            channel = getattr(player, "_np_channel", None)
            author = getattr(player, "_np_author", None)
            if channel:
                await self._send_now_playing_channel(channel, author, track)

    async def _send_now_playing(self, interaction: discord.Interaction, track: wavelink.Playable):
        embed = self._build_np_embed(track, interaction.user)
        view = MusicControlView(self.bot)
        msg = await interaction.followup.send(embed=embed, view=view, wait=True)
        active_player_messages[interaction.guild.id] = msg

    async def _send_now_playing_channel(self, channel: discord.TextChannel, author, track: wavelink.Playable):
        embed = self._build_np_embed(track, author)
        view = MusicControlView(self.bot)
        try:
            old = active_player_messages.pop(channel.guild.id, None)
            if old:
                try: await old.delete()
                except Exception: pass
            msg = await channel.send(embed=embed, view=view)
            active_player_messages[channel.guild.id] = msg
        except Exception as e:
            print(f"NP send failed: {e}")

    def _build_np_embed(self, track: wavelink.Playable, requester) -> discord.Embed:
        sec = track.length // 1000
        duration = f"{sec // 60}:{sec % 60:02d}"
        uri = (track.uri or "").lower()
        if "spotify" in uri:
            src = f"{EMOJI.SPOTIFY} Spotify"
        elif "youtube" in uri or "youtu.be" in uri:
            src = f"{EMOJI.YOUTUBE} YouTube"
        elif "soundcloud" in uri:
            src = f"{EMOJI.SOUNDCLOUD} SoundCloud"
        else:
            src = f"{EMOJI.MUSICAL_NOTE} Unknown"

        embed = discord.Embed(title=f"{EMOJI.MUSICAL_NOTES} Now Playing", color=0x1DB954)
        embed.add_field(name="Track", value=f"**{track.title[:70]}**", inline=False)
        embed.add_field(name="Artist", value=f"`{track.author[:40]}`", inline=True)
        embed.add_field(name="Duration", value=f"`{duration}`", inline=True)
        embed.add_field(name="Source", value=src, inline=True)
        if track.artwork:
            embed.set_image(url=track.artwork)
        embed.set_footer(text=f"Requested by {requester.display_name}",
                         icon_url=getattr(requester.display_avatar, "url", None))
        return embed

    async def _search_and_play(self, interaction: discord.Interaction, query: str):
        player = await self._ensure_voice(interaction)
        if not player: return

        # Spotify handling
        if spotify_api:
            if SPOTIFY_TRACK_RE.match(query):
                return await self._spotify_track(interaction, player, query)
            if SPOTIFY_PLAYLIST_RE.match(query):
                return await self._spotify_playlist(interaction, player, query, "playlist")
            if SPOTIFY_ALBUM_RE.match(query):
                return await self._spotify_playlist(interaction, player, query, "album")

        # regular search
        await interaction.followup.send(
            embed=discord.Embed(title=f"{EMOJI.SEARCH} Searching",
                                description=f"`{query[:80]}`", color=0x1DB954),
            ephemeral=True)

        try:
            results = await wavelink.Playable.search(query)
        except Exception as e:
            return await interaction.followup.send(f"❌ Search error: {e}", ephemeral=True)

        if not results:
            return await interaction.followup.send("❌ No results found.", ephemeral=True)

        if isinstance(results, wavelink.Playlist):
            for t in results.tracks:
                player.queue.put(t)
            await interaction.followup.send(
                embed=discord.Embed(title=f"{EMOJI.ADD} Playlist Queued",
                                    description=f"**{results.name}** — {len(results.tracks)} tracks",
                                    color=0x1DB954),
                ephemeral=True)
        else:
            track = results[0]
            if player.playing or player.paused or player.current:
                player.queue.put(track)
                await interaction.followup.send(
                    embed=discord.Embed(title=f"{EMOJI.ADD} Added to Queue",
                                        description=f"**{track.title[:70]}**",
                                        color=0x1DB954),
                    ephemeral=True)
                return
            else:
                await player.play(track)

        # store channel + author so we can send NP on auto-advance
        player._np_channel = interaction.channel
        player._np_author = interaction.user

        # If we started playing just now (nothing was playing)
        if player.current:
            await self._send_now_playing(interaction, player.current)

    async def _spotify_track(self, interaction, player, link):
        try:
            tid = SPOTIFY_TRACK_RE.search(link).group(1)
            info = await spotify_api.track(tid)
            title = info["name"]
            author = ", ".join(a["name"] for a in info["artists"])
            results = await wavelink.Playable.search(f"{title} {author}")
            if not results:
                return await interaction.followup.send("❌ Not available on YouTube.", ephemeral=True)
            track = results[0] if not isinstance(results, wavelink.Playlist) else results.tracks[0]
            if player.playing or player.paused or player.current:
                player.queue.put(track)
                await interaction.followup.send(
                    embed=discord.Embed(title=f"{EMOJI.SPOTIFY} Spotify Track Queued",
                                        description=f"**{track.title[:70]}**", color=0x1DB954),
                    ephemeral=True)
            else:
                await player.play(track)
                player._np_channel = interaction.channel
                player._np_author = interaction.user
                await self._send_now_playing(interaction, track)
        except Exception as e:
            await interaction.followup.send(f"❌ Spotify error: {e}", ephemeral=True)

    async def _spotify_playlist(self, interaction, player, link, kind):
        await interaction.followup.send("⏳ Loading Spotify content...", ephemeral=True)
        try:
            if kind == "playlist":
                pid = SPOTIFY_PLAYLIST_RE.search(link).group(1)
                data = await spotify_api.playlist(pid)
                items = data.get("tracks", {}).get("items", [])
                name = data.get("name", "Playlist")
            else:
                aid = SPOTIFY_ALBUM_RE.search(link).group(1)
                data = await spotify_api.album(aid)
                items = data.get("tracks", {}).get("items", [])
                name = data.get("name", "Album")

            added = 0
            for it in items:
                entry = it.get("track") or it
                if not entry: continue
                t = entry.get("name", "")
                a = ", ".join(x["name"] for x in entry.get("artists", []))
                try:
                    res = await wavelink.Playable.search(f"{t} {a}")
                    if res:
                        tr = res[0] if not isinstance(res, wavelink.Playlist) else res.tracks[0]
                        player.queue.put(tr)
                        added += 1
                except Exception:
                    continue

            await interaction.followup.send(
                embed=discord.Embed(title=f"{EMOJI.SPOTIFY} Spotify {kind.title()} Queued",
                                    description=f"**{name}** — {added} tracks added",
                                    color=0x1DB954),
                ephemeral=True)

            if not player.current and not player.playing:
                await self._play_next_from_queue(player, interaction)
                player._np_channel = interaction.channel
                player._np_author = interaction.user
                if player.current:
                    await self._send_now_playing(interaction, player.current)
        except Exception as e:
            await interaction.followup.send(f"❌ Spotify error: {e}", ephemeral=True)

    # ============================================================
    # SLASH COMMANDS
    # ============================================================
    @app_commands.command(name="play", description="Play a song or add it to the queue")
    @app_commands.describe(query="Song name or URL (YouTube / Spotify / SoundCloud)")
    async def play(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        await self._search_and_play(interaction, query)

    @app_commands.command(name="search", description="Search YouTube and pick a result")
    @app_commands.describe(query="Search query")
    async def search(self, interaction: discord.Interaction, query: str):
        await interaction.response.defer()
        if not interaction.user.voice:
            return await interaction.followup.send("❌ Join a voice channel first.", ephemeral=True)
        try:
            results = await wavelink.Playable.search(query)
        except Exception as e:
            return await interaction.followup.send(f"❌ Search error: {e}", ephemeral=True)
        if not results:
            return await interaction.followup.send("❌ No results.", ephemeral=True)
        tracks = results.tracks[:10] if isinstance(results, wavelink.Playlist) else list(results)[:10]
        view = SearchResultView(self, tracks, interaction.user)
        await interaction.followup.send(
            embed=discord.Embed(title=f"{EMOJI.SEARCH} Search Results",
                                description="Pick a track from the dropdown below.",
                                color=0x1DB954),
            view=view, ephemeral=True)

    @app_commands.command(name="pause", description="Pause the current track")
    async def pause(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.playing:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        await player.pause(True)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.PAUSE} Paused", color=0x1DB954))

    @app_commands.command(name="resume", description="Resume playback")
    async def resume(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.paused:
            return await interaction.response.send_message("❌ Nothing paused.", ephemeral=True)
        await player.pause(False)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.PLAY} Resumed", color=0x1DB954))

    @app_commands.command(name="skip", description="Skip the current track")
    async def skip(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.playing:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        await player.skip(force=True)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.SKIP} Skipped", color=0x1DB954))

    @app_commands.command(name="stop", description="Stop and disconnect")
    async def stop(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player):
            return await interaction.response.send_message("❌ Not connected.", ephemeral=True)
        msg = active_player_messages.pop(interaction.guild.id, None)
        if msg:
            try: await msg.delete()
            except Exception: pass
        player.queue.clear()
        await player.disconnect()
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.STOP} Stopped", color=0x1DB954))

    @app_commands.command(name="queue", description="Show the current queue")
    async def queue(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player):
            return await interaction.response.send_message("❌ Not connected.", ephemeral=True)
        await interaction.response.send_message(embed=_build_queue_embed(player))

    @app_commands.command(name="nowplaying", description="Show what's currently playing")
    async def nowplaying(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        t = player.current
        pos = player.position / 1000
        length = t.length / 1000
        bar_len = 20
        fill = int(bar_len * (pos / length)) if length else 0
        bar = "█" * fill + "▬" * (bar_len - fill)
        embed = discord.Embed(title=f"{EMOJI.MUSICAL_NOTES} Now Playing", color=0x1DB954)
        embed.add_field(name="Track", value=f"**{t.title[:70]}**", inline=False)
        embed.add_field(name="Artist", value=f"`{t.author[:40]}`", inline=True)
        embed.add_field(name="Progress",
                        value=f"`{int(pos // 60)}:{int(pos % 60):02d}` {bar} `{int(length // 60)}:{int(length % 60):02d}`",
                        inline=False)
        if t.artwork:
            embed.set_thumbnail(url=t.artwork)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="volume", description="Change playback volume (1-200)")
    @app_commands.describe(level="Volume level")
    async def volume(self, interaction: discord.Interaction, level: app_commands.Range[int, 0, 200]):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player):
            return await interaction.response.send_message("❌ Not connected.", ephemeral=True)
        await player.set_volume(level)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.VOLUME_HIGH} Volume set to {level}%", color=0x1DB954))

    @app_commands.command(name="clearqueue", description="Clear the music queue")
    async def clearqueue(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player):
            return await interaction.response.send_message("❌ Not connected.", ephemeral=True)
        n = len(player.queue)
        player.queue.clear()
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.CLEAR} Queue Cleared",
                                description=f"Removed **{n}** tracks.",
                                color=0x1DB954))

    @app_commands.command(name="shuffle", description="Shuffle the queue")
    async def shuffle(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player) or player.queue.is_empty:
            return await interaction.response.send_message("❌ Queue is empty.", ephemeral=True)
        current = player.queue[0] if not player.queue.is_empty else None
        rest = list(player.queue)
        random.shuffle(rest)
        player.queue.clear()
        for t in rest:
            player.queue.put(t)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.SHUFFLE} Shuffled",
                                description=f"Shuffled **{len(rest)}** tracks.",
                                color=0x1DB954))

    @app_commands.command(name="loop", description="Toggle loop mode")
    async def loop(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.playing:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        player.queue.mode = (wavelink.QueueMode.loop
                             if player.queue.mode != wavelink.QueueMode.loop
                             else wavelink.QueueMode.normal)
        state = "enabled 🔁" if player.queue.mode == wavelink.QueueMode.loop else "disabled"
        await interaction.response.send_message(
            embed=discord.Embed(title=f"Loop {state}", color=0x1DB954))

    @app_commands.command(name="seek", description="Seek to a position (in seconds)")
    @app_commands.describe(seconds="Position in seconds")
    async def seek(self, interaction: discord.Interaction, seconds: int):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        if seconds < 0 or seconds * 1000 > player.current.length:
            return await interaction.response.send_message("❌ Invalid position.", ephemeral=True)
        await player.seek(seconds * 1000)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"⏩ Seeked to {seconds}s", color=0x1DB954))

    @app_commands.command(name="replay", description="Replay the current track from the start")
    async def replay(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.current:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        await player.seek(0)
        await interaction.response.send_message(
            embed=discord.Embed(title="🔄 Replaying", color=0x1DB954))

    @app_commands.command(name="join", description="Join your voice channel")
    async def join(self, interaction: discord.Interaction):
        if not interaction.user.voice:
            return await interaction.response.send_message("❌ Join a voice channel first.", ephemeral=True)
        vc = interaction.guild.voice_client
        if vc and vc.channel == interaction.user.voice.channel:
            return await interaction.response.send_message("✅ Already in your channel.", ephemeral=True)
        if vc:
            await vc.move_to(interaction.user.voice.channel)
        else:
            await interaction.user.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.SUCCESS} Joined {interaction.user.voice.channel.mention}",
                                color=0x1DB954))

    @app_commands.command(name="disconnect", description="Disconnect from voice")
    async def disconnect(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player):
            return await interaction.response.send_message("❌ Not connected.", ephemeral=True)
        await player.disconnect()
        await interaction.response.send_message(
            embed=discord.Embed(title="👋 Disconnected", color=0x1DB954))

    @app_commands.command(name="filter", description="Open the audio filter menu")
    async def filter_cmd(self, interaction: discord.Interaction):
        player = interaction.guild.voice_client
        if not isinstance(player, wavelink.Player) or not player.playing:
            return await interaction.response.send_message("❌ Nothing playing.", ephemeral=True)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{EMOJI.FILTER} Audio Filters",
                                description="Pick a filter below:",
                                color=0x1DB954),
            view=FilterSelectView(player), ephemeral=True)

    @app_commands.command(name="help", description="Show all bot commands")
    async def help_cmd(self, interaction: discord.Interaction):
        embed = discord.Embed(title=f"{EMOJI.MUSICAL_NOTES} Music Bot Commands",
                              description="All commands use **slash** (`/`)",
                              color=0x1DB954)
        embed.add_field(name="🎶 Playback", value=(
            "`/play <song>` — Play from YouTube/Spotify/SoundCloud\n"
            "`/search <query>` — Pick from search results\n"
            "`/pause` `/resume` `/skip` `/stop`\n"
            "`/replay` `/seek <sec>` `/nowplaying`"
        ), inline=False)
        embed.add_field(name="🔊 Queue & Volume", value=(
            "`/queue` — Show queue\n"
            "`/clearqueue` `/shuffle` `/loop`\n"
            "`/volume <0-200>`"
        ), inline=False)
        embed.add_field(name="🎛️ Extras", value=(
            "`/filter` — Audio filters\n"
            "`/join` `/disconnect`"
        ), inline=False)
        embed.set_footer(text="Enjoy! 🎵")
        await interaction.response.send_message(embed=embed)

    # ============================================================
    # LAVALINK EVENTS
    # ============================================================
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        player, track = payload.player, payload.track
        if not player or not track: return
        track_histories.setdefault(player.guild.id, []).append(track)
        if len(track_histories[player.guild.id]) > 30:
            track_histories[player.guild.id].pop(0)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        player = payload.player
        if not player: return
        if player.queue.is_empty:
            # queue ended
            old = active_player_messages.pop(player.guild.id, None)
            if old:
                try: await old.delete()
                except Exception: pass
            try: await player.disconnect()
            except Exception: pass
            return

        next_track = player.queue.get()
        await player.play(next_track)

        # send new NP message in the same channel
        channel = getattr(player, "_np_channel", None)
        author = getattr(player, "_np_author", None)
        if channel:
            cog = self.bot.get_cog("Music")
            if cog:
                await cog._send_now_playing_channel(channel, author, next_track)


# ============================================================
# SEARCH RESULT VIEW
# ============================================================
class SearchResultView(View):
    def __init__(self, cog: Music, tracks: List[wavelink.Playable], user: discord.User):
        super().__init__(timeout=60)
        self.cog = cog
        self.tracks = tracks
        self.user = user

        options = []
        for i, t in enumerate(tracks[:10]):
            label = f"{t.title[:80]}".strip() or "Unknown"
            options.append(discord.SelectOption(
                label=label[:100],
                description=f"by {t.author[:50]}".strip() or "Unknown",
                value=str(i)))

        self.select = Select(placeholder="🎵 Pick a track...", options=options)
        self.select.callback = self._on_pick
        self.add_item(self.select)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message("❌ This menu isn't for you.", ephemeral=True)
            return False
        return True

    async def _on_pick(self, interaction: discord.Interaction):
        idx = int(self.select.values[0])
        track = self.tracks[idx]
        player = interaction.guild.voice_client
        if not player:
            try:
                player = await interaction.user.voice.channel.connect(cls=wavelink.Player, self_deaf=True)
                await player.set_volume(100)
            except Exception as e:
                return await interaction.response.send_message(f"❌ {e}", ephemeral=True)
        if player.playing or player.paused or player.current:
            player.queue.put(track)
            await interaction.response.send_message(
                embed=discord.Embed(title=f"{EMOJI.ADD} Added to Queue",
                                    description=f"**{track.title[:70]}**",
                                    color=0x1DB954),
                ephemeral=True)
        else:
            await player.play(track)
            player._np_channel = interaction.channel
            player._np_author = interaction.user
            await interaction.response.send_message(
                embed=discord.Embed(title=f"{EMOJI.PLAY} Now Playing",
                                    description=f"**{track.title[:70]}**",
                                    color=0x1DB954),
                ephemeral=True)
            await self.cog._send_now_playing_channel(interaction.channel, interaction.user, track)
        self.stop()


# ============================================================
# BOT CLIENT
# ============================================================
intents = discord.Intents.default()
intents.message_content = False
intents.voice_states = True
intents.guilds = True
intents.members = True


class MusicBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned, intents=intents, help_command=None)

    async def setup_hook(self):
        # persistent view for the music control panel
        self.add_view(MusicControlView(self))
        await self.add_cog(Music(self))
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash commands")
        except Exception as e:
            print(f"❌ Sync failed: {e}")

    async def on_ready(self):
        print(f"✅ Logged in as {self.user} ({self.user.id})")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening, name="/play"),
            status=discord.Status.online)


bot = MusicBot()


def main():
    if not CFG["token"]:
        print("❌ DISCORD_TOKEN not set (env or bot_config.json)")
        return
    try:
        bot.run(CFG["token"])
    except discord.LoginFailure:
        print("❌ Invalid token")
    except Exception as e:
        print(f"❌ Startup error: {e}")


if __name__ == "__main__":
    main()
