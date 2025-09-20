---
title: "JavaScript Modern Development"
date: "2024-04-10"
tags: ["javascript", "es6", "frontend", "nodejs"]
---

# JavaScript Modern Development

JavaScript is a versatile programming language that powers both frontend and backend development, with modern features and frameworks.

## ES6+ Features

### Arrow Functions
```javascript
// Traditional function
function add(a, b) {
  return a + b;
}

// Arrow function
const add = (a, b) => a + b;

// Single parameter
const square = x => x * x;

// No parameters
const greet = () => 'Hello World';
```

### Destructuring
```javascript
// Object destructuring
const { name, age, email } = user;

// Array destructuring
const [first, second, third] = array;

// Default values
const { name = 'Anonymous', age = 0 } = user;
```

### Template Literals
```javascript
// String interpolation
const message = `Hello ${name}, you are ${age} years old`;

// Multi-line strings
const html = `
  <div>
    <h1>${title}</h1>
    <p>${content}</p>
  </div>
`;
```

### Spread Operator
```javascript
// Array spreading
const newArray = [...oldArray, newItem];

// Object spreading
const newObject = { ...oldObject, newProperty: value };

// Function arguments
const max = Math.max(...numbers);
```

## Async Programming

### Promises
```javascript
// Creating promises
const fetchData = () => {
  return new Promise((resolve, reject) => {
    // Async operation
    if (success) {
      resolve(data);
    } else {
      reject(error);
    }
  });
};

// Using promises
fetchData()
  .then(data => console.log(data))
  .catch(error => console.error(error));
```

### Async/Await
```javascript
// Async function
async function fetchUserData() {
  try {
    const response = await fetch('/api/users');
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error:', error);
  }
}

// Using async/await
const userData = await fetchUserData();
```

## Modules

### ES6 Modules
```javascript
// Exporting
export const name = 'John';
export function greet() {
  return 'Hello!';
}

// Default export
export default class User {
  constructor(name) {
    this.name = name;
  }
}

// Importing
import { name, greet } from './module.js';
import User from './User.js';
```

### CommonJS (Node.js)
```javascript
// Exporting
module.exports = {
  name: 'John',
  greet: function() {
    return 'Hello!';
  }
};

// Importing
const { name, greet } = require('./module.js');
```

## DOM Manipulation

### Selecting Elements
```javascript
// By ID
const element = document.getElementById('myId');

// By class
const elements = document.getElementsByClassName('myClass');

// By tag
const divs = document.getElementsByTagName('div');

// Modern selectors
const element = document.querySelector('#myId');
const elements = document.querySelectorAll('.myClass');
```

### Event Handling
```javascript
// Add event listener
element.addEventListener('click', function(event) {
  console.log('Clicked!');
});

// Arrow function
element.addEventListener('click', (event) => {
  console.log('Clicked!');
});

// Remove event listener
element.removeEventListener('click', handler);
```

## Modern JavaScript Features

### Classes
```javascript
class User {
  constructor(name, email) {
    this.name = name;
    this.email = email;
  }
  
  greet() {
    return `Hello, I'm ${this.name}`;
  }
  
  static createAdmin(name) {
    return new User(name, 'admin@example.com');
  }
}

// Inheritance
class Admin extends User {
  constructor(name) {
    super(name, 'admin@example.com');
    this.role = 'admin';
  }
}
```

### Map and Set
```javascript
// Map
const userMap = new Map();
userMap.set('id1', { name: 'John' });
userMap.set('id2', { name: 'Jane' });

// Set
const uniqueIds = new Set([1, 2, 3, 3, 4]); // [1, 2, 3, 4]
```

### Array Methods
```javascript
// Map
const doubled = numbers.map(n => n * 2);

// Filter
const evens = numbers.filter(n => n % 2 === 0);

// Reduce
const sum = numbers.reduce((acc, n) => acc + n, 0);

// Find
const user = users.find(u => u.id === 123);

// Some/Every
const hasAdults = users.some(u => u.age >= 18);
const allAdults = users.every(u => u.age >= 18);
```

## Node.js Development

### File System
```javascript
const fs = require('fs').promises;

// Read file
const data = await fs.readFile('file.txt', 'utf8');

// Write file
await fs.writeFile('output.txt', 'Hello World');

// Check if file exists
const exists = await fs.access('file.txt').then(() => true).catch(() => false);
```

### HTTP Server
```javascript
const http = require('http');

const server = http.createServer((req, res) => {
  res.writeHead(200, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ message: 'Hello World' }));
});

server.listen(3000, () => {
  console.log('Server running on port 3000');
});
```

## Popular Frameworks

### Frontend
- **React**: Component-based UI library
- **Vue.js**: Progressive JavaScript framework
- **Angular**: Full-featured framework
- **Svelte**: Compile-time framework

### Backend
- **Express.js**: Minimal web framework
- **Fastify**: Fast and low overhead
- **Koa.js**: Next generation web framework
- **NestJS**: Enterprise-grade framework

## Best Practices

### Code Organization
- Use modules and classes
- Follow naming conventions
- Write readable code
- Use meaningful variable names

### Error Handling
- Use try-catch blocks
- Handle promise rejections
- Log errors appropriately
- Provide user-friendly messages

### Performance
- Avoid memory leaks
- Use efficient algorithms
- Minimize DOM manipulation
- Optimize bundle size

### Security
- Validate input data
- Sanitize user input
- Use HTTPS
- Implement proper authentication
