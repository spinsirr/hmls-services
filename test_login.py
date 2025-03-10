#!/usr/bin/env python3

import httpx
import json
import urllib.parse

# Test direct login to Auth Service
print("Testing direct login to Auth Service...")
auth_url = "http://localhost:8001/login"
auth_data = urllib.parse.urlencode({
    "username": "python_test@example.com",
    "password": "password123"
})
auth_headers = {"Content-Type": "application/x-www-form-urlencoded"}

auth_response = httpx.post(auth_url, content=auth_data, headers=auth_headers)
print(f"Auth Service Status: {auth_response.status_code}")
print(json.dumps(auth_response.json(), indent=2))
print()

# Test login through API Gateway
print("Testing login through API Gateway...")
api_url = "http://localhost:8000/auth/login"
api_data = urllib.parse.urlencode({
    "username": "python_test@example.com",
    "password": "password123"
})
api_headers = {"Content-Type": "application/x-www-form-urlencoded"}

api_response = httpx.post(api_url, content=api_data, headers=api_headers)
print(f"API Gateway Status: {api_response.status_code}")
print(json.dumps(api_response.json(), indent=2))
print()

print("Login Test Completed!") 