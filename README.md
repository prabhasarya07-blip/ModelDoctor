# ModelDoctor 🩺

### "The MRI for your ML Pipeline"

**Team ASTROID** — Prabhas N & Poornima Bhat · Open Innovation Track

> "94% Accuracy. 0% Trustworthy."

[![Live App](https://img.shields.io/badge/Live%20App-Open%20ModelDoctor-00DEB4?style=flat-square&logo=vercel)](https://modeldoctor-frontend.vercel.app)
[![Health](https://img.shields.io/badge/API-v2.0.0-4285F4?style=flat-square)](https://modeldoctor-frontend.vercel.app/api/health)

---

## 📋 About

**ModelDoctor** is a diagnostic tool for Machine Learning code. It finds *silent failures* — bugs that never crash and never raise an exception, but quietly corrupt your results until the model is in production and your metrics are a lie.

The core problem it attacks: a model reporting 94% accuracy is meaningless if the scaler was fitted on the full dataset before the train/test split. That number is inflated by test-set leakage, and nothing in a notebook will tell you. ModelDoctor reads the pipeline, reconstructs the execution order, and reports which findings are costing you credibility.

### 🔗 Live URL

**https://modeldoctor-frontend.vercel.app**

| Resource | Link |
|---|---|
| **Live application** | https://modeldoctor-frontend.vercel.app |
| API health check | https://modeldoctor-frontend.vercel.app/api/health |
| Source repository | https://github.com/prabhasarya07-blip/ModelDoctor |
| Frontend project (Vercel) | `modeldoctor-frontend` · Node 24.x · Production |

Deployed on Vercel as a single Next.js 14 app — the analysis engine runs server-side, so no API key, no Python process, and no external model call is needed to use it. Paste code, press **Run Diagnosis** (or `Ctrl+Enter`), and get a scored report.

### Who it's for

- **Data scientists and ML engineers** reviewing a pipeline before it ships
- **Reviewers** who need a second opinion on someone else's notebook
- **Teams** that want a repeatable pre-merge checklist instead of code review by memory

### How it works (V2)

The original prototype called Gemini 2.5 Flash for deep reasoning. **V2 is a deterministic Rules Engine** ported to TypeScript and running in Next.js Route Handlers. The same findings now come back in **single-digit milliseconds** with no external API, no rate limit, and no network dependency — which is what makes it deployable and free to run.

| Layer | Component | File | Role |
|---|---|---|---|
| 1 | Parser | `src/lib/server/parser.ts` | AST-based call extraction in source order |
| 2 | Pipeline Analyzer | `src/lib/server/pipeline-analyzer.ts` | Stages, complexity, GPU waste, code type |
| 3 | Rules Engine | `src/lib/server/rules.ts` | Leakage, overfitting, best-practice rules |
| 4 | Scoring | `rules.ts → calculateScore()` | Weighted health score from issue impact |
| 5 | Report | `engine.ts → runDiagnosis()` | Assembles response, timings, stages |
| — | Pattern Scanner | `src/lib/server/pattern-scanner.ts` | 37 regex heuristics for live scan |

The **Pattern Scanner** also runs standalone at `/api/quick-scan` to power live feedback while you type, debounced and cancellable via `AbortSignal`.

---

## 🩻 What it diagnoses

37 detection patterns across 8 categories, mapped to **8 CRITICAL**, **11 HIGH**, **13 MEDIUM**, and **5 LOW** severity findings.

### 🔴 Data leakage (`DL` × 7) — the highest-value catches

Fitted transformers that leak test-set statistics into training. Each pattern only fires when the match appears **before** the train/test split.

| Pattern | Detects |
|---|---|
| `DL-SCALE-BEFORE-SPLIT` | `StandardScaler` / `MinMaxScaler` / `RobustScaler` fitted on the full dataset |
| `DL-ENCODE-BEFORE-SPLIT` | `LabelEncoder` / `OneHotEncoder` / `get_dummies` applied before splitting |
| `DL-IMPUTE-BEFORE-SPLIT` | `SimpleImputer` / `fillna` / `interpolate` leaking test distribution |
| `DL-PCA-BEFORE-SPLIT` | `PCA` / `TruncatedSVD` / `TSNE` / `UMAP` fitted before splitting |
| `DL-SMOTE-BEFORE-SPLIT` | `SMOTE` / `ADASYN` generating test-like training samples |
| `DL-FEATURE-SELECT-BEFORE-SPLIT` | `SelectKBest` / `chi2` / `mutual_info_classif` using the target early |
| `DL-TFIDF-BEFORE-SPLIT` | `TfidfVectorizer` / `CountVectorizer` leaking vocabulary and IDF weights |

### 🔴 Train/test split (`TS` × 6)

| Pattern | Detects |
|---|---|
| `TS-NO-SPLIT` | No split or cross-validation found anywhere |
| `TS-SHUFFLE-TIMESERIES` | `shuffle=True` on possibly temporal data |
| `TS-NO-RANDOM-STATE` | Non-reproducible splits |
| `TS-NO-STRATIFY` | Classification split without `stratify=` |
| `TS-TINY-TEST-SIZE` | Test set too small to be meaningful |
| `TS-HUGE-TEST-SIZE` | Test set above 50% of the data |

### 🟠 Overfitting risk (`OF` × 5)

`OF-NO-REGULARIZATION` · `OF-NO-VALIDATION` · `OF-DEEP-NO-DROPOUT` · `OF-TREE-NO-DEPTH-LIMIT` · `OF-HIGH-EPOCHS-NO-EARLYSTOP`

### 🔴 Feature misuse (`FM` × 3)

`FM-TARGET-IN-FEATURES` (CRITICAL) · `FM-ID-IN-FEATURES` · `FM-FUTURE-FEATURE`

### 🟠 Preprocessing errors (`PE` × 4)

`PE-NO-NULL-HANDLING` · `PE-FIT-TRANSFORM-ON-TEST` (CRITICAL) · `PE-LABEL-ENCODE-ORDINAL` · `PE-NO-SCALING`

### 🟡 Gradient instability (`GI` × 5)

`GI-HIGH-LEARNING-RATE` · `GI-TINY-LEARNING-RATE` · `GI-NO-GRADIENT-CLIP` · `GI-NO-BATCHNORM` · `GI-EVAL-MODE-MISSING`

### 🟡 Evaluation mistakes (`EV` × 4)

`EV-ACCURACY-IMBALANCED` · `EV-TRAIN-SCORE-ONLY` · `EV-NO-METRICS` · `EV-R2-NEGATIVE-POSSIBLE`

### 🟡 Reproducibility (`RP` × 3)

`RP-NO-RANDOM-SEED` · `RP-GPU-NO-DEVICE` · `RP-PANDAS-INPLACE-CHAIN`

---

## 🚀 Quick Start

### Prerequisites

- **Node.js 18+** — that is the only hard requirement for the deployed version
- No API key. No Python. No Docker.

### Run the app locally

```bash
cd modeldoctor-frontend
npm install
npm run dev:next
```

Open **http://localhost:3000**. A sample buggy pipeline is pre-loaded — click **Run Diagnosis** or press `Ctrl+Enter`.

> `npm install` uses `legacy-peer-deps=true` (pinned in `.npmrc`) because the dependency tree contains peer ranges npm's default resolver cannot dedupe.

### Other commands

```bash
npm run build      # production build
npm run start      # serve the production build
npm run lint       # eslint
npm run dev        # Next.js + FastAPI backend together (legacy dev workflow)
```

---

## 🏗 Project Structure

```
ModelDoctor/
├── modeldoctor-frontend/              # ← the deployed app (Next.js 14 + TS)
│   ├── src/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   ├── diagnose/route.ts  # POST — full 5-layer diagnosis
│   │   │   │   ├── quick-scan/route.ts# POST — Layer 1 only, live scan
│   │   │   │   └── health/route.ts    # GET  — service info
│   │   │   ├── layout.tsx
│   │   │   └── page.tsx               # single-page application
│   │   ├── components/
│   │   │   ├── Diagnosis/             # HealthScore, IssueCard, SeverityBadge, report
│   │   │   ├── Editor/                # Monaco editor + sample loader
│   │   │   ├── Layout/                # Header, NeuralBackground, MLSignalsShowcase
│   │   │   └── UI/                    # DiagnoseButton, LoadingState, ErrorState
│   │   ├── hooks/
│   │   │   ├── useDiagnosis.ts        # diagnosis state machine
│   │   │   └── useLiveScan.ts         # debounced, cancellable quick scan
│   │   ├── lib/
│   │   │   ├── server/                # engine, parser, pipeline-analyzer,
│   │   │   │                          # pattern-scanner, rules
│   │   │   ├── api.ts                 # fetch client
│   │   │   ├── types.ts               # shared interfaces
│   │   │   ├── sample-codes.ts        # 3 pre-built buggy pipelines
│   │   │   └── report-export.ts       # shareable report snapshots
│   │   └── ...
│   ├── scripts/parity-check.mjs        # TS vs FastAPI output parity harness
│   ├── vercel.json                     # function timeouts
│   └── package.json
│
├── modeldoctor-backend/                # original Python prototype (optional)
│   ├── main.py, routers/, services/,
│   │   rules/, models/, prompts/
│   └── tests/                          # test_engine.py, test_scoring.py
│
├── docs/                               # runbook + 20-min talk script (MD + PDF)
└── scripts/                            # PDF generation + cleanup helpers
```

---

## 🔌 API

All endpoints are same-origin under `/api`. Maximum input length is **50,000 characters**, minimum **10**.

### `POST /api/diagnose`

Runs the full 5-layer pipeline. `maxDuration` 30s.

```bash
curl -X POST https://modeldoctor-frontend.vercel.app/api/diagnose \
  -H "Content-Type: application/json" \
  -d '{"code":"import pandas as pd\nfrom sklearn.preprocessing import StandardScaler\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.linear_model import Ridge\ndf = pd.read_csv(\"data.csv\")\nscaler = StandardScaler()\ndf_scaled = scaler.fit_transform(df)\ny = df[\"target\"]\nX = df.drop(\"target\", axis=1)\nX_train, X_test, y_train, y_test = train_test_split(df_scaled, y, test_size=0.2, random_state=42)\nmodel = Ridge(alpha=1.0)\nmodel.fit(X_train, y_train)\nprint(model.score(X_test, y_test))","language":"python"}'
```

This snippet has `StandardScaler` fitted on the full dataset before the split. The response below is the real output.

**Request**

```jsonc
{
  "code": "string, required, 10–50000 chars",
  "language": "string, e.g. \"python\"",
  "context": {                    // optional
    "dataset_size": "10000",
    "model_type": "classification",
    "framework": "sklearn"
  }
}
```

**Response** — verified against the live deployment:

```jsonc
{
  "health_score": 40,                  // 0–100
  "issues": [
    {
      "id": "DL-001",
      "type": "DATA_LEAKAGE",
      "severity": "CRITICAL",          // CRITICAL | HIGH | MEDIUM | LOW
      "title": "Data Leakage: Preprocessing before Train/Test Split",
      "explanation": "Scaling or imputing the entire dataset before splitting causes data leakage. Test set statistics influence the training data.",
      "suggested_fix": "Move the preprocessing step AFTER train_test_split. Fit the scaler on X_train only, then transform X_train and X_test separately.",
      "location": { "line_start": 6, "line_end": 6, "code_snippet": null },
      "health_impact": 30,             // points deducted from health_score
      "estimated_quality_impact": "Severely overestimated real-world performance.",
      "refactored_code": "X_train, X_test, y_train, y_test = train_test_split(X, y)\nscaler = StandardScaler()\nX_train = scaler.fit_transform(X_train)\nX_test = scaler.transform(X_test)"
    },
    {
      "id": "BP-002",
      "type": "DATA_QUALITY",
      "severity": "MEDIUM",
      "title": "Possible Missing Value Mishandling",
      "explanation": "No explicit missing value handling (imputation or dropping) was detected.",
      "suggested_fix": "Check your dataset for NaNs, and use SimpleImputer or df.fillna() if present.",
      "location": null,              // null when the finding is file-wide
      "health_impact": 5,
      "estimated_quality_impact": "Model training might crash, or errors will silently propagate."
    }
  ],
  "pipeline_stages": [
    { "name": "preprocess", "line": 6, "details": { "method": "StandardScaler" } },
    { "name": "preprocess", "line": 7, "details": { "method": "fit_transform" } },
    { "name": "split",      "line": 10, "details": { "method": "train_test_split" } },
    { "name": "train",      "line": 12, "details": { "method": "fit" } },
    { "name": "evaluate",   "line": 13, "details": { "method": "score" } }
  ],
  "model_complexity_score": 1,         // 1–10
  "gpu_waste_risk": "Low",             // Low | High (Deep network, no GPU device mapped)
  "summary": "Analyzed 8 ML operations logic map. Found 2 pipeline flaws. Detected ML Stage: Research/Experimentation.",
  "diagnosis_time_ms": 2,              // varies per request; typically 0–3ms
  "model_used": "ModelDoctor Rules Engine V2"
}
```

Errors return `{ "detail": "...", "error_type": "ValidationError" | "InternalError" }` with status `400` or `500`.

### `POST /api/quick-scan`

Layer 1 only — the 37 pattern scanner. Backs live editor feedback. Never throws: malformed input returns an empty flag list. `maxDuration` 10s.

**Request**

```jsonc
{ "code": "...", "language": "python" }
```

**Response**

```jsonc
{
  "flags": [
    {
      "pattern_id": "DL-SCALE-BEFORE-SPLIT",
      "pattern_name": "Scaler fitted before train/test split",
      "severity": "CRITICAL",
      "description": "StandardScaler/MinMaxScaler/RobustScaler fitted on full dataset before split. Test data statistics leak into training.",
      "line_number": 6,
      "matched_code": "df_scaled = s.fit_transform(df)",
      "confidence": 0.9
    }
  ],
  "scan_time_ms": 3.69
}
```

### `GET /api/health`

```jsonc
// https://modeldoctor-frontend.vercel.app/api/health
{
  "name": "ModelDoctor API",
  "version": "2.0.0",
  "tagline": "The MRI for your ML pipeline.",
  "team": "ASTROID — Prabhas N & Poornima Bhat",
  "architecture": "3-Layer Pipeline: Pattern Scanner → Data Analyzer → Rules Engine",
  "status": "healthy",
  "engine": "ModelDoctor Rules Engine V2",
  "pattern_count": 37
}
```

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 14 (App Router, Route Handlers) |
| Language | TypeScript 5.7 |
| Runtime | Node.js 24.x on Vercel |
| Styling | Tailwind CSS 3.4 + Framer Motion 11 |
| Code editor | Monaco Editor (`@monaco-editor/react`) |
| 3D visuals | React Three Fiber + drei + three.js |
| Icons | Lucide React |
| Analysis | Custom deterministic rules engine — no LLM call required |
| Hosting | Vercel |
| Legacy backend | FastAPI + Gemini 2.5 Flash (Python prototype, kept for parity testing) |

---

## 🧪 Testing & Parity

The TypeScript engine is a port of the Python engine. `scripts/parity-check.mjs` asserts both implementations return identical findings for every built-in sample snippet, so behaviour cannot silently drift between them.

```bash
# Terminal 1 — Next.js route handlers
cd modeldoctor-frontend && npm run build && npx next start -p 3111

# Terminal 2 — FastAPI backend
cd modeldoctor-backend && python -m uvicorn main:app --port 8123

# Terminal 3
cd modeldoctor-frontend && node scripts/parity-check.mjs
```

Python unit tests:

```bash
cd modeldoctor-backend && python run_tests.py
```

---

## 🔐 Security & Input Handling

- Input validated and trimmed server-side: minimum 10, maximum 50,000 characters
- `POST /api/diagnose` returns `400` with a clear message for malformed JSON, missing `code`, or oversized input
- `/api/quick-scan` is fail-safe by design — any error yields an empty flag list rather than a broken editor
- Analysis runs entirely server-side; detection patterns are never shipped in the client bundle
- No API keys in the deployed app — the rules engine needs no credentials
- No analytics, cookies, or user data collected

---

## 🧭 Configuration

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | *(empty)* | Point the client at an external backend. Empty = same-origin `/api/*` Route Handlers (the default for local dev and Vercel). |

`vercel.json` pins function timeouts: 30s for `/api/diagnose`, 10s for `/api/quick-scan`.

---

## 🗺 Roadmap

- Language coverage beyond Python (R, SQL, PySpark)
- A CLI for pre-commit hooks and CI gating
- A shared ruleset so findings stay consistent across editor, CI, and dashboard
- Severity-weighted diffing to catch pipelines that got *worse* between commits

---

## 📄 Documentation

- Runbook (Markdown) — [`docs/ModelDoctor_Runbook.md`](docs/ModelDoctor_Runbook.md)
- Runbook (PDF) — [`docs/ModelDoctor_Runbook.pdf`](docs/ModelDoctor_Runbook.pdf)
- 20-minute talk script (Markdown) — [`docs/ModelDoctor_20min_Script.md`](docs/ModelDoctor_20min_Script.md)
- 20-minute talk script (PDF) — [`docs/ModelDoctor_20min_Script.pdf`](docs/ModelDoctor_20min_Script.pdf)

Regenerate the PDFs:

```bash
python scripts/generate_runbook_pdf.py
python scripts/generate_runbook_pdf.py --in docs/ModelDoctor_20min_Script.md --out docs/ModelDoctor_20min_Script.pdf
```

---

## 📄 License

No license file is published yet. Until one is added, all rights are reserved — treat this repository as unlicensed and do not redistribute it.

---

<div align="center">

### 🩺 *Trustworthy ML, from the start.*

**[Try ModelDoctor →](https://modeldoctor-frontend.vercel.app)**

</div>