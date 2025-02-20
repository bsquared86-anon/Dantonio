#!/bin/bash

set -e

# Grafana setup
docker run -d \
    --name grafana \
    -p 3000:3000 \
    -v grafana-storage:/var/lib/grafana \
    grafana/grafana

# Configure datasource
curl -X POST \
    -H "Content-Type: application/json" \
    --data-binary @monitoring/grafana/datasource.json \
    http://admin:admin@localhost:3000/api/datasources

# Import dashboards
curl -X POST \
    -H "Content-Type: application/json" \
    --data-binary @monitoring/grafana/dashboard.json \
    http://admin:admin@localhost:3000/api/dashboards/db

echo "Grafana setup completed"

