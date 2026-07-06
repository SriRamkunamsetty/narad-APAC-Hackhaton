# 🏛️ NARAD
### Neural Agentic Real-time Advisor for Decisions

**A live AI parliament for Indian smart cities — 5 autonomous Google ADK agents that independently analyze real-time city data, debate, vote, and reach transparent consensus decisions, accelerated by NVIDIA RAPIDS for instant what-if scenario simulation.**

Built for the Google Cloud × NVIDIA Hackathon 2026 — addressing:
- **PS1: AI for Better Living and Smarter Communities** (primary fit)
- **PS2: Data Intelligence + Acceleration** — satisfies the "2+ services" requirement explicitly: **BigQuery** (Google Cloud data layer) + **NVIDIA RAPIDS and cuDF/CuPy** (NVIDIA acceleration layer), spanning both categories

---

## 🎯 What Makes NARAD Different

Most "smart city AI" submissions are a chatbot wrapped around a dashboard. NARAD is structurally different:

1. **Agent Parliament, not a single chatbot.** Five specialized ADK agents (Transport, Health, Environment, Economy, Safety) independently analyze the same live data and **vote**. When they disagree, NARAD logs the disagreement instead of hiding it — a transparent "dissent log" that shows exactly where city departments would clash in the real world.

2. **Causal reasoning, not just correlation.** NARAD doesn't just report "AQI is high." It traces the causal chain: traffic congestion → vehicular emissions → AQI spike → predicted ER visit surge within 6 hours — connecting five domains that are normally siloed.

3. **NVIDIA RAPIDS scenario simulation.** Ask "what if we close NH-44 for 3 hours?" and NARAD runs 1,000+ Monte Carlo simulations across traffic, health, safety, and environment impact — in milliseconds on GPU vs. minutes on CPU. This is a genuinely different decision-making capability, not just a speed bump.

4. **Real-time, not batch.** A live WebSocket feed streams city conditions, alerts, and parliament sessions to the dashboard continuously — this is built to run as a 24/7 city operations tool, not a one-shot demo.

5. **Honest data provenance, with a real path to zero simulation.** Every metric on the dashboard is labeled **● Live**, **✎ Manual**, or **○ Sim** — no hidden mock data. For sectors with no public API (hospital capacity, in India's case), NARAD doesn't just fake it: hospital staff can self-report their own status directly, and that becomes genuinely real data instantly, blended transparently with simulation only for hospitals that haven't reported yet. The moment a real government API exists for any domain, or more hospitals opt in, the "real" percentage grows with zero architecture changes — this is designed to converge toward 100% real data over time, not stay a permanent demo.

6. **"Ask NARAD" — a grounded, multilingual natural language interface.** Anyone — a city official, a journalist, a resident — can ask a plain-language question ("Is it safe to travel through the city right now?") and get an answer grounded in live city data, the latest parliament decision, and (once BigQuery is connected) similar past incidents pulled from real history — a lightweight RAG pipeline, not free-associated LLM output. It answers in English, Hindi, or Telugu, directly addressing PS1's "Accessibility and inclusive communities" solution area for a city where Telugu is the primary language for most residents.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     REACT DASHBOARD (Vite + Tailwind)            │
│   Live Metrics · Ask NARAD (NL, multilingual) · Agent Parliament │
│   UI · Scenario Simulator · RAPIDS Benchmark · Hospital Reports  │
└───────────────────────────┬───────────────────────────────────────┘
                            │ WebSocket + REST
┌───────────────────────────▼───────────────────────────────────────┐
│                    FASTAPI BACKEND (Cloud Run)                    │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────────┐ │
│  │ Live Data    │  │  Agent Parliament │  │  NVIDIA RAPIDS       │ │
│  │ Feeds        │──▶  5 ADK Agents     │  │  Engine               │ │
│  │ (Weather/    │  │  (Gemini 2.0)     │  │  (cuDF/cuPy + CPU    │ │
│  │  AQI/Traffic/│  │  Vote → Consensus │  │   fallback)           │ │
│  │  Hospital/   │  │  → Dissent Log →  │  │  Monte Carlo          │ │
│  │  Safety/Econ)│  │  Causal Chain     │  │  Simulation            │ │
│  └──────┬──────┘  └─────────┬────────┘  └──────────────────────┘ │
│         │                   │                                      │
│         ▼                   ▼                                      │
│  ┌────────────────────────────────┐  ┌───────────────────────┐   │
│  │  BigQuery (persistent history) │◀─│  Ask NARAD (NL + RAG)  │   │
│  │  pulse_history · decisions     │  │  Gemini + live context │   │
│  └────────────────────────────────┘  └───────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### The 5 Agents

| Agent | Domain | Key Signals |
|---|---|---|
| 🚦 Transport | Mobility, congestion, incidents | Congestion %, avg speed, travel time index |
| 🏥 Health | Hospital capacity, EMS | Bed availability, ICU capacity, ER wait times |
| 🌫️ Environment | Air quality, climate | AQI, PM2.5/PM10, heat stress |
| ⚡ Economy | Utilities, resources | Grid load, fuel prices, water supply |
| 🚔 Safety | Law enforcement, emergencies | Active incidents, response times, alert level |

Each agent runs **concurrently** (not sequentially) via `asyncio.gather`, analyzes the same live snapshot through its own domain lens using a Gemini-powered ADK `LlmAgent` with a custom analysis tool, and returns a structured vote (`approve` / `reject` / `abstain` / `escalate`) with confidence and urgency. A synthesis layer then:
- Counts votes to determine overall urgency
- Builds a **causal chain** connecting cross-domain effects
- Logs **dissent** wherever agents' urgency assessments diverge sharply
- Produces a prioritized action plan

---

## 📂 Project Structure

```
narad/
├── backend/
│   ├── main.py                    # FastAPI app, REST + WebSocket endpoints
│   ├── config.py                  # Environment configuration
│   ├── security.py                # API key auth, rate limiting, audit logging
│   ├── agents/
│   │   ├── specialized_agents.py  # The 5 ADK LlmAgent definitions + tools
│   │   ├── parliament.py          # Orchestrator: run agents, synthesize consensus
│   │   └── concierge.py           # "Ask NARAD" — grounded NL Q&A, multilingual (EN/HI/TE)
│   ├── data/
│   │   ├── live_feeds.py          # Real API calls (OpenWeather/OpenAQ/Google Maps) + simulation
│   │   ├── rapids_engine.py       # NVIDIA RAPIDS/cuDF Monte Carlo + benchmarking
│   │   ├── manual_reports.py      # Hospital self-reporting store (no public HMIS API exists)
│   │   └── bigquery_store.py      # Persistent history: pulse snapshots + parliament decisions
│   ├── models/
│   │   └── schemas.py             # Pydantic schemas for all data structures
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # Main dashboard shell
│   │   ├── components/              # StatusBar, CityPulseGrid, AgentParliament,
│   │   │                            # ScenarioSimulator, BenchmarkCard, TrendChart,
│   │   │                            # HospitalReportForm, AskNarad
│   │   ├── hooks/
│   │   │   ├── useNaradSocket.ts    # WebSocket connection with auto-reconnect
│   │   │   └── useAccessKey.ts      # Session-only access key (never in the build)
│   │   └── utils/api.ts             # REST client
│   └── package.json
├── deployment/
│   ├── cloudbuild.yaml             # CI/CD pipeline: build → push → deploy
│   └── deploy.sh                   # One-command deploy script
├── Dockerfile                      # CPU deployment (works everywhere, no GPU needed)
├── Dockerfile.gpu                  # GPU deployment with real RAPIDS/cuDF acceleration
├── setup.sh                        # Local dev setup
└── .env.example
```

---

## 🚀 Quick Start (Local)

### 1. Get a free Gemini API key
Visit **[aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)** → Create API key → copy the `AIza...` string. Takes 2 minutes, no billing required.

### 2. (Optional) Get a Google Maps API key for real live traffic
Visit **[console.cloud.google.com/google/maps-apis/credentials](https://console.cloud.google.com/google/maps-apis/credentials)**, enable the **Distance Matrix API**, and copy the key. Without this, traffic falls back to realistic simulation — everything still works, just not with live road data.

### 3. Set an admin access key
Required for any write action (submitting hospital reports, triggering a parliament session) — these endpoints refuse requests entirely without it. Any string works locally:
```
NARAD_ADMIN_API_KEY=my-local-dev-key
```

### 4. Setup
```bash
git clone <your-repo>
cd narad
chmod +x setup.sh && ./setup.sh
```

Edit `.env` and paste your keys:
```
GEMINI_API_KEY=AIzaSy...your_gemini_key_here
GOOGLE_MAPS_API_KEY=AIzaSy...your_maps_key_here   # optional
NARAD_ADMIN_API_KEY=my-local-dev-key
```

### 5. Run
```bash
# Terminal 1 — backend
python3 -m uvicorn backend.main:app --reload --port 8080

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open **http://localhost:5173** — you'll see live Hyderabad city data streaming in. Paste your `NARAD_ADMIN_API_KEY` into the dashboard's "Access Key" field (in Hospital Status Reporting) to unlock "Convene Session" and report submission — read-only data works without it.

> **No Gemini API key?** The system runs in graceful fallback mode — rule-based agent decisions instead of Gemini reasoning — so it never crashes, but you won't see the "wow" multi-agent reasoning. Get the key, it's free and takes 2 minutes.

### 6. Verify what's actually live
```bash
curl http://localhost:8080/api/diagnostics/llm
curl http://localhost:8080/api/diagnostics/traffic
curl http://localhost:8080/api/diagnostics/bigquery
```
All three should report success once your keys/credentials are in place — see [What's Real vs. Simulated](#-whats-real-vs-simulated-full-transparency) below for exactly what each controls. BigQuery is optional locally (history falls back to an in-memory buffer without it) but enables persistent, queryable history across restarts — see [BigQuery Setup](#-bigquery-persistent-history-ps2) below.

---

## 🗄️ BigQuery: Persistent History (PS2)

The in-memory buffers (`state.pulse_history`, `state.decision_history`) are fast but reset on every restart and don't survive Cloud Run scaling to multiple instances. BigQuery replaces both with real, queryable, persistent storage — this is the piece that explicitly satisfies PS2's "use 2+ services from the Google Cloud data layer" requirement, alongside NVIDIA RAPIDS/cuDF on the acceleration side.

**What gets stored:**
- Every city pulse snapshot (`pulse_history` table) — AQI, congestion, hospital load, incidents, overall health score, plus the full raw JSON
- Every parliament decision (`parliament_decisions` table) — consensus, causal chain, dissent log, action plan, full raw JSON

**What this unlocks beyond just "persistence":**
- Real historical trend queries (`/api/city-pulse/history?hours=24` now queries actual BigQuery data, not a 200-point rolling window)
- Lightweight RAG for "Ask NARAD" — when answering a question, NARAD pulls similar past incidents (same urgency level) from BigQuery as grounding context
- A clean foundation for BigQuery ML forecasting (predicting AQI/traffic/hospital load hours ahead) as a natural next step — the historical table already exists

**Setup (local):**
```bash
# 1. Set a REAL GCP project you own in .env
GCP_PROJECT_ID=your-real-project-id

# 2. Authenticate locally
gcloud auth application-default login

# 3. Enable the API
gcloud services enable bigquery.googleapis.com

# 4. Verify
curl http://localhost:8080/api/diagnostics/bigquery
```

**Setup (Cloud Run deployment):** handled automatically by `deployment/deploy.sh` — it enables the BigQuery API and grants the Cloud Run service account `roles/bigquery.dataEditor` + `roles/bigquery.jobUser`.

**Without any of this configured:** NARAD runs exactly as before — in-memory buffers serve every endpoint, nothing breaks, `/api/diagnostics/bigquery` just reports `"available": false` with a clear explanation of what to fix.

---

## ☁️ Deploy to Google Cloud Run

### One command:
```bash
chmod +x deployment/deploy.sh
./deployment/deploy.sh YOUR_GCP_PROJECT_ID YOUR_GEMINI_API_KEY us-central1 YOUR_GOOGLE_MAPS_API_KEY
```

This will:
1. Enable required GCP APIs (Cloud Run, Cloud Build, Artifact Registry)
2. Build the Docker image (multi-stage: React build → Python backend)
3. Push to Artifact Registry
4. Deploy to Cloud Run with your API key as a secure env var
5. Print your live public URL

### Manual deployment:
```bash
gcloud builds submit \
  --config=deployment/cloudbuild.yaml \
  --substitutions=_GEMINI_API_KEY="your_key_here",_GOOGLE_MAPS_API_KEY="optional_maps_key" \
  .
```

### GPU-accelerated deployment (real RAPIDS, not simulated speedup):
```bash
docker build -f Dockerfile.gpu -t narad-gpu .
docker tag narad-gpu us-central1-docker.pkg.dev/PROJECT_ID/narad-repo/narad-gpu
docker push us-central1-docker.pkg.dev/PROJECT_ID/narad-repo/narad-gpu

gcloud run deploy narad-gpu \
  --image=us-central1-docker.pkg.dev/PROJECT_ID/narad-repo/narad-gpu \
  --region=us-central1 \
  --gpu=1 --gpu-type=nvidia-l4 \
  --memory=16Gi --cpu=4 --no-cpu-throttling \
  --set-env-vars=GEMINI_API_KEY=your_key_here,SERVE_STATIC=true,GOOGLE_MAPS_API_KEY=optional_maps_key
```

> **Note:** Cloud Run GPU support (nvidia-l4) requires your project to be allowlisted / have GPU quota in the target region. Without it, the CPU Dockerfile still demonstrates the full parliament + scenario simulation logic, with a clearly-labeled *simulated* RAPIDS speedup based on real CPU benchmarks — the architecture is identical either way, only the execution backend (cuDF vs pandas) changes.

---

## 🔒 Security

Every write endpoint fails **closed**, not open — if `NARAD_ADMIN_API_KEY` isn't configured on the server, data-mutating requests are refused outright rather than silently allowed through.

**What's implemented and tested:**

| Protection | Where | What it stops |
|---|---|---|
| API key auth (`X-API-Key` header) | Hospital report submit/delete, parliament trigger (REST **and** WebSocket) | Anonymous submission of fake hospital data; unauthorized cost-incurring Gemini calls |
| Fail-closed design | Same endpoints | If the key is simply unset, writes are refused — never silently open |
| Rate limiting (per-IP) | `/api/ask` (15/min), `/api/scenario/simulate` (20/min) | Cost/abuse from repeated Gemini or compute-heavy calls |
| Input validation (Pydantic `Field` constraints) | All write payloads | Negative bed counts, oversized strings, malformed numeric input |
| Restricted CORS | All endpoints | Arbitrary third-party websites making cross-origin requests against the API |
| Security headers | All responses | `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, `Strict-Transport-Security` (HSTS) |
| Audit logging | Every authenticated write | Every submit/delete/trigger is logged to Cloud Logging *and* BigQuery (`audit_log` table) with identity, IP, and details |
| Request Correlation | All responses | `X-Request-ID` header containing a UUID for tracking requests across logs |
| Secrets in Secret Manager | Deployment | `deploy.sh` stores the Gemini key, Maps key, and admin key in Secret Manager, not as plain Cloud Build substitutions |

---

## 🛠️ Testing & Quality Assurance

NARAD includes a full automated test suite to ensure the system is stable and safe for deployment.

- **CI/CD Pipeline Gate**: The Cloud Build pipeline (`cloudbuild.yaml`) runs `pytest` automatically. The build will **fail** and refuse to deploy if any tests fail.
- **Test Coverage**:
  - `test_schemas.py`: Validates all Pydantic models and field constraints (e.g., negative bed counts).
  - `test_security.py`: Ensures the fail-closed auth, rate limiters, and HSTS headers work properly.
  - `test_manual_reports.py`: Tests the hospital report caching (memory and BigQuery logic).
  - `test_rapids_engine.py`: Verifies the Monte Carlo simulations calculate risk bounds correctly.
  - `test_live_feeds.py`: Checks the exponential backoff, retry logic, and timeouts.
  - `test_parliament.py`: Ensures the ADK `Runner` cleans up sessions and respects execution timeouts to prevent memory leaks.
  - `test_api_integration.py`: End-to-end checks on REST APIs.

## 🛡️ Resilience & Incident Response

To prevent system-wide stalls from external API failures, NARAD uses:
- **Exponential Backoff**: Calls to Google Maps, OpenWeather, and OpenAQ automatically retry with backoff on failure before gracefully degrading to simulation mode.
- **LLM Timeouts**: The Gemini ADK parliament loop runs with a strict 20-second timeout per session.
- **Session Cleanup**: The ADK `Runner` aggressively cleans up old memory sessions to prevent Cloud Run out-of-memory errors.

**For full runbooks on handling production failures, see [INCIDENT_RESPONSE.md](INCIDENT_RESPONSE.md).**

**The access key model, honestly explained:** hospital staff/operators enter a shared admin key into the dashboard's "Access Key" field each browser session (stored in `sessionStorage` only — never written into the JS bundle, never in `localStorage`). `deploy.sh` generates this key randomly and prints it once during deployment.

**A shared key is a real limitation, not a solved problem.** Every operator uses the *same* credential — the audit log can record who *claimed* to submit a report (via the free-text "Reported By" field) but cannot cryptographically verify it was actually them. Before any real hospital staff are onboarded, this should be replaced with per-user authentication — **Firebase Authentication** or **Google Cloud Identity Platform** is the natural fit (same ecosystem, and it directly enables real per-user accountability in the audit trail).

**Also worth knowing:**
- The rate limiter is in-memory and per-instance — correct for a single Cloud Run instance, but doesn't synchronize across multiple replicas under real load. **Google Cloud Armor** in front of Cloud Run is the standard production pattern for this and doesn't have that limitation.
- None of this has been through a real security audit. See [Government Deployment Readiness](#-government-deployment-readiness-please-read-before-any-real-handoff) below.

---

## 🎬 Demo Script (for judges)

1. **Open the dashboard** — live Hyderabad metrics are already streaming (AQI, traffic, hospital capacity, safety, grid load). Point out the **● Live / ✎ Manual / ○ Sim** badge on each card — judges see immediately which data is real (Weather, AQI, Traffic once keys are set), which is real-but-human-sourced (Hospitals, once one self-reports), and which is honestly-labeled simulation (Safety, Economy — no public API exists for these anywhere).
2. **Ask NARAD a question** — type "Is it safe to travel through the city right now?" and switch the language toggle to తెలుగు (Telugu) mid-conversation. This is the moment to say: *"this isn't a generic chatbot bolted on — every answer is grounded in the live pulse and the parliament's actual decision, and it speaks the language most Hyderabad residents are actually comfortable in."*
3. **Submit a hospital status report** — open the "Hospital Status Reporting" form, pick a hospital, enter bed counts, hit submit. Watch the Hospital card's badge flip from **○ Sim** to **✎ Manual** instantly (no page refresh) — this is the moment to say: *"the moment a real hospital does this in production, that's genuinely real data, not a mock."*
4. **Click "Convene Session"** — watch all 5 agents deliberate in real time (~2-4 seconds). Expand any agent card to see its individual analysis, confidence, and vote.
5. **Point to the Dissent Log** — this is the differentiator. Show a judge where Health voted "escalate" but Economy voted "approve" — a real disagreement two city departments would have, made transparent instead of averaged away.
6. **Point to the Causal Chain** — traffic → emissions → AQI → predicted hospital surge. This is reasoning, not just data display.
7. **Run a Scenario Simulation** — pick "Festival Mass Gathering," run 1000+ Monte Carlo simulations, show the RAPIDS speedup multiplier and the resulting risk assessment.
8. **Run the Benchmark card** — show the live pandas vs. RAPIDS comparison chart at 1M records.
9. **Close on deployability** — this is a working Cloud Run service right now, not a local demo. Show the live URL, and hit `/api/diagnostics/llm`, `/api/diagnostics/traffic`, and `/api/diagnostics/bigquery` to show judges the system self-reports exactly which data sources are live vs. simulated, and that BigQuery is genuinely persisting history for PS2 — no black box anywhere.

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | Google Agent Development Kit (ADK) — `LlmAgent`, `Runner`, `InMemorySessionService` |
| LLM | Gemini 2.0 Flash |
| Natural language interface | "Ask NARAD" — Gemini + lightweight RAG (live pulse + BigQuery history), English/Hindi/Telugu |
| Acceleration | NVIDIA RAPIDS (cuDF, CuPy) with automatic CPU (pandas/NumPy) fallback |
| Persistent storage | BigQuery — pulse history + parliament decisions (PS2 data-layer requirement) |
| Backend | FastAPI, WebSockets, asyncio |
| Frontend | React 18, TypeScript, Vite, Tailwind CSS, Recharts |
| Deployment | Docker, Google Cloud Run, Cloud Build, Artifact Registry |
| Live data | OpenWeatherMap, OpenAQ, Google Maps Distance Matrix (with realistic pattern-based simulation fallback) |

---

## 📊 What's Real vs. Simulated (full transparency)

Being upfront about this — it's what a serious engineer would want to know:

- **Agent reasoning**: 100% real — actual Gemini 2.0 Flash calls via ADK, with real structured tool use and JSON-parsed voting.
- **Weather & Air Quality**: Real OpenWeatherMap/OpenAQ APIs when keys are provided; falls back to a physically-realistic simulation model (seasonal AQI patterns for Hyderabad) when keys are absent.
- **Traffic**: Real Google Maps Distance Matrix API (`departure_time=now`, live `duration_in_traffic`) across four major Hyderabad corridors (Gachibowli–Hitech City, Kukatpally–Secunderabad, Banjara Hills–Madhapur, LB Nagar–Abids) when `GOOGLE_MAPS_API_KEY` is set. Falls back to time-of-day-curve simulation otherwise.
- **RAPIDS acceleration**: On a machine with an NVIDIA GPU + cuDF installed, this runs *actual* GPU-accelerated Monte Carlo simulation and benchmarking. Without a GPU, it computes the real CPU (pandas/NumPy) baseline and reports a clearly-labeled *simulated* speedup (based on published RAPIDS benchmark ratios) — the code path (`GPU_AVAILABLE` flag) is identical, so deploying to a GPU-backed Cloud Run instance flips it to fully real with zero code changes.
- **Hospital capacity**: Three-tier data — (1) a live public HMIS API, if one ever becomes available, would slot in with zero changes elsewhere; (2) **hospital staff self-report their own status directly** through the dashboard's "Hospital Status Reporting" form — this is genuinely real data the moment it's submitted, no external vendor needed; (3) any hospitals that haven't self-reported yet are filled in with realistic simulation so the city-wide total stays meaningful. The dashboard shows exactly how many hospitals are self-reporting and what % coverage that represents.
- **Safety data**: Still simulated for now — same reasoning as hospitals (no public police/incident API exists), and the identical self-reporting pattern could be added for police stations with no architecture changes, just a parallel endpoint.
- **Economy data** (utility load, fuel price): Simulated — the only "real" options are unofficial scraper APIs with no reliability guarantee, which isn't a foundation worth building a civic tool on.

### Self-check your setup
NARAD shows exactly what's real directly in the dashboard — every metric card in the top row carries a small **● Live** or **○ Sim** badge, sourced from the backend's own `data_sources` field on each city pulse update. There's no need to trust a README claim; the running app tells you.

For a deeper check (e.g. before a demo), two diagnostic endpoints confirm each integration explicitly:

```bash
curl http://localhost:8080/api/diagnostics/llm
# → { "live_call_success": true/false, "error": "..." }

curl http://localhost:8080/api/diagnostics/traffic
# → { "mode": "live_google_maps" | "simulation", "error": "..." }
```
If either shows `false`/`"simulation"` with a non-null `error`, the message tells you exactly what to fix (usually: add the API key to `.env` and restart).

---

## 🏛️ Government Deployment Readiness (please read before any real handoff)

This section exists because NARAD was built with the intent of handing it to a real government body for real operational use. That's a fundamentally different bar than a hackathon demo, and it deserves a direct, specific answer rather than a vague "it's secure" claim.

**What this project genuinely has going for it, as of this build:**
- Fail-closed authentication on every write path (REST and WebSocket), tested end-to-end
- Input validation, rate limiting, restricted CORS, security headers, audit logging to BigQuery
- Honest data provenance (Live/Manual/Simulated badges) so no one is misled about what's real
- Secrets stored in Secret Manager, not in code or plain build substitutions

**What is genuinely still missing before this should run any real hospital, emergency, or government workflow:**

1. **A formal security audit (VAPT).** In India, government-facing IT systems generally require a Vulnerability Assessment and Penetration Testing engagement with a **CERT-In empanelled auditor** before go-live. This is a compliance requirement, not optional due diligence — nothing in this codebase substitutes for it.
2. **Real per-user authentication.** The current shared-admin-key model (see [Security](#-security) above) cannot attribute a write action to a specific verified human. Firebase Authentication / Cloud Identity Platform, with per-user accounts for every hospital and department, is required before real accountability is possible.
3. **A data protection / privacy review.** Hospital capacity data, even aggregated, may fall under data protection obligations depending on what's eventually connected (patient-level data is NOT currently handled, deliberately — but any future integration would need this reviewed by qualified counsel, not inferred from this README).
4. **Infrastructure hardening beyond a single Cloud Run service.** Production government infrastructure typically needs: multi-region failover, formal SLAs, a incident response runbook, monitoring/alerting (Cloud Monitoring + on-call), and a tested disaster recovery plan. None of that exists yet — this is one Cloud Run service with in-memory buffers as a fallback layer.
5. **Load testing at real scale.** This has been tested for correctness, not for concurrent load from thousands of real users or a genuine city-wide emergency spike in traffic.
6. **Legal/procurement sign-off.** Any real government deployment goes through a formal procurement, data-sharing agreement, and legal review process — a hackathon project can be the *technical basis* for a pilot proposal, but it isn't a substitute for that process.
7. **A real human-in-the-loop decision policy.** NARAD is decision *support* — every action_plan item and consensus statement should require explicit human sign-off before anything operational happens (dispatching resources, issuing public advisories). Nothing in this codebase should be wired to autonomously execute real-world actions without that gate, and it currently isn't — keep it that way.

**How I'd frame this to a government stakeholder, honestly:** *"This is a working technical prototype that demonstrates a genuinely novel decision-support architecture, with real security fundamentals in place. It is not yet a certified, audited production system, and shouldn't be represented as one. The right next step is a security audit and a pilot program with human oversight at every stage — not a direct production handoff."* That framing will land far better with any serious government IT evaluator than an overclaim would, and it's also just the accurate state of things.

---

## 🇮🇳 Why This Matters

Hyderabad has ~10 million residents. During a real AQI spike, a real hospital surge, and a real traffic incident happening simultaneously, five different government departments currently make decisions in isolation — Transport doesn't know what Health needs, Health doesn't know what Economy can absorb. NARAD doesn't replace human decision-makers; it gives them a fast, transparent, always-on first-pass analysis that surfaces disagreement instead of hiding it, so the humans in the room can make a better-informed call, faster.
