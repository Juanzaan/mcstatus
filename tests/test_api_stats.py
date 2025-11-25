"""
Test suite for /api/stats endpoint
Tests statistics calculation accuracy
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


def test_stats_endpoint_basic(client):
    """Test basic /api/stats endpoint response"""
    response = client.get('/api/stats')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    assert 'stats' in data


def test_stats_structure(client):
    """Test stats response structure"""
    response = client.get('/api/stats')
    data = response.get_json()
    
    stats = data['stats']
    required_fields = ['total_servers', 'total_players', 'premium_count', 'cracked_count']
    
    for field in required_fields:
        assert field in stats
        assert isinstance(stats[field], int)
        assert stats[field] >= 0


def test_stats_consistency(client):
    """Test that stats are consistent with server data"""
    # Get stats
    stats_response = client.get('/api/stats')
    stats = stats_response.get_json()['stats']
    
    # Get all servers
    servers_response = client.get('/api/servers/all')
    servers_data = servers_response.get_json()
    
    # Verify total count matches
    assert stats['total_servers'] == servers_data['count']


def test_stats_endpoint_with_trailing_slash(client):
    """Test /api/stats/ (with trailing slash) also works"""
    response = client.get('/api/stats/')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    assert 'stats' in data
