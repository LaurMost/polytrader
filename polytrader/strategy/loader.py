"""
Strategy loader for dynamically loading strategy scripts.
"""

import importlib.util
import inspect
from pathlib import Path
from typing import Optional, Type

from polytrader.strategy.base import Strategy
from polytrader.utils.logging import get_logger

logger = get_logger(__name__)


class StrategyLoader:
    """
    Loads strategy classes from Python files.
    
    Usage:
        loader = StrategyLoader()
        strategy_class = loader.load("strategies/my_strategy.py")
        strategy = strategy_class()
    """

    def load(self, path: str) -> Optional[Type[Strategy]]:
        """
        Load a strategy class from a Python file.
        
        Args:
            path: Path to the strategy Python file
            
        Returns:
            Strategy class, or None if not found
        """
        file_path = Path(path)
        
        if not file_path.exists():
            logger.error(f"Strategy file not found: {path}")
            return None
        
        if not file_path.suffix == ".py":
            logger.error(f"Strategy file must be a Python file: {path}")
            return None
        
        try:
            # Load the module
            spec = importlib.util.spec_from_file_location(
                file_path.stem,
                file_path
            )
            
            if spec is None or spec.loader is None:
                logger.error(f"Could not load module spec: {path}")
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Find Strategy subclass
            strategy_class = self._find_strategy_class(module)
            
            if strategy_class is None:
                logger.error(f"No Strategy subclass found in: {path}")
                return None
            
            logger.info(f"Loaded strategy: {strategy_class.name}")
            return strategy_class
            
        except Exception as e:
            logger.error(f"Failed to load strategy: {e}")
            return None

    def _find_strategy_class(self, module) -> Optional[Type[Strategy]]:
        """Find a Strategy subclass in a module."""
        for name, obj in inspect.getmembers(module):
            if (
                inspect.isclass(obj) and
                issubclass(obj, Strategy) and
                obj is not Strategy
            ):
                return obj
        return None

    def load_multiple(self, paths: list[str]) -> list[Type[Strategy]]:
        """
        Load multiple strategy classes.
        
        Args:
            paths: List of paths to strategy files
            
        Returns:
            List of loaded strategy classes
        """
        strategies = []
        for path in paths:
            strategy_class = self.load(path)
            if strategy_class:
                strategies.append(strategy_class)
        return strategies

