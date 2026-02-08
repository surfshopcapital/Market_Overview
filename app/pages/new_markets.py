"""New Markets page."""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import SessionLocal
from app.utils.db_utils import get_new_events, get_markets_for_event, get_all_categories

st.title("🆕 New Markets")
st.markdown("Track recently opened events and markets")

# Initialize database session
if 'db' not in st.session_state:
    st.session_state.db = SessionLocal()

db = st.session_state.db

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    
    time_window = st.selectbox(
        "Time Window",
        options=[12, 24, 48, 168],  # 12h, 24h, 48h, 7d
        format_func=lambda x: f"Last {x}h" if x < 168 else "Last 7 days",
        index=1  # Default to 24h
    )
    
    categories = get_all_categories(db)
    category_filter = st.selectbox("Category", options=categories)
    
    search_term = st.text_input("Search", placeholder="Search events...")

# Get new events
try:
    df = get_new_events(
        db, 
        window_hours=time_window,
        search_term=search_term if search_term else None,
        category_filter=category_filter if category_filter != "All" else None
    )
    
    if df.empty:
        st.info(f"No new events found in the last {time_window} hours")
    else:
        st.metric("New Events", len(df))
        
        st.markdown("### Events")
        st.markdown("*Click on a row to see markets within the event*")
        
        # Display events table with selection
        event_selection = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # Show markets for selected event
        if event_selection and event_selection.selection.rows:
            selected_idx = event_selection.selection.rows[0]
            selected_event = df.iloc[selected_idx]
            event_ticker = selected_event["Event Ticker"]
            
            st.markdown(f"### Markets in: {selected_event['Title']}")
            
            markets_df = get_markets_for_event(db, event_ticker)
            
            if not markets_df.empty:
                st.dataframe(
                    markets_df,
                    use_container_width=True,
                    hide_index=True
                )
                
                # Add link to Kalshi
                st.markdown(f"[View on Kalshi →](https://kalshi.com/events/{event_ticker})")
            else:
                st.info("No markets found for this event")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.exception(e)

# Refresh button
if st.button("🔄 Refresh Data"):
    st.rerun()
