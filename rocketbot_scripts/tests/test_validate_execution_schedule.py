# coding: utf-8
"""
Tests for validate_execution_schedule.py

Run with:
    python -m unittest rocketbot_scripts.tests.test_validate_execution_schedule
    python -m unittest discover rocketbot_scripts/tests
"""

import unittest
import sys
import os
import datetime
from datetime import date, time

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the script functions
from workflows.validate_execution_schedule import (
    is_holiday,
    parse_time_ranges,
    parse_time_from_string,
    is_time_in_ranges,
    validate_execution,
)


class TestHolidayDetection(unittest.TestCase):
    """Test holiday detection functionality"""

    def test_christmas_is_holiday(self):
        """Christmas (December 25) should be detected as holiday"""
        christmas = date(2024, 12, 25)
        is_hol, name = is_holiday(christmas, "CO")
        self.assertTrue(is_hol)
        self.assertIsNotNone(name)
        self.assertIn("Christmas", name)

    def test_independence_day_is_holiday(self):
        """Colombia Independence Day (July 20) should be detected"""
        independence_day = date(2024, 7, 20)
        is_hol, name = is_holiday(independence_day, "CO")
        self.assertTrue(is_hol)
        self.assertIsNotNone(name)

    def test_regular_day_not_holiday(self):
        """Regular working day should not be holiday"""
        regular_day = date(2024, 3, 15)  # Mid-March, no holiday
        is_hol, name = is_holiday(regular_day, "CO")
        self.assertFalse(is_hol)
        self.assertIsNone(name)

    def test_new_year_is_holiday(self):
        """New Year's Day (January 1) should be holiday"""
        new_year = date(2024, 1, 1)
        is_hol, name = is_holiday(new_year, "CO")
        self.assertTrue(is_hol)
        self.assertIsNotNone(name)


class TestTimeRangeParsing(unittest.TestCase):
    """Test time range parsing from various formats"""

    def test_parse_json_string(self):
        """Parse time ranges from JSON string"""
        json_str = '[{"HoraInicio": "0700", "HoraFin": "1200"}]'
        result = parse_time_ranges(json_str)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["HoraInicio"], "0700")
        self.assertEqual(result[0]["HoraFin"], "1200")

    def test_parse_list(self):
        """Parse time ranges from list"""
        ranges_list = [{"HoraInicio": "0700", "HoraFin": "1200"}]
        result = parse_time_ranges(ranges_list)
        self.assertEqual(result, ranges_list)

    def test_parse_multiple_ranges(self):
        """Parse multiple time ranges"""
        json_str = """[
            {"HoraInicio": "0700", "HoraFin": "1200"},
            {"HoraInicio": "1300", "HoraFin": "2300"}
        ]"""
        result = parse_time_ranges(json_str)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["HoraInicio"], "0700")
        self.assertEqual(result[1]["HoraInicio"], "1300")

    def test_parse_empty_string(self):
        """Empty string should return empty list"""
        result = parse_time_ranges("")
        self.assertEqual(result, [])

    def test_parse_none(self):
        """None should return empty list"""
        result = parse_time_ranges(None)
        self.assertEqual(result, [])

    def test_parse_invalid_json(self):
        """Invalid JSON should raise ValueError"""
        with self.assertRaises(ValueError):
            parse_time_ranges("not valid json")

    def test_parse_non_list_json(self):
        """JSON that's not a list should raise ValueError"""
        with self.assertRaises(ValueError):
            parse_time_ranges('{"HoraInicio": "0700"}')

    def test_parse_python_literal_syntax(self):
        """Should parse Python literal syntax with single quotes"""
        python_str = "[{'HoraInicio': '0700', 'HoraFin': '1200'}]"
        result = parse_time_ranges(python_str)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["HoraInicio"], "0700")
        self.assertEqual(result[0]["HoraFin"], "1200")


class TestTimeStringParsing(unittest.TestCase):
    """Test parsing time from string format"""

    def test_parse_morning_time(self):
        """Parse morning time (07:30)"""
        result = parse_time_from_string("0730")
        self.assertEqual(result, time(7, 30))

    def test_parse_afternoon_time(self):
        """Parse afternoon time (14:45)"""
        result = parse_time_from_string("1445")
        self.assertEqual(result, time(14, 45))

    def test_parse_midnight(self):
        """Parse midnight (00:00)"""
        result = parse_time_from_string("0000")
        self.assertEqual(result, time(0, 0))

    def test_parse_end_of_day(self):
        """Parse end of day (23:59)"""
        result = parse_time_from_string("2359")
        self.assertEqual(result, time(23, 59))

    def test_parse_invalid_format(self):
        """Invalid format should raise ValueError"""
        with self.assertRaises(ValueError):
            parse_time_from_string("07:30")  # Wrong format (should be 0730)

    def test_parse_too_short(self):
        """Too short string should raise ValueError"""
        with self.assertRaises(ValueError):
            parse_time_from_string("730")

    def test_parse_invalid_hour(self):
        """Invalid hour should raise ValueError"""
        with self.assertRaises(ValueError):
            parse_time_from_string("2500")  # 25 hours

    def test_parse_invalid_minute(self):
        """Invalid minute should raise ValueError"""
        with self.assertRaises(ValueError):
            parse_time_from_string("0760")  # 60 minutes


class TestTimeInRanges(unittest.TestCase):
    """Test checking if time is within allowed ranges"""

    def test_time_within_single_range(self):
        """Time within single range should match"""
        ranges = [{"HoraInicio": "0700", "HoraFin": "1200"}]
        current = time(9, 30)
        in_range, matched = is_time_in_ranges(current, ranges)
        self.assertTrue(in_range)
        self.assertEqual(matched, ranges[0])

    def test_time_before_range(self):
        """Time before range should not match"""
        ranges = [{"HoraInicio": "0700", "HoraFin": "1200"}]
        current = time(6, 30)
        in_range, matched = is_time_in_ranges(current, ranges)
        self.assertFalse(in_range)
        self.assertIsNone(matched)

    def test_time_after_range(self):
        """Time after range should not match"""
        ranges = [{"HoraInicio": "0700", "HoraFin": "1200"}]
        current = time(13, 0)
        in_range, matched = is_time_in_ranges(current, ranges)
        self.assertFalse(in_range)
        self.assertIsNone(matched)

    def test_time_at_range_start(self):
        """Time at range start should match (inclusive)"""
        ranges = [{"HoraInicio": "0700", "HoraFin": "1200"}]
        current = time(7, 0)
        in_range, matched = is_time_in_ranges(current, ranges)
        self.assertTrue(in_range)
        self.assertEqual(matched, ranges[0])

    def test_time_at_range_end(self):
        """Time at range end should match (inclusive)"""
        ranges = [{"HoraInicio": "0700", "HoraFin": "1200"}]
        current = time(12, 0)
        in_range, matched = is_time_in_ranges(current, ranges)
        self.assertTrue(in_range)
        self.assertEqual(matched, ranges[0])

    def test_time_in_second_range(self):
        """Time in second of multiple ranges should match"""
        ranges = [
            {"HoraInicio": "0700", "HoraFin": "1200"},
            {"HoraInicio": "1300", "HoraFin": "2300"},
        ]
        current = time(15, 0)
        in_range, matched = is_time_in_ranges(current, ranges)
        self.assertTrue(in_range)
        self.assertEqual(matched, ranges[1])

    def test_time_between_ranges(self):
        """Time between two ranges should not match"""
        ranges = [
            {"HoraInicio": "0700", "HoraFin": "1200"},
            {"HoraInicio": "1300", "HoraFin": "2300"},
        ]
        current = time(12, 30)  # Between 12:00 and 13:00
        in_range, matched = is_time_in_ranges(current, ranges)
        self.assertFalse(in_range)
        self.assertIsNone(matched)

    def test_no_ranges_specified(self):
        """No ranges means no restrictions (should allow)"""
        ranges = []
        current = time(3, 0)  # 3 AM
        in_range, matched = is_time_in_ranges(current, ranges)
        self.assertTrue(in_range)
        self.assertIsNone(matched)


class TestValidateExecution(unittest.TestCase):
    """Test main validation function"""

    def test_allowed_workday_during_hours(self):
        """Regular workday during allowed hours should be allowed"""
        # March 15, 2024 at 10:00 AM (not a holiday)
        test_datetime = datetime.datetime(2024, 3, 15, 10, 0)
        ranges = [{"HoraInicio": "0700", "HoraFin": "1900"}]

        result = validate_execution(
            time_ranges=ranges, check_holidays=True, current_datetime=test_datetime
        )

        self.assertTrue(result["allowed"])
        self.assertFalse(result["is_holiday"])
        self.assertTrue(result["is_in_time_range"])
        self.assertEqual(result["reason"], "Execution allowed")

    def test_blocked_on_holiday(self):
        """Execution on holiday should be blocked"""
        # Christmas 2024 at 10:00 AM
        christmas = datetime.datetime(2024, 12, 25, 10, 0)
        ranges = [{"HoraInicio": "0700", "HoraFin": "1900"}]

        result = validate_execution(
            time_ranges=ranges, check_holidays=True, current_datetime=christmas
        )

        self.assertFalse(result["allowed"])
        self.assertTrue(result["is_holiday"])
        self.assertIn("Holiday", result["reason"])

    def test_allowed_on_holiday_when_check_disabled(self):
        """Holiday should be allowed when check_holidays=False"""
        christmas = datetime.datetime(2024, 12, 25, 10, 0)
        ranges = [{"HoraInicio": "0700", "HoraFin": "1900"}]

        result = validate_execution(
            time_ranges=ranges, check_holidays=False, current_datetime=christmas
        )

        self.assertTrue(result["allowed"])
        self.assertTrue(result["is_holiday"])  # Detected but not blocking

    def test_blocked_outside_time_range(self):
        """Execution outside time range should be blocked"""
        # March 15, 2024 at 6:00 AM (before 7 AM start)
        test_datetime = datetime.datetime(2024, 3, 15, 6, 0)
        ranges = [{"HoraInicio": "0700", "HoraFin": "1900"}]

        result = validate_execution(
            time_ranges=ranges, check_holidays=True, current_datetime=test_datetime
        )

        self.assertFalse(result["allowed"])
        self.assertFalse(result["is_in_time_range"])
        self.assertEqual(result["reason"], "Outside allowed time ranges")

    def test_multiple_time_ranges(self):
        """Should work with multiple time ranges"""
        # March 15, 2024 at 2:00 PM (in second range)
        test_datetime = datetime.datetime(2024, 3, 15, 14, 0)
        ranges = [
            {"HoraInicio": "0700", "HoraFin": "1200"},
            {"HoraInicio": "1300", "HoraFin": "2300"},
        ]

        result = validate_execution(
            time_ranges=ranges, check_holidays=True, current_datetime=test_datetime
        )

        self.assertTrue(result["allowed"])
        self.assertTrue(result["is_in_time_range"])
        self.assertEqual(result["matched_time_range"], ranges[1])

    def test_json_string_time_ranges(self):
        """Should accept JSON string for time ranges"""
        test_datetime = datetime.datetime(2024, 3, 15, 10, 0)
        ranges_json = '[{"HoraInicio": "0700", "HoraFin": "1900"}]'

        result = validate_execution(
            time_ranges=ranges_json, check_holidays=True, current_datetime=test_datetime
        )

        self.assertTrue(result["allowed"])

    def test_no_time_ranges(self):
        """No time ranges should allow any time"""
        # March 15, 2024 at 3:00 AM
        test_datetime = datetime.datetime(2024, 3, 15, 3, 0)

        result = validate_execution(
            time_ranges=None, check_holidays=True, current_datetime=test_datetime
        )

        self.assertTrue(result["allowed"])
        self.assertTrue(result["is_in_time_range"])

    def test_invalid_time_ranges_format(self):
        """Invalid time ranges should return error"""
        test_datetime = datetime.datetime(2024, 3, 15, 10, 0)

        result = validate_execution(
            time_ranges="invalid json",
            check_holidays=True,
            current_datetime=test_datetime,
        )

        self.assertFalse(result["allowed"])
        self.assertIn("Invalid time ranges", result["reason"])

    def test_result_contains_all_fields(self):
        """Result should contain all expected fields"""
        test_datetime = datetime.datetime(2024, 3, 15, 10, 0)
        ranges = [{"HoraInicio": "0700", "HoraFin": "1900"}]

        result = validate_execution(
            time_ranges=ranges, check_holidays=True, current_datetime=test_datetime
        )

        # Check all required fields
        self.assertIn("allowed", result)
        self.assertIn("current_date", result)
        self.assertIn("current_time", result)
        self.assertIn("is_holiday", result)
        self.assertIn("holiday_name", result)
        self.assertIn("is_in_time_range", result)
        self.assertIn("matched_time_range", result)
        self.assertIn("reason", result)

    def test_edge_case_midnight(self):
        """Test at midnight boundary"""
        # March 15, 2024 at 00:00
        test_datetime = datetime.datetime(2024, 3, 15, 0, 0)
        ranges = [{"HoraInicio": "0000", "HoraFin": "0600"}]

        result = validate_execution(
            time_ranges=ranges, check_holidays=True, current_datetime=test_datetime
        )

        self.assertTrue(result["allowed"])

    def test_edge_case_end_of_day(self):
        """Test at end of day boundary"""
        # March 15, 2024 at 23:59
        test_datetime = datetime.datetime(2024, 3, 15, 23, 59)
        ranges = [{"HoraInicio": "2000", "HoraFin": "2359"}]

        result = validate_execution(
            time_ranges=ranges, check_holidays=True, current_datetime=test_datetime
        )

        self.assertTrue(result["allowed"])

    def test_midnight_outside_day_ranges(self):
        """Test at midnight (00:25) with daytime ranges - should be blocked"""
        # December 6, 2025 at 00:25 (12:25 AM)
        test_datetime = datetime.datetime(2025, 12, 6, 0, 25)
        ranges = [
            {"HoraInicio": "0700", "HoraFin": "1200"},
            {"HoraInicio": "1200", "HoraFin": "1300"},
            {"HoraInicio": "1300", "HoraFin": "2300"},
        ]

        result = validate_execution(
            time_ranges=ranges, check_holidays=True, current_datetime=test_datetime
        )

        # Should be blocked (outside all ranges)
        self.assertFalse(result["allowed"])
        self.assertFalse(result["is_in_time_range"])
        self.assertIsNone(result["matched_time_range"])
        self.assertEqual(result["reason"], "Outside allowed time ranges")


if __name__ == "__main__":
    unittest.main()
