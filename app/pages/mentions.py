"""Mentions Markets page."""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import SessionLocal
from app.utils.db_utils import get_mention_markets, get_markets_for_event
from app.utils.refresh import show_refresh_controls

st.title("💬 Mention Markets")
st.markdown("Markets about mentions, sorted by expiration time")

# Show refresh controls
show_refresh_controls()

# Initialize database session
if 'db' not in st.session_state:
    st.session_state.db = SessionLocal()

db = st.session_state.db

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    
    new_window = st.selectbox(
        "'New' Threshold",
        options=[6, 12, 24, 48],
        format_func=lambda x: f"Last {x} hours",
        index=2  # Default to 24h
    )
    
    search_term = st.text_input("Search", placeholder="Search markets...")

# Get mention markets
try:
    df = get_mention_markets(
        db,
        new_window_hours=new_window,
        search_term=search_term if search_term else None
    )
    
    if df.empty:
        st.info("No mention markets found")
    else:
        st.metric("Mention Markets", len(df))
        new_count = (df["New"] == "🆕").sum()
        if new_count > 0:
            st.metric(f"New (within {new_window}h)", new_count)
        
        # Display markets with color coding
        st.markdown("### Markets (🆕 = new)")
        
        # Use conditional formatting for new markets
        styled_df = df.style.apply(
            lambda row: ['background-color: #fff3cd' if row['New'] == '🆕' else '' for _ in row],
            axis=1
        )
        
        st.dataframe(
            df[[col for col in df.columns if col != "Event Ticker"]],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # Show event details for selected market
        event_selection = st.dataframe(
            df[[col for col in df.columns if col != "Event Ticker"]],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        if event_selection and event_selection.selection.rows:
            selected_idx = event_selection.selection.rows[0]
            selected_market = df.iloc[selected_idx]
            event_ticker = selected_market["Event Ticker"]
            ticker = selected_market["Ticker"]
            
            st.markdown(f"### Related Markets in Event: {selected_market['Event']}")
            
            markets_df = get_markets_for_event(db, event_ticker)
            
            if not markets_df.empty:
                st.dataframe(
                    markets_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Add links
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"[View Market on Kalshi →](https://kalshi.com/markets/{ticker})")
                with col2:
                    st.markdown(f"[View Event on Kalshi →](https://kalshi.com/events/{event_ticker})")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.exception(e)
