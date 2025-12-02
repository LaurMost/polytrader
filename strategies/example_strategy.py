"""
Example trading strategy for Polytrader.

This strategy demonstrates:
- How to define market targets
- Implementing trading logic in on_price_update
- Using indicators for signals
- Position management
- Logging and signal tracking

Run with:
    polytrader run strategies/example_strategy.py --paper
"""

from polytrader import Strategy, Market
from polytrader.indicators import sma, rsi, momentum


class MomentumStrategy(Strategy):
    """
    A simple momentum-based strategy for prediction markets.
    
    Strategy Logic:
    - Buy YES when price momentum is positive and RSI < 70
    - Sell when RSI > 80 or momentum turns negative
    - Use SMA crossover as confirmation
    
    This is an example strategy - not financial advice!
    """
    
    # Strategy metadata
    name = "momentum_example"
    description = "Simple momentum strategy for prediction markets"
    version = "1.0.0"
    
    # Markets to trade - replace with actual Polymarket URLs
    markets = [
        # Add your target market URLs here:
        # "https://polymarket.com/event/fed-decision-in-october",
        # "https://polymarket.com/event/bitcoin-100k",
    ]
    
    # Strategy parameters
    RSI_PERIOD = 14
    SMA_FAST = 5
    SMA_SLOW = 20
    RSI_OVERBOUGHT = 70
    RSI_OVERSOLD = 30
    POSITION_SIZE = 50  # USDC per trade
    
    def __init__(self):
        super().__init__()
        
        # Price history for indicators
        self._price_history: dict[str, list[float]] = {}
        
        # Track last signals to avoid spam
        self._last_signal: dict[str, str] = {}
    
    def on_start(self) -> None:
        """Called when strategy starts."""
        self.log(f"Starting {self.name} strategy")
        self.log(f"Parameters: RSI={self.RSI_PERIOD}, SMA_FAST={self.SMA_FAST}, SMA_SLOW={self.SMA_SLOW}")
        self.log(f"Tracking {len(self.markets)} markets")
        
        # Initialize price history for each market
        for market in self._markets.values():
            self._price_history[market.id] = []
    
    def on_stop(self) -> None:
        """Called when strategy stops."""
        self.log("Strategy stopped")
        self.log(f"Final P&L: ${self.pnl:.2f}")
        self.log(f"Total trades: {self._stats['total_trades']}")
    
    def on_price_update(self, market: Market, price: float) -> None:
        """
        Main trading logic - called on every price update.
        
        Args:
            market: Market with updated prices
            price: Current price (YES token)
        """
        # Store price in history
        if market.id not in self._price_history:
            self._price_history[market.id] = []
        
        self._price_history[market.id].append(price)
        prices = self._price_history[market.id]
        
        # Need enough data for indicators
        if len(prices) < self.SMA_SLOW:
            return
        
        # Calculate indicators
        current_rsi = rsi(prices, self.RSI_PERIOD).iloc[-1]
        sma_fast = sma(prices, self.SMA_FAST).iloc[-1]
        sma_slow = sma(prices, self.SMA_SLOW).iloc[-1]
        current_momentum = momentum(prices, 5).iloc[-1]
        
        # Get current position
        current_position = self.position(market)
        
        # Generate signals
        signal = self._generate_signal(
            price=price,
            rsi_value=current_rsi,
            sma_fast=sma_fast,
            sma_slow=sma_slow,
            momentum_value=current_momentum,
            has_position=current_position > 0,
        )
        
        # Execute signal
        if signal and signal != self._last_signal.get(market.id):
            self._execute_signal(market, signal, price)
            self._last_signal[market.id] = signal
    
    def _generate_signal(
        self,
        price: float,
        rsi_value: float,
        sma_fast: float,
        sma_slow: float,
        momentum_value: float,
        has_position: bool,
    ) -> str:
        """
        Generate trading signal based on indicators.
        
        Returns:
            "BUY", "SELL", or "HOLD"
        """
        # Skip if RSI is NaN
        if rsi_value != rsi_value:  # NaN check
            return "HOLD"
        
        # BUY conditions:
        # - Not already in position
        # - RSI not overbought
        # - Positive momentum
        # - Fast SMA above slow SMA (uptrend)
        if not has_position:
            if (
                rsi_value < self.RSI_OVERBOUGHT and
                momentum_value > 0 and
                sma_fast > sma_slow
            ):
                return "BUY"
        
        # SELL conditions:
        # - Currently in position
        # - RSI overbought OR momentum negative
        if has_position:
            if rsi_value > self.RSI_OVERBOUGHT or momentum_value < 0:
                return "SELL"
        
        return "HOLD"
    
    def _execute_signal(self, market: Market, signal: str, price: float) -> None:
        """Execute a trading signal."""
        if signal == "BUY":
            self.signal(market, "BUY", f"RSI/Momentum entry at {price:.4f}")
            order = self.buy(market, size=self.POSITION_SIZE)
            
            if order:
                self.log(f"BUY order placed: {self.POSITION_SIZE} USDC at {price:.4f}")
        
        elif signal == "SELL":
            self.signal(market, "SELL", f"Exit at {price:.4f}")
            order = self.sell(market)
            
            if order:
                self.log(f"SELL order placed at {price:.4f}")
    
    def on_fill(self, order, trade) -> None:
        """Called when an order is filled."""
        self.log(f"Order filled: {trade.side.value} {trade.size}@{trade.price:.4f}")
        self._stats["total_trades"] += 1
    
    def on_error(self, error: Exception) -> None:
        """Called when an error occurs."""
        self.log(f"Error: {error}", level="error")


class SimpleValueStrategy(Strategy):
    """
    A simpler value-based strategy.
    
    Strategy Logic:
    - Buy YES when price < 0.30 (undervalued)
    - Buy NO when price > 0.70 (overvalued YES)
    - Sell when price returns to fair value (0.45-0.55)
    
    This is an example strategy - not financial advice!
    """
    
    name = "simple_value"
    description = "Buy undervalued outcomes"
    version = "1.0.0"
    
    markets = []
    
    # Value thresholds
    UNDERVALUED_YES = 0.30
    OVERVALUED_YES = 0.70
    FAIR_VALUE_LOW = 0.45
    FAIR_VALUE_HIGH = 0.55
    POSITION_SIZE = 100
    
    def on_price_update(self, market: Market, price: float) -> None:
        """Trading logic based on value."""
        yes_position = self.position(market, "YES")
        no_position = self.position(market, "NO")
        
        # Buy undervalued YES
        if price < self.UNDERVALUED_YES and yes_position == 0:
            self.signal(market, "BUY_YES", f"Undervalued at {price:.2%}")
            self.buy(market, size=self.POSITION_SIZE, outcome="YES")
        
        # Buy NO when YES is overvalued
        elif price > self.OVERVALUED_YES and no_position == 0:
            self.signal(market, "BUY_NO", f"YES overvalued at {price:.2%}")
            self.buy(market, size=self.POSITION_SIZE, outcome="NO")
        
        # Sell YES at fair value
        elif yes_position > 0 and self.FAIR_VALUE_LOW < price < self.FAIR_VALUE_HIGH:
            self.signal(market, "SELL_YES", f"Fair value reached at {price:.2%}")
            self.sell(market, outcome="YES")
        
        # Sell NO at fair value
        elif no_position > 0 and self.FAIR_VALUE_LOW < price < self.FAIR_VALUE_HIGH:
            self.signal(market, "SELL_NO", f"Fair value reached at {price:.2%}")
            self.sell(market, outcome="NO")


# You can also create strategies that use ML models:

class MLStrategy(Strategy):
    """
    Template for ML-based strategy.
    
    This shows how you might integrate a machine learning model.
    """
    
    name = "ml_template"
    description = "Machine learning based predictions"
    version = "1.0.0"
    
    markets = []
    
    def __init__(self):
        super().__init__()
        self.model = None
        self._features_buffer: dict[str, list] = {}
    
    def on_start(self) -> None:
        """Load your trained model here."""
        self.log("Loading ML model...")
        
        # Example: Load a trained model
        # from joblib import load
        # self.model = load("models/my_model.joblib")
        
        # For this example, we'll use a simple heuristic
        self.model = None
        self.log("ML model loaded (placeholder)")
    
    def on_price_update(self, market: Market, price: float) -> None:
        """Generate predictions using ML model."""
        # Collect features
        features = self._extract_features(market, price)
        
        if features is None:
            return
        
        # Make prediction
        if self.model:
            # prediction = self.model.predict([features])[0]
            # probability = self.model.predict_proba([features])[0]
            pass
        else:
            # Placeholder: simple rule
            prediction = 1 if price < 0.4 else 0
        
        # Execute based on prediction
        if prediction == 1 and self.position(market) == 0:
            self.buy(market, size=50)
        elif prediction == 0 and self.position(market) > 0:
            self.sell(market)
    
    def _extract_features(self, market: Market, price: float) -> list:
        """Extract features for ML model."""
        if market.id not in self._features_buffer:
            self._features_buffer[market.id] = []
        
        self._features_buffer[market.id].append(price)
        prices = self._features_buffer[market.id]
        
        # Need enough history
        if len(prices) < 20:
            return None
        
        # Example features
        import pandas as pd
        price_series = pd.Series(prices)
        
        return [
            price,
            price_series.rolling(5).mean().iloc[-1],
            price_series.rolling(20).mean().iloc[-1],
            price_series.rolling(10).std().iloc[-1],
            price_series.pct_change().iloc[-1],
            market.volume,
            market.liquidity,
        ]


# Default strategy to run
# Change this to your preferred strategy class
DefaultStrategy = MomentumStrategy

