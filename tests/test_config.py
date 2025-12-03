"""
Tests for polytrader.config module.
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


class TestConfig:
    """Tests for configuration loading and management."""
    
    def test_config_singleton(self):
        """Test that Config is a singleton."""
        from polytrader.config import Config
        
        # Reset singleton for testing
        Config._instance = None
        Config._config = {}
        
        config1 = Config()
        config2 = Config()
        
        assert config1 is config2
    
    def test_config_default_mode(self):
        """Test that config has default mode."""
        from polytrader.config import Config
        
        # Reset singleton
        Config._instance = None
        Config._config = {}
        
        config = Config()
        
        # Should have default mode
        assert config.mode in ("paper", "live")
    
    def test_config_paper_mode(self):
        """Test paper mode detection."""
        from polytrader.config import Config
        
        # Reset singleton
        Config._instance = None
        Config._config = {}
        
        config = Config()
        config.set("mode", "paper")
        
        assert config.is_paper == True
        assert config.mode == "paper"
    
    def test_config_live_mode(self):
        """Test live mode detection."""
        from polytrader.config import Config
        
        # Reset singleton
        Config._instance = None
        Config._config = {}
        
        config = Config()
        config.set("mode", "live")
        
        assert config.is_live == True
        assert config.mode == "live"
    
    def test_config_set_method(self):
        """Test setting config values."""
        from polytrader.config import Config
        
        # Reset singleton
        Config._instance = None
        Config._config = {}
        
        config = Config()
        config.set("mode", "live")
        
        assert config.get("mode") == "live"
    
    def test_config_get_method(self):
        """Test getting config values."""
        from polytrader.config import Config
        
        # Reset singleton
        Config._instance = None
        Config._config = {}
        
        config = Config()
        
        assert config.get("nonexistent", "default") == "default"
    
    def test_config_get_nested(self):
        """Test getting nested config values with dot notation."""
        from polytrader.config import Config
        
        # Reset singleton
        Config._instance = None
        Config._config = {}
        
        config = Config()
        
        # Should have default API settings
        assert config.get("api.chain_id", 137) == 137
    
    def test_get_config_function(self):
        """Test get_config function returns config."""
        from polytrader.config import get_config, Config
        
        # Reset singleton
        Config._instance = None
        Config._config = {}
        
        config = get_config()
        
        assert config is not None
        assert isinstance(config, Config)
    
    def test_config_properties(self):
        """Test config property accessors."""
        from polytrader.config import Config
        
        # Reset singleton
        Config._instance = None
        Config._config = {}
        
        config = Config()
        
        # Test various properties
        assert isinstance(config.host, str)
        assert isinstance(config.chain_id, int)
        assert isinstance(config.data_dir, Path)


class TestConfigEnvVars:
    """Tests for environment variable substitution."""
    
    def test_env_var_substitution(self):
        """Test that ${VAR} patterns are substituted."""
        from polytrader.config import Config
        
        config = Config()
        
        # Test internal substitution method
        test_dict = {"key": "${TEST_VAR}"}
        
        with patch.dict(os.environ, {"TEST_VAR": "test_value"}):
            result = config._substitute_env_vars(test_dict)
            assert result["key"] == "test_value"
    
    def test_env_var_with_default(self):
        """Test ${VAR:default} pattern."""
        from polytrader.config import Config
        
        config = Config()
        
        # Test with default value
        test_dict = {"key": "${NONEXISTENT_VAR:default_value}"}
        result = config._substitute_env_vars(test_dict)
        
        assert result["key"] == "default_value"

