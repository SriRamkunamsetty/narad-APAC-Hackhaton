# NARAD Incident Response Runbook

This is a starting template, not a finished operational document. Before any real deployment, this needs: actual on-call names/contacts, a real paging system (PagerDuty/Opsgenie), and sign-off from whoever owns operations for the deployment. Filling in the brackets below is the minimum bar before this is usable.

---

## Severity Levels

| Severity | Definition | Response time | Example |
|---|---|---|---|
| **SEV-1** | Core service down, no city data flowing | Immediate | Cloud Run service returning 5xx on all requests |
| **SEV-2** | Degraded but functional — a subsystem down | Within 1 hour | Gemini API down (agents fall back to rule-based) |
| **SEV-3** | Minor issue, no user-facing impact | Within 1 business day | BigQuery history temporarily unavailable |

**On-call contact:** `[FILL IN — name, phone, escalation path]`
**Paging system:** `[FILL IN — PagerDuty/Opsgenie/etc]`

---

## First Response: Always Start Here

```bash
# 1. Is the service even reachable?
curl -w "\n%{http_code}\n" https://[YOUR_CLOUD_RUN_URL]/api/health

# 2. What does the deepened health check say?
curl https://[YOUR_CLOUD_RUN_URL]/api/health | python3 -m json.tool
```

The `/api/health` response tells you exactly what's degraded:
- `"status": "unhealthy"` → core functionality broken, treat as SEV-1
- `"status": "degraded"` → optional integration down (Gemini or admin key unset), treat as SEV-2/3
- `"status": "healthy"` → check the specific symptom you're chasing elsewhere

Then check each integration individually:
```bash
curl https://[URL]/api/diagnostics/llm
curl https://[URL]/api/diagnostics/traffic
curl https://[URL]/api/diagnostics/bigquery
```

---

## Scenario: Gemini API is down or rate-limited

**Symptoms:** Parliament sessions show generic "Automated fallback analysis" text instead of specific reasoning; `/api/diagnostics/llm` shows `"live_call_success": false`.

**Impact:** Degraded, not down. The rule-based fallback (`_fallback_stance` in `parliament.py`) keeps the system operational with simpler heuristics.

**Action:**
1. Check [Google Cloud Status Dashboard](https://status.cloud.google.com/) for Gemini API incidents.
2. Check quota: `gcloud services quota list --service=generativelanguage.googleapis.com`
3. If quota-exhausted, this is expected behavior working correctly — no code fix needed, just wait or request a quota increase.
4. If Gemini is confirmed down upstream, no action needed — system self-heals when it recovers. Communicate degraded mode to stakeholders if this persists beyond 15 minutes.

---

## Scenario: BigQuery unavailable

**Symptoms:** `/api/diagnostics/bigquery` shows `"available": false`; hospital reports submitted on one instance don't appear on another (if running multiple Cloud Run instances).

**Impact:** SEV-3 on a single instance (in-memory fallback works fine). **SEV-2 if running multiple instances** — hospital report cross-instance consistency depends on BigQuery.

**Action:**
1. Check the actual error: `curl https://[URL]/api/diagnostics/bigquery`
2. Common causes: expired/revoked service account credentials, BigQuery API quota, IAM permissions changed.
3. Verify service account permissions:
   ```bash
   gcloud projects get-iam-policy $PROJECT_ID \
     --flatten="bindings[].members" \
     --filter="bindings.members:*compute@developer.gserviceaccount.com"
   ```
4. If this is a multi-instance deployment and BigQuery is down, consider temporarily scaling to `--min-instances=1 --max-instances=1` to sidestep the cross-instance consistency gap until BigQuery recovers.

---

## Scenario: Suspected unauthorized data manipulation

**Symptoms:** Hospital capacity numbers look implausible; someone reports a hospital status that doesn't match reality.

**Impact:** SEV-1 — this is exactly the "manipulate the system" risk the security layer exists to prevent.

**Action:**
1. **Immediately check the audit log** — every write is logged with identity, IP, and details:
   ```sql
   SELECT * FROM `[PROJECT].[DATASET].audit_log`
   WHERE action = 'hospital_report_submit'
   ORDER BY timestamp DESC LIMIT 50
   ```
2. Identify the submitting IP/identity and cross-reference against known authorized operators.
3. **Rotate the admin API key immediately** if compromise is suspected:
   ```bash
   NEW_KEY=$(openssl rand -hex 24)
   printf '%s' "$NEW_KEY" | gcloud secrets versions add narad-admin-key --data-file=-
   gcloud run services update narad-city-ai --region=$REGION \
     --update-secrets=NARAD_ADMIN_API_KEY=narad-admin-key:latest
   ```
   Distribute the new key to legitimate operators through a secure channel immediately after rotation.
4. Delete the fraudulent report:
   ```bash
   curl -X DELETE "https://[URL]/api/manual-data/hospital/[NAME]" -H "X-API-Key: $NEW_KEY"
   ```
5. **This incident is a strong signal that per-user authentication (Firebase Auth) is overdue** — see the [Security](../README.md#-security) section of the README. A shared key cannot prevent this class of incident from recurring; it can only help you detect and respond to it after the fact.

---

## Scenario: Memory growth / instance restarting repeatedly

**Symptoms:** Cloud Run instance restarts unexpectedly; Cloud Monitoring shows steadily climbing memory usage before each restart.

**Likely cause:** Check first whether this is the ADK session leak (fixed as of this version — every parliament session now cleans up its sessions via `try/finally`). If you're running an older version of this code, that's almost certainly the cause.

**Action:**
1. Confirm the fix is present: `grep -n "delete_session" backend/agents/parliament.py` should show it being called in a `finally` block.
2. If present and the leak persists, check for a NEW leak source — anything creating ADK sessions, WebSocket connections, or BigQuery clients without cleanup.
3. Cloud Monitoring → Metrics Explorer → filter by `run.googleapis.com/container/memory/utilizations` for the service, to visualize the growth curve.

---

## Scenario: Rate limiting blocking legitimate traffic

**Symptoms:** Users report `429 Too Many Requests` on `/api/ask` or `/api/scenario/simulate`.

**Action:**
1. Check if this is a genuine traffic spike or a misbehaving client hammering the endpoint.
2. Current limits: `/api/ask` = 15/min/IP, `/api/scenario/simulate` = 20/min/IP (see `backend/main.py` route decorators).
3. If legitimate traffic needs a higher limit, adjust the `rate_limiter(max_requests=..., window_seconds=...)` values and redeploy.
4. **Remember:** this rate limiter is in-memory and per-instance. If running multiple Cloud Run instances, actual aggregate throughput allowed is `limit × instance_count`. For real production rate limiting, migrate to Google Cloud Armor at the load balancer level.

---

## Rolling Back a Bad Deployment

```bash
# List recent revisions
gcloud run revisions list --service=narad-city-ai --region=$REGION

# Roll back to a specific known-good revision
gcloud run services update-traffic narad-city-ai --region=$REGION \
  --to-revisions=[REVISION_NAME]=100
```

---

## Escalation Path (fill in before real deployment)

1. `[FILL IN — first responder]`
2. `[FILL IN — technical escalation]`
3. `[FILL IN — who has authority to take the service offline entirely, if needed]`

---

## What This Runbook Does NOT Cover

This document assumes you already have Cloud Monitoring alerting policies configured to page someone when `/api/health` returns non-200 or reports `"status": "unhealthy"`. **That alerting does not exist yet** — this runbook tells you what to do once paged, not how the page gets triggered. Setting up that alerting is a required next step, not an assumption this document should quietly make.
