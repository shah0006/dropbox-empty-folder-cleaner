#!/bin/bash

# Check if client_secrets.json exists
if [ ! -f "client_secrets.json" ]; then
    echo "WARNING: client_secrets.json not found! Google Drive features may not work."
fi

# Start the application
# Using exec to replace the shell with the uvicorn process for better signal handling
exec uvicorn main:app --host 0.0.0.0 --port 8765
