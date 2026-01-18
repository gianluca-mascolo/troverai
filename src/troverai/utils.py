"""Utility functions for TroveRAI."""

import sys
from datetime import datetime, timedelta

# Channel name mappings (display name -> API name)
CHANNEL_MAP = {
    "rai1": "rai-1",
    "rai2": "rai-2",
    "rai3": "rai-3",
    "rai4": "rai-4",
    "rai5": "rai-5",
    "raimovie": "rai-movie",
    "raipremium": "rai-premium",
    "raigulp": "rai-gulp",
    "raiyoyo": "rai-yoyo",
    "raistoria": "rai-storia",
    "raiscuola": "rai-scuola",
    "rainews24": "rai-news-24",
    "raisport": "rai-sport",
}


def normalize_channel(channel):
    """Normalize channel name to API format."""
    # Remove spaces and lowercase
    clean = channel.lower().replace(" ", "").replace("-", "")

    # Check mapping
    if clean in CHANNEL_MAP:
        return CHANNEL_MAP[clean]

    # Already in correct format?
    if channel.startswith("rai-"):
        return channel

    # Try adding rai- prefix
    return f"rai-{channel.lower()}"


def parse_date(date_str):
    """Parse date string to dd-mm-yyyy format."""
    today = datetime.now()

    if date_str in ("oggi", "today"):
        return today.strftime("%d-%m-%Y")
    elif date_str in ("domani", "tomorrow"):
        return (today + timedelta(days=1)).strftime("%d-%m-%Y")
    elif date_str in ("ieri", "yesterday"):
        return (today - timedelta(days=1)).strftime("%d-%m-%Y")
    else:
        # Try to parse as date
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%d-%m-%Y")
            except ValueError:
                continue

        # Try as offset (e.g., +1, -2)
        if date_str.startswith("+") or date_str.startswith("-"):
            try:
                offset = int(date_str)
                return (today + timedelta(days=offset)).strftime("%d-%m-%Y")
            except ValueError:
                pass

        print(f"Error: Invalid date format: {date_str}", file=sys.stderr)
        sys.exit(1)


def format_duration(duration_str):
    """Format duration string (HH:MM:SS) to readable format."""
    if not duration_str:
        return ""

    parts = duration_str.split(":")
    if len(parts) == 3:
        h, m, _ = int(parts[0]), int(parts[1]), int(parts[2])
        if h > 0:
            return f"{h}h{m:02d}m"
        else:
            return f"{m}m"
    return duration_str


def is_current_program(time_str, duration_str):
    """Check if a program is currently on air."""
    if not time_str:
        return False

    now = datetime.now()

    try:
        # Parse program start time
        prog_time = datetime.strptime(time_str, "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )

        # Parse duration
        if duration_str:
            parts = duration_str.split(":")
            if len(parts) == 3:
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                duration = timedelta(hours=h, minutes=m, seconds=s)
                end_time = prog_time + duration

                return prog_time <= now <= end_time

        # If no duration, just check if it started
        return prog_time <= now

    except ValueError:
        return False


def find_current_program(events):
    """Find the currently airing program from a list of events."""
    for event in events:
        if event:
            time_str = event.get("hour", "")
            duration_str = event.get("duration", "")
            if is_current_program(time_str, duration_str):
                return event
    return None


def filter_by_dfp(events, tipo=None, genere=None):
    """Filter events by dfp typology and/or genre."""
    if not tipo and not genere:
        return events

    filtered = []
    for event in events:
        if not event:
            continue
        dfp = event.get("dfp", {})

        if tipo and dfp.get("escaped_typology_name", "").lower() != tipo.lower():
            continue
        if genere and dfp.get("escaped_genre_name", "").lower() != genere.lower():
            continue

        filtered.append(event)
    return filtered
