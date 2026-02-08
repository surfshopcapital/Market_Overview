"""Email digest worker to generate and send market digests."""
import logging
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import pytz
import resend

from config import settings, SessionLocal
from db.models import (
    Market, Event, MarketSnapshot, EmailSettings, 
    EmailDigestLog, Category
)
from sqlalchemy import and_, func, desc

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/emailer.log', mode='a')
    ]
)
logger = logging.getLogger(__name__)


class EmailDigester:
    """Email digest generator and sender."""
    
    def __init__(self):
        self.db = SessionLocal()
        resend.api_key = settings.RESEND_API_KEY
        self.tz = pytz.timezone(settings.TIMEZONE)
    
    def __del__(self):
        """Clean up database connection."""
        if hasattr(self, 'db'):
            self.db.close()
    
    def should_send_now(self) -> bool:
        """Check if we should send an email based on settings."""
        email_settings = self.db.query(EmailSettings).first()
        if not email_settings:
            logger.warning("No email settings found")
            return False
        
        now = datetime.now(self.tz)
        current_time = now.strftime("%H:%M")
        
        # Check if current time matches any send time (within 5-minute window)
        for send_time in email_settings.send_times:
            send_hour, send_minute = map(int, send_time.split(':'))
            if abs(now.hour - send_hour) == 0 and abs(now.minute - send_minute) <= 5:
                # Check if we already sent in the last hour
                last_log = self.db.query(EmailDigestLog).filter(
                    EmailDigestLog.sent_at >= datetime.utcnow() - timedelta(hours=1),
                    EmailDigestLog.success == True
                ).first()
                
                if last_log:
                    logger.info("Already sent digest in the last hour, skipping")
                    return False
                
                return True
        
        return False
    
    def run(self, force: bool = False):
        """Run the email digest process."""
        logger.info("=" * 80)
        logger.info("Starting email digest run")
        logger.info("=" * 80)
        
        try:
            if not force and not self.should_send_now():
                logger.info("Not scheduled to send now, exiting")
                return
            
            # Get email settings
            email_settings = self.db.query(EmailSettings).first()
            if not email_settings:
                logger.error("No email settings found")
                return
            
            # Generate digest content
            digest_data = self._generate_digest(email_settings)
            
            # Generate HTML email
            html_content = self._generate_html(digest_data, email_settings)
            
            # Send email
            self._send_email(
                recipients=email_settings.recipients,
                subject=f"Kalshi Markets Digest - {datetime.now(self.tz).strftime('%B %d, %Y %I:%M %p %Z')}",
                html_content=html_content,
                digest_data=digest_data
            )
            
            logger.info("Email digest completed successfully")
            
        except Exception as e:
            logger.error(f"Error during email digest: {e}", exc_info=True)
            self._log_digest(
                recipients=[],
                sections=[],
                counts={},
                success=False,
                error_message=str(e)
            )
    
    def _generate_digest(self, settings: EmailSettings) -> Dict[str, Any]:
        """Generate digest data based on settings."""
        digest = {
            "new_markets": [],
            "trending": [],
            "mentions": [],
            "relative_volume": []
        }
        
        # New Markets
        if settings.enabled_sections.get("new_markets", True):
            digest["new_markets"] = self._get_new_markets(
                settings.new_markets_window_hours
            )
        
        # Trending
        if settings.enabled_sections.get("trending", True):
            digest["trending"] = self._get_trending_markets()
        
        # Mentions
        if settings.enabled_sections.get("mentions", True):
            digest["mentions"] = self._get_mention_markets(
                settings.mentions_new_window_hours
            )
        
        # Relative Volume
        if settings.enabled_sections.get("relative_volume", True):
            digest["relative_volume"] = self._get_relative_volume_markets(
                settings.relative_volume_period_hours,
                settings.relative_volume_baseline_days,
                settings.relative_volume_top_n
            )
        
        return digest
    
    def _get_new_markets(self, window_hours: int) -> List[Dict[str, Any]]:
        """Get new markets within window."""
        cutoff = datetime.utcnow() - timedelta(hours=window_hours)
        
        markets = self.db.query(Market, Event).join(
            Event, Market.event_ticker == Event.event_ticker
        ).filter(
            Market.first_seen_at >= cutoff,
            Market.status == "open"
        ).order_by(
            desc(Market.volume)
        ).limit(10).all()
        
        result = []
        for market, event in markets:
            result.append({
                "ticker": market.ticker,
                "title": market.title,
                "event_title": event.title,
                "category": event.category,
                "open_time": market.open_time,
                "volume": market.volume or 0,
                "yes_bid": market.yes_bid,
                "yes_ask": market.yes_ask,
                "url": f"https://kalshi.com/markets/{market.ticker}"
            })
        
        return result
    
    def _get_trending_markets(self) -> List[Dict[str, Any]]:
        """Get trending markets."""
        markets = self.db.query(Market, Event).join(
            Event, Market.event_ticker == Event.event_ticker
        ).filter(
            Market.is_trending == True,
            Market.status == "open"
        ).order_by(
            desc(Market.volume_24h)
        ).all()
        
        result = []
        for market, event in markets:
            result.append({
                "ticker": market.ticker,
                "title": market.title,
                "event_title": event.title,
                "category": event.category,
                "volume_24h": market.volume_24h or 0,
                "yes_bid": market.yes_bid,
                "yes_ask": market.yes_ask,
                "url": f"https://kalshi.com/markets/{market.ticker}"
            })
        
        return result
    
    def _get_mention_markets(self, new_window_hours: int) -> List[Dict[str, Any]]:
        """Get mention markets sorted by expiration."""
        cutoff = datetime.utcnow() - timedelta(hours=new_window_hours)
        
        markets = self.db.query(Market, Event).join(
            Event, Market.event_ticker == Event.event_ticker
        ).filter(
            Market.is_mention == True,
            Market.status == "open",
            Market.expiration_time.isnot(None)
        ).order_by(
            Market.expiration_time.asc()
        ).all()
        
        result = []
        for market, event in markets:
            is_new = market.first_seen_at >= cutoff
            time_remaining = None
            if market.expiration_time:
                delta = market.expiration_time - datetime.utcnow()
                days = delta.days
                hours = delta.seconds // 3600
                time_remaining = f"{days}d {hours}h" if days > 0 else f"{hours}h"
            
            result.append({
                "ticker": market.ticker,
                "title": market.title,
                "event_title": event.title,
                "category": event.category,
                "expiration_time": market.expiration_time,
                "time_remaining": time_remaining,
                "is_new": is_new,
                "yes_bid": market.yes_bid,
                "yes_ask": market.yes_ask,
                "url": f"https://kalshi.com/markets/{market.ticker}"
            })
        
        return result
    
    def _get_relative_volume_markets(
        self, 
        period_hours: int, 
        baseline_days: int,
        top_n: int
    ) -> List[Dict[str, Any]]:
        """Get markets with high relative volume (excluding sports)."""
        # Get sports categories
        sports_cats = self.db.query(Category.name).filter(
            Category.is_sports == True
        ).all()
        sports_categories = [cat[0] for cat in sports_cats]
        
        # Get events not in sports categories
        current_cutoff = datetime.utcnow() - timedelta(hours=period_hours)
        baseline_cutoff = datetime.utcnow() - timedelta(days=baseline_days)
        
        # Get current period volume per event
        current_query = self.db.query(
            Event.event_ticker,
            Event.title,
            Event.category,
            func.sum(Market.volume).label("current_volume")
        ).join(
            Market, Market.event_ticker == Event.event_ticker
        ).filter(
            Market.status == "open",
            ~Event.category.in_(sports_categories) if sports_categories else True
        ).group_by(
            Event.event_ticker, Event.title, Event.category
        ).all()
        
        result = []
        
        for event_ticker, title, category, current_volume in current_query:
            if not current_volume or current_volume == 0:
                continue
            
            # Get baseline average from snapshots
            baseline_snapshots = self.db.query(
                func.avg(MarketSnapshot.volume).label("avg_volume")
            ).join(
                Market, Market.ticker == MarketSnapshot.ticker
            ).filter(
                Market.event_ticker == event_ticker,
                MarketSnapshot.snapshot_time >= baseline_cutoff,
                MarketSnapshot.snapshot_time < current_cutoff
            ).scalar()
            
            if not baseline_snapshots or baseline_snapshots < 100:
                continue
            
            # Calculate relative volume
            baseline_daily_avg = baseline_snapshots / baseline_days
            relative = current_volume / baseline_daily_avg if baseline_daily_avg > 0 else 0
            
            if relative >= 2.0:  # At least 2x baseline
                result.append({
                    "event_ticker": event_ticker,
                    "title": title,
                    "category": category,
                    "current_volume": int(current_volume),
                    "baseline_avg": int(baseline_daily_avg),
                    "relative": round(relative, 2),
                    "url": f"https://kalshi.com/events/{event_ticker}"
                })
        
        # Sort by relative volume and take top N
        result.sort(key=lambda x: x["relative"], reverse=True)
        return result[:top_n]
    
    def _generate_html(self, digest_data: Dict[str, Any], settings: EmailSettings) -> str:
        """Generate HTML email content."""
        now = datetime.now(self.tz)
        
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; border-bottom: 2px solid #95a5a6; padding-bottom: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th {{ background-color: #3498db; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background-color: #f5f5f5; }}
        a {{ color: #3498db; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .new-badge {{ background-color: #e74c3c; color: white; padding: 2px 8px; border-radius: 3px; font-size: 0.8em; }}
        .footer {{ margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; font-size: 0.9em; color: #7f8c8d; }}
        .no-data {{ color: #7f8c8d; font-style: italic; padding: 20px; }}
    </style>
</head>
<body>
    <h1>Kalshi Markets Digest</h1>
    <p><strong>{now.strftime('%B %d, %Y at %I:%M %p %Z')}</strong></p>
"""
        
        # New Markets
        if digest_data["new_markets"]:
            html += f"""
    <h2>🆕 New Markets (Top 10 by Volume)</h2>
    <table>
        <tr>
            <th>Market</th>
            <th>Event</th>
            <th>Category</th>
            <th>Volume</th>
            <th>Bid/Ask</th>
        </tr>
"""
            for market in digest_data["new_markets"]:
                bid = f"{market['yes_bid']}¢" if market['yes_bid'] else "—"
                ask = f"{market['yes_ask']}¢" if market['yes_ask'] else "—"
                html += f"""
        <tr>
            <td><a href="{market['url']}">{market['title'][:80]}</a></td>
            <td>{market['event_title'][:50]}</td>
            <td>{market['category']}</td>
            <td>{market['volume']:,}</td>
            <td>{bid}/{ask}</td>
        </tr>
"""
            html += "    </table>\n"
        
        # Trending
        if digest_data["trending"]:
            html += f"""
    <h2>📈 Trending Markets</h2>
    <table>
        <tr>
            <th>Market</th>
            <th>Event</th>
            <th>Category</th>
            <th>24h Volume</th>
            <th>Bid/Ask</th>
        </tr>
"""
            for market in digest_data["trending"]:
                bid = f"{market['yes_bid']}¢" if market['yes_bid'] else "—"
                ask = f"{market['yes_ask']}¢" if market['yes_ask'] else "—"
                html += f"""
        <tr>
            <td><a href="{market['url']}">{market['title'][:80]}</a></td>
            <td>{market['event_title'][:50]}</td>
            <td>{market['category']}</td>
            <td>{market['volume_24h']:,}</td>
            <td>{bid}/{ask}</td>
        </tr>
"""
            html += "    </table>\n"
        
        # Mentions
        if digest_data["mentions"]:
            html += f"""
    <h2>💬 Mention Markets (Sorted by Expiration)</h2>
    <table>
        <tr>
            <th>Market</th>
            <th>Event</th>
            <th>Time Remaining</th>
            <th>Bid/Ask</th>
        </tr>
"""
            for market in digest_data["mentions"]:
                new_badge = '<span class="new-badge">NEW</span> ' if market['is_new'] else ''
                bid = f"{market['yes_bid']}¢" if market['yes_bid'] else "—"
                ask = f"{market['yes_ask']}¢" if market['yes_ask'] else "—"
                html += f"""
        <tr>
            <td>{new_badge}<a href="{market['url']}">{market['title'][:80]}</a></td>
            <td>{market['event_title'][:50]}</td>
            <td>{market['time_remaining']}</td>
            <td>{bid}/{ask}</td>
        </tr>
"""
            html += "    </table>\n"
        
        # Relative Volume
        if digest_data["relative_volume"]:
            html += f"""
    <h2>🔥 Relative Volume Standouts (No Sports)</h2>
    <table>
        <tr>
            <th>Event</th>
            <th>Category</th>
            <th>Current Volume</th>
            <th>Baseline Avg</th>
            <th>Relative</th>
        </tr>
"""
            for item in digest_data["relative_volume"]:
                html += f"""
        <tr>
            <td><a href="{item['url']}">{item['title'][:80]}</a></td>
            <td>{item['category']}</td>
            <td>{item['current_volume']:,}</td>
            <td>{item['baseline_avg']:,}</td>
            <td><strong>{item['relative']}x</strong></td>
        </tr>
"""
            html += "    </table>\n"
        
        # Footer
        html += """
    <div class="footer">
        <p>This is an automated digest from your Kalshi Markets Dashboard.</p>
        <p>Configure your digest settings at your Streamlit dashboard.</p>
    </div>
</body>
</html>
"""
        return html
    
    def _send_email(
        self, 
        recipients: List[str], 
        subject: str, 
        html_content: str,
        digest_data: Dict[str, Any]
    ):
        """Send email via Resend."""
        try:
            from_email = f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM}>"
            response = resend.Emails.send({
                "from": from_email,
                "to": recipients,
                "subject": subject,
                "html": html_content,
            })
            
            # Resend returns dict with "id" on success
            email_id = response.get("id") if isinstance(response, dict) else getattr(response, "id", None)
            if response and email_id:
                logger.info(f"Email sent successfully to {', '.join(recipients)}")
                self._log_digest(
                    recipients=recipients,
                    sections=list(digest_data.keys()),
                    counts={
                        "new_markets": len(digest_data.get("new_markets", [])),
                        "trending": len(digest_data.get("trending", [])),
                        "mentions": len(digest_data.get("mentions", [])),
                        "relative_volume": len(digest_data.get("relative_volume", []))
                    },
                    success=True
                )
            else:
                logger.error(f"Failed to send email: {response}")
                self._log_digest(
                    recipients=recipients,
                    sections=list(digest_data.keys()),
                    counts={},
                    success=False,
                    error_message=str(response)
                )
        
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            self._log_digest(
                recipients=recipients,
                sections=list(digest_data.keys()),
                counts={},
                success=False,
                error_message=str(e)
            )
            raise
    
    def _log_digest(
        self,
        recipients: List[str],
        sections: List[str],
        counts: Dict[str, int],
        success: bool,
        error_message: Optional[str] = None
    ):
        """Log email digest to database."""
        try:
            log = EmailDigestLog(
                sent_at=datetime.utcnow(),
                recipients=recipients,
                sections_included=sections,
                new_markets_count=counts.get("new_markets", 0),
                trending_markets_count=counts.get("trending", 0),
                mentions_count=counts.get("mentions", 0),
                relative_volume_count=counts.get("relative_volume", 0),
                success=success,
                error_message=error_message
            )
            self.db.add(log)
            self.db.commit()
        except Exception as e:
            logger.error(f"Error logging digest: {e}")
            self.db.rollback()


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Send Kalshi markets email digest")
    parser.add_argument("--force", action="store_true", help="Force send regardless of schedule")
    args = parser.parse_args()
    
    try:
        digester = EmailDigester()
        digester.run(force=args.force)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in email worker: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
