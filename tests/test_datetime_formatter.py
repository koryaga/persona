#!/usr/bin/env python3
import datetime
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from persona.agent import builder


class TestDateTimeFormatter:
    """Tests for datetime formatting in system prompt."""

    def test_datetime_includes_timezone_abbreviation(self):
        """Test that datetime output includes timezone name."""
        result = datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
        assert isinstance(result, str)
        assert len(result) > 0
        assert ' ' in result
        parts = result.split(' ')
        assert len(parts) == 3
        assert parts[0].count('-') == 2
        assert parts[1].count(':') == 2

    def test_get_instructions_includes_date_line(self):
        """Test that get_instructions includes the date/time line."""
        dt_result = datetime.datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %Z')
        assert 'Current date and time:' in f"Current date and time: {dt_result}"
        assert dt_result.endswith('MSK') or dt_result.endswith('UTC')
