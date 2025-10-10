#!/bin/bash

# TapCommand Backend Startup Script

echo "Starting TapCommand Backend..."

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "Creating virtual environment..."
    cd ..
    python3 -m venv venv
    cd backend
fi

# Activate virtual environment
echo "Activating virtual environment..."
source ../venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Start the FastAPI server
echo "Starting FastAPI server..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload