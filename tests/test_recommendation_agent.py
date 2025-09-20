"""Tests for the recommendation agent service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import sys
import os

# Ensure clean imports by clearing any cached modules
for module_name in list(sys.modules.keys()):
    if module_name == 'main':
        del sys.modules[module_name]

# Add the recommendation-agent directory to the path for imports
rec_agent_path = os.path.join(os.path.dirname(__file__), '..', 'recommendation-agent')
if rec_agent_path not in sys.path:
    sys.path.insert(0, rec_agent_path)


@pytest.fixture(scope="function")
def mock_env_and_deps():
    """Set up mocks for external dependencies."""
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
        with patch('google.generativeai.configure') as mock_configure:
            with patch('google.generativeai.GenerativeModel') as mock_model_class:
                with patch('pb.demo_pb2_grpc') as mock_grpc:
                    with patch('pb.demo_pb2') as mock_pb2:
                        # Set up mock model instance
                        mock_model_instance = Mock()
                        mock_model_class.return_value = mock_model_instance
                        
                        yield {
                            'model_instance': mock_model_instance,
                            'model_class': mock_model_class,
                            'configure': mock_configure,
                            'grpc': mock_grpc,
                            'pb2': mock_pb2
                        }


@pytest.fixture
def recommendation_main(mock_env_and_deps):
    """Import and return the recommendation main module with mocked dependencies."""
    # Force reimport of main module
    import importlib
    import main as rec_main
    importlib.reload(rec_main)
    
    # Inject the mock model instance
    rec_main.model = mock_env_and_deps['model_instance']
    
    return rec_main


@pytest.fixture
def client(recommendation_main):
    """Create a test client for the FastAPI app."""
    return TestClient(recommendation_main.app)


@pytest.fixture
def mock_grpc_channel():
    """Mock gRPC channel and stub."""
    with patch('grpc.insecure_channel') as mock_channel:
        mock_stub = Mock()
        mock_channel.return_value = Mock()
        yield mock_channel, mock_stub


@pytest.fixture
def sample_product():
    """Sample product data for testing."""
    return {
        "id": "test-id",
        "name": "Test Product",
        "description": "A test product",
        "picture": "test.jpg",
        "priceUsd": {
            "currencyCode": "USD",
            "units": 10,
            "nanos": 500000000
        }
    }


@pytest.fixture
def sample_grpc_product():
    """Sample gRPC product response."""
    product = Mock()
    product.id = "test-id"
    product.name = "Test Product"
    product.description = "A test product"
    product.picture = "test.jpg"
    product.price_usd.currency_code = "USD"
    product.price_usd.units = 10
    product.price_usd.nanos = 500000000
    return product


class TestHealthCheck:
    """Test health check endpoint."""
    
    @pytest.mark.unit
    def test_health_check_returns_ok(self, client):
        """Test that health check returns OK status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ok", 
            "message": "Recommendation agent is healthy"
        }


class TestRecommendationEndpoint:
    """Test the recommendation endpoint."""
    
    @pytest.mark.unit
    def test_recommend_requires_viewed_products(self, client):
        """Test that recommendation endpoint requires viewed products."""
        response = client.post("/recommend", json={
            "session_id": "test-session",
            "viewed_products": []
        })
        assert response.status_code == 400
        assert "Viewed products list cannot be empty" in response.json()["detail"]
    
    @pytest.mark.unit
    def test_recommend_requires_product_catalog(self, client, recommendation_main):
        """Test that recommendation endpoint requires product catalog."""
        # Clear the product catalog
        recommendation_main.VALID_PRODUCT_NAMES.clear()
        
        response = client.post("/recommend", json={
            "session_id": "test-session",
            "viewed_products": ["product1"]
        })
        assert response.status_code == 503
        assert "Product catalog not available" in response.json()["detail"]
    
    @pytest.mark.unit
    def test_recommend_success(self, client, recommendation_main, sample_product, mock_env_and_deps):
        """Test successful recommendation flow."""
        # Setup mocks
        recommendation_main.VALID_PRODUCT_NAMES.clear()
        recommendation_main.VALID_PRODUCT_NAMES.extend(["Product A", "Product B", "Test Product"])
        
        mock_response = Mock()
        mock_response.text = "Test Product"
        mock_env_and_deps['model_instance'].generate_content.return_value = mock_response
        
        with patch.object(recommendation_main, 'get_product_from_catalog', return_value=sample_product):
            response = client.post("/recommend", json={
                "session_id": "test-session",
                "viewed_products": ["Product A"]
            })
        
        assert response.status_code == 200
        assert response.json() == {"recommended_product": sample_product}
        
        # Verify the prompt was constructed correctly
        mock_env_and_deps['model_instance'].generate_content.assert_called_once()
        prompt_arg = mock_env_and_deps['model_instance'].generate_content.call_args[0][0]
        assert "Product A" in prompt_arg
        assert "Test Product" in prompt_arg
        
        # Clean up
        recommendation_main.VALID_PRODUCT_NAMES.clear()
    
    @pytest.mark.unit
    def test_recommend_product_not_found(self, client, recommendation_main, mock_env_and_deps):
        """Test recommendation when product is not found in catalog."""
        # Setup mocks
        recommendation_main.VALID_PRODUCT_NAMES.clear()
        recommendation_main.VALID_PRODUCT_NAMES.extend(["Product A", "Product B"])
        
        mock_response = Mock()
        mock_response.text = "Unknown Product"
        mock_env_and_deps['model_instance'].generate_content.return_value = mock_response
        
        with patch.object(recommendation_main, 'get_product_from_catalog', return_value=None):
            response = client.post("/recommend", json={
                "session_id": "test-session",
                "viewed_products": ["Product A"]
            })
        
        assert response.status_code == 404
        assert "not found in catalog" in response.json()["detail"]
        
        # Clean up
        recommendation_main.VALID_PRODUCT_NAMES.clear()
    
    @pytest.mark.unit
    def test_recommend_gemini_api_error(self, client, recommendation_main, mock_env_and_deps):
        """Test recommendation when Gemini API fails."""
        # Setup mocks
        recommendation_main.VALID_PRODUCT_NAMES.clear()
        recommendation_main.VALID_PRODUCT_NAMES.extend(["Product A", "Product B"])
        mock_env_and_deps['model_instance'].generate_content.side_effect = Exception("API Error")
        
        response = client.post("/recommend", json={
            "session_id": "test-session",
            "viewed_products": ["Product A"]
        })
        
        assert response.status_code == 500
        assert "Failed to get recommendation" in response.json()["detail"]
        
        # Clean up
        recommendation_main.VALID_PRODUCT_NAMES.clear()


class TestProductCatalogIntegration:
    """Test product catalog gRPC integration."""
    
    @pytest.mark.unit
    def test_get_product_from_catalog_success(self, recommendation_main, sample_grpc_product, mock_env_and_deps):
        """Test successful product retrieval from catalog."""
        # Setup mocks
        mock_stub = Mock()
        mock_env_and_deps['grpc'].ProductCatalogServiceStub.return_value = mock_stub
        
        mock_response = Mock()
        mock_response.results = [sample_grpc_product]
        mock_stub.SearchProducts.return_value = mock_response
        
        with patch('grpc.insecure_channel'):
            # Call the function
            result = recommendation_main.get_product_from_catalog("Test Product")
        
        # Assertions
        assert result is not None
        assert result["id"] == "test-id"
        assert result["name"] == "Test Product"
        assert result["description"] == "A test product"
        assert result["picture"] == "test.jpg"
        assert result["priceUsd"]["currencyCode"] == "USD"
        assert result["priceUsd"]["units"] == 10
        assert result["priceUsd"]["nanos"] == 500000000
    
    @pytest.mark.unit
    def test_get_product_from_catalog_not_found(self, recommendation_main, mock_env_and_deps):
        """Test product not found in catalog."""
        # Setup mocks
        mock_stub = Mock()
        mock_env_and_deps['grpc'].ProductCatalogServiceStub.return_value = mock_stub
        
        mock_response = Mock()
        mock_response.results = []
        mock_stub.SearchProducts.return_value = mock_response
        
        with patch('grpc.insecure_channel'):
            # Call the function
            result = recommendation_main.get_product_from_catalog("Non-existent Product")
        
        # Assertions
        assert result is None
    
    @pytest.mark.unit
    def test_get_product_from_catalog_grpc_error(self, recommendation_main, mock_env_and_deps):
        """Test gRPC error handling in product retrieval."""
        # Setup mocks
        mock_stub = Mock()
        mock_env_and_deps['grpc'].ProductCatalogServiceStub.return_value = mock_stub
        mock_stub.SearchProducts.side_effect = Exception("gRPC Error")
        
        with patch('grpc.insecure_channel'):
            # Call the function
            result = recommendation_main.get_product_from_catalog("Test Product")
        
        # Assertions
        assert result is None


class TestProductCatalogSync:
    """Test product catalog synchronization on startup."""
    
    @pytest.mark.unit
    def test_sync_product_catalog_success(self, recommendation_main, mock_env_and_deps):
        """Test successful product catalog sync."""
        # Setup mocks
        mock_stub = Mock()
        mock_env_and_deps['grpc'].ProductCatalogServiceStub.return_value = mock_stub
        
        mock_product1 = Mock()
        mock_product1.name = "Product A"
        mock_product2 = Mock()
        mock_product2.name = "Product B"
        
        mock_response = Mock()
        mock_response.products = [mock_product1, mock_product2]
        mock_stub.ListProducts.return_value = mock_response
        
        with patch('grpc.insecure_channel'):
            # Clear and call the function
            recommendation_main.VALID_PRODUCT_NAMES.clear()
            recommendation_main.sync_product_catalog()
        
        # Assertions
        assert "Product A" in recommendation_main.VALID_PRODUCT_NAMES
        assert "Product B" in recommendation_main.VALID_PRODUCT_NAMES
        assert len(recommendation_main.VALID_PRODUCT_NAMES) == 2
    
    @pytest.mark.unit
    def test_sync_product_catalog_grpc_error(self, recommendation_main, mock_env_and_deps):
        """Test gRPC error handling in catalog sync."""
        # Setup mocks
        mock_stub = Mock()
        mock_env_and_deps['grpc'].ProductCatalogServiceStub.return_value = mock_stub
        mock_stub.ListProducts.side_effect = Exception("gRPC Connection Error")
        
        with patch('grpc.insecure_channel'):
            # Clear and call the function
            recommendation_main.VALID_PRODUCT_NAMES.clear()
            recommendation_main.sync_product_catalog()
        
        # Should not crash and VALID_PRODUCT_NAMES should remain empty
        assert len(recommendation_main.VALID_PRODUCT_NAMES) == 0


class TestRecommendRequestModel:
    """Test the RecommendRequest Pydantic model."""
    
    @pytest.mark.unit
    def test_recommend_request_valid_data(self, recommendation_main):
        """Test valid RecommendRequest creation."""
        request_data = {
            "session_id": "test-session-123",
            "viewed_products": ["Product A", "Product B"]
        }
        request = recommendation_main.RecommendRequest(**request_data)
        
        assert request.session_id == "test-session-123"
        assert request.viewed_products == ["Product A", "Product B"]
    
    @pytest.mark.unit
    def test_recommend_request_missing_fields(self, recommendation_main):
        """Test RecommendRequest with missing fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            recommendation_main.RecommendRequest(session_id="test-session")
        
        with pytest.raises(Exception):  # Pydantic validation error
            recommendation_main.RecommendRequest(viewed_products=["Product A"])