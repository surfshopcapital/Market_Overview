"""Kalshi API client for public endpoints. No authentication required."""
import time
import logging
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config.settings import settings
from kalshi.schemas import (
    MarketsListResponse, EventsListResponse, EventResponse,
    MarketResponse, TagsByCategoriesResponse
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple token bucket rate limiter."""
    
    def __init__(self, calls_per_second: int = 10):
        self.calls_per_second = calls_per_second
        self.min_interval = 1.0 / calls_per_second
        self.last_call_time = 0.0
    
    def wait(self):
        """Wait if necessary to respect rate limit."""
        now = time.time()
        time_since_last_call = now - self.last_call_time
        
        if time_since_last_call < self.min_interval:
            sleep_time = self.min_interval - time_since_last_call
            time.sleep(sleep_time)
        
        self.last_call_time = time.time()


class KalshiClient:
    """Kalshi API client for public market data. Uses unauthenticated endpoints only."""
    
    def __init__(
        self, 
        base_url: Optional[str] = None,
        rate_limit_per_second: int = 10
    ):
        self.base_url = (base_url or settings.KALSHI_API_BASE_URL).rstrip("/")
        self.session = self._create_session()
        self.rate_limiter = RateLimiter(calls_per_second=rate_limit_per_second)
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic."""
        session = requests.Session()
        
        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with rate limiting and error handling. Public endpoints only."""
        self.rate_limiter.wait()
        
        # Properly join base URL and endpoint (strip leading slash from endpoint)
        endpoint = endpoint.lstrip("/")
        url = f"{self.base_url}/{endpoint}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json_data,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP error for {method} {endpoint}: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            raise
        except Exception as e:
            logger.error(f"Error making request to {method} {endpoint}: {e}")
            raise
    
    def get_markets(
        self, 
        limit: int = 200,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        min_created_ts: Optional[int] = None,
        max_created_ts: Optional[int] = None,
        min_updated_ts: Optional[int] = None,
        min_close_ts: Optional[int] = None,
        max_close_ts: Optional[int] = None
    ) -> MarketsListResponse:
        """Get markets with optional filters."""
        params = {"limit": min(limit, 1000)}
        
        if cursor:
            params["cursor"] = cursor
        if status:
            params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker
        if event_ticker:
            params["event_ticker"] = event_ticker
        if min_created_ts:
            params["min_created_ts"] = min_created_ts
        if max_created_ts:
            params["max_created_ts"] = max_created_ts
        if min_updated_ts:
            params["min_updated_ts"] = min_updated_ts
        if min_close_ts:
            params["min_close_ts"] = min_close_ts
        if max_close_ts:
            params["max_close_ts"] = max_close_ts
        
        data = self._make_request("GET", "/markets", params=params)
        return MarketsListResponse(**data)
    
    def get_all_markets(
        self,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
        event_ticker: Optional[str] = None,
        min_created_ts: Optional[int] = None,
        max_created_ts: Optional[int] = None,
        min_updated_ts: Optional[int] = None,
        max_results: Optional[int] = None
    ) -> List[MarketResponse]:
        """Get all markets using pagination."""
        all_markets = []
        cursor = None
        
        while True:
            response = self.get_markets(
                limit=200,
                cursor=cursor,
                status=status,
                series_ticker=series_ticker,
                event_ticker=event_ticker,
                min_created_ts=min_created_ts,
                max_created_ts=max_created_ts,
                min_updated_ts=min_updated_ts
            )
            
            all_markets.extend(response.markets)
            
            if max_results and len(all_markets) >= max_results:
                return all_markets[:max_results]
            
            cursor = response.cursor
            if not cursor:
                break
        
        return all_markets
    
    def get_events(
        self,
        limit: int = 200,
        cursor: Optional[str] = None,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
        with_nested_markets: bool = True,
        min_close_ts: Optional[int] = None
    ) -> EventsListResponse:
        """Get events with optional filters. Note: status filter may not be supported."""
        params = {
            "limit": min(limit, 200),
            "with_nested_markets": str(with_nested_markets).lower()
        }
        
        if cursor:
            params["cursor"] = cursor
        # Don't send status parameter - API doesn't support it
        # if status:
        #     params["status"] = status
        if series_ticker:
            params["series_ticker"] = series_ticker
        if min_close_ts:
            params["min_close_ts"] = min_close_ts
        
        data = self._make_request("GET", "/events", params=params)
        return EventsListResponse(**data)
    
    def get_all_events(
        self,
        status: Optional[str] = None,
        series_ticker: Optional[str] = None,
        with_nested_markets: bool = True,
        max_results: Optional[int] = None
    ) -> List[EventResponse]:
        """Get all events using pagination."""
        all_events = []
        cursor = None
        page = 1
        
        while True:
            logger.info(f"Fetching events page {page}...")
            response = self.get_events(
                limit=200,
                cursor=cursor,
                status=status,
                series_ticker=series_ticker,
                with_nested_markets=with_nested_markets
            )
            
            all_events.extend(response.events)
            markets_count = sum(len(e.markets or []) for e in response.events)
            logger.info(f"Page {page} done: got {len(response.events)} events, {markets_count} markets. Total so far: {len(all_events)} events")
            
            if max_results and len(all_events) >= max_results:
                return all_events[:max_results]
            
            cursor = response.cursor
            if not cursor:
                break
            page += 1
        
        return all_events
    
    def get_event(self, event_ticker: str) -> EventResponse:
        """Get single event by ticker."""
        data = self._make_request("GET", f"/events/{event_ticker}")
        # API returns {"event": {...}, "markets": [...]}
        event_data = data.get("event", {})
        if "markets" not in event_data and "markets" in data:
            event_data["markets"] = data["markets"]
        return EventResponse(**event_data)
    
    def get_tags_by_categories(self) -> TagsByCategoriesResponse:
        """Get tags organized by categories."""
        data = self._make_request("GET", "/search/tags_by_categories")
        return TagsByCategoriesResponse(**data)
    
    def get_series_list(
        self,
        limit: int = 200,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get series list."""
        params = {"limit": min(limit, 200)}
        if cursor:
            params["cursor"] = cursor
        
        return self._make_request("GET", "/series", params=params)
