"""
Test suite for API filtering and search endpoints.
Validates the restored functionality including alternate IPs search.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from core import api
from core import database as db

@pytest.fixture
def client():
    """Create a test client"""
    api.app.config['TESTING'] = True
    with api.app.test_client() as client:
        yield client

class TestAPIRestoration:
    """Test restored API functionality"""
    
    def test_api_compile(self):
        """Verify API module compiles without errors"""
        import py_compile
        import tempfile
        
        # Compile to verify syntax
        with tempfile.TemporaryDirectory() as tmpdir:
            compiled = os.path.join(tmpdir, 'api.pyc')
            py_compile.compile('core/api.py', compiled, doraise=True)
        
        assert True, "API compiles successfully"
    
    def test_get_servers_basic(self, client):
        """Test basic /api/servers endpoint"""
        response = client.get('/api/servers')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['success'] is True
        assert 'servers' in data
        assert 'pagination' in data
    
    def test_get_servers_pagination(self, client):
        """Test pagination parameters"""
        response = client.get('/api/servers?page=1&limit=10')
        assert response.status_code == 200
        
        data = response.get_json()
        assert data['pagination']['page'] == 1
        assert data['pagination']['limit'] == 10
        assert len(data['servers']) <= 10
    
    def test_filter_by_category_premium(self, client):
        """Test filtering by premium category"""
        response = client.get('/api/servers?category=premium')
        assert response.status_code == 200
        
        data = response.get_json()
        for server in data['servers']:
            assert server.get('premium') is True
    
    def test_filter_by_category_non_premium(self, client):
        """Test filtering by non-premium category"""
        response = client.get('/api/servers?category=non_premium')
        assert response.status_code == 200
        
        data = response.get_json()
        for server in data['servers']:
            assert server.get('premium') is False or server.get('premium') is None
            assert server.get('status') == 'online'
    
    def test_search_by_ip(self, client):
        """Test search by main IP"""
        # First get a server to search for
        response = client.get('/api/servers?limit=1')
        servers = response.get_json()['servers']
        
        if servers:
            test_ip = servers[0]['ip']
            search_term = test_ip[:5]  # Partial IP search
            
            response = client.get(f'/api/servers?search={search_term}')
            assert response.status_code == 200
            
            data = response.get_json()
            assert len(data['servers']) > 0
    
    def test_search_by_alternate_ip(self, client):
        """Test search by alternate IP (NEW FEATURE)"""
        # This is the critical new functionality
        response = client.get('/api/servers')
        servers = response.get_json()['servers']
        
        # Find a server with alternate IPs
        test_server = None
        for server in servers:
            if server.get('alternate_ips') and len(server['alternate_ips']) > 0:
                test_server = server
                break
        
        if test_server:
            alt_ip = test_server['alternate_ips'][0]
            search_term = alt_ip[:5]  # Partial search
            
            response = client.get(f'/api/servers?search={search_term}')
            assert response.status_code == 200
            
            data = response.get_json()
            # Should find the server by its alternate IP
            found = any(s['ip'] == test_server['ip'] for s in data['servers'])
            assert found, f"Server with alternate IP '{alt_ip}' should be found by search"
    
    def test_filter_by_player_count(self, client):
        """Test player count filtering"""
        response = client.get('/api/servers?min_players=10&max_players=100')
        assert response.status_code == 200
        
        data = response.get_json()
        for server in data['servers']:
            players = server.get('online', 0)
            assert 10 <= players <= 100
    
    def test_filter_by_version(self, client):
        """Test version filtering"""
        response = client.get('/api/servers?version=1.20')
        assert response.status_code == 200
        
        data = response.get_json()
        for server in data['servers']:
            assert '1.20' in server.get('version', '').lower()
    
    def test_sort_by_players(self, client):
        """Test sorting by player count"""
        response = client.get('/api/servers?sort=players&limit=20')
        assert response.status_code == 200
        
        data = response.get_json()
        servers = data['servers']
        
        # Verify descending order
        for i in range(len(servers) - 1):
            assert servers[i].get('online', 0) >= servers[i+1].get('online', 0)
    
    def test_combined_filters(self, client):
        """Test multiple filters combined"""
        response = client.get('/api/servers?category=premium&min_players=5&sort=players&limit=10')
        assert response.status_code == 200
        
        data = response.get_json()
        for server in data['servers']:
            assert server.get('premium') is True
            assert server.get('online', 0) >= 5

if __name__ == '__main__':
    pytest.main([__file__, '-v'])
