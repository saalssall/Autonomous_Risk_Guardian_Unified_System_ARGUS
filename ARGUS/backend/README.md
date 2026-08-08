# ARGUS backend

FastAPI + SQLite backend. Stores sensor readings and camera observations,
serves them back to the dashboard over REST (no WebSocket — the dashboard
polls).

## Setup

```
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set `ANTHROPIC_API_KEY` — only needed for
`POST /api/ai-explanation/{node_id}`; everything else works without it.

## Running

```
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Tables are created automatically on startup — you don't need to run
`seed.py` first, though it's there if you want example risk-assessment data
to demo against: `python3 seed.py`.

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/sensor-data` | ESP32 posts a sensor reading here |
| POST | `/api/image` | Camera pipeline posts a snapshot + detection flags here |
| POST | `/api/ai-explanation/{node_id}` | Calls Claude to explain the node's latest risk assessment in plain language. Needs `ANTHROPIC_API_KEY` set (see `.env.example`) |
| GET | `/api/nodes` | List all known nodes |
| GET | `/api/nodes/{node_id}` | One node's status/battery/location |
| GET | `/api/history/{node_id}` | Recent sensor readings for a node |
| GET | `/api/observations/{node_id}` | Recent camera observations for a node |
| GET | `/api/risk` | All risk assessments |
| GET | `/api/alerts` | HIGH/CRITICAL risk assessments only |
| GET | `/uploads/<filename>` | Serves uploaded snapshot images |

**No authentication on any endpoint.** Fine for a local demo on a trusted
network; add a check before this goes anywhere less controlled.
