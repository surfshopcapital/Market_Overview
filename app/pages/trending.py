"""Trending Markets page."""
import streamlit as st
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import SessionLocal
from app.utils.db_utils import get_trending_markets, get_markets_for_event, get_all_categories
from app.utils.refresh import show_refresh_controls

st.title("📈 Trending Markets")
st.markdown("Markets with high 24-hour volume (sports excluded)")

# Show refresh controls
show_refresh_controls()

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

# Cached trending fetch
@st.cache_data(ttl=1800)  # Cache for 30 minutes
def get_cached_trending(search_term_val, category_val):
    _db = SessionLocal()
    try:
        return get_trending_markets(
            _db,
            search_term=search_term_val,
            category_filter=category_val
        )
    finally:
        _db.close()

def style_trends(df):
    """Apply green/red coloring to trend columns."""
    def color_trend(val):
        if isinstance(val, str):
            if val.startswith("↗"):
                return "color: #2ecc71; font-weight: bold"
            elif val.startswith("↘"):
                return "color: #e74c3c; font-weight: bold"
        return ""
    
    styled = df.style
    for col in ["30m Trend", "24h Trend"]:
        if col in df.columns:
            styled = styled.map(color_trend, subset=[col])
    return styled

# Get trending markets
try:
    df = get_cached_trending(
        search_term if search_term else None,
        category_filter if category_filter != "All" else None
    )
    
    if df.empty:
        st.info("No trending markets found")
    else:
        st.metric("Trending Markets", len(df))
        
        # Display markets with selection (hide Event Ticker and Ticker)
        display_cols = [c for c in df.columns if c not in ("Event Ticker", "Ticker")]
        event_selection = st.dataframe(
            df[display_cols],
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="trending_markets_table"
        )
        
        # Show event details for selected market
        if event_selection and event_selection.selection.rows:
            selected_idx = event_selection.selection.rows[0]
            selected_market = df.iloc[selected_idx]
            event_ticker = selected_market["Event Ticker"]
            ticker = selected_market["Ticker"]
            
            st.markdown(f"### All Markets in Event: {selected_market['Event']}")
            
            markets_df = get_markets_for_event(db, event_ticker)
            
            if not markets_df.empty:
                # Hide Ticker column for display
                display_markets = markets_df[[c for c in markets_df.columns if c != "Ticker"]]
                st.dataframe(
                    display_markets,
                    use_container_width=True,
                    hide_index=True,
                    key="trending_markets_detail"
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
