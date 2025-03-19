#!/bin/bash

# Install the correct version of protobuf
pip install protobuf==4.25.1 grpcio==1.60.0 grpcio-tools==1.60.0

# Remove old generated files
rm -f common/proto/*_pb2.py common/proto/*_pb2_grpc.py

# Regenerate proto files
python -m grpc_tools.protoc \
  -I. \
  --python_out=. \
  --grpc_python_out=. \
  common/proto/auth.proto \
  common/proto/appointment.proto \
  common/proto/notification.proto

echo "Proto files regenerated successfully!" 