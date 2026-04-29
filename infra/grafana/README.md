# Grafana (optional, Phase 7+)

This directory holds Grafana provisioning files for monitoring the bot when
running in live mode. Not enabled in the default Docker Compose.

To enable, add a Grafana service to a compose override and mount this
directory at `/etc/grafana/provisioning` and `/var/lib/grafana/dashboards`.

Suggested dashboards (TODO):
- bot_overview.json — uptime, P&L by window, open positions, last signal
- risk_health.json — drawdown, consecutive losses, kill switch state, approval expiry
- ml_health.json — model accuracy_oos, last training time, prediction count
