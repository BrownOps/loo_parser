# Loo Parser

[![Test & Lint](https://github.com/brownops/loo_parser/actions/workflows/test.yml/badge.svg)](https://github.com/brownops/loo_parser/actions/workflows/test.yml)

A Python tool for parsing WhatsApp chat exports to track and analyze bathroom usage patterns through specific emoji-based messages.

## Overview

Loo Parser processes WhatsApp chat logs to extract, track, and analyze messages containing 💩 and 🚽 emojis according to a specific syntax. It helps keep track of bathroom usage over time by different chat participants, including timing and frequency analysis.

## Features

- Parse WhatsApp chat exports (.txt format)
- Recognize multiple message formats for tracking events:
  - Live events (happening now): `💩`
  - Past events (specific time): `💩 YYYY-MM-DD HH:MM`
  - Events with time shift: `💩 +N` or `💩 -N`
  - Setting default time shift: `🚽 +N` or `🚽 -N`
- Track per-user bathroom usage patterns
- Detect and alert on unusual timing patterns
- Export structured data as JSON for further analysis

## Installation

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) - Rust-based, fast virtual environment and package manager

### Setup

1.  Clone the repository:
    ```bash
    git clone <repository-url>
    cd loo_parser
    ```
2.  Create and activate a virtual environment with uv:

    ```bash
    # Create a virtual environment
    uv venv

    # Activate it
    source .venv/bin/activate  # On Linux/macOS
    # .venv\Scripts\activate    # On Windows
    ```

3.  Install the package in development mode:

    ```bash
    # Install dependencies much faster than pip
    uv pip install -e .

    # For development with testing tools
    uv pip install -e ".[dev]"         # In bash
    uv pip install -e ".\[dev\]"       # In zsh (escape the brackets)
    ```

## Usage

After installation, you can run the parser from your command line:

```bash
loo-parser [INPUT_FILE] [OUTPUT_FILE]
```

For example, using the provided sample file:

```bash
loo-parser whatsapp_chat_example.txt example_results.json
```

This will parse the `whatsapp_chat_example.txt` file and save the extracted poop events to `example_results.json`.

If no files are specified, it will default to `whatsapp_chat.txt` for input and `poop_results.json` for output.

### Message Format Examples

The parser recognizes the following message formats:

```
[DD/MM/YY, HH:MM:SS] Alice: 💩                         # Current poop event
[DD/MM/YY, HH:MM:SS] Bob: 💩 2023-04-15 08:30          # Past poop event
[DD/MM/YY, HH:MM:SS] Charlie: 💩 +2                    # Current poop with +2 shift
[DD/MM/YY, HH:MM:SS] Dave: 💩 -1 2023-04-10 19:45      # Past poop with -1 shift
[DD/MM/YY, HH:MM:SS] Eve: 🚽 +3                        # Set default shift to +3
```

### Output Format

The parser outputs JSON data in the following format:

```json
[
  {
    "sender": "Alice",
    "message_timestamp": "2023-05-01T10:05:00",
    "original_message": "💩",
    "type": "poop_live",
    "shift": 0,
    "poop_time": "2023-05-01T10:05:00",
    "status": "ok"
  },
  {
    "sender": "Bob",
    "message_timestamp": "2023-05-01T10:07:00",
    "original_message": "💩 2023-04-30 09:00",
    "type": "poop_past",
    "shift": 0,
    "poop_time": "2023-04-30T09:00:00",
    "status": "ok"
  }
]
```

Status values can be:

- `ok`: Normal event
- `alert`: Event with unusual timing (>30 days gap)
- `error`: Invalid format or parsing error

## Development

This project uses modern Python development tools for a better developer experience:

1.  **Virtual environment with uv**:
    ```bash
    uv venv
    source .venv/bin/activate
    ```
2.  **Dependency management with uv**:

    ```bash
    # Install development dependencies
    uv pip install -e ".[dev]"  # In bash
    uv pip install -e ".\[dev\]"  # In zsh (escape the brackets)

    # Update dependencies
    uv pip freeze > requirements.txt
    ```

3.  **Testing**:

    ```bash
    # Run all tests
    pytest

    # Run specific tests
    pytest tests/test_parser.py -k "test_name"
    ```

4.  **Code quality tools**:

    ```bash
    # Format code
    ruff format .

    # Lint and fix issues
    ruff check --fix .
    ```
