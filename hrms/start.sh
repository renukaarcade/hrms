#!/bin/bash
echo "========================================="
echo "  Hotel Room Management System (HRMS)"
echo "========================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required. Please install Python 3.8+"
    exit 1
fi

# Check Flask
python3 -c "import flask, jwt" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required packages..."
    pip3 install flask pyjwt --break-system-packages 2>/dev/null || pip3 install flask pyjwt
fi

echo "Starting HRMS Backend..."
echo "Open http://localhost:5000 in your browser"
echo ""
echo "Default Login: admin / admin123"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

cd "$(dirname "$0")/backend"
python3 server.py
