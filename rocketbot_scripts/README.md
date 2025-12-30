# Rocketbot Scripts

Repository for plain standalone Python scripts executed by Rocketbot workflows.

## Overview

This directory contains simple, self-contained Python scripts that Rocketbot can execute directly. Unlike the modular architecture in other parts of this repository, these scripts are standalone and don't import from shared modules.

## Directory Structure

```
rocketbot_scripts/
├── README.md                # This file
├── requirements.txt         # Script dependencies
├── workflows/               # Scripts organized by workflow
│   └── validate_execution_schedule.py
└── tests/                   # Tests for scripts
    ├── __init__.py
    ├── test_validate_execution_schedule.py
    └── fixtures/            # Test data
        └── time_ranges.json
```

## Installation

Install script dependencies:

```bash
pip install -r requirements.txt
```

**Note**: The `holidays` library is required for holiday detection features in scripts.

## Creating a New Script

### 1. Naming Convention

Scripts should follow the pattern: `<descriptive_name>.py`

Examples:
- `validate_execution_schedule.py`
- `generate_monthly_report.py`
- `process_emails.py`

### 2. Script Template

```python
# coding: utf-8
"""
Script: [Script Name]
Version: 1.0.0
Created: YYYY-MM-DD

Description:
    Brief description of what this script does and its purpose.

Usage in Rocketbot:
    Inputs:
        - locStrParam1: Description of first parameter
        - locIntParam2: Description of second parameter

    Outputs:
        - locDctResult: Description of output variable

Example:
    SetVar("locStrParam1", "value")
    SetVar("locIntParam2", 123)
    Execute("script_name.py")
    # After execution:
    # result = GetVar("locDctResult")
"""

import json
from typing import Dict, Any

# ============================================================================
# CORE LOGIC FUNCTIONS
# ============================================================================

def helper_function(data: str) -> str:
    """
    Helper function example.

    Args:
        data: Input data

    Returns:
        Processed data
    """
    return data.upper()


def main_logic(param1: str, param2: int) -> Dict[str, Any]:
    """
    Main business logic - testable independently of Rocketbot.

    Args:
        param1: Description
        param2: Description

    Returns:
        Dictionary with results

    Example:
        >>> main_logic("test", 123)
        {'status': 'success', 'data': ...}
    """
    try:
        # Use globals() for helper functions to ensure Rocketbot compatibility
        _helper_function = globals().get('helper_function', helper_function)

        # Your implementation here
        processed = _helper_function(param1)

        result = {
            "status": "success",
            "message": "Operation completed",
            "data": {
                "processed": processed,
                "param2": param2
            }
        }

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "data": None
        }

# ============================================================================
# ROCKETBOT WRAPPER
# ============================================================================

# Check if running in Rocketbot environment
try:
    GetVar  # type: ignore[name-defined]
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
        # Get parameters from Rocketbot (use GetVar with 'loc' prefix)
        param1 = GetVar("locStrParam1")
        param2 = GetVar("locIntParam2")

        # Execute core logic using globals() for Rocketbot compatibility
        _main_logic = globals().get('main_logic', main_logic)
        result = _main_logic(param1, param2)

        # Set output variables
        SetVar("locDctResult", result)

        # Print result for logging
        print(f"Script completed: {result['status']}")

    except Exception as e:
        import traceback
        error_msg = f"Script error: {str(e)}"
        print(error_msg)
        print("Full traceback:")
        traceback.print_exc()

        # Set error result
        SetVar("locDctResult", {
            "status": "error",
            "message": error_msg
        })

# ============================================================================
# STANDALONE EXECUTION (for testing)
# ============================================================================

if __name__ == "__main__" and not IN_ROCKETBOT:
    print("=== Script Test ===\n")

    # Test execution with sample data
    result = main_logic("test_value", 123)
    print(f"Result: {result}\n")

    print("=== Test Complete ===")
```

### 3. Documentation Standards

Each script must include:

1. **Header docstring** with:
   - Script name
   - Version (semantic versioning)
   - Creation/update dates
   - Description
   - Rocketbot inputs and outputs
   - Usage example

2. **Function docstrings** with:
   - Purpose
   - Parameters with types
   - Return value description
   - Example usage

3. **Comments** for complex logic

### 4. Script Structure

Recommended structure:

1. **Imports**: All required libraries
2. **Core Logic**: Business logic functions (testable)
3. **Rocketbot Wrapper**: Interface with Rocketbot (GetParams/SetVar)
4. **Standalone Execution**: For testing outside Rocketbot

## Testing Scripts

### Running Tests

**All tests:**
```bash
python -m unittest discover rocketbot_scripts/tests
```

**Specific script tests:**
```bash
python -m unittest rocketbot_scripts.tests.test_<script_name>
```

**Single test case:**
```bash
python -m unittest rocketbot_scripts.tests.test_<script_name>.TestClassName.test_method_name
```

### Creating Tests

Tests should be placed in `tests/test_<script_name>.py`:

```python
# coding: utf-8
"""
Tests for <script_name>.py

Run with:
    python -m unittest rocketbot_scripts.tests.test_<script_name>
"""

import unittest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import script functions
from workflows.<script_name> import main_logic, helper_function


class TestMainLogic(unittest.TestCase):
    """Test main business logic"""

    def test_success_case(self):
        """Test successful execution"""
        result = main_logic("test_input", 123)
        self.assertEqual(result["status"], "success")

    def test_error_case(self):
        """Test error handling"""
        result = main_logic(None, 123)
        self.assertEqual(result["status"], "error")


if __name__ == "__main__":
    unittest.main()
```

### Test Fixtures

Place test data in `tests/fixtures/`:
- JSON files for configuration
- CSV files for sample data
- Mock responses

## Example: Validation Script

### validate_execution_schedule.py

This script validates if bot execution is allowed based on:
- Colombian holidays
- Configured time ranges

**Rocketbot Setup:**

```
# Set input variables
SetVar("time_ranges", '[{"HoraInicio": "0700", "HoraFin": "1900"}]')
SetVar("check_holidays", True)
SetVar("timezone_offset", -5)

# Execute script
Execute("rocketbot_scripts/workflows/validate_execution_schedule.py")

# Read results
is_allowed = GetVar("is_execution_allowed")  # True/False
validation_result = GetVar("validation_result")  # Detailed result dict

# Check result
If is_allowed == True:
    # Continue with workflow
    ...
Else:
    # Stop execution
    Print("Execution blocked: " + validation_result["reason"])
```

**Result Structure:**

```json
{
    "allowed": true,
    "current_date": "2024-12-05",
    "current_time": "09:30",
    "is_holiday": false,
    "holiday_name": null,
    "is_in_time_range": true,
    "matched_time_range": {
        "HoraInicio": "0700",
        "HoraFin": "1900"
    },
    "reason": "Execution allowed"
}
```

**Time Ranges Configuration:**

```json
[
    {
        "HoraInicio": "0700",
        "HoraFin": "1200"
    },
    {
        "HoraInicio": "1300",
        "HoraFin": "2300"
    }
]
```

This allows execution from 7AM-12PM and 1PM-11PM, blocking during the lunch hour.

## Best Practices

### 1. Keep Scripts Self-Contained

- No imports from other repository modules (`shared/`, etc.)
- Use standard library when possible
- Document external dependencies in `requirements.txt`

### 2. Use `globals()` for Function Calls (Critical for Rocketbot)

**Why it matters:** Rocketbot executes scripts using Python's `exec()` with a limited namespace. Functions defined in your script may not be accessible when called from other functions.

**The Problem:**
```python
# This works in standalone Python but FAILS in Rocketbot:
def helper():
    return "data"

def main():
    result = helper()  # NameError: name 'helper' is not defined
    return result
```

**The Solution:**
```python
# This works in both standalone Python AND Rocketbot:
def helper():
    return "data"

def main():
    _helper = globals().get('helper', helper)
    result = _helper()  # Works!
    return result
```

**Pattern to follow:**
```python
def process_data(data: str) -> str:
    # When calling ANY helper function from your script:
    _my_helper = globals().get('my_helper', my_helper)
    return _my_helper(data)

# In Rocketbot wrapper:
if IN_ROCKETBOT:
    # When calling main functions:
    _main_logic = globals().get('main_logic', main_logic)
    result = _main_logic(param1, param2)
```

**When to use this:**
- ✅ When calling helper functions from main logic
- ✅ When calling main functions from Rocketbot wrapper
- ✅ Any function-to-function call within the script
- ❌ Not needed for built-in Python functions (json.loads, etc.)
- ❌ Not needed for imported library functions

### 3. Use `GetVar`/`SetVar` (Not `GetParams`)

Rocketbot provides `GetVar` and `SetVar` for variable access:

```python
# Correct:
value = GetVar("locStrMyVariable")
SetVar("locDctResult", result)

# Incorrect:
value = GetParams("my_variable")  # GetParams doesn't exist in Rocketbot
```

**Variable Naming Convention:**
- Prefix with `loc` (local variable)
- Add type hint: `Str`, `Int`, `Dct`, `Lst`, `Bln`
- Examples: `locStrName`, `locIntCount`, `locDctResult`, `locLstItems`, `locBlnIsValid`

### 4. Parse Inputs Flexibly (JSON and Python Syntax)

**Why it matters:** Rocketbot may pass complex data (lists, dicts) as strings in different formats - sometimes JSON (double quotes), sometimes Python literal syntax (single quotes).

**The Problem:**
```python
# Input might come as JSON:
time_ranges = '[{"HoraInicio": "0700", "HoraFin": "1200"}]'

# Or as Python literal:
time_ranges = "[{'HoraInicio': '0700', 'HoraFin': '1200'}]"

# Using only json.loads() fails on Python literals
import json
parsed = json.loads(time_ranges)  # ❌ Fails with single quotes!
```

**The Solution:**
```python
import json
import ast

# Register modules in globals for Rocketbot compatibility
globals()['json'] = json
globals()['ast'] = ast

def parse_input(data_input):
    """Parse input from JSON or Python literal syntax"""
    # If already parsed (list/dict), return it
    if isinstance(data_input, (list, dict)):
        return data_input

    # If string, try both formats
    if isinstance(data_input, str):
        _json = globals().get('json', json)
        _ast = globals().get('ast', ast)

        # Try JSON first (preferred format)
        try:
            return _json.loads(data_input)
        except _json.JSONDecodeError:
            # Fallback to Python literal syntax
            try:
                return _ast.literal_eval(data_input)
            except (ValueError, SyntaxError) as e:
                raise ValueError(f"Invalid input format: {e}")

    raise ValueError(f"Unsupported input type: {type(data_input)}")
```

**When to use this:**
- ✅ Parsing lists or dicts from Rocketbot variables
- ✅ When input format is uncertain (JSON vs Python syntax)
- ✅ Complex structured data (time ranges, configurations, etc.)
- ❌ Simple strings that aren't meant to be parsed
- ❌ Already-parsed Python objects

**Best practice:** Add debug logging to see what format you're receiving:
```python
print(f"DEBUG: Parsing input (type: {type(data_input).__name__})")
print(f"DEBUG: Input value: {str(data_input)[:100]}...")  # First 100 chars
```

### 5. Version Control

- Include version in script docstring
- Use semantic versioning (MAJOR.MINOR.PATCH)
- Update version on changes
- Track changes in git commits

### 6. Error Handling with Traceback

- Always use try/except blocks
- Return structured error results
- Log errors with print statements AND traceback
- Never crash - return error status instead

```python
try:
    result = process_data(data)
    return {"status": "success", "data": result}
except Exception as e:
    import traceback
    print(f"Error: {e}")
    print("Full traceback:")
    traceback.print_exc()
    return {"status": "error", "message": str(e)}
```

### 7. Testing

- Write tests for all business logic
- Use `unittest` framework
- Test both success and error cases
- Include edge cases
- Use fixtures for test data

### 8. Documentation

- Clear docstrings on all functions
- Document Rocketbot inputs/outputs (with `loc` prefix)
- Include usage examples
- Update documentation when changing code

### 9. Code Style

- Use type hints for parameters and returns
- Follow PEP 8 naming conventions
- Keep functions focused and small
- Use descriptive variable names

## Workflow Organization

As scripts grow, organize them in subdirectories:

```
workflows/
├── reporting/
│   ├── generate_daily_report.py
│   └── send_monthly_summary.py
├── data_processing/
│   ├── clean_data.py
│   └── transform_data.py
└── utilities/
    ├── validate_execution_schedule.py
    └── check_system_health.py
```

## Dependencies

Current dependencies (from `requirements.txt`):
- `holidays>=0.35` - For holiday detection

To add new dependencies:
1. Add to `requirements.txt`
2. Install: `pip install -r requirements.txt`
3. Document in script docstring

## Troubleshooting

### "NameError: name 'function_name' is not defined" in Rocketbot

**Problem:** Functions defined in your script can't be found when called.

**Cause:** Rocketbot uses `exec()` with a limited namespace, so function definitions may not be accessible.

**Solution:** Use `globals()` pattern for all function calls:

```python
# Change this:
def my_helper():
    return "data"

def main():
    result = my_helper()  # ❌ Fails in Rocketbot

# To this:
def my_helper():
    return "data"

def main():
    _my_helper = globals().get('my_helper', my_helper)
    result = _my_helper()  # ✅ Works in Rocketbot
```

See **Best Practices → Use globals() for Function Calls** for detailed explanation.

### Script not found in Rocketbot

Ensure the script path is correct relative to Rocketbot's working directory:
```
rocketbot_scripts/workflows/<script_name>.py
```

### Import errors

Scripts should be standalone. If you need shared functionality:
1. Copy code into script (for small utils)
2. Create a new standalone util script
3. Or reconsider if this should be a module instead

### Tests failing

1. Check `holidays` library is installed: `pip install holidays` or `uv pip install holidays`
2. Verify Python path includes parent directory
3. Run with verbose flag: `python -m unittest -v`
4. Activate venv if using one: `source .venv/bin/activate`

### Holiday detection not working

Install the holidays library:
```bash
# Using pip:
pip install holidays

# Using uv (faster):
uv pip install holidays

# From requirements file:
pip install -r rocketbot_scripts/requirements.txt
```

### Variables not found in Rocketbot

**Problem:** `GetParams` or variable names don't work.

**Solution:**
1. Use `GetVar`/`SetVar` (not `GetParams`)
2. Use `loc` prefix for variable names
3. Follow naming convention: `locStrName`, `locIntCount`, `locDctResult`

```python
# Correct:
value = GetVar("locStrInputData")
SetVar("locDctResult", result)

# Incorrect:
value = GetParams("input_data")  # ❌ GetParams doesn't exist
```

## Version History

### Version 1.1.0 (2025-12-05)
- Added `globals()` pattern for Rocketbot compatibility
- Updated script template with proper Rocketbot patterns
- Enhanced error handling with traceback
- Documented `GetVar`/`SetVar` usage and naming conventions
- Fixed namespace issues in `validate_execution_schedule.py`
- All 38 tests passing with `holidays` library

### Version 1.0.0 (2024-12-05)
- Initial repository structure
- First script: `validate_execution_schedule.py`
- Testing infrastructure
- Documentation

## Contributing

When adding new scripts:

1. Create script in `workflows/`
2. Follow naming conventions
3. Include comprehensive docstring
4. Create tests in `tests/`
5. Update this README if needed
6. Test thoroughly before committing
