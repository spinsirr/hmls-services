#!/bin/bash

# HMLS Services API Test Script
# This script tests the basic functionality of the HMLS distributed services

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}HMLS Services API Test${NC}"
echo "==============================="

# Base URL for the API Gateway
API_URL="http://localhost:8000"

# Test health endpoints
echo -e "${YELLOW}Testing health endpoints...${NC}"
curl -s $API_URL/health
echo -e "\n"

# Register a test user
echo -e "${YELLOW}Registering a test user...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST $API_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "email": "test@example.com",
    "phone_number": "1234567890",
    "password": "password123",
    "vehicle_year": "2020",
    "vehicle_make": "Toyota",
    "vehicle_model": "Camry"
  }')
echo $REGISTER_RESPONSE | python -m json.tool
echo -e "\n"

# Login with the test user
echo -e "${YELLOW}Logging in with the test user...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST $API_URL/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=password123")
echo $LOGIN_RESPONSE | python -m json.tool
echo -e "\n"

# Extract the access token
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Get the current user profile
echo -e "${YELLOW}Getting the current user profile...${NC}"
curl -s -X GET $API_URL/auth/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool
echo -e "\n"

# Create an appointment
echo -e "${YELLOW}Creating an appointment...${NC}"
APPOINTMENT_RESPONSE=$(curl -s -X POST $API_URL/appointments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{
    "email": "test@example.com",
    "phone_number": "1234567890",
    "appointment_time": "2025-04-01T10:00:00Z",
    "vehicle_year": "2020",
    "vehicle_make": "Toyota",
    "vehicle_model": "Camry",
    "problem_description": "Regular maintenance"
  }')
echo $APPOINTMENT_RESPONSE | python -m json.tool
echo -e "\n"

# Get all appointments
echo -e "${YELLOW}Getting all appointments...${NC}"
curl -s -X GET $API_URL/appointments \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool
echo -e "\n"

echo -e "${GREEN}API Test Completed!${NC}"
echo "===============================" 