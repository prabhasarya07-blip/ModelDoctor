import logging
from models.schemas import DiagnosisIssue, Severity

logger = logging.getLogger("modeldoctor")

class ScoringEngine:
    """Calculates a realistic health score for an ML pipeline."""
    
    def calculate_score(self, issues: list[DiagnosisIssue]) -> int:
        score = 100
        
        # Deduct impact for each issue, capping penalties to avoid 
        # dropping below 0 unreasonably.
        critical_count = 0
        high_count = 0
        
        for issue in issues:
            if issue.severity == Severity.CRITICAL:
                critical_count += 1
                # First critical is massive, subsequent ones are less impactful
                penalty = issue.health_impact if critical_count == 1 else issue.health_impact // 2
                score -= penalty
            elif issue.severity == Severity.HIGH:
                high_count += 1
                penalty = issue.health_impact if high_count <= 2 else issue.health_impact // 2
                score -= penalty
            elif issue.severity == Severity.MEDIUM:
                score -= issue.health_impact
            elif issue.severity == Severity.LOW:
                score -= issue.health_impact
        
        # Ensure meaningful floor and boundaries
        if critical_count > 0:
            score = min(score, 40) # A model with critical issues can never be "passing"
            
        return max(0, min(100, score))
