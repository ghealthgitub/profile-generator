#!/bin/bash

# 🫚 GINGER UNIVERSE - Quick Start Script

echo "========================================"
echo "🫚 GINGER UNIVERSE"
echo "Doctor Profile Generator"
echo "========================================"
echo ""

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed!"
    echo "Please install Python 3.8+ from python.org"
    exit 1
fi

echo "✅ Python found: $(python3 --version)"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate 2>/dev/null || . venv/Scripts/activate 2>/dev/null

# Install dependencies
echo "📥 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo ""
echo "✅ Setup complete!"
echo ""
echo "========================================"
echo "🚀 Starting Ginger Universe..."
echo "========================================"
echo ""
echo "🌐 Access the application at:"
echo "   http://localhost:5000"
echo ""
echo "🔑 Default login:"
echo "   Username: admin@ginger.healthcare"
echo "   Password: GingerUniverse2026!"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

# Run the application
python3 app.py
