"""Main Streamlit application."""
import streamlit as st

# Page configuration
st.set_page_config(
    page_title="Kalshi Markets Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Navigation
pages = {
    "New Markets": [
        st.Page("pages/new_markets.py", title="🆕 New Markets", icon="🆕"),
    ],
    "Analytics": [
        st.Page("pages/trending.py", title="📈 Trending", icon="📈"),
        st.Page("pages/mentions.py", title="💬 Mentions", icon="💬"),
        st.Page("pages/relative_volume.py", title="🔥 Relative Volume", icon="🔥"),
    ],
    "Settings": [
        st.Page("pages/email_settings.py", title="⚙️ Email Settings", icon="⚙️"),
    ],
}

pg = st.navigation(pages)
pg.run()
