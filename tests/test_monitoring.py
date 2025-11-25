import pytest
from core.api import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_metrics_endpoint(client):
    """Test that /metrics returns Prometheus data"""
    response = client.get('/metrics')
    assert response.status_code == 200
    assert response.content_type.startswith('text/plain')
    data = response.get_data(as_text=True)
    
    # Check for our custom metrics
    assert 'http_requests_total' in data
    assert 'system_cpu_usage_percent' in data
    assert 'system_memory_usage_percent' in data

def test_detailed_health_system_stats(client):
    """Test that /api/health includes system stats"""
    response = client.get('/api/health')
    assert response.status_code == 200
    
    data = response.get_json()
    assert data['status'] in ['healthy', 'degraded', 'unhealthy']
    assert 'system' in data['checks']
    
    system = data['checks']['system']
    assert 'cpu_percent' in system
    assert 'memory_percent' in system
    assert isinstance(system['cpu_percent'], (int, float))
