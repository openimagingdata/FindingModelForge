# FastAPI Starter Template

A modern, production-ready FastAPI application template with GitHub OAuth authentication, JWT tokens, Tailwind CSS, and Alpine.js. Perfect for rapid development of web applications with contemporary best practices.

## ✨ Features

### 🔐 Authentication & Security

- **GitHub OAuth Integration**: Secure login using GitHub OAuth
- **JWT Token Management**: Access and refresh tokens with HTTP-only cookies
- **XSS Protection**: Secure token storage preventing client-side access
- **Environment-based Configuration**: Proper secrets management

### 🎨 Modern Frontend

- **Tailwind CSS**: Utility-first CSS framework with custom dark theme
- **Alpine.js**: Lightweight JavaScript framework for interactivity
- **Jinja2 Templates**: Server-side rendering with template inheritance
- **Flowbite Components**: Pre-built UI components for rapid development
- **Responsive Design**: Mobile-first design with blue/purple color scheme
- **Dark Mode Support**: System preference detection with manual toggle

### 🔧 Developer Experience

- **uv Package Management**: Fast, modern Python package manager
- **Ruff Linting & Formatting**: Lightning-fast code quality tools
- **MyPy Type Checking**: Static type analysis for Python
- **Pre-commit Hooks**: Automated code quality checks
- **Hot Reload**: Fast development feedback loop

### 🐳 Production Ready

- **Docker Support**: Multi-stage builds for development and production
- **Health Check Endpoints**: Kubernetes-ready monitoring endpoints
- **GitHub Actions CI/CD**: Automated testing and Docker builds
- **Security Scanning**: Dependency and code security checks

## 🚀 Quick Start

### Prerequisites

- [Python 3.13+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/) package manager
- [Docker](https://docker.com) (optional)
- [GitHub OAuth App](https://github.com/settings/applications/new)

### Installation

1. **Clone and setup the project:**

   ```bash
   git clone https://github.com/openimagingdata/FindingModelForge.git
   cd FindingModelForge/fastapi-starter
   ```

2. **Install uv (if not already installed):**

   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. **Install dependencies:**

   ```bash
   uv sync --all-extras --dev
   ```

4. **Configure environment:**

   ```bash
   cp .env.example .env
   # Edit .env with your GitHub OAuth credentials
   ```

5. **Run the development server:**

   ```bash
   ./scripts/dev.sh
   # Or manually: uv run uvicorn app.main:app --reload
   ```

6. **Visit the application:**

   - Web Interface: <http://localhost:8000>
   - API Documentation: <http://localhost:8000/docs>
   - Health Check: <http://localhost:8000/api/health>

### GitHub OAuth Setup

1. Go to [GitHub Developer Settings](https://github.com/settings/applications/new)
2. Create a new OAuth App with these settings:
   - **Application name**: FastAPI Starter (or your app name)
   - **Homepage URL**: `http://localhost:8000`
   - **Authorization callback URL**: `http://localhost:8000/auth/callback`
3. Copy the Client ID and Client Secret to your `.env` file:

   ```env
   GITHUB_CLIENT_ID=your_client_id_here
   GITHUB_CLIENT_SECRET=your_client_secret_here
   ```

## 📁 Project Structure

```text
fastapi-starter/
├── app/                    # FastAPI application
│   ├── main.py            # Main application entry point
│   ├── auth.py            # Authentication utilities and JWT handling
│   ├── config.py          # Configuration management
│   ├── models.py          # Pydantic models for data validation
│   ├── health.py          # Health check endpoints
│   └── routers/           # API route modules
│       ├── auth.py        # Authentication routes
│       └── pages.py       # Page rendering routes
├── static/                # Static assets
│   ├── css/style.css      # Custom CSS with dark theme
│   ├── js/app.js          # Alpine.js utilities and app logic
│   └── images/            # SVG icons and favicon
├── templates/             # Jinja2 templates
│   ├── base.html          # Base template with Tailwind and Alpine.js
│   ├── index.html         # Landing page with features showcase
│   ├── login.html         # GitHub OAuth login page
│   ├── dashboard.html     # Protected user dashboard
│   └── components/        # Reusable template components
│       ├── navbar.html    # Navigation with authentication state
│       └── footer.html    # Information footer
├── scripts/               # Development and deployment scripts
├── tests/                 # Test files
├── .github/workflows/     # CI/CD configuration
├── pyproject.toml         # Python project configuration
├── uv.toml               # uv package manager configuration
├── Dockerfile            # Multi-stage container configuration
├── docker-compose.yml    # Development environment
└── README.md             # This file
```

## 🛠️ Development

### Available Scripts

- **`./scripts/dev.sh`**: Start development server with hot reload
- **`./scripts/test.sh`**: Run tests with coverage and quality checks
- **`./scripts/lint.sh`**: Format code and fix linting issues
- **`./scripts/check.sh`**: Run quality checks (CI-friendly)
- **`./scripts/build.sh`**: Build production Docker image

### Development Workflow

1. **Start the development server:**

   ```bash
   ./scripts/dev.sh
   ```

2. **Run tests:**

   ```bash
   ./scripts/test.sh
   ```

3. **Format and lint code:**

   ```bash
   ./scripts/lint.sh
   ```

4. **Install pre-commit hooks:**

   ```bash
   uv run pre-commit install
   ```

### Code Quality Tools

- **Ruff**: Lightning-fast linting and formatting
- **MyPy**: Static type checking
- **Pytest**: Testing framework with coverage
- **Pre-commit**: Automated quality checks on commit

## 🐳 Docker Usage

### Development with Docker Compose

```bash
# Start all services
docker-compose up

# Build and start
docker-compose up --build

# Run in background
docker-compose up -d
```

### Production Build

```bash
# Build production image
./scripts/build.sh

# Or manually
docker build -t fastapi-starter:latest .

# Run production container
docker run -p 8000:8000 --env-file .env fastapi-starter:latest
```

## 🔧 Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# Application
APP_NAME="FastAPI Starter"
DEBUG=true
ENVIRONMENT="development"

# Security
SECRET_KEY="your-secret-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# GitHub OAuth
GITHUB_CLIENT_ID="your-github-client-id"
GITHUB_CLIENT_SECRET="your-github-client-secret"

# Server
HOST="0.0.0.0"
PORT=8000
```

### Advanced Configuration

The application uses Pydantic settings for configuration management. See `app/config.py` for all available options.

## 🧪 Testing

### Running Tests

```bash
# Run all tests with coverage
./scripts/test.sh

# Run specific test file
uv run pytest tests/test_auth.py

# Run with verbose output
uv run pytest -v

# Run tests matching pattern
uv run pytest -k "test_health"
```

### Test Coverage

The project aims for high test coverage. Coverage reports are generated in HTML format:

```bash
# Generate coverage report
uv run pytest --cov=app --cov-report=html
open htmlcov/index.html
```

## 🚀 Deployment

### GitHub Actions CI/CD

The project includes a complete CI/CD pipeline:

- **Testing**: Automated testing on push/PR
- **Security**: Dependency and code security scanning
- **Building**: Docker image builds and pushes to GitHub Container Registry
- **Deployment**: Configurable deployment hooks

### Health Monitoring

Health check endpoints for monitoring:

- **`/api/health`**: Basic health status
- **`/api/health/ready`**: Readiness check (for load balancers)
- **`/api/health/live`**: Liveness check (for container orchestrators)

### Production Checklist

- [ ] Set strong `SECRET_KEY` in production
- [ ] Configure GitHub OAuth with production URLs
- [ ] Set up SSL/TLS termination
- [ ] Configure monitoring and logging
- [ ] Set up backup strategies
- [ ] Review security headers and CORS settings

## 🎨 Customization

### Styling

- **Colors**: Modify Tailwind configuration in `templates/base.html`
- **Components**: Add/modify components in `templates/components/`
- **Custom CSS**: Edit `static/css/style.css`

### Authentication

- **OAuth Providers**: Extend `app/auth.py` for additional providers
- **User Model**: Modify `app/models.py` for additional user fields
- **Permissions**: Add role-based access control

### Database Integration

The template uses in-memory storage by default. To add database support:

1. Add database dependencies to `pyproject.toml`
2. Configure database settings in `app/config.py`
3. Create database models and connection logic
4. Update user management in `app/auth.py`

## 📖 API Documentation

### Interactive Documentation

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Home page |
| `/login` | GET | Login page |
| `/dashboard` | GET | Protected dashboard |
| `/auth/login` | GET | GitHub OAuth redirect |
| `/auth/callback` | GET | OAuth callback handler |
| `/auth/logout` | GET/POST | Logout user |
| `/auth/me` | GET | Current user info |
| `/api/health` | GET | Health check |

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- Follow existing code style (enforced by Ruff)
- Add tests for new functionality
- Update documentation as needed
- Ensure all CI checks pass

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](../LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework
- [Alpine.js](https://alpinejs.dev/) - Lightweight JavaScript framework
- [uv](https://docs.astral.sh/uv/) - Fast Python package manager
- [Ruff](https://docs.astral.sh/ruff/) - Fast Python linter and formatter

## 🆘 Support

- **Documentation**: Check this README and inline code comments
- **Issues**: [GitHub Issues](https://github.com/openimagingdata/FindingModelForge/issues)
- **Discussions**: [GitHub Discussions](https://github.com/openimagingdata/FindingModelForge/discussions)

---

## Happy coding! 🎉
