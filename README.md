# HMLS Distributed Services

This directory contains a distributed microservices implementation of the HMLS system, breaking down the monolithic server into separate services that communicate with each other.

## Architecture Overview

The system is composed of the following services:

1. **API Gateway**: Entry point for all client requests, handles routing to appropriate services
2. **Auth Service**: Manages user authentication and authorization
3. **Appointment Service**: Handles appointment creation, scheduling, and management
4. **Notification Service**: Manages sending notifications to users

## Communication

Services communicate with each other using:
- REST API calls for synchronous operations
- Message queues (Redis) for asynchronous operations

## Shared Components

Common code is shared through the `common` package, which includes:
- Data models
- Utility functions
- Configuration management

## Getting Started

1. Set up environment variables in each service's `.env` file
2. Start each service individually or use Docker Compose to start all services
3. Access the API through the API Gateway

## Development

Each service can be developed and deployed independently, allowing for:
- Independent scaling
- Isolated testing
- Separate deployment pipelines

## Service Dependencies

- PostgreSQL: For persistent data storage
- Redis: For caching, message queues, and rate limiting

## Directory Structure

```
hmls-services/
├── api-gateway/         # API Gateway service
├── auth-service/        # Authentication service
├── appointment-service/ # Appointment management service
├── notification-service/# Notification service
└── common/              # Shared code and utilities
    ├── models/          # Shared data models
    └── utils/           # Shared utility functions
``` 