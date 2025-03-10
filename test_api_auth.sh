#!/bin/bash

# HMLS API Gateway Auth Test Script
# This script tests the authentication endpoints of the API Gateway

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}HMLS API Gateway Auth Test${NC}"
echo "==============================="

# Base URL for the API Gateway
API_URL="http://localhost:8000"

# Test health endpoint
echo -e "${YELLOW}Testing health endpoint...${NC}"
curl -s $API_URL/health
echo -e "\n\n"

# Register a test user
echo -e "${YELLOW}Registering a test user through API Gateway...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "API",
    "last_name": "User",
    "email": "api_test@example.com",
    "phone_number": "9876543210",
    "password": "password123",
    "vehicle_year": "2021",
    "vehicle_make": "Honda",
    "vehicle_model": "Civic"
  }')
echo $REGISTER_RESPONSE | python -m json.tool
echo -e "\n"

# Login with the test user
echo -e "${YELLOW}Logging in with the test user through API Gateway...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST $API_URL/auth/login \
  --data-urlencode "username=api_test@example.com" \
  --data-urlencode "password=password123")
echo $LOGIN_RESPONSE | python -m json.tool
echo -e "\n"

# Extract the access token
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Get the current user profile
echo -e "${YELLOW}Getting the current user profile through API Gateway...${NC}"
curl -s -X GET $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool
echo -e "\n"

echo -e "${GREEN}API Gateway Auth Test Completed!${NC}"
echo "===============================" 