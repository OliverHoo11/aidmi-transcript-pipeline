#!/bin/bash

# AidMi Transcript Pipeline - Run Script

echo "======================================"
echo "AidMi Transcript-to-Note Pipeline"
echo "======================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found!"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo ""
    echo "⚠️  Please edit .env and add your OPENAI_API_KEY"
    echo "Then run this script again."
    exit 1
fi

# Check if OpenAI API key is set
if ! grep -q "OPENAI_API_KEY=sk-" .env; then
    echo "⚠️  OPENAI_API_KEY not configured in .env file"
    echo "Please edit .env and add your OpenAI API key"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✓ Setup complete!"
echo ""
echo "Starting FastAPI server..."
echo "API will be available at: http://localhost:8000"
echo "API docs available at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Run the server
python main.py
