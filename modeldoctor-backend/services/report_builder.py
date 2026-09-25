"""Report Builder — Assembles the final diagnosis report.

Combines pattern scanner results, AST deep analysis, and Gemini LLM output into
a unified, severity-sorted, health-scored, GPU-waste-estimated response.
"""

from __future__ import annotations

from models.schemas import DiagnosisIssue, DiagnosisResponse
from utils.scoring import (
    calculate_health_score,
    severity_sort_key,
    get_health_grade,
    estimate_gpu_waste_risk,
)


def build_report(
    gemini_health_score: int,
    issues: list[DiagnosisIssue],
    summary: str,
    elapsed_ms: int,
) -> DiagnosisResponse:
    """Assemble the final diagnosis report.

    - Recalculates health score from issues (overrides LLM score for consistency)
    - Sorts issues by severity (CRITICAL first)
    - Enriches summary with grade and GPU waste estimate
    """
    # Sort issues: CRITICAL → HIGH → MEDIUM → LOW
    sorted_issues = sorted(issues, key=lambda i: severity_sort_key(i.severity))

    # Recalculate health score from actual issue impacts
    calculated_score = calculate_health_score(sorted_issues)

    # If the LLM score and calculated score diverge heavily, average them
    if abs(calculated_score - gemini_health_score) > 20:
        final_score = (calculated_score + gemini_health_score) // 2
    else:
        final_score = calculated_score

    final_score = max(0, min(100, final_score))

    # Enhance summary with grade and GPU waste
    grade = get_health_grade(final_score)
    gpu_risk = estimate_gpu_waste_risk(sorted_issues)

    if not summary or len(summary) < 20:
        summary = _generate_summary(sorted_issues, final_score, grade, gpu_risk)
    else:
        # Append grade and GPU waste to LLM summary
        summary = f"{summary}\n\nHealth Grade: {grade} ({final_score}/100). GPU Waste Risk: {gpu_risk}"

    return DiagnosisResponse(
        health_score=final_score,
        issues=sorted_issues,
        summary=summary,
        diagnosis_time_ms=elapsed_ms,
        model_used="gemini-2.5-flash",
    )


def _generate_summary(
    issues: list[DiagnosisIssue],
    score: int,
    grade: str,
    gpu_risk: str,
) -> str:
    """Generate a fallback summary if the LLM didn't provide a good one."""
    if not issues:
        return (
            f"No significant issues detected in this ML pipeline. Health Grade: {grade} ({score}/100). "
            f"The code follows good practices for data handling and model training. "
            f"GPU Waste Risk: {gpu_risk}"
        )

    critical_count = sum(1 for i in issues if i.severity.value == "CRITICAL")
    high_count = sum(1 for i in issues if i.severity.value == "HIGH")
    medium_count = sum(1 for i in issues if i.severity.value == "MEDIUM")

    parts = []
    if critical_count:
        parts.append(f"{critical_count} CRITICAL")
    if high_count:
        parts.append(f"{high_count} HIGH")
    if medium_count:
        parts.append(f"{medium_count} MEDIUM")

    issue_text = ", ".join(parts) if parts else f"{len(issues)} issues"

    if score < 30:
        urgency = "Pipeline is NOT safe to train. Immediate fixes required before spending any GPU time."
    elif score < 50:
        urgency = "Pipeline has serious issues that will produce unreliable results. Fix before training."
    elif score < 65:
        urgency = "Pipeline has significant issues that should be addressed for trustworthy results."
    elif score < 80:
        urgency = "Pipeline is mostly healthy but has room for improvement."
    else:
        urgency = "Pipeline is in good shape with minor improvements possible."

    return (
        f"Found {issue_text} issue(s). Health Grade: {grade} ({score}/100). "
        f"{urgency} GPU Waste Risk: {gpu_risk}"
    )
