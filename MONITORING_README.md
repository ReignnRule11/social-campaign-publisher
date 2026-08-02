Prometheus & Grafana monitoring (quick start)

Files added:
- prometheus.yml            - Prometheus scrape config (scrapes app:8000/metrics)
- docker-compose.monitoring.yml - Compose to start Prometheus + Grafana (assumes 'app' service from docker-compose.yml)
- grafana_dashboard.json    - Minimal dashboard JSON with retry-related panels

Quick start (with docker-compose from repo root):

1. Ensure docker and docker-compose are installed.
2. Start main stack and monitoring together:
   docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up --build
3. Grafana will be at http://localhost:3000 (admin/admin). Import the grafana_dashboard.json under Dashboards > Manage > Import.
4. Prometheus UI at http://localhost:9090

Notes:
- The docker-compose.monitoring.yml expects the app service name to be 'app' and reachable by that name from Prometheus (the default docker-compose in this repo exposes the app on port 8000).
- For production, secure Grafana and add persistent volumes for Prometheus & Grafana data.
