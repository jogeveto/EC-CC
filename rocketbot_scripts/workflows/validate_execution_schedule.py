# coding: utf-8
"""
Script: Validate Execution Schedule
Version: 1.2.2
Created: 2025-12-05
Updated: 2025-12-06

Description:
    Validates if bot execution is allowed based on Colombian holidays
    and configured time ranges. Returns detailed validation result.

Usage in Rocketbot:
    Inputs:
        - locLstTimeRanges: JSON string or list with format:
          [{"HoraInicio": "0700", "HoraFin": "1200"}, ...]
        - locBlnCheckHolidays: Boolean (default: True) - block on holidays
        - locIntTimezoneOffset: Hours from UTC (default: -5 for Colombia)

    Outputs:
        - locBlnIsExecutionAllowed: Boolean - True if execution allowed
        - locBnValidationResult: Dict with validation details

Example:
    time_ranges = '[{"HoraInicio": "0700", "HoraFin": "1200"}]'
    check_holidays = True
    timezone_offset = -5

    # After execution:
    # locBlnIsExecutionAllowed = True/False
    # locBnValidationResult = {...}
"""

import json
import datetime
from datetime import date, time
from typing import List, Dict, Any, Optional, Tuple
import traceback
import ast

# Explicitly register standard library modules in globals for Rocketbot compatibility
globals()['json'] = json
globals()['datetime'] = datetime
globals()['date'] = date
globals()['time'] = time
globals()['traceback'] = traceback
globals()['ast'] = ast

try:
    import holidays
    # Explicitly register in globals for Rocketbot compatibility
    globals()['holidays'] = holidays
except ImportError:
    print(
        "WARNING: 'holidays' library not installed. Install with: pip install holidays"
    )
    holidays = None
    globals()['holidays'] = None


# ============================================================================
# CORE VALIDATION FUNCTIONS
# ============================================================================


def is_holiday(check_date: date, country: str = "CO") -> Tuple[bool, Optional[str]]:
    """
    Check if a given date is a holiday in the specified country.

    Args:
        check_date: Date to check
        country: Country code (default: 'CO' for Colombia)

    Returns:
        Tuple of (is_holiday: bool, holiday_name: str or None)

    Example:
        >>> is_holiday(date(2024, 12, 25), 'CO')
        (True, 'Christmas Day')
    """
    # Access holidays module via globals for Rocketbot compatibility
    _holidays = globals().get('holidays')

    if _holidays is None:
        return False, None

    try:
        country_holidays = _holidays.country_holidays(country, years=[check_date.year])
        if check_date in country_holidays:
            holiday_name = country_holidays.get(check_date)
            return True, holiday_name
        return False, None
    except Exception as e:
        print(f"Error checking holiday: {e}")
        return False, None


# Explicitly register function in globals for Rocketbot compatibility
globals()["is_holiday"] = is_holiday


def parse_time_ranges(ranges_input: Any) -> List[Dict[str, str]]:
    """
    Parse time ranges from various input formats.

    Args:
        ranges_input: Can be:
            - JSON string: '[{"HoraInicio": "0700", "HoraFin": "1200"}]'
            - Python string: "[{'HoraInicio': '0700', 'HoraFin': '1200'}]"
            - List of dicts: [{"HoraInicio": "0700", "HoraFin": "1200"}]
            - None: Returns empty list

    Returns:
        List of time range dictionaries

    Raises:
        ValueError: If input format is invalid

    Example:
        >>> parse_time_ranges('[{"HoraInicio": "0700", "HoraFin": "1200"}]')
        [{'HoraInicio': '0700', 'HoraFin': '1200'}]
    """
    if ranges_input is None or ranges_input == "":
        return []

    # If already a list, return it
    if isinstance(ranges_input, list):
        return ranges_input

    # If string, try to parse
    if isinstance(ranges_input, str):
        # Debug: Log input for troubleshooting
        print(f"DEBUG: Parsing time ranges from string (type: {type(ranges_input).__name__})")
        print(f"DEBUG: Input value: {ranges_input[:100]}...")  # First 100 chars

        # Access modules via globals for Rocketbot compatibility
        _json = globals().get('json', json)
        _ast = globals().get('ast', ast)

        # Try JSON first (proper format)
        try:
            parsed = _json.loads(ranges_input)
            if not isinstance(parsed, list):
                raise ValueError("Time ranges must be a list")
            print(f"DEBUG: Successfully parsed as JSON")
            return parsed
        except _json.JSONDecodeError as e:
            print(f"DEBUG: JSON parsing failed: {e}")

            # Try Python literal syntax as fallback (single quotes, etc.)
            try:
                parsed = _ast.literal_eval(ranges_input)
                if not isinstance(parsed, list):
                    raise ValueError("Time ranges must be a list")
                print(f"DEBUG: Successfully parsed as Python literal")
                return parsed
            except (ValueError, SyntaxError) as e2:
                raise ValueError(
                    f"Invalid time ranges format. "
                    f"JSON error: {e}. "
                    f"Python literal error: {e2}. "
                    f"Input: {ranges_input[:50]}..."
                )

    raise ValueError(f"Unsupported time ranges format: {type(ranges_input)}")

# Explicitly register function in globals for Rocketbot compatibility
globals()['parse_time_ranges'] = parse_time_ranges


def parse_time_from_string(time_str: str) -> time:
    """
    Parse time from string format "HHMM" to datetime.time object.

    Args:
        time_str: Time in format "HHMM" (e.g., "0730", "1445")

    Returns:
        datetime.time object

    Raises:
        ValueError: If time format is invalid

    Example:
        >>> parse_time_from_string("0730")
        datetime.time(7, 30)
    """
    if not time_str or len(time_str) != 4:
        raise ValueError(f"Time must be in HHMM format, got: {time_str}")

    try:
        hour = int(time_str[:2])
        minute = int(time_str[2:])
        return time(hour=hour, minute=minute)
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid time format '{time_str}': {e}")

# Explicitly register function in globals for Rocketbot compatibility
globals()['parse_time_from_string'] = parse_time_from_string


def is_time_in_ranges(
    current_time: time, time_ranges: List[Dict[str, str]]
) -> Tuple[bool, Optional[Dict[str, str]]]:
    """
    Check if current time falls within any of the allowed time ranges.

    Args:
        current_time: Time to check
        time_ranges: List of time range dicts with "HoraInicio" and "HoraFin"

    Returns:
        Tuple of (is_in_range: bool, matched_range: dict or None)

    Example:
        >>> ranges = [{"HoraInicio": "0700", "HoraFin": "1200"}]
        >>> is_time_in_ranges(time(9, 30), ranges)
        (True, {"HoraInicio": "0700", "HoraFin": "1200"})
    """
    if not time_ranges:
        # No ranges specified means no time restrictions
        return True, None

    # Use globals() to ensure function is available in Rocketbot's execution context
    _parse_time_from_string = globals().get(
        "parse_time_from_string", parse_time_from_string
    )

    for time_range in time_ranges:
        try:
            start_time = _parse_time_from_string(time_range.get("HoraInicio", ""))
            end_time = _parse_time_from_string(time_range.get("HoraFin", ""))

            # Check if current time is within range (inclusive)
            if start_time <= current_time <= end_time:
                return True, time_range
        except ValueError as e:
            print(f"Warning: Invalid time range {time_range}: {e}")
            continue

    return False, None

# Explicitly register function in globals for Rocketbot compatibility
globals()['is_time_in_ranges'] = is_time_in_ranges


def validate_execution(
    time_ranges: Any = None,
    check_holidays: bool = True,
    timezone_offset: int = -5,
    current_datetime: Optional[datetime.datetime] = None,
) -> Dict[str, Any]:
    """
    Main validation function to check if execution is allowed.

    Args:
        time_ranges: Time ranges configuration (JSON string or list)
        check_holidays: Whether to block execution on holidays
        timezone_offset: Hours offset from UTC (default: -5 for Colombia)
        current_datetime: Override current datetime (for testing)

    Returns:
        Dictionary with validation results:
        {
            "allowed": True/False,
            "current_date": "2024-12-05",
            "current_time": "09:30",
            "is_holiday": False,
            "holiday_name": None,
            "is_in_time_range": True,
            "matched_time_range": {"HoraInicio": "0700", "HoraFin": "1200"},
            "reason": "Execution allowed" or reason for denial
        }

    Example:
        >>> result = validate_execution(
        ...     time_ranges='[{"HoraInicio": "0700", "HoraFin": "1200"}]',
        ...     check_holidays=True
        ... )
        >>> result['allowed']
        True
    """
    # Get current datetime in specified timezone
    if current_datetime is None:
        tz = datetime.timezone(datetime.timedelta(hours=timezone_offset))
        current_datetime = datetime.datetime.now(tz)

    current_date = current_datetime.date()
    current_time = current_datetime.time()

    # Initialize result
    result = {
        "allowed": True,
        "current_date": current_date.strftime("%Y-%m-%d"),
        "current_time": current_time.strftime("%H:%M"),
        "is_holiday": False,
        "holiday_name": None,
        "is_in_time_range": True,
        "matched_time_range": None,
        "reason": "Execution allowed",
    }

    # Check holidays (always detect, but only block if check_holidays=True)
    # Use globals() to ensure function is available in Rocketbot's execution context
    _is_holiday = globals().get("is_holiday", is_holiday)
    is_hol, hol_name = _is_holiday(current_date)
    result["is_holiday"] = is_hol
    result["holiday_name"] = hol_name

    if check_holidays and is_hol:
        result["allowed"] = False
        result["reason"] = f"Holiday: {hol_name}"
        return result

    # Parse and check time ranges
    try:
        # Use globals() with fallback to ensure functions are found
        _parse_time_ranges = globals().get("parse_time_ranges", parse_time_ranges)
        _is_time_in_ranges = globals().get("is_time_in_ranges", is_time_in_ranges)

        parsed_ranges = _parse_time_ranges(time_ranges)

        if parsed_ranges:  # Only check if ranges are specified
            in_range, matched_range = _is_time_in_ranges(current_time, parsed_ranges)
            result["is_in_time_range"] = in_range
            result["matched_time_range"] = matched_range

            if not in_range:
                result["allowed"] = False
                result["reason"] = "Outside allowed time ranges"
                return result
    except ValueError as e:
        result["allowed"] = False
        result["reason"] = f"Invalid time ranges configuration: {e}"
        return result

    return result

# Explicitly register function in globals for Rocketbot compatibility
globals()['validate_execution'] = validate_execution


# ============================================================================
# ROCKETBOT WRAPPER
# ============================================================================

# Check if running in Rocketbot environment
try:
    GetParams  # type: ignore[name-defined]
    SetVar  # type: ignore[name-defined]
    IN_ROCKETBOT = True
except NameError:
    IN_ROCKETBOT = False

    # Define mocks for testing
    def GetVar(name):
        return None

    def SetVar(name, value):
        pass


if IN_ROCKETBOT:
    try:
        # Get parameters from Rocketbot
        time_ranges_param = GetVar("locLstTimeRanges")
        check_holidays_param = GetVar("locBlnCheckHolidays")
        timezone_offset_param = GetVar("locIntTimezoneOffset")

        # Parse parameters with defaults
        check_holidays_value = (
            True if check_holidays_param is None else bool(check_holidays_param)
        )
        timezone_offset_value = (
            -5 if timezone_offset_param is None else int(timezone_offset_param)
        )

        # Execute validation
        # Explicitly reference function from globals to ensure it's available in Rocketbot's exec context
        _validate_execution = globals().get("validate_execution", validate_execution)
        validation_result = _validate_execution(
            time_ranges=time_ranges_param,
            check_holidays=check_holidays_value,
            timezone_offset=timezone_offset_value,
        )

        # Set output variables
        SetVar("locBlnIsExecutionAllowed", validation_result["allowed"])
        SetVar("locBnValidationResult", validation_result)

        # Print result for logging
        print(f"Validation result: {validation_result['reason']}")

    except Exception as e:
        error_msg = f"Error in validation script: {str(e)}"
        print(error_msg)
        print("Full traceback:")
        traceback.print_exc()

        # Set error result
        error_result = {"allowed": False, "reason": error_msg}
        SetVar("locBlnIsExecutionAllowed", False)
        SetVar("locBnValidationResult", error_result)


# ============================================================================
# STANDALONE EXECUTION (for testing)
# ============================================================================

if __name__ == "__main__" and not IN_ROCKETBOT:
    print("=== Validation Script Test ===\n")

    # Test 1: Working hours validation
    print("Test 1: Working hours (7AM-7PM)")
    test_ranges = [{"HoraInicio": "0700", "HoraFin": "1900"}]
    result = validate_execution(time_ranges=test_ranges, check_holidays=True)
    print(f"Result: {result}\n")

    # Test 2: Multiple time ranges
    print("Test 2: Multiple ranges (7AM-12PM, 1PM-11PM)")
    test_ranges = [
        {"HoraInicio": "0700", "HoraFin": "1200"},
        {"HoraInicio": "1300", "HoraFin": "2300"},
    ]
    result = validate_execution(time_ranges=test_ranges, check_holidays=True)
    print(f"Result: {result}\n")

    # Test 3: Holiday check (Christmas)
    print("Test 3: Holiday check (December 25, 2024)")
    christmas = datetime.datetime(2024, 12, 25, 10, 0)
    result = validate_execution(
        time_ranges=test_ranges, check_holidays=True, current_datetime=christmas
    )
    print(f"Result: {result}\n")

    print("=== Tests Complete ===")
