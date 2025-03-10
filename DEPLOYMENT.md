# HMLS Services Deployment Guide

This guide provides instructions for deploying the HMLS distributed services.

## Prerequisites

- Docker
- Docker Compose
- Git

## Deployment Steps

### 1. Clone the Repository

If you haven't already, clone the repository:

```bash
git clone <repository-url>
cd hmls
```

### 2. Configure Environment Variables

Copy the example environment file and update it with your configuration:

```bash
cd hmls-services
cp .env.example .env
```

Edit the `.env` file to update the following:
- `SECRET_KEY`: Set a secure secret key
- `SMTP_SERVER`, `SMTP_USERNAME`, `SMTP_PASSWORD`: Configure for email notifications
- `SMS_API_KEY`: Configure for SMS notifications

### 3. Deploy with the Deployment Script

Run the deployment script:

```bash
./deploy.sh
```

This script will:
- Check for required dependencies
- Build and start all services
- Verify that services are running

### 4. Manual Deployment

If you prefer to deploy manually:

1. Make sure the database initialization script is executable:
   ```bash
   chmod +x hmls-services/scripts/init-multiple-postgres-dbs.sh
   ```

2. Build and start the services:
   ```bash
   cd hmls-services
   docker-compose build
   docker-compose up -d
   ```

3. Check service status:
   ```bash
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   curl http://localhost:8003/health
   ```

## Service URLs

- API Gateway: http://localhost:8000
- Auth Service: http://localhost:8001
- Appointment Service: http://localhost:8002
- Notification Service: http://localhost:8003

## Testing the API

After deploying the services, you can run the test script to verify that the API Gateway is working correctly:

```bash
./test_api.sh
```

This script will:
1. Test the health endpoints
2. Register a test user
3. Log in with the test user
4. Get the user profile
5. Create an appointment
6. Get all appointments

## Useful Commands

- View logs: `docker-compose logs -f`
- Stop services: `docker-compose down`
- Restart services: `docker-compose restart`
- View specific service logs: `docker-compose logs -f <service-name>`

## Troubleshooting

### Services Not Starting

Check the logs for errors:
```bash
docker-compose logs -f
```

### Database Connection Issues

Ensure the PostgreSQL container is running:
```bash
docker-compose ps postgres
```

Check PostgreSQL logs:
```bash
docker-compose logs postgres
```

### Redis Connection Issues

Ensure the Redis container is running:
```bash
docker-compose ps redis
```

Check Redis logs:
```bash
docker-compose logs redis
``` 