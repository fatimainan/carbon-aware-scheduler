# Carbon-Aware Scheduler — FastAPI bridge

This small FastAPI service exposes your scheduler's execution log to the React
dashboard. It does not replace `main.py` or `worker.py` — it runs alongside
them and reads the same `logs/execution_log.json` file your `Executor` writes.

## 1. Install

From your `carbon_aware_scheduler/` project root:

```bash
pip install fastapi "uvicorn[standard]"
```

(Or add `fastapi` and `uvicorn[standard]` to `requirements.txt`.)

## 2. Place the file

Copy `main.py` from this folder into your project as `python-backend/main.py`
(or any path that can `import` your existing scheduler code — the file does
not depend on it directly, so anywhere works).

## 3. Run it

From your scheduler project root:

```bash
uvicorn python-backend.main:app --reload --host 0.0.0.0 --port 8000
```

Now your two services run side-by-side:

| Process | Command | Purpose |
| --- | --- | --- |
| Scheduler | `python main.py --sim --cycles 10` | Writes `logs/execution_log.json` |
| Worker | `python worker.py` | Drains delayed jobs from Redis |
| **API** | `uvicorn python-backend.main:app --port 8000` | **Reads the log; serves the dashboard** |

Verify:

```bash
curl http://localhost:8000/api/dashboard
```

You should see `{"config": {...}, "cycles": [...], "generatedAt": "..."}`.

## 4. Point the dashboard at it

In `artifacts/carbon-dashboard/`, set the env var (a `.env.local` file in
that directory works in dev):

```env
VITE_API_BASE_URL=http://localhost:8000
```

Then restart the dashboard. It polls `/api/dashboard` every 5 seconds and
will show new cycles as your scheduler emits them.

## 5. CORS in production

When you deploy the dashboard, set `ALLOWED_ORIGINS` on the FastAPI service
to your dashboard's URL:

```bash
ALLOWED_ORIGINS="https://your-dashboard.replit.app" \
  uvicorn python-backend.main:app --host 0.0.0.0 --port 8000
```

## API contract

```jsonc
GET /api/dashboard
{
  "config": {
    "threshold": 200,
    "delaySeconds": 30,
    "zone": "DE",
    "actionName": "data_processor"
  },
  "cycles": [
    {
      "cycle": 1,
      "timestampOffsetMin": 0,
      "carbonIntensity": 85,
      "decision": "execute",
      "executionStatus": "executed",
      "executionDurationMs": 0.31,
      "scenario": "A"
    }
    // ... one per cycle ...
  ],
  "generatedAt": "2026-04-29T19:10:00+00:00"
}
```

If you ever change the executor's log format, the only file you need to
update is `_to_cycles()` inside `main.py`.
