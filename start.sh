#!/bin/bash

echo "Starting M-Team Auto Login Tool..."
echo

echo "Running M-Team Auto Login..."
if command -v python3 &> /dev/null; then
    python3 install.py
    python3 run.py
elif command -v python &> /dev/null; then
    python install.py
    python run.py
else
    echo "Error: Python interpreter not found"
    echo "Please ensure Python is properly installed"
    exit 1
fi

echo
echo "Program completed" 