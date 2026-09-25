from models.schemas import DiagnosisIssue, Severity, IssueLocation
from services.engine import EngineRule
from services.parser import ParsedCode
from services.pipeline_analyzer import MLEvidence

class DataLeakageRule(EngineRule):
    """Detects Data Leakage (scaling/imputing before split) and Target Leakage."""
    
    def check(self, parsed: ParsedCode, evidence: MLEvidence) -> list[DiagnosisIssue]:
        issues = []
        
        split_line = next((s.line for s in evidence.stages if s.name == "split"), None)
        
        # 1. Scale before split leakage
        for stage in evidence.stages:
            if stage.name == "preprocess" and split_line and stage.line < split_line:
                issues.append(DiagnosisIssue(
                    id="DL-001",
                    type="DATA_LEAKAGE",
                    severity=Severity.CRITICAL,
                    title="Data Leakage: Preprocessing before Train/Test Split",
                    explanation="Scaling or imputing the entire dataset before splitting causes data leakage. Test set statistics influence the training data.",
                    suggested_fix="Move the preprocessing step AFTER train_test_split. Fit the scaler on X_train only, then transform X_train and X_test separately.",
                    location=IssueLocation(line_start=stage.line, line_end=stage.line),
                    health_impact=30,
                    estimated_quality_impact="Severely overestimated real-world performance.",
                    refactored_code=f"X_train, X_test, y_train, y_test = train_test_split(X, y)\nscaler = StandardScaler()\nX_train = scaler.fit_transform(X_train)\nX_test = scaler.transform(X_test)"
                ))
                break

        # 2. Target Leakage (Features derived from labels)
        for var, lines in parsed.assignments.items():
            if ("target" in var.lower() or "label" in var.lower()) and "drop" not in parsed.code:
                # If target might be in features
                if "X" in parsed.assignments and any(line > lines[0] for line in parsed.assignments["X"]):
                    pass # Heuristic: target is dropped or separated later
                else:
                    issues.append(DiagnosisIssue(
                        id="DL-002",
                        type="DATA_LEAKAGE",
                        severity=Severity.CRITICAL,
                        title="Target Leakage Risk",
                        explanation="The target column was not explicitly dropped from the feature set. Model may securely learn the label.",
                        suggested_fix="Ensure X = df.drop(columns=['target']) before training.",
                        health_impact=35,
                        estimated_quality_impact="Perfect 100% accuracy, but completely useless model.",
                        refactored_code=f"X = df.drop(columns=['{var}'])\ny = df['{var}']"
                    ))
                    break
        
        # 3. Training on test data
        train_calls = [s.line for s in evidence.stages if s.name == "train"]
        eval_calls = [s.line for s in evidence.stages if s.name == "evaluate"]
        if train_calls and not eval_calls and evidence.has_train_test_split:
             # Basic heuristic; if test data is used in fit
             for call in parsed.calls_in_order:
                 if call.get("method") == "fit" and "test" in str(parsed.code.splitlines()[int(call.get("line", 1))-1]).lower():
                     issues.append(DiagnosisIssue(
                         id="DL-003",
                         type="DATA_LEAKAGE",
                         severity=Severity.CRITICAL,
                         title="Training on Test Data",
                         explanation="The model's fit() method appears to be training on the test dataset.",
                         suggested_fix="Ensure model.fit() only takes X_train and y_train.",
                         location=IssueLocation(line_start=call.get("line")),
                         health_impact=50,
                         estimated_quality_impact="Catastrophic failure in real-world generalization."
                     ))
        
        return issues
