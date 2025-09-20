---
title: "REST API Development"
date: "2024-04-05"
tags: ["rest", "api", "http", "web-services"]
---

# REST API Development

REST (Representational State Transfer) is an architectural style for designing web services that are scalable, maintainable, and easy to understand.

## REST Principles

### Stateless
- Each request contains all necessary information
- No server-side session storage
- Client maintains application state

### Client-Server Architecture
- Separation of concerns
- Independent evolution
- Scalability benefits

### Cacheable
- Responses can be cached
- Improves performance
- Reduces server load

### Uniform Interface
- Consistent resource identification
- Standard HTTP methods
- Self-descriptive messages

## HTTP Methods

### GET
- Retrieve resource data
- Idempotent and safe
- Can be cached

### POST
- Create new resources
- Not idempotent
- Request body contains data

### PUT
- Update entire resource
- Idempotent
- Replace resource completely

### PATCH
- Partial updates
- Idempotent
- Modify specific fields

### DELETE
- Remove resources
- Idempotent
- No request body needed

## Resource Design

### URL Structure
- Use nouns, not verbs
- Hierarchical organization
- Consistent naming

### Examples
```
GET /api/v1/users
GET /api/v1/users/123
POST /api/v1/users
PUT /api/v1/users/123
DELETE /api/v1/users/123
```

### Query Parameters
- Filtering: ?status=active
- Sorting: ?sort=name
- Pagination: ?page=1&limit=10
- Searching: ?q=searchterm

## Status Codes

### 2xx Success
- **200 OK**: Request successful
- **201 Created**: Resource created
- **204 No Content**: Success, no response body

### 4xx Client Error
- **400 Bad Request**: Invalid request
- **401 Unauthorized**: Authentication required
- **403 Forbidden**: Access denied
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation error

### 5xx Server Error
- **500 Internal Server Error**: Server error
- **502 Bad Gateway**: Upstream server error
- **503 Service Unavailable**: Server overloaded

## Request/Response Format

### Headers
- **Content-Type**: application/json
- **Accept**: application/json
- **Authorization**: Bearer token
- **User-Agent**: Client information

### Request Body
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "age": 30
}
```

### Response Body
```json
{
  "id": 123,
  "name": "John Doe",
  "email": "john@example.com",
  "age": 30,
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Error Handling

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}
```

### Error Types
- **Validation Errors**: Input validation failures
- **Business Logic Errors**: Domain-specific errors
- **System Errors**: Server-side errors
- **Authentication Errors**: Auth-related issues

## Authentication

### API Keys
- Simple authentication
- Header-based
- Easy to implement

### JWT Tokens
- Stateless authentication
- Self-contained
- Expiration support

### OAuth 2.0
- Industry standard
- Multiple grant types
- Third-party integration

## Versioning

### URL Versioning
- /api/v1/users
- /api/v2/users
- Clear versioning

### Header Versioning
- Accept: application/vnd.api+json;version=1
- More flexible
- Cleaner URLs

### Query Parameter Versioning
- ?version=1
- Simple implementation
- Less common

## Pagination

### Offset-Based
- ?page=1&limit=10
- Simple to implement
- Performance issues with large offsets

### Cursor-Based
- ?cursor=abc123&limit=10
- Better performance
- More complex implementation

### Response Format
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 100,
    "pages": 10
  }
}
```

## Rate Limiting

### Implementation
- Request counting
- Time window limits
- IP-based or user-based

### Headers
- X-RateLimit-Limit: 1000
- X-RateLimit-Remaining: 999
- X-RateLimit-Reset: 1640995200

### Strategies
- Fixed window
- Sliding window
- Token bucket
- Leaky bucket

## Documentation

### OpenAPI/Swagger
- Interactive documentation
- Code generation
- Testing capabilities

### API Documentation
- Clear descriptions
- Examples for each endpoint
- Error scenarios
- Authentication requirements

## Testing

### Unit Testing
- Test individual functions
- Mock external dependencies
- High coverage

### Integration Testing
- Test API endpoints
- Database interactions
- External service calls

### Load Testing
- Performance under load
- Scalability testing
- Bottleneck identification
