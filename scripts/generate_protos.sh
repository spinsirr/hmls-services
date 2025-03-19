#!/bin/bash

# Generate Python code from proto files
python -m grpc_tools.protoc \
  -I./common/proto \
  --python_out=./common/proto \
  --grpc_python_out=./common/proto \
  ./common/proto/auth.proto \
  ./common/proto/appointment.proto \
  ./common/proto/notification.proto

# Create __init__.py files to make the generated code importable
touch ./common/proto/__init__.py
touch ./common/proto/auth_pb2_grpc.py
touch ./common/proto/appointment_pb2_grpc.py
touch ./common/proto/notification_pb2_grpc.py

echo "Proto files generated successfully!" 