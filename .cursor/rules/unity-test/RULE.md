---
alwaysApply: false
---
# TRYCORE Testing Guidelines

## Context
Generate Unit Tests using `pytest` that comply with the TRYCORE Quality Gate requirements.

## 1. Coverage & Scope
- **Target**: Minimum **80% Code Coverage** on NEW CODE.
- **Scope**: Focus tests on business logic and edge cases.
- **Smart Exclusions**: 
  - Do NOT write tests for generated files, DTOs without logic, or 3rd party wrappers.
  - Do NOT calculate coverage on the test files themselves.

## 2. Test Structure (AAA)
- Follow **Arrange, Act, Assert** pattern in every test function.
- Tests must be independent and isolated.

## 3. Mocking & Isolation
- **Mock External Dependencies**: NEVER hit a real Database, API, or File System in a Unit Test.
- Use `unittest.mock` or `pytest-mock` (`mocker` fixture).
- Mock the *import* of the dependency, not the instance (where possible).

## 4. Quality Gate Simulation
- Ensure tests cover:
  - Happy Path (Standard execution).
  - Edge Cases (Nulls, boundaries).
  - Exception Scenarios (Verify that the code raises the expected errors).

## Example Template
```python
import pytest
from unittest.mock import Mock, patch
from my_module import process_data

def test_process_data_should_return_valid_result():
    # Arrange
    mock_db = Mock()
    mock_db.get_user.return_value = {"id": 1}
    
    # Act
    result = process_data(mock_db)
    
    # Assert
    assert result == "Success"
    mock_db.get_user.assert_called_once()