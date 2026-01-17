"""
TroveRAI CLI - TV Schedule viewer for RaiPlay

Fetches and displays TV schedules from RaiPlay.
Requires authentication (run raiplay_auth.py --login first).
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

# Constants
# Token file is expected in current working directory
TOKEN_FILE = Path.cwd() / "raiplay_tokens.json"
PALINSESTO_URL = "https://www.raiplay.it/palinsesto/app/old"
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


def load_tokens():
    """Load authentication tokens from file."""
    if not TOKEN_FILE.exists():
        print("Error: Not authenticated. Run 'raiplay_auth.py --login' first.", file=sys.stderr)
        sys.exit(1)

    with open(TOKEN_FILE) as f:
        return json.load(f)


def get_session():
    """Create an authenticated requests session."""
    tokens = load_tokens()

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {tokens['jwt_token']}",
        "Accept": "application/json"
    })
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
        h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
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


def print_program(prog, show_current=True, compact=False):
    """Print a single program entry."""
    time = prog.get("timePublished", "??:??")
    duration = prog.get("duration", "")
    name = prog.get("name", "")

    # Get name from isPartOf if not directly available
    if not name:
        is_part_of = prog.get("isPartOf", {})
        name = is_part_of.get("name", "Unknown")

    # Check if current
    is_current = is_current_program(time, duration) if show_current else False

    # Format output
    duration_fmt = format_duration(duration)

    if compact:
        marker = ">" if is_current else " "
        print(f"{marker} {time} {name}")
    else:
        marker = "\033[1;32m>>>\033[0m" if is_current else "   "
        name_fmt = f"\033[1m{name}\033[0m" if is_current else name

        if duration_fmt:
            print(f"{marker} {time} - {name_fmt} ({duration_fmt})")
        else:
            print(f"{marker} {time} - {name_fmt}")

        # Show subtitle/description for current program
        if is_current and not compact:
            subtitle = prog.get("subtitle", "")
            if not subtitle:
                is_part_of = prog.get("isPartOf", {})
                subtitle = is_part_of.get("description", "")

            if subtitle:
                # Truncate long descriptions
                if len(subtitle) > 100:
                    subtitle = subtitle[:97] + "..."
                print(f"       \033[3m{subtitle}\033[0m")


def cmd_schedule(args):
    """Show schedule for a channel."""
    session = get_session()

    channel = normalize_channel(args.canale)
    date = parse_date(args.data)

    print(f"\033[1;36m=== {args.canale.upper()} - {date} ===\033[0m\n")

    data = fetch_schedule(session, channel, date)

    if not data:
        print("No schedule data available.")
        return

    # Parse the nested structure
    for channel_name, channel_data in data.items():
        for day_data in channel_data:
            for palinsesto in day_data.get("palinsesto", []):
                programs = palinsesto.get("programmi", [])

                # Filter by time range if specified
                if args.dalle or args.alle:
                    filtered = []
                    for prog in programs:
                        time = prog.get("timePublished", "00:00")
                        if args.dalle and time < args.dalle:
                            continue
                        if args.alle and time > args.alle:
                            continue
                        filtered.append(prog)
                    programs = filtered

                # Show programs
                for prog in programs:
                    if prog:  # Skip empty entries
                        print_program(prog, show_current=(date == datetime.now().strftime("%d-%m-%Y")),
                                     compact=args.compatto)

                if not programs:
                    print("No programs found for the specified time range.")


def cmd_now(args):
    """Show what's currently on air."""
    session = get_session()

    data = fetch_now_on_air(session)

    if not data:
        print("Error fetching current programs.", file=sys.stderr)
        return

    print(f"\033[1;36m=== Ora in onda - {datetime.now().strftime('%H:%M')} ===\033[0m\n")

    channels = data.get("dirette", [])

    # Filter by channel if specified
    if args.canale:
        filter_channel = args.canale.lower().replace("-", " ").replace("rai ", "rai")
        channels = [c for c in channels if filter_channel in c.get("channel", "").lower().replace(" ", "")]

    for channel in channels:
        channel_name = channel.get("channel", "Unknown")
        item = channel.get("currentItem", {})

        name = item.get("name", "")
        if not name:
            is_part_of = item.get("isPartOf", {})
            name = is_part_of.get("name", "Unknown")

        time = item.get("timePublished", "")

        if args.compatto:
            print(f"{channel_name}: {name}")
        else:
            print(f"\033[1;33m{channel_name}\033[0m")
            print(f"  {time} - \033[1m{name}\033[0m")

            # Show description
            description = item.get("isPartOf", {}).get("description", "")
            if description and not args.compatto:
                if len(description) > 120:
                    description = description[:117] + "..."
                print(f"  \033[3m{description}\033[0m")
            print()


def cmd_channels(args):
    """List available channels."""
    session = get_session()

    data = fetch_channels(session)

    if not data:
        print("Error fetching channels.", file=sys.stderr)
        return

    print("\033[1;36m=== Canali disponibili ===\033[0m\n")

    for channel in data.get("channels", []):
        label = channel.get("label", "")
        path = channel.get("absolute_path", "")
        print(f"  {label:20} (--canale {path})")


def cmd_prime_time(args):
    """Show prime time schedule (20:00-23:00) for main channels."""
    session = get_session()

    date = parse_date(args.data)
    main_channels = ["rai-1", "rai-2", "rai-3"]

    print(f"\033[1;36m=== Prima Serata - {date} ===\033[0m\n")

    for channel in main_channels:
        data = fetch_schedule(session, channel, date)

        if not data:
            continue

        for channel_name, channel_data in data.items():
            print(f"\033[1;33m{channel_name}\033[0m")

            for day_data in channel_data:
                for palinsesto in day_data.get("palinsesto", []):
                    programs = palinsesto.get("programmi", [])

                    # Filter for prime time (20:00 - 23:59)
                    for prog in programs:
                        if prog:
                            time = prog.get("timePublished", "00:00")
                            if "20:" <= time <= "23:59":
                                name = prog.get("name", "")
                                if not name:
                                    name = prog.get("isPartOf", {}).get("name", "Unknown")
                                duration = format_duration(prog.get("duration", ""))

                                print(f"  {time} - {name}", end="")
                                if duration:
                                    print(f" ({duration})")
                                else:
                                    print()
            print()


def cmd_search(args):
    """Search for a program in today's schedule."""
    session = get_session()

    date = parse_date(args.data)
    search_term = args.cerca.lower()

    channels = ["rai-1", "rai-2", "rai-3", "rai-4", "rai-5",
                "rai-movie", "rai-premium", "rai-storia"]

    print(f"\033[1;36m=== Ricerca: '{args.cerca}' - {date} ===\033[0m\n")

    found = False

    for channel in channels:
        data = fetch_schedule(session, channel, date)

        if not data:
            continue

        for channel_name, channel_data in data.items():
            for day_data in channel_data:
                for palinsesto in day_data.get("palinsesto", []):
                    programs = palinsesto.get("programmi", [])

                    for prog in programs:
                        if prog:
                            name = prog.get("name", "")
                            if not name:
                                name = prog.get("isPartOf", {}).get("name", "")

                            if search_term in name.lower():
                                time = prog.get("timePublished", "??:??")
                                duration = format_duration(prog.get("duration", ""))

                                print(f"\033[1;33m{channel_name}\033[0m - {time}")
                                print(f"  \033[1m{name}\033[0m", end="")
                                if duration:
                                    print(f" ({duration})")
                                else:
                                    print()
                                print()
                                found = True

    if not found:
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
        """
    )

    # Main commands
    parser.add_argument("--ora", "-o", action="store_true",
                        help="Show what's currently on air")
    parser.add_argument("--canale", "-c", metavar="NOME",
                        help="Show schedule for a specific channel")
    parser.add_argument("--canali", action="store_true",
                        help="List available channels")
    parser.add_argument("--prima-serata", "-p", action="store_true",
                        help="Show prime time (20:00-23:00) on Rai 1/2/3")
    parser.add_argument("--cerca", "-s", metavar="TESTO",
                        help="Search for a program by name")

    # Options
    parser.add_argument("--data", "-d", default="oggi",
                        help="Date (oggi/domani/dd-mm-yyyy, default: oggi)")
    parser.add_argument("--dalle", metavar="HH:MM",
                        help="Filter programs starting from time")
    parser.add_argument("--alle", metavar="HH:MM",
                        help="Filter programs until time")
    parser.add_argument("--compatto", action="store_true",
                        help="Compact output format")

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
