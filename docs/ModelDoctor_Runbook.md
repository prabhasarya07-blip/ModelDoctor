# ModelDoctor Runbook (Hackathon)

This document explains how the project works, how to run it locally, and how to demo it.

## What ModelDoctor Does
ModelDoctor is a web app that diagnoses common silent-failure patterns in ML Python code.

It runs a 3-stage pipeline:
1. Layer 1 (Pattern Scanner): fast heuristics/regex rules that flag likely issues.
2. Layer 2 (AST Analyzer): parses code structure and infers ordering, complexity, and deployment readiness signals.
3. Layer 3 (Gemini): uses the evidence from layers 1 and 2 to produce a structured JSON report (issues + fixes + summary).

## Repo Layout
- `modeldoctor-frontend/`: Next.js 14 (TypeScript) UI + Monaco editor
- `modeldoctor-backend/`: FastAPI service that runs the pipeline and calls Gemini

## API Overview
Backend base URL: `http://localhost:8000`

- `GET /health`: simple health check
- `POST /api/quick-scan`: Layer-1 only (used for live markers in the editor)
- `POST /api/diagnose`: Full pipeline (Layer 1 + Layer 2 + Gemini + report builder)

### Request (diagnose)
```json
{
  "code": "import pandas as pd\n...",
  "language": "python",
  "context": {
    "dataset_size": "10000",
    "model_type": "classification",
    "framework": "sklearn"
  }
}
```

### Response (diagnose)
```json
{
  "health_score": 23,
  "issues": [
    {
      "id": "DL-001",
      "type": "DATA_LEAKAGE",
      "severity": "CRITICAL",
      "title": "StandardScaler applied before train/test split",
      "explanation": "...",
      "suggested_fix": "...",
      "location": { "line_start": 12, "line_end": 13 },
      "health_impact": -40
    }
  ],
  "summary": "Critical data leakage detected...",
  "diagnosis_time_ms": 7823,
  "model_used": "gemini-2.5-flash"
}
```

## How The Frontend Works
Main page: `modeldoctor-frontend/src/app/page.tsx`

- Monaco editor provides the code input.
- Live scan uses `POST /api/quick-scan` on a debounce timer.
- Full diagnosis uses `POST /api/diagnose` when the user clicks "Run Diagnosis" or presses Ctrl+Enter.

Key files:
- `modeldoctor-frontend/src/lib/api.ts`: API client
- `modeldoctor-frontend/src/hooks/useDiagnosis.ts`: diagnosis state machine
- `modeldoctor-frontend/src/hooks/useLiveScan.ts`: debounced live scanning

## How The Backend Works
Entry point: `modeldoctor-backend/main.py`

Request flow for `POST /api/diagnose`:
1. Validate and sanitize the incoming code payload.
2. Layer 1: `services/pattern_scanner.py` returns a list of suspicious patterns.
3. Layer 2: `services/ast_analyzer.py` returns AST insights and a formatted prompt section.
4. Layer 3: `services/gemini_service.py` calls Gemini and robustly parses/retries/repairs the JSON response.
5. `services/report_builder.py` recalculates and normalizes the final score, sorts issues, and builds the response.

## Local Setup (Windows)
Prereqs:
- Python 3.10+ (you have Python 3.12 on this machine)
- Node.js 18+
- A Gemini API key

### 1) Backend
```bash
cd modeldoctor-backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Environment variables:
- `GEMINI_API_KEY`: required for full diagnosis
- `CORS_ORIGINS`: comma-separated origins (default: `http://localhost:3000,http://127.0.0.1:3000`)
- `CORS_ALLOW_CREDENTIALS`: `true`/`false` (default: `true`)

### 2) Frontend
```bash
cd modeldoctor-frontend
npm install
npm run dev
```

Environment variables:
- `NEXT_PUBLIC_API_URL`: backend base URL (default is `http://localhost:8000`)

### 3) Open The App
Visit: `http://localhost:3000`

## Demo Script (3-5 Minutes)
1. Open the app and pick a sample code snippet with leakage.
2. Point out the live scan markers appearing in the editor.
3. Click "Run Diagnosis" to trigger the full pipeline.
4. Open the top CRITICAL finding, show the explanation and fix.
5. Apply the fix in the editor and rerun to show score improvement.

## Troubleshooting
- If the frontend can’t reach the backend:
  - Confirm backend is running on port 8000
  - Set `NEXT_PUBLIC_API_URL=http://localhost:8000`
- If Gemini fails:
  - Confirm `GEMINI_API_KEY` is set in backend environment
  - Try a shorter code snippet (backend enforces a max code length)

