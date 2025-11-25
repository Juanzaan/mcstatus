# Minecraft Server Scanner - Tests

This directory contains the test suite for the scanner.

## Running Tests

```bash
# Install pytest
pip install pytest

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_database.py -v

# Run with coverage
pip install pytest-cov
pytest tests/ --cov=. --cov-report=html
```

## Test Files

- `test_database.py` - Database operations and caching
- `test_scanner.py` - Scanner utility functions and retry logic

## Test Coverage

- ✅ Database initialization
- ✅ Scan creation
- ✅ Player UUID storage
- ✅ Geolocation caching with TTL
- ✅ Server data storage
- ✅ Statistics aggregation
- ✅ VarInt/String packing
- ✅ Retry logic with exponential backoff
- ✅ Icon saving

## Adding Tests

Create new test files following the pattern:

```python
import pytest

def test_feature_name():
    """Test description"""
    # Arrange
    # Act
    # Assert
    pass
```
