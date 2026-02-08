"""Mentions page - shows events with mention markets, drill-down to markets."""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import SessionLocal
from app.utils.db_utils import get_mention_events, get_mention_markets_for_event
from app.utils.refresh import show_refresh_controls

st.title("💬 Mention Markets")
st.markdown("Events with mention markets, sorted by soonest expiration")

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
    
    search_term = st.text_input("Search", placeholder="Search events...")

try:
    df = get_mention_events(
        db,
        new_window_hours=new_window,
        search_term=search_term if search_term else None
    )
    
    if df.empty:
        st.info("No mention events found")
    else:
        st.metric("Mention Events", len(df))
        
        st.markdown("### Events (click row to see mention markets)")
        
        event_selection = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="mentions_events_table"
        )
        
        # Show markets drill-down for selected event
        if event_selection and event_selection.selection.rows:
            selected_idx = event_selection.selection.rows[0]
            selected_event = df.iloc[selected_idx]
            event_ticker = selected_event["Event Ticker"]
            
            st.markdown(f"### Mention Markets in: {selected_event['Title']}")
            
            markets_df = get_mention_markets_for_event(db, event_ticker)
            
            if not markets_df.empty:
                # Hide Ticker for display
                display_cols = [c for c in markets_df.columns if c != "Ticker"]
                st.dataframe(
                    markets_df[display_cols],
                    use_container_width=True,
                    hide_index=True,
                    key="mentions_markets_detail"
                )
                
                st.markdown(f"[View Event on Kalshi →](https://kalshi.com/events/{event_ticker})")
            else:
                st.info("No mention markets found for this event")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.exception(e)
