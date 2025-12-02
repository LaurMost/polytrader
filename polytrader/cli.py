"""
Command-line interface for Polytrader.
"""

import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout

from polytrader.config import get_config
from polytrader.core.client import PolymarketClient
from polytrader.core.executor import OrderExecutor
from polytrader.data.storage import Storage
from polytrader.data.market import MarketDataFetcher
from polytrader.strategy.loader import StrategyLoader
from polytrader.strategy.runner import StrategyRunner
from polytrader.utils.url_parser import (
    format_market_summary,
    get_market_from_url,
    is_valid_polymarket_url,
)
from polytrader.utils.helpers import format_amount, format_percentage, format_pnl

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """
    Polytrader - Quantitative Trading Tool for Polymarket
    
    A CLI tool for developing and running trading strategies on Polymarket
    prediction markets.
    """
    pass


# ==================== Strategy Commands ====================


@main.command()
@click.argument("strategy_path", type=click.Path(exists=True))
@click.option("--paper/--live", default=True, help="Trading mode")
@click.option("--config", "-c", type=click.Path(), help="Config file path")
def run(strategy_path: str, paper: bool, config: Optional[str]):
    """
    Run a trading strategy.
    
    STRATEGY_PATH: Path to the strategy Python file
    
    Example:
        polytrader run strategies/my_strategy.py --paper
    """
    # Set mode
    cfg = get_config()
    cfg.set("mode", "paper" if paper else "live")
    
    if config:
        cfg.load(config)
    
    # Load strategy
    loader = StrategyLoader()
    strategy_class = loader.load(strategy_path)
    
    if not strategy_class:
        console.print("[red]Failed to load strategy[/red]")
        return
    
    strategy = strategy_class()
    
    console.print(Panel(
        f"[bold green]Starting Strategy: {strategy.name}[/bold green]\n"
        f"Mode: {'Paper' if paper else 'Live'}\n"
        f"Markets: {len(strategy.markets)}",
        title="Polytrader"
    ))
    
    # Run strategy
    runner = StrategyRunner(strategy)
    
    try:
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Strategy stopped by user[/yellow]")


# ==================== Market Commands ====================


@main.command()
@click.argument("url")
def market(url: str):
    """
    Get market details from a Polymarket URL.
    
    URL: Polymarket event or market URL
    
    Example:
        polytrader market https://polymarket.com/event/fed-decision
    """
    if not is_valid_polymarket_url(url):
        console.print("[red]Invalid Polymarket URL[/red]")
        return
    
    with console.status("Fetching market data..."):
        market_obj = get_market_from_url(url)
    
    if not market_obj:
        console.print("[red]Market not found[/red]")
        return
    
    # Display market info
    console.print(Panel(
        format_market_summary(market_obj),
        title=f"Market: {market_obj.question[:60]}...",
        border_style="blue"
    ))


@main.command()
@click.argument("url")
@click.option("--live", is_flag=True, help="Watch live price updates")
@click.option("--interval", "-i", default=5, help="Refresh interval in seconds")
def watch(url: str, live: bool, interval: int):
    """
    Watch market prices.
    
    URL: Polymarket event or market URL
    
    Example:
        polytrader watch https://polymarket.com/event/fed-decision --live
    """
    if not is_valid_polymarket_url(url):
        console.print("[red]Invalid Polymarket URL[/red]")
        return
    
    market_obj = get_market_from_url(url)
    
    if not market_obj:
        console.print("[red]Market not found[/red]")
        return
    
    if live:
        # Live WebSocket watching
        _watch_live(market_obj)
    else:
        # Periodic refresh
        _watch_polling(market_obj, interval)


def _watch_polling(market_obj, interval: int):
    """Watch market with polling."""
    client = PolymarketClient()
    
    def create_table():
        market = client.get_market_by_id(market_obj.id) or market_obj
        
        table = Table(title=market.question[:60])
        table.add_column("Outcome", style="cyan")
        table.add_column("Price", justify="right")
        table.add_column("Probability", justify="right")
        
        table.add_row(
            "YES",
            f"{market.price_yes:.4f}",
            format_percentage(market.price_yes)
        )
        table.add_row(
            "NO",
            f"{market.price_no:.4f}",
            format_percentage(market.price_no)
        )
        
        return table
    
    try:
        with Live(create_table(), refresh_per_second=1/interval, console=console) as live:
            while True:
                import time
                time.sleep(interval)
                live.update(create_table())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching[/yellow]")


def _watch_live(market_obj):
    """Watch market with WebSocket."""
    from polytrader.core.websocket import WebSocketManager
    
    ws = WebSocketManager()
    
    def on_price(update):
        if update.token_id == market_obj.token_id_yes:
            console.print(f"[green]YES: {update.price:.4f}[/green]")
        else:
            console.print(f"[red]NO: {update.price:.4f}[/red]")
    
    ws.on_price_update(on_price)
    
    async def run():
        await ws.subscribe_market([market_obj.token_id_yes, market_obj.token_id_no])
        await ws.run()
    
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching[/yellow]")


@main.command()
@click.option("--limit", "-n", default=20, help="Number of markets to show")
@click.option("--closed", is_flag=True, help="Include closed markets")
def markets(limit: int, closed: bool):
    """
    List available markets.
    
    Example:
        polytrader markets --limit 10
    """
    client = PolymarketClient()
    
    with console.status("Fetching markets..."):
        market_list = client.get_markets(closed=closed, limit=limit)
    
    table = Table(title=f"Polymarket Markets (Top {limit})")
    table.add_column("Question", style="cyan", max_width=50)
    table.add_column("YES", justify="right")
    table.add_column("Volume", justify="right")
    table.add_column("Status")
    
    for m in market_list:
        status = "[red]Closed[/red]" if m.closed else "[green]Active[/green]"
        table.add_row(
            m.question[:50] + "..." if len(m.question) > 50 else m.question,
            format_percentage(m.price_yes),
            format_amount(m.volume),
            status
        )
    
    console.print(table)


# ==================== Account Commands ====================


@main.command()
def balance():
    """
    Show account balance.
    
    Example:
        polytrader balance
    """
    config = get_config()
    executor = OrderExecutor()
    
    mode = "Paper" if config.is_paper else "Live"
    
    table = Table(title=f"Account Balance ({mode})")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")
    
    table.add_row("USDC Balance", format_amount(executor.balance))
    table.add_row("Position Value", format_amount(executor.equity - executor.balance))
    table.add_row("Total Equity", format_amount(executor.equity))
    table.add_row("Realized P&L", format_pnl(executor.realized_pnl))
    
    console.print(table)


@main.command()
def orders():
    """
    List open orders.
    
    Example:
        polytrader orders
    """
    storage = Storage()
    order_list = storage.get_orders(limit=50)
    
    if not order_list:
        console.print("[yellow]No orders found[/yellow]")
        return
    
    table = Table(title="Orders")
    table.add_column("ID", style="dim")
    table.add_column("Side")
    table.add_column("Price", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Filled", justify="right")
    table.add_column("Status")
    
    for order in order_list:
        side_color = "green" if order.side.value == "BUY" else "red"
        table.add_row(
            order.id[:12] + "...",
            f"[{side_color}]{order.side.value}[/{side_color}]",
            f"{order.price:.4f}",
            f"{order.size:.2f}",
            f"{order.filled_size:.2f}",
            order.status.value
        )
    
    console.print(table)


@main.command()
def positions():
    """
    List open positions.
    
    Example:
        polytrader positions
    """
    executor = OrderExecutor()
    pos_list = executor.get_all_positions()
    
    if not pos_list:
        console.print("[yellow]No open positions[/yellow]")
        return
    
    table = Table(title="Positions")
    table.add_column("Token", style="dim")
    table.add_column("Size", justify="right")
    table.add_column("Avg Price", justify="right")
    table.add_column("Cost Basis", justify="right")
    table.add_column("Realized P&L", justify="right")
    
    for pos in pos_list:
        table.add_row(
            pos.token_id[:20] + "...",
            f"{pos.size:.2f}",
            f"{pos.avg_entry_price:.4f}",
            format_amount(pos.cost_basis),
            format_pnl(pos.realized_pnl)
        )
    
    console.print(table)


@main.command()
@click.option("--limit", "-n", default=20, help="Number of trades to show")
def history(limit: int):
    """
    View trade history.
    
    Example:
        polytrader history --limit 50
    """
    storage = Storage()
    trades = storage.get_trades(limit=limit)
    
    if not trades:
        console.print("[yellow]No trades found[/yellow]")
        return
    
    table = Table(title=f"Trade History (Last {limit})")
    table.add_column("Time", style="dim")
    table.add_column("Side")
    table.add_column("Price", justify="right")
    table.add_column("Size", justify="right")
    table.add_column("Value", justify="right")
    table.add_column("Type")
    
    for trade in trades:
        side_color = "green" if trade.side.value == "BUY" else "red"
        trade_type = "Paper" if trade.is_paper else "Live"
        
        table.add_row(
            trade.executed_at.strftime("%Y-%m-%d %H:%M") if trade.executed_at else "",
            f"[{side_color}]{trade.side.value}[/{side_color}]",
            f"{trade.price:.4f}",
            f"{trade.size:.2f}",
            format_amount(trade.value),
            trade_type
        )
    
    console.print(table)


# ==================== Export Commands ====================


@main.command()
@click.option("--trades", "export_trades", is_flag=True, help="Export trades")
@click.option("--orders", "export_orders", is_flag=True, help="Export orders")
@click.option("--positions", "export_positions", is_flag=True, help="Export positions")
@click.option("--all", "export_all", is_flag=True, help="Export all data")
@click.option("--output", "-o", type=click.Path(), help="Output directory")
def export(export_trades: bool, export_orders: bool, export_positions: bool,
           export_all: bool, output: Optional[str]):
    """
    Export data to CSV files.
    
    Example:
        polytrader export --all --output ./exports
    """
    storage = Storage()
    
    if output:
        storage.csv_dir = Path(output)
        storage.csv_dir.mkdir(parents=True, exist_ok=True)
    
    if export_all:
        export_trades = export_orders = export_positions = True
    
    if not any([export_trades, export_orders, export_positions]):
        console.print("[yellow]Specify what to export: --trades, --orders, --positions, or --all[/yellow]")
        return
    
    if export_trades:
        path = storage.export_trades_csv()
        console.print(f"[green]Exported trades to {path}[/green]")
    
    if export_orders:
        path = storage.export_orders_csv()
        console.print(f"[green]Exported orders to {path}[/green]")
    
    if export_positions:
        path = storage.export_positions_csv()
        console.print(f"[green]Exported positions to {path}[/green]")


# ==================== Config Commands ====================


@main.command()
def config():
    """
    Show current configuration.
    
    Example:
        polytrader config
    """
    cfg = get_config()
    
    table = Table(title="Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value")
    
    table.add_row("Mode", cfg.mode)
    table.add_row("API Host", cfg.host)
    table.add_row("Chain ID", str(cfg.chain_id))
    table.add_row("Data Directory", str(cfg.data_dir))
    table.add_row("Database", str(cfg.database_path))
    table.add_row("Log Level", cfg.log_level)
    table.add_row("Private Key", "***" if cfg.private_key else "[red]Not set[/red]")
    
    console.print(table)


# ==================== Analytics Commands ====================


@main.command()
@click.option("--port", "-p", default=8501, help="Port to run dashboard on")
def dashboard(port: int):
    """
    Launch the performance dashboard.
    
    Opens a Streamlit web dashboard for monitoring strategy performance,
    viewing metrics, and analyzing statistical significance.
    
    Example:
        polytrader dashboard
        polytrader dashboard --port 8502
    """
    import subprocess
    import sys
    
    dashboard_path = Path(__file__).parent.parent / "dashboard.py"
    
    if not dashboard_path.exists():
        console.print("[red]Dashboard file not found[/red]")
        console.print(f"Expected at: {dashboard_path}")
        return
    
    console.print(Panel(
        f"[bold green]Starting Performance Dashboard[/bold green]\n\n"
        f"URL: http://localhost:{port}\n"
        f"Press Ctrl+C to stop",
        title="Polytrader Dashboard"
    ))
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            str(dashboard_path),
            "--server.port", str(port),
            "--server.headless", "true",
        ])
    except KeyboardInterrupt:
        console.print("\n[yellow]Dashboard stopped[/yellow]")
    except FileNotFoundError:
        console.print("[red]Streamlit not installed. Run: pip install streamlit[/red]")


@main.command()
@click.option("--export", "-e", is_flag=True, help="Export stats to CSV")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def stats(export: bool, as_json: bool):
    """
    Show performance statistics.
    
    Displays key performance metrics including P&L, Sharpe ratio,
    win rate, and statistical significance.
    
    Example:
        polytrader stats
        polytrader stats --export
        polytrader stats --json
    """
    from polytrader.analytics.metrics import calculate_all_metrics
    from polytrader.analytics.significance import calculate_statistical_summary
    import json as json_lib
    
    storage = Storage()
    trades = storage.get_trades(limit=10000)
    
    if not trades:
        console.print("[yellow]No trades found. Run some trades first![/yellow]")
        return
    
    # Calculate metrics
    metrics = calculate_all_metrics(trades)
    returns = metrics.get("returns")
    
    if returns is not None and not returns.empty:
        stats_data = calculate_statistical_summary(returns)
    else:
        stats_data = {}
    
    if as_json:
        # Output as JSON
        output = {
            "performance": {
                "total_pnl": metrics["total_pnl"],
                "win_rate": metrics["win_rate"],
                "sharpe_ratio": metrics["sharpe_ratio"],
                "max_drawdown_pct": metrics["max_drawdown_pct"],
                "profit_factor": metrics["profit_factor"],
                "expectancy": metrics["expectancy"],
                "num_trades": metrics["num_trades"],
            },
            "statistics": {
                "t_statistic": stats_data.get("t_statistic", 0),
                "p_value": stats_data.get("p_value", 1),
                "is_significant": stats_data.get("is_significant", False),
                "mean_ci_lower": stats_data.get("mean_ci_lower", 0),
                "mean_ci_upper": stats_data.get("mean_ci_upper", 0),
            }
        }
        console.print(json_lib.dumps(output, indent=2))
        return
    
    # Performance Metrics Table
    console.print("\n")
    perf_table = Table(title="📊 Performance Metrics")
    perf_table.add_column("Metric", style="cyan")
    perf_table.add_column("Value", justify="right")
    
    perf_table.add_row("Total P&L", format_pnl(metrics["total_pnl"]))
    perf_table.add_row("Win Rate", format_percentage(metrics["win_rate"]))
    perf_table.add_row("Wins / Losses", f"{metrics['wins']} / {metrics['losses']}")
    perf_table.add_row("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    perf_table.add_row("Max Drawdown", format_percentage(metrics["max_drawdown_pct"]))
    perf_table.add_row("Profit Factor", f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] != float('inf') else "∞")
    perf_table.add_row("Expectancy", format_pnl(metrics["expectancy"]))
    perf_table.add_row("Total Trades", str(metrics["num_trades"]))
    
    console.print(perf_table)
    
    # Statistical Significance Table
    if stats_data:
        console.print("\n")
        sig_table = Table(title="🔬 Statistical Significance")
        sig_table.add_column("Metric", style="cyan")
        sig_table.add_column("Value", justify="right")
        
        p_value = stats_data.get("p_value", 1)
        is_sig = stats_data.get("is_significant", False)
        
        sig_table.add_row("T-Statistic", f"{stats_data.get('t_statistic', 0):.3f}")
        sig_table.add_row("P-Value", f"{p_value:.4f}")
        sig_table.add_row(
            "Significance",
            "[green]✓ Significant (p < 0.05)[/green]" if is_sig else "[red]✗ Not Significant[/red]"
        )
        sig_table.add_row(
            "Mean Return 95% CI",
            f"[{stats_data.get('mean_ci_lower', 0):.4f}, {stats_data.get('mean_ci_upper', 0):.4f}]"
        )
        sig_table.add_row("Sample Size", str(stats_data.get("sample_size", 0)))
        sig_table.add_row(
            "Required Trades",
            f"~{stats_data.get('required_trades', 0)} ({stats_data.get('data_sufficiency_pct', 0):.0f}% complete)"
        )
        
        console.print(sig_table)
        
        # Interpretation
        console.print("\n")
        if is_sig:
            console.print(Panel(
                "[bold green]✅ Your strategy shows statistically significant alpha![/bold green]\n\n"
                f"With a p-value of {p_value:.4f}, there is strong evidence that your "
                "returns are not due to random chance.",
                title="Interpretation",
                border_style="green"
            ))
        else:
            console.print(Panel(
                "[bold yellow]⚠️ Not enough evidence of alpha yet[/bold yellow]\n\n"
                f"With a p-value of {p_value:.4f}, we cannot conclude that your strategy "
                "generates consistent returns. Consider:\n"
                "• Running more trades to increase sample size\n"
                "• Reviewing strategy logic for improvements\n"
                "• Checking if market conditions have changed",
                title="Interpretation",
                border_style="yellow"
            ))
    
    # Export if requested
    if export:
        import pandas as pd
        
        export_data = {
            "metric": list(metrics.keys()),
            "value": [
                str(v) if not isinstance(v, (pd.DataFrame, pd.Series, list)) else "..."
                for v in metrics.values()
            ]
        }
        df = pd.DataFrame(export_data)
        
        export_path = Path("stats_export.csv")
        df.to_csv(export_path, index=False)
        console.print(f"\n[green]Stats exported to {export_path}[/green]")


if __name__ == "__main__":
    main()

