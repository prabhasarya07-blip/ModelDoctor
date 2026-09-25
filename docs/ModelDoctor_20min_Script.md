# ModelDoctor: 20-Minute Hackathon Script (Speaker Notes)

Audience: hackathon judges + engineers + product folks  
Goal: make the problem vivid, prove the solution works, and show why this becomes a real product.

## 0:00 - 1:30 | Hook: "Accuracy Is Not Trust"
Say:
- "If I tell you my model is 94% accurate, you might clap. But if that 94% comes from leakage, it is not a model, it is a lie."
- "Most ML failures do not crash. They silently corrupt results and get discovered in production or during an audit."
- "ModelDoctor is the MRI for ML code: it tells you what is wrong, why it matters, and how to fix it, before you waste GPU time."

Show:
- The app landing screen and editor (do not run anything yet).

Transition:
- "Let me show what breaks in the real world and why existing tools do not catch it in time."

## 1:30 - 4:00 | The Real Problem (With Examples)
Say (keep it concrete):
- "In ML, a pipeline can be technically correct Python and still be scientifically invalid."
- "Here are common silent failures:"
- "1) Data leakage: scaling/encoding/imputation before train-test split."
- "2) Time-series split mistakes: random shuffle on ordered data."
- "3) Evaluation mistakes: reporting training accuracy, leakage via target features, wrong metric."
- "4) Deployment readiness gaps: no serialization, missing versioning/reproducibility, weak logging."

Why it hurts:
- "You waste compute, publish wrong results, and ship models that cannot be reproduced."
- "The cost is not just money, it is trust: your team and stakeholders stop believing your metrics."

## 4:00 - 6:00 | Why Existing Tools Fall Short
Say:
- "Linters are great, but they check style, not ML correctness."
- "Unit tests rarely exist for ML scripts, and even when they do, they don’t validate leakage or evaluation hygiene."
- "Generic AI assistants can suggest code, but they usually do not run structured, repeatable deployment checks."
- "We need a system that understands ML pipeline structure and produces a clinical report: prioritized, actionable, and explainable."

Transition:
- "Now I’ll show ModelDoctor doing exactly that."

## 6:00 - 10:00 | Live Demo: From Bug to Fix to Score Jump
Setup:
- Pick a pre-loaded sample that has leakage and missing deployment pieces.

Say (before clicking):
- "The editor has a live scanner that flags suspicious patterns while you type. This is Layer 1 only, so it is fast."

Do:
1. Point to live scan markers in the editor.
2. Click "Run Diagnosis" (or Ctrl+Enter).

Say (while scanning):
- "Now we run the full pipeline: heuristics + AST structure + Gemini reasoning."
- "The key is we combine evidence: what it looks like and what it actually does."

After results:
- "Here is the health score."
- "Here are issues ranked by severity. Let’s open the first CRITICAL one."

Explain one issue deeply (example: scaler before split):
- What it is: "The scaler is fitted on full X, which leaks test distribution."
- Why it matters: "Your test score is inflated and not reproducible."
- Fix: "Split first, fit scaler on train, transform both."

Do:
- Apply the suggested fix in the editor (small change).
- Re-run diagnosis.

Say:
- "The score improves because we removed a root-cause validity bug, not because we changed formatting."
- "This is the point: fast feedback that moves code toward production readiness."

## 10:00 - 14:00 | Under The Hood: The 3-Layer Architecture
Say:
- "ModelDoctor is not just an LLM prompt. It is a pipeline with guardrails."

### Layer 1: Pattern Scanner (Fast Heuristics)
Say:
- "We scan for known ML anti-patterns with lightweight rules."
- "This is immediate feedback, and it provides evidence to later layers."

### Layer 2: AST Deep Analyzer (Structural Intelligence)
Say:
- "We parse Python into an AST and extract structure:"
- "Imports and ML framework hints"
- "Call ordering and ML lifecycle: split -> fit -> evaluate -> serialize"
- "Complexity hotspots and nested logic"
- "Deployment readiness signals"

Key point:
- "AST analysis makes the system repeatable and less hallucination-prone. It provides a stable view of code behavior."

### Layer 3: Gemini Reasoning (Explain + Fix)
Say:
- "The LLM is used for what it does best: reasoning, explanation, and producing code fixes."
- "We also enforce structured JSON output and repair parsing errors to keep the backend robust."

Transition:
- "That gives us a product-level output: a report that is consistent, readable, and usable."

## 14:00 - 16:30 | What Makes This a Real Product (Not Just a Demo)
Say:
- "Winning hackathons is about showing the path to a real product."
- "Here is the product angle:"
- "1) Developer workflow: live feedback, one-click fixes, batch scanning."
- "2) Team workflow: shareable reports for review and compliance."
- "3) CI workflow: fail a PR if a pipeline has CRITICAL leakage or missing serialization."

Optional (if you have time):
- "We can evolve from 'paste code' to 'scan repo' to 'enforce quality gates'."

## 16:30 - 18:30 | Roadmap (Judge-Friendly)
Say:
- "Near-term roadmap:"
- "Repo-wide scanning (multiple files) with consolidated report"
- "Security scan for secrets and unsafe I/O"
- "Performance hints for data pipelines"
- "VS Code extension for in-editor diagnosis"

Say:
- "Long-term:"
- "Framework specialization (sklearn, PyTorch, TF), time-series-aware checks"
- "Governance: audit trail output, model cards, reproducibility packets"

## 18:30 - 20:00 | Close: The One-Sentence Win
Say:
- "ModelDoctor makes ML code trustworthy before it becomes expensive."
- "It prevents silent failures, saves compute, and makes teams confident in what they ship."
- "If you care about reliable AI, you care about pipeline quality. This is how we enforce it."

Ask:
- "We’re looking for pilot repos and feedback on false positives/false negatives."
- "If you’re a judge: evaluate us on impact, technical depth, and product path. We built for all three."

## Q&A Backup (If Asked)
- "Why not just use ChatGPT?": "We provide structured evidence (L1+L2), a repeatable checklist, and robust JSON output with validation."
- "How do you reduce hallucinations?": "AST evidence + strict schema + fallback paths when Gemini fails."
- "How do you monetize?": "Team/enterprise plans for CI gates, repo scanning, policy rules, and compliance artifacts."

