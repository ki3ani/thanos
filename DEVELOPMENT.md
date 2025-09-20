# Development Guide

## Quick Start

1. **Setup Development Environment**:
   ```bash
   make dev-setup
   ```

2. **Run Services Locally with Docker**:
   ```bash
   # Copy environment template
   cp .env.example .env
   # Edit .env with your configuration
   
   # Start all services
   docker-compose -f docker-compose.dev.yml up -d
   ```

3. **Access Services**:
   - UI: http://localhost:3000
   - Frontend Proxy: http://localhost:8080  
   - Recommendation Agent: http://localhost:8081
   - MCP Toolbox: http://localhost:8082

## Development Commands

```bash
# Format code
make format

# Run linting
make lint  

# Run tests
make test

# Run security scans
make security

# Build all images
make build-all

# Clean up
make clean
```

## Environment Variables

Create a `.env` file in the root directory:

```bash
# Google Gemini API Key (required for recommendation agent)
GEMINI_API_KEY=your_gemini_api_key_here

# Development settings
DEBUG=true
LOG_LEVEL=debug
```

## Testing

### Unit Tests
```bash
# Run all tests
pytest

# Run specific service tests  
cd frontend-proxy && pytest tests/
cd recommendation-agent && pytest tests/
```

### Integration Tests
```bash
# Start services first
docker-compose -f docker-compose.dev.yml up -d

# Run integration tests
python scripts/integration-tests.py
```

### Load Testing
```bash
# Install locust
pip install locust

# Run load tests
cd tests/performance
locust -f locustfile.py --host=http://localhost:8080
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and ensure all checks pass:
   ```bash
   make ci  # Runs formatting, linting, tests, and security checks
   ```  
4. Submit a pull request

## CI/CD Pipeline

The repository includes comprehensive CI/CD workflows:

- **Continuous Integration**: Code quality, testing, and security
- **Continuous Deployment**: Automated deployments to staging/production  
- **Quality Assurance**: Comprehensive code quality checks
- **Security Monitoring**: Regular vulnerability scanning
- **Infrastructure Monitoring**: Health checks and alerting

All workflows are triggered automatically on pushes and pull requests.

## Troubleshooting

### Common Issues

1. **Docker build failures**:
   - Check Docker daemon is running
   - Verify Dockerfile syntax
   - Check available disk space

2. **Service connection errors**:
   - Verify services are running: `docker-compose ps`
   - Check logs: `docker-compose logs <service-name>`
   - Verify port mappings

3. **Test failures**:
   - Install test dependencies: `pip install pytest pytest-asyncio`
   - Check service dependencies are running
   - Review test output for specific errors

### Getting Help

- Check the main [README.md](README.md) for architecture overview
- Review workflow logs in GitHub Actions
- Open an issue for bugs or questions