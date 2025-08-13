# 🐳 Docker Workflow with GitHub Actions

Complete automated Docker build and push system using GitHub Container Registry (GHCR).

## 🚀 Quick Start

### 1. **Local Development**
```bash
# Make sure you have the local token
echo 'export GHCR_NEW="ghp_yourTokenHere"' > .cursor_secrets/ghcr.env

# Build and push locally
./scripts/docker-build.sh push

# Or just build locally
./scripts/docker-build.sh build
```

### 2. **Automated CI/CD**
- Push to `main` or `develop` branch → Automatic build and push
- Create a tag (e.g., `v1.0.0`) → Automatic versioned release
- Pull request → Security scan and validation

## 📁 Workflow Files

### **Main Build Workflow** (`.github/workflows/docker-build.yml`)
- 🔄 Triggers on push to main/develop branches
- 🏷️ Automatic tagging (branch, commit hash, latest)
- 🚀 Multi-platform support (amd64, arm64)
- 💾 GitHub Actions cache for faster builds

### **Multi-Platform Build** (`.github/workflows/multi-platform-build.yml`)
- 🖥️ Builds for multiple CPU architectures
- 📦 Optimized for different platforms
- 🔄 Matrix strategy for parallel builds

### **Security Scanner** (`.github/workflows/security-scan.yml`)
- 🛡️ Trivy vulnerability scanning
- 🔒 Runs on every pull request
- 📊 Results in GitHub Security tab

## 🔐 Authentication Setup

### **Repository Secrets** (Already configured ✅)
- `GHCR_NEW` - Main authentication token
- `GHCR_TOKEN` - Backup token

### **Local Development**
```bash
# Create secrets directory (git-ignored)
mkdir -p .cursor_secrets

# Store your token
echo 'export GHCR_NEW="ghp_yourTokenHere"' > .cursor_secrets/ghcr.env
chmod 600 .cursor_secrets/ghcr.env
```

## 🛠️ Local Scripts

### **Docker Build Script** (`scripts/docker-build.sh`)
```bash
# Show help
./scripts/docker-build.sh help

# Build image locally
./scripts/docker-build.sh build

# Build and push to GHCR
./scripts/docker-build.sh push

# Login to GHCR only
./scripts/docker-build.sh login

# Clean up local images
./scripts/docker-build.sh clean
```

## 📋 Workflow Triggers

| Action | Trigger | Result |
|--------|---------|---------|
| Push to `main` | ✅ Build + Push + Deploy | Production image |
| Push to `develop` | ✅ Build + Push | Development image |
| Create tag `v*` | ✅ Build + Push + Version | Release image |
| Pull Request | ✅ Security Scan | Validation only |
| Manual | ✅ Custom build | On-demand |

## 🏷️ Image Tagging Strategy

- **`latest`** - Latest commit on main branch
- **`main-abc1234`** - Specific commit hash
- **`v1.2.3`** - Semantic version tags
- **`v1.2`** - Major.minor version
- **`develop-abc1234`** - Development branch commits

## 🔍 Monitoring & Debugging

### **GitHub Actions Tab**
- View all workflow runs
- Check build logs
- Monitor build times

### **Security Tab**
- Vulnerability scan results
- Security advisories
- Dependency alerts

### **Packages Tab**
- View all container images
- Check image sizes
- Manage package versions

## 🚨 Troubleshooting

### **Build Fails**
```bash
# Check local Docker
docker --version
docker buildx version

# Verify token
echo $GHCR_NEW

# Test login manually
echo $GHCR_NEW | docker login ghcr.io -u haymayndzultra --password-stdin
```

### **Push Fails**
```bash
# Check permissions
# Ensure GHCR_NEW secret has write access to packages

# Verify image exists locally
docker images | grep ghcr.io

# Check network connectivity
curl -I https://ghcr.io
```

### **Security Scan Issues**
```bash
# Check Trivy installation
trivy --version

# Run scan locally
trivy image --severity HIGH,CRITICAL your-image:latest
```

## 🔄 Token Rotation

### **When to Rotate**
- Every 90 days (GitHub recommendation)
- After security incidents
- When team members leave

### **Rotation Process**
1. **Generate new token** in GitHub
2. **Update repository secret** `GHCR_NEW`
3. **Update local file** `.cursor_secrets/ghcr.env`
4. **Test authentication** with new token

## 📊 Performance Optimization

### **Build Cache**
- GitHub Actions cache for layers
- Multi-stage builds for efficiency
- .dockerignore for context optimization

### **Parallel Builds**
- Matrix strategy for platforms
- Concurrent job execution
- Resource optimization

## 🎯 Best Practices

### **Dockerfile Optimization**
```dockerfile
# Use multi-stage builds
FROM node:18-alpine AS builder
# ... build steps

FROM node:18-alpine AS runtime
# ... runtime setup

# Minimize layers
RUN apt-get update && apt-get install -y package && rm -rf /var/lib/apt/lists/*
```

### **Security**
- Regular base image updates
- Vulnerability scanning on every build
- Minimal runtime images
- Non-root user execution

## 🔗 Useful Links

- [GitHub Container Registry](https://ghcr.io)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [Trivy Security Scanner](https://aquasecurity.github.io/trivy/)

---

## 🎉 Success!

Your Docker workflow is now fully automated! 

- **Local development** → Use `./scripts/docker-build.sh`
- **CI/CD** → Automatic on every push
- **Security** → Scanned on every PR
- **Multi-platform** → Built for all architectures

Push to main branch to see it in action! 🚀
