#!/bin/bash

set -e

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup configuration
mkdir -p config
cp config/config.example.yaml config/config.yaml

# Setup database
python manage.py init_db

# Setup git hooks
cp scripts/git-hooks/* .git/hooks/
chmod +x .git/hooks/*

echo "Environment setup completed"

