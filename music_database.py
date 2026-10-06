import aiosqlite
import json
import datetime
from typing import Optional, List, Dict, Any
import asyncio

class MusicDatabase:
    def __init__(self, db_path: str = "music_data.db"):
        self.db_path = db_path
        self.db = None
        
    async def connect(self):
        self.db = await aiosqlite.connect(self.db_path)
        await self.db.execute("PRAGMA foreign_keys = ON")
        await self.create_tables()
        print("✅ Music Database connected successfully")
        
    async def close(self):
        if self.db:
            await self.db.close()
            print("🔒 Music Database closed")
    
    async def create_tables(self):
        async with self.db.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                server_id INTEGER PRIMARY KEY,
                server_name TEXT NOT NULL,
                total_plays INTEGER DEFAULT 0,
                total_searches INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """):
            pass
            
        async with self.db.execute("""
            CREATE TABLE IF NOT EXISTS voice_channels (
                channel_id INTEGER PRIMARY KEY,
                server_id INTEGER NOT NULL,
                channel_name TEXT NOT NULL,
                total_plays INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers (server_id)
            )
        """):
            pass
            
        async with self.db.execute("""
            CREATE TABLE IF NOT EXISTS music_plays (
                play_id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                track_title TEXT NOT NULL,
                track_author TEXT,
                track_uri TEXT,
                track_duration INTEGER,
                track_source TEXT,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed BOOLEAN DEFAULT 0,
                FOREIGN KEY (server_id) REFERENCES servers (server_id),
                FOREIGN KEY (channel_id) REFERENCES voice_channels (channel_id)
            )
        """):
            pass
            
        async with self.db.execute("""
            CREATE TABLE IF NOT EXISTS music_searches (
                search_id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                search_query TEXT NOT NULL,
                results_count INTEGER DEFAULT 0,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers (server_id)
            )
        """):
            pass
            
        async with self.db.execute("""
            CREATE TABLE IF NOT EXISTS queue_history (
                queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                queue_data TEXT NOT NULL,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers (server_id),
                FOREIGN KEY (channel_id) REFERENCES voice_channels (channel_id)
            )
        """):
            pass
            
        async with self.db.execute("""
            CREATE TABLE IF NOT EXISTS playback_sessions (
                session_id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                current_track TEXT,
                queue_data TEXT,
                position INTEGER DEFAULT 0,
                volume INTEGER DEFAULT 100,
                is_paused BOOLEAN DEFAULT 0,
                loop_mode TEXT DEFAULT 'normal',
                filters_data TEXT,
                saved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                auto_resume BOOLEAN DEFAULT 1,
                FOREIGN KEY (server_id) REFERENCES servers (server_id),
                FOREIGN KEY (channel_id) REFERENCES voice_channels (channel_id)
            )
        """):
            pass
            
        async with self.db.execute("""
            CREATE TABLE IF NOT EXISTS listening_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                total_listens INTEGER DEFAULT 0,
                total_duration INTEGER DEFAULT 0,
                favorite_genre TEXT,
                last_listened TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers (server_id)
            )
        """):
            pass
            
        async with self.db.execute("""
            CREATE TABLE IF NOT EXISTS top_tracks (
                track_id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER NOT NULL,
                track_title TEXT NOT NULL,
                track_author TEXT,
                track_uri TEXT,
                play_count INTEGER DEFAULT 1,
                last_played TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers (server_id)
            )
        """):
            pass
            
        await self.db.commit()
    
    async def register_server(self, server_id: int, server_name: str):
        async with self.db.execute(
            """INSERT INTO servers (server_id, server_name, last_active) 
               VALUES (?, ?, ?)
               ON CONFLICT(server_id) DO UPDATE SET 
                   server_name = excluded.server_name,
                   last_active = excluded.last_active""",
            (server_id, server_name, datetime.datetime.now())
        ):
            pass
        await self.db.commit()
    
    async def register_voice_channel(self, channel_id: int, server_id: int, channel_name: str):
        async with self.db.execute(
            """INSERT INTO voice_channels (channel_id, server_id, channel_name, last_active) 
               VALUES (?, ?, ?, ?)
               ON CONFLICT(channel_id) DO UPDATE SET 
                   channel_name = excluded.channel_name,
                   last_active = excluded.last_active""",
            (channel_id, server_id, channel_name, datetime.datetime.now())
        ):
            pass
        await self.db.commit()
    
    async def log_music_play(
        self, 
        server_id: int, 
        channel_id: int, 
        user_id: int, 
        user_name: str,
        track_title: str,
        track_author: str = None,
        track_uri: str = None,
        track_duration: int = 0,
        track_source: str = "unknown"
    ):
        async with self.db.execute(
            """INSERT INTO music_plays 
               (server_id, channel_id, user_id, user_name, track_title, track_author, 
                track_uri, track_duration, track_source, played_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (server_id, channel_id, user_id, user_name, track_title, track_author, 
             track_uri, track_duration, track_source, datetime.datetime.now())
        ):
            pass
        
        await self.db.execute(
            "UPDATE servers SET total_plays = total_plays + 1, last_active = ? WHERE server_id = ?",
            (datetime.datetime.now(), server_id)
        )
        await self.db.execute(
            "UPDATE voice_channels SET total_plays = total_plays + 1, last_active = ? WHERE channel_id = ?",
            (datetime.datetime.now(), channel_id)
        )
        
        await self.update_top_tracks(server_id, track_title, track_author, track_uri)
        await self.update_user_stats(server_id, user_id, user_name, track_duration)
        
        await self.db.commit()
    
    async def log_search(
        self, 
        server_id: int, 
        user_id: int, 
        user_name: str,
        search_query: str,
        results_count: int = 0
    ):
        async with self.db.execute(
            """INSERT INTO music_searches 
               (server_id, user_id, user_name, search_query, results_count, searched_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (server_id, user_id, user_name, search_query, results_count, datetime.datetime.now())
        ):
            pass
        
        await self.db.execute(
            "UPDATE servers SET total_searches = total_searches + 1, last_active = ? WHERE server_id = ?",
            (datetime.datetime.now(), server_id)
        )
        
        await self.db.commit()
    
    async def save_playback_session(
        self,
        server_id: int,
        channel_id: int,
        current_track: Dict[str, Any] = None,
        queue_data: List[Dict[str, Any]] = None,
        position: int = 0,
        volume: int = 100,
        is_paused: bool = False,
        loop_mode: str = 'normal',
        filters_data: Dict[str, Any] = None,
        auto_resume: bool = True
    ):
        await self.db.execute(
            "DELETE FROM playback_sessions WHERE server_id = ? AND channel_id = ?",
            (server_id, channel_id)
        )
        
        async with self.db.execute(
            """INSERT INTO playback_sessions 
               (server_id, channel_id, current_track, queue_data, position, volume, 
                is_paused, loop_mode, filters_data, saved_at, auto_resume)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                server_id, channel_id, 
                json.dumps(current_track) if current_track else None,
                json.dumps(queue_data) if queue_data else None,
                position, volume, is_paused, loop_mode,
                json.dumps(filters_data) if filters_data else None,
                datetime.datetime.now(),
                auto_resume
            )
        ):
            pass
        
        await self.db.commit()
    
    async def get_playback_session(self, server_id: int, channel_id: int) -> Optional[Dict[str, Any]]:
        async with self.db.execute(
            """SELECT current_track, queue_data, position, volume, is_paused, 
                      loop_mode, filters_data, auto_resume
               FROM playback_sessions 
               WHERE server_id = ? AND channel_id = ?
               ORDER BY saved_at DESC LIMIT 1""",
            (server_id, channel_id)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'current_track': json.loads(row[0]) if row[0] else None,
                    'queue_data': json.loads(row[1]) if row[1] else None,
                    'position': row[2],
                    'volume': row[3],
                    'is_paused': bool(row[4]),
                    'loop_mode': row[5],
                    'filters_data': json.loads(row[6]) if row[6] else None,
                    'auto_resume': bool(row[7])
                }
        return None
    
    async def clear_playback_session(self, server_id: int, channel_id: int):
        await self.db.execute(
            "DELETE FROM playback_sessions WHERE server_id = ? AND channel_id = ?",
            (server_id, channel_id)
        )
        await self.db.commit()
    
    async def update_top_tracks(self, server_id: int, track_title: str, track_author: str = None, track_uri: str = None):
        async with self.db.execute(
            "SELECT track_id, play_count FROM top_tracks WHERE server_id = ? AND track_title = ?",
            (server_id, track_title)
        ) as cursor:
            row = await cursor.fetchone()
            
        if row:
            await self.db.execute(
                "UPDATE top_tracks SET play_count = play_count + 1, last_played = ? WHERE track_id = ?",
                (datetime.datetime.now(), row[0])
            )
        else:
            await self.db.execute(
                """INSERT INTO top_tracks (server_id, track_title, track_author, track_uri, play_count, last_played)
                   VALUES (?, ?, ?, ?, 1, ?)""",
                (server_id, track_title, track_author, track_uri, datetime.datetime.now())
            )
        await self.db.commit()
    
    async def update_user_stats(self, server_id: int, user_id: int, user_name: str, duration: int = 0):
        async with self.db.execute(
            "SELECT total_listens, total_duration FROM listening_stats WHERE server_id = ? AND user_id = ?",
            (server_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            
        if row:
            await self.db.execute(
                """UPDATE listening_stats 
                   SET total_listens = total_listens + 1, total_duration = total_duration + ?, 
                       user_name = ?, last_listened = ?
                   WHERE server_id = ? AND user_id = ?""",
                (duration, user_name, datetime.datetime.now(), server_id, user_id)
            )
        else:
            await self.db.execute(
                """INSERT INTO listening_stats 
                   (server_id, user_id, user_name, total_listens, total_duration, last_listened)
                   VALUES (?, ?, ?, 1, ?, ?)""",
                (server_id, user_id, user_name, duration, datetime.datetime.now())
            )
        await self.db.commit()
    
    async def get_server_stats(self, server_id: int) -> Dict[str, Any]]:
        async with self.db.execute(
            "SELECT total_plays, total_searches FROM servers WHERE server_id = ?",
            (server_id,)
        ) as cursor:
            row = await cursor.fetchone()
            total_plays = row[0] if row else 0
            total_searches = row[1] if row else 0
        
        async with self.db.execute(
            "SELECT COUNT(*) FROM music_plays WHERE server_id = ? AND played_at >= datetime('now', '-7 days')",
            (server_id,)
        ) as cursor:
            row = await cursor.fetchone()
            plays_this_week = row[0] if row else 0
        
        async with self.db.execute(
            "SELECT COUNT(DISTINCT user_id) FROM music_plays WHERE server_id = ?",
            (server_id,)
        ) as cursor:
            row = await cursor.fetchone()
            unique_listeners = row[0] if row else 0
        
        return {
            'total_plays': total_plays,
            'total_searches': total_searches,
            'plays_this_week': plays_this_week,
            'unique_listeners': unique_listeners
        }
    
    async def get_top_tracks(self, server_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        tracks = []
        async with self.db.execute(
            """SELECT track_title, track_author, play_count, last_played 
               FROM top_tracks 
               WHERE server_id = ? 
               ORDER BY play_count DESC 
               LIMIT ?""",
            (server_id, limit)
        ) as cursor:
            async for row in cursor:
                tracks.append({
                    'title': row[0],
                    'author': row[1],
                    'play_count': row[2],
                    'last_played': row[3]
                })
        return tracks
    
    async def get_user_listening_history(self, server_id: int, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        history = []
        async with self.db.execute(
            """SELECT track_title, track_author, track_duration, played_at 
               FROM music_plays 
               WHERE server_id = ? AND user_id = ? 
               ORDER BY played_at DESC 
               LIMIT ?""",
            (server_id, user_id, limit)
        ) as cursor:
            async for row in cursor:
                history.append({
                    'title': row[0],
                    'author': row[1],
                    'duration': row[2],
                    'played_at': row[3]
                })
        return history
    
    async def get_user_stats(self, server_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        async with self.db.execute(
            """SELECT user_name, total_listens, total_duration, last_listened 
               FROM listening_stats 
               WHERE server_id = ? AND user_id = ?""",
            (server_id, user_id)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    'user_name': row[0],
                    'total_listens': row[1],
                    'total_duration': row[2],
                    'last_listened': row[3]
                }
        return None
    
    async def get_recent_searches(self, server_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        searches = []
        async with self.db.execute(
            """SELECT user_name, search_query, results_count, searched_at 
               FROM music_searches 
               WHERE server_id = ? 
               ORDER BY searched_at DESC 
               LIMIT ?""",
            (server_id, limit)
        ) as cursor:
            async for row in cursor:
                searches.append({
                    'user_name': row[0],
                    'query': row[1],
                    'results': row[2],
                    'searched_at': row[3]
                })
        return searches
    
    async def save_queue_snapshot(self, server_id: int, channel_id: int, queue_data: List[Dict[str, Any]]):
        async with self.db.execute(
            """INSERT INTO queue_history (server_id, channel_id, queue_data, saved_at)
               VALUES (?, ?, ?, ?)""",
            (server_id, channel_id, json.dumps(queue_data), datetime.datetime.now())
        ):
            pass
        await self.db.commit()
    
    async def get_all_active_sessions(self) -> List[Dict[str, Any]]:
        sessions = []
        async with self.db.execute(
            """SELECT server_id, channel_id, current_track, queue_data, position, 
                      volume, is_paused, loop_mode, filters_data, auto_resume
               FROM playback_sessions 
               WHERE auto_resume = 1
               ORDER BY saved_at DESC"""
        ) as cursor:
            async for row in cursor:
                sessions.append({
                    'server_id': row[0],
                    'channel_id': row[1],
                    'current_track': json.loads(row[2]) if row[2] else None,
                    'queue_data': json.loads(row[3]) if row[3] else None,
                    'position': row[4],
                    'volume': row[5],
                    'is_paused': bool(row[6]),
                    'loop_mode': row[7],
                    'filters_data': json.loads(row[8]) if row[8] else None,
                    'auto_resume': bool(row[9])
                })
        return sessions