"""
Test suite for health check endpoints
Tests both basic and detailed health endpoints
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.api import app


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_basic_health_endpoint(client):
    """Test /health endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] == 'healthy'
    assert 'service' in data


def test_detailed_health_endpoint(client):
    """Test /api/health endpoint"""
    response = client.get('/api/health')
    assert response.status_code in [200, 503]  # Can be 200 (healthy) or 503 (unhealthy)
    
    data = response.get_json()
    assert 'status' in data
    assert 'service' in data
    assert 'timestamp' in data
    assert 'checks' in data
    
    # Verify checks structure
    checks = data['checks']
    assert 'data_file' in checks
    assert 'data_freshness' in checks or checks['data_file']['status'] == 'error'
    assert 'scheduler' in checks
    assert 'data_loading' in checks


def test_health_data_file_check(client):
    """Test that health endpoint checks data file"""
    response = client.get('/api/health')
    data = response.get_json()
    
    data_file_check = data['checks']['data_file']
    assert 'status' in data_file_check
    assert 'exists' in data_file_check
    assert 'path' in data_file_check


def test_health_scheduler_check(client):
    """Test that health endpoint checks scheduler"""
    response = client.get('/api/health')
    data = response.get_json()
    
    scheduler_check = data['checks']['scheduler']
    assert 'status' in scheduler_check
    assert 'details' in scheduler_check or 'error' in scheduler_check


def test_health_data_loading_check(client):
    """Test that health endpoint can load data"""
    response = client.get('/api/health')
    data = response.get_json()
    
    loading_check = data['checks']['data_loading']
    assert 'status' in loading_check
    
    if loading_check['status'] == 'ok':
        assert 'server_count' in loading_check
        assert 'stats' in loading_check
