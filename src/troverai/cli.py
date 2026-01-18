"""
TroveRAI CLI - TV Schedule viewer for RaiPlay

Fetches and displays TV schedules from RaiPlay.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

import requests

# Color support (respect NO_COLOR environment variable)
# https://no-color.org
if "NO_COLOR" in os.environ:
    COLOR_RESET = ""
    COLOR_BOLD = ""
    COLOR_ITALIC = ""
    COLOR_CYAN_BOLD = ""
    COLOR_YELLOW_BOLD = ""
    COLOR_GREEN_BOLD = ""
else:
    COLOR_RESET = "\033[0m"
    COLOR_BOLD = "\033[1m"
    COLOR_ITALIC = "\033[3m"
    COLOR_CYAN_BOLD = "\033[1;36m"
    COLOR_YELLOW_BOLD = "\033[1;33m"
    COLOR_GREEN_BOLD = "\033[1;32m"

PALINSESTO_URL = "https://www.raiplay.it/palinsesto/app"
ORA_IN_ONDA_URL = "https://www.raiplay.it/dl/palinsesti/oraInOnda.json"
CHANNELS_URL = "https://www.raiplay.it/guidatv.json"

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


def get_session():
    """Create a requests session."""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36", "Accept": "application/json"})
    return session


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


def fetch_schedule(session, channel, date):
    """Fetch schedule for a specific channel and date."""
    url = f"{PALINSESTO_URL}/{channel}/{date}.json"

    response = session.get(url)

    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code} for {url}", file=sys.stderr)
        return None

    try:
        return response.json()
    except json.JSONDecodeError:
        print("Error: Invalid JSON response", file=sys.stderr)
        return None


def fetch_now_on_air(session):
    """Fetch what's currently on air on all channels."""
    response = session.get(ORA_IN_ONDA_URL)

    if response.status_code != 200:
        return None

    return response.json()


def fetch_channels(session):
    """Fetch list of available channels."""
    response = session.get(CHANNELS_URL)

    if response.status_code != 200:
        return None

    return response.json()


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
        prog_time = datetime.strptime(time_str, "%H:%M").replace(year=now.year, month=now.month, day=now.day)

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


def print_program(prog, show_current=True, compact=False):
    """Print a single program entry."""
    time = prog.get("hour", "??:??")
    duration = prog.get("duration", "")
    name = prog.get("name", "Unknown")

    # Check if current
    is_current = is_current_program(time, duration) if show_current else False

    # Format output
    duration_fmt = format_duration(duration)

    if compact:
        marker = ">" if is_current else " "
        print(f"{marker} {time} {name}")
    else:
        marker = f"{COLOR_GREEN_BOLD}>>>{COLOR_RESET}" if is_current else "   "
        name_fmt = f"{COLOR_BOLD}{name}{COLOR_RESET}" if is_current else name

        if duration_fmt:
            print(f"{marker} {time} - {name_fmt} ({duration_fmt})")
        else:
            print(f"{marker} {time} - {name_fmt}")

        # Show subtitle/description for current program
        if is_current and not compact:
            description = prog.get("description", "")

            if description:
                # Truncate long descriptions
                if len(description) > 100:
                    description = description[:97] + "..."
                print(f"       {COLOR_ITALIC}{description}{COLOR_RESET}")


def cmd_schedule(args):
    """Show schedule for a channel."""
    session = get_session()

    channel = normalize_channel(args.canale)
    date = parse_date(args.data)

    if not args.json:
        print(f"{COLOR_CYAN_BOLD}=== {args.canale.upper()} - {date} ==={COLOR_RESET}\n")

    data = fetch_schedule(session, channel, date)

    if not data:
        if args.json:
            output_json([])
        else:
            print("No schedule data available.")
        return

    # For JSON, output the raw API response
    if args.json:
        output_json(data)
        return

    # Parse the events array
    events = data.get("events", [])

    # Filter by time range if specified
    if args.dalle or args.alle:
        filtered = []
        for event in events:
            time = event.get("hour", "00:00")
            if args.dalle and time < args.dalle:
                continue
            if args.alle and time > args.alle:
                continue
            filtered.append(event)
        events = filtered

    # Filter by typology/genre
    events = filter_by_dfp(events, args.tipo, args.genere)

    # Show programs
    for event in events:
        if event:  # Skip empty entries
            print_program(event, show_current=(date == datetime.now().strftime("%d-%m-%Y")), compact=args.compatto)

    if not events:
        print("No programs found for the specified time range.")


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


def output_json(data):
    """Print data as JSON."""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_now(args):
    """Show what's currently on air (or schedule for specified date)."""
    session = get_session()

    date = parse_date(args.data)
    is_today = date == datetime.now().strftime("%d-%m-%Y")

    # Main channels to check
    all_channels = ["rai-1", "rai-2", "rai-3", "rai-4", "rai-5", "rai-movie", "rai-premium", "rai-gulp", "rai-yoyo", "rai-storia", "rai-scuola", "rai-news-24", "rai-sport"]

    # Filter by channel if specified
    if args.canale:
        filter_channel = normalize_channel(args.canale)
        all_channels = [c for c in all_channels if filter_channel in c]

    # Collect data for JSON output
    json_data = {}

    if not args.json:
        if is_today:
            print(f"{COLOR_CYAN_BOLD}=== Ora in onda - {datetime.now().strftime('%H:%M')} ==={COLOR_RESET}\n")
        else:
            print(f"{COLOR_CYAN_BOLD}=== Palinsesto - {date} ==={COLOR_RESET}\n")

    for channel in all_channels:
        data = fetch_schedule(session, channel, date)

        if not data:
            continue

        channel_name = data.get("channel", channel)
        events = data.get("events", [])

        # For JSON output, collect full raw data
        if args.json:
            json_data[channel] = data
            continue

        # For terminal output, show current program (if today) or full schedule
        if is_today:
            current_prog = find_current_program(events)

            # Filter by typology/genre
            if current_prog:
                filtered = filter_by_dfp([current_prog], args.tipo, args.genere)
                current_prog = filtered[0] if filtered else None

            if current_prog:
                name = current_prog.get("name", "Unknown")
                time = current_prog.get("hour", "")
                duration = format_duration(current_prog.get("duration", ""))

                if args.compatto:
                    print(f"{channel_name}: {name}")
                else:
                    print(f"{COLOR_YELLOW_BOLD}{channel_name}{COLOR_RESET}")
                    if duration:
                        print(f"  {time} - {COLOR_BOLD}{name}{COLOR_RESET} ({duration})")
                    else:
                        print(f"  {time} - {COLOR_BOLD}{name}{COLOR_RESET}")

                    # Show description
                    description = current_prog.get("description", "")
                    if description:
                        if len(description) > 120:
                            description = description[:117] + "..."
                        print(f"  {COLOR_ITALIC}{description}{COLOR_RESET}")
                    print()
        else:
            # Show full schedule for non-today dates
            # Filter by typology/genre
            events = filter_by_dfp(events, args.tipo, args.genere)

            print(f"{COLOR_YELLOW_BOLD}{channel_name}{COLOR_RESET}")
            for event in events:
                if event:
                    name = event.get("name", "Unknown")
                    time = event.get("hour", "??:??")
                    duration = format_duration(event.get("duration", ""))

                    if args.compatto:
                        print(f"  {time} {name}")
                    else:
                        if duration:
                            print(f"  {time} - {name} ({duration})")
                        else:
                            print(f"  {time} - {name}")
            print()

    if args.json:
        output_json(json_data)


def cmd_channels(args):
    """List available channels."""
    session = get_session()

    data = fetch_channels(session)

    if not data:
        if args.json:
            output_json([])
        else:
            print("Error fetching channels.", file=sys.stderr)
        return

    if args.json:
        output_json(data)
    else:
        print(f"{COLOR_CYAN_BOLD}=== Canali disponibili ==={COLOR_RESET}\n")

        for channel in data.get("channels", []):
            label = channel.get("label", "")
            path = channel.get("absolute_path", "")
            print(f"  {label:20} (--canale {path})")


def cmd_prime_time(args):
    """Show prime time schedule (20:00-23:00) for main channels."""
    session = get_session()

    date = parse_date(args.data)
    main_channels = ["rai-1", "rai-2", "rai-3"]

    # Collect raw data for JSON output
    json_data = {}

    if not args.json:
        print(f"{COLOR_CYAN_BOLD}=== Prima Serata - {date} ==={COLOR_RESET}\n")

    for channel in main_channels:
        data = fetch_schedule(session, channel, date)

        if not data:
            continue

        if args.json:
            json_data[channel] = data

        channel_name = data.get("channel", channel)
        events = data.get("events", [])

        # Filter for prime time (20:00 - 23:59)
        prime_events = [e for e in events if e and "20:" <= e.get("hour", "00:00") <= "23:59"]

        # Filter by typology/genre
        prime_events = filter_by_dfp(prime_events, args.tipo, args.genere)

        if not args.json:
            print(f"{COLOR_YELLOW_BOLD}{channel_name}{COLOR_RESET}")

        for event in prime_events:
            if not args.json:
                name = event.get("name", "Unknown")
                time = event.get("hour", "00:00")
                duration = format_duration(event.get("duration", ""))

                print(f"  {time} - {name}", end="")
                if duration:
                    print(f" ({duration})")
                else:
                    print()

        if not args.json:
            print()

    if args.json:
        output_json(json_data)


def cmd_search(args):
    """Search for a program in today's schedule."""
    session = get_session()

    date = parse_date(args.data)
    search_term = args.cerca.lower()

    channels = ["rai-1", "rai-2", "rai-3", "rai-4", "rai-5", "rai-movie", "rai-premium", "rai-storia"]

    # Collect raw programs for JSON output
    json_programs = []

    if not args.json:
        print(f"{COLOR_CYAN_BOLD}=== Ricerca: '{args.cerca}' - {date} ==={COLOR_RESET}\n")

    found = False

    for channel in channels:
        data = fetch_schedule(session, channel, date)

        if not data:
            continue

        channel_name = data.get("channel", channel)
        events = data.get("events", [])

        # Filter by name
        matching = [e for e in events if e and search_term in e.get("name", "").lower()]

        # Filter by typology/genre
        matching = filter_by_dfp(matching, args.tipo, args.genere)

        for event in matching:
            found = True
            name = event.get("name", "")
            if args.json:
                json_programs.append(event)
            else:
                time = event.get("hour", "??:??")
                duration = format_duration(event.get("duration", ""))

                print(f"{COLOR_YELLOW_BOLD}{channel_name}{COLOR_RESET} - {time}")
                print(f"  {COLOR_BOLD}{name}{COLOR_RESET}", end="")
                if duration:
                    print(f" ({duration})")
                else:
                    print()
                print()

    if args.json:
        output_json(json_programs)
    elif not found:
        print(f"Nessun programma trovato con '{args.cerca}'")


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="troverai",
        description="TroveRAI - TV Schedule viewer for RaiPlay",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --ora                        # What's on air now
  %(prog)s --canale rai-1               # Today's Rai 1 schedule
  %(prog)s --canale rai-1 --data domani # Tomorrow's schedule
  %(prog)s --canale rai-2 --dalle 20:00 # Evening schedule
  %(prog)s --prima-serata               # Prime time on main channels
  %(prog)s --cerca "film"               # Search for programs
  %(prog)s --canali                     # List available channels

Date formats:
  oggi, today, domani, tomorrow, ieri, yesterday
  dd-mm-yyyy, dd/mm/yyyy, +1, -2 (offset from today)
        """,
    )

    # Main commands
    parser.add_argument("--ora", "-o", action="store_true", help="Show what's currently on air")
    parser.add_argument("--canale", "-c", metavar="NOME", help="Show schedule for a specific channel")
    parser.add_argument("--canali", action="store_true", help="List available channels")
    parser.add_argument("--prima-serata", "-p", action="store_true", help="Show prime time (20:00-23:00) on Rai 1/2/3")
    parser.add_argument("--cerca", "-s", metavar="TESTO", help="Search for a program by name")

    # Options
    parser.add_argument("--data", "-d", default="oggi", help="Date (oggi/domani/dd-mm-yyyy, default: oggi)")
    parser.add_argument("--dalle", metavar="HH:MM", help="Filter programs starting from time")
    parser.add_argument("--alle", metavar="HH:MM", help="Filter programs until time")
    parser.add_argument("--compatto", action="store_true", help="Compact output format")
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument("--tipo", "-t", metavar="TIPO", help="Filter by typology (Film, ProgrammiTv, SerieTV)")
    parser.add_argument("--genere", "-g", metavar="GENERE", help="Filter by genre (Commedia, Drammatico, AzioneAvventura, etc.)")

    args = parser.parse_args()

    # Execute command
    if args.ora:
        cmd_now(args)
    elif args.canali:
        cmd_channels(args)
    elif args.prima_serata:
        cmd_prime_time(args)
    elif args.cerca:
        cmd_search(args)
    elif args.canale:
        cmd_schedule(args)
    else:
        # Default: show what's on now
        cmd_now(args)


if __name__ == "__main__":
    main()
