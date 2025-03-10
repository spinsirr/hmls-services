#!/bin/bash

# HMLS Auth Service Test Script
# This script tests the basic functionality of the Auth Service

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}HMLS Auth Service Test${NC}"
echo "==============================="

# Base URL for the Auth Service
AUTH_URL="http://localhost:8001"

# Test health endpoint
echo -e "${YELLOW}Testing health endpoint...${NC}"
curl -s $AUTH_URL/health
echo -e "\n\n"

# Register a test user
echo -e "${YELLOW}Registering a test user...${NC}"
REGISTER_RESPONSE=$(curl -s -X POST $AUTH_URL/register \
  -H "Content-Type: application/json" \
  -d '{
    "first_name": "Test",
    "last_name": "User",
    "email": "test_auth@example.com",
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
LOGIN_RESPONSE=$(curl -s -X POST $AUTH_URL/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test_auth@example.com&password=password123")
echo $LOGIN_RESPONSE | python -m json.tool
echo -e "\n"

# Extract the access token
ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# Get the current user profile
echo -e "${YELLOW}Getting the current user profile...${NC}"
curl -s -X GET $AUTH_URL/me \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool
echo -e "\n"

# Validate token
echo -e "${YELLOW}Validating token...${NC}"
curl -s -X POST $AUTH_URL/validate-token \
  -H "Authorization: Bearer $ACCESS_TOKEN" | python -m json.tool
echo -e "\n"

echo -e "${GREEN}Auth Service Test Completed!${NC}"
echo "===============================" 