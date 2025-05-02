import json
import re
from collections import defaultdict, namedtuple
from datetime import datetime, timedelta

import typer
from dateutil.parser import ParserError
from dateutil.parser import parse as dateutil_parse

# Define the named tuple for WhatsApp messages
WhatsAppMessage = namedtuple("WhatsAppMessage", ["timestamp", "sender", "content"])

# Date and time formats
DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%H:%M"
DATETIME_FMT = f"{DATE_FMT} {TIME_FMT}"

# Message pattern regex definitions - ORDER MATTERS - more specific patterns first
PATTERNS = {
    "toilet_set_shift": r"^🚽\s*(\S+)(?:\s+.*)?$",
    "poop_live_shift": r"^💩\s*([+-]\d+)$",
    "poop_past_shift": r"^💩\s*([+-]\d+)\s+(\d{4}-\d{1,2}-\d{1,2})\s+(\d{1,2}:\d{2})(?:\s+.*)?$",
    "poop_past": r"^💩\s*(\d{4}-\d{1,2}-\d{1,2})\s+(\d{1,2}:\d{2})(?:\s+.*)?$",
    "poop_live": r"^💩",
}


def parse_datetime(date_str: str, time_str: str) -> datetime | None:
    """
    Parse date and time strings into a datetime object.

    Args:
        date_str: Date string in various formats (YYYY-MM-DD, YYYY-M-D, etc.)
        time_str: Time string (HH:MM, H:MM, etc.)

    Returns:
        datetime object or None if parsing fails
    """
    try:
        datetime_str = f"{date_str} {time_str}"
        return dateutil_parse(datetime_str)
    except (ParserError, ValueError):
        return None


def parse_whatsapp_line(line: str) -> WhatsAppMessage | None:
    """
    Parse a single WhatsApp export line into a WhatsAppMessage.

    Args:
        line: A line from WhatsApp chat export

    Returns:
        WhatsAppMessage tuple or None if line doesn't match expected format

    Example input: "[02/05/25, 14:30:15] Alice: Hello"
    """
    pattern = re.compile(r"\[(\d{2})/(\d{2})/(\d{2}), (\d{2}):(\d{2}):(\d{2})\] (.*?): (.+)")
    m = pattern.match(line)
    if not m:
        return None

    day, month, year, hh, mm, ss, sender, content = m.groups()
    try:
        timestamp = datetime.strptime(f"20{year}-{month}-{day} {hh}:{mm}:{ss}", "%Y-%m-%d %H:%M:%S")
        return WhatsAppMessage(timestamp=timestamp, sender=sender.strip(), content=content.strip())
    except ValueError:
        return None


class PoopAnalyzer:
    """
    Analyze WhatsApp messages to track bathroom usage patterns.

    Maintains per-sender shift state and processes different message
    types related to bathroom usage.
    """

    def __init__(self):
        self.sender_shift = defaultdict(int)

    def analyze_messages(self, messages: list[WhatsAppMessage]) -> list[dict]:
        """
        Process a list of WhatsApp messages and extract bathroom-related events.

        Args:
            messages: List of WhatsAppMessage objects

        Returns:
            List of dictionaries containing structured event data
        """
        results = []
        for msg in messages:
            record = self._process_message(msg)
            if record is not None:
                results.append(record)
        return results

    def _process_message(self, msg: WhatsAppMessage) -> dict | None:
        """
        Process a single message to identify its type and extract relevant data.

        Args:
            msg: A WhatsAppMessage object

        Returns:
            Dictionary with processed data or None if message isn't relevant
        """
        text = msg.content
        for msg_type, regex in PATTERNS.items():
            m = re.compile(regex).match(text)
            if not m:
                continue

            groups = m.groups()
            # Handle toilet shift setting
            if msg_type == "toilet_set_shift":
                try:
                    shift = int(groups[0])
                    self.sender_shift[msg.sender] = shift
                    return {
                        "sender": msg.sender,
                        "message_timestamp": msg.timestamp,
                        "type": msg_type,
                        "shift": shift,
                        "status": "ok",
                    }
                except ValueError:
                    return {
                        "sender": msg.sender,
                        "message_timestamp": msg.timestamp,
                        "original_message": text,
                        "type": "toilet_set_shift_invalid_number",
                        "status": "error",
                    }

            # Handle poop events
            try:
                shift, poop_time = self._extract_poop_info(msg_type, groups, msg)
                if poop_time is None:
                    status = "error"
                    details = "invalid_datetime_format"
                else:
                    status = self._compute_status(poop_time, msg.timestamp)
                    details = None

                result = {
                    "sender": msg.sender,
                    "message_timestamp": msg.timestamp,
                    "original_message": text,
                    "type": msg_type,
                    "shift": shift,
                    "poop_time": poop_time,
                    "status": status,
                }
                if details:
                    result["error_details"] = details
                return result

            except (ValueError, IndexError):
                return {
                    "sender": msg.sender,
                    "message_timestamp": msg.timestamp,
                    "original_message": text,
                    "type": msg_type + "_processing_error",
                    "status": "error",
                }

        # Handle messages with emojis but not matching patterns
        if "💩" in text:
            return {
                "sender": msg.sender,
                "message_timestamp": msg.timestamp,
                "original_message": text,
                "type": "unrecognized_poop_emoji",
                "status": "error",
            }

        if "🚽" in text:
            return {
                "sender": msg.sender,
                "message_timestamp": msg.timestamp,
                "original_message": text,
                "type": "unrecognized_toilet_emoji",
                "status": "error",
            }

        # Ignore messages not related to poop or toilet shifts
        return None

    def _extract_poop_info(
        self, msg_type: str, groups: tuple, msg: WhatsAppMessage
    ) -> tuple[int, datetime | None]:
        """
        Extract shift and timestamp information from message regex groups.

        Args:
            msg_type: Type of message pattern matched
            groups: Regex match groups
            msg: Original WhatsAppMessage

        Returns:
            Tuple of (shift, poop_time)
        """
        current_sender_shift = self.sender_shift[msg.sender]

        if msg_type == "poop_live":
            return current_sender_shift, msg.timestamp
        elif msg_type == "poop_live_shift":
            shift = int(groups[0])
            return shift, msg.timestamp
        elif msg_type == "poop_past":
            poop_dt = parse_datetime(groups[0], groups[1])
            return current_sender_shift, poop_dt
        elif msg_type == "poop_past_shift":
            shift = int(groups[0])
            poop_dt = parse_datetime(groups[1], groups[2])
            return shift, poop_dt

        return 0, None

    def _compute_status(self, poop_time: datetime, message_timestamp: datetime) -> str:
        """
        Determine status based on the time difference between poop and message.

        Args:
            poop_time: When the event occurred
            message_timestamp: When the message was sent

        Returns:
            'ok' if < 30 days difference, 'alert' if > 30 days, 'error' if invalid
        """
        if not isinstance(poop_time, datetime):
            return "error"
        return "alert" if (message_timestamp - poop_time) > timedelta(days=30) else "ok"


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime objects."""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def main(input_file: str = None, output_file: str = None):
    """
    Parse WhatsApp chat exports and analyze bathroom-related messages.

    Args:
        input_file: Path to WhatsApp chat export file
        output_file: Path for output JSON file
    """
    # Use default files if not specified
    input_file = input_file or "whatsapp_chat.txt"
    output_file = output_file or "poop_results.json"

    try:
        # Read the input file
        with open(input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Parse messages
        messages = [parse_whatsapp_line(line) for line in lines if parse_whatsapp_line(line)]

        # Analyze messages
        analyzer = PoopAnalyzer()
        results = analyzer.analyze_messages(messages)

        # Print summary
        print(f"Processed {len(messages)} messages, found {len(results)} relevant records.")

        # Store results as JSON
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, cls=DateTimeEncoder, ensure_ascii=False)

        print(f"Results saved to {output_file}")
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


def cli():
    """Command-line interface entry point."""
    parser = typer.Typer()

    @parser.command()
    def run(
        input_file: str = typer.Argument(None, help="Path to WhatsApp chat export file"),
        output_file: str = typer.Argument(None, help="Path for output JSON file"),
    ):
        return main(input_file, output_file)

    parser()


if __name__ == "__main__":
    import sys

    sys.exit(main())
