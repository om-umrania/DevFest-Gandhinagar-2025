---
title: "Docker Compose Orchestration"
date: "2024-05-02"
tags: ["docker-compose", "orchestration", "containers", "devops"]
---

# Docker Compose Orchestration

Docker Compose is a tool for defining and running multi-container Docker applications using YAML files.

## What is Docker Compose?

### Purpose
- Define multi-container applications
- Manage service dependencies
- Simplify development workflows
- Easy environment setup

### Benefits
- **Single Command**: Start entire stack
- **Environment Parity**: Same setup everywhere
- **Service Discovery**: Containers can communicate
- **Volume Management**: Shared data persistence

## Basic Structure

### docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "3000:3000"
    depends_on:
      - db
    environment:
      - NODE_ENV=production
      - DB_HOST=db
    volumes:
      - .:/app
      - /app/node_modules

  db:
    image: postgres:13
    environment:
      POSTGRES_DB: myapp
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

## Service Configuration

### Build Options
```yaml
services:
  web:
    # Build from Dockerfile
    build: .
    
    # Build with context and Dockerfile
    build:
      context: .
      dockerfile: Dockerfile.prod
    
    # Build with build args
    build:
      context: .
      args:
        - NODE_ENV=production
        - VERSION=1.0.0
```

### Image and Ports
```yaml
services:
  web:
    # Use existing image
    image: nginx:alpine
    
    # Port mapping
    ports:
      - "80:80"        # host:container
      - "443:443"
      - "8080:80"      # Multiple mappings
    
    # Expose ports without mapping
    expose:
      - "3000"
```

### Environment Variables
```yaml
services:
  web:
    # Environment file
    env_file:
      - .env
      - .env.local
    
    # Individual variables
    environment:
      - NODE_ENV=production
      - DEBUG=true
      - API_URL=https://api.example.com
    
    # Object format
    environment:
      NODE_ENV: production
      DEBUG: "true"
      API_URL: https://api.example.com
```

## Networking

### Default Network
```yaml
services:
  web:
    image: nginx
    # Automatically connected to default network
  
  db:
    image: postgres
    # Can communicate with web using service name
```

### Custom Networks
```yaml
services:
  web:
    image: nginx
    networks:
      - frontend
      - backend
  
  db:
    image: postgres
    networks:
      - backend

networks:
  frontend:
    driver: bridge
  backend:
    driver: bridge
    internal: true  # No external access
```

### External Networks
```yaml
services:
  web:
    image: nginx
    networks:
      - existing_network

networks:
  existing_network:
    external: true
```

## Volumes

### Named Volumes
```yaml
services:
  db:
    image: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
    driver: local
```

### Bind Mounts
```yaml
services:
  web:
    image: nginx
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./html:/usr/share/nginx/html
      - /host/path:/container/path
```

### Volume Configuration
```yaml
volumes:
  postgres_data:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: /path/to/host/directory
```

## Health Checks

### Basic Health Check
```yaml
services:
  web:
    image: nginx
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Health Check with Dependencies
```yaml
services:
  web:
    image: nginx
    depends_on:
      db:
        condition: service_healthy
  
  db:
    image: postgres
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
```

## Scaling Services

### Scale Command
```bash
# Scale web service to 3 instances
docker-compose up --scale web=3

# Scale multiple services
docker-compose up --scale web=3 --scale worker=2
```

### Load Balancing
```yaml
services:
  web:
    image: nginx
    ports:
      - "80:80"
    depends_on:
      - app
  
  app:
    image: myapp
    # Multiple instances will be load balanced
```

## Development vs Production

### Development Override
```yaml
# docker-compose.override.yml
version: '3.8'

services:
  web:
    volumes:
      - .:/app  # Live code reload
    environment:
      - DEBUG=true
    ports:
      - "3000:3000"
```

### Production Configuration
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  web:
    image: myapp:latest
    environment:
      - NODE_ENV=production
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

## Common Commands

### Basic Commands
```bash
# Start services
docker-compose up

# Start in background
docker-compose up -d

# Start specific service
docker-compose up web

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# View logs
docker-compose logs

# View logs for specific service
docker-compose logs web

# Follow logs
docker-compose logs -f web
```

### Build and Management
```bash
# Build services
docker-compose build

# Build specific service
docker-compose build web

# Pull images
docker-compose pull

# Remove stopped containers
docker-compose rm

# Execute command in service
docker-compose exec web bash

# Run one-time command
docker-compose run web npm test
```

## Best Practices

### File Organization
- Use descriptive service names
- Group related services
- Use environment files
- Separate dev/prod configurations

### Security
- Don't run as root
- Use specific image tags
- Limit resource usage
- Use secrets for sensitive data

### Performance
- Use multi-stage builds
- Optimize image layers
- Use appropriate base images
- Monitor resource usage

### Maintenance
- Regular image updates
- Clean up unused resources
- Monitor logs
- Backup volumes
