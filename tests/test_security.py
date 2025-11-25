import pytest
import json
import random
import string
from core.api import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def generate_random_string(length=100):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class TestAPISecurity:
    
    def test_security_headers(self, client):
        """Test presence of basic security headers"""
        response = client.get('/health')
        # Flask default doesn't add many, but we should check if we add CORS
        assert 'Access-Control-Allow-Origin' in response.headers

    def test_404_handling(self, client):
        """Ensure 404s are handled gracefully (no stack traces leak)"""
        response = client.get('/api/non_existent_endpoint_12345')
        assert response.status_code == 404
        assert response.is_json
        data = response.get_json()
        assert 'error' in data

    def test_method_not_allowed(self, client):
        """Ensure 405 for wrong methods"""
        # /api/servers is GET only
        response = client.post('/api/servers')
        assert response.status_code == 405

    def test_input_fuzzing_pagination(self, client):
        """Fuzzing pagination parameters with invalid types/values"""
        fuzz_inputs = [
            '-1', '0', 'abc', '1.5', '999999999999999999', 
            '<script>alert(1)</script>', '%00'
        ]
        
        for val in fuzz_inputs:
            response = client.get(f'/api/servers?page={val}&limit={val}')
            # Should return 200 (handled gracefully with defaults) or 400
            # But NEVER 500
            assert response.status_code in [200, 400]

    def test_input_fuzzing_search(self, client):
        """Fuzzing search parameter with long strings and special chars"""
        long_str = generate_random_string(10000)
        special_chars = "' OR 1=1; --"
        
        for val in [long_str, special_chars]:
            response = client.get(f'/api/servers?search={val}')
            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data.get('servers'), list)

    def test_scheduler_auth_bypass_attempt(self, client):
        """
        If we had auth, we'd test bypass here. 
        For now, just ensure it accepts valid types and rejects invalid ones safely.
        """
        # Valid type
        response = client.post('/api/scheduler/run_now?type=refresh_status')
        assert response.status_code in [200, 202]
        
        # Invalid type (Fuzzing)
        response = client.post('/api/scheduler/run_now?type=DELETE_ALL')
        assert response.status_code == 400
