"""
TroveRAI CLI - TV Schedule viewer for RaiPlay

Fetches and displays TV schedules from RaiPlay.
"""

import argparse

from .commands import cmd_channels, cmd_now, cmd_prime_time, cmd_schedule, cmd_search


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
    parser.add_argument(
        "--ora", "-o", action="store_true", help="Show what's currently on air"
    )
    parser.add_argument(
        "--canale", "-c", metavar="NOME", help="Show schedule for a specific channel"
    )
    parser.add_argument(
        "--canali", action="store_true", help="List available channels"
    )
    parser.add_argument(
        "--prima-serata",
        "-p",
        action="store_true",
        help="Show prime time (20:00-23:00) on Rai 1/2/3",
    )
    parser.add_argument(
        "--cerca", "-s", metavar="TESTO", help="Search for a program by name"
    )

    # Options
    parser.add_argument(
        "--data",
        "-d",
        default=None,
        help="Date (oggi/domani/dd-mm-yyyy, default: oggi)",
    )
    parser.add_argument(
        "--dalle", metavar="HH:MM", help="Filter programs starting from time"
    )
    parser.add_argument("--alle", metavar="HH:MM", help="Filter programs until time")
    parser.add_argument(
        "--compatto", action="store_true", help="Compact output format"
    )
    parser.add_argument("--json", action="store_true", help="Output in JSON format")
    parser.add_argument(
        "--tipo",
        "-t",
        metavar="TIPO",
        help="Filter by typology (Film, ProgrammiTv, SerieTV)",
    )
    parser.add_argument(
        "--genere",
        "-g",
        metavar="GENERE",
        help="Filter by genre (Commedia, Drammatico, AzioneAvventura, etc.)",
    )

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
