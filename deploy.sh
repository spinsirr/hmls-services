#!/bin/bash

# HMLS Services Deployment Script
# This script helps deploy the HMLS distributed services

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}HMLS Services Deployment${NC}"
echo "==============================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed. Please install Docker and try again.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed. Please install Docker Compose and try again.${NC}"
    exit 1
fi

# Navigate to the root directory
cd ..

# Check if .env file exists
if [ ! -f hmls-services/.env ]; then
    echo -e "${YELLOW}Warning: .env file not found. Creating from .env.example${NC}"
    cp hmls-services/.env.example hmls-services/.env
    echo -e "${YELLOW}Please update the .env file with your configuration before continuing.${NC}"
    exit 1
fi

# Make sure the database initialization script is executable
chmod +x hmls-services/scripts/init-multiple-postgres-dbs.sh

# Build and start the services
echo -e "${GREEN}Building and starting services...${NC}"
docker-compose -f hmls-services/docker-compose.yml build
docker-compose -f hmls-services/docker-compose.yml up -d

# Check if services are running
echo -e "${GREEN}Checking service status...${NC}"
sleep 5 # Give services time to start

# Check API Gateway
if curl -s http://localhost:8000/health | grep -q "healthy"; then
    echo -e "${GREEN}API Gateway is running.${NC}"
else
    echo -e "${RED}API Gateway is not responding. Check logs with 'docker-compose -f hmls-services/docker-compose.yml logs api-gateway'${NC}"
fi

# Check Auth Service
if curl -s http://localhost:8001/health | grep -q "healthy"; then
    echo -e "${GREEN}Auth Service is running.${NC}"
else
    echo -e "${RED}Auth Service is not responding. Check logs with 'docker-compose -f hmls-services/docker-compose.yml logs auth-service'${NC}"
fi

# Check Appointment Service
if curl -s http://localhost:8002/health | grep -q "healthy"; then
    echo -e "${GREEN}Appointment Service is running.${NC}"
else
    echo -e "${RED}Appointment Service is not responding. Check logs with 'docker-compose -f hmls-services/docker-compose.yml logs appointment-service'${NC}"
fi

# Check Notification Service
if curl -s http://localhost:8003/health | grep -q "healthy"; then
    echo -e "${GREEN}Notification Service is running.${NC}"
else
    echo -e "${RED}Notification Service is not responding. Check logs with 'docker-compose -f hmls-services/docker-compose.yml logs notification-service'${NC}"
fi

echo -e "${GREEN}Deployment completed!${NC}"
echo "==============================="
echo -e "API Gateway: http://localhost:8000"
echo -e "Auth Service: http://localhost:8001"
echo -e "Appointment Service: http://localhost:8002"
echo -e "Notification Service: http://localhost:8003"
echo -e "==============================="
echo -e "To view logs: docker-compose -f hmls-services/docker-compose.yml logs -f"
echo -e "To stop services: docker-compose -f hmls-services/docker-compose.yml down"
echo -e "To restart services: docker-compose -f hmls-services/docker-compose.yml restart" 