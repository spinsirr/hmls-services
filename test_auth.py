#!/usr/bin/env python3

import httpx
import json

# Base URL for the Auth Service
AUTH_URL = "http://localhost:8001"

# Test health endpoint
print("Testing health endpoint...")
response = httpx.get(f"{AUTH_URL}/health")
print(f"Status: {response.status_code}")
print(response.json())
print()

# Register a test user
print("Registering a test user...")
register_data = {
    "first_name": "Python",
    "last_name": "Test",
    "email": "python_test@example.com",
    "phone_number": "5555555555",
    "password": "password123",
    "vehicle_year": "2022",
    "vehicle_make": "Tesla",
    "vehicle_model": "Model 3"
}
response = httpx.post(f"{AUTH_URL}/register", json=register_data)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
print()

# Login with the test user
print("Logging in with the test user...")
login_data = {
    "username": "python_test@example.com",
    "password": "password123"
}
response = httpx.post(
    f"{AUTH_URL}/login", 
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
print("Getting the current user profile...")
response = httpx.get(
    f"{AUTH_URL}/me",
    headers={"Authorization": f"Bearer {access_token}"}
)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
print()

# Validate token
print("Validating token...")
response = httpx.post(
    f"{AUTH_URL}/validate-token",
    headers={"Authorization": f"Bearer {access_token}"}
)
print(f"Status: {response.status_code}")
print(json.dumps(response.json(), indent=2))
print()

print("Auth Service Test Completed!") 