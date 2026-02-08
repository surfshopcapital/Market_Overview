"""New Markets page."""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import SessionLocal
from app.utils.db_utils import get_new_events, get_markets_for_event, get_all_categories, get_new_counts
from app.utils.refresh import show_refresh_controls

st.title("🆕 New Markets")
st.markdown("Track recently opened events and markets (sports excluded)")

# Show refresh controls
show_refresh_controls()

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
    
    st.markdown("---")
    st.header("Exclude Categories")
    exclude_crypto = st.checkbox("Exclude Crypto", value=True)
    exclude_climate = st.checkbox("Exclude Climate / Weather", value=True)

# Build exclusion list
exclude_cats = []
if exclude_crypto:
    exclude_cats.append("Crypto")
if exclude_climate:
    exclude_cats.extend(["Climate", "Weather"])

# Get new events
try:
    df = get_new_events(
        db, 
        window_hours=time_window,
        search_term=search_term if search_term else None,
        category_filter=category_filter if category_filter != "All" else None,
        exclude_categories=exclude_cats if exclude_cats else None
    )
    
    # Get 24h counts
    counts_24h = get_new_counts(db, window_hours=24)
    
    # Show metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(f"New Events ({time_window}h)", len(df))
    with col2:
        st.metric("New Events (24h)", counts_24h["new_events"])
    with col3:
        st.metric("New Markets (24h)", counts_24h["new_markets"])
    
    if df.empty:
        st.info(f"No new events found in the last {time_window} hours")
    else:
        st.markdown("### Events")
        st.markdown("*Click on a row to see markets within the event*")
        
        # Display events table with selection
        event_selection = st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="new_events_table"
        )
        
        # Show markets for selected event
        if event_selection and event_selection.selection.rows:
            selected_idx = event_selection.selection.rows[0]
            selected_event = df.iloc[selected_idx]
            event_ticker = selected_event["Event Ticker"]
            
            st.markdown(f"### Markets in: {selected_event['Title']}")
            
            markets_df = get_markets_for_event(db, event_ticker)
            
            if not markets_df.empty:
                # Hide Ticker column for display
                display_markets = markets_df[[c for c in markets_df.columns if c != "Ticker"]]
                st.dataframe(
                    display_markets,
                    use_container_width=True,
                    hide_index=True,
                    key="new_markets_detail"
                )
                
                # Add link to Kalshi
                st.markdown(f"[View on Kalshi →](https://kalshi.com/events/{event_ticker})")
            else:
                st.info("No markets found for this event")

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.exception(e)
