"""Command handlers for TroveRAI CLI."""

import sys
from datetime import datetime

from .api import fetch_channels, fetch_schedule
from .output import (
    COLOR_BOLD,
    COLOR_CYAN_BOLD,
    COLOR_ITALIC,
    COLOR_RESET,
    COLOR_YELLOW_BOLD,
    output_json,
    print_program,
)
from .utils import (
    filter_by_dfp,
    find_current_program,
    format_duration,
    normalize_channel,
    parse_date,
)


def cmd_schedule(args):
    """Show schedule for a channel."""
    channel = normalize_channel(args.canale)
    date = parse_date(args.data)

    if not args.json:
        print(f"{COLOR_CYAN_BOLD}=== {args.canale.upper()} - {date} ==={COLOR_RESET}\n")

    data = fetch_schedule(channel, date)

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
            print_program(
                event,
                show_current=(date == datetime.now().strftime("%d-%m-%Y")),
                compact=args.compatto,
            )

    if not events:
        print("No programs found for the specified time range.")


def cmd_now(args):
    """Show what's currently on air (or schedule for specified date)."""
    date = parse_date(args.data)
    is_today = date == datetime.now().strftime("%d-%m-%Y")

    # Main channels to check
    all_channels = [
        "rai-1",
        "rai-2",
        "rai-3",
        "rai-4",
        "rai-5",
        "rai-movie",
        "rai-premium",
        "rai-gulp",
        "rai-yoyo",
        "rai-storia",
        "rai-scuola",
        "rai-news-24",
        "rai-sport",
    ]

    # Filter by channel if specified
    if args.canale:
        filter_channel = normalize_channel(args.canale)
        all_channels = [c for c in all_channels if filter_channel in c]

    # Collect data for JSON output
    json_data = {}

    if not args.json:
        if is_today:
            print(
                f"{COLOR_CYAN_BOLD}=== Ora in onda - {datetime.now().strftime('%H:%M')} ==={COLOR_RESET}\n"
            )
        else:
            print(f"{COLOR_CYAN_BOLD}=== Palinsesto - {date} ==={COLOR_RESET}\n")

    for channel in all_channels:
        data = fetch_schedule(channel, date)

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
                        print(
                            f"  {time} - {COLOR_BOLD}{name}{COLOR_RESET} ({duration})"
                        )
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
    data = fetch_channels()

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
    date = parse_date(args.data)
    main_channels = ["rai-1", "rai-2", "rai-3"]

    # Collect raw data for JSON output
    json_data = {}

    if not args.json:
        print(f"{COLOR_CYAN_BOLD}=== Prima Serata - {date} ==={COLOR_RESET}\n")

    for channel in main_channels:
        data = fetch_schedule(channel, date)

        if not data:
            continue

        if args.json:
            json_data[channel] = data

        channel_name = data.get("channel", channel)
        events = data.get("events", [])

        # Filter for prime time (20:00 - 23:59)
        prime_events = [
            e for e in events if e and "20:" <= e.get("hour", "00:00") <= "23:59"
        ]

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
    date = parse_date(args.data)
    search_term = args.cerca.lower()

    channels = [
        "rai-1",
        "rai-2",
        "rai-3",
        "rai-4",
        "rai-5",
        "rai-movie",
        "rai-premium",
        "rai-storia",
    ]

    # Collect raw programs for JSON output
    json_programs = []

    if not args.json:
        print(
            f"{COLOR_CYAN_BOLD}=== Ricerca: '{args.cerca}' - {date} ==={COLOR_RESET}\n"
        )

    found = False

    for channel in channels:
        data = fetch_schedule(channel, date)

        if not data:
            continue

        channel_name = data.get("channel", channel)
        events = data.get("events", [])

        # Filter by name
        matching = [
            e for e in events if e and search_term in e.get("name", "").lower()
        ]

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
