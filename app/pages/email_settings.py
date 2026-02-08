"""Email Settings page."""
import streamlit as st
import sys
import os
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from config import SessionLocal
from db.models import EmailSettings
from workers.emailer import EmailDigester

st.title("⚙️ Email Settings")
st.markdown("Configure your market digest email preferences")

# Initialize database session
if 'db' not in st.session_state:
    st.session_state.db = SessionLocal()

db = st.session_state.db

# Get current settings
settings = db.query(EmailSettings).first()

if not settings:
    # Create default settings
    settings = EmailSettings(id=1)
    db.add(settings)
    db.commit()
    st.success("Created default email settings")

# Form for email settings
with st.form("email_settings_form"):
    st.markdown("### Recipients")
    recipients_text = st.text_area(
        "Email Addresses (one per line)",
        value="\n".join(settings.recipients),
        help="Enter one email address per line"
    )
    
    st.markdown("### Schedule")
    col1, col2 = st.columns(2)
    
    with col1:
        send_times_text = st.text_area(
            "Send Times (HH:MM format, one per line)",
            value="\n".join(settings.send_times),
            help="Enter times in 24-hour format (e.g., 06:00, 18:00)"
        )
    
    with col2:
        timezone = st.text_input(
            "Timezone",
            value=settings.timezone,
            help="Timezone for send times (e.g., America/New_York)"
        )
    
    st.markdown("### Sections")
    col1, col2 = st.columns(2)
    
    with col1:
        enable_new_markets = st.checkbox(
            "New Markets",
            value=settings.enabled_sections.get("new_markets", True)
        )
        enable_trending = st.checkbox(
            "Trending",
            value=settings.enabled_sections.get("trending", True)
        )
    
    with col2:
        enable_mentions = st.checkbox(
            "Mentions",
            value=settings.enabled_sections.get("mentions", True)
        )
        enable_relative_volume = st.checkbox(
            "Relative Volume",
            value=settings.enabled_sections.get("relative_volume", True)
        )
    
    st.markdown("### Section Parameters")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        new_markets_window = st.number_input(
            "New Markets Window (hours)",
            min_value=1,
            max_value=168,
            value=settings.new_markets_window_hours
        )
        
        mentions_new_window = st.number_input(
            "Mentions 'New' Window (hours)",
            min_value=1,
            max_value=168,
            value=settings.mentions_new_window_hours
        )
    
    with col2:
        relative_volume_period = st.number_input(
            "Relative Volume Period (hours)",
            min_value=1,
            max_value=168,
            value=settings.relative_volume_period_hours
        )
        
        relative_volume_baseline = st.number_input(
            "Relative Volume Baseline (days)",
            min_value=7,
            max_value=90,
            value=settings.relative_volume_baseline_days
        )
    
    with col3:
        relative_volume_top_n = st.number_input(
            "Relative Volume Top N",
            min_value=5,
            max_value=50,
            value=settings.relative_volume_top_n
        )
    
    # Submit button
    submitted = st.form_submit_button("💾 Save Settings", type="primary")
    
    if submitted:
        try:
            # Parse recipients
            recipients = [r.strip() for r in recipients_text.strip().split("\n") if r.strip()]
            
            # Parse send times
            send_times = [t.strip() for t in send_times_text.strip().split("\n") if t.strip()]
            
            # Validate send times format
            for time_str in send_times:
                try:
                    hours, minutes = map(int, time_str.split(":"))
                    if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                        raise ValueError
                except:
                    st.error(f"Invalid time format: {time_str}. Use HH:MM (e.g., 06:00)")
                    st.stop()
            
            # Update settings
            settings.recipients = recipients
            settings.send_times = send_times
            settings.timezone = timezone
            settings.enabled_sections = {
                "new_markets": enable_new_markets,
                "trending": enable_trending,
                "mentions": enable_mentions,
                "relative_volume": enable_relative_volume
            }
            settings.new_markets_window_hours = new_markets_window
            settings.mentions_new_window_hours = mentions_new_window
            settings.relative_volume_period_hours = relative_volume_period
            settings.relative_volume_baseline_days = relative_volume_baseline
            settings.relative_volume_top_n = relative_volume_top_n
            
            db.commit()
            st.success("✅ Settings saved successfully!")
            
        except Exception as e:
            st.error(f"Error saving settings: {e}")
            db.rollback()

# Test email button
st.markdown("---")
st.markdown("### Test Email")
st.markdown("Send a test digest email with current settings")

if st.button("📧 Send Test Email Now", type="secondary"):
    try:
        with st.spinner("Generating and sending test email..."):
            digester = EmailDigester()
            digester.run(force=True)
        st.success("✅ Test email sent successfully!")
    except Exception as e:
        st.error(f"Error sending test email: {e}")
        st.exception(e)

# Display current schedule
st.markdown("---")
st.markdown("### Current Schedule")
st.markdown(f"**Timezone:** {settings.timezone}")
st.markdown("**Send Times:**")
for time_str in settings.send_times:
    st.markdown(f"- {time_str}")

st.markdown("**Recipients:**")
for recipient in settings.recipients:
    st.markdown(f"- {recipient}")

# Show last digest logs
st.markdown("---")
st.markdown("### Recent Digest Logs")

from db.models import EmailDigestLog
from sqlalchemy import desc

logs = db.query(EmailDigestLog).order_by(
    desc(EmailDigestLog.sent_at)
).limit(10).all()

if logs:
    log_data = []
    for log in logs:
        log_data.append({
            "Sent At": log.sent_at.strftime("%Y-%m-%d %H:%M UTC"),
            "Recipients": ", ".join(log.recipients),
            "New": log.new_markets_count,
            "Trending": log.trending_markets_count,
            "Mentions": log.mentions_count,
            "Rel. Vol.": log.relative_volume_count,
            "Status": "✅ Success" if log.success else f"❌ Failed: {log.error_message}"
        })
    
    import pandas as pd
    st.dataframe(pd.DataFrame(log_data), use_container_width=True, hide_index=True)
else:
    st.info("No digest logs found")
