@echo off
echo Building Docker image...
docker build --target development -t mcstatus:dev .

echo.
echo Running tests in container...
docker run --rm mcstatus:dev pytest tests/test_docker.py tests/test_health.py tests/test_api_stats.py -v

echo.
echo Tests complete!
