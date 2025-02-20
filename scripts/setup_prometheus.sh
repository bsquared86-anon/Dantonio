#!/bin/bash

set -e

# Create Prometheus configuration
mkdir -p prometheus/data
cp monitoring/prometheus/prometheus.yml prometheus/

# Start Prometheus
docker run -d \
    --name prometheus \
    -p 9090:9090 \
    -v $(pwd)/prometheus:/etc/prometheus \
    -v prometheus-data:/prometheus \
    prom/prometheus

# Configure alerting rules
cp monitoring/prometheus/rules.yml prometheus/

# Reload Prometheus configuration
curl -X POST http://localhost:9090/-/reload

echo "Prometheus setup completed"

