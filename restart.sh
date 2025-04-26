#!/bin/bash

echo "Stopping old uvicorn process..."
pkill -f "uvicorn main:app --host 0.0.0.0 --port 8000"

sleep 2

echo "Starting uvicorn server..."
nohup uvicorn main:app --host 0.0.0.0 --port 8000 > uvicorn.log 2>&1 &

echo "Server restarted successfully!"
