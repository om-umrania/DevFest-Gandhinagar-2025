---
title: "React Development Guide"
date: "2024-04-15"
tags: ["react", "frontend", "javascript", "components"]
---

# React Development Guide

React is a JavaScript library for building user interfaces, particularly single-page applications with component-based architecture.

## Core Concepts

### Components
- Reusable UI pieces
- Encapsulate logic and presentation
- Can be functional or class-based

### JSX
- JavaScript XML syntax
- Write HTML-like code in JavaScript
- Compiles to JavaScript

### Virtual DOM
- In-memory representation of DOM
- Efficient updates
- Reconciliation process

## Functional Components

### Basic Component
```jsx
function Welcome(props) {
  return <h1>Hello, {props.name}</h1>;
}

// Arrow function
const Welcome = (props) => {
  return <h1>Hello, {props.name}</h1>;
};
```

### Using Components
```jsx
function App() {
  return (
    <div>
      <Welcome name="John" />
      <Welcome name="Jane" />
    </div>
  );
}
```

## Hooks

### useState
```jsx
import { useState } from 'react';

function Counter() {
  const [count, setCount] = useState(0);
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={() => setCount(count + 1)}>
        Increment
      </button>
    </div>
  );
}
```

### useEffect
```jsx
import { useState, useEffect } from 'react';

function UserProfile({ userId }) {
  const [user, setUser] = useState(null);
  
  useEffect(() => {
    fetch(`/api/users/${userId}`)
      .then(response => response.json())
      .then(data => setUser(data));
  }, [userId]);
  
  if (!user) return <div>Loading...</div>;
  
  return <div>{user.name}</div>;
}
```

### Custom Hooks
```jsx
function useCounter(initialValue = 0) {
  const [count, setCount] = useState(initialValue);
  
  const increment = () => setCount(count + 1);
  const decrement = () => setCount(count - 1);
  const reset = () => setCount(initialValue);
  
  return { count, increment, decrement, reset };
}

// Using custom hook
function Counter() {
  const { count, increment, decrement, reset } = useCounter(0);
  
  return (
    <div>
      <p>Count: {count}</p>
      <button onClick={increment}>+</button>
      <button onClick={decrement}>-</button>
      <button onClick={reset}>Reset</button>
    </div>
  );
}
```

## Props and State

### Props
```jsx
// Parent component
function App() {
  const user = { name: 'John', age: 30 };
  return <UserCard user={user} />;
}

// Child component
function UserCard({ user }) {
  return (
    <div>
      <h2>{user.name}</h2>
      <p>Age: {user.age}</p>
    </div>
  );
}
```

### State Management
```jsx
function TodoList() {
  const [todos, setTodos] = useState([]);
  const [inputValue, setInputValue] = useState('');
  
  const addTodo = () => {
    if (inputValue.trim()) {
      setTodos([...todos, { id: Date.now(), text: inputValue }]);
      setInputValue('');
    }
  };
  
  return (
    <div>
      <input
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
      />
      <button onClick={addTodo}>Add Todo</button>
      <ul>
        {todos.map(todo => (
          <li key={todo.id}>{todo.text}</li>
        ))}
      </ul>
    </div>
  );
}
```

## Event Handling

### Basic Events
```jsx
function Button() {
  const handleClick = () => {
    console.log('Button clicked!');
  };
  
  return <button onClick={handleClick}>Click me</button>;
}
```

### Form Handling
```jsx
function ContactForm() {
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    message: ''
  });
  
  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
  };
  
  const handleSubmit = (e) => {
    e.preventDefault();
    console.log('Form submitted:', formData);
  };
  
  return (
    <form onSubmit={handleSubmit}>
      <input
        name="name"
        value={formData.name}
        onChange={handleChange}
        placeholder="Name"
      />
      <input
        name="email"
        type="email"
        value={formData.email}
        onChange={handleChange}
        placeholder="Email"
      />
      <textarea
        name="message"
        value={formData.message}
        onChange={handleChange}
        placeholder="Message"
      />
      <button type="submit">Submit</button>
    </form>
  );
}
```

## Conditional Rendering

### If Statements
```jsx
function UserGreeting({ user }) {
  if (user) {
    return <h1>Welcome back, {user.name}!</h1>;
  }
  return <h1>Please sign in.</h1>;
}
```

### Ternary Operator
```jsx
function LoginButton({ isLoggedIn }) {
  return (
    <button>
      {isLoggedIn ? 'Logout' : 'Login'}
    </button>
  );
}
```

### Logical AND
```jsx
function Notification({ message }) {
  return (
    <div>
      {message && <div className="notification">{message}</div>}
    </div>
  );
}
```

## Lists and Keys

### Rendering Lists
```jsx
function TodoList({ todos }) {
  return (
    <ul>
      {todos.map(todo => (
        <li key={todo.id}>
          {todo.text}
        </li>
      ))}
    </ul>
  );
}
```

### Keys
- Unique identifier for each item
- Help React identify changes
- Use stable, unique values

## Context API

### Creating Context
```jsx
import { createContext, useContext } from 'react';

const ThemeContext = createContext();

function ThemeProvider({ children }) {
  const [theme, setTheme] = useState('light');
  
  return (
    <ThemeContext.Provider value={{ theme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

function useTheme() {
  return useContext(ThemeContext);
}
```

### Using Context
```jsx
function ThemedButton() {
  const { theme, setTheme } = useTheme();
  
  return (
    <button
      style={{ background: theme === 'light' ? '#fff' : '#333' }}
      onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
    >
      Toggle Theme
    </button>
  );
}
```

## Performance Optimization

### React.memo
```jsx
const ExpensiveComponent = React.memo(({ data }) => {
  return <div>{/* Expensive rendering */}</div>;
});
```

### useMemo
```jsx
function ExpensiveCalculation({ items }) {
  const expensiveValue = useMemo(() => {
    return items.reduce((sum, item) => sum + item.value, 0);
  }, [items]);
  
  return <div>Total: {expensiveValue}</div>;
}
```

### useCallback
```jsx
function Parent({ items }) {
  const handleClick = useCallback((id) => {
    console.log('Clicked item:', id);
  }, []);
  
  return (
    <div>
      {items.map(item => (
        <Child key={item.id} item={item} onClick={handleClick} />
      ))}
    </div>
  );
}
```

## Testing

### Jest and React Testing Library
```jsx
import { render, screen, fireEvent } from '@testing-library/react';
import Counter from './Counter';

test('increments counter when button is clicked', () => {
  render(<Counter />);
  
  const button = screen.getByText('Increment');
  fireEvent.click(button);
  
  expect(screen.getByText('Count: 1')).toBeInTheDocument();
});
```

## Best Practices

### Component Design
- Single responsibility
- Reusable and composable
- Clear prop interfaces
- Proper naming conventions

### State Management
- Keep state close to where it's used
- Use context for global state
- Consider external state management for complex apps

### Performance
- Use React.memo for expensive components
- Optimize re-renders
- Lazy load components when needed
- Use proper keys in lists
