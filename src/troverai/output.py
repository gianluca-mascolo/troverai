"""Output formatting for TroveRAI."""

import json
import os

from .utils import format_duration, is_current_program

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


def output_json(data):
    """Print data as JSON."""
    print(json.dumps(data, ensure_ascii=False, indent=2))
