from models.schemas import DiagnosisIssue, Severity, IssueLocation
from services.engine import EngineRule
from services.parser import ParsedCode
from services.pipeline_analyzer import MLEvidence

class OverfittingRule(EngineRule):
    """Detects Overfitting risk (model size vs dataset size, missing validation)."""
    
    def check(self, parsed: ParsedCode, evidence: MLEvidence) -> list[DiagnosisIssue]:
        issues = []
        
        # 1. Missing Validation Split
        if not evidence.has_validation:
            issues.append(DiagnosisIssue(
                id="OF-001",
                type="OVERFITTING",
                severity=Severity.HIGH,
                title="Missing Validation Data",
                explanation="There is no train_test_split or cross-validation found. Training without validating leads to undetected overfitting.",
                suggested_fix="Use sklearn.model_selection.train_test_split to create a testing baseline.",
                health_impact=20,
                estimated_quality_impact="Model operates blindly. Can't ensure generalization."
            ))
            
        # 2. Wrong evaluation metrics (Classification vs Regression)
        # Check if classification models use regression metrics or vice versa.
        # This belongs in evaluation, but we merge it in the rules.
        if "accuracy_score" in parsed.code and ("Regressor" in ",".join(evidence.model_types_detected)):
            issues.append(DiagnosisIssue(
                id="EV-001",
                type="EVALUATION_ERROR",
                severity=Severity.HIGH,
                title="Classification Metric on Regression Model",
                explanation="Accuracy cannot be used to evaluate Regression models.",
                suggested_fix="Use mean_squared_error or r2_score for regressors.",
                health_impact=15,
                estimated_quality_impact="Inaccurate quality assessment."
            ))

        # 3. Overfitting risk (complexity vs regularizers)
        layers = sum(1 for call in parsed.calls_in_order if call.get("function") in ("Dense", "Linear", "LSTM"))
        if layers > 4 and "Dropout" not in parsed.code and "EarlyStopping" not in parsed.code:
             issues.append(DiagnosisIssue(
                 id="OF-002",
                 type="OVERFITTING",
                 severity=Severity.HIGH,
                 title="Overfitting Risk: Deep Network without Regularization",
                 explanation="Deep network identified with no Dropout or EarlyStopping. High chance of memorizing noise.",
                 suggested_fix="Add Dropout layers between dense layers or implement EarlyStopping callbacks.",
                 health_impact=20,
                 estimated_quality_impact="Significant drop in test accuracy compared to train accuracy."
             ))

        # 4. Tree depth missing
        if "DecisionTreeClassifier" in parsed.code and "max_depth" not in parsed.code:
            issues.append(DiagnosisIssue(
                 id="OF-003",
                 type="OVERFITTING",
                 severity=Severity.MEDIUM, # Actually, requirements say HIGH for Overfitting Risk
                 title="Overfitting Risk: Unconstrained Tree Depth",
                 explanation="Decision trees without max_depth grow until they perfectly memorize the training data.",
                 suggested_fix="Set a max_depth constraint (e.g., max_depth=5) or min_samples_split.",
                 health_impact=15,
                 estimated_quality_impact="Poor generalization on unseen data."
             ))

        return issues
