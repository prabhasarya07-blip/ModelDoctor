from __future__ import annotations

import logging
from typing import Any
from models.schemas import Severity, DiagnosisIssue, IssueLocation
from services.parser import ParsedCode
from services.pipeline_analyzer import MLEvidence

logger = logging.getLogger("modeldoctor")

class EngineRule:
    def check(self, parsed: ParsedCode, evidence: MLEvidence) -> list[DiagnosisIssue]:
        raise NotImplementedError

class DetectionEngine:
    def __init__(self):
        self.rules: list[EngineRule] = []

    def register_rule(self, rule: EngineRule):
        self.rules.append(rule)

    def run_all(self, parsed: ParsedCode, evidence: MLEvidence) -> list[DiagnosisIssue]:
        issues = []
        for rule in self.rules:
            try:
                issues.extend(rule.check(parsed, evidence))
            except Exception as e:
                logger.error(f"Rule {rule.__class__.__name__} failed: {e}")
        return issues
