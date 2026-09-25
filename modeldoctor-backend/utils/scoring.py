"""Health score calculation utilities.

Enhanced with:
  - Diminishing returns for duplicate issue types
  - GPU waste estimation
  - Letter grade assignment
"""

from __future__ import annotations

from collections import Counter

from models.schemas import DiagnosisIssue, Severity


def calculate_health_score(issues: list[DiagnosisIssue]) -> int:
    """Calculate the pipeline health score from 0–100.

    Starts at 100 and deducts based on issue severity.
    Uses diminishing returns: 2nd+ issue of same type counts less.
    """
    score = 100
    type_counts: Counter[str] = Counter()

    for issue in issues:
        # Use the LLM-provided impact, but clamp it to severity ranges
        impact = abs(issue.health_impact)

        if issue.severity == Severity.CRITICAL:
            impact = max(25, min(impact, 40))
        elif issue.severity == Severity.HIGH:
            impact = max(15, min(impact, 25))
        elif issue.severity == Severity.MEDIUM:
            impact = max(5, min(impact, 15))
        elif issue.severity == Severity.LOW:
            impact = max(2, min(impact, 5))

        # Diminishing returns: 2nd issue of same type = 60%, 3rd = 40%, 4th+ = 25%
        type_counts[issue.type] += 1
        occurrence = type_counts[issue.type]
        if occurrence == 2:
            impact = int(impact * 0.6)
        elif occurrence == 3:
            impact = int(impact * 0.4)
        elif occurrence >= 4:
            impact = int(impact * 0.25)

        score -= impact

    return max(0, min(100, score))


def severity_sort_key(severity: Severity) -> int:
    """Return sort priority (lower = more severe = appears first)."""
    return {
        Severity.CRITICAL: 0,
        Severity.HIGH: 1,
        Severity.MEDIUM: 2,
        Severity.LOW: 3,
    }.get(severity, 4)


def get_health_grade(score: int) -> str:
    """Convert numeric score to a letter grade."""
    if score >= 90:
        return "A"
    elif score >= 80:
        return "B"
    elif score >= 65:
        return "C"
    elif score >= 50:
        return "D"
    else:
        return "F"


def estimate_gpu_waste_risk(issues: list[DiagnosisIssue]) -> str:
    """Estimate how much GPU time would be wasted by training with these issues.

    Returns a human-readable risk assessment.
    """
    critical_count = sum(1 for i in issues if i.severity == Severity.CRITICAL)
    high_count = sum(1 for i in issues if i.severity == Severity.HIGH)

    has_leakage = any(i.type == "DATA_LEAKAGE" for i in issues)
    has_mismatch = any(i.type == "CODE_DATA_MISMATCH" for i in issues)

    if has_mismatch:
        return "CODE WILL CRASH — 100% wasted. Fix data mismatches first."
    elif has_leakage and critical_count >= 2:
        return "EXTREME — all training results will be invalid. Every GPU second is wasted money."
    elif critical_count >= 1:
        return "HIGH — model will train but produce unreliable results. Significant compute waste likely."
    elif high_count >= 2:
        return "MODERATE — model will underperform significantly. 30-50% of compute arguably wasted."
    elif high_count >= 1:
        return "LOW-MODERATE — model will work but with degraded quality. Some optimization opportunity lost."
    else:
        return "LOW — minor improvements possible but pipeline is fundamentally sound."
