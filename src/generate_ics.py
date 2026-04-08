#!/usr/bin/env python3
"""
Generate US Economic Events Calendar (.ics) from live API data
Supports Google Calendar, Apple Calendar, and other iCal-compatible apps
"""

import sys
import uuid
import hashlib
import json
import urllib.request
import urllib.error
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


# =============================================================================
# Configuration
# =============================================================================

API_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


# =============================================================================
# Data Model
# =============================================================================

@dataclass
class EconomicEvent:
    name: str
    date: datetime              # event date and time (ET)
    event_type: str             # type: CPI, FOMC, NFP, GDP, PCE, RETAIL
    importance: str             # importance: high, medium, low
    description: Optional[str] = None
    country: str = "US"


# =============================================================================
# Fetcher Functions (merged from fetcher.py)
# =============================================================================

def fetch_calendar_data() -> list[dict]:
    """Fetch economic calendar data from API with retry logic"""
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(
                API_URL,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                }
            )

            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data

        except urllib.error.HTTPError as e:
            if e.code == 429:  # Too Many Requests
                if attempt < MAX_RETRIES - 1:
                    wait_time = RETRY_DELAY * (attempt + 1)
                    print(f"⚠️  Rate limited (429), waiting {wait_time}s before retry {attempt + 1}/{MAX_RETRIES}...")
                    time.sleep(wait_time)
                    continue
            print(f"⚠️  HTTP error {e.code}: {e.reason}")
            return []
        except urllib.error.URLError as e:
            print(f"⚠️  URL error: {e.reason}")
            return []
        except json.JSONDecodeError as e:
            print(f"⚠️  JSON decode error: {e}")
            return []

    return []


def map_event_type(title: str) -> str:
    """Map event title to event type"""
    title_upper = title.upper()

    if "FOMC" in title_upper or "FED" in title_upper:
        return "FOMC"
    elif "CPI" in title_upper:
        return "CPI"
    elif "NON-FARM" in title_upper or "NFP" in title_upper or "PAYROLL" in title_upper:
        return "NFP"
    elif "PCE" in title_upper:
        return "PCE"
    elif "GDP" in title_upper:
        return "GDP"
    elif "RETAIL SALES" in title_upper:
        return "RETAIL"
    elif "UNEMPLOYMENT" in title_upper or "JOBLESS" in title_upper:
        return "NFP"
    else:
        return "OTHER"


def parse_event(event_data: dict) -> Optional[EconomicEvent]:
    """Parse API event data into EconomicEvent"""
    try:
        title = event_data.get("title", "")
        country = event_data.get("country", "")
        date_str = event_data.get("date", "")
        impact = event_data.get("impact", "Low")
        forecast = event_data.get("forecast", "")
        previous = event_data.get("previous", "")

        # Skip non-US events
        if country != "USD":
            return None

        # Skip holidays
        if impact == "Holiday":
            return None

        # Parse date (ISO 8601 format with timezone)
        # Example: "2026-04-10T08:30:00-04:00"
        event_date = datetime.fromisoformat(date_str)

        # Map impact to importance
        importance = impact.lower()

        # Build description
        desc_parts = []
        if forecast:
            desc_parts.append(f"Forecast: {forecast}")
        if previous:
            desc_parts.append(f"Previous: {previous}")
        description = " | ".join(desc_parts) if desc_parts else None

        # Map event type
        event_type = map_event_type(title)

        return EconomicEvent(
            name=title,
            date=event_date,
            event_type=event_type,
            importance=importance,
            description=description,
            country="US"
        )
    except Exception as e:
        print(f"⚠️  Failed to parse event: {e}")
        return None


def fetch_us_high_impact_events() -> list[EconomicEvent]:
    """Fetch US high-impact economic events from API"""
    raw_data = fetch_calendar_data()

    if not raw_data:
        print("⚠️  No data fetched from API, falling back to static data")
        return []

    events = []
    for event_data in raw_data:
        event = parse_event(event_data)
        if event:
            events.append(event)

    # Sort by date
    events.sort(key=lambda x: x.date)

    print(f"✅ Fetched {len(events)} US events from API")

    # Print high importance events
    high_impact = [e for e in events if e.importance == "high"]
    print(f"🔴 High impact events: {len(high_impact)}")
    for e in high_impact[:5]:  # Show first 5
        print(f"   - {e.date.strftime('%Y-%m-%d')}: {e.name}")

    return high_impact


def generate_ical_event(event: EconomicEvent, sequence: int = 0) -> str:
    """Generate a single iCalendar event (VEVENT)"""
    
    # Generate unique UID
    uid_base = f"{event.name}-{event.date.isoformat()}"
    uid = hashlib.md5(uid_base.encode()).hexdigest() + "@economic-calendar"
    
    # API data has timezone info, convert to UTC
    dtstart_utc = event.date.astimezone(timezone.utc)
    dtend_utc = dtstart_utc + timedelta(hours=1)  # Assume 1-hour duration
    
    dtstamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dtstart = dtstart_utc.strftime("%Y%m%dT%H%M%SZ")
    dtend = dtend_utc.strftime("%Y%m%dT%H%M%SZ")
    
    # Build event description
    description_parts = [event.event_type]
    if event.description:
        description_parts.append(event.description)
    description_parts.append(f"Importance: {event.importance.upper()}")
    description = " | ".join(description_parts)
    
    # Add alarm (1 day before)
    alarm = """BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Reminder
TRIGGER:-P1D
END:VALARM"""
    
    vevent = f"""BEGIN:VEVENT
DTSTAMP:{dtstamp}
UID:{uid}
SEQUENCE:{sequence}
SUMMARY:{event.name}
DESCRIPTION:{description}
DTSTART:{dtstart}
DTEND:{dtend}
STATUS:CONFIRMED
{alarm}
END:VEVENT"""
    
    return vevent


def generate_ical_calendar(events: list[EconomicEvent]) -> str:
    """Generate complete iCalendar file content"""
    
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    header = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Economic Calendar//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:US Economic Calendar
X-WR-TIMEZONE:America/New_York
X-WR-CALDESC:High importance US economic events from live feed
REFRESH-INTERVAL;VALUE=DURATION:P1D
SOURCE;VALUE=URI:https://github.com/economic-calendar
LAST-MODIFIED:{now}"""
    
    footer = "END:VCALENDAR"
    
    vevents = []
    for i, event in enumerate(events):
        vevent = generate_ical_event(event, sequence=i)
        vevents.append(vevent)
    
    calendar = header + "\n" + "\n".join(vevents) + "\n" + footer
    return calendar


def save_calendar(output_path: Path) -> Path:
    """Generate and save calendar file from live API data
    
    Args:
        output_path: Path to save the .ics file
        
    Returns:
        Path to generated file
        
    Raises:
        SystemExit: If API fetch fails
    """
    # Fetch from API only
    events = fetch_us_high_impact_events()
    
    if not events:
        print("❌ Failed to fetch events from API. Exiting.")
        sys.exit(1)
    
    # Filter past events (keep last 7 days for reference)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    
    future_events = [e for e in events if e.date >= cutoff]
    
    if not future_events:
        print("⚠️  No future events found in API response.")
        future_events = events  # Use all events if no future ones
    
    # Sort by date
    future_events.sort(key=lambda x: x.date)
    
    ical_content = generate_ical_calendar(future_events)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(ical_content, encoding='utf-8')
    
    print(f"✅ Calendar generated: {output_path}")
    print(f"📊 Total events: {len(future_events)}")
    
    # Print high-importance events count
    high_importance = [e for e in future_events if e.importance == "high"]
    print(f"🔴 High importance: {len(high_importance)}")
    
    # Count by type
    by_type = {}
    for e in future_events:
        by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
    print("📈 By type:")
    for etype, count in sorted(by_type.items()):
        print(f"   {etype}: {count}")
    
    return output_path


def main():
    """Main function"""
    # Output path
    output_dir = Path(__file__).parent.parent / "output"
    output_path = output_dir / "us-economic-calendar.ics"
    
    # Generate calendar
    save_calendar(output_path)


if __name__ == "__main__":
    main()
