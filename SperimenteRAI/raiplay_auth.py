#!/usr/bin/env python3
"""
RaiPlay Authentication Helper

Authenticates to RaiPlay and provides tokens for API access.
Supports automatic token refresh when JWT expires.
"""

import argparse
import base64
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import requests

# Constants
CONFIG_URL = "https://www.raiplay.it/mobile/prod/config/RaiPlay_Config.json"
LOGIN_URL = "https://www.raiplay.it/raisso/login/domain/app/social"
# Refresh URL uses www.rai.it base (from raiSsoServicesNew.raiSsoBaseUrl)
DEFAULT_REFRESH_URL = "https://www.rai.it/raisso/user/token/refresh"

# File paths (relative to current working directory)
TOKEN_FILE = Path.cwd() / "raiplay_tokens.json"
CONFIG_CACHE_FILE = Path.cwd() / "raiplay_config_cache.json"
ENV_FILE = Path.cwd() / ".env"

# Config cache duration (1 day)
CONFIG_CACHE_DURATION = timedelta(days=1)

# Refresh token before it expires (5 minutes buffer)
TOKEN_REFRESH_BUFFER = timedelta(minutes=5)


def decode_jwt(token):
    """
    Decode a JWT token without verification.
    Returns the payload as a dict, or None if decoding fails.
    """
    try:
        # JWT format: header.payload.signature
        parts = token.split(".")
        if len(parts) != 3:
            return None

        # Decode payload (second part)
        payload = parts[1]

        # Add padding if needed (base64 requires padding to multiple of 4)
        padding = 4 - len(payload) % 4
        if padding != 4:
            payload += "=" * padding

        # Decode base64
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)

    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def get_token_expiry(jwt_token):
    """
    Get the expiration datetime from a JWT token.
    Returns None if token cannot be decoded or has no expiry.
    """
    payload = decode_jwt(jwt_token)
    if payload is None:
        return None

    exp = payload.get("exp")
    if exp is None:
        return None

    # exp is Unix timestamp
    return datetime.fromtimestamp(exp)


def is_token_expired(jwt_token, buffer=None):
    """
    Check if a JWT token is expired or about to expire.

    Args:
        jwt_token: The JWT token string
        buffer: Time buffer before actual expiry (default: TOKEN_REFRESH_BUFFER)

    Returns:
        True if token is expired or will expire within buffer time
    """
    if buffer is None:
        buffer = TOKEN_REFRESH_BUFFER

    expiry = get_token_expiry(jwt_token)
    if expiry is None:
        # Cannot determine expiry, assume not expired
        return False

    return datetime.now() >= (expiry - buffer)


def fetch_config(force_refresh=False):
    """
    Fetch RaiPlay config from remote or cache.

    The config contains API keys and endpoints that may change over time.
    We cache it locally to avoid fetching on every request.
    """
    # Check cache first (unless force refresh)
    if not force_refresh and CONFIG_CACHE_FILE.exists():
        try:
            with open(CONFIG_CACHE_FILE) as f:
                cache = json.load(f)

            # Check if cache is still valid
            cached_time = datetime.fromisoformat(cache.get("_cached_at", "2000-01-01"))
            if datetime.now() - cached_time < CONFIG_CACHE_DURATION:
                return cache.get("config")
        except (json.JSONDecodeError, ValueError, KeyError):
            pass  # Cache invalid, fetch fresh

    # Fetch from remote
    try:
        response = requests.get(CONFIG_URL, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }, timeout=10)

        if response.status_code != 200:
            print(f"Warning: Failed to fetch config (HTTP {response.status_code})", file=sys.stderr)
            return None

        config = response.json()

        # Cache the config
        cache = {
            "_cached_at": datetime.now().isoformat(),
            "_source": CONFIG_URL,
            "config": config
        }
        with open(CONFIG_CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)

        return config

    except requests.RequestException as e:
        print(f"Warning: Failed to fetch config: {e}", file=sys.stderr)
        return None


def get_domain_api_key(config=None):
    """Extract the domain API key from config."""
    if config is None:
        config = fetch_config()

    if config is None:
        print("Error: Could not fetch RaiPlay config", file=sys.stderr)
        sys.exit(1)

    # Try multiple known paths for the domain API key
    paths = [
        ["userServices", "raiPlayServicesNew", "raiPlayDomainApiKey"],
        ["userServices", "raiPlayServices", "raiPlayDomainApiKey"],
        ["gigya", "raiPlayDomainApiKey"],
    ]

    for path in paths:
        try:
            value = config
            for key in path:
                value = value[key]
            return value
        except (KeyError, TypeError):
            continue

    print("Error: raiPlayDomainApiKey not found in config", file=sys.stderr)
    print("Config structure may have changed. Try --config --refresh", file=sys.stderr)
    sys.exit(1)


def load_credentials():
    """Load credentials from .env file."""
    if not ENV_FILE.exists():
        print(f"Error: {ENV_FILE} not found", file=sys.stderr)
        sys.exit(1)

    credentials = {}
    with open(ENV_FILE) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                # Remove quotes
                value = value.strip().strip('"').strip("'")
                credentials[key] = value

    return credentials.get("RAIPLAY_USERNAME"), credentials.get("RAIPLAY_PASSWORD")


def login(username, password):
    """Authenticate to RaiPlay and return tokens."""
    # Get domain API key from config
    domain_api_key = get_domain_api_key()

    response = requests.post(
        LOGIN_URL,
        data={
            "email": username,
            "password": password,
            "domainApiKey": domain_api_key
        },
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    )

    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}", file=sys.stderr)
        print(response.text, file=sys.stderr)
        return None

    data = response.json()

    if data.get("response") != "OK":
        print(f"Error: {data}", file=sys.stderr)
        return None

    return {
        "jwt_token": data.get("authorization"),
        "refresh_token": data.get("refreshToken"),
        "ua": data.get("ua"),
        "uid": data["raisso"]["uid"],
        "email": data["raisso"]["email"],
        "first_name": data["raisso"]["firstName"],
        "last_name": data["raisso"]["lastName"],
        "login_time": datetime.now().isoformat()
    }


def get_refresh_url(config=None):
    """Get the refresh token URL from config."""
    if config is None:
        config = fetch_config()

    if config is None:
        return DEFAULT_REFRESH_URL

    # Get base URL and path from config
    try:
        sso_services = config.get("userServices", {}).get("raiSsoServicesNew", {})
        base_url = sso_services.get("raiSsoBaseUrl", "https://www.rai.it")
        refresh_path = sso_services.get("raiSsoRefreshToken", "/raisso/user/token/refresh")
        return f"{base_url}{refresh_path}"
    except (KeyError, TypeError):
        return DEFAULT_REFRESH_URL


def refresh_token(tokens):
    """
    Refresh the JWT token using the refresh token.

    Args:
        tokens: Dict containing jwt_token and refresh_token

    Returns:
        Updated tokens dict, or None if refresh failed
    """
    if not tokens or not tokens.get("refresh_token"):
        print("Error: No refresh token available", file=sys.stderr)
        return None

    refresh_url = get_refresh_url()
    domain_api_key = get_domain_api_key()

    try:
        # Send refresh request with refresh token and domain API key
        response = requests.post(
            refresh_url,
            data={
                "refreshToken": tokens["refresh_token"],
                "domainApiKey": domain_api_key
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Authorization": f"Bearer {tokens['jwt_token']}",
                "Content-Type": "application/x-www-form-urlencoded"
            }
        )

        if response.status_code != 200:
            # Debug: show response body for troubleshooting
            print(f"Error refreshing token: HTTP {response.status_code}", file=sys.stderr)
            try:
                error_detail = response.json()
                print(f"Server response: {error_detail}", file=sys.stderr)
            except json.JSONDecodeError:
                if response.text:
                    print(f"Server response: {response.text[:200]}", file=sys.stderr)
            return None

        # Try to parse JSON response
        try:
            data = response.json()

            if data.get("response") != "OK" and "authorization" not in data:
                print(f"Error refreshing token: {data}", file=sys.stderr)
                return None

            # Update tokens with new values from JSON
            tokens["jwt_token"] = data.get("authorization", tokens["jwt_token"])
            if data.get("refreshToken"):
                tokens["refresh_token"] = data["refreshToken"]

        except json.JSONDecodeError:
            # Response is the JWT token directly (plain text, not JSON)
            new_token = response.text.strip()

            # Verify it looks like a JWT (three base64 parts separated by dots)
            if new_token.count(".") == 2 and new_token.startswith("eyJ"):
                tokens["jwt_token"] = new_token
            else:
                print(f"Invalid refresh response: {response.text[:100]}", file=sys.stderr)
                return None

        tokens["last_refresh"] = datetime.now().isoformat()
        return tokens

    except requests.RequestException as e:
        print(f"Error refreshing token: {e}", file=sys.stderr)
        return None


def save_tokens(tokens, quiet=False):
    """Save tokens to file."""
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)
    if not quiet:
        print(f"Tokens saved to {TOKEN_FILE}")


def load_tokens():
    """Load tokens from file."""
    if not TOKEN_FILE.exists():
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f)


def ensure_valid_token(tokens=None, auto_refresh=True):
    """
    Ensure we have a valid (non-expired) token.

    Args:
        tokens: Token dict, or None to load from file
        auto_refresh: If True, automatically refresh expired tokens

    Returns:
        Valid tokens dict, or None if unable to get valid tokens
    """
    if tokens is None:
        tokens = load_tokens()

    if tokens is None:
        return None

    jwt_token = tokens.get("jwt_token")
    if not jwt_token:
        return None

    # Check if token is expired
    if is_token_expired(jwt_token):
        if not auto_refresh:
            return None

        print("Token expired, refreshing...", file=sys.stderr)
        refreshed = refresh_token(tokens)

        if refreshed:
            save_tokens(refreshed, quiet=True)
            print("Token refreshed successfully", file=sys.stderr)
            return refreshed
        else:
            print("Token refresh failed. Please login again with --login", file=sys.stderr)
            return None

    return tokens


def get_auth_session(tokens=None, auto_refresh=True):
    """
    Create an authenticated requests session.

    Automatically refreshes the token if expired.
    """
    tokens = ensure_valid_token(tokens, auto_refresh=auto_refresh)

    if tokens is None:
        print("Error: No valid tokens available. Run with --login first.", file=sys.stderr)
        sys.exit(1)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Authorization": f"Bearer {tokens['jwt_token']}",
        "Accept": "application/json"
    })
    return session


def cmd_login(args):
    """Perform login and save tokens."""
    username, password = load_credentials()

    if not username or not password:
        print("Error: RAIPLAY_USERNAME and RAIPLAY_PASSWORD must be set in .env", file=sys.stderr)
        sys.exit(1)

    print(f"Logging in as {username}...")
    tokens = login(username, password)

    if tokens:
        print(f"Success! Logged in as {tokens['first_name']} {tokens['last_name']}")

        # Show token expiry
        expiry = get_token_expiry(tokens["jwt_token"])
        if expiry:
            print(f"Token expires: {expiry.strftime('%Y-%m-%d %H:%M:%S')}")

        save_tokens(tokens)
        return tokens
    else:
        print("Login failed!", file=sys.stderr)
        sys.exit(1)


def cmd_refresh(args):
    """Refresh the JWT token."""
    tokens = load_tokens()

    if tokens is None:
        print("Error: Not logged in. Run with --login first.", file=sys.stderr)
        sys.exit(1)

    print("Refreshing token...")
    refreshed = refresh_token(tokens)

    if refreshed:
        print("Token refreshed successfully!")

        # Show new expiry
        expiry = get_token_expiry(refreshed["jwt_token"])
        if expiry:
            print(f"New token expires: {expiry.strftime('%Y-%m-%d %H:%M:%S')}")

        save_tokens(refreshed)
    else:
        print("Token refresh failed. Please login again with --login", file=sys.stderr)
        sys.exit(1)


def cmd_status(args):
    """Show current authentication status."""
    tokens = load_tokens()

    if tokens is None:
        print("Not logged in. Run with --login to authenticate.")
        return

    print(f"Logged in as: {tokens.get('first_name', '?')} {tokens.get('last_name', '?')}")
    print(f"Email: {tokens.get('email', '?')}")
    print(f"UID: {tokens.get('uid', '?')}")
    print(f"Login time: {tokens.get('login_time', '?')}")

    # Token expiry info
    jwt_token = tokens.get("jwt_token")
    if jwt_token:
        expiry = get_token_expiry(jwt_token)
        if expiry:
            now = datetime.now()
            if expiry > now:
                remaining = expiry - now
                hours, remainder = divmod(int(remaining.total_seconds()), 3600)
                minutes, seconds = divmod(remainder, 60)
                print(f"Token expires: {expiry.strftime('%Y-%m-%d %H:%M:%S')} ({hours}h {minutes}m remaining)")
            else:
                print(f"Token expired: {expiry.strftime('%Y-%m-%d %H:%M:%S')} (EXPIRED)")
        else:
            print("Token expiry: Unknown")

    if tokens.get("last_refresh"):
        print(f"Last refresh: {tokens.get('last_refresh')}")

    print(f"Token file: {TOKEN_FILE}")


def cmd_token(args):
    """Print the JWT token for use with curl."""
    # Use ensure_valid_token to auto-refresh if needed
    tokens = ensure_valid_token(auto_refresh=True)

    if tokens is None:
        print("Error: Not logged in. Run with --login first.", file=sys.stderr)
        sys.exit(1)

    if args.export:
        print(f"export RAIPLAY_TOKEN='{tokens['jwt_token']}'")
    else:
        print(tokens['jwt_token'])


def cmd_test(args):
    """Test authentication by fetching current schedule."""
    session = get_auth_session()

    print("Testing authentication...")
    response = session.get("https://www.raiplay.it/dl/palinsesti/oraInOnda.json")

    if response.status_code == 200:
        data = response.json()
        print(f"Success! Found {len(data.get('dirette', []))} channels currently on air.")

        # Show what's on Rai 1
        for channel in data.get("dirette", []):
            if channel.get("channel") == "Rai 1":
                item = channel.get("currentItem", {})
                name = item.get("name", item.get("isPartOf", {}).get("name", "Unknown"))
                print(f"\nRai 1 now playing: {name}")
                break
    else:
        print(f"Error: HTTP {response.status_code}", file=sys.stderr)
        sys.exit(1)


def cmd_config(args):
    """Show or refresh the RaiPlay config."""
    config = fetch_config(force_refresh=args.refresh)

    if config is None:
        print("Error: Could not fetch config", file=sys.stderr)
        sys.exit(1)

    # Show relevant config values
    print("RaiPlay Configuration:")
    print(f"  Source: {CONFIG_URL}")

    if CONFIG_CACHE_FILE.exists():
        with open(CONFIG_CACHE_FILE) as f:
            cache = json.load(f)
        print(f"  Cached at: {cache.get('_cached_at', 'unknown')}")
        print(f"  Cache file: {CONFIG_CACHE_FILE}")

    # Get user services section
    user_services = config.get("userServices", {})
    raiplay_services = user_services.get("raiPlayServicesNew", {})
    gigya = user_services.get("gigya", {})

    print()
    print("Authentication Keys:")
    print(f"  Domain API Key: {raiplay_services.get('raiPlayDomainApiKey', 'NOT FOUND')}")
    print(f"  Gigya API Key: {gigya.get('raiPlayApiKey', 'NOT FOUND')[:50]}...")
    print(f"  Data Server: {gigya.get('dataServer', 'NOT FOUND')}")

    print()
    print("SSO Endpoints:")
    sso = user_services.get("raiSsoServicesNew", {})
    sso_base = sso.get('raiSsoBaseUrl', 'NOT FOUND')
    print(f"  Base URL: {sso_base}")
    print(f"  Login: {raiplay_services.get('raiPlayLogin', 'NOT FOUND')}")
    print(f"  Logout: {sso.get('raiSsoLogOut', 'NOT FOUND')}")
    refresh_path = sso.get('raiSsoRefreshToken', 'NOT FOUND')
    print(f"  Refresh Token: {refresh_path}")
    if sso_base != 'NOT FOUND' and refresh_path != 'NOT FOUND':
        print(f"  Refresh URL: {sso_base}{refresh_path}")


def main():
    parser = argparse.ArgumentParser(
        description="RaiPlay Authentication Helper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --login              # Authenticate and save tokens
  %(prog)s --status             # Show current login status and token expiry
  %(prog)s --token              # Print JWT token (auto-refreshes if expired)
  %(prog)s --token --export     # Print as export command for shell
  %(prog)s --refresh-token      # Manually refresh the JWT token
  %(prog)s --test               # Test authentication
  %(prog)s --config             # Show current config
  %(prog)s --config --refresh   # Force refresh config from server

Using with curl:
  export RAIPLAY_TOKEN=$(%(prog)s --token)
  curl -H "Authorization: Bearer $RAIPLAY_TOKEN" \\
    "https://www.raiplay.it/palinsesto/app/old/rai-1/17-01-2026.json"

Token auto-refresh:
  The JWT token is automatically refreshed when expired:
  - When using --token
  - When using get_auth_session() in Python
        """
    )

    parser.add_argument("--login", "-l", action="store_true",
                        help="Perform login and save tokens")
    parser.add_argument("--status", "-s", action="store_true",
                        help="Show current authentication status and token expiry")
    parser.add_argument("--token", "-t", action="store_true",
                        help="Print the JWT token (auto-refreshes if expired)")
    parser.add_argument("--export", "-e", action="store_true",
                        help="Print token as export command")
    parser.add_argument("--refresh-token", action="store_true",
                        help="Manually refresh the JWT token")
    parser.add_argument("--test", action="store_true",
                        help="Test authentication")
    parser.add_argument("--config", "-c", action="store_true",
                        help="Show RaiPlay configuration")
    parser.add_argument("--refresh", "-r", action="store_true",
                        help="Force refresh config from server (use with --config)")

    args = parser.parse_args()

    if args.login:
        cmd_login(args)
    elif args.refresh_token:
        cmd_refresh(args)
    elif args.status:
        cmd_status(args)
    elif args.token:
        cmd_token(args)
    elif args.test:
        cmd_test(args)
    elif args.config:
        cmd_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
