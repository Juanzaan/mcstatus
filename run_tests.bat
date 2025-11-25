@echo off
echo Running tests with pytest...
pytest tests/ -v --cov=core --cov-report=html --cov-report=term
echo.
echo Coverage report generated in htmlcov/index.html
pause
