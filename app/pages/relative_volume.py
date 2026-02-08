"""Relative Volume page."""
import streamlit as st
import sys
import os
import plotly.express as px

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import SessionLocal
from app.utils.db_utils import (
    get_relative_volume_events, get_markets_for_event, get_daily_volume_history
)
from app.utils.refresh import show_refresh_controls

st.title("🔥 Relative Volume")
st.markdown("Events with unusually high volume vs. baseline (sports excluded)")

# Show refresh controls
show_refresh_controls()

# Initialize database session
if 'db' not in st.session_state:
    st.session_state.db = SessionLocal()

db = st.session_state.db

# Sidebar filters
with st.sidebar:
    st.header("Settings")
    
    period = st.selectbox(
        "Current Period",
        options=[6, 12, 24, 48],
        format_func=lambda x: f"Last {x} hours",
        index=2  # Default to 24h
    )
    
    baseline = st.selectbox(
        "Baseline Window",
        options=[7, 14, 30],
        format_func=lambda x: f"{x} days",
        index=0  # Default to 7 days
    )
    
    search_term = st.text_input("Search", placeholder="Search events...")

# Get relative volume events with caching
@st.cache_data(ttl=1800)  # Cache for 30 minutes
def get_cached_relative_volume(period_hours: int, baseline_days: int, search_term: str = None):
    """Cached wrapper for relative volume query."""
    db = SessionLocal()
    try:
        return get_relative_volume_events(
            db,
            period_hours=period_hours,
            baseline_days=baseline_days,
            search_term=search_term
        )
    finally:
        db.close()

try:
    df = get_cached_relative_volume(
        period_hours=period,
        baseline_days=baseline,
        search_term=search_term if search_term else None
    )
    
    if df.empty:
        st.info("No events with significant relative volume found")
        st.markdown("""
        **Note:** Events need:
        - At least 1.5x baseline volume
        - Minimum baseline of 100 contracts
        - Non-sports category
        """)
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Standout Events", len(df))
        with col2:
            avg_relative = df["Relative"].mean()
            st.metric("Avg Relative", f"{avg_relative:.1f}x")
        with col3:
            max_relative = df["Relative"].max()
            st.metric("Max Relative", f"{max_relative:.1f}x")
        
        st.markdown("### Standout Events")
        st.markdown(f"*Current period: Last {period}h | Baseline: {baseline} days*")
        
        # Display events with selection
        event_selection = st.dataframe(
            df[[col for col in df.columns if col != "Event Ticker"]],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # Show details for selected event
        if event_selection and event_selection.selection.rows:
            selected_idx = event_selection.selection.rows[0]
            selected_event = df.iloc[selected_idx]
            event_ticker = selected_event["Event Ticker"]
            
            st.markdown("---")
            st.markdown(f"### Details: {selected_event['Title']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Volume Comparison")
                st.metric("Current Period Volume", f"{selected_event['Current Volume']:,}")
                st.metric("Baseline Daily Avg", f"{selected_event['Baseline Avg']:,}")
                st.metric("Relative Multiple", f"{selected_event['Relative']}x")
            
            with col2:
                st.markdown("#### Volume History")
                history_df = get_daily_volume_history(db, event_ticker, days=30)
                
                if not history_df.empty:
                    fig = px.line(
                        history_df,
                        x="Date",
                        y="Volume",
                        title=f"Daily Volume (Last 30 Days)",
                        labels={"Volume": "Contracts", "Date": "Date"}
                    )
                    fig.update_traces(line_color='#3498db')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No historical data available")
            
            st.markdown("#### Markets in Event")
            markets_df = get_markets_for_event(db, event_ticker)
            
            if not markets_df.empty:
                st.dataframe(
                    markets_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                st.markdown(f"[View on Kalshi →](https://kalshi.com/events/{event_ticker})")
            else:
                st.info("No markets found for this event")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.exception(e)
