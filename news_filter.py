"""
News Filter
===========
Fetches the weekly economic calendar from ForexFactory and blocks
trading within a configurable window around high-impact USD events.

Gold (XAUUSD) is almost exclusively driven by USD macro events
(FOMC, NFP, CPI, PPI, GDP, etc.), so we filter on USD impact only.

Fails open: if the calendar cannot be fetched, a warning is logged
and trading is allowed to continue rather than shutting the bot down.

Requires: pip install requests
"""

import requests
from datetime import datetime, timezone, timedelta
from logger import setup_logger

logger = setup_logger()

# Currencies whose High-impact events can move Gold significantly
WATCHED_CURRENCIES = {"USD"}


class NewsFilter:
    CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

    def __init__(self, window_minutes=30):
        """
        Parameters
        ----------
        window_minutes : int
            How many minutes before AND after a high-impact event to
            block trading. Default is 30 (i.e., a 60-minute blackout
            window centred on the event).
        """
        self.window_minutes = window_minutes
        self._cached_events = []
        self._cache_date = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_events(self):
        """Fetch this week's calendar and return only High-impact USD events."""
        try:
            response = requests.get(self.CALENDAR_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            filtered = [
                e for e in data
                if e.get("impact") == "High"
                and e.get("country") in WATCHED_CURRENCIES
            ]
            return filtered

        except requests.exceptions.RequestException as e:
            logger.warning(
                f"NewsFilter: Could not reach calendar API ({e}). "
                f"News filter inactive for this cycle — trading continues."
            )
            return []
        except Exception as e:
            logger.warning(f"NewsFilter: Unexpected error ({e}). Trading continues.")
            return []

    def _refresh_if_needed(self):
        """Refresh the event cache once per day."""
        today = datetime.now(timezone.utc).date()
        if self._cache_date != today:
            self._cached_events = self._fetch_events()
            self._cache_date = today
            logger.info(
                f"NewsFilter: Loaded {len(self._cached_events)} high-impact USD "
                f"events for {today}."
            )

    @staticmethod
    def _parse_event_time(raw_date):
        """Parse ForexFactory date string to UTC datetime."""
        # ForexFactory uses ISO-8601 with a timezone offset, e.g. "2024-01-31T19:00:00-05:00"
        dt = datetime.fromisoformat(raw_date)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_blocked(self):
        """
        Return True if we are within window_minutes of a high-impact
        news event. Should be called once per bot loop iteration before
        generating a signal.
        """
        self._refresh_if_needed()

        if not self._cached_events:
            return False

        now = datetime.now(timezone.utc)
        window = timedelta(minutes=self.window_minutes)

        for event in self._cached_events:
            try:
                event_time = self._parse_event_time(event["date"])
            except (KeyError, ValueError):
                continue

            delta = abs((now - event_time).total_seconds())
            if delta <= window.total_seconds():
                logger.info(
                    f"NewsFilter: Blocking trade — '{event.get('title', 'Unknown')}' "
                    f"scheduled at {event_time.strftime('%Y-%m-%d %H:%M UTC')} "
                    f"(±{self.window_minutes} min window)."
                )
                return True

        return False

    def next_event(self):
        """
        Return a string describing the next upcoming high-impact event,
        or None if none are found. Useful for dashboard display.
        """
        self._refresh_if_needed()
        now = datetime.now(timezone.utc)
        upcoming = []

        for event in self._cached_events:
            try:
                event_time = self._parse_event_time(event["date"])
            except (KeyError, ValueError):
                continue
            if event_time > now:
                upcoming.append((event_time, event.get("title", "Unknown")))

        if not upcoming:
            return None

        upcoming.sort(key=lambda x: x[0])
        t, title = upcoming[0]
        delta_min = int((t - now).total_seconds() / 60)
        return f"{title} at {t.strftime('%H:%M UTC')} (in {delta_min} min)"
