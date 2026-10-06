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
from discord.ui import Button, View, Select
import wavelink
import aiohttp
import asyncio
import base64
import re
import json
import random
import io

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
                f"` {Embed._fmt_ms(pos)} ` {E.PLAY} ` {dur} `"
            ),
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
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━"
            )
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
                f"**Prefix:** `{prefix}`  •  **Quality:** `384 kbps Ultra HD`\n"
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
                f"**{E.HEADPHONES}  Voice**  •  `{prefix}join`  •  `{prefix}disconnect`"
            ),
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
        if not vc:
            return await interaction.response.send_message(
                embed=Embed.error("Not Connected"), ephemeral=True)

        name = select.values[0]
        filters = wavelink.Filters()
        desc = ""

        if name == "nightcore":
            filters.timescale.set(pitch=1.2, speed=1.2, rate=1); desc = "🌙 Nightcore"
        elif name == "bassboost":
            filters.equalizer.set(bands=[{"band":i,"gain":g} for i,g in enumerate([0.9,0.7,0.5,0.3,0.1,0.0])])
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
# MUSIC CONTROL VIEW — 100% WORKING BUTTONS
# ═══════════════════════════════════════════════════════════

def get_vc(interaction: discord.Interaction):
    """Helper: safely fetch the guild's voice client as a wavelink Player."""
    vc = interaction.guild.voice_client
    if vc and isinstance(vc, wavelink.Player):
        return vc
    return None


class MusicControlView(View):
    """
    Persistent control view. Every button re-fetches the live player
    from the guild so nothing ever goes stale.
    """

    def __init__(self):
        super().__init__(timeout=None)

    # ─── interaction guard ───
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        vc = get_vc(interaction)
        if not vc or not vc.connected:
            try:
                await interaction.response.send_message(
                    embed=Embed.error("Not Connected",
                                      "I'm not currently in a voice channel."),
                    ephemeral=True)
            except Exception:
                pass
            return False

        member_vc = getattr(interaction.user.voice, "channel", None)
        if member_vc is None or member_vc.id != vc.channel.id:
            try:
                await interaction.response.send_message(
                    embed=Embed.error("Wrong Channel",
                                      "You need to be in my voice channel to use these buttons."),
                    ephemeral=True)
            except Exception:
                pass
            return False
        return True

    async def _run(self, interaction: discord.Interaction, fn):
        """Always respond, always log."""
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
                        embed=Embed.error("Button Error", f"`{type(e).__name__}: {e}`"),
                        ephemeral=True)
                else:
                    await interaction.followup.send(
                        embed=Embed.error("Button Error", f"`{type(e).__name__}: {e}`"),
                        ephemeral=True)
            except Exception:
                pass

    # ═══════════ ROW 0 ═══════════
    @discord.ui.button(emoji=E.PREV, style=discord.ButtonStyle.secondary,
                       custom_id="mc_prev", row=0)
    async def btn_prev(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            hist = track_histories.get(interaction.guild.id, [])
            if len(hist) < 2:
                return await interaction.response.send_message(
                    embed=Embed.error("No History", "Nothing before this track."),
                    ephemeral=True)
            # hist[-1] = current, pop it; hist[-1] now = previous
            hist.pop()
            prev = hist[-1]
            await vc.play(prev)
            await interaction.response.send_message(
                embed=Embed.success("Previous", f"**{prev.title[:60]}**"),
                ephemeral=True)
        await self._run(interaction, go)

    @discord.ui.button(emoji=E.PAUSE, style=discord.ButtonStyle.primary,
                       custom_id="mc_pr", row=0)
    async def btn_pr(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            if vc.paused:
                await vc.pause(False)
                await interaction.response.send_message(
                    embed=Embed.success("Resumed", f"{E.PLAY} Playback resumed"),
                    ephemeral=True)
            else:
                await vc.pause(True)
                await interaction.response.send_message(
                    embed=Embed.warning("Paused", f"{E.PAUSE} Playback paused"),
                    ephemeral=True)
        await self._run(interaction, go)

    @discord.ui.button(emoji=E.STOP, style=discord.ButtonStyle.danger,
                       custom_id="mc_stop", row=0)
    async def btn_stop(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            gid = interaction.guild.id
            old = active_player_messages.pop(gid, None)
            if old:
                try: await old.delete()
                except Exception: pass
            if vc:
                vc.queue.clear()
                try: await vc.disconnect()
                except Exception: pass
            await interaction.response.send_message(
                embed=Embed.success("Stopped", "Playback stopped."),
                ephemeral=True)
        await self._run(interaction, go)

    @discord.ui.button(emoji=E.SKIP, style=discord.ButtonStyle.secondary,
                       custom_id="mc_skip", row=0)
    async def btn_skip(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            if not vc.playing and not vc.paused:
                return await interaction.response.send_message(
                    embed=Embed.error("Nothing Playing"), ephemeral=True)

            cur_title = vc.current.title[:50] if vc.current else "Unknown"
            has_next = not vc.queue.is_empty

            # ── RESPOND FIRST so Discord is happy ──
            await interaction.response.send_message(
                embed=Embed.success(
                    "Skipped",
                    f"{E.SKIP} Skipped **{cur_title}**"
                    + ("" if has_next else "\n*Queue is empty — stopping.*")),
                ephemeral=True)

            # ── THEN stop (fires on_wavelink_track_end which plays next) ──
            try:
                await vc.stop()
            except Exception as e:
                print(f"[SKIP] stop error: {e}")
                # Fallback: manually play next
                if has_next:
                    try:
                        nxt = await vc.queue.get_wait()
                        await vc.play(nxt)
                    except Exception as e2:
                        print(f"[SKIP] manual next error: {e2}")
        await self._run(interaction, go)

    @discord.ui.button(emoji=E.REPLAY, style=discord.ButtonStyle.secondary,
                       custom_id="mc_replay", row=0)
    async def btn_replay(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            if not vc.playing:
                return await interaction.response.send_message(
                    embed=Embed.error("Nothing Playing"), ephemeral=True)
            await vc.seek(0)
            await interaction.response.send_message(
                embed=Embed.success("Replaying", f"{E.REPLAY} Restarted"),
                ephemeral=True)
        await self._run(interaction, go)

    # ═══════════ ROW 1 ═══════════
    @discord.ui.button(emoji=E.VOL_MUTE, style=discord.ButtonStyle.secondary,
                       custom_id="mc_mute", row=1)
    async def btn_mute(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            if not hasattr(vc, "_pmv"):
                vc._pmv = vc.volume
                await vc.set_volume(0)
                await interaction.response.send_message(
                    embed=Embed.success("Muted", f"{E.VOL_MUTE}"),
                    ephemeral=True)
            else:
                await vc.set_volume(vc._pmv)
                delattr(vc, "_pmv")
                await interaction.response.send_message(
                    embed=Embed.success("Unmuted", f"{E.VOL_HIGH}"),
                    ephemeral=True)
        await self._run(interaction, go)

    @discord.ui.button(emoji=E.VOL_LOW, style=discord.ButtonStyle.primary,
                       custom_id="mc_vd", row=1)
    async def btn_vd(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            new = max(0, vc.volume - 20)
            await vc.set_volume(new)
            await interaction.response.send_message(
                embed=Embed.success("Volume", f"{E.VOL_LOW} `{vc.volume}%`"),
                ephemeral=True)
        await self._run(interaction, go)

    @discord.ui.button(emoji=E.VOL_HIGH, style=discord.ButtonStyle.primary,
                       custom_id="mc_vu", row=1)
    async def btn_vu(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            new = min(200, vc.volume + 20)
            await vc.set_volume(new)
            await interaction.response.send_message(
                embed=Embed.success("Volume", f"{E.VOL_HIGH} `{vc.volume}%`"),
                ephemeral=True)
        await self._run(interaction, go)

    # ═══════════ ROW 2 ═══════════
    @discord.ui.button(emoji=E.QUEUE, style=discord.ButtonStyle.secondary,
                       custom_id="mc_q", row=2)
    async def btn_q(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            # Debug: print actual queue size
            qsize = len(vc.queue)
            print(f"[QUEUE BTN] gid={interaction.guild.id} qsize={qsize} "
                  f"current={vc.current.title if vc.current else None}")

            # Always respond — even if empty, show the now-playing info
            embed = Embed.queue_list(vc, page=1)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        await self._run(interaction, go)

    @discord.ui.button(emoji=E.SHUFFLE, style=discord.ButtonStyle.secondary,
                       custom_id="mc_shuffle", row=2)
    async def btn_shuffle(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            if vc.queue.is_empty:
                return await interaction.response.send_message(
                    embed=Embed.error("Queue Empty"), ephemeral=True)
            q = list(vc.queue)
            random.shuffle(q)
            vc.queue.clear()
            for t in q:
                vc.queue.put(t)
            await interaction.response.send_message(
                embed=Embed.success("Shuffled", f"{E.SHUFFLE} **{len(q)}** tracks"),
                ephemeral=True)
        await self._run(interaction, go)

    @discord.ui.button(emoji=E.LOOP, style=discord.ButtonStyle.success,
                       custom_id="mc_loop", row=2)
    async def btn_loop(self, interaction: discord.Interaction, button: Button):
        async def go():
            vc = get_vc(interaction)
            vc.queue.mode = (wavelink.QueueMode.loop
                             if vc.queue.mode != wavelink.QueueMode.loop
                             else wavelink.QueueMode.normal)
            if vc.queue.mode == wavelink.QueueMode.loop:
                await interaction.response.send_message(
                    embed=Embed.success("Loop Enabled", f"{E.LOOP}"),
                    ephemeral=True)
            else:
                await interaction.response.send_message(
                    embed=Embed.warning("Loop Disabled", f"{E.LOOP}"),
                    ephemeral=True)
        await self._run(interaction, go)

    @discord.ui.button(emoji=E.FILTER, style=discord.ButtonStyle.success,
                       custom_id="mc_filter", row=2)
    async def btn_filter(self, interaction: discord.Interaction, button: Button):
        async def go():
            await interaction.response.send_message(
                embed=discord.Embed(
                    title=f"{E.FILTER}  Audio Filters",
                    description="Choose a filter:",
                    color=Colors.ACCENT),
                view=FilterSelectView(), ephemeral=True)
        await self._run(interaction, go)


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
        except as
