#!/usr/bin/env python3

import httpx
import json

# Base URL for the API Gateway
API_URL = "http://localhost:8000"

# Test health endpoint
print("Testing health endpoint...")
response = httpx.get(f"{API_URL}/health")
print(f"Status: {response.status_code}")
print(response.json())
print()

# Register a test user
print("Registering a test user through API Gateway...")
register_data = {
    "first_name": "API",
    "last_name": "Gateway",
    "email": "api_gateway@example.com",
    "phone_number": "1112223333",
    "password": "password123",
    "vehicle_year": "2023",
    "vehicle_make": "Ford",
    "vehicle_model": "Mustang"
}
response = httpx.post(f"{API_URL}/auth/register", json=register_data)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
print()

# Login with the test user
print("Logging in with the test user through API Gateway...")
login_data = {
    "username": "api_gateway@example.com",
    "password": "password123"
}
response = httpx.post(
    f"{API_URL}/auth/login", 
    data=login_data,
    headers={"Content-Type": "application/x-www-form-urlencoded"}
)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
print()

# Extract the access token
token_data = response.json()
access_token = token_data.get("access_token")

# Get the current user profile
print("Getting the current user profile through API Gateway...")
response = httpx.get(
    f"{API_URL}/auth/me",
    headers={"Authorization": f"Bearer {access_token}"}
)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
print()

print("API Gateway Test Completed!") 