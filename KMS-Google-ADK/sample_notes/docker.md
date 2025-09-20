---
title: "Docker Containerization"
date: "2024-03-30"
tags: ["docker", "containers", "devops", "deployment"]
---

# Docker Containerization

Docker is a platform that enables developers to package applications and their dependencies into lightweight, portable containers.

## What are Containers?

### Definition
- Lightweight, standalone executable packages
- Include application code, runtime, system tools, libraries
- Run consistently across different environments

### Benefits
- **Consistency**: Same environment everywhere
- **Portability**: Run on any system with Docker
- **Efficiency**: Share OS kernel, less resource usage
- **Scalability**: Easy to scale up/down

## Docker Architecture

### Docker Engine
- **Docker Daemon**: Background service managing containers
- **Docker CLI**: Command-line interface
- **Docker API**: REST API for Docker operations

### Key Components
- **Images**: Read-only templates for containers
- **Containers**: Running instances of images
- **Registries**: Storage for Docker images
- **Dockerfile**: Text file with build instructions

## Docker Images

### Image Layers
- Images are built in layers
- Each instruction creates a new layer
- Layers are cached for efficiency
- Immutable once created

### Base Images
- **Alpine**: Minimal Linux distribution
- **Ubuntu**: Full-featured Linux
- **Node**: Node.js runtime
- **Python**: Python runtime

### Image Commands
```bash
# Build image
docker build -t myapp:latest .

# List images
docker images

# Remove image
docker rmi myapp:latest

# Pull image
docker pull nginx:latest
```

## Dockerfile

### Basic Structure
```dockerfile
FROM node:16-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

### Common Instructions
- **FROM**: Base image
- **WORKDIR**: Set working directory
- **COPY/ADD**: Copy files
- **RUN**: Execute commands
- **EXPOSE**: Document port
- **CMD**: Default command

## Docker Containers

### Container Lifecycle
- **Create**: `docker create`
- **Start**: `docker start`
- **Run**: `docker run` (create + start)
- **Stop**: `docker stop`
- **Remove**: `docker rm`

### Container Commands
```bash
# Run container
docker run -d -p 3000:3000 myapp:latest

# List running containers
docker ps

# Stop container
docker stop container_id

# Remove container
docker rm container_id
```

## Docker Compose

### Multi-Container Applications
- Define services in YAML file
- Manage multiple containers together
- Easy development setup

### Example docker-compose.yml
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "3000:3000"
    depends_on:
      - db
  db:
    image: postgres:13
    environment:
      POSTGRES_DB: myapp
      POSTGRES_PASSWORD: password
```

### Compose Commands
```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Stop services
docker-compose down

# Build and start
docker-compose up --build
```

## Docker Registry

### Docker Hub
- Public registry for Docker images
- Official images available
- Private repositories for organizations

### Private Registries
- **AWS ECR**: Amazon's container registry
- **Azure ACR**: Microsoft's container registry
- **Google GCR**: Google's container registry

### Registry Commands
```bash
# Login to registry
docker login

# Tag image
docker tag myapp:latest username/myapp:latest

# Push image
docker push username/myapp:latest

# Pull image
docker pull username/myapp:latest
```

## Best Practices

### Image Optimization
- Use multi-stage builds
- Minimize layers
- Use .dockerignore
- Choose appropriate base image

### Security
- Don't run as root
- Use specific image tags
- Scan for vulnerabilities
- Keep images updated

### Performance
- Use build cache effectively
- Optimize layer ordering
- Minimize image size
- Use health checks

## Use Cases

### Development
- Consistent development environment
- Easy setup for new developers
- Isolated dependencies

### Testing
- Consistent test environment
- Parallel test execution
- Easy cleanup

### Deployment
- Consistent production environment
- Easy scaling
- Rollback capabilities

### CI/CD
- Consistent build environment
- Easy deployment
- Version control for infrastructure
