"""Refresh utility for Streamlit pages."""
from datetime import datetime
import streamlit as st
import pytz
from config import settings

def show_refresh_controls():
    """Display refresh controls and timestamp."""
    tz = pytz.timezone(settings.TIMEZONE)
    
    # Get last refresh time from session state
    if 'last_refresh' not in st.session_state:
        st.session_state.last_refresh = datetime.now(tz)
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        last_refresh = st.session_state.last_refresh
        time_ago = (datetime.now(tz) - last_refresh).total_seconds()
        
        if time_ago < 60:
            time_str = f"{int(time_ago)} seconds ago"
        elif time_ago < 3600:
            time_str = f"{int(time_ago / 60)} minutes ago"
        else:
            time_str = f"{int(time_ago / 3600)} hours ago"
        
        st.caption(f"Last updated: {time_str}")
    
    with col2:
        st.caption("Auto-refresh: Every 15 min")
    
    with col3:
        if st.button("🔄 Refresh Now", type="primary", use_container_width=True):
            st.session_state.last_refresh = datetime.now(tz)
            st.rerun()
    
    return st.session_state.last_refresh
