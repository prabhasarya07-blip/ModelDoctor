"""Pydantic models for request/response schemas."""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ───── Request Models ─────


class CodeContext(BaseModel):
    """Optional metadata about the ML code being diagnosed."""

    dataset_size: Optional[str] = None
    model_type: Optional[str] = None
    framework: Optional[str] = None


class DiagnoseRequest(BaseModel):
    """Request body for POST /diagnose."""

    code: str = Field(..., min_length=10, description="Python ML code to diagnose")
    language: str = Field(default="python", description="Programming language")
    context: Optional[CodeContext] = None


# ───── Response Models ─────


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IssueLocation(BaseModel):
    """Where in the code the issue was found."""

    line_start: Optional[int] = None
    line_end: Optional[int] = None
    code_snippet: Optional[str] = None


class DiagnosisIssue(BaseModel):
    """A single diagnosed issue in the ML pipeline."""

    id: str = Field(..., description="Issue ID like DL-001, OF-001")
    type: str = Field(..., description="Issue category: DATA_LEAKAGE, OVERFITTING, etc.")
    severity: Severity
    title: str
    explanation: str
    suggested_fix: str
    location: Optional[IssueLocation] = None
    health_impact: int = Field(..., description="Points deducted from 100")
    estimated_quality_impact: str = Field(default="Unknown", description="Estimated impact on model quality")
    refactored_code: Optional[str] = Field(default=None, description="Auto-refactoring exact string replacement if applicable")


class PipelineStageSchema(BaseModel):
    """Visualizes a step in the ML pipeline"""
    name: str
    line: int
    details: dict


class DiagnosisResponse(BaseModel):
    """Full diagnosis report returned to the frontend."""

    health_score: int = Field(..., ge=0, le=100)
    issues: list[DiagnosisIssue]
    pipeline_stages: list[PipelineStageSchema] = Field(default_factory=list)
    model_complexity_score: int = Field(default=1, ge=1, le=10)
    gpu_waste_risk: str = Field(default="Low")
    summary: str
    diagnosis_time_ms: int
    model_used: str = "Static Analyzer Engine V2"


class QuickScanResponse(BaseModel):
    """Lightweight response for real-time pattern scanning (no Gemini)."""

    flags: list["PatternFlag"]
    scan_time_ms: float = Field(..., description="Time taken for the scan in ms")


# ───── Internal Models ─────


class PatternFlag(BaseModel):
    """A suspect pattern found by the static scanner."""

    pattern_id: str
    pattern_name: str
    severity: Severity
    description: str
    line_number: Optional[int] = None
    matched_code: Optional[str] = None
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
