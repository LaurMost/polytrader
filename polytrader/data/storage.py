"""
Data storage for Polytrader.

Provides SQLite storage for trades, orders, and positions with CSV export.
"""

import csv
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from polytrader.config import get_config
from polytrader.data.models import Order, OrderSide, OrderStatus, OrderType, Position, Trade
from polytrader.utils.logging import get_logger

logger = get_logger(__name__)


class Storage:
    """
    SQLite-based storage with CSV export capabilities.
    
    Usage:
        storage = Storage()
        
        # Save a trade
        storage.save_trade(trade)
        
        # Query trades
        trades = storage.get_trades(market_id="...")
        
        # Export to CSV
        storage.export_trades_csv("trades.csv")
    """

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize storage.
        
        Args:
            db_path: Path to SQLite database (default from config)
        """
        self.config = get_config()
        self.db_path = db_path or self.config.database_path
        self.csv_dir = self.config.csv_dir
        
        # Ensure directories exist
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.csv_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Orders table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS orders (
                    id TEXT PRIMARY KEY,
                    market_id TEXT,
                    token_id TEXT,
                    side TEXT,
                    order_type TEXT,
                    status TEXT,
                    price REAL,
                    size REAL,
                    filled_size REAL,
                    is_paper INTEGER,
                    created_at TEXT,
                    updated_at TEXT,
                    filled_at TEXT
                )
            """)
            
            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    order_id TEXT,
                    market_id TEXT,
                    token_id TEXT,
                    side TEXT,
                    price REAL,
                    size REAL,
                    fee REAL,
                    is_paper INTEGER,
                    executed_at TEXT,
                    FOREIGN KEY (order_id) REFERENCES orders(id)
                )
            """)
            
            # Positions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS positions (
                    token_id TEXT PRIMARY KEY,
                    market_id TEXT,
                    size REAL,
                    avg_entry_price REAL,
                    realized_pnl REAL,
                    opened_at TEXT,
                    updated_at TEXT
                )
            """)
            
            # Price history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT,
                    token_id TEXT,
                    price REAL,
                    timestamp TEXT
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(executed_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_orders_market ON orders(market_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_price_market ON price_history(market_id)")
            
            conn.commit()

    def _connect(self) -> sqlite3.Connection:
        """Create database connection."""
        return sqlite3.connect(self.db_path)

    # ==================== Order Operations ====================

    def save_order(self, order: Order) -> None:
        """Save an order to the database."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO orders
                (id, market_id, token_id, side, order_type, status, price, size,
                 filled_size, is_paper, created_at, updated_at, filled_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                order.id,
                order.market_id,
                order.token_id,
                order.side.value,
                order.order_type.value,
                order.status.value,
                order.price,
                order.size,
                order.filled_size,
                1 if order.is_paper else 0,
                order.created_at.isoformat() if order.created_at else None,
                order.updated_at.isoformat() if order.updated_at else None,
                order.filled_at.isoformat() if order.filled_at else None,
            ))
            conn.commit()

    def get_order(self, order_id: str) -> Optional[Order]:
        """Get an order by ID."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_order(row)
        return None

    def get_orders(
        self,
        market_id: Optional[str] = None,
        status: Optional[OrderStatus] = None,
        limit: int = 100,
    ) -> list[Order]:
        """Get orders with optional filters."""
        query = "SELECT * FROM orders WHERE 1=1"
        params = []
        
        if market_id:
            query += " AND market_id = ?"
            params.append(market_id)
        
        if status:
            query += " AND status = ?"
            params.append(status.value)
        
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_order(row) for row in cursor.fetchall()]

    def _row_to_order(self, row: tuple) -> Order:
        """Convert database row to Order object."""
        return Order(
            id=row[0],
            market_id=row[1],
            token_id=row[2],
            side=OrderSide(row[3]),
            order_type=OrderType(row[4]),
            status=OrderStatus(row[5]),
            price=row[6],
            size=row[7],
            filled_size=row[8],
            is_paper=bool(row[9]),
            created_at=datetime.fromisoformat(row[10]) if row[10] else None,
            updated_at=datetime.fromisoformat(row[11]) if row[11] else None,
            filled_at=datetime.fromisoformat(row[12]) if row[12] else None,
        )

    # ==================== Trade Operations ====================

    def save_trade(self, trade: Trade) -> None:
        """Save a trade to the database."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO trades
                (id, order_id, market_id, token_id, side, price, size, fee,
                 is_paper, executed_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.id,
                trade.order_id,
                trade.market_id,
                trade.token_id,
                trade.side.value,
                trade.price,
                trade.size,
                trade.fee,
                1 if trade.is_paper else 0,
                trade.executed_at.isoformat() if trade.executed_at else None,
            ))
            conn.commit()

    def get_trades(
        self,
        market_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> list[Trade]:
        """Get trades with optional filters."""
        query = "SELECT * FROM trades WHERE 1=1"
        params = []
        
        if market_id:
            query += " AND market_id = ?"
            params.append(market_id)
        
        if start_date:
            query += " AND executed_at >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND executed_at <= ?"
            params.append(end_date.isoformat())
        
        query += " ORDER BY executed_at DESC LIMIT ?"
        params.append(limit)
        
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [self._row_to_trade(row) for row in cursor.fetchall()]

    def _row_to_trade(self, row: tuple) -> Trade:
        """Convert database row to Trade object."""
        return Trade(
            id=row[0],
            order_id=row[1],
            market_id=row[2],
            token_id=row[3],
            side=OrderSide(row[4]),
            price=row[5],
            size=row[6],
            fee=row[7],
            is_paper=bool(row[8]),
            executed_at=datetime.fromisoformat(row[9]) if row[9] else None,
        )

    # ==================== Position Operations ====================

    def save_position(self, position: Position) -> None:
        """Save a position to the database."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO positions
                (token_id, market_id, size, avg_entry_price, realized_pnl,
                 opened_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                position.token_id,
                position.market_id,
                position.size,
                position.avg_entry_price,
                position.realized_pnl,
                position.opened_at.isoformat() if position.opened_at else None,
                position.updated_at.isoformat() if position.updated_at else None,
            ))
            conn.commit()

    def get_positions(self) -> list[Position]:
        """Get all positions."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM positions WHERE size != 0")
            return [self._row_to_position(row) for row in cursor.fetchall()]

    def _row_to_position(self, row: tuple) -> Position:
        """Convert database row to Position object."""
        return Position(
            token_id=row[0],
            market_id=row[1],
            size=row[2],
            avg_entry_price=row[3],
            realized_pnl=row[4],
            opened_at=datetime.fromisoformat(row[5]) if row[5] else None,
            updated_at=datetime.fromisoformat(row[6]) if row[6] else None,
        )

    # ==================== Price History ====================

    def save_price(self, market_id: str, token_id: str, price: float) -> None:
        """Save a price point."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO price_history (market_id, token_id, price, timestamp)
                VALUES (?, ?, ?, ?)
            """, (market_id, token_id, price, datetime.now().isoformat()))
            conn.commit()

    def get_price_history(
        self,
        market_id: str,
        token_id: Optional[str] = None,
        limit: int = 1000,
    ) -> pd.DataFrame:
        """Get price history as DataFrame."""
        query = "SELECT * FROM price_history WHERE market_id = ?"
        params = [market_id]
        
        if token_id:
            query += " AND token_id = ?"
            params.append(token_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self._connect() as conn:
            return pd.read_sql_query(query, conn, params=params)

    # ==================== CSV Export ====================

    def export_trades_csv(self, filename: Optional[str] = None) -> Path:
        """Export trades to CSV."""
        filename = filename or f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.csv_dir / filename
        
        trades = self.get_trades(limit=10000)
        
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "order_id", "market_id", "token_id", "side",
                "price", "size", "fee", "is_paper", "executed_at"
            ])
            
            for trade in trades:
                writer.writerow([
                    trade.id,
                    trade.order_id,
                    trade.market_id,
                    trade.token_id,
                    trade.side.value,
                    trade.price,
                    trade.size,
                    trade.fee,
                    trade.is_paper,
                    trade.executed_at.isoformat() if trade.executed_at else "",
                ])
        
        logger.info(f"Exported {len(trades)} trades to {filepath}")
        return filepath

    def export_orders_csv(self, filename: Optional[str] = None) -> Path:
        """Export orders to CSV."""
        filename = filename or f"orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.csv_dir / filename
        
        orders = self.get_orders(limit=10000)
        
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "market_id", "token_id", "side", "order_type", "status",
                "price", "size", "filled_size", "is_paper", "created_at"
            ])
            
            for order in orders:
                writer.writerow([
                    order.id,
                    order.market_id,
                    order.token_id,
                    order.side.value,
                    order.order_type.value,
                    order.status.value,
                    order.price,
                    order.size,
                    order.filled_size,
                    order.is_paper,
                    order.created_at.isoformat() if order.created_at else "",
                ])
        
        logger.info(f"Exported {len(orders)} orders to {filepath}")
        return filepath

    def export_positions_csv(self, filename: Optional[str] = None) -> Path:
        """Export positions to CSV."""
        filename = filename or f"positions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = self.csv_dir / filename
        
        positions = self.get_positions()
        
        with open(filepath, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "token_id", "market_id", "size", "avg_entry_price",
                "realized_pnl", "opened_at", "updated_at"
            ])
            
            for pos in positions:
                writer.writerow([
                    pos.token_id,
                    pos.market_id,
                    pos.size,
                    pos.avg_entry_price,
                    pos.realized_pnl,
                    pos.opened_at.isoformat() if pos.opened_at else "",
                    pos.updated_at.isoformat() if pos.updated_at else "",
                ])
        
        logger.info(f"Exported {len(positions)} positions to {filepath}")
        return filepath

    # ==================== Statistics ====================

    def get_stats(self) -> dict[str, Any]:
        """Get storage statistics."""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM trades")
            total_trades = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM positions WHERE size != 0")
            open_positions = cursor.fetchone()[0]
            
            cursor.execute("SELECT SUM(size * price) FROM trades WHERE side = 'BUY'")
            total_bought = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT SUM(size * price) FROM trades WHERE side = 'SELL'")
            total_sold = cursor.fetchone()[0] or 0
            
            return {
                "total_orders": total_orders,
                "total_trades": total_trades,
                "open_positions": open_positions,
                "total_volume_bought": total_bought,
                "total_volume_sold": total_sold,
                "total_volume": total_bought + total_sold,
            }

    def __repr__(self) -> str:
        return f"Storage(db={self.db_path})"

