import os
import sys
import subprocess

def install_package(package):
    try:
        __import__(package)
    except ImportError:
        print(f"Installing {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

for pkg in ["discord.py", "wavelink", "Pillow", "aiohttp", "aiosqlite", "PyNaCl"]:
    name = {"discord.py": "discord", "Pillow": "PIL", "PyNaCl": "nacl"}.get(pkg, pkg)
    try:
        __import__(name)
    except ImportError:
        install_package(pkg)

import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import Button, View, Select
import wavelink
import aiohttp
import asyncio
import base64
import re
import json
import random

try:
    from music_database import MusicDatabase
except ImportError:
    class MusicDatabase:
        async def connect(self): pass
        async def close(self): pass
        async def register_server(self, *a, **k): pass
        async def register_voice_channel(self, *a, **k): pass
        async def log_music_play(self, *a, **k): pass
        async def log_search(self, *a, **k): pass


# ═══════════════════════════════════════════════════════════
# DESIGN
# ═══════════════════════════════════════════════════════════

class Colors:
    PRIMARY = 0x5865F2; SUCCESS = 0x57F287; WARNING = 0xFEE75C
    ERROR = 0xED4245; MUSIC = 0x1DB954; ACCENT = 0xEB459E; INFO = 0x00B0F4

class E:
    PLAY="▶️";PAUSE="⏸️";STOP="⏹️";SKIP="⏭️";PREV="⏮️";REPLAY="🔄"
    SHUFFLE="🔀";LOOP="🔁";VOL_HIGH="🔊";VOL_LOW="🔉";VOL_MUTE="🔇"
    OK="✅";NO="❌";WARN="⚠️";INFO="ℹ️";LOAD="⏳";SEARCH="🔍";SPARKLE="✨"
    NOTE="🎵";NOTES="🎶";HEADPHONES="🎧";MIC="🎤";RADIO="📻"
    QUEUE="📜";LIST="📋";CLEAR="🗑️";ADD="➕";CLOCK="🕒";TIMER="⏱️"
    FILTER="🎛️";QUALITY="💎";SETTINGS="⚙️";MUSIC_BOX="🎼"


class Embed:
    @staticmethod
    def _fmt_ms(ms):
        s = int(ms // 1000)
        h, s = divmod(s, 3600); m, s = divmod(s, 60)
        return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

    @staticmethod
    def now_playing(track, player, requester=None):
        dur = Embed._fmt_ms(track.length)
        pos = player.position
        uri = (track.uri or "").lower()
        if "spotify" in uri: src, col = "Spotify", 0x1DB954
        elif "youtube" in uri or "youtu.be" in uri: src, col = "YouTube", 0xFF0000
        elif "soundcloud" in uri: src, col = "SoundCloud", 0xFF5500
        else: src, col = "Unknown", Colors.MUSIC

        embed = discord.Embed(
            title=f"{E.HEADPHONES}  Now Playing",
            description=(
                f"### [{track.title[:70]}]({track.uri})\n"
                f"{E.MIC} **{track.author[:50]}**\n\n"
                f"` {Embed._fmt_ms(pos)} ` {E.PLAY} ` {dur} `"),
            color=col)

        if requester:
            embed.set_footer(
                text=f"Requested by {requester.display_name}  •  {src}  •  384 kbps",
                icon_url=requester.display_avatar.url)
        else:
            embed.set_footer(text=f"{src}  •  384 kbps")

        if track.artwork:
            embed.set_thumbnail(url=track.artwork)

        vol_icon = E.VOL_MUTE if player.volume == 0 else (E.VOL_LOW if player.volume < 50 else E.VOL_HIGH)
        embed.add_field(name=f"{E.QUEUE} Queue", value=f"`{len(player.queue)}`", inline=True)
        embed.add_field(name=f"{vol_icon} Volume", value=f"`{player.volume}%`", inline=True)
        embed.add_field(name=f"{E.QUALITY} Quality", value="`Ultra HD`", inline=True)
        return embed

    @staticmethod
    def success(t, d=None): return discord.Embed(title=f"{E.OK}  {t}", description=d, color=Colors.SUCCESS)
    @staticmethod
    def error(t, d=None): return discord.Embed(title=f"{E.NO}  {t}", description=d, color=Colors.ERROR)
    @staticmethod
    def warning(t, d=None): return discord.Embed(title=f"{E.WARN}  {t}", description=d, color=Colors.WARNING)
    @staticmethod
    def info(t, d=None): return discord.Embed(title=f"{E.INFO}  {t}", description=d, color=Colors.INFO)

    @staticmethod
    def added(track, position, requester):
        dur = Embed._fmt_ms(track.length)
        e = discord.Embed(
            title=f"{E.ADD}  Added to Queue",
            description=(
                f"**[{track.title[:70]}]({track.uri})**\n"
                f"{E.MIC} {track.author[:50]}\n"
                f"{E.TIMER} `{dur}`  •  Position: `#{position}`"),
            color=Colors.MUSIC)
        if track.artwork: e.set_thumbnail(url=track.artwork)
        e.set_footer(text=f"Requested by {requester.display_name}",
                     icon_url=requester.display_avatar.url)
        return e

    @staticmethod
    def playlist_added(name, count, total_ms, requester):
        e = discord.Embed(
            title=f"{E.NOTES}  Playlist Added",
            description=f"**{name}**\n\n{E.QUEUE} **{count}** tracks\n{E.TIMER} Total: `{Embed._fmt_ms(total_ms)}`",
            color=Colors.MUSIC)
        e.set_footer(text=f"Requested by {requester.display_name}",
                     icon_url=requester.display_avatar.url)
        return e

    @staticmethod
    def queue_list(player, page=1, per_page=10):
        tracks = list(player.queue)
        total = len(tracks)
        max_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, max_pages))
        start = (page - 1) * per_page
        chunk = tracks[start:start + per_page]
        total_ms = sum(t.length for t in tracks)

        e = discord.Embed(
            title=f"{E.QUEUE}  Queue  •  Page {page}/{max_pages}",
            color=Colors.PRIMARY)

        if player.current:
            cur = player.current
            e.description = (
                f"**Currently Playing**\n"
                f"{E.PLAY} [{cur.title[:60]}]({cur.uri})\n"
                f"{E.MIC} {cur.author[:40]}\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━")
        else:
            e.description = "**Currently Playing**\nNothing."

        if total == 0:
            e.add_field(name="📭 Up Next", value="*The queue is empty.*", inline=False)
        else:
            for i, t in enumerate(chunk, start + 1):
                dur = Embed._fmt_ms(t.length)
                e.add_field(
                    name=f"`{i:>2}.` {t.title[:50]}",
                    value=f"{E.MIC} {t.author[:35]}  •  `{dur}`",
                    inline=False)

        footer = f"{total} track{'s' if total != 1 else ''}"
        if total: footer += f"  •  {Embed._fmt_ms(total_ms)}"
        if max_pages > 1: footer += f"  •  Page {page}/{max_pages}"
        e.set_footer(text=footer)
        return e

    @staticmethod
    def help_main(prefix="x!"):
        e = discord.Embed(
            title=f"{E.MUSIC_BOX}  Music Bot  —  Help",
            description=(
                f"**Prefix:** `{prefix}`  •  **Slash:** `/`  •  **Quality:** `384 kbps Ultra HD`\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"**{E.PLAY}  Playback**\n"
                f"`{prefix}play <song>`  •  `{prefix}pause`  •  `{prefix}resume`\n"
                f"`{prefix}skip`  •  `{prefix}stop`  •  `{prefix}replay`  •  `{prefix}previous`\n"
                f"`{prefix}seek <sec>`  •  `{prefix}nowplaying`\n\n"
                f"**{E.VOL_HIGH}  Volume & Queue**\n"
                f"`{prefix}volume <1-200>`  •  `{prefix}queue [page]`  •  `{prefix}clearqueue`\n"
                f"`{prefix}shuffle`  •  `{prefix}loop`\n\n"
                f"**{E.FILTER}  Effects**  •  `{prefix}filter`  •  `{prefix}autoplay`\n\n"
                f"**{E.LIST}  Playlists**\n"
                f"`{prefix}createplaylist <n>`  •  `{prefix}savequeue <n>`  •  `{prefix}playplaylist <n>`\n"
                f"`{prefix}viewplaylist <n>`  •  `{prefix}deleteplaylist <n>`  •  `{prefix}playlists`\n\n"
                f"**{E.HEADPHONES}  Voice**  •  `{prefix}join`  •  `{prefix}disconnect`\n\n"
                f"*All commands also work as slash commands!*"),
            color=Colors.MUSIC)
        e.set_footer(text="🎵 Enjoy the music!")
        return e


# ═══════════════════════════════════════════════════════════
# FILTER VIEW
# ═══════════════════════════════════════════════════════════

class FilterSelectView(View):
    def __init__(self):
        super().__init__(timeout=120)

    @discord.ui.select(
        placeholder="🎛️ Choose an audio filter…",
        options=[
            discord.SelectOption(label="Nightcore", value="nightcore", emoji="🌙"),
            discord.SelectOption(label="Bass Boost", value="bassboost", emoji="🔊"),
            discord.SelectOption(label="Vaporwave", value="vaporwave", emoji="🌴"),
            discord.SelectOption(label="Karaoke", value="karaoke", emoji="🎤"),
            discord.SelectOption(label="Tremolo", value="tremolo", emoji="〰️"),
            discord.SelectOption(label="Vibrato", value="vibrato", emoji="🎶"),
            discord.SelectOption(label="Rotation", value="rotation", emoji="🔄"),
            discord.SelectOption(label="Distortion", value="distortion", emoji="🎸"),
            discord.SelectOption(label="8D Audio", value="8d", emoji="🎧"),
            discord.SelectOption(label="Clear All", value="clear", emoji="🧹"),
        ])
    async def pick(self, interaction: discord.Interaction, select: Select):
        vc = interaction.guild.voice_client
        if not vc or not isinstance(vc, wavelink.Player):
            return await interaction.response.send_message(
                embed=Embed.error("Not Connected"), ephemeral=True)

        name = select.values[0]
        filters = wavelink.Filters()
        desc = ""

        if name == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.2, rate=1); desc = "🌙 Nightcore"
        elif name == "bassboost":
            filters.equalizer.set(bands=[{"band": i, "gain": g}
                                          for i, g in enumerate([0.9, 0.7, 0.5, 0.3, 0.1, 0.0])])
            desc = "🔊 Bass Boost"
        elif name == "vaporwave":
            filters.timescale.set(rate=0.8, pitch=0.9); desc = "🌴 Vaporwave"
        elif name == "karaoke":
            filters.karaoke.set(level=1.0, mono_level=1.0, filter_band=220.0, filter_width=100.0)
            desc = "🎤 Karaoke"
        elif name == "tremolo":
            filters.tremolo.set(depth=0.5, frequency=10.0); desc = "〰️ Tremolo"
        elif name == "vibrato":
            filters.vibrato.set(depth=0.5, frequency=5.0); desc = "🎶 Vibrato"
        elif name == "rotation":
            filters.rotation.set(rotation_hz=0.2); desc = "🔄 Rotation"
        elif name == "distortion":
            filters.distortion.set(sin_offset=0.0, sin_scale=1.0, cos_offset=0.0,
                                    cos_scale=1.0, tan_offset=0.0, tan_scale=1.0,
                                    offset=0.0, scale=1.0)
            desc = "🎸 Distortion"
        elif name == "8d":
            filters.rotation.set(rotation_hz=0.15)
            filters.tremolo.set(depth=0.3, frequency=4.0); desc = "🎧 8D Audio"
        elif name == "clear":
            filters = wavelink.Filters(); desc = "🧹 Cleared"

        await vc.set_filters(filters)
        await interaction.response.send_message(
            embed=discord.Embed(title=f"{E.SPARKLE}  Filter Applied",
                                description=desc, color=Colors.ACCENT),
            ephemeral=True)


# ═══════════════════════════════════════════════════════════
# MUSIC CONTROL VIEW — FIXED
# ═══════════════════════════════════════════════════════════

def get_vc(interaction: discord.Interaction):
    vc = interaction.guild.voice_client
    if vc and isinstance(vc, wavelink.Player):
        return vc
    return None


class MusicControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        vc = get_vc(interaction)
        if not vc or not vc.connected:
            try:
                await interaction.response.send_message(
                    embed=Embed.error("Not Connected", "I'm not in a voice channel."),
                    ephemeral=True)
            except Exception: pass
            return False
        member_ch = getattr(interaction.user.voice, "channel", None)
        if member_ch is None or member_ch.id != vc.channel.id:
            try:
                await interaction.response.send_message(
                    embed=Embed.error("Wrong Channel", "Join my voice channel first."),
                    ephemeral=True)
            except Exception: pass
            return False
        return True

    async def _run(self, interaction, fn):
        try:
            await fn()
        except discord.errors.InteractionResponded:
            pass
        except Exception as e:
            import traceback
            print(f"[BTN ERROR] {type(e).__name__}: {e}")
            traceback.print_exc()
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        embed=Embed.error("Error", f"`{type(e).__name__}: {e}`"),
                        ephemeral=True)
                else:
                    await interaction.followup.send(
                        embed=Embed.error("Error", f"`{type(e).__name__}: {e}`"),
                        ephemeral=True)
            except Exception: pass

    # ── Row 0 ──
    @discord.ui.button(emoji=E.PREV, style=discord.ButtonStyle.secondary,
                       custom_id="mc_prev", row=0)
    async def btn_prev(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            hist = track_histories.get(i.guild.id, [])
            if len(hist) < 2:
                return await i.response.send_message(
                    embed=Embed.error("No History"), ephemeral=True)
            hist.pop()
            prev = hist[-1]
            await vc.play(prev)
            await i.response.send_message(
                embed=Embed.success("Previous", f"**{prev.title[:60]}**"),
                ephemeral=True)
        await self._run(i, go)

    @discord.ui.button(emoji=E.PAUSE, style=discord.ButtonStyle.primary,
                       custom_id="mc_pr", row=0)
    async def btn_pr(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            if vc.paused:
                await vc.pause(False)
                await i.response.send_message(
                    embed=Embed.success("Resumed", f"{E.PLAY}"), ephemeral=True)
            else:
                await vc.pause(True)
                await i.response.send_message(
                    embed=Embed.warning("Paused", f"{E.PAUSE}"), ephemeral=True)
        await self._run(i, go)

    @discord.ui.button(emoji=E.STOP, style=discord.ButtonStyle.danger,
                       custom_id="mc_stop", row=0)
    async def btn_stop(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            gid = i.guild.id
            old = active_player_messages.pop(gid, None)
            if old:
                try: await old.delete()
                except Exception: pass
            if vc:
                vc.queue.clear()
                try: await vc.disconnect()
                except Exception: pass
            await i.response.send_message(
                embed=Embed.success("Stopped"), ephemeral=True)
        await self._run(i, go)

    @discord.ui.button(emoji=E.SKIP, style=discord.ButtonStyle.secondary,
                       custom_id="mc_skip", row=0)
    async def btn_skip(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            if not vc.playing and not vc.paused:
                return await i.response.send_message(
                    embed=Embed.error("Nothing Playing"), ephemeral=True)

            cur = vc.current.title[:50] if vc.current else "Unknown"
            has_next = not vc.queue.is_empty

            await i.response.send_message(
                embed=Embed.success(
                    "Skipped",
                    f"{E.SKIP} **{cur}**"
                    + ("" if has_next else "\n*Queue empty — stopping.*")),
                ephemeral=True)

            # Respond first, then stop (which fires on_wavelink_track_end)
            try:
                await vc.stop()
            except Exception as e:
                print(f"[SKIP] stop err: {e}")
                if has_next:
                    try:
                        nxt = await vc.queue.get_wait()
                        await vc.play(nxt)
                    except Exception as e2:
                        print(f"[SKIP] manual err: {e2}")
        await self._run(i, go)

    @discord.ui.button(emoji=E.REPLAY, style=discord.ButtonStyle.secondary,
                       custom_id="mc_replay", row=0)
    async def btn_replay(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            if not vc.playing:
                return await i.response.send_message(
                    embed=Embed.error("Nothing Playing"), ephemeral=True)
            await vc.seek(0)
            await i.response.send_message(
                embed=Embed.success("Replaying", f"{E.REPLAY}"), ephemeral=True)
        await self._run(i, go)

    # ── Row 1 ──
    @discord.ui.button(emoji=E.VOL_MUTE, style=discord.ButtonStyle.secondary,
                       custom_id="mc_mute", row=1)
    async def btn_mute(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            if not hasattr(vc, "_pmv"):
                vc._pmv = vc.volume
                await vc.set_volume(0)
                await i.response.send_message(
                    embed=Embed.success("Muted", f"{E.VOL_MUTE}"), ephemeral=True)
            else:
                await vc.set_volume(vc._pmv)
                delattr(vc, "_pmv")
                await i.response.send_message(
                    embed=Embed.success("Unmuted", f"{E.VOL_HIGH}"), ephemeral=True)
        await self._run(i, go)

    @discord.ui.button(emoji=E.VOL_LOW, style=discord.ButtonStyle.primary,
                       custom_id="mc_vd", row=1)
    async def btn_vd(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            await vc.set_volume(max(0, vc.volume - 20))
            await i.response.send_message(
                embed=Embed.success("Volume", f"{E.VOL_LOW} `{vc.volume}%`"),
                ephemeral=True)
        await self._run(i, go)

    @discord.ui.button(emoji=E.VOL_HIGH, style=discord.ButtonStyle.primary,
                       custom_id="mc_vu", row=1)
    async def btn_vu(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            await vc.set_volume(min(200, vc.volume + 20))
            await i.response.send_message(
                embed=Embed.success("Volume", f"{E.VOL_HIGH} `{vc.volume}%`"),
                ephemeral=True)
        await self._run(i, go)

    # ── Row 2 ──
    @discord.ui.button(emoji=E.QUEUE, style=discord.ButtonStyle.secondary,
                       custom_id="mc_q", row=2)
    async def btn_q(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            embed = Embed.queue_list(vc, page=1)
            await i.response.send_message(embed=embed, ephemeral=True)
        await self._run(i, go)

    @discord.ui.button(emoji=E.SHUFFLE, style=discord.ButtonStyle.secondary,
                       custom_id="mc_shuffle", row=2)
    async def btn_shuffle(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            if vc.queue.is_empty:
                return await i.response.send_message(
                    embed=Embed.error("Queue Empty"), ephemeral=True)
            q = list(vc.queue)
            random.shuffle(q)
            vc.queue.clear()
            for t in q:
                vc.queue.put(t)
            await i.response.send_message(
                embed=Embed.success("Shuffled", f"{E.SHUFFLE} **{len(q)}** tracks"),
                ephemeral=True)
        await self._run(i, go)

    @discord.ui.button(emoji=E.LOOP, style=discord.ButtonStyle.success,
                       custom_id="mc_loop", row=2)
    async def btn_loop(self, i: discord.Interaction, b: Button):
        async def go():
            vc = get_vc(i)
            vc.queue.mode = (wavelink.QueueMode.loop
                             if vc.queue.mode != wavelink.QueueMode.loop
                             else wavelink.QueueMode.normal)
            if vc.queue.mode == wavelink.QueueMode.loop:
                await i.response.send_message(
                    embed=Embed.success("Loop Enabled", f"{E.LOOP}"), ephemeral=True)
            else:
                await i.response.send_message(
                    embed=Embed.warning("Loop Disabled", f"{E.LOOP}"), ephemeral=True)
        await self._run(i, go)

    @discord.ui.button(emoji=E.FILTER, style=discord.ButtonStyle.success,
                       custom_id="mc_filter", row=2)
    async def btn_filter(self, i: discord.Interaction, b: Button):
        async def go():
            await i.response.send_message(
                embed=discord.Embed(
                    title=f"{E.FILTER}  Audio Filters",
                    description="Choose a filter:",
                    color=Colors.ACCENT),
                view=FilterSelectView(), ephemeral=True)
        await self._run(i, go)


# ═══════════════════════════════════════════════════════════
# SPOTIFY
# ═══════════════════════════════════════════════════════════

SPOTIFY_TRACK_REGEX = r"https?://open\.spotify\.com/track/([a-zA-Z0-9]+)"
SPOTIFY_PLAYLIST_REGEX = r"https?://open\.spotify\.com/playlist/([a-zA-Z0-9]+)"
SPOTIFY_ALBUM_REGEX = r"https?://open\.spotify\.com/album/([a-zA-Z0-9]+)"


class SpotifyAPI:
    BASE_URL = "https://api.spotify.com/v1"
    def __init__(self, cid, csec):
        self.cid, self.csec, self.token = cid, csec, None

    async def get_token(self):
        auth = base64.b64encode(f"{self.cid}:{self.csec}".encode()).decode()
        async with aiohttp.ClientSession() as s:
            async with s.post("https://accounts.spotify.com/api/token",
                              headers={"Authorization": f"Basic {auth}"},
                              data={"grant_type": "client_credentials"}) as r:
                if r.status != 200: raise Exception(f"Spotify token {r.status}")
                self.token = (await r.json()).get("access_token")

    async def get(self, endpoint):
        for attempt in range(2):
            if not self.token or attempt > 0: await self.get_token()
            async with aiohttp.ClientSession() as s:
                async with s.get(f"{self.BASE_URL}/{endpoint}",
                                 headers={"Authorization": f"Bearer {self.token}"}) as r:
                    if r.status == 401 and attempt == 0: continue
                    if r.status != 200: raise Exception(f"Spotify {r.status}")
                    return await r.json()
        raise Exception("Spotify retries")

    async def get_track(self, tid): return await self.get(f"tracks/{tid}")
    async def get_playlist(self, pid): return await self.get(f"playlists/{pid}")
    async def get_album(self, aid): return await self.get(f"albums/{aid}")


try:
    with open('bot_config.json') as f:
        cfg = json.load(f)
        sid = cfg.get('spotify_client_id') or os.environ.get("SPOTIFY_CLIENT_ID")
        ssec = cfg.get('spotify_client_secret') or os.environ.get("SPOTIFY_CLIENT_SECRET")
except FileNotFoundError:
    sid = os.environ.get("SPOTIFY_CLIENT_ID")
    ssec = os.environ.get("SPOTIFY_CLIENT_SECRET")

spotify_api = SpotifyAPI(sid, ssec) if sid and ssec else None
print("✅ Spotify initialized" if spotify_api else "⚠️ Spotify not configured")


# ═══════════════════════════════════════════════════════════
# GLOBAL STATE
# ═══════════════════════════════════════════════════════════

active_player_messages = {}
track_histories = {}
user_playlists = {}
blacklist_check = lambda: commands.check(lambda ctx: True)
ignore_check = lambda: commands.check(lambda ctx: True)


# ═══════════════════════════════════════════════════════════
# MUSIC COG
# ═══════════════════════════════════════════════════════════

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        await self.connect_nodes()

    async def connect_nodes(self):
        try:
            uri = pwd = None
            try:
                with open('bot_config.json') as f:
                    c = json.load(f)
                    uri = c.get('lavalink_uri') or os.environ.get("LAVALINK_URI")
                    pwd = c.get('lavalink_password') or os.environ.get("LAVALINK_PASSWORD")
            except FileNotFoundError:
                uri = os.environ.get("LAVALINK_URI")
                pwd = os.environ.get("LAVALINK_PASSWORD")

            if not uri or not pwd:
                uri = "https://lava-v4.ajieblogs.eu.org:443/"
                pwd = "https://dsc.gg/ajidevserver"
                print("⚠️ Using default Lavalink node")

            nodes = [wavelink.Node(uri=uri, password=pwd)]
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=None)
            print("🎵 Lavalink connected")
        except Exception as e:
            print(f"❌ Lavalink: {e}")

    async def auto_delete(self, msg, delay):
        await asyncio.sleep(delay)
        try: await msg.delete()
        except Exception: pass

    async def display_player(self, player, track, ctx):
        try:
            gid = ctx.guild.id
            old = active_player_messages.pop(gid, None)
            if old:
                try: await old.delete()
                except Exception: pass
            embed = Embed.now_playing(track, player, ctx.author)
            view = MusicControlView()
            msg = await ctx.send(embed=embed, view=view)
            active_player_messages[gid] = msg
        except Exception as e:
            print(f"display_player: {e}")

    async def _ensure_voice(self, ctx):
        if not ctx.author.voice:
            await ctx.send(embed=Embed.error("Voice Required", "Join a voice channel first."))
            return None
        vc = ctx.voice_client
        if vc and isinstance(vc, wavelink.Player):
            vc.ctx = ctx
            return vc
        if not wavelink.Pool.nodes:
            await ctx.send(embed=Embed.error("Music Server Offline", "Try again in a minute."))
            return None
        try:
            vc = await asyncio.wait_for(
                ctx.author.voice.channel.connect(cls=wavelink.Player, self_deaf=True, timeout=20.0),
                timeout=25.0)
            await vc.set_volume(100)
            vc.ctx = ctx
            return vc
        except asyncio.TimeoutError:
            try:
                if ctx.guild.voice_client:
                    await ctx.guild.voice_client.disconnect(force=True)
            except Exception: pass
            await ctx.send(embed=Embed.error("Voice Timeout", "Lavalink may be down."))
            return None
        except discord.Forbidden:
            await ctx.send(embed=Embed.error("No Permission",
                                              "I need **Connect** + **Speak** permissions."))
            return None
        except Exception as e:
            try:
                if ctx.guild.voice_client:
                    await ctx.guild.voice_client.disconnect(force=True)
            except Exception: pass
            await ctx.send(embed=Embed.error("Connection Failed",
                                              f"`{type(e).__name__}: {e}`"))
            return None

    async def play_source(self, ctx, query):
        vc = await self._ensure_voice(ctx)
        if not vc: return

        if vc.playing and vc.channel != ctx.author.voice.channel:
            return await ctx.send(embed=Embed.error(
                "Wrong Channel", f"Join {vc.channel.mention} to control music."))

        if spotify_api and re.match(SPOTIFY_TRACK_REGEX, query):
            return await self._spotify(ctx, vc, query, "track")
        if spotify_api and re.match(SPOTIFY_PLAYLIST_REGEX, query):
            return await self._spotify(ctx, vc, query, "playlist")
        if spotify_api and re.match(SPOTIFY_ALBUM_REGEX, query):
            return await self._spotify(ctx, vc, query, "album")

        search_msg = await ctx.send(embed=discord.Embed(
            title=f"{E.SEARCH}  Searching…", description=f"`{query}`", color=Colors.INFO))

        try:
            tracks = await wavelink.Playable.search(query)
        except Exception as e:
            return await search_msg.edit(embed=Embed.error("Search Error", str(e)))

        if not tracks:
            return await search_msg.edit(embed=Embed.error(
                "No Results", f"Nothing found for `{query}`."))

        if isinstance(tracks, wavelink.Playlist):
            await vc.queue.put_wait(tracks.tracks)
            total_ms = sum(t.length for t in tracks.tracks)
            await search_msg.edit(embed=Embed.playlist_added(
                tracks.name, len(tracks.tracks), total_ms, ctx.author))
            asyncio.create_task(self.auto_delete(search_msg, 8))
        else:
            track = tracks[0]
            pos = len(vc.queue) + (1 if vc.playing else 0)
            await vc.queue.put_wait(track)
            if pos > 0:
                await search_msg.edit(embed=Embed.added(track, pos, ctx.author))
                asyncio.create_task(self.auto_delete(search_msg, 8))
            else:
                asyncio.create_task(self.auto_delete(search_msg, 3))

        if not vc.playing and not vc.queue.is_empty:
            nt = await vc.queue.get_wait()
            await vc.play(nt)
            await self.display_player(vc, nt, ctx)

    async def _spotify(self, ctx, vc, link, kind):
        try:
            if kind == "track":
                tid = re.search(SPOTIFY_TRACK_REGEX, link).group(1)
                info = await spotify_api.get_track(tid)
                title = info['name']
                author = ', '.join(a['name'] for a in info['artists'])
                results = await wavelink.Playable.search(f"{title} by {author}")
                if not results:
                    return await ctx.send(embed=Embed.error("Unavailable"))
                track = results[0] if not isinstance(results, wavelink.Playlist) else results.tracks[0]
                await vc.queue.put_wait(track)
                if not vc.playing:
                    nt = await vc.queue.get_wait()
                    await vc.play(nt)
                    await self.display_player(vc, nt, ctx)
                else:
                    await ctx.send(embed=Embed.added(track, len(vc.queue), ctx.author))

            elif kind in ("playlist", "album"):
                msg = await ctx.send(embed=discord.Embed(
                    title=f"{E.LOAD}  Loading Spotify…", color=Colors.INFO))
                if kind == "playlist":
                    pid = re.search(SPOTIFY_PLAYLIST_REGEX, link).group(1)
                    data = await spotify_api.get_playlist(pid)
                    items = data.get("tracks", {}).get("items", [])
                    name = data.get("name", "Playlist")
                else:
                    aid = re.search(SPOTIFY_ALBUM_REGEX, link).group(1)
                    data = await spotify_api.get_album(aid)
                    items = data.get("tracks", {}).get("items", [])
                    name = data.get("name", "Album")

                added = 0; total_ms = 0
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
                            added += 1; total_ms += tr.length
                    except Exception: continue

                await msg.edit(embed=Embed.playlist_added(name, added, total_ms, ctx.author))
                asyncio.create_task(self.auto_delete(msg, 8))

                if not vc.playing and not vc.queue.is_empty:
                    nt = await vc.queue.get_wait()
                    await vc.play(nt)
                    await self.display_player(vc, nt, ctx)
        except Exception as e:
            await ctx.send(embed=Embed.error("Spotify Error", str(e)))

    # ═══════════════════════════════════════════════════════
    # HYBRID COMMANDS (work as both prefix x! and slash /)
    # ═══════════════════════════════════════════════════════

    @commands.hybrid_command(name="play", aliases=["p"],
                              description="Play a song from YouTube/Spotify/SoundCloud")
    @app_commands.describe(query="Song name or URL")
    async def play(self, ctx, *, query: str):
        await self.play_source(ctx, query)

    @commands.hybrid_command(name="join", description="Join your voice channel")
    async def join(self, ctx):
        vc = await self._ensure_voice(ctx)
        if vc:
            await ctx.send(embed=Embed.success("Connected", f"Joined {vc.channel.mention}"))

    @commands.hybrid_command(name="disconnect", aliases=["dc", "leave"],
                              description="Disconnect from voice")
    async def disconnect(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send(embed=Embed.error("Not Connected"))
        if ctx.author.voice and ctx.author.voice.channel != vc.channel:
            return await ctx.send(embed=Embed.error("Wrong Channel"))
        await vc.disconnect()
        await ctx.send(embed=Embed.success("Disconnected", f"{E.HEADPHONES} Left voice"))

    @commands.hybrid_command(name="pause", description="Pause playback")
    async def pause(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send(embed=Embed.error("Nothing Playing"))
        await vc.pause(True)
        await ctx.send(embed=Embed.warning("Paused", f"{E.PAUSE} Playback paused"))

    @commands.hybrid_command(name="resume", description="Resume playback")
    async def resume(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.paused:
            return await ctx.send(embed=Embed.error("Nothing Paused"))
        await vc.pause(False)
        await ctx.send(embed=Embed.success("Resumed", f"{E.PLAY} Playback resumed"))

    @commands.hybrid_command(name="skip", description="Skip current track")
    async def skip(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send(embed=Embed.error("Nothing Playing"))
        cur = vc.current.title[:50] if vc.current else "unknown"
        await vc.stop()
        await ctx.send(embed=Embed.success("Skipped", f"{E.SKIP} Skipped **{cur}**"))

    @commands.hybrid_command(name="stop", description="Stop and disconnect")
    async def stop(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send(embed=Embed.error("Not Connected"))
        gid = ctx.guild.id
        msg = active_player_messages.pop(gid, None)
        if msg:
            try: await msg.delete()
            except Exception: pass
        vc.queue.clear()
        await vc.disconnect()
        await ctx.send(embed=Embed.success("Stopped", f"{E.STOP} Playback stopped"))

    @commands.hybrid_command(name="volume", aliases=["vol"], description="Set volume 1-200")
    @app_commands.describe(level="Volume level 1-200")
    async def volume(self, ctx, level: int):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send(embed=Embed.error("Not Connected"))
        if not 1 <= level <= 200:
            return await ctx.send(embed=Embed.error("Invalid Range", "Volume must be 1-200."))
        await vc.set_volume(level)
        icon = E.VOL_MUTE if level == 0 else (E.VOL_LOW if level < 50 else E.VOL_HIGH)
        await ctx.send(embed=Embed.success("Volume Set", f"{icon} `{level}%`"))

    @commands.hybrid_command(name="queue", aliases=["q"], description="Show the queue")
    @app_commands.describe(page="Page number")
    async def queue(self, ctx, page: int = 1):
        vc = ctx.voice_client
        if not vc or vc.queue.is_empty:
            return await ctx.send(embed=Embed.info("Queue", "The queue is empty."))
        await ctx.send(embed=Embed.queue_list(vc, page))

    @commands.hybrid_command(name="clearqueue", aliases=["cq"], description="Clear the queue")
    async def clearqueue(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send(embed=Embed.error("Not Connected"))
        n = len(vc.queue)
        vc.queue.clear()
        await ctx.send(embed=Embed.success("Queue Cleared", f"{E.CLEAR} Removed **{n}** tracks"))

    @commands.hybrid_command(name="shuffle", description="Shuffle the queue")
    async def shuffle(self, ctx):
        vc = ctx.voice_client
        if not vc or vc.queue.is_empty:
            return await ctx.send(embed=Embed.error("Queue Empty"))
        q = list(vc.queue)
        random.shuffle(q)
        vc.queue.clear()
        for t in q:
            vc.queue.put(t)
        await ctx.send(embed=Embed.success("Shuffled", f"{E.SHUFFLE} Randomised **{len(q)}** tracks"))

    @commands.hybrid_command(name="loop", description="Toggle loop mode")
    async def loop(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send(embed=Embed.error("Nothing Playing"))
        vc.queue.mode = (wavelink.QueueMode.loop
                         if vc.queue.mode != wavelink.QueueMode.loop
                         else wavelink.QueueMode.normal)
        if vc.queue.mode == wavelink.QueueMode.loop:
            await ctx.send(embed=Embed.success("Loop Enabled", f"{E.LOOP} Queue will repeat"))
        else:
            await ctx.send(embed=Embed.warning("Loop Disabled", f"{E.LOOP} Loop mode off"))

    @commands.hybrid_command(name="nowplaying", aliases=["np"],
                              description="Show current track")
    async def nowplaying(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send(embed=Embed.error("Nothing Playing"))
        await ctx.send(embed=Embed.now_playing(vc.current, vc, ctx.author))

    @commands.hybrid_command(name="seek", description="Seek to a position")
    @app_commands.describe(seconds="Position in seconds")
    async def seek(self, ctx, seconds: int):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send(embed=Embed.error("Nothing Playing"))
        if seconds < 0 or seconds * 1000 > vc.current.length:
            return await ctx.send(embed=Embed.error("Invalid", f"0-{vc.current.length // 1000}s."))
        await vc.seek(seconds * 1000)
        await ctx.send(embed=Embed.success("Seeked", f"{E.TIMER} `{Embed._fmt_ms(seconds * 1000)}`"))

    @commands.hybrid_command(name="replay", description="Restart current track")
    async def replay(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send(embed=Embed.error("Nothing Playing"))
        await vc.seek(0)
        await ctx.send(embed=Embed.success("Replaying", f"{E.REPLAY} Restarted"))

    @commands.hybrid_command(name="previous", aliases=["prev"],
                              description="Play previous track")
    async def previous(self, ctx):
        vc = ctx.voice_client
        if not vc:
            return await ctx.send(embed=Embed.error("Not Connected"))
        hist = track_histories.get(ctx.guild.id, [])
        if len(hist) < 2:
            return await ctx.send(embed=Embed.error("No History"))
        hist.pop()
        prev = hist[-1]
        await vc.play(prev)
        await ctx.send(embed=Embed.success("Previous", f"**{prev.title[:60]}**"))

    @commands.hybrid_command(name="autoplay", description="Toggle 24/7 autoplay")
    async def autoplay(self, ctx):
        vc = await self._ensure_voice(ctx)
        if not vc: return
        vc._autoplay_only = True
        queries = ["lofi hip hop radio", "lofi study music", "chill lofi beats",
                   "latest hindi songs", "arijit singh songs", "sad songs english",
                   "top english songs", "arabic songs"]
        msg = await ctx.send(embed=discord.Embed(
            title=f"{E.LOAD}  Starting Autoplay…", color=Colors.INFO))
        added = 0
        for _ in range(20):
            try:
                r = await wavelink.Playable.search(random.choice(queries))
                if r:
                    tr = r[0] if not isinstance(r, wavelink.Playlist) else r.tracks[0]
                    await vc.queue.put_wait(tr)
                    added += 1
            except Exception: continue
        await msg.edit(embed=Embed.success(
            "Autoplay Started",
            f"{E.NOTES} Loaded **{added}** tracks\nStop with `x!stop` or `/stop`"))
        if not vc.playing and not vc.queue.is_empty:
            nt = await vc.queue.get_wait()
            await vc.play(nt)

    @commands.hybrid_command(name="filter", description="Open audio filter menu")
    async def filter_cmd(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.playing:
            return await ctx.send(embed=Embed.error("Nothing Playing"))
        await ctx.send(
            embed=discord.Embed(title=f"{E.FILTER}  Audio Filters",
                                description="Choose a filter below.",
                                color=Colors.ACCENT),
            view=FilterSelectView())

    @commands.hybrid_command(name="search", description="Search YouTube")
    @app_commands.describe(query="Search terms")
    async def search_cmd(self, ctx, *, query: str):
        if not ctx.author.voice:
            return await ctx.send(embed=Embed.error("Voice Required"))
        results = await wavelink.Playable.search(query, source="ytsearch")
        if not results:
            return await ctx.send(embed=Embed.error("No Results"))
        top = results[:5] if not isinstance(results, wavelink.Playlist) else results.tracks[:5]
        embed = discord.Embed(title=f"{E.SEARCH}  Search Results",
                              description=f"Top 5 for `{query}`",
                              color=Colors.INFO)
        for i, t in enumerate(top, 1):
            d = Embed._fmt_ms(t.length)
            embed.add_field(name=f"`{i}.` {t.title[:55]}",
                            value=f"{E.MIC} {t.author[:40]}  •  `{d}`",
                            inline=False)
        embed.set_footer(text="Use /play or x!play <song> to play")
        await ctx.send(embed=embed)

    # ── Playlists ──
    @commands.hybrid_command(name="createplaylist", description="Create a new playlist")
    @app_commands.describe(name="Playlist name")
    async def createplaylist(self, ctx, *, name: str):
        uid = ctx.author.id
        user_playlists.setdefault(uid, {})
        if name in user_playlists[uid]:
            return await ctx.send(embed=Embed.error("Exists", f"**{name}** already exists."))
        user_playlists[uid][name] = []
        await ctx.send(embed=Embed.success("Playlist Created", f"{E.LIST} **{name}**"))

    @commands.hybrid_command(name="playlists", description="View your playlists")
    async def playlists(self, ctx):
        pls = user_playlists.get(ctx.author.id, {})
        if not pls:
            return await ctx.send(embed=Embed.info("No Playlists",
                                                    "Create one with `/createplaylist`."))
        embed = discord.Embed(title=f"{E.LIST}  Your Playlists", color=Colors.PRIMARY)
        for n, t in list(pls.items())[:15]:
            embed.add_field(name=f"{E.NOTE} {n}", value=f"`{len(t)}` tracks", inline=True)
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="viewplaylist", description="View a playlist")
    @app_commands.describe(name="Playlist name")
    async def viewplaylist(self, ctx, *, name: str):
        pls = user_playlists.get(ctx.author.id, {})
        if name not in pls:
            return await ctx.send(embed=Embed.error("Not Found"))
        tracks = pls[name]
        embed = discord.Embed(title=f"{E.LIST}  {name}", color=Colors.PRIMARY)
        if not tracks:
            embed.description = "Empty playlist."
        else:
            for i, t in enumerate(tracks[:10], 1):
                embed.add_field(name=f"`{i:>2}.` {t['title'][:45]}",
                                value=f"{E.MIC} {t['author'][:35]}", inline=False)
        embed.set_footer(text=f"Total {len(tracks)} tracks")
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="deleteplaylist", description="Delete a playlist")
    @app_commands.describe(name="Playlist name")
    async def deleteplaylist(self, ctx, *, name: str):
        pls = user_playlists.get(ctx.author.id, {})
        if name not in pls:
            return await ctx.send(embed=Embed.error("Not Found"))
        del pls[name]
        await ctx.send(embed=Embed.success("Deleted", f"**{name}** removed"))

    @commands.hybrid_command(name="savequeue", description="Save queue as playlist")
    @app_commands.describe(name="Playlist name")
    async def savequeue(self, ctx, *, name: str):
        vc = ctx.voice_client
        if not vc or vc.queue.is_empty:
            return await ctx.send(embed=Embed.error("Queue Empty"))
        uid = ctx.author.id
        user_playlists.setdefault(uid, {})
        user_playlists[uid][name] = [
            {"title": t.title, "uri": t.uri, "author": t.author} for t in vc.queue]
        await ctx.send(embed=Embed.success(
            "Queue Saved", f"{E.LIST} **{len(vc.queue)}** tracks → **{name}**"))

    @commands.hybrid_command(name="playplaylist", description="Play a saved playlist")
    @app_commands.describe(name="Playlist name")
    async def playplaylist(self, ctx, *, name: str):
        pls = user_playlists.get(ctx.author.id, {})
        if name not in pls:
            return await ctx.send(embed=Embed.error("Not Found"))
        vc = await self._ensure_voice(ctx)
        if not vc: return

        msg = await ctx.send(embed=discord.Embed(
            title=f"{E.LOAD}  Loading Playlist…",
            description=f"**{name}**", color=Colors.INFO))
        loaded = 0; total_ms = 0
        for e in pls[name]:
            try:
                r = await wavelink.Playable.search(e["uri"])
                if r:
                    tr = r[0] if not isinstance(r, wavelink.Playlist) else r.tracks[0]
                    await vc.queue.put_wait(tr)
                    loaded += 1; total_ms += tr.length
            except Exception: continue
        await msg.edit(embed=Embed.playlist_added(name, loaded, total_ms, ctx.author))
        asyncio.create_task(self.auto_delete(msg, 8))
        if not vc.playing and not vc.queue.is_empty:
            nt = await vc.queue.get_wait()
            await vc.play(nt)
            await self.display_player(vc, nt, ctx)

    @commands.hybrid_command(name="diagnose", aliases=["diag"],
                              description="Diagnose voice connection issues")
    async def diagnose(self, ctx):
        lines = []
        try:
            import nacl
            lines.append(f"{E.OK} **PyNaCl**: `{nacl.__version__}`")
        except ImportError:
            lines.append(f"{E.NO} **PyNaCl**: NOT INSTALLED → `pip install PyNaCl`")

        nodes = wavelink.Pool.nodes
        if nodes:
            for nid, node in nodes.items():
                try: status = node.status.name if hasattr(node, "status") else "?"
                except Exception: status = "?"
                lines.append(f"{E.OK} **Lavalink** `{node.uri}` → `{status}`")
        else:
            lines.append(f"{E.NO} **Lavalink**: No nodes")

        vc = ctx.voice_client
        if vc:
            lines.append(f"{E.OK} **Voice**: `{vc.channel.name}`")
        else:
            lines.append(f"{E.INFO} **Voice**: Not connected")

        if ctx.author.voice:
            lines.append(f"{E.OK} **You**: `{ctx.author.voice.channel.name}`")
            perms = ctx.author.voice.channel.permissions_for(ctx.guild.me)
            lines.append(f"{'✅' if perms.connect else '❌'} Connect perm")
            lines.append(f"{'✅' if perms.speak else '❌'} Speak perm")
        else:
            lines.append(f"{E.NO} **You**: Not in voice")

        await ctx.send(embed=discord.Embed(title="🔍  Diagnostics",
                                            description="\n".join(lines),
                                            color=Colors.INFO))

    # ═══════════════════════════════════════════════════════
    # LISTENERS
    # ═══════════════════════════════════════════════════════

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload):
        p, t = payload.player, payload.track
        if not p or not t: return
        track_histories.setdefault(p.guild.id, []).append(t)
        if len(track_histories[p.guild.id]) > 25:
            track_histories[p.guild.id].pop(0)

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload):
        player = payload.player
        if not player: return

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
                except Exception: continue

        # remove old now-playing message
        if hasattr(player, "ctx") and player.ctx:
            gid = player.ctx.guild.id
            if not getattr(player, "_autoplay_only", False):
                old = active_player_messages.pop(gid, None)
                if old:
                    try: await old.delete()
                    except Exception: pass

        # play next
        if not player.queue.is_empty:
            nxt = await player.queue.get_wait()
            await player.play(nxt)
            if hasattr(player, "ctx") and player.ctx:
                cog = player.client.get_cog("Music")
                if cog and not getattr(player, "_autoplay_only", False):
                    await cog.display_player(player, nxt, player.ctx)
        else:
            ctx = getattr(player, "ctx", None)
            try: await player.disconnect()
            except Exception: pass
            if ctx:
                try:
                    await ctx.channel.send(embed=Embed.info(
                        "Queue Ended", f"{E.STOP} All tracks finished. Left the channel."))
                except Exception: pass


# ═══════════════════════════════════════════════════════════
# HELP COG
# ═══════════════════════════════════════════════════════════

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="help", aliases=["h"],
                              description="Show all commands")
    async def help_cmd(self, ctx):
        await ctx.send(embed=Embed.help_main(ctx.prefix or "x!"))


# ═══════════════════════════════════════════════════════════
# BOT
# ═══════════════════════════════════════════════════════════

intents = discord.Intents.all()


def load_token():
    try:
        with open('bot_config.json') as f:
            c = json.load(f)
            t = c.get('discord_token') or os.environ.get('DISCORD_TOKEN')
            if t and t.strip():
                return t
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
            print(f"DB: {e}")

        # Register persistent view so buttons work after restart
        self.add_view(MusicControlView())

        await self.add_cog(Music(self))
        await self.add_cog(HelpCog(self))
        print("✅ Cogs loaded  •  persistent view registered")

        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} slash command(s)")
        except Exception as e:
            print(f"❌ Slash sync failed: {e}")

    async def close(self):
        if self.session:
            await self.session.close()
        try: await self.music_db.close()
        except Exception: pass
        await super().close()

    async def on_ready(self):
        print(f"✅ Logged in as {self.user}  •  {len(self.guilds)} guilds")
        await self.change_presence(
            activity=discord.Activity(type=discord.ActivityType.listening,
                                       name="x!help  •  /help  •  🎵"),
            status=discord.Status.online)


bot = MusicBot()


def main():
    token = load_token()
    if not token:
        print("❌ DISCORD_TOKEN missing (env or bot_config.json)")
        return
    try:
        bot.run(token)
    except discord.LoginFailure:
        print("❌ Invalid token")
    except Exception as e:
        print(f"❌ {e}")


if __name__ == "__main__":
    main()
