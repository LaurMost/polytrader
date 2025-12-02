"""
Polytrader Performance Dashboard.

A Streamlit-based web dashboard for monitoring trading strategy performance,
calculating statistical significance, and visualizing results.

Run with:
    streamlit run dashboard.py
    
Or via CLI:
    polytrader dashboard
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import numpy as np

# Add polytrader to path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from polytrader.data.storage import Storage
from polytrader.data.models import Trade, OrderSide
from polytrader.analytics.metrics import calculate_all_metrics, build_equity_curve
from polytrader.analytics.significance import calculate_statistical_summary


# Page configuration
st.set_page_config(
    page_title="Polytrader Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }
    .positive { color: #00c853; }
    .negative { color: #ff5252; }
    .neutral { color: #ffc107; }
</style>
""", unsafe_allow_html=True)


def load_trades() -> list[Trade]:
    """Load trades from storage."""
    try:
        storage = Storage()
        return storage.get_trades(limit=10000)
    except Exception as e:
        st.error(f"Error loading trades: {e}")
        return []


def create_equity_chart(equity_df: pd.DataFrame) -> go.Figure:
    """Create interactive equity curve chart."""
    if equity_df.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="No trade data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        return fig
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=equity_df["date"],
        y=equity_df["equity"],
        mode="lines",
        name="Equity",
        line=dict(color="#00c853", width=2),
        fill="tozeroy",
        fillcolor="rgba(0, 200, 83, 0.1)",
    ))
    
    fig.update_layout(
        title="Equity Curve",
        xaxis_title="Date",
        yaxis_title="Equity ($)",
        template="plotly_dark",
        height=400,
        hovermode="x unified",
    )
    
    return fig


def create_pnl_distribution(pnl_per_trade: list) -> go.Figure:
    """Create P&L distribution histogram."""
    if not pnl_per_trade:
        fig = go.Figure()
        fig.add_annotation(
            text="No P&L data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=20)
        )
        return fig
    
    fig = go.Figure()
    
    # Color bars based on positive/negative
    colors = ["#00c853" if p > 0 else "#ff5252" for p in pnl_per_trade]
    
    fig.add_trace(go.Histogram(
        x=pnl_per_trade,
        nbinsx=30,
        marker_color="#4fc3f7",
        opacity=0.7,
        name="P&L Distribution",
    ))
    
    # Add mean line
    mean_pnl = np.mean(pnl_per_trade)
    fig.add_vline(
        x=mean_pnl,
        line_dash="dash",
        line_color="#ffc107",
        annotation_text=f"Mean: ${mean_pnl:.2f}",
    )
    
    fig.update_layout(
        title="P&L Distribution per Trade",
        xaxis_title="P&L ($)",
        yaxis_title="Frequency",
        template="plotly_dark",
        height=350,
    )
    
    return fig


def create_drawdown_chart(equity_df: pd.DataFrame) -> go.Figure:
    """Create drawdown chart."""
    if equity_df.empty:
        fig = go.Figure()
        return fig
    
    equity = equity_df["equity"]
    running_max = equity.expanding().max()
    drawdown_pct = (equity - running_max) / running_max * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=equity_df["date"],
        y=drawdown_pct,
        mode="lines",
        name="Drawdown",
        line=dict(color="#ff5252", width=2),
        fill="tozeroy",
        fillcolor="rgba(255, 82, 82, 0.2)",
    ))
    
    fig.update_layout(
        title="Drawdown Over Time",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        template="plotly_dark",
        height=300,
    )
    
    return fig


def create_win_loss_chart(wins: int, losses: int) -> go.Figure:
    """Create win/loss pie chart."""
    if wins == 0 and losses == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No trades",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
        )
        return fig
    
    fig = go.Figure(data=[go.Pie(
        labels=["Wins", "Losses"],
        values=[wins, losses],
        hole=0.4,
        marker_colors=["#00c853", "#ff5252"],
    )])
    
    fig.update_layout(
        title="Win/Loss Ratio",
        template="plotly_dark",
        height=300,
    )
    
    return fig


def create_cumulative_returns_chart(returns: pd.Series) -> go.Figure:
    """Create cumulative returns chart."""
    if returns.empty:
        fig = go.Figure()
        return fig
    
    cumulative = (1 + returns).cumprod() - 1
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=list(range(len(cumulative))),
        y=cumulative * 100,
        mode="lines",
        name="Cumulative Return",
        line=dict(color="#4fc3f7", width=2),
    ))
    
    fig.update_layout(
        title="Cumulative Returns",
        xaxis_title="Trade #",
        yaxis_title="Cumulative Return (%)",
        template="plotly_dark",
        height=300,
    )
    
    return fig


def main():
    """Main dashboard application."""
    
    # Header
    st.title("📈 Polytrader Performance Dashboard")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Filters")
        
        # Date range filter
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                value=datetime.now() - timedelta(days=30)
            )
        with col2:
            end_date = st.date_input(
                "End Date",
                value=datetime.now()
            )
        
        # Refresh button
        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.header("📊 Quick Stats")
    
    # Load data
    trades = load_trades()
    
    # Calculate metrics
    if trades:
        metrics = calculate_all_metrics(trades)
        returns = metrics.get("returns", pd.Series())
        stats = calculate_statistical_summary(returns) if not returns.empty else {}
    else:
        metrics = {
            "total_pnl": 0, "win_rate": 0, "sharpe_ratio": 0,
            "max_drawdown_pct": 0, "num_trades": 0, "wins": 0, "losses": 0,
            "profit_factor": 0, "expectancy": 0, "equity_df": pd.DataFrame(),
            "returns": pd.Series(), "pnl_per_trade": [],
        }
        stats = {}
    
    # Sidebar stats
    with st.sidebar:
        st.metric("Total Trades", metrics["num_trades"])
        st.metric("Win Rate", f"{metrics['win_rate']:.1%}")
        st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
    
    # Main content - Key Metrics Row
    st.subheader("📊 Key Performance Metrics")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        pnl_color = "normal" if metrics["total_pnl"] >= 0 else "inverse"
        st.metric(
            "Total P&L",
            f"${metrics['total_pnl']:,.2f}",
            delta=f"{metrics['total_pnl']:+,.2f}",
            delta_color=pnl_color,
        )
    
    with col2:
        st.metric(
            "Win Rate",
            f"{metrics['win_rate']:.1%}",
            delta=f"{metrics['wins']}W / {metrics['losses']}L",
        )
    
    with col3:
        sharpe_color = "normal" if metrics["sharpe_ratio"] >= 1 else "off"
        st.metric(
            "Sharpe Ratio",
            f"{metrics['sharpe_ratio']:.2f}",
            delta="Good" if metrics["sharpe_ratio"] >= 1 else "Needs Work",
            delta_color=sharpe_color,
        )
    
    with col4:
        st.metric(
            "Max Drawdown",
            f"{metrics['max_drawdown_pct']:.1%}",
            delta=f"{metrics['max_drawdown_pct']:.1%}",
            delta_color="inverse",
        )
    
    with col5:
        st.metric(
            "Profit Factor",
            f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] != float('inf') else "∞",
            delta="Profitable" if metrics['profit_factor'] > 1 else "Unprofitable",
            delta_color="normal" if metrics['profit_factor'] > 1 else "inverse",
        )
    
    st.markdown("---")
    
    # Charts Row 1
    col1, col2 = st.columns([2, 1])
    
    with col1:
        equity_chart = create_equity_chart(metrics["equity_df"])
        st.plotly_chart(equity_chart, use_container_width=True)
    
    with col2:
        win_loss_chart = create_win_loss_chart(metrics["wins"], metrics["losses"])
        st.plotly_chart(win_loss_chart, use_container_width=True)
    
    # Charts Row 2
    col1, col2 = st.columns(2)
    
    with col1:
        pnl_dist_chart = create_pnl_distribution(metrics["pnl_per_trade"])
        st.plotly_chart(pnl_dist_chart, use_container_width=True)
    
    with col2:
        drawdown_chart = create_drawdown_chart(metrics["equity_df"])
        st.plotly_chart(drawdown_chart, use_container_width=True)
    
    st.markdown("---")
    
    # Statistical Significance Section
    st.subheader("🔬 Statistical Significance Analysis")
    
    if stats:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### T-Test Results")
            
            p_value = stats.get("p_value", 1.0)
            t_stat = stats.get("t_statistic", 0.0)
            
            if p_value < 0.05:
                st.success(f"✅ **Statistically Significant** (p = {p_value:.4f})")
            elif p_value < 0.10:
                st.warning(f"⚠️ **Marginally Significant** (p = {p_value:.4f})")
            else:
                st.error(f"❌ **Not Significant** (p = {p_value:.4f})")
            
            st.write(f"**T-Statistic:** {t_stat:.3f}")
            st.write(f"**Sample Size:** {stats.get('sample_size', 0)} trades")
        
        with col2:
            st.markdown("### Confidence Intervals")
            
            mean_lower = stats.get("mean_ci_lower", 0)
            mean_upper = stats.get("mean_ci_upper", 0)
            sharpe_lower = stats.get("sharpe_ci_lower", 0)
            sharpe_upper = stats.get("sharpe_ci_upper", 0)
            
            st.write(f"**Mean Return (95% CI):**")
            st.write(f"  [{mean_lower:.4f}, {mean_upper:.4f}]")
            
            st.write(f"**Sharpe Ratio (95% CI):**")
            st.write(f"  [{sharpe_lower:.2f}, {sharpe_upper:.2f}]")
            
            # Is zero excluded from CI?
            if mean_lower > 0:
                st.success("✅ Zero excluded from mean CI - Evidence of positive alpha")
            elif mean_upper < 0:
                st.error("❌ Negative returns indicated")
            else:
                st.warning("⚠️ Zero included in CI - More data needed")
        
        with col3:
            st.markdown("### Data Sufficiency")
            
            required = stats.get("required_trades", 0)
            current = stats.get("sample_size", 0)
            sufficiency = stats.get("data_sufficiency_pct", 0)
            
            st.progress(min(sufficiency / 100, 1.0))
            st.write(f"**Progress:** {sufficiency:.1f}%")
            st.write(f"**Current:** {current} trades")
            st.write(f"**Required:** ~{required} trades")
            
            if sufficiency >= 100:
                st.success("✅ Sufficient data for conclusions")
            else:
                st.info(f"ℹ️ Need ~{required - current} more trades")
    else:
        st.info("No trade data available for statistical analysis. Run some trades first!")
    
    st.markdown("---")
    
    # Additional Metrics Table
    st.subheader("📋 Detailed Metrics")
    
    metrics_table = {
        "Metric": [
            "Total P&L",
            "Gross Profit",
            "Gross Loss",
            "Win Rate",
            "Average Win",
            "Average Loss",
            "Win/Loss Ratio",
            "Profit Factor",
            "Expectancy",
            "Sharpe Ratio",
            "Max Drawdown",
            "Total Trades",
        ],
        "Value": [
            f"${metrics['total_pnl']:,.2f}",
            f"${metrics.get('gross_profit', 0):,.2f}",
            f"${metrics.get('gross_loss', 0):,.2f}",
            f"{metrics['win_rate']:.2%}",
            f"${metrics.get('avg_win', 0):,.2f}",
            f"${metrics.get('avg_loss', 0):,.2f}",
            f"{metrics.get('win_loss_ratio', 0):.2f}",
            f"{metrics['profit_factor']:.2f}" if metrics['profit_factor'] != float('inf') else "∞",
            f"${metrics.get('expectancy', 0):,.2f}",
            f"{metrics['sharpe_ratio']:.2f}",
            f"{metrics['max_drawdown_pct']:.2%}",
            f"{metrics['num_trades']}",
        ],
    }
    
    st.dataframe(
        pd.DataFrame(metrics_table),
        use_container_width=True,
        hide_index=True,
    )
    
    # Export section
    st.markdown("---")
    st.subheader("📥 Export Data")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("Export Trades CSV"):
            storage = Storage()
            filepath = storage.export_trades_csv()
            st.success(f"Exported to {filepath}")
    
    with col2:
        if st.button("Export Metrics CSV"):
            metrics_df = pd.DataFrame([{
                k: v for k, v in metrics.items() 
                if not isinstance(v, (pd.DataFrame, pd.Series, list))
            }])
            metrics_df.to_csv("metrics_export.csv", index=False)
            st.success("Exported to metrics_export.csv")
    
    with col3:
        if st.button("Export Full Report"):
            st.info("Full report export coming soon!")


if __name__ == "__main__":
    main()

