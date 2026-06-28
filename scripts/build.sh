#!/usr/bin/env bash
set -o errexit

pip install --upgrade pip
pip install -r requirements.txt
python3 -m spacy download en_core_web_sm

echo "Build completed successfully!"
