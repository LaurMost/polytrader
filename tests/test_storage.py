"""
Tests for polytrader.data.storage module.
"""

import pytest
from datetime import datetime
from pathlib import Path


class TestStorage:
    """Tests for Storage class."""
    
    def test_storage_initialization(self, temp_dir):
        """Test Storage initialization."""
        from polytrader.data.storage import Storage
        
        db_path = temp_dir / "test.db"
        storage = Storage(db_path=db_path)
        
        assert storage is not None
        assert storage.db_path == db_path
    
    def test_save_and_get_trade(self, temp_dir, sample_trade):
        """Test saving and retrieving a trade."""
        from polytrader.data.storage import Storage
        
        db_path = temp_dir / "test.db"
        storage = Storage(db_path=db_path)
        
        # Save trade
        storage.save_trade(sample_trade)
        
        # Retrieve trades
        trades = storage.get_trades(limit=10)
        
        assert len(trades) >= 1
        assert trades[0].id == sample_trade.id
    
    def test_save_and_get_order(self, temp_dir, sample_order):
        """Test saving and retrieving an order."""
        from polytrader.data.storage import Storage
        
        db_path = temp_dir / "test.db"
        storage = Storage(db_path=db_path)
        
        # Save order
        storage.save_order(sample_order)
        
        # Retrieve orders
        orders = storage.get_orders(limit=10)
        
        assert len(orders) >= 1
        assert orders[0].id == sample_order.id
    
    def test_save_and_get_position(self, temp_dir, sample_position):
        """Test saving and retrieving a position."""
        from polytrader.data.storage import Storage
        
        db_path = temp_dir / "test.db"
        storage = Storage(db_path=db_path)
        
        # Save position
        storage.save_position(sample_position)
        
        # Retrieve all positions
        positions = storage.get_positions()
        
        assert len(positions) >= 1
        assert positions[0].token_id == sample_position.token_id
    
    def test_get_trades_with_limit(self, temp_dir, sample_trades):
        """Test getting trades with limit."""
        from polytrader.data.storage import Storage
        
        db_path = temp_dir / "test.db"
        storage = Storage(db_path=db_path)
        
        # Save multiple trades
        for trade in sample_trades[:10]:
            storage.save_trade(trade)
        
        # Get with limit
        trades = storage.get_trades(limit=5)
        
        assert len(trades) == 5
    
    def test_export_trades_csv(self, temp_dir, sample_trades):
        """Test exporting trades to CSV."""
        from polytrader.data.storage import Storage
        
        db_path = temp_dir / "test.db"
        storage = Storage(db_path=db_path)
        
        # Save trades
        for trade in sample_trades[:5]:
            storage.save_trade(trade)
        
        # Export to CSV
        csv_path = storage.export_trades_csv()
        
        assert Path(csv_path).exists()
        
        # Verify content
        with open(csv_path, 'r') as f:
            content = f.read()
            assert 'id' in content
            assert 'price' in content
    
    def test_export_orders_csv(self, temp_dir, sample_order):
        """Test exporting orders to CSV."""
        from polytrader.data.storage import Storage
        
        db_path = temp_dir / "test.db"
        storage = Storage(db_path=db_path)
        
        # Save order
        storage.save_order(sample_order)
        
        # Export to CSV
        csv_path = storage.export_orders_csv()
        
        assert Path(csv_path).exists()
    
    def test_update_order(self, temp_dir, sample_order):
        """Test updating an order."""
        from polytrader.data.storage import Storage
        from polytrader.data.models import OrderStatus
        
        db_path = temp_dir / "test.db"
        storage = Storage(db_path=db_path)
        
        # Save order
        storage.save_order(sample_order)
        
        # Update order status
        sample_order.status = OrderStatus.FILLED
        storage.save_order(sample_order)
        
        # Retrieve and verify
        orders = storage.get_orders(limit=10)
        updated_order = next((o for o in orders if o.id == sample_order.id), None)
        
        assert updated_order is not None
        assert updated_order.status == OrderStatus.FILLED
    
    def test_empty_database(self, temp_dir):
        """Test operations on empty database."""
        from polytrader.data.storage import Storage
        
        db_path = temp_dir / "test.db"
        storage = Storage(db_path=db_path)
        
        trades = storage.get_trades(limit=10)
        orders = storage.get_orders(limit=10)
        
        assert trades == []
        assert orders == []
    
    def test_get_positions_empty(self, temp_dir):
        """Test getting positions from empty database."""
        from polytrader.data.storage import Storage
        
        db_path = temp_dir / "test.db"
        storage = Storage(db_path=db_path)
        
        positions = storage.get_positions()
        
        assert positions == []


class TestStoragePersistence:
    """Tests for storage persistence."""
    
    def test_data_persists_across_instances(self, temp_dir, sample_trade):
        """Test that data persists when creating new Storage instance."""
        from polytrader.data.storage import Storage
        
        db_path = temp_dir / "test.db"
        
        # Save with first instance
        storage1 = Storage(db_path=db_path)
        storage1.save_trade(sample_trade)
        
        # Create new instance and retrieve
        storage2 = Storage(db_path=db_path)
        trades = storage2.get_trades(limit=10)
        
        assert len(trades) >= 1
        assert trades[0].id == sample_trade.id

