"""Tests for the frontend proxy service."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
import responses
import sys
import os

# Add the frontend-proxy directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'frontend-proxy'))

import main


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(main.app)


@pytest.fixture
def mock_requests():
    """Mock the requests module."""
    with patch('main.requests') as mock:
        yield mock


class TestProxyFunctionality:
    """Test the basic proxy functionality."""
    
    @pytest.mark.unit
    def test_proxy_get_request(self, client, mock_requests):
        """Test GET request proxying."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = b'{"test": "content"}'
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_requests.request.return_value = mock_response
        
        # Make request
        response = client.get("/test-path")
        
        # Assertions
        assert response.status_code == 200
        assert response.content == b'{"test": "content"}'
        
        # Verify the proxy call
        mock_requests.request.assert_called_once()
        call_args = mock_requests.request.call_args
        assert call_args[1]['method'] == 'GET'
        assert call_args[1]['url'] == 'http://frontend-real:8080/test-path'
    
    @pytest.mark.unit
    def test_proxy_post_request(self, client, mock_requests):
        """Test POST request proxying (non-cart)."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = b'{"result": "success"}'
        mock_response.status_code = 201
        mock_response.headers = {"Content-Type": "application/json"}
        mock_requests.request.return_value = mock_response
        
        # Make request
        test_data = {"key": "value"}
        response = client.post("/api/endpoint", json=test_data)
        
        # Assertions
        assert response.status_code == 201
        assert response.content == b'{"result": "success"}'
        
        # Verify the proxy call
        mock_requests.request.assert_called_once()
        call_args = mock_requests.request.call_args
        assert call_args[1]['method'] == 'POST'
        assert call_args[1]['url'] == 'http://frontend-real:8080/api/endpoint'
    
    @pytest.mark.unit
    def test_proxy_preserves_headers(self, client, mock_requests):
        """Test that proxy preserves request headers (except host)."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = b'test'
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_requests.request.return_value = mock_response
        
        # Make request with custom headers
        headers = {
            "Authorization": "Bearer token",
            "Content-Type": "application/json",
            "Host": "should-be-filtered",
            "Custom-Header": "custom-value"
        }
        response = client.get("/test", headers=headers)
        
        # Verify the proxy call
        mock_requests.request.assert_called_once()
        call_args = mock_requests.request.call_args
        forwarded_headers = call_args[1]['headers']
        
        # Check that all headers except 'host' are forwarded (headers are case-insensitive)
        header_names = [key.lower() for key in forwarded_headers.keys()]
        assert "authorization" in header_names
        assert "content-type" in header_names  
        assert "custom-header" in header_names
        assert "host" not in header_names
    
    @pytest.mark.unit
    def test_proxy_preserves_cookies(self, client, mock_requests):
        """Test that proxy preserves cookies."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = b'test'
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_requests.request.return_value = mock_response
        
        # Make request with cookies
        client.cookies.set("session_id", "test-session")
        client.cookies.set("user_pref", "test-pref")
        
        response = client.get("/test")
        
        # Verify the proxy call
        mock_requests.request.assert_called_once()
        call_args = mock_requests.request.call_args
        forwarded_cookies = call_args[1]['cookies']
        
        # Check that cookies are forwarded
        assert "session_id" in forwarded_cookies
        assert "user_pref" in forwarded_cookies


class TestCartInterception:
    """Test the cart request interception logic."""
    
    @pytest.mark.unit
    def test_cart_interception_success(self, client, mock_requests):
        """Test successful cart request interception and event publishing."""
        # Setup mock responses
        mock_proxy_response = Mock()
        mock_proxy_response.content = b'{"cart": "updated"}'
        mock_proxy_response.status_code = 200
        mock_proxy_response.headers = {"Content-Type": "application/json"}
        
        mock_mcp_response = Mock()
        mock_mcp_response.status_code = 200
        
        # Configure mock to return different responses for different calls
        mock_requests.request.return_value = mock_proxy_response
        mock_requests.post.return_value = mock_mcp_response
        
        # Prepare form data
        form_data = "product_id=test-product-123&quantity=2"
        
        # Make cart request with session cookie
        response = client.post(
            "/cart",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            cookies={"session_id": "user-456"}
        )
        
        # Assertions for the main response
        assert response.status_code == 200
        assert response.content == b'{"cart": "updated"}'
        
        # Verify MCP event was published
        mock_requests.post.assert_called_once()
        mcp_call_args = mock_requests.post.call_args
        
        # Check MCP URL
        expected_mcp_url = "http://mcp-toolbox-service:8080/mcp"
        assert expected_mcp_url in mcp_call_args[0][0]  # First positional argument
        
        # Check event data
        event_data = mcp_call_args[1]['json']
        assert event_data['topic'] == 'user-activity'
        assert event_data['event'] == 'item_added_to_cart'
        assert event_data['data']['user_id'] == 'user-456'
        assert event_data['data']['product_id'] == 'test-product-123'
        assert event_data['data']['quantity'] == '2'
        
        # Verify timeout was set
        assert mcp_call_args[1]['timeout'] == 1
    
    @pytest.mark.unit
    def test_cart_interception_no_session(self, client, mock_requests):
        """Test cart interception with no session cookie."""
        # Setup mock responses
        mock_proxy_response = Mock()
        mock_proxy_response.content = b'{"cart": "updated"}'
        mock_proxy_response.status_code = 200
        mock_proxy_response.headers = {}
        
        mock_requests.request.return_value = mock_proxy_response
        mock_requests.post.return_value = Mock(status_code=200)
        
        # Prepare form data
        form_data = "product_id=test-product&quantity=1"
        
        # Make cart request without session cookie
        response = client.post(
            "/cart",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Should still work but use default user_id
        mock_requests.post.assert_called_once()
        event_data = mock_requests.post.call_args[1]['json']
        assert event_data['data']['user_id'] == 'unknown_user'
    
    @pytest.mark.unit
    def test_cart_interception_no_product_id(self, client, mock_requests):
        """Test cart interception with missing product_id."""
        # Setup mock responses
        mock_proxy_response = Mock()
        mock_proxy_response.content = b'{"cart": "updated"}'
        mock_proxy_response.status_code = 200
        mock_proxy_response.headers = {}
        
        mock_requests.request.return_value = mock_proxy_response
        
        # Prepare form data without product_id
        form_data = "quantity=1&other_field=value"
        
        # Make cart request
        response = client.post(
            "/cart",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Should still proxy but not publish event
        assert response.status_code == 200
        mock_requests.post.assert_not_called()
    
    @pytest.mark.unit
    def test_cart_interception_mcp_error(self, client, mock_requests):
        """Test cart interception when MCP publishing fails."""
        # Setup mock responses
        mock_proxy_response = Mock()
        mock_proxy_response.content = b'{"cart": "updated"}'
        mock_proxy_response.status_code = 200
        mock_proxy_response.headers = {}
        
        mock_requests.request.return_value = mock_proxy_response
        mock_requests.post.side_effect = Exception("MCP Error")
        
        # Prepare form data
        form_data = "product_id=test-product&quantity=1"
        
        # Make cart request
        response = client.post(
            "/cart",
            content=form_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Should still return successful proxy response even if MCP fails
        assert response.status_code == 200
        assert response.content == b'{"cart": "updated"}'
    
    @pytest.mark.unit
    def test_cart_interception_malformed_data(self, client, mock_requests):
        """Test cart interception with malformed form data."""
        # Setup mock responses
        mock_proxy_response = Mock()
        mock_proxy_response.content = b'{"cart": "updated"}'
        mock_proxy_response.status_code = 200
        mock_proxy_response.headers = {}
        
        mock_requests.request.return_value = mock_proxy_response
        
        # Send malformed data (not proper form encoding)
        malformed_data = b"invalid-form-data-\xff\xfe"
        
        # Make cart request
        response = client.post(
            "/cart",
            content=malformed_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        # Should still proxy successfully even with malformed data
        assert response.status_code == 200
        assert response.content == b'{"cart": "updated"}'
        
        # Should not have published an event due to parsing error
        mock_requests.post.assert_not_called()


class TestNonCartRequests:
    """Test that non-cart requests are proxied normally."""
    
    @pytest.mark.unit
    def test_non_cart_post_request(self, client, mock_requests):
        """Test POST request to non-cart endpoint."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = b'{"result": "success"}'
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_requests.request.return_value = mock_response
        
        # Make POST request to different endpoint
        response = client.post("/api/orders", json={"item": "test"})
        
        # Should proxy normally without event publishing
        assert response.status_code == 200
        mock_requests.request.assert_called_once()
        mock_requests.post.assert_not_called()
        
        # Verify correct URL
        call_args = mock_requests.request.call_args
        assert call_args[1]['url'] == 'http://frontend-real:8080/api/orders'
    
    @pytest.mark.unit
    def test_put_request(self, client, mock_requests):
        """Test PUT request proxying."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = b'{"updated": true}'
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_requests.request.return_value = mock_response
        
        # Make PUT request
        response = client.put("/api/profile", json={"name": "Test User"})
        
        # Should proxy normally
        assert response.status_code == 200
        mock_requests.request.assert_called_once()
        
        call_args = mock_requests.request.call_args
        assert call_args[1]['method'] == 'PUT'
        assert call_args[1]['url'] == 'http://frontend-real:8080/api/profile'
    
    @pytest.mark.unit
    def test_delete_request(self, client, mock_requests):
        """Test DELETE request proxying."""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = b''
        mock_response.status_code = 204
        mock_response.headers = {}
        mock_requests.request.return_value = mock_response
        
        # Make DELETE request
        response = client.delete("/api/items/123")
        
        # Should proxy normally
        assert response.status_code == 204
        mock_requests.request.assert_called_once()
        
        call_args = mock_requests.request.call_args
        assert call_args[1]['method'] == 'DELETE'
        assert call_args[1]['url'] == 'http://frontend-real:8080/api/items/123'


class TestEnvironmentVariables:
    """Test environment variable configuration."""
    
    @pytest.mark.unit
    def test_default_toolbox_url(self):
        """Test default toolbox URL construction."""
        expected_url = "http://mcp-toolbox-service:8080"
        assert main.TOOLBOX_URL == expected_url
    
    @pytest.mark.unit
    @patch.dict(os.environ, {'TOOLBOX_SERVICE_HOST': 'custom-host', 'TOOLBOX_SERVICE_PORT': '9090'}, clear=False)
    def test_custom_toolbox_url(self):
        """Test custom toolbox URL from environment variables."""
        # Need to reload the module to pick up new env vars
        import importlib
        import sys
        
        # Remove the module from sys.modules to force reload
        if 'main' in sys.modules:
            del sys.modules['main']
        
        # Reimport with new environment
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'frontend-proxy'))
        import main
        
        expected_url = "http://custom-host:9090"
        assert main.TOOLBOX_URL == expected_url
    
    @pytest.mark.unit
    def test_real_frontend_url(self):
        """Test frontend URL configuration."""
        expected_url = "http://frontend-real:8080"
        assert main.REAL_FRONTEND_URL == expected_url


class TestResponseHandling:
    """Test response handling and forwarding."""
    
    @pytest.mark.unit
    def test_response_headers_forwarded(self, client, mock_requests):
        """Test that response headers are forwarded correctly."""
        # Setup mock response with custom headers
        mock_response = Mock()
        mock_response.content = b'test content'
        mock_response.status_code = 200
        mock_response.headers = {
            'Content-Type': 'application/json',
            'Cache-Control': 'no-cache',
            'Custom-Header': 'custom-value'
        }
        mock_requests.request.return_value = mock_response
        
        # Make request
        response = client.get("/test")
        
        # Check that headers are preserved
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/json'
        assert response.headers['Cache-Control'] == 'no-cache'
        assert response.headers['Custom-Header'] == 'custom-value'
    
    @pytest.mark.unit
    def test_response_redirects_not_followed(self, client, mock_requests):
        """Test that redirects are not automatically followed."""
        # Setup mock response with redirect
        mock_response = Mock()
        mock_response.content = b''
        mock_response.status_code = 302
        mock_response.headers = {'Location': 'http://example.com/redirect'}
        mock_requests.request.return_value = mock_response
        
        # Make request
        response = client.get("/test")
        
        # Should return redirect status without following
        assert response.status_code == 302
        
        # Verify allow_redirects=False was used
        call_args = mock_requests.request.call_args
        assert call_args[1]['allow_redirects'] is False