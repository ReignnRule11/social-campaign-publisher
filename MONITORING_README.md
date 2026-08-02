Prometheus & Grafana monitoring (quick start)

Files added:
- prometheus.yml            - Prometheus scrape config (scrapes app:8000/metrics)
- docker-compose.monitoring.yml - Compose to start Prometheus + Grafana (assumes 'app' service from docker-compose.yml)
- grafana_dashboard.json    - Minimal dashboard JSON with retry-related panels

Quick start (with docker-compose from repo root):

1. Ensure docker and docker-compose are installed.
2. Start main stack and monitoring together:
   docker-compose -f docker-compose.yml -f docker-compose.monitoring.yml up --build
3. Grafana will be at http://localhost:3000. Default admin user is 'admin' and the password is taken from GRAFANA_ADMIN_PASSWORD env var (default 'admin' if not set).
   The dashboard is auto-provisioned; no manual import needed.
4. Prometheus UI at http://localhost:9090

Notes:
- docker-compose.monitoring.yml mounts provisioning files into Grafana so the datasource and dashboard are auto-loaded.
- For production, use Docker secrets to protect sensitive values. The compose file now uses a Docker secret for Grafana admin password: ./secrets/grafana_admin_password.txt. Replace that file with a secure secret before deploying.
- Persistent volumes (prometheus-data, grafana-data) are declared for Prometheus and Grafana. These ensure metric and dashboard state survives container restarts.
- Prometheus alert rules are included (prometheus_alerts.yml) that fire when retry_max_reached_total > 0.
- Alertmanager is included in docker-compose.monitoring.yml and wired to Prometheus. Alertmanager config examples (alertmanager.yml) include Slack and email receivers — replace placeholders with your secrets.
- To receive notifications, configure real SMTP/Slack webhook secrets and either mount them as Docker secrets or provide via a secure mechanism.
- To inspect dashboards before Grafana starts, you can view grafana_dashboard.json in the repo.
