import aiosqlite
import datetime
import json
from typing import Optional, List, Dict, Any


class MusicDatabase:
    def __init__(self, db_path: str = "music_data.db"):
        self.db_path = db_path
        self.db: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Connect to database and create tables"""
        self.db = await aiosqlite.connect(self.db_path)
        await self.create_tables()
        print("✅ Database connected successfully")

    async def close(self):
        """Close database connection"""
        if self.db:
            await self.db.close()
            print("✅ Database closed")

    async def create_tables(self):
        """Create all required tables"""
        # Servers table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS servers (
                id INTEGER PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Voice channels table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS voice_channels (
                id INTEGER PRIMARY KEY,
                server_id INTEGER,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(id)
            )
        """)

        # Music plays table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS music_plays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                channel_id INTEGER,
                user_id INTEGER,
                user_name TEXT,
                track_title TEXT,
                track_author TEXT,
                track_uri TEXT,
                track_duration INTEGER,
                track_source TEXT,
                played_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(id)
            )
        """)

        # Searches table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS searches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                user_id INTEGER,
                user_name TEXT,
                search_query TEXT,
                results_count INTEGER,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(id)
            )
        """)

        # Playback sessions table
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS playback_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                server_id INTEGER,
                channel_id INTEGER,
                current_track TEXT,
                queue_data TEXT,
                position INTEGER,
                volume INTEGER,
                is_paused BOOLEAN,
                loop_mode TEXT,
                auto_resume BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (server_id) REFERENCES servers(id)
            )
        """)

        await self.db.commit()

    async def register_server(self, server_id: int, server_name: str):
        """Register or update a server"""
        await self.db.execute("""
            INSERT OR REPLACE INTO servers (id, name) VALUES (?, ?)
        """, (server_id, server_name))
        await self.db.commit()

    async def register_voice_channel(self, channel_id: int, server_id: int, channel_name: str):
        """Register or update a voice channel"""
        await self.db.execute("""
            INSERT OR REPLACE INTO voice_channels (id, server_id, name) VALUES (?, ?, ?)
        """, (channel_id, server_id, channel_name))
        await self.db.commit()

    async def log_music_play(
        self,
        server_id: int,
        channel_id: int,
        user_id: int,
        user_name: str,
        track_title: str,
        track_author: str,
        track_uri: str,
        track_duration: int,
        track_source: str = "youtube"
    ):
        """Log a music play event"""
        await self.db.execute("""
            INSERT INTO music_plays 
            (server_id, channel_id, user_id, user_name, track_title, track_author, 
             track_uri, track_duration, track_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (server_id, channel_id, user_id, user_name, track_title, track_author,
              track_uri, track_duration, track_source))
        await self.db.commit()

    async def log_search(
        self,
        server_id: int,
        user_id: int,
        user_name: str,
        search_query: str,
        results_count: int
    ):
        """Log a search event"""
        await self.db.execute("""
            INSERT INTO searches 
            (server_id, user_id, user_name, search_query, results_count)
            VALUES (?, ?, ?, ?, ?)
        """, (server_id, user_id, user_name, search_query, results_count))
        await self.db.commit()

    async def save_playback_session(
        self,
        server_id: int,
        channel_id: int,
        current_track: Optional[Dict],
        queue_data: List[Dict],
        position: int,
        volume: int,
        is_paused: bool,
        loop_mode: str,
        auto_resume: bool = True
    ):
        """Save current playback session"""
        # Delete old session for this server
        await self.db.execute("""
            DELETE FROM playback_sessions WHERE server_id = ?
        """, (server_id,))

        await self.db.execute("""
            INSERT INTO playback_sessions
            (server_id, channel_id, current_track, queue_data, position, volume,
             is_paused, loop_mode, auto_resume)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            server_id,
            channel_id,
            json.dumps(current_track) if current_track else None,
            json.dumps(queue_data),
            position,
            volume,
            is_paused,
            loop_mode,
            auto_resume
        ))
        await self.db.commit()

    async def get_all_active_sessions(self) -> List[Dict[str, Any]]:
        """Get all active playback sessions"""
        cursor = await self.db.execute("""
            SELECT * FROM playback_sessions WHERE auto_resume = 1
        """)
        rows = await cursor.fetchall()

        sessions = []
        for row in rows:
            sessions.append({
                'id': row[0],
                'server_id': row[1],
                'channel_id': row[2],
                'current_track': json.loads(row[3]) if row[3] else None,
                'queue_data': json.loads(row[4]) if row[4] else [],
                'position': row[5],
                'volume': row[6],
                'is_paused': bool(row[7]),
                'loop_mode': row[8],
                'auto_resume': bool(row[9])
            })
        return sessions

    async def get_server_stats(self, server_id: int) -> Dict[str, Any]:
        """Get comprehensive server statistics"""
        # Total plays
        cursor = await self.db.execute("""
            SELECT COUNT(*) FROM music_plays WHERE server_id = ?
        """, (server_id,))
        total_plays = (await cursor.fetchone())[0]

        # Total searches
        cursor = await self.db.execute("""
            SELECT COUNT(*) FROM searches WHERE server_id = ?
        """, (server_id,))
        total_searches = (await cursor.fetchone())[0]

        # Plays this week
        week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
        cursor = await self.db.execute("""
            SELECT COUNT(*) FROM music_plays 
            WHERE server_id = ? AND played_at > ?
        """, (server_id, week_ago))
        plays_this_week = (await cursor.fetchone())[0]

        # Unique listeners
        cursor = await self.db.execute("""
            SELECT COUNT(DISTINCT user_id) FROM music_plays WHERE server_id = ?
        """, (server_id,))
        unique_listeners = (await cursor.fetchone())[0]

        return {
            'total_plays': total_plays,
            'total_searches': total_searches,
            'plays_this_week': plays_this_week,
            'unique_listeners': unique_listeners
        }

    async def get_top_tracks(self, server_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most played tracks for a server"""
        cursor = await self.db.execute("""
            SELECT track_title, track_author, COUNT(*) as play_count
            FROM music_plays
            WHERE server_id = ?
            GROUP BY track_title, track_author
            ORDER BY play_count DESC
            LIMIT ?
        """, (server_id, limit))
        rows = await cursor.fetchall()

        return [
            {
                'title': row[0],
                'author': row[1],
                'play_count': row[2]
            }
            for row in rows
        ]

    async def get_user_listening_history(
        self, server_id: int, user_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get user's listening history"""
        cursor = await self.db.execute("""
            SELECT track_title, track_author, track_duration, played_at
            FROM music_plays
            WHERE server_id = ? AND user_id = ?
            ORDER BY played_at DESC
            LIMIT ?
        """, (server_id, user_id, limit))
        rows = await cursor.fetchall()

        return [
            {
                'title': row[0],
                'author': row[1],
                'duration': row[2],
                'played_at': row[3]
            }
            for row in rows
        ]

    async def get_user_stats(self, server_id: int, user_id: int) -> Dict[str, Any]:
        """Get user's personal statistics"""
        cursor = await self.db.execute("""
            SELECT COUNT(*), COALESCE(SUM(track_duration), 0)
            FROM music_plays
            WHERE server_id = ? AND user_id = ?
        """, (server_id, user_id))
        row = await cursor.fetchone()

        if not row or row[0] == 0:
            return None

        return {
            'total_listens': row[0],
            'total_duration': row[1]
        }

    async def get_recent_searches(self, server_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent searches for a server"""
        cursor = await self.db.execute("""
            SELECT search_query, user_name, results_count, searched_at
            FROM searches
            WHERE server_id = ?
            ORDER BY searched_at DESC
            LIMIT ?
        """, (server_id, limit))
        rows = await cursor.fetchall()

        return [
            {
                'query': row[0],
                'user_name': row[1],
                'results': row[2],
                'searched_at': row[3]
            }
            for row in rows
        ]
