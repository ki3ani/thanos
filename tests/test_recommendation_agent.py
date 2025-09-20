"""Tests for the recommendation agent service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import HTTPException
import sys
import os

# Add the recommendation-agent directory to the path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'recommendation-agent'))


@pytest.fixture(autouse=True)
def setup_mocks():
    """Set up mocks for external dependencies before importing main."""
    with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-key'}):
        with patch('google.generativeai.configure'):
            with patch('google.generativeai.GenerativeModel') as mock_model:
                # Import main after mocking
                import main
                
                # Set up the mock model instance
                mock_model_instance = Mock()
                mock_model.return_value = mock_model_instance
                main.model = mock_model_instance
                
                yield main


@pytest.fixture
def client(setup_mocks):
    """Create a test client for the FastAPI app."""
    main = setup_mocks
    return TestClient(main.app)


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
    def test_recommend_requires_viewed_products(self, client, setup_mocks):
        """Test that recommendation endpoint requires viewed products."""
        response = client.post("/recommend", json={
            "session_id": "test-session",
            "viewed_products": []
        })
        assert response.status_code == 400
        assert "Viewed products list cannot be empty" in response.json()["detail"]
    
    @pytest.mark.unit
    def test_recommend_requires_product_catalog(self, client, setup_mocks):
        """Test that recommendation endpoint requires product catalog."""
        main = setup_mocks
        # Clear the product catalog
        main.VALID_PRODUCT_NAMES.clear()
        
        response = client.post("/recommend", json={
            "session_id": "test-session",
            "viewed_products": ["product1"]
        })
        assert response.status_code == 503
        assert "Product catalog not available" in response.json()["detail"]
    
    @pytest.mark.unit
    @patch('main.get_product_from_catalog')
    def test_recommend_success(self, mock_get_product, client, setup_mocks, sample_product):
        """Test successful recommendation flow."""
        main = setup_mocks
        # Setup mocks
        main.VALID_PRODUCT_NAMES.clear()
        main.VALID_PRODUCT_NAMES.extend(["Product A", "Product B", "Test Product"])
        
        mock_response = Mock()
        mock_response.text = "Test Product"
        main.model.generate_content.return_value = mock_response
        mock_get_product.return_value = sample_product
        
        response = client.post("/recommend", json={
            "session_id": "test-session",
            "viewed_products": ["Product A"]
        })
        
        assert response.status_code == 200
        assert response.json() == {"recommended_product": sample_product}
        
        # Verify the prompt was constructed correctly
        main.model.generate_content.assert_called_once()
        prompt_arg = main.model.generate_content.call_args[0][0]
        assert "Product A" in prompt_arg
        assert "Test Product" in prompt_arg
        
        # Clean up
        main.VALID_PRODUCT_NAMES.clear()
    
    @pytest.mark.unit
    @patch('main.get_product_from_catalog')
    def test_recommend_product_not_found(self, mock_get_product, client, setup_mocks):
        """Test recommendation when product is not found in catalog."""
        main = setup_mocks
        # Setup mocks
        main.VALID_PRODUCT_NAMES.clear()
        main.VALID_PRODUCT_NAMES.extend(["Product A", "Product B"])
        
        mock_response = Mock()
        mock_response.text = "Unknown Product"
        main.model.generate_content.return_value = mock_response
        mock_get_product.return_value = None
        
        response = client.post("/recommend", json={
            "session_id": "test-session",
            "viewed_products": ["Product A"]
        })
        
        assert response.status_code == 404
        assert "not found in catalog" in response.json()["detail"]
        
        # Clean up
        main.VALID_PRODUCT_NAMES.clear()
    
    @pytest.mark.unit
    def test_recommend_gemini_api_error(self, client, setup_mocks):
        """Test recommendation when Gemini API fails."""
        main = setup_mocks
        # Setup mocks
        main.VALID_PRODUCT_NAMES.clear()
        main.VALID_PRODUCT_NAMES.extend(["Product A", "Product B"])
        main.model.generate_content.side_effect = Exception("API Error")
        
        response = client.post("/recommend", json={
            "session_id": "test-session",
            "viewed_products": ["Product A"]
        })
        
        assert response.status_code == 500
        assert "Failed to get recommendation" in response.json()["detail"]
        
        # Clean up
        main.VALID_PRODUCT_NAMES.clear()


class TestProductCatalogIntegration:
    """Test product catalog gRPC integration."""
    
    @pytest.mark.unit
    @patch('pb.demo_pb2_grpc.ProductCatalogServiceStub')
    @patch('grpc.insecure_channel')
    def test_get_product_from_catalog_success(self, mock_channel, mock_stub_class, setup_mocks, sample_grpc_product):
        """Test successful product retrieval from catalog."""
        main = setup_mocks
        # Setup mocks
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub
        
        mock_response = Mock()
        mock_response.results = [sample_grpc_product]
        mock_stub.SearchProducts.return_value = mock_response
        
        # Call the function
        result = main.get_product_from_catalog("Test Product")
        
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
    @patch('pb.demo_pb2_grpc.ProductCatalogServiceStub')
    @patch('grpc.insecure_channel')
    def test_get_product_from_catalog_not_found(self, mock_channel, mock_stub_class, setup_mocks):
        """Test product not found in catalog."""
        main = setup_mocks
        # Setup mocks
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub
        
        mock_response = Mock()
        mock_response.results = []
        mock_stub.SearchProducts.return_value = mock_response
        
        # Call the function
        result = main.get_product_from_catalog("Non-existent Product")
        
        # Assertions
        assert result is None
    
    @pytest.mark.unit
    @patch('pb.demo_pb2_grpc.ProductCatalogServiceStub')
    @patch('grpc.insecure_channel')
    def test_get_product_from_catalog_grpc_error(self, mock_channel, mock_stub_class, setup_mocks):
        """Test gRPC error handling in product retrieval."""
        main = setup_mocks
        # Setup mocks
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub
        mock_stub.SearchProducts.side_effect = Exception("gRPC Error")
        
        # Call the function
        result = main.get_product_from_catalog("Test Product")
        
        # Assertions
        assert result is None


class TestProductCatalogSync:
    """Test product catalog synchronization on startup."""
    
    @pytest.mark.unit
    @patch('pb.demo_pb2_grpc.ProductCatalogServiceStub')
    @patch('grpc.insecure_channel')
    def test_sync_product_catalog_success(self, mock_channel, mock_stub_class, setup_mocks):
        """Test successful product catalog sync."""
        main = setup_mocks
        # Setup mocks
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub
        
        mock_product1 = Mock()
        mock_product1.name = "Product A"
        mock_product2 = Mock()
        mock_product2.name = "Product B"
        
        mock_response = Mock()
        mock_response.products = [mock_product1, mock_product2]
        mock_stub.ListProducts.return_value = mock_response
        
        # Clear and call the function
        main.VALID_PRODUCT_NAMES.clear()
        main.sync_product_catalog()
        
        # Assertions
        assert "Product A" in main.VALID_PRODUCT_NAMES
        assert "Product B" in main.VALID_PRODUCT_NAMES
        assert len(main.VALID_PRODUCT_NAMES) == 2
    
    @pytest.mark.unit
    @patch('pb.demo_pb2_grpc.ProductCatalogServiceStub')
    @patch('grpc.insecure_channel')
    def test_sync_product_catalog_grpc_error(self, mock_channel, mock_stub_class, setup_mocks):
        """Test gRPC error handling in catalog sync."""
        main = setup_mocks
        # Setup mocks
        mock_stub = Mock()
        mock_stub_class.return_value = mock_stub
        mock_stub.ListProducts.side_effect = Exception("gRPC Connection Error")
        
        # Clear and call the function
        main.VALID_PRODUCT_NAMES.clear()
        main.sync_product_catalog()
        
        # Should not crash and VALID_PRODUCT_NAMES should remain empty
        assert len(main.VALID_PRODUCT_NAMES) == 0


class TestRecommendRequestModel:
    """Test the RecommendRequest Pydantic model."""
    
    @pytest.mark.unit
    def test_recommend_request_valid_data(self, setup_mocks):
        """Test valid RecommendRequest creation."""
        main = setup_mocks
        request_data = {
            "session_id": "test-session-123",
            "viewed_products": ["Product A", "Product B"]
        }
        request = main.RecommendRequest(**request_data)
        
        assert request.session_id == "test-session-123"
        assert request.viewed_products == ["Product A", "Product B"]
    
    @pytest.mark.unit
    def test_recommend_request_missing_fields(self, setup_mocks):
        """Test RecommendRequest with missing fields."""
        main = setup_mocks
        with pytest.raises(Exception):  # Pydantic validation error
            main.RecommendRequest(session_id="test-session")
        
        with pytest.raises(Exception):  # Pydantic validation error
            main.RecommendRequest(viewed_products=["Product A"])