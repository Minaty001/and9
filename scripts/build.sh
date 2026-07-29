#!/usr/bin/env bash
set -o errexit

# Use virtual environment if it exists, otherwise create one
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt

echo "Build completed successfully!"
