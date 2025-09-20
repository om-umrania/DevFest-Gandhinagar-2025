---
title: "SQL Database Management"
date: "2024-04-25"
tags: ["sql", "database", "mysql", "postgresql"]
---

# SQL Database Management

SQL (Structured Query Language) is the standard language for managing relational databases and performing operations on data.

## Database Fundamentals

### What is a Database?
- Organized collection of data
- Stored electronically
- Managed by Database Management System (DBMS)

### Types of Databases
- **Relational**: Tables with rows and columns
- **NoSQL**: Document, key-value, graph databases
- **In-memory**: Data stored in RAM
- **Distributed**: Data spread across multiple servers

## SQL Basics

### Data Types
- **INTEGER**: Whole numbers
- **VARCHAR(n)**: Variable-length strings
- **TEXT**: Long text data
- **DATE**: Date values
- **DECIMAL**: Decimal numbers
- **BOOLEAN**: True/false values

### Creating Tables
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) UNIQUE,
    age INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Inserting Data
```sql
INSERT INTO users (name, email, age) 
VALUES ('John Doe', 'john@example.com', 30);

INSERT INTO users (name, email, age) 
VALUES 
    ('Jane Smith', 'jane@example.com', 25),
    ('Bob Johnson', 'bob@example.com', 35);
```

### Querying Data
```sql
-- Select all columns
SELECT * FROM users;

-- Select specific columns
SELECT name, email FROM users;

-- Filter with WHERE
SELECT * FROM users WHERE age > 25;

-- Sort with ORDER BY
SELECT * FROM users ORDER BY name ASC;

-- Limit results
SELECT * FROM users LIMIT 10;
```

## Advanced Queries

### Joins
```sql
-- Inner join
SELECT u.name, p.title 
FROM users u
INNER JOIN posts p ON u.id = p.user_id;

-- Left join
SELECT u.name, p.title 
FROM users u
LEFT JOIN posts p ON u.id = p.user_id;

-- Right join
SELECT u.name, p.title 
FROM users u
RIGHT JOIN posts p ON u.id = p.user_id;
```

### Aggregation
```sql
-- Count records
SELECT COUNT(*) FROM users;

-- Group by
SELECT age, COUNT(*) 
FROM users 
GROUP BY age;

-- Having clause
SELECT age, COUNT(*) 
FROM users 
GROUP BY age 
HAVING COUNT(*) > 1;

-- Sum, average, min, max
SELECT 
    SUM(age) as total_age,
    AVG(age) as average_age,
    MIN(age) as youngest,
    MAX(age) as oldest
FROM users;
```

### Subqueries
```sql
-- Find users older than average
SELECT * FROM users 
WHERE age > (SELECT AVG(age) FROM users);

-- Exists
SELECT * FROM users u
WHERE EXISTS (
    SELECT 1 FROM posts p 
    WHERE p.user_id = u.id
);
```

## Data Modification

### Updating Data
```sql
-- Update single record
UPDATE users 
SET age = 31 
WHERE id = 1;

-- Update multiple records
UPDATE users 
SET age = age + 1 
WHERE age < 30;
```

### Deleting Data
```sql
-- Delete specific records
DELETE FROM users WHERE id = 1;

-- Delete all records
DELETE FROM users;

-- Truncate table (faster)
TRUNCATE TABLE users;
```

### Altering Tables
```sql
-- Add column
ALTER TABLE users ADD COLUMN phone VARCHAR(20);

-- Modify column
ALTER TABLE users MODIFY COLUMN age INT NOT NULL;

-- Drop column
ALTER TABLE users DROP COLUMN phone;

-- Add index
CREATE INDEX idx_email ON users(email);
```

## Indexes and Performance

### Types of Indexes
- **Primary Key**: Unique identifier
- **Unique Index**: Prevents duplicates
- **Composite Index**: Multiple columns
- **Full-text Index**: Text search

### Creating Indexes
```sql
-- Single column index
CREATE INDEX idx_name ON users(name);

-- Composite index
CREATE INDEX idx_name_age ON users(name, age);

-- Unique index
CREATE UNIQUE INDEX idx_email ON users(email);
```

### Query Optimization
- Use indexes on frequently queried columns
- Avoid SELECT * in production
- Use LIMIT for large result sets
- Analyze query execution plans

## Transactions

### ACID Properties
- **Atomicity**: All or nothing
- **Consistency**: Valid state transitions
- **Isolation**: Concurrent transactions don't interfere
- **Durability**: Committed changes persist

### Transaction Control
```sql
-- Start transaction
START TRANSACTION;

-- Perform operations
INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com');
UPDATE accounts SET balance = balance - 100 WHERE user_id = 1;

-- Commit or rollback
COMMIT;
-- OR
ROLLBACK;
```

## Stored Procedures

### Creating Procedures
```sql
DELIMITER //
CREATE PROCEDURE GetUserByAge(IN min_age INT)
BEGIN
    SELECT * FROM users WHERE age >= min_age;
END //
DELIMITER ;

-- Call procedure
CALL GetUserByAge(25);
```

### Functions
```sql
DELIMITER //
CREATE FUNCTION GetUserCount() RETURNS INT
READS SQL DATA
BEGIN
    DECLARE user_count INT;
    SELECT COUNT(*) INTO user_count FROM users;
    RETURN user_count;
END //
DELIMITER ;

-- Use function
SELECT GetUserCount();
```

## Database Design

### Normalization
- **1NF**: Atomic values, no repeating groups
- **2NF**: 1NF + no partial dependencies
- **3NF**: 2NF + no transitive dependencies

### Relationships
- **One-to-One**: Each record relates to one record
- **One-to-Many**: One record relates to many records
- **Many-to-Many**: Many records relate to many records

### Foreign Keys
```sql
CREATE TABLE posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(200) NOT NULL,
    content TEXT,
    user_id INT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

## Popular Databases

### MySQL
- Open-source relational database
- Widely used in web applications
- Good performance and reliability

### PostgreSQL
- Advanced open-source database
- ACID compliant
- Rich feature set

### SQLite
- Lightweight, embedded database
- No server required
- Good for development and testing

### SQL Server
- Microsoft's database system
- Enterprise features
- Windows integration

## Best Practices

### Security
- Use parameterized queries
- Validate input data
- Implement proper access control
- Regular security updates

### Performance
- Design efficient schemas
- Use appropriate indexes
- Monitor query performance
- Regular maintenance

### Backup and Recovery
- Regular backups
- Test restore procedures
- Point-in-time recovery
- Disaster recovery planning
