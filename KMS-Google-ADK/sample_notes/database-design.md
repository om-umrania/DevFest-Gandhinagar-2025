---
title: "Database Design Principles"
date: "2024-02-01"
tags: ["database", "sql", "design", "normalization"]
---

# Database Design Principles

Database design is the process of creating a detailed data model of a database.

## Normalization

### First Normal Form (1NF)
- Each table cell should contain atomic values
- No repeating groups or arrays

### Second Normal Form (2NF)
- Must be in 1NF
- All non-key attributes must depend on the entire primary key

### Third Normal Form (3NF)
- Must be in 2NF
- No transitive dependencies

## Entity-Relationship Modeling

### Entities
- Objects or concepts in the real world
- Represented as tables

### Attributes
- Properties of entities
- Represented as columns

### Relationships
- **One-to-One**: Each record in one table relates to one record in another
- **One-to-Many**: One record relates to many records
- **Many-to-Many**: Many records relate to many records

## Key Design Considerations

### Primary Keys
- Uniquely identify each record
- Should be immutable
- Can be natural or surrogate

### Foreign Keys
- Link tables together
- Maintain referential integrity
- Enable joins

### Indexing
- Improve query performance
- Balance between read and write performance
- Consider composite indexes

## Database Types

### Relational Databases
- **MySQL**: Open-source, widely used
- **PostgreSQL**: Advanced features, ACID compliant
- **SQLite**: Lightweight, embedded
- **Oracle**: Enterprise-grade, feature-rich

### NoSQL Databases
- **MongoDB**: Document-based
- **Redis**: Key-value store
- **Cassandra**: Wide-column store
- **Neo4j**: Graph database
