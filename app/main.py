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
        st.Page("app/pages/new_markets.py", title="🆕 New Markets", icon="🆕"),
    ],
    "Analytics": [
        st.Page("app/pages/trending.py", title="📈 Trending", icon="📈"),
        st.Page("app/pages/mentions.py", title="💬 Mentions", icon="💬"),
        st.Page("app/pages/relative_volume.py", title="🔥 Relative Volume", icon="🔥"),
    ],
    "Settings": [
        st.Page("app/pages/email_settings.py", title="⚙️ Email Settings", icon="⚙️"),
    ],
}

pg = st.navigation(pages)
pg.run()
