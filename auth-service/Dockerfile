FROM python:3.11-slim

WORKDIR /app

# Copy requirements files
COPY hmls-services/auth-service/requirements.txt .
COPY hmls-services/common/requirements.txt ./common-requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt -r common-requirements.txt

# Copy application code
COPY hmls-services/auth-service/ .
COPY hmls-services/common/ ./common/

# Expose gRPC port
EXPOSE 50051

# Command to run the application
CMD ["python", "main.py"] 