---
title: "Node.js Backend Development"
date: "2024-04-20"
tags: ["nodejs", "backend", "javascript", "server"]
---

# Node.js Backend Development

Node.js is a JavaScript runtime built on Chrome's V8 JavaScript engine, enabling server-side JavaScript development.

## Core Features

### Event-Driven Architecture
- Non-blocking I/O operations
- Event loop for handling requests
- Asynchronous programming model

### NPM Ecosystem
- Largest package registry
- Rich library ecosystem
- Easy dependency management

### Cross-Platform
- Runs on Windows, macOS, Linux
- Consistent API across platforms
- Cloud deployment support

## Getting Started

### Installation
```bash
# Install Node.js
# Download from nodejs.org or use package manager

# Check version
node --version
npm --version

# Initialize project
npm init -y
```

### Basic Server
```javascript
const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'text/plain' });
  res.end('Hello World!');
});

server.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

## Express.js Framework

### Installation
```bash
npm install express
```

### Basic Express App
```javascript
const express = require('express');
const app = express();

// Middleware
app.use(express.json());

// Routes
app.get('/', (req, res) => {
  res.json({ message: 'Hello World!' });
});

app.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

### Routing
```javascript
// GET route
app.get('/users', (req, res) => {
  res.json(users);
});

// POST route
app.post('/users', (req, res) => {
  const newUser = req.body;
  users.push(newUser);
  res.status(201).json(newUser);
});

// PUT route
app.put('/users/:id', (req, res) => {
  const id = req.params.id;
  const updatedUser = req.body;
  // Update user logic
  res.json(updatedUser);
});

// DELETE route
app.delete('/users/:id', (req, res) => {
  const id = req.params.id;
  // Delete user logic
  res.status(204).send();
});
```

## Middleware

### Built-in Middleware
```javascript
// Parse JSON bodies
app.use(express.json());

// Parse URL-encoded bodies
app.use(express.urlencoded({ extended: true }));

// Serve static files
app.use(express.static('public'));

// CORS
app.use(cors());
```

### Custom Middleware
```javascript
// Logger middleware
app.use((req, res, next) => {
  console.log(`${req.method} ${req.path} - ${new Date()}`);
  next();
});

// Authentication middleware
const authenticate = (req, res, next) => {
  const token = req.headers.authorization;
  if (!token) {
    return res.status(401).json({ error: 'No token provided' });
  }
  // Verify token logic
  next();
};

// Using middleware
app.get('/protected', authenticate, (req, res) => {
  res.json({ message: 'Protected route' });
});
```

## Database Integration

### MongoDB with Mongoose
```javascript
const mongoose = require('mongoose');

// Connect to MongoDB
mongoose.connect('mongodb://localhost:27017/myapp');

// Define schema
const userSchema = new mongoose.Schema({
  name: String,
  email: String,
  age: Number
});

// Create model
const User = mongoose.model('User', userSchema);

// CRUD operations
app.get('/users', async (req, res) => {
  try {
    const users = await User.find();
    res.json(users);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

app.post('/users', async (req, res) => {
  try {
    const user = new User(req.body);
    await user.save();
    res.status(201).json(user);
  } catch (error) {
    res.status(400).json({ error: error.message });
  }
});
```

### PostgreSQL with Sequelize
```javascript
const { Sequelize, DataTypes } = require('sequelize');

// Connect to PostgreSQL
const sequelize = new Sequelize('postgres://user:password@localhost:5432/myapp');

// Define model
const User = sequelize.define('User', {
  name: DataTypes.STRING,
  email: DataTypes.STRING,
  age: DataTypes.INTEGER
});

// Sync database
sequelize.sync();

// CRUD operations
app.get('/users', async (req, res) => {
  try {
    const users = await User.findAll();
    res.json(users);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});
```

## Authentication

### JWT Authentication
```javascript
const jwt = require('jsonwebtoken');

// Login route
app.post('/login', async (req, res) => {
  const { email, password } = req.body;
  
  // Validate credentials
  const user = await User.findOne({ email });
  if (!user || !await bcrypt.compare(password, user.password)) {
    return res.status(401).json({ error: 'Invalid credentials' });
  }
  
  // Generate JWT
  const token = jwt.sign(
    { userId: user.id },
    process.env.JWT_SECRET,
    { expiresIn: '1h' }
  );
  
  res.json({ token });
});

// Protected route
app.get('/profile', authenticate, (req, res) => {
  res.json({ user: req.user });
});
```

### Password Hashing
```javascript
const bcrypt = require('bcrypt');

// Hash password
const hashedPassword = await bcrypt.hash(password, 10);

// Compare password
const isValid = await bcrypt.compare(password, hashedPassword);
```

## Error Handling

### Global Error Handler
```javascript
app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({ error: 'Something went wrong!' });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});
```

### Async Error Handling
```javascript
const asyncHandler = (fn) => (req, res, next) => {
  Promise.resolve(fn(req, res, next)).catch(next);
};

app.get('/users', asyncHandler(async (req, res) => {
  const users = await User.find();
  res.json(users);
}));
```

## File Upload

### Multer Middleware
```javascript
const multer = require('multer');

// Configure storage
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    cb(null, 'uploads/');
  },
  filename: (req, file, cb) => {
    cb(null, Date.now() + '-' + file.originalname);
  }
});

const upload = multer({ storage });

// Upload route
app.post('/upload', upload.single('file'), (req, res) => {
  res.json({ message: 'File uploaded successfully' });
});
```

## Testing

### Jest Testing
```javascript
const request = require('supertest');
const app = require('./app');

describe('GET /users', () => {
  test('should return all users', async () => {
    const response = await request(app).get('/users');
    expect(response.status).toBe(200);
    expect(Array.isArray(response.body)).toBe(true);
  });
});
```

## Deployment

### Environment Variables
```javascript
require('dotenv').config();

const PORT = process.env.PORT || 3000;
const DB_URL = process.env.DB_URL || 'mongodb://localhost:27017/myapp';
```

### PM2 Process Manager
```bash
# Install PM2
npm install -g pm2

# Start application
pm2 start app.js

# Monitor
pm2 monit

# Restart
pm2 restart app
```

## Best Practices

### Code Organization
- Use modules and separate concerns
- Implement proper error handling
- Use environment variables
- Follow RESTful API design

### Security
- Validate input data
- Use HTTPS in production
- Implement rate limiting
- Keep dependencies updated

### Performance
- Use compression middleware
- Implement caching
- Optimize database queries
- Monitor application performance
