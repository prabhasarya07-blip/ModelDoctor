from models.schemas import DiagnosisIssue, Severity, IssueLocation
from services.engine import EngineRule
from services.parser import ParsedCode
from services.pipeline_analyzer import MLEvidence

class BestPracticesRule(EngineRule):
    """Detects missing scaling, low-level deployment issues, and compute waste."""
    
    def check(self, parsed: ParsedCode, evidence: MLEvidence) -> list[DiagnosisIssue]:
        issues = []
        
        # 1. Missing Scaling
        # Some models require scaling.
        requires_scaling = {"SVC", "SVR", "KNeighbors", "LogisticRegression", "Dense", "Linear"}
        if any(model in parsed.code for model in requires_scaling) and not evidence.has_scaler:
            issues.append(DiagnosisIssue(
                id="BP-001",
                type="PREPROCESSING",
                severity=Severity.MEDIUM,
                title="Missing Feature Scaling",
                explanation="Model relies on distance or gradient descent, but no scaling (e.g., StandardScaler) was found.",
                suggested_fix="Use sklearn.preprocessing.StandardScaler on training data before fitting.",
                health_impact=10,
                estimated_quality_impact="Slower convergence or degraded performance."
            ))

        # 2. Missing Value Handling
        if "fillna" not in parsed.code and "SimpleImputer" not in parsed.code and "dropna" not in parsed.code:
             issues.append(DiagnosisIssue(
                 id="BP-002",
                 type="DATA_QUALITY",
                 severity=Severity.MEDIUM,
                 title="Possible Missing Value Mishandling",
                 explanation="No explicit missing value handling (imputation or dropping) was detected.",
                 suggested_fix="Check your dataset for NaNs, and use SimpleImputer or df.fillna() if present.",
                 health_impact=5,
                 estimated_quality_impact="Model training might crash, or errors will silently propagate."
             ))

        # 3. Logging / Code Cleanliness (Low Severity)
        if "logger" not in parsed.code and "logging" not in parsed.code and evidence.code_type == "production":
             issues.append(DiagnosisIssue(
                 id="BP-003",
                 type="DEPLOYMENT",
                 severity=Severity.LOW,
                 title="Missing Production Logging",
                 explanation="Production ML pipelines should use structured logging instead of print statements.",
                 suggested_fix="Import logging and configure a logger.",
                 health_impact=2,
                 estimated_quality_impact="No impact on model metrics, just harder maintainability."
             ))
             
        # 4. Deployment Readiness: random_state
        if "train_test_split" in parsed.code and "random_state" not in parsed.code:
            issues.append(DiagnosisIssue(
                 id="BP-004",
                 type="DEPLOYMENT",
                 severity=Severity.LOW,
                 title="Non-Reproducible Split",
                 explanation="train_test_split used without random_state.",
                 suggested_fix="Add random_state=42 (or any integer) to ensure reproducibility.",
                 health_impact=1,
                 estimated_quality_impact="Results will vary slightly every run.",
                 refactored_code="X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)"
             ))

        return issues
