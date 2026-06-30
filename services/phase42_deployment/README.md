# Phase 42: Deployment

## Overview

Manages the deployment lifecycle for the JARVIS assistant across Android, desktop, and cloud platforms. Provides environment profile management, packaging, health monitoring, and update/rollback capabilities.

## Components

### Environment Profiles

Three built-in profiles cover the full deployment lifecycle:

| Profile | Platform | Log Level | Features |
|---------|----------|-----------|----------|
| **development** | desktop | DEBUG | Mock services, verbose logging, debug mode |
| **staging** | cloud | INFO | External APIs in test mode, telemetry |
| **production** | cloud | WARNING | All features, resource limits, auto-scaling |

- `EnvironmentManager` auto-detects the current platform (Android via `ANDROID_ROOT`, cloud via Kubernetes/AWS/Cloud Run env vars, desktop fallback)
- Custom profiles can be registered at runtime

### Packaging

The `Packaging` component creates, extracts, verifies, and inspects deployment archives:

- **create_package**: Bundles files into a zip archive with SHA-256 checksum
- **extract_package**: Extracts a package to a destination directory
- **verify_package**: Validates package integrity via checksum comparison
- **list_contents**: Lists files in a package without extraction

### Health Checks

The `HealthChecker` monitors registered services:

- **check_service**: Check a single service by name
- **check_all**: Aggregate health across all registered services
- **is_healthy** / **get_unhealthy_services**: Quick status queries
- **start_periodic_checks** / **stop_periodic_checks**: Background monitoring with configurable interval

### Updates & Rollback

The `UpdateManager` handles version management:

- **check_for_updates**: Query remote/local for available updates
- **apply_update**: Apply a verified update manifest
- **rollback**: Revert to a previous version (specific or latest)
- **get_version_history**: List all recorded versions
- **verify_update**: Validate manifest integrity before applying

## Usage

```python
from services.phase42_deployment import DeploymentService

svc = DeploymentService()
await svc.initialize()

# Deploy a new version
pkg = await svc.deploy("1.0.0", ["/path/to/app.py", "/path/to/config.yaml"])

# Check health
health = await svc.check_health()
print(f"Health: {health.status}")

# Switch environment profile
await svc.switch_profile("production")

# Rollback to previous version
await svc.rollback()

# Get current state
state = await svc.get_state()
print(f"Current version: {state.current_version}")

await svc.shutdown()
```

## Configuration

Configuration is via environment variables with the `JARVIS_PHASE42_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `JARVIS_PHASE42_ENVIRONMENT` | `development` | Deployment environment |
| `JARVIS_PHASE42_PLATFORM` | `desktop` | Target platform |
| `JARVIS_PHASE42_ENABLE_HEALTH_CHECKS` | `true` | Enable periodic health checks |
| `JARVIS_PHASE42_HEALTH_CHECK_INTERVAL_SECONDS` | `30` | Interval between checks |
| `JARVIS_PHASE42_PACKAGE_FORMAT` | `zip` | Archive format |
| `JARVIS_PHASE42_ROLLBACK_MAX_VERSIONS` | `5` | Max rollback versions stored |
| `JARVIS_PHASE42_UPDATE_CHECK_URL` | `""` | Update server URL |
