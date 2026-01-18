# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TroveRAI is a CLI tool to fetch and display TV schedules from RaiPlay (Italian public TV streaming service). The name is a pun in Italian meaning both "You will find it" and containing "RAI".

## Commands

```bash
# Install dependencies
poetry install

# Run the CLI
poetry run troverai --ora              # What's on air now
poetry run troverai --canale rai-1     # Today's schedule for Rai 1
poetry run troverai --prima-serata     # Prime time on main channels
poetry run troverai --cerca "film"     # Search for programs

# Filter by typology and genre
poetry run troverai --canale rai-movie --tipo Film          # Only films
poetry run troverai --canale rai-movie --genere Commedia    # Only comedies
poetry run troverai --ora --tipo Film                       # Films on air now

# Run as module
poetry run python -m troverai --help

# Disable colors
NO_COLOR=1 poetry run troverai --ora
```

## Architecture

### Source Layout
Uses PEP-compliant `src/` layout:
- `src/troverai/cli.py` - Main CLI implementation with all commands
- `src/troverai/__main__.py` - Entry point for `python -m troverai`
- `src/troverai/__init__.py` - Package metadata

### SperimenteRAI/
Development experiments folder (not part of the main package). Contains:
- `raiplay_auth.py` - Authentication helper for RaiPlay account features
- `raiplay.py` - RaiPlay catalog query tool
- `jsonfix.py` - JSON repair utility

Note: The main CLI does not require authentication. The palinsesto APIs are public.

## Conventions

### Git Workflow
- **FORBIDDEN**: Never push directly to `main` branch. Always open a pull request.
- **Branch names**: Must follow [Conventional Branch](https://conventional-branch.github.io) naming (e.g., `feat/add-json-output`, `fix/token-refresh`, `docs/update-readme`).
- **Commit messages**: Must follow [Conventional Commits](https://www.conventionalcommits.org/) (e.g., `feat:`, `fix:`, `docs:`, `refactor:`).
- **Pull request titles**: Must start with conventional commit prefix (e.g., `feat: add JSON output`, `fix: token refresh error`).
- **PR merging**: Claude must NEVER ask to merge a pull request. All PRs will be reviewed and merged by a human on GitHub.

### Sensitive Files
JSON files containing tokens/cache (used by experimental scripts in SperimenteRAI/) should be prefixed with `rai` (e.g., `raiplay_tokens.json`) - these are gitignored via `rai*.json` pattern.

### Colors
Respect `NO_COLOR` environment variable. Use the color constants defined in `cli.py` (`COLOR_BOLD`, `COLOR_RESET`, etc.) instead of hardcoded ANSI codes.
