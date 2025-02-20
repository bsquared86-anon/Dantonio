#!/bin/bash

set -e

# Configuration
COVERAGE_MIN=80

# Run tests with coverage
pytest tests/ \
    --cov=app \
    --cov-report=term-missing \
    --cov-report=html:coverage \
    --junitxml=test-results.xml

# Check coverage threshold
coverage report --fail-under=$COVERAGE_MIN

# Run integration tests
pytest tests/integration --log-cli-level=INFO

echo "All tests passed successfully"

