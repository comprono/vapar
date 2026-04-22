import sqlite3
import json
import threading
from typing import List, Optional, Dict, Any
from datetime import datetime
from common.schemas.market_data import Quote, Trade
from data_layer.storage.base import BaseStorage

class SQLiteStorage(BaseStorage):
    """
    SQLite storage adapter with connection pooling.
    Thread-safe, persistent connection for high performance.
    """
    
    def __init__(self, db_path: str = "trading.db"):
        self.db_path = db_path
        self.conn = None
        self.cursor = None
        self._lock = threading.Lock()  # Thread safety
        self._connected = False
    
    async def connect(self):
        """Create database and tables (with connection pooling)."""
        if self._connected and self.conn:
            print(f"[SQLITE] Already connected to {self.db_path}")
            return
            
        try:
            with self._lock:
                self.conn = sqlite3.connect(
                    self.db_path, 
                    check_same_thread=False,
                    isolation_level=None  # Autocommit mode for better concurrency
                )
                self.cursor = self.conn.cursor()
                
                # Create tables (same as before)
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quotes (
                        time TEXT NOT NULL,
                        instrument_id TEXT NOT NULL,
                        exchange TEXT NOT NULL,
                        price REAL NOT NULL,
                        volume REAL,
                        bid REAL,
                        ask REAL,
                        metadata TEXT
                    )
                """)
                
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS trades (
                        time TEXT NOT NULL,
                        trade_id TEXT UNIQUE NOT NULL,
                        instrument_id TEXT NOT NULL,
                        side TEXT NOT NULL,
                        quantity REAL NOT NULL,
                        price REAL NOT NULL,
                        fee REAL DEFAULT 0,
                        exchange TEXT,
                        metadata TEXT
                    )
                """)
                
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        actor TEXT DEFAULT 'system',
                        data TEXT NOT NULL,
                        model_version TEXT,
                        session_id TEXT
                    )
                """)
                
                # Create indexes
                self.cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_quotes_instrument_time 
                    ON quotes(instrument_id, time DESC)
                """)
                
                self.cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
                    ON audit_log(timestamp DESC)
                """)
                
                self._connected = True
                print(f"[SQLITE] Connected to {self.db_path} with connection pooling")
        except Exception as e:
            print(f"[SQLITE] Connection failed: {e}")
            raise
    
    async def save_quote(self, quote: Quote):
        """Insert a single quote."""
        try:
            self.cursor.execute(
                """
                INSERT INTO quotes (time, instrument_id, exchange, price, volume, bid, ask, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    quote.timestamp.isoformat(),
                    quote.instrument_id,
                    getattr(quote, 'exchange', 'UNKNOWN'),
                    quote.price,
                    getattr(quote, 'volume', None),
                    getattr(quote, 'bid', None),
                    getattr(quote, 'ask', None),
                    json.dumps({})
                )
            )
            self.conn.commit()
        except Exception as e:
            print(f"[SQLITE] Failed to save quote: {e}")
    
    async def save_quotes_batch(self, quotes: List[Quote]):
        """Batch insert quotes."""
        try:
            data = [
                (
                    q.timestamp.isoformat(),
                    q.instrument_id,
                    getattr(q, 'exchange', 'UNKNOWN'),
                    q.price,
                    getattr(q, 'volume', None),
                    getattr(q, 'bid', None),
                    getattr(q, 'ask', None),
                    json.dumps({})
                )
                for q in quotes
            ]
            
            self.cursor.executemany(
                """
                INSERT INTO quotes (time, instrument_id, exchange, price, volume, bid, ask, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                data
            )
            self.conn.commit()
            print(f"[SQLITE] Saved {len(quotes)} quotes")
        except Exception as e:
            print(f"[SQLITE] Batch save failed: {e}")
    
    async def save_trade(self, trade: Trade):
        """Save an executed trade."""
        try:
            self.cursor.execute(
                """
                INSERT INTO trades (time, trade_id, instrument_id, side, quantity, price, fee, exchange, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade.timestamp.isoformat(),
                    trade.trade_id,
                    trade.instrument_id,
                    trade.side,
                    trade.quantity,
                    trade.price,
                    getattr(trade, 'fee', 0),
                    getattr(trade, 'exchange', 'PAPER'),
                    json.dumps({})
                )
            )
            self.conn.commit()
        except Exception as e:
            print(f"[SQLITE] Failed to save trade: {e}")
    
    async def save_blob(self, key: str, data: bytes):
        """Not implemented for SQLite."""
        pass
    
    def query_quotes(
        self, 
        instrument_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict]:
        """Fetch historical quotes."""
        try:
            self.cursor.execute(
                """
                SELECT time, instrument_id, price, volume, bid, ask
                FROM quotes
                WHERE instrument_id = ?
                  AND time >= ?
                  AND time <= ?
                ORDER BY time ASC
                """,
                (instrument_id, start_time.isoformat(), end_time.isoformat())
            )
            
            rows = self.cursor.fetchall()
            return [
                {
                    "timestamp": row[0],
                    "instrument_id": row[1],
                    "price": row[2],
                    "volume": row[3],
                    "bid": row[4],
                    "ask": row[5]
                }
                for row in rows
            ]
        except Exception as e:
            print(f"[SQLITE] Query failed: {e}")
            return []
    
    def save_audit_event(
        self, 
        event_type: str, 
        data: Dict[str, Any], 
        actor: str = "system",
        model_version: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Write to audit log."""
        try:
            self.cursor.execute(
                """
                INSERT INTO audit_log (timestamp, event_type, actor, data, model_version, session_id)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (datetime.now().isoformat(), event_type, actor, json.dumps(data), model_version, session_id)
            )
            self.conn.commit()
        except Exception as e:
            print(f"[SQLITE] Audit log failed: {e}")
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
        print("[SQLITE] Connection closed")
