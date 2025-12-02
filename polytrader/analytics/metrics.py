"""
Performance metrics for trading strategies.

Provides functions to calculate P&L, Sharpe ratio, drawdown, win rate, etc.
"""

from datetime import datetime
from typing import Optional, Union

import numpy as np
import pandas as pd

from polytrader.data.models import Trade, OrderSide


def calculate_pnl(trades: list[Trade]) -> dict:
    """
    Calculate P&L metrics from a list of trades.
    
    Args:
        trades: List of Trade objects
        
    Returns:
        Dict with total_pnl, realized_pnl, gross_profit, gross_loss
    """
    if not trades:
        return {
            "total_pnl": 0.0,
            "realized_pnl": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "num_trades": 0,
        }
    
    # For prediction markets, profit comes from buying low and the market
    # resolving in your favor, or selling high before resolution
    # Simplified: track buy/sell pairs
    
    pnl_values = []
    gross_profit = 0.0
    gross_loss = 0.0
    
    # Group trades by token_id to match buys with sells
    trades_by_token: dict[str, list[Trade]] = {}
    for trade in trades:
        if trade.token_id not in trades_by_token:
            trades_by_token[trade.token_id] = []
        trades_by_token[trade.token_id].append(trade)
    
    for token_id, token_trades in trades_by_token.items():
        buys = [t for t in token_trades if t.side == OrderSide.BUY]
        sells = [t for t in token_trades if t.side == OrderSide.SELL]
        
        # Simple FIFO matching
        buy_idx = 0
        for sell in sells:
            if buy_idx < len(buys):
                buy = buys[buy_idx]
                # P&L = (sell_price - buy_price) * size
                trade_pnl = (sell.price - buy.price) * min(sell.size, buy.size)
                pnl_values.append(trade_pnl)
                
                if trade_pnl > 0:
                    gross_profit += trade_pnl
                else:
                    gross_loss += abs(trade_pnl)
                
                buy_idx += 1
    
    total_pnl = sum(pnl_values)
    
    return {
        "total_pnl": total_pnl,
        "realized_pnl": total_pnl,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "num_trades": len(trades),
        "pnl_per_trade": pnl_values,
    }


def calculate_returns(
    trades: list[Trade],
    starting_balance: float = 10000.0,
) -> pd.Series:
    """
    Calculate return series from trades.
    
    Args:
        trades: List of Trade objects
        starting_balance: Initial account balance
        
    Returns:
        Pandas Series of returns
    """
    if not trades:
        return pd.Series(dtype=float)
    
    # Build equity curve first
    equity_df = build_equity_curve(trades, starting_balance)
    
    if equity_df.empty:
        return pd.Series(dtype=float)
    
    # Calculate returns
    returns = equity_df["equity"].pct_change().dropna()
    
    return returns


def calculate_sharpe(
    returns: Union[pd.Series, list],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Calculate annualized Sharpe ratio.
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Trading periods per year (252 for daily)
        
    Returns:
        Sharpe ratio
    """
    if isinstance(returns, list):
        returns = pd.Series(returns)
    
    if returns.empty or len(returns) < 2:
        return 0.0
    
    excess_returns = returns - (risk_free_rate / periods_per_year)
    
    mean_return = excess_returns.mean()
    std_return = excess_returns.std()
    
    if std_return == 0 or np.isnan(std_return):
        return 0.0
    
    sharpe = (mean_return / std_return) * np.sqrt(periods_per_year)
    
    return float(sharpe)


def calculate_sortino(
    returns: Union[pd.Series, list],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> float:
    """
    Calculate annualized Sortino ratio (uses downside deviation).
    
    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Trading periods per year
        
    Returns:
        Sortino ratio
    """
    if isinstance(returns, list):
        returns = pd.Series(returns)
    
    if returns.empty or len(returns) < 2:
        return 0.0
    
    excess_returns = returns - (risk_free_rate / periods_per_year)
    
    mean_return = excess_returns.mean()
    
    # Downside deviation (only negative returns)
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0:
        return float("inf") if mean_return > 0 else 0.0
    
    downside_std = downside_returns.std()
    
    if downside_std == 0 or np.isnan(downside_std):
        return 0.0
    
    sortino = (mean_return / downside_std) * np.sqrt(periods_per_year)
    
    return float(sortino)


def calculate_max_drawdown(equity_curve: Union[pd.Series, pd.DataFrame]) -> dict:
    """
    Calculate maximum drawdown from equity curve.
    
    Args:
        equity_curve: Series or DataFrame with 'equity' column
        
    Returns:
        Dict with max_drawdown, max_drawdown_pct, drawdown_duration
    """
    if isinstance(equity_curve, pd.DataFrame):
        if "equity" in equity_curve.columns:
            equity = equity_curve["equity"]
        else:
            equity = equity_curve.iloc[:, 0]
    else:
        equity = equity_curve
    
    if equity.empty or len(equity) < 2:
        return {
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "drawdown_duration": 0,
        }
    
    # Calculate running maximum
    running_max = equity.expanding().max()
    
    # Calculate drawdown
    drawdown = equity - running_max
    drawdown_pct = drawdown / running_max
    
    # Find maximum drawdown
    max_dd = drawdown.min()
    max_dd_pct = drawdown_pct.min()
    
    # Calculate drawdown duration (periods from peak to recovery)
    in_drawdown = drawdown < 0
    
    # Find longest consecutive drawdown period
    drawdown_periods = []
    current_period = 0
    
    for is_dd in in_drawdown:
        if is_dd:
            current_period += 1
        else:
            if current_period > 0:
                drawdown_periods.append(current_period)
            current_period = 0
    
    if current_period > 0:
        drawdown_periods.append(current_period)
    
    max_duration = max(drawdown_periods) if drawdown_periods else 0
    
    return {
        "max_drawdown": float(max_dd),
        "max_drawdown_pct": float(max_dd_pct),
        "drawdown_duration": max_duration,
    }


def calculate_win_rate(trades: list[Trade]) -> dict:
    """
    Calculate win rate and related metrics.
    
    Args:
        trades: List of Trade objects
        
    Returns:
        Dict with win_rate, wins, losses, avg_win, avg_loss
    """
    pnl_data = calculate_pnl(trades)
    pnl_per_trade = pnl_data.get("pnl_per_trade", [])
    
    if not pnl_per_trade:
        return {
            "win_rate": 0.0,
            "wins": 0,
            "losses": 0,
            "avg_win": 0.0,
            "avg_loss": 0.0,
            "win_loss_ratio": 0.0,
        }
    
    wins = [p for p in pnl_per_trade if p > 0]
    losses = [p for p in pnl_per_trade if p < 0]
    
    num_wins = len(wins)
    num_losses = len(losses)
    total = num_wins + num_losses
    
    win_rate = num_wins / total if total > 0 else 0.0
    avg_win = np.mean(wins) if wins else 0.0
    avg_loss = np.mean(losses) if losses else 0.0
    
    win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else float("inf")
    
    return {
        "win_rate": win_rate,
        "wins": num_wins,
        "losses": num_losses,
        "avg_win": float(avg_win),
        "avg_loss": float(avg_loss),
        "win_loss_ratio": float(win_loss_ratio) if win_loss_ratio != float("inf") else 0.0,
    }


def calculate_profit_factor(trades: list[Trade]) -> float:
    """
    Calculate profit factor (gross profit / gross loss).
    
    Args:
        trades: List of Trade objects
        
    Returns:
        Profit factor (>1 is profitable)
    """
    pnl_data = calculate_pnl(trades)
    
    gross_profit = pnl_data["gross_profit"]
    gross_loss = pnl_data["gross_loss"]
    
    if gross_loss == 0:
        return float("inf") if gross_profit > 0 else 0.0
    
    return gross_profit / gross_loss


def calculate_expectancy(trades: list[Trade]) -> float:
    """
    Calculate expected value per trade.
    
    Expectancy = (Win Rate * Avg Win) - (Loss Rate * Avg Loss)
    
    Args:
        trades: List of Trade objects
        
    Returns:
        Expected value per trade
    """
    win_data = calculate_win_rate(trades)
    
    win_rate = win_data["win_rate"]
    loss_rate = 1 - win_rate
    avg_win = win_data["avg_win"]
    avg_loss = abs(win_data["avg_loss"])
    
    expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
    
    return expectancy


def build_equity_curve(
    trades: list[Trade],
    starting_balance: float = 10000.0,
) -> pd.DataFrame:
    """
    Build equity curve from trades.
    
    Args:
        trades: List of Trade objects
        starting_balance: Initial account balance
        
    Returns:
        DataFrame with date and equity columns
    """
    if not trades:
        return pd.DataFrame(columns=["date", "equity"])
    
    # Sort trades by execution time
    sorted_trades = sorted(
        trades,
        key=lambda t: t.executed_at if t.executed_at else datetime.min
    )
    
    equity_points = []
    balance = starting_balance
    
    for trade in sorted_trades:
        # Simplified: each trade adjusts balance
        if trade.side == OrderSide.BUY:
            balance -= trade.price * trade.size
        else:
            balance += trade.price * trade.size
        
        equity_points.append({
            "date": trade.executed_at or datetime.now(),
            "equity": balance,
        })
    
    df = pd.DataFrame(equity_points)
    
    if not df.empty:
        df = df.sort_values("date").reset_index(drop=True)
    
    return df


def calculate_all_metrics(
    trades: list[Trade],
    starting_balance: float = 10000.0,
) -> dict:
    """
    Calculate all performance metrics.
    
    Args:
        trades: List of Trade objects
        starting_balance: Initial account balance
        
    Returns:
        Dict with all metrics
    """
    # P&L metrics
    pnl_data = calculate_pnl(trades)
    
    # Win rate metrics
    win_data = calculate_win_rate(trades)
    
    # Build equity curve
    equity_df = build_equity_curve(trades, starting_balance)
    
    # Calculate returns
    returns = calculate_returns(trades, starting_balance)
    
    # Risk metrics
    sharpe = calculate_sharpe(returns)
    sortino = calculate_sortino(returns)
    drawdown_data = calculate_max_drawdown(equity_df)
    
    # Other metrics
    profit_factor = calculate_profit_factor(trades)
    expectancy = calculate_expectancy(trades)
    
    return {
        # P&L
        "total_pnl": pnl_data["total_pnl"],
        "gross_profit": pnl_data["gross_profit"],
        "gross_loss": pnl_data["gross_loss"],
        "num_trades": pnl_data["num_trades"],
        
        # Win rate
        "win_rate": win_data["win_rate"],
        "wins": win_data["wins"],
        "losses": win_data["losses"],
        "avg_win": win_data["avg_win"],
        "avg_loss": win_data["avg_loss"],
        "win_loss_ratio": win_data["win_loss_ratio"],
        
        # Risk metrics
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "max_drawdown": drawdown_data["max_drawdown"],
        "max_drawdown_pct": drawdown_data["max_drawdown_pct"],
        "drawdown_duration": drawdown_data["drawdown_duration"],
        
        # Other
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        
        # Data
        "equity_df": equity_df,
        "returns": returns,
        "pnl_per_trade": pnl_data.get("pnl_per_trade", []),
    }

