"""Trending Markets page."""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import SessionLocal
from app.utils.db_utils import get_trending_markets, get_markets_for_event, get_all_categories

st.title("📈 Trending Markets")
st.markdown("Markets with high 24-hour volume")

# Initialize database session
if 'db' not in st.session_state:
    st.session_state.db = SessionLocal()

db = st.session_state.db

# Sidebar filters
with st.sidebar:
    st.header("Filters")
    
    categories = get_all_categories(db)
    category_filter = st.selectbox("Category", options=categories)
    
    search_term = st.text_input("Search", placeholder="Search markets...")

# Get trending markets
try:
    df = get_trending_markets(
        db,
        search_term=search_term if search_term else None,
        category_filter=category_filter if category_filter != "All" else None
    )
    
    if df.empty:
        st.info("No trending markets found")
    else:
        st.metric("Trending Markets", len(df))
        
        # Display markets with selection
        st.dataframe(
            df[[col for col in df.columns if col != "Event Ticker"]],  # Hide Event Ticker column
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
            
            st.markdown(f"### All Markets in Event: {selected_market['Event']}")
            
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

# Refresh button
if st.button("🔄 Refresh Data"):
    st.rerun()
