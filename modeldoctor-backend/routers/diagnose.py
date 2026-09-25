"""POST /diagnose endpoint — The core ModelDoctor API.

Refactored 5-Layer Architecture:
  Layer 1: Code Parser Layer      (AST Structural Analysis)
  Layer 2: ML Pipeline Analyzer   (Semantic Workflow Mapping)
  Layer 3: Issue Detection Engine (Rule checks)
  Layer 4: Scoring Engine         (Realistic Severity Models)
  Layer 5: Report Generator       (Formats response)
"""

from __future__ import annotations

import logging
import time
import traceback

from fastapi import APIRouter, HTTPException

from models.schemas import DiagnoseRequest, DiagnosisResponse, QuickScanResponse
from services.pattern_scanner import format_flags_for_prompt, scan_code

# New Architecture imports
from services.parser import parse_code
from services.pipeline_analyzer import analyze_pipeline
from services.engine import DetectionEngine
from services.scoring import ScoringEngine

from services.rules.data_leakage import DataLeakageRule
from services.rules.overfitting import OverfittingRule
from services.rules.best_practices import BestPracticesRule

logger = logging.getLogger("modeldoctor")
router = APIRouter()

MAX_CODE_LENGTH = 50_000  # 50k chars max

# Initialize Engine globally
engine = DetectionEngine()
engine.register_rule(DataLeakageRule())
engine.register_rule(OverfittingRule())
engine.register_rule(BestPracticesRule())
scoring_engine = ScoringEngine()

def _validate_code(code: str) -> str:
    """Validate and sanitize code input. Returns cleaned code."""
    code = code.strip()
    if len(code) < 10:
        raise HTTPException(
            status_code=400,
            detail="Code too short for meaningful analysis. Please provide at least 10 characters.",
        )
    if len(code) > MAX_CODE_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Code too long ({len(code):,} chars). Maximum is {MAX_CODE_LENGTH:,} characters.",
        )
    return code


# ──────────────────────────── Endpoints ────────────────────────────

@router.post("/diagnose", response_model=DiagnosisResponse)
async def diagnose(request: DiagnoseRequest) -> DiagnosisResponse:
    """Full 5-layer diagnosis pipeline."""
    code = _validate_code(request.code)
    return await _run_diagnosis_v2(code=code)


@router.post("/quick-scan", response_model=QuickScanResponse)
async def quick_scan(request: DiagnoseRequest) -> QuickScanResponse:
    """Lightweight Layer-1-only scan. Used for real-time editor feedback."""
    code = request.code.strip()
    if len(code) < 10:
        return QuickScanResponse(flags=[], scan_time_ms=0)

    t0 = time.perf_counter()
    try:
        flags = scan_code(code)
    except Exception as e:
        logger.error("Quick scan failed: %s", e)
        flags = []
    elapsed = round((time.perf_counter() - t0) * 1000, 2)

    return QuickScanResponse(flags=flags, scan_time_ms=elapsed)


# ──────────────────────────── Pipeline ────────────────────────────

async def _run_diagnosis_v2(code: str) -> DiagnosisResponse:
    """Run the refactored 5-layer ModelDoctor diagnostic pipeline."""
    pipeline_start = time.perf_counter()
    timings: dict[str, float] = {}

    try:
        # Layer 1 & 2: Abstract understanding
        t0 = time.perf_counter()
        parsed = parse_code(code)
        evidence = analyze_pipeline(parsed)
        timings["parse_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # Layer 3: Run Engine Rules in Memory (Parallel concept)
        t0 = time.perf_counter()
        issues = engine.run_all(parsed, evidence)
        timings["engine_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # Layer 4: Realistic Scoring Output
        t0 = time.perf_counter()
        health_score = scoring_engine.calculate_score(issues)
        timings["scoring_ms"] = round((time.perf_counter() - t0) * 1000, 1)

        # Layer 5: Report Generation 
        total_ms = round((time.perf_counter() - pipeline_start) * 1000, 1)
        
        summary = (
            f"Analyzed {len(parsed.calls_in_order)} ML operations logic map. "
            f"Found {len(issues)} pipeline flaws. "
            f"Detected ML Stage: {'Production' if evidence.code_type == 'production' else 'Research/Experimentation'}."
        )

        logger.info(
            "V2 Pipeline complete: score=%d, issues=%d, total=%.0fms",
            health_score, len(issues), total_ms
        )

        # Translate stages for frontend visualization
        mapped_stages = [
            {"name": s.name, "line": s.line, "details": s.details}
            for s in evidence.stages
        ]
        
        # Calculate Model Complexity Score
        # Max Depth ranges from 1-7 realistically. Deep layers exist -> add penalty
        depth = parsed.tree and hasattr(parsed.tree, 'body') and 3 # Simplified approximation
        layer_count = sum(1 for call in parsed.calls_in_order if call.get("function") in {"Dense", "Conv2d", "LSTM", "Linear", "TransformerEncoder"})
        complexity_score = min(10, max(1, (layer_count // 2) + 1))
        
        # Identify Compute Waste Risk
        gpu_waste = "Low"
        if layer_count > 3:
            has_device = any("to" == call.get("method") or "cuda" == call.get("method") for call in parsed.calls_in_order)
            gpu_waste = "High (Deep network, no GPU device mapped)" if not has_device else "Low"

        return DiagnosisResponse(
            health_score=health_score,
            issues=issues,
            pipeline_stages=mapped_stages,
            model_complexity_score=complexity_score,
            gpu_waste_risk=gpu_waste,
            summary=summary,
            diagnosis_time_ms=int(total_ms),
            model_used="ModelDoctor Rules Engine V2"
        )

    except Exception as e:
        logger.error("Diagnosis failed: %s\n%s", e, traceback.format_exc())
        return DiagnosisResponse(
            health_score=0,
            issues=[],
            summary=f"Analysis encountered an error. Please try again. ({type(e).__name__})",
            diagnosis_time_ms=int((time.perf_counter() - pipeline_start) * 1000),
            model_used="ModelDoctor Rules Engine V2"
        )
