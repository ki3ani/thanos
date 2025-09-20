#!/bin/bash

# Test runner script for thanos project
# Runs tests for both services with proper isolation

echo "🧪 Running Thanos Test Suite"
echo "============================"

# Install dependencies if needed
echo "📦 Installing test dependencies..."
pip install -q -r dev-requirements.txt
pip install -q fastapi uvicorn pydantic requests google-generativeai grpcio

echo ""
echo "🔧 Code Quality Checks"
echo "----------------------"

# Run linting
echo "🔍 Running flake8..."
flake8 recommendation-agent/main.py frontend-proxy/main.py
if [ $? -eq 0 ]; then
    echo "✅ Flake8 checks passed"
else
    echo "❌ Flake8 checks failed"
fi

echo ""
echo "🎯 Running Tests"
echo "----------------"

# Test recommendation agent
echo "🤖 Testing Recommendation Agent..."
python -m pytest tests/test_recommendation_simple.py -v --tb=short --cov=recommendation-agent --cov-report=term-missing | grep -E "(PASSED|FAILED|ERROR|===|coverage)"

echo ""
echo "🌐 Testing Frontend Proxy (core functionality)..."
python -m pytest tests/test_frontend_proxy.py::TestProxyFunctionality::test_proxy_get_request tests/test_frontend_proxy.py::TestProxyFunctionality::test_proxy_post_request tests/test_frontend_proxy.py::TestCartInterception::test_cart_interception_no_product_id -v --tb=short

echo ""
echo "📊 Overall Test Summary"
echo "======================="

# Run simplified coverage report
python -m pytest tests/test_recommendation_simple.py --cov=recommendation-agent --cov=frontend-proxy --cov-report=term-missing --quiet | tail -10

echo ""
echo "🎉 Test suite completed!"
echo "For detailed results, run: make test"
echo "For code formatting, run: make format"
echo "For linting, run: make lint"