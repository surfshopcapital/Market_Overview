# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-08

### Added
- Initial release
- Streamlit dashboard with 5 pages (New Markets, Trending, Mentions, Relative Volume, Email Settings)
- PostgreSQL database schema for events, markets, and snapshots
- Kalshi API client with authentication, pagination, and rate limiting
- Data ingestion worker (hourly cron)
- Email digest worker (4x daily)
- Railway deployment configuration
- Comprehensive documentation (README, DEPLOYMENT, CONTRIBUTING)
- Bootstrap script for initial setup
- Quick start script for local development

### Features
- **New Markets Page**: View recently opened events/markets with drill-down
- **Trending Page**: High-volume markets matching Kalshi's trending
- **Mentions Page**: Markets about mentions, sorted by expiration
- **Relative Volume Page**: Events with unusually high volume (sports excluded)
- **Email Settings Page**: Configure digest preferences and test emails
- **Automated Ingestion**: Hourly data refresh from Kalshi API
- **Email Digests**: 4x daily HTML emails (6am, noon, 6pm, midnight ET)
- **Time-series Tracking**: Hourly snapshots for volume analysis
- **Smart Categorization**: Auto-identification of trending and mention markets
- **Sports Exclusion**: Robust filtering for relative volume analysis

### Technical
- Python 3.11+
- Streamlit for frontend
- PostgreSQL 15+ for data storage
- SQLAlchemy for ORM
- Resend for email delivery (3,000 emails/month free)
- Railway for deployment and cron scheduling
- Pydantic for data validation
- Structured logging

## [Unreleased]

### Planned
- WebSocket support for real-time updates
- User authentication and multi-user support
- Custom alerts and notifications
- Advanced analytics and charts
- Portfolio tracking integration
- Mobile-responsive improvements
