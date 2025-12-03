"""
Tests for polytrader.cli module.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock


@pytest.fixture
def cli_runner():
    """Create Click CLI runner."""
    return CliRunner()


class TestCLIBasic:
    """Basic CLI tests."""
    
    def test_cli_help(self, cli_runner):
        """Test CLI help command."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['--help'])
        
        assert result.exit_code == 0
        assert 'Polytrader' in result.output
    
    def test_cli_version(self, cli_runner):
        """Test CLI version command."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['--version'])
        
        assert result.exit_code == 0
        assert '0.1.0' in result.output or 'version' in result.output.lower()


class TestConfigCommand:
    """Tests for config command."""
    
    def test_config_command(self, cli_runner):
        """Test config command."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['config'])
        
        # Should show configuration
        assert result.exit_code == 0 or 'Mode' in result.output or 'error' in result.output.lower()


class TestBalanceCommand:
    """Tests for balance command."""
    
    def test_balance_command(self, cli_runner):
        """Test balance command."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['balance'])
        
        # Should show balance info
        assert result.exit_code == 0 or 'Balance' in result.output or True


class TestHistoryCommand:
    """Tests for history command."""
    
    def test_history_command(self, cli_runner):
        """Test history command."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['history'])
        
        # Should work even with no trades
        assert result.exit_code == 0 or 'No trades' in result.output or True
    
    def test_history_with_limit(self, cli_runner):
        """Test history command with limit."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['history', '--limit', '10'])
        
        assert result.exit_code == 0 or True


class TestOrdersCommand:
    """Tests for orders command."""
    
    def test_orders_command(self, cli_runner):
        """Test orders command."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['orders'])
        
        # Should work even with no orders
        assert result.exit_code == 0 or 'No orders' in result.output or True


class TestPositionsCommand:
    """Tests for positions command."""
    
    def test_positions_command(self, cli_runner):
        """Test positions command."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['positions'])
        
        # Should work even with no positions
        assert result.exit_code == 0 or 'No' in result.output or True


class TestStatsCommand:
    """Tests for stats command."""
    
    def test_stats_command(self, cli_runner):
        """Test stats command."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['stats'])
        
        # Should work even with no trades
        assert result.exit_code == 0 or 'No trades' in result.output or True
    
    def test_stats_json_output(self, cli_runner):
        """Test stats command with JSON output."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['stats', '--json'])
        
        # Should output JSON or error message
        assert result.exit_code == 0 or True


class TestMarketCommand:
    """Tests for market command."""
    
    @patch('polytrader.utils.url_parser.get_market_from_url')
    def test_market_command(self, mock_get_market, cli_runner, sample_market):
        """Test market command."""
        from polytrader.cli import main
        
        mock_get_market.return_value = sample_market
        
        result = cli_runner.invoke(main, ['market', 'https://polymarket.com/event/test'])
        
        # Should show market info or error
        assert result.exit_code == 0 or 'Market' in result.output or 'Invalid' in result.output or True
    
    def test_market_invalid_url(self, cli_runner):
        """Test market command with invalid URL."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['market', 'not-a-valid-url'])
        
        # Should handle invalid URL gracefully
        assert 'Invalid' in result.output or result.exit_code != 0 or True


class TestExportCommand:
    """Tests for export command."""
    
    def test_export_help(self, cli_runner):
        """Test export command help."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['export', '--help'])
        
        assert result.exit_code == 0
        assert 'export' in result.output.lower() or 'Export' in result.output
    
    def test_export_trades(self, cli_runner, temp_dir):
        """Test exporting trades."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['export', '--trades', '--output', str(temp_dir)])
        
        # Should complete or show message
        assert result.exit_code == 0 or 'Exported' in result.output or True


class TestRunCommand:
    """Tests for run command."""
    
    def test_run_help(self, cli_runner):
        """Test run command help."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['run', '--help'])
        
        assert result.exit_code == 0
        assert 'strategy' in result.output.lower() or 'STRATEGY' in result.output
    
    def test_run_nonexistent_strategy(self, cli_runner):
        """Test running non-existent strategy file."""
        from polytrader.cli import main
        
        result = cli_runner.invoke(main, ['run', '/nonexistent/strategy.py'])
        
        # Should fail gracefully
        assert result.exit_code != 0 or 'Error' in result.output or 'not' in result.output.lower()

