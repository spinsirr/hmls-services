FROM python:3.11-slim

WORKDIR /app

# Copy requirements files
COPY hmls-services/notification-service/requirements.txt .
COPY hmls-services/common/requirements.txt ./common-requirements.txt

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt -r common-requirements.txt

# Copy application code
COPY hmls-services/notification-service/ .
COPY hmls-services/common/ ./common/

# Expose port
EXPOSE 8003

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8003"] 