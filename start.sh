#!/bin/bash

echo "Starting M-Team Auto Login Tool (with Virtual Environment)..."
echo

echo "Running auto installer (will create virtual environment)..."
if command -v python3 &> /dev/null; then
    python3 install.py
elif command -v python &> /dev/null; then
    python install.py
else
    echo "Error: Python interpreter not found"
    echo "Please ensure Python is properly installed"
    exit 1
fi

echo
echo "Installation complete, starting main program in virtual environment..."
echo

echo "Running M-Team Auto Login in virtual environment..."
if [ -f "venv/bin/python" ]; then
    echo "Using virtual environment Python..."
    venv/bin/python run.py
else
    echo "Virtual environment not found, using system Python..."
    if command -v python3 &> /dev/null; then
        python3 run.py
    elif command -v python &> /dev/null; then
        python run.py
    else
        echo "Error: Python interpreter not found"
        echo "Please ensure Python is properly installed"
        exit 1
    fi
fi

echo
echo "Program completed, exiting automatically..."
sleep 2 