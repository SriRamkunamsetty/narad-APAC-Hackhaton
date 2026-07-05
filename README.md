# 🏛️ NARAD
### Neural Agentic Real-time Advisor for Decisions

**A live AI parliament for Indian smart cities — 5 autonomous Google ADK agents that independently analyze real-time city data, debate, vote, and reach transparent consensus decisions, accelerated by NVIDIA RAPIDS for instant what-if scenario simulation.**

Built for the Google Cloud × NVIDIA Hackathon 2026 — addressing:
- **PS1: AI for Better Living and Smarter Communities**
- **PS2: Data Intelligence + Acceleration**

---

## 🎯 What Makes NARAD Different

Most "smart city AI" submissions are a chatbot wrapped around a dashboard. NARAD is structurally different:

1. **Agent Parliament, not a single chatbot.** Five specialized ADK agents (Transport, Health, Environment, Economy, Safety) independently analyze the same live data and **vote**. When they disagree, NARAD logs the disagreement instead of hiding it — a transparent "dissent log" that shows exactly where city departments would clash in the real world.

2. **Causal reasoning, not just correlation.** NARAD doesn't just report "AQI is high." It traces the causal chain: traffic congestion → vehicular emissions → AQI spike → predicted ER visit surge within 6 hours — connecting five domains that are normally siloed.

3. **NVIDIA RAPIDS scenario simulation.** Ask "what if we close NH-44 for 3 hours?" and NARAD runs 1,000+ Monte Carlo simulations across traffic, health, safety, and environment impact — in milliseconds on GPU vs. minutes on CPU. This is a genuinely different decision-making capability, not just a speed bump.

4. **Real-time, not batch.** A live WebSocket feed streams city conditions, alerts, and parliament sessions to the dashboard continuously — this is built to run as a 24/7 city operations tool, not a one-shot demo.

5. **Honest data provenance, with a real path to zero simulation.** Every metric on the dashboard is labeled **● Live**, **✎ Manual**, or **○ Sim** — no hidden mock data. For sectors with no public API (hospital capacity, in India's case), NARAD doesn't just fake it: hospital staff can self-report their own status directly, and that becomes genuinely real data instantly, blended transparently with simulation only for hospitals that haven't reported yet. The moment a real government API exists for any domain, or more hospitals opt in, the "real" percentage grows with zero architecture changes — this is designed to converge toward 100% real data over time, not stay a permanent demo.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     REACT DASHBOARD (Vite + Tailwind)            │
│   Live Metrics · Agent Parliament UI · Scenario Simulator ·      │
│   RAPIDS Benchmark · Real-time Trends · Alert Feed               │
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
│  └─────────────┘  └──────────────────┘  └──────────────────────┘ │
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
│   ├── agents/
│   │   ├── specialized_agents.py  # The 5 ADK LlmAgent definitions + tools
│   │   └── parliament.py          # Orchestrator: run agents, synthesize consensus
│   ├── data/
│   │   ├── live_feeds.py          # Real API calls (OpenWeather/OpenAQ/Google Maps) + simulation
│   │   └── rapids_engine.py       # NVIDIA RAPIDS/cuDF Monte Carlo + benchmarking
│   ├── models/
│   │   └── schemas.py             # Pydantic schemas for all data structures
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx                  # Main dashboard shell
│   │   ├── components/              # StatusBar, CityPulseGrid, AgentParliament,
│   │   │                            # ScenarioSimulator, BenchmarkCard, TrendChart
│   │   ├── hooks/useNaradSocket.ts  # WebSocket connection with auto-reconnect
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

### 3. Setup
```bash
git clone <your-repo>
cd narad
chmod +x setup.sh && ./setup.sh
```

Edit `.env` and paste your keys:
```
GEMINI_API_KEY=AIzaSy...your_gemini_key_here
GOOGLE_MAPS_API_KEY=AIzaSy...your_maps_key_here   # optional
```

### 4. Run
```bash
# Terminal 1 — backend
python3 -m uvicorn backend.main:app --reload --port 8080

# Terminal 2 — frontend
cd frontend && npm run dev
```

Open **http://localhost:5173** — you'll see live Hyderabad city data streaming in, and the Agent Parliament will run its first session within ~60 seconds automatically (or click "Convene Session" to trigger manually).

> **No API key?** The system runs in graceful fallback mode — rule-based agent decisions instead of Gemini reasoning — so it never crashes, but you won't see the "wow" multi-agent reasoning. Get the key, it's free and takes 2 minutes.

### 5. Verify what's actually live
```bash
curl http://localhost:8080/api/diagnostics/llm
curl http://localhost:8080/api/diagnostics/traffic
```
Both should report success once your keys are in place — see [What's Real vs. Simulated](#-whats-real-vs-simulated-full-transparency) below for exactly what each controls.

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

## 🎬 Demo Script (for judges)

1. **Open the dashboard** — live Hyderabad metrics are already streaming (AQI, traffic, hospital capacity, safety, grid load). Point out the **● Live / ✎ Manual / ○ Sim** badge on each card — judges see immediately which data is real (Weather, AQI, Traffic once keys are set), which is real-but-human-sourced (Hospitals, once one self-reports), and which is honestly-labeled simulation (Safety, Economy — no public API exists for these anywhere).
2. **Submit a hospital status report** — open the "Hospital Status Reporting" form, pick a hospital, enter bed counts, hit submit. Watch the Hospital card's badge flip from **○ Sim** to **✎ Manual** instantly (no page refresh) — this is the moment to say: *"the moment a real hospital does this in production, that's genuinely real data, not a mock."*
3. **Click "Convene Session"** — watch all 5 agents deliberate in real time (~2-4 seconds). Expand any agent card to see its individual analysis, confidence, and vote.
4. **Point to the Dissent Log** — this is the differentiator. Show a judge where Health voted "escalate" but Economy voted "approve" — a real disagreement two city departments would have, made transparent instead of averaged away.
5. **Point to the Causal Chain** — traffic → emissions → AQI → predicted hospital surge. This is reasoning, not just data display.
6. **Run a Scenario Simulation** — pick "Festival Mass Gathering," run 1000+ Monte Carlo simulations, show the RAPIDS speedup multiplier and the resulting risk assessment.
7. **Run the Benchmark card** — show the live pandas vs. RAPIDS comparison chart at 1M records.
8. **Close on deployability** — this is a working Cloud Run service right now, not a local demo. Show the live URL, and optionally hit `/api/diagnostics/llm` and `/api/diagnostics/traffic` to show judges the system self-reports exactly which data sources are live vs. simulated — no black box.

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| Agent orchestration | Google Agent Development Kit (ADK) — `LlmAgent`, `Runner`, `InMemorySessionService` |
| LLM | Gemini 2.0 Flash |
| Acceleration | NVIDIA RAPIDS (cuDF, CuPy) with automatic CPU (pandas/NumPy) fallback |
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

## 🇮🇳 Why This Matters

Hyderabad has ~10 million residents. During a real AQI spike, a real hospital surge, and a real traffic incident happening simultaneously, five different government departments currently make decisions in isolation — Transport doesn't know what Health needs, Health doesn't know what Economy can absorb. NARAD doesn't replace human decision-makers; it gives them a fast, transparent, always-on first-pass analysis that surfaces disagreement instead of hiding it, so the humans in the room can make a better-informed call, faster.
