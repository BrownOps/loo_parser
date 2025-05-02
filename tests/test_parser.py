from datetime import datetime, timedelta

import pytest

# Import from the installed package or src layout
from loo_parser.parser import (
    PoopAnalyzer,
    WhatsAppMessage,
    parse_datetime,
    parse_whatsapp_line,
)

# --- Tests for parse_datetime ---


def test_parse_datetime_valid():
    """Test parsing valid date and time strings."""
    assert parse_datetime("2025-05-02", "14:30") == datetime(2025, 5, 2, 14, 30)


def test_parse_datetime_valid_single_digit_day():
    """Test parsing valid date with single digit day."""
    assert parse_datetime("2025-05-1", "11:00") == datetime(2025, 5, 1, 11, 0)


def test_parse_datetime_valid_single_digit_month():
    """Test parsing valid date with single digit month."""
    assert parse_datetime("2025-1-02", "09:05") == datetime(2025, 1, 2, 9, 5)


def test_parse_datetime_valid_single_digit_both():
    """Test parsing valid date with single digit month and day."""
    assert parse_datetime("2025-1-1", "08:00") == datetime(2025, 1, 1, 8, 0)


def test_parse_datetime_valid_different_separator():
    """Test parsing valid date with different separator (e.g., /)."""
    # dateutil should handle this automatically
    assert parse_datetime("2025/05/02", "14:30") == datetime(2025, 5, 2, 14, 30)


def test_parse_datetime_invalid_month():
    """Test parsing with an invalid month."""
    assert parse_datetime("2025-13-01", "00:00") is None


def test_parse_datetime_invalid_format():
    """Test parsing with an invalid date format string."""
    assert parse_datetime("invalid-date", "10:00") is None


# --- Tests for parse_whatsapp_line ---


def test_parse_whatsapp_line_valid_poop():
    """Test parsing a valid WhatsApp line with poop emoji."""
    line = "[02/05/25, 14:30:15] Alice: 💩"
    expected_ts = datetime(2025, 5, 2, 14, 30, 15)
    expected_msg = WhatsAppMessage(timestamp=expected_ts, sender="Alice", content="💩")
    assert parse_whatsapp_line(line) == expected_msg


def test_parse_whatsapp_line_valid_normal():
    """Test parsing a valid normal WhatsApp line."""
    line = "[03/06/24, 10:00:00] Bob: Hello there"
    expected_ts = datetime(2024, 6, 3, 10, 0, 0)
    expected_msg = WhatsAppMessage(timestamp=expected_ts, sender="Bob", content="Hello there")
    assert parse_whatsapp_line(line) == expected_msg


def test_parse_whatsapp_line_invalid_format():
    """Test parsing a line with an invalid format."""
    line = "This is not a valid WhatsApp line"
    assert parse_whatsapp_line(line) is None


def test_parse_whatsapp_line_invalid_date_in_line():
    """Test parsing a line with an invalid date within the brackets."""
    line = "[32/13/25, 14:30:15] Alice: Test"  # Invalid day/month
    assert parse_whatsapp_line(line) is None


# --- Tests for PoopAnalyzer Class ---


@pytest.fixture
def analyzer():
    """Pytest fixture to create a fresh PoopAnalyzer instance for tests."""
    return PoopAnalyzer()


def test_analyzer_init(analyzer):
    """Test the initial state of the analyzer."""
    assert isinstance(analyzer.sender_shift, dict)
    assert len(analyzer.sender_shift) == 0


def test_compute_status_ok(analyzer):
    """Test _compute_status returns 'ok' for recent times relative to message time."""
    # Poop time is 15 days before the message reporting it
    message_time = datetime(2024, 6, 1, 12, 0, 0)
    recent_poop = message_time - timedelta(days=15)
    assert analyzer._compute_status(recent_poop, message_time) == "ok"
    # Poop time is the same as the message time (e.g. poop_live)
    live_poop_time = message_time
    assert analyzer._compute_status(live_poop_time, message_time) == "ok"


def test_compute_status_alert(analyzer):
    """Test _compute_status returns 'alert' for old times relative to message time."""
    # Poop time is 45 days before the message reporting it
    message_time = datetime(2024, 6, 1, 12, 0, 0)
    old_poop = message_time - timedelta(days=45)
    assert analyzer._compute_status(old_poop, message_time) == "alert"


def test_compute_status_exactly_30_days(analyzer):
    """Test _compute_status returns 'ok' when diff is exactly 30 days."""
    message_time = datetime(2024, 6, 1, 12, 0, 0)
    thirty_days_ago = message_time - timedelta(days=30)
    # Status should be 'ok' because the condition is > 30 days
    assert analyzer._compute_status(thirty_days_ago, message_time) == "ok"


def test_compute_status_invalid_input(analyzer):
    """Test _compute_status returns 'error' for non-datetime poop_time input."""
    message_time = datetime.now()
    assert analyzer._compute_status("not a datetime", message_time) == "error"


# --- Refactored Tests for PoopAnalyzer Scenarios ---


# Helper to run analysis and get results for a specific sender
def _get_result_for_sender(analyzer, messages, sender_name):
    results = analyzer.analyze_messages(messages)
    sender_results = [r for r in results if r["sender"] == sender_name]
    assert len(sender_results) == 1, (
        f"Expected 1 result for {sender_name}, got {len(sender_results)}"
    )
    return sender_results[0]


def test_analyzer_poop_live_default_shift(analyzer):
    """Test basic poop_live message with default shift (0)."""
    msg = WhatsAppMessage(timestamp=datetime(2024, 5, 1, 10, 0, 0), sender="Alice", content="💩")
    res = _get_result_for_sender(analyzer, [msg], "Alice")
    assert res["type"] == "poop_live" and res["shift"] == 0
    assert res["poop_time"] == msg.timestamp and res["status"] == "ok"
    assert analyzer.sender_shift.get("Alice", 0) == 0  # Shift state should remain default


def test_analyzer_poop_live_with_trailing_text(analyzer):
    """Test poop_live message with trailing text."""
    msg = WhatsAppMessage(
        timestamp=datetime(2024, 5, 1, 22, 0, 0), sender="Jane", content="💩 <edited>"
    )
    res = _get_result_for_sender(analyzer, [msg], "Jane")
    assert res["type"] == "poop_live" and res["shift"] == 0
    assert res["poop_time"] == msg.timestamp and res["status"] == "ok"


def test_analyzer_toilet_set_shift(analyzer):
    """Test setting the shift state with toilet_set_shift."""
    msg1 = WhatsAppMessage(timestamp=datetime(2024, 5, 1, 10, 0, 0), sender="Alice", content="💩")
    msg2 = WhatsAppMessage(
        timestamp=datetime(2024, 5, 1, 10, 5, 0), sender="Alice", content="🚽 +2"
    )
    results = analyzer.analyze_messages([msg1, msg2])
    assert len(results) == 2
    res_set_shift = [r for r in results if r["type"] == "toilet_set_shift"][0]
    assert (
        res_set_shift["sender"] == "Alice"
        and res_set_shift["shift"] == 2
        and res_set_shift["status"] == "ok"
    )
    assert analyzer.sender_shift.get("Alice") == 2  # Verify shift state updated


def test_analyzer_toilet_set_shift_with_trailing_text(analyzer):
    """Test setting the shift state with trailing text."""
    msg = WhatsAppMessage(
        timestamp=datetime(2024, 5, 1, 23, 30, 0),
        sender="Kevin",
        content="🚽 -1 Edited",
    )
    res = _get_result_for_sender(analyzer, [msg], "Kevin")
    assert res["type"] == "toilet_set_shift" and res["shift"] == -1 and res["status"] == "ok"
    assert analyzer.sender_shift.get("Kevin") == -1


def test_analyzer_poop_live_uses_set_shift(analyzer):
    """Test that poop_live uses the previously set shift state."""
    msg1 = WhatsAppMessage(
        timestamp=datetime(2024, 5, 1, 10, 5, 0), sender="Alice", content="🚽 +2"
    )
    msg2 = WhatsAppMessage(timestamp=datetime(2024, 5, 1, 11, 0, 0), sender="Alice", content="💩")
    results = analyzer.analyze_messages([msg1, msg2])
    res_poop = [r for r in results if r["type"] == "poop_live"][0]
    assert res_poop["sender"] == "Alice" and res_poop["shift"] == 2  # Uses set shift
    assert res_poop["poop_time"] == msg2.timestamp and res_poop["status"] == "ok"
    assert analyzer.sender_shift.get("Alice") == 2  # State remains


def test_analyzer_poop_live_shift_overrides_state(analyzer):
    """Test poop_live_shift overrides state shift for that message only."""
    msg1 = WhatsAppMessage(
        timestamp=datetime(2024, 5, 1, 10, 5, 0), sender="Alice", content="🚽 +2"
    )
    msg2 = WhatsAppMessage(
        timestamp=datetime(2024, 5, 1, 12, 0, 0), sender="Alice", content="💩 -1"
    )  # Override shift
    results = analyzer.analyze_messages([msg1, msg2])
    res_poop_shift = [r for r in results if r["type"] == "poop_live_shift"][0]
    assert (
        res_poop_shift["sender"] == "Alice" and res_poop_shift["shift"] == -1
    )  # Uses message shift
    assert res_poop_shift["poop_time"] == msg2.timestamp and res_poop_shift["status"] == "ok"
    assert analyzer.sender_shift.get("Alice") == 2  # Verify state shift unchanged


def test_analyzer_poop_past_default_shift(analyzer):
    """Test basic poop_past message with default shift and ok status."""
    msg_time = datetime(2024, 5, 1, 13, 0, 0)
    poop_time = datetime(2024, 4, 15, 8, 0)  # 16 days prior -> ok status
    msg = WhatsAppMessage(
        sender="Bob",
        timestamp=msg_time,
        content=f"💩 {poop_time.strftime('%Y-%m-%d %H:%M')}",
    )
    res = _get_result_for_sender(analyzer, [msg], "Bob")
    assert res["type"] == "poop_past" and res["shift"] == 0
    assert res["poop_time"] == poop_time and res["status"] == "ok"
    assert analyzer.sender_shift.get("Bob", 0) == 0


def test_analyzer_poop_past_alert_status(analyzer):
    """Test poop_past message resulting in alert status."""
    msg_time = datetime(2024, 5, 2, 0, 0, 0)
    poop_time = msg_time - timedelta(days=31)  # 31 days prior -> alert status
    msg = WhatsAppMessage(
        sender="Dave",
        timestamp=msg_time,
        content=f"💩 {poop_time.strftime('%Y-%m-%d %H:%M')}",
    )
    res = _get_result_for_sender(analyzer, [msg], "Dave")
    assert res["type"] == "poop_past" and res["shift"] == 0
    assert res["poop_time"] == poop_time and res["status"] == "alert"


def test_analyzer_poop_past_flexible_date_parsing(analyzer):
    """Test poop_past with flexible date formats (single digits)."""
    msg_time = datetime(2024, 5, 1, 19, 0, 0)
    poop_time = datetime(2024, 4, 1, 9, 0)  # 30 days 10 hours prior -> alert
    msg = WhatsAppMessage(sender="Gina", timestamp=msg_time, content="💩 2024-4-1 09:00")
    res = _get_result_for_sender(analyzer, [msg], "Gina")
    assert res["type"] == "poop_past" and res["shift"] == 0
    assert res["poop_time"] == poop_time and res["status"] == "alert"  # Diff > 30 days


def test_analyzer_poop_past_single_digit_hour(analyzer):
    """Test poop_past with single digit hour."""
    msg_time = datetime(2024, 5, 1, 21, 0, 0)
    poop_time = datetime(2024, 4, 20, 3, 30)  # 11 days prior -> ok
    msg = WhatsAppMessage(sender="Ian", timestamp=msg_time, content="💩 2024-04-20 3:30")
    res = _get_result_for_sender(analyzer, [msg], "Ian")
    assert res["type"] == "poop_past" and res["shift"] == 0
    assert res["poop_time"] == poop_time and res["status"] == "ok"


def test_analyzer_poop_past_with_trailing_text(analyzer):
    """Test poop_past message with trailing text."""
    msg_time = datetime(2024, 5, 1, 20, 0, 0)
    poop_time = datetime(2024, 4, 30, 15, 0)  # 1 day prior -> ok
    msg = WhatsAppMessage(
        sender="Harry",
        timestamp=msg_time,
        content="💩 2024-04-30 15:00 some extra text",
    )
    res = _get_result_for_sender(analyzer, [msg], "Harry")
    assert res["type"] == "poop_past" and res["shift"] == 0
    assert res["poop_time"] == poop_time and res["status"] == "ok"


def test_analyzer_poop_past_shift(analyzer):
    """Test poop_past_shift message uses specified shift and doesn't affect state."""
    msg_time = datetime(2024, 5, 1, 14, 0, 0)
    poop_time = datetime(2024, 4, 10, 9, 30)  # 21 days prior -> ok
    msg = WhatsAppMessage(sender="Bob", timestamp=msg_time, content="💩 +3 2024-04-10 09:30")
    res = _get_result_for_sender(analyzer, [msg], "Bob")
    assert res["type"] == "poop_past_shift" and res["shift"] == 3
    assert res["poop_time"] == poop_time and res["status"] == "ok"
    assert analyzer.sender_shift.get("Bob", 0) == 0  # State unchanged


def test_analyzer_unrecognized_poop_emoji(analyzer):
    """Test message containing poop emoji but not matching patterns."""
    msg = WhatsAppMessage(
        timestamp=datetime(2024, 5, 1, 15, 0, 0), sender="Charlie", content="I saw a 💩"
    )
    res = _get_result_for_sender(analyzer, [msg], "Charlie")
    assert res["type"] == "unrecognized_poop_emoji" and res["status"] == "error"


def test_analyzer_ignore_non_poop_message(analyzer):
    """Test that messages without poop/toilet emojis are ignored."""
    msg = WhatsAppMessage(
        timestamp=datetime(2024, 5, 1, 16, 0, 0), sender="Alice", content="Hello world"
    )
    results = analyzer.analyze_messages([msg])
    assert len(results) == 0  # No relevant messages found


def test_analyzer_poop_past_invalid_datetime(analyzer):
    """Test poop_past with an invalid date string."""
    msg = WhatsAppMessage(
        timestamp=datetime(2024, 5, 1, 17, 0, 0),
        sender="Eve",
        content="💩 2024-13-01 10:00",
    )  # Invalid month
    res = _get_result_for_sender(analyzer, [msg], "Eve")
    assert res["type"] == "poop_past" and res["status"] == "error"
    assert res["poop_time"] is None and res.get("error_details") == "invalid_datetime_format"


def test_analyzer_toilet_set_shift_invalid_number(analyzer):
    """Test toilet_set_shift with invalid shift number."""
    msg = WhatsAppMessage(
        timestamp=datetime(2024, 5, 1, 18, 0, 0), sender="Frank", content="🚽 abc"
    )
    res = _get_result_for_sender(analyzer, [msg], "Frank")
    assert res["type"] == "toilet_set_shift_invalid_number" and res["status"] == "error"
    assert analyzer.sender_shift.get("Frank", 0) == 0  # Shift state unaffected
