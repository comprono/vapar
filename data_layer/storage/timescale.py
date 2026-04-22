import psycopg2
from psycopg2.extras import execute_batch, Json
from typing import List, Optional, Dict, Any
from datetime import datetime
from common.schemas.market_data import Quote, Trade
from data_layer.storage.base import BaseStorage

class TimescaleStorage(BaseStorage):
    """
    TimescaleDB + Postgres storage adapter.
    Provides efficient time-series storage and audit logging.
    """
    
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.conn = None
        self.cursor = None
    
    async def connect(self):
        """Establish database connection."""
        try:
            self.conn = psycopg2.connect(self.connection_string)
            self.cursor = self.conn.cursor()
            print("[TIMESCALE] Connected to database")
        except Exception as e:
            print(f"[TIMESCALE] Connection failed: {e}")
            raise
    
    async def save_quote(self, quote: Quote):
        """Insert a single quote."""
        try:
            self.cursor.execute(
                """
                INSERT INTO quotes (time, instrument_id, exchange, price, volume, bid, ask, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    quote.timestamp,
                    quote.instrument_id,
                    quote.exchange if hasattr(quote, 'exchange') else 'UNKNOWN',
                    quote.price,
                    getattr(quote, 'volume', None),
                    getattr(quote, 'bid', None),
                    getattr(quote, 'ask', None),
                    Json({})
                )
            )
            self.conn.commit()
        except Exception as e:
            print(f"[TIMESCALE] Failed to save quote: {e}")
            self.conn.rollback()
    
    async def save_quotes_batch(self, quotes: List[Quote]):
        """Batch insert quotes for performance."""
        try:
            data = [
                (
                    q.timestamp,
                    q.instrument_id,
                    getattr(q, 'exchange', 'UNKNOWN'),
                    q.price,
                    getattr(q, 'volume', None),
                    getattr(q, 'bid', None),
                    getattr(q, 'ask', None),
                    Json({})
                )
                for q in quotes
            ]
            
            execute_batch(
                self.cursor,
                """
                INSERT INTO quotes (time, instrument_id, exchange, price, volume, bid, ask, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                data
            )
            self.conn.commit()
            print(f"[TIMESCALE] Saved {len(quotes)} quotes")
        except Exception as e:
            print(f"[TIMESCALE] Batch save failed: {e}")
            self.conn.rollback()
    
    async def save_trade(self, trade: Trade):
        """Save an executed trade."""
        try:
            self.cursor.execute(
                """
                INSERT INTO trades (time, trade_id, instrument_id, side, quantity, price, fee, exchange, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    trade.timestamp,
                    trade.trade_id,
                    trade.instrument_id,
                    trade.side,
                    trade.quantity,
                    trade.price,
                    getattr(trade, 'fee', 0),
                    getattr(trade, 'exchange', 'PAPER'),
                    Json({})
                )
            )
            self.conn.commit()
        except Exception as e:
            print(f"[TIMESCALE] Failed to save trade: {e}")
            self.conn.rollback()
    
    async def save_blob(self, key: str, data: bytes):
        """Store binary data (not implemented for now)."""
        pass
    
    def query_quotes(
        self, 
        instrument_id: str, 
        start_time: datetime, 
        end_time: datetime
    ) -> List[Dict]:
        """Fetch historical quotes for a symbol and time range."""
        try:
            self.cursor.execute(
                """
                SELECT time, instrument_id, price, volume, bid, ask
                FROM quotes
                WHERE instrument_id = %s
                  AND time >= %s
                  AND time <= %s
                ORDER BY time ASC
                """,
                (instrument_id, start_time, end_time)
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
            print(f"[TIMESCALE] Query failed: {e}")
            return []
    
    def save_audit_event(
        self, 
        event_type: str, 
        data: Dict[str, Any], 
        actor: str = "system",
        model_version: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        """Write to immutable audit log."""
        try:
            self.cursor.execute(
                """
                INSERT INTO audit_log (event_type, actor, data, model_version, session_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (event_type, actor, Json(data), model_version, session_id)
            )
            self.conn.commit()
        except Exception as e:
            print(f"[TIMESCALE] Audit log failed: {e}")
            self.conn.rollback()
    
    def close(self):
        """Close database connection."""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        print("[TIMESCALE] Connection closed")
