# NARAD Incident Response & Runbook

This document outlines common failure scenarios, escalation paths, and remediation procedures for operating NARAD in production.

## 1. Core Services Dependencies
NARAD relies on the following external services:
- **Gemini API**: Powers the AI agent parliament.
- **Google Maps API**: Live traffic data.
- **OpenWeather / OpenAQ**: Live weather and air quality.
- **BigQuery**: State synchronization and historical data storage.

## 2. Common Failure Scenarios

### 2.1. Gemini API Timeout or Quota Exhaustion
**Symptoms**: 
- Parliament sessions fail to complete.
- Dashboard shows fallback rule-based decisions.
**Remediation**:
- Check GCP quotas for Gemini API.
- The system gracefully degrades to rule-based logic to ensure stability. No immediate action is required for safety, but check the API key configuration.

### 2.2. BigQuery Connection Failure
**Symptoms**:
- `api/diagnostics/bigquery` reports unavailable.
- Hospital self-reports do not sync across Cloud Run instances.
**Remediation**:
- Check GCP Service Account permissions (`roles/bigquery.dataEditor`).
- The system will fallback to in-memory caching. Redeploy or fix permissions to restore horizontal scaling sync.

### 2.3. ADK Session Memory Leaks
**Symptoms**:
- Cloud Run instance memory usage steadily increases over time.
**Remediation**:
- This issue was patched in v1.1. Ensure the backend is running the latest deployment image where `runner.run_async` is properly wrapped in a `try/finally` block to call `delete_session`.

## 3. Escalation Paths
- **Level 1 (Automated)**: Anomaly detection triggers parliament.
- **Level 2 (Manual)**: Authorized admins trigger a session via `/api/parliament/trigger`.
- **Level 3 (System Outage)**: If the Cloud Run service is unreachable, check the Load Balancer / Cloud Armor logs.

## 4. Post-Incident Review
All manual triggers and hospital reports are logged in the `audit_log` BigQuery table. Use these logs to reconstruct the timeline of events during a crisis.
