from models.schemas import DiagnosisIssue, Severity
from services.scoring import ScoringEngine

def test_scoring_realistic_cap():
    engine = ScoringEngine()
    
    assert engine.calculate_score([]) == 100
    
    critical_issue = DiagnosisIssue(
        id="DL-001", type="DATA_LEAKAGE", severity=Severity.CRITICAL,
        title="Test", explanation="Test", suggested_fix="Test", health_impact=30
    )
    assert engine.calculate_score([critical_issue]) <= 40
    
    critical_issue_2 = DiagnosisIssue(
        id="DL-002", type="DATA_LEAKAGE", severity=Severity.CRITICAL,
        title="Test", explanation="Test", suggested_fix="Test", health_impact=40
    )
    score = engine.calculate_score([critical_issue, critical_issue_2])
    assert score <= 40
    
    high_issue = DiagnosisIssue(
        id="OF-001", type="OVERFITTING", severity=Severity.HIGH,
        title="Test", explanation="Test", suggested_fix="Test", health_impact=20
    )
    med_issue = DiagnosisIssue(
        id="BP-001", type="BEST_PRACTICES", severity=Severity.MEDIUM,
        title="Test", explanation="Test", suggested_fix="Test", health_impact=10
    )
    score_mixed = engine.calculate_score([high_issue, med_issue])
    assert score_mixed == 70
