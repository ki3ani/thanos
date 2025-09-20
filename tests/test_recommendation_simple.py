"""Simplified tests for the recommendation agent service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import sys
import os

# Ensure clean environment for testing
for module in list(sys.modules.keys()):
    if 'main' in module or 'pb' in module:
        if module in sys.modules:
            del sys.modules[module]

# Set up paths
rec_agent_path = os.path.join(os.path.dirname(__file__), '..', 'recommendation-agent')
sys.path.insert(0, rec_agent_path)

# Mock all external dependencies before importing
with patch.dict(os.environ, {'GEMINI_API_KEY': 'test-api-key'}):
    with patch('google.generativeai.configure'):
        with patch('google.generativeai.GenerativeModel') as mock_genai_model:
            with patch('grpc.insecure_channel'):
                with patch('pb.demo_pb2_grpc.ProductCatalogServiceStub'):
                    with patch('pb.demo_pb2.Empty'):
                        with patch('pb.demo_pb2.SearchProductsRequest'):
                            # Import main after all mocking
                            import main as rec_main
                            
                            # Set up mock instances
                            mock_model_instance = Mock()
                            mock_genai_model.return_value = mock_model_instance
                            rec_main.model = mock_model_instance


class TestRecommendationAgentBasics:
    """Test basic functionality of the recommendation agent."""

    def setup_method(self):
        """Reset state before each test."""
        rec_main.VALID_PRODUCT_NAMES.clear()

    def test_health_endpoint(self):
        """Test health check endpoint."""
        client = TestClient(rec_main.app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "healthy" in data["message"]

    def test_empty_viewed_products(self):
        """Test recommendation with empty viewed products."""
        client = TestClient(rec_main.app)
        response = client.post("/recommend", json={
            "session_id": "test-session",
            "viewed_products": []
        })
        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]

    def test_no_product_catalog(self):
        """Test recommendation when product catalog is empty."""
        rec_main.VALID_PRODUCT_NAMES.clear()
        client = TestClient(rec_main.app)
        response = client.post("/recommend", json={
            "session_id": "test-session", 
            "viewed_products": ["some-product"]
        })
        assert response.status_code == 503
        assert "not available" in response.json()["detail"]

    def test_successful_recommendation(self):
        """Test successful recommendation flow."""
        # Set up test data
        rec_main.VALID_PRODUCT_NAMES.extend(["Product A", "Product B", "Recommended Product"])
        
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = "Recommended Product"
        rec_main.model.generate_content.return_value = mock_response
        
        # Mock product catalog response
        with patch.object(rec_main, 'get_product_from_catalog') as mock_get_product:
            mock_get_product.return_value = {
                "id": "rec-123",
                "name": "Recommended Product",
                "description": "A great product",
                "picture": "product.jpg",
                "priceUsd": {
                    "currencyCode": "USD",
                    "units": 25,
                    "nanos": 0
                }
            }
            
            client = TestClient(rec_main.app)
            response = client.post("/recommend", json={
                "session_id": "test-session",
                "viewed_products": ["Product A"]
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "recommended_product" in data
            assert data["recommended_product"]["name"] == "Recommended Product"

    def test_product_not_found_in_catalog(self):
        """Test when recommended product is not found in catalog."""
        rec_main.VALID_PRODUCT_NAMES.extend(["Product A", "Product B"])
        
        # Mock Gemini response
        mock_response = Mock()
        mock_response.text = "Unknown Product"
        rec_main.model.generate_content.return_value = mock_response
        
        # Mock product catalog to return None
        with patch.object(rec_main, 'get_product_from_catalog', return_value=None):
            client = TestClient(rec_main.app)
            response = client.post("/recommend", json={
                "session_id": "test-session",
                "viewed_products": ["Product A"]
            })
            
            # Due to the broad exception handling, this becomes a 500 error
            assert response.status_code == 500
            assert "Failed to get recommendation" in response.json()["detail"]

    def test_gemini_api_error(self):
        """Test when Gemini API fails."""
        rec_main.VALID_PRODUCT_NAMES.extend(["Product A", "Product B"])
        
        # Mock Gemini to raise an exception
        rec_main.model.generate_content.side_effect = Exception("API Error")
        
        client = TestClient(rec_main.app)
        response = client.post("/recommend", json={
            "session_id": "test-session",
            "viewed_products": ["Product A"]
        })
        
        assert response.status_code == 500
        assert "Failed to get recommendation" in response.json()["detail"]

    def test_request_model_validation(self):
        """Test RecommendRequest model validation."""
        # Valid request
        request = rec_main.RecommendRequest(
            session_id="test-session",
            viewed_products=["Product A", "Product B"]
        )
        assert request.session_id == "test-session"
        assert request.viewed_products == ["Product A", "Product B"]
        
        # Test validation errors
        with pytest.raises(Exception):
            rec_main.RecommendRequest(session_id="test")  # Missing viewed_products
            
        with pytest.raises(Exception):
            rec_main.RecommendRequest(viewed_products=["A"])  # Missing session_id


class TestProductCatalogMethods:
    """Test product catalog related methods."""

    def setup_method(self):
        """Reset state before each test."""
        rec_main.VALID_PRODUCT_NAMES.clear()

    def test_product_catalog_sync(self):
        """Test product catalog synchronization."""
        with patch('grpc.insecure_channel') as mock_channel:
            with patch('pb.demo_pb2_grpc.ProductCatalogServiceStub') as mock_stub_class:
                with patch('pb.demo_pb2.Empty'):
                    # Set up mocks
                    mock_stub = Mock()
                    mock_stub_class.return_value = mock_stub
                    
                    # Mock product list response
                    mock_product1 = Mock()
                    mock_product1.name = "Test Product 1"
                    mock_product2 = Mock()
                    mock_product2.name = "Test Product 2"
                    
                    mock_response = Mock()
                    mock_response.products = [mock_product1, mock_product2]
                    mock_stub.ListProducts.return_value = mock_response
                    
                    # Call sync function
                    rec_main.sync_product_catalog()
                    
                    # Verify products were added
                    assert "Test Product 1" in rec_main.VALID_PRODUCT_NAMES
                    assert "Test Product 2" in rec_main.VALID_PRODUCT_NAMES

    def test_get_product_from_catalog(self):
        """Test getting product details from catalog."""
        with patch('grpc.insecure_channel'):
            with patch('pb.demo_pb2_grpc.ProductCatalogServiceStub') as mock_stub_class:
                with patch('pb.demo_pb2.SearchProductsRequest'):
                    # Set up mocks
                    mock_stub = Mock()
                    mock_stub_class.return_value = mock_stub
                    
                    # Mock product search response
                    mock_product = Mock()
                    mock_product.id = "test-123"
                    mock_product.name = "Test Product"
                    mock_product.description = "A test product"
                    mock_product.picture = "test.jpg"
                    mock_product.price_usd.currency_code = "USD"
                    mock_product.price_usd.units = 10
                    mock_product.price_usd.nanos = 500000000
                    
                    mock_response = Mock()
                    mock_response.results = [mock_product]
                    mock_stub.SearchProducts.return_value = mock_response
                    
                    # Call function
                    result = rec_main.get_product_from_catalog("Test Product")
                    
                    # Verify result structure
                    assert result is not None
                    assert result["id"] == "test-123"
                    assert result["name"] == "Test Product"
                    assert result["priceUsd"]["units"] == 10
                    assert result["priceUsd"]["nanos"] == 500000000

    def test_get_product_from_catalog_not_found(self):
        """Test getting product when not found."""
        with patch('grpc.insecure_channel'):
            with patch('pb.demo_pb2_grpc.ProductCatalogServiceStub') as mock_stub_class:
                with patch('pb.demo_pb2.SearchProductsRequest'):
                    # Set up mocks
                    mock_stub = Mock()
                    mock_stub_class.return_value = mock_stub
                    
                    # Mock empty response
                    mock_response = Mock()
                    mock_response.results = []
                    mock_stub.SearchProducts.return_value = mock_response
                    
                    # Call function
                    result = rec_main.get_product_from_catalog("Non-existent Product")
                    
                    # Should return None
                    assert result is None