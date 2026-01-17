#!/usr/bin/env python3
"""
JSONFix - Repair common errors in JSON files

Automatically fixes:
- Double or multiple commas (,,)
- Trailing commas before ] or }
- Single quotes instead of double quotes
- Unquoted object keys
- Comments (// and /* */)
- BOM (byte order mark)
- Control characters in strings
"""

import argparse
import json
import re
import sys
from pathlib import Path


class JSONFixer:
    """Class to repair JSON files with common errors."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.fixes_applied = []

    def log(self, message):
        """Log a fix if verbose mode is enabled."""
        self.fixes_applied.append(message)
        if self.verbose:
            print(f"  [FIX] {message}", file=sys.stderr)

    def fix_bom(self, content):
        """Remove BOM (Byte Order Mark) from the beginning."""
        if content.startswith('\ufeff'):
            self.log("Removed BOM (Byte Order Mark)")
            return content[1:]
        return content

    def fix_comments(self, content):
        """Remove JavaScript-style comments."""
        original = content

        # Remove single-line comments (// ...)
        # Be careful not to remove // inside strings
        result = []
        in_string = False
        escape_next = False
        i = 0

        while i < len(content):
            char = content[i]

            if escape_next:
                result.append(char)
                escape_next = False
                i += 1
                continue

            if char == '\\' and in_string:
                escape_next = True
                result.append(char)
                i += 1
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                result.append(char)
                i += 1
                continue

            if not in_string and char == '/' and i + 1 < len(content):
                next_char = content[i + 1]
                if next_char == '/':
                    # Single-line comment - skip until newline
                    while i < len(content) and content[i] != '\n':
                        i += 1
                    continue
                elif next_char == '*':
                    # Multi-line comment - skip until */
                    i += 2
                    while i + 1 < len(content) and not (content[i] == '*' and content[i + 1] == '/'):
                        i += 1
                    i += 2  # Skip the */
                    continue

            result.append(char)
            i += 1

        content = ''.join(result)

        if content != original:
            self.log("Removed JavaScript-style comments")

        return content

    def fix_single_quotes(self, content):
        """Replace single quotes with double quotes for strings."""
        original = content

        # This is tricky - we need to handle cases like:
        # {'key': 'value'} -> {"key": "value"}
        # But not touch apostrophes inside already double-quoted strings

        result = []
        i = 0
        in_double_string = False
        in_single_string = False
        escape_next = False

        while i < len(content):
            char = content[i]

            if escape_next:
                result.append(char)
                escape_next = False
                i += 1
                continue

            if char == '\\':
                escape_next = True
                result.append(char)
                i += 1
                continue

            if char == '"' and not in_single_string:
                in_double_string = not in_double_string
                result.append(char)
                i += 1
                continue

            if char == "'" and not in_double_string:
                # Convert single quote to double quote
                in_single_string = not in_single_string
                result.append('"')
                i += 1
                continue

            result.append(char)
            i += 1

        content = ''.join(result)

        if content != original:
            self.log("Converted single quotes to double quotes")

        return content

    def fix_unquoted_keys(self, content):
        """Add quotes around unquoted object keys."""
        original = content

        # Match unquoted keys: { key: or , key:
        # This pattern looks for word characters followed by : that aren't in quotes
        pattern = r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)(\s*:)'

        def replacer(match):
            return f'{match.group(1)}"{match.group(2)}"{match.group(3)}'

        # Apply multiple times to catch nested cases
        for _ in range(5):
            new_content = re.sub(pattern, replacer, content)
            if new_content == content:
                break
            content = new_content

        if content != original:
            self.log("Added quotes to unquoted keys")

        return content

    def fix_trailing_commas(self, content):
        """Remove trailing commas before ] or }."""
        original = content

        # Remove trailing commas before ] or }
        # Handle whitespace and newlines between comma and bracket
        pattern = r',(\s*[\]\}])'

        count = 0
        while True:
            new_content = re.sub(pattern, r'\1', content)
            if new_content == content:
                break
            count += 1
            content = new_content

        if count > 0:
            self.log(f"Removed {count} trailing comma(s)")

        return content

    def fix_multiple_commas(self, content):
        """Fix multiple consecutive commas (with optional whitespace between)."""
        original = content

        # Match multiple commas with whitespace between them
        pattern = r',(\s*,)+'

        count = 0
        while True:
            matches = list(re.finditer(pattern, content))
            if not matches:
                break
            count += len(matches)
            content = re.sub(pattern, ',', content)

        if count > 0:
            self.log(f"Fixed {count} sequence(s) of multiple commas")

        return content

    def fix_leading_commas(self, content):
        """Remove leading commas after [ or {."""
        original = content

        # Remove commas right after [ or {
        pattern = r'([\[\{]\s*),+'

        count = 0
        while True:
            new_content = re.sub(pattern, r'\1', content)
            if new_content == content:
                break
            count += 1
            content = new_content

        if count > 0:
            self.log(f"Removed {count} leading comma(s)")

        return content

    def fix_control_characters(self, content):
        """Remove or escape control characters in strings."""
        original = content

        # Replace common problematic control characters
        replacements = {
            '\t': '\\t',  # Tab (often already OK, but let's be safe)
            '\r': '',      # Carriage return - remove
            '\x00': '',    # Null byte - remove
            '\x1f': '',    # Unit separator - remove
        }

        for char, replacement in replacements.items():
            if char in content:
                content = content.replace(char, replacement)

        # Remove other control characters (except \n which is often fine)
        control_pattern = r'[\x00-\x08\x0b\x0c\x0e-\x1f]'
        content = re.sub(control_pattern, '', content)

        if content != original:
            self.log("Removed control characters")

        return content

    def fix_infinity_nan(self, content):
        """Replace JavaScript Infinity and NaN with null."""
        original = content

        # Replace Infinity and NaN (which are valid JS but not JSON)
        content = re.sub(r'\bInfinity\b', 'null', content)
        content = re.sub(r'\bNaN\b', 'null', content)
        content = re.sub(r'\bundefined\b', 'null', content)

        if content != original:
            self.log("Replaced Infinity/NaN/undefined with null")

        return content

    def fix_all(self, content):
        """Apply all fixes in the correct order."""
        self.fixes_applied = []

        # Order matters! Apply fixes from least to most aggressive
        content = self.fix_bom(content)
        content = self.fix_comments(content)
        content = self.fix_control_characters(content)
        content = self.fix_infinity_nan(content)
        content = self.fix_single_quotes(content)
        content = self.fix_unquoted_keys(content)
        content = self.fix_multiple_commas(content)
        content = self.fix_leading_commas(content)
        content = self.fix_trailing_commas(content)

        return content

    def validate(self, content):
        """Try to parse the JSON and return (success, error_message)."""
        try:
            json.loads(content)
            return True, None
        except json.JSONDecodeError as e:
            return False, str(e)

    def fix_and_validate(self, content):
        """Fix the content and validate it. Returns (fixed_content, success, message)."""
        # First, check if it's already valid
        valid, error = self.validate(content)
        if valid:
            return content, True, "JSON is already valid"

        # Apply fixes
        fixed = self.fix_all(content)

        # Validate again
        valid, error = self.validate(fixed)
        if valid:
            return fixed, True, f"JSON repaired successfully ({len(self.fixes_applied)} fix(es) applied)"
        else:
            return fixed, False, f"Could not fully repair JSON: {error}"


def main():
    parser = argparse.ArgumentParser(
        description='JSONFix - Repair common errors in JSON files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Errors fixed automatically:
  - Double or multiple commas (,,)
  - Trailing commas before ] or }
  - Single quotes instead of double quotes
  - Unquoted object keys
  - Comments (// and /* */)
  - BOM (byte order mark)
  - Control characters
  - Infinity, NaN, undefined

Examples:
  %(prog)s file.json                    # Print fixed JSON to stdout
  %(prog)s file.json -o fixed.json      # Save to a new file
  %(prog)s file.json --inplace          # Modify the original file
  %(prog)s file.json --check            # Validate only, no modifications
  %(prog)s file.json --pretty           # Format the output
        """
    )

    parser.add_argument('file', help='JSON file to repair')
    parser.add_argument('-o', '--output', metavar='FILE',
                        help='Output file (default: stdout)')
    parser.add_argument('--inplace', '-i', action='store_true',
                        help='Modify the original file')
    parser.add_argument('--check', '-c', action='store_true',
                        help='Validate only, do not modify')
    parser.add_argument('--pretty', '-p', action='store_true',
                        help='Format the JSON output')
    parser.add_argument('--indent', type=int, default=2,
                        help='Indentation for --pretty (default: 2)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show details of each fix')
    parser.add_argument('--quiet', '-q', action='store_true',
                        help='Suppress status messages')

    args = parser.parse_args()

    # Read input file
    input_path = Path(args.file)
    if not input_path.exists():
        print(f"Error: File not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    try:
        content = input_path.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        # Try with latin-1 as fallback
        try:
            content = input_path.read_text(encoding='latin-1')
        except Exception as e:
            print(f"Error reading file: {e}", file=sys.stderr)
            sys.exit(1)

    # Fix the JSON
    fixer = JSONFixer(verbose=args.verbose)
    fixed_content, success, message = fixer.fix_and_validate(content)

    # Report status
    if not args.quiet:
        status_icon = "+" if success else "!"
        print(f"[{status_icon}] {message}", file=sys.stderr)

        if fixer.fixes_applied and not args.verbose:
            print(f"  Fixes applied:", file=sys.stderr)
            for fix in fixer.fixes_applied:
                print(f"    - {fix}", file=sys.stderr)

    # Handle --check mode
    if args.check:
        sys.exit(0 if success else 1)

    if not success:
        print("Warning: JSON may not be fully valid", file=sys.stderr)

    # Format if requested
    if args.pretty and success:
        try:
            data = json.loads(fixed_content)
            fixed_content = json.dumps(data, indent=args.indent, ensure_ascii=False)
        except json.JSONDecodeError:
            pass  # Keep the fixed but unparseable content

    # Output
    if args.inplace:
        input_path.write_text(fixed_content, encoding='utf-8')
        if not args.quiet:
            print(f"File modified: {args.file}", file=sys.stderr)
    elif args.output:
        output_path = Path(args.output)
        output_path.write_text(fixed_content, encoding='utf-8')
        if not args.quiet:
            print(f"Saved to: {args.output}", file=sys.stderr)
    else:
        print(fixed_content)


if __name__ == '__main__':
    main()
