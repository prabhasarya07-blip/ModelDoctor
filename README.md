# ModelDoctor 🩺
### "The MRI for your ML Pipeline"
**Team ASTROID** — Prabhas N  | Open Innovation Track

> "94% Accuracy. 0% Trustworthy."

---

## What is ModelDoctor?

ModelDoctor is an AI-powered diagnostic system that catches **silent failures** in Machine Learning code — bugs that don't crash but silently corrupt your model's validity.

**In ~8 seconds**, it scans your Python ML code through a two-layer pipeline:
1. **Pattern Scanner** — Static heuristic analysis (<10ms)
2. **Gemini 2.5 Flash** — Deep AI reasoning (~4.5s)
3. **Report Assembly** — Health score + severity-sorted issues

### What it diagnoses:
- 🔴 **Data Leakage** — preprocessing before train/test split
- 🔴 **Train/Test Split Errors** — random shuffle on time-series
- 🟠 **Overfitting Risk** — no regularization, no validation
- 🟠 **Feature Misuse** — target leakage, future-looking features
- 🟡 **Gradient Instability** — exploding/vanishing gradients
- 🟡 **Preprocessing Errors** — missing value handling issues

---

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- A [Gemini API key](https://aistudio.google.com/apikey)

### 1. Backend (FastAPI)

```bash
cd modeldoctor-backend

# Add your Gemini API key
# Edit .env file and replace "your_gemini_api_key_here" with your actual key

# Install dependencies
pip install -r requirements.txt
```

### 2. Frontend (Next.js)

```bash
cd modeldoctor-frontend

# Install dependencies
npm install

### 3. Open the app
Visit **http://localhost:3000** — the demo code is pre-loaded!

Click **Run Diagnosis** (or `Ctrl+Enter`) to see it in action.

---

## Project Structure

```
ModelDoctor/
├── modeldoctor-backend/
│   ├── main.py                  # FastAPI entry point
│   ├── routers/
│   │   └── diagnose.py          # POST /api/diagnose endpoint
│   ├── services/
│   │   ├── pattern_scanner.py   # Layer 1: Static analysis
│   │   ├── gemini_service.py    # Layer 2: LLM reasoning
│   │   └── report_builder.py    # Layer 3: Report assembly
│   ├── models/
│   │   └── schemas.py           # Pydantic models
│   ├── prompts/
│   │   └── diagnosis_prompt.py  # Gemini prompt engineering
│   ├── utils/
│   │   └── scoring.py           # Health score calculation
│   ├── requirements.txt
│   └── .env
│
└── modeldoctor-frontend/
    ├── src/
    │   ├── app/
    │   │   ├── layout.tsx       # Root layout
    │   │   ├── page.tsx         # Main application page
    │   │   └── globals.css      # Global styles + design system
    │   ├── components/
    │   │   ├── Editor/          # Monaco code editor
    │   │   ├── Diagnosis/       # Health score, issue cards, report
    │   │   ├── UI/              # Buttons, loading, errors
    │   │   └── Layout/          # Header, neural background
    │   ├── hooks/
    │   │   └── useDiagnosis.ts  # Diagnosis state management
    │   └── lib/
    │       ├── api.ts           # Backend API client
    │       ├── types.ts         # TypeScript interfaces
    │       └── sample-codes.ts  # 3 pre-built buggy examples
    └── package.json
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Framer Motion |
| Code Editor | Monaco Editor (VS Code's editor) |
| Backend | FastAPI (Python) |
| AI Engine | Gemini 2.5 Flash |
| Design | Glassmorphism, JetBrains Mono, animated SVG health ring |

---

## API

### `POST /api/diagnose`

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

**Response:**
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

---

*"Trustworthy ML, from the start."*

---

## Documentation
- Runbook (Markdown): `docs/ModelDoctor_Runbook.md`
- Runbook (PDF): `docs/ModelDoctor_Runbook.pdf`
- 20-min Script (Markdown): `docs/ModelDoctor_20min_Script.md`
- 20-min Script (PDF): `docs/ModelDoctor_20min_Script.pdf`

To regenerate the PDF:
```bash
python scripts/generate_runbook_pdf.py
```

To generate the 20-min talk PDF:
```bash
python scripts/generate_runbook_pdf.py --in docs/ModelDoctor_20min_Script.md --out docs/ModelDoctor_20min_Script.pdf
```
