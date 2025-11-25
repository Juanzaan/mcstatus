"""
Tests to run inside Docker container
Validates that the containerized application works correctly
"""
import pytest
import requests
import time


BASE_URL = "http://localhost:5000"


def wait_for_api(max_retries=30, delay=1):
    """Wait for API to be ready"""
    for i in range(max_retries):
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                return True
        except requests.exceptions.RequestException:
            pass
        time.sleep(delay)
    return False


def test_api_is_running():
    """Test that API is accessible"""
    assert wait_for_api(), "API did not start within timeout period"


def test_health_endpoint():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'


def test_detailed_health_endpoint():
    """Test detailed health endpoint"""
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code in [200, 503]
    data = response.json()
    assert 'status' in data
    assert 'checks' in data


def test_stats_endpoint():
    """Test stats endpoint"""
    response = requests.get(f"{BASE_URL}/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert 'stats' in data


def test_servers_endpoint():
    """Test servers endpoint with pagination"""
    response = requests.get(f"{BASE_URL}/api/servers?page=1&limit=10")
    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert 'servers' in data
    assert 'pagination' in data
    assert len(data['servers']) <= 10


def test_environment_configuration():
    """Test that environment variables are properly configured"""
    response = requests.get(f"{BASE_URL}/api/health")
    data = response.json()
    
    # Should have data file check
    assert 'data_file' in data['checks']
    
    # Should have scheduler check
    assert 'scheduler' in data['checks']
