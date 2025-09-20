# Thanos - Microservices Platform

A comprehensive microservices platform featuring AI-powered recommendations, proxy services, and real-time data processing with a complete CI/CD pipeline.

## 🏗️ Architecture

The platform consists of several microservices:

- **Frontend Proxy** (`frontend-proxy/`) - FastAPI proxy service that intercepts and processes requests
- **Recommendation Agent** (`recommendation-agent/`) - AI-powered recommendation service using Google Gemini
- **MCP Toolbox** (`mcp-toolbox/`) - Go-based toolbox service for data processing
- **UI** (`ui/`) - Static HTML frontend interface
- **Kubernetes Manifests** - Deployment configurations for Google Kubernetes Engine

## 🚀 CI/CD Pipeline

This repository features a comprehensive CI/CD pipeline with the following workflows:

### 📋 Available Workflows

1. **Continuous Integration** (`.github/workflows/ci.yml`)
   - Automated testing and quality checks
   - Docker image building
   - Security scanning with Trivy
   - Multi-service change detection

2. **Continuous Deployment** (`.github/workflows/cd.yml`)
   - Automated deployment to staging and production
   - Image building and pushing to Google Artifact Registry
   - Kubernetes deployment with rollback capabilities
   - Environment-specific deployments

3. **Quality Assurance** (`.github/workflows/qa.yml`)
   - Code formatting checks (Black, isort)
   - Linting (flake8, mypy, bandit)
   - Dockerfile linting (hadolint)
   - Kubernetes YAML validation
   - Performance testing setup

4. **Security & Dependencies** (`.github/workflows/security.yml`)
   - Weekly dependency updates
   - Vulnerability scanning
   - Automated security issue creation
   - Docker image security scanning

### 🔧 Pipeline Features

- **Smart Change Detection**: Only builds and deploys services that have changed
- **Multi-Environment Support**: Separate staging and production deployments
- **Security First**: Comprehensive security scanning at multiple levels
- **Quality Gates**: Code formatting, linting, and testing requirements
- **Automated Updates**: Weekly dependency updates with vulnerability checks
- **Rollback Capabilities**: Kubernetes rollout status monitoring

## 🛠️ Development Setup

### Prerequisites

- Python 3.11+
- Docker
- kubectl (for Kubernetes deployments)
- Google Cloud SDK (for GCP deployments)

### Local Development

1. **Clone the repository**:
   ```bash
   git clone https://github.com/ki3ani/thanos.git
   cd thanos
   ```

2. **Set up Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install black isort flake8 mypy pytest bandit
   ```

4. **Install service dependencies**:
   ```bash
   # For frontend-proxy
   cd frontend-proxy
   pip install -r requirements.txt
   cd ..
   
   # For recommendation-agent
   cd recommendation-agent
   pip install -r requirements.txt
   cd ..
   ```

### Running Services Locally

#### Frontend Proxy
```bash
cd frontend-proxy
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

#### Recommendation Agent
```bash
cd recommendation-agent
export GEMINI_API_KEY=your_api_key_here
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

## 🧪 Testing

### Running Tests
```bash
# Run all tests
pytest

# Run tests for specific service
cd frontend-proxy
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=. --cov-report=html
```

### Code Quality Checks
```bash
# Format code
black frontend-proxy/ recommendation-agent/
isort frontend-proxy/ recommendation-agent/

# Lint code
flake8 frontend-proxy/ recommendation-agent/

# Type checking
mypy frontend-proxy/ recommendation-agent/ --ignore-missing-imports

# Security scanning
bandit -r frontend-proxy/ recommendation-agent/
```

## 🐳 Docker

### Building Images
```bash
# Build frontend-proxy
docker build -t frontend-proxy ./frontend-proxy

# Build recommendation-agent
docker build -t recommendation-agent ./recommendation-agent

# Build mcp-toolbox
docker build -t mcp-toolbox ./mcp-toolbox
```

### Running with Docker Compose (Example)
```bash
# Create a docker-compose.yml file for local testing
docker-compose up -d
```

## ☸️ Kubernetes Deployment

### Manual Deployment
```bash
# Apply all Kubernetes manifests
kubectl apply -f frontend-real-service.yaml
kubectl apply -f frontend-proxy/kubernetes.yaml
kubectl apply -f recommendation-agent/kubernetes.yaml
kubectl apply -f mcp-toolbox/kubernetes.yaml

# Check deployment status
kubectl get pods
kubectl get services
```

### Environment Configuration

The deployment requires the following secrets and configuration:

1. **Google Cloud Service Account**: For pushing to Artifact Registry and deploying to GKE
2. **Gemini API Key**: For the recommendation service
3. **Database Configuration**: For the MCP toolbox service

## 📊 Monitoring and Observability

The platform includes:
- Health check endpoints for all services
- Kubernetes readiness and liveness probes
- Comprehensive logging
- Performance monitoring capabilities

## 🔐 Security

### Security Features
- Container vulnerability scanning
- Dependency vulnerability monitoring
- Security-focused linting with bandit
- Regular automated security audits
- Kubernetes security best practices

### Secrets Management
All sensitive data is managed through:
- Kubernetes secrets
- GitHub Actions secrets
- Environment variable injection

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and ensure all quality checks pass
4. Commit your changes: `git commit -m 'Add amazing feature'`
5. Push to the branch: `git push origin feature/amazing-feature`
6. Open a Pull Request

### Code Standards
- Follow PEP 8 style guidelines
- Use Black for code formatting
- Write tests for new functionality
- Ensure all CI checks pass
- Update documentation as needed

### Pull Request Process
1. Ensure all tests pass locally
2. Update documentation if needed
3. Request review from maintainers
4. Address any feedback
5. Merge after approval

## 📈 Pipeline Status

[![CI](https://github.com/ki3ani/thanos/actions/workflows/ci.yml/badge.svg)](https://github.com/ki3ani/thanos/actions/workflows/ci.yml)
[![CD](https://github.com/ki3ani/thanos/actions/workflows/cd.yml/badge.svg)](https://github.com/ki3ani/thanos/actions/workflows/cd.yml)
[![QA](https://github.com/ki3ani/thanos/actions/workflows/qa.yml/badge.svg)](https://github.com/ki3ani/thanos/actions/workflows/qa.yml)
[![Security](https://github.com/ki3ani/thanos/actions/workflows/security.yml/badge.svg)](https://github.com/ki3ani/thanos/actions/workflows/security.yml)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙋‍♂️ Support

For questions, issues, or contributions:
- Open an issue on GitHub
- Check the documentation
- Review existing discussions

## 🔄 Release Process

Releases are automatically managed through the CI/CD pipeline:
1. Changes merged to `main` trigger staging deployment
2. Manual production deployment through GitHub Actions
3. Semantic versioning based on commit messages
4. Automated release notes generation

## 📚 Additional Resources

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Cloud Documentation](https://cloud.google.com/docs)
- [Docker Best Practices](https://docs.docker.com/develop/best-practices/)

---

Built with ❤️ by the Thanos Development Team