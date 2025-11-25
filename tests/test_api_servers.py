"""
Test suite for /api/servers endpoint
Tests pagination, filtering, and sorting functionality
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


def test_servers_endpoint_basic(client):
    """Test basic /api/servers endpoint response"""
    response = client.get('/api/servers')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['success'] is True
    assert 'servers' in data
    assert 'pagination' in data
    assert isinstance(data['servers'], list)


def test_servers_pagination(client):
    """Test pagination parameters"""
    # Test page 1
    response = client.get('/api/servers?page=1&limit=10')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['pagination']['page'] == 1
    assert data['pagination']['limit'] == 10
    assert len(data['servers']) <= 10
    
    # Test page 2
    response = client.get('/api/servers?page=2&limit=10')
    assert response.status_code == 200
    data = response.get_json()
    assert data['pagination']['page'] == 2


def test_servers_filtering_category(client):
    """Test category filtering"""
    # Test premium filter
    response = client.get('/api/servers?category=premium')
    assert response.status_code == 200
    
    data = response.get_json()
    for server in data['servers']:
        assert server.get('premium') is True
    
    # Test non-premium filter
    response = client.get('/api/servers?category=non_premium')
    assert response.status_code == 200
    
    data = response.get_json()
    for server in data['servers']:
        assert server.get('premium') is False
        assert server.get('status') == 'online'


def test_servers_search(client):
    """Test search functionality"""
    response = client.get('/api/servers?search=hypixel')
    assert response.status_code == 200
    
    data = response.get_json()
    # Search should return results containing 'hypixel' in name, ip, or description
    for server in data['servers']:
        search_term = 'hypixel'
        found = (
            search_term in server.get('ip', '').lower() or
            search_term in server.get('name', '').lower() or
            search_term in server.get('description', '').lower()
        )
        assert found is True


def test_servers_player_count_filter(client):
    """Test min/max player count filtering"""
    response = client.get('/api/servers?min_players=100')
    assert response.status_code == 200
    
    data = response.get_json()
    for server in data['servers']:
        assert server.get('online', 0) >= 100


def test_servers_sorting(client):
    """Test sorting functionality"""
    # Sort by players (descending)
    response = client.get('/api/servers?sort=players&limit=20')
    assert response.status_code == 200
    
    data = response.get_json()
    servers = data['servers']
    
    # Verify descending order
    for i in range(len(servers) - 1):
        assert servers[i].get('online', 0) >= servers[i + 1].get('online', 0)


def test_servers_combined_filters(client):
    """Test multiple filters combined"""
    response = client.get('/api/servers?category=premium&min_players=50&sort=players&limit=5')
    assert response.status_code == 200
    
    data = response.get_json()
    assert len(data['servers']) <= 5
    
    for server in data['servers']:
        assert server.get('premium') is True
        assert server.get('online', 0) >= 50


def test_pagination_metadata(client):
    """Test pagination metadata accuracy"""
    response = client.get('/api/servers?limit=50')
    assert response.status_code == 200
    
    data = response.get_json()
    pagination = data['pagination']
    
    assert 'total_items' in pagination
    assert 'total_pages' in pagination
    assert pagination['total_pages'] == (pagination['total_items'] + pagination['limit'] - 1) // pagination['limit']
