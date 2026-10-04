/* ────────────────────────────────────────
   Layers 3 & 4: Detection rules + scoring.
   Port of services/engine.py, services/scoring.py
   and services/rules/*.py
   ──────────────────────────────────────── */

import { DiagnosisIssue, IssueLocation } from "@/lib/types";
import { ParsedCode } from "./parser";
import { MLEvidence } from "./pipeline-analyzer";

export type EngineRule = (
  parsed: ParsedCode,
  evidence: MLEvidence
) => DiagnosisIssue[];

const loc = (line: number): IssueLocation => ({
  line_start: line,
  line_end: line,
  code_snippet: null,
});

/* ── Rule 1: Data leakage ── */

export const dataLeakageRule: EngineRule = (parsed, evidence) => {
  const issues: DiagnosisIssue[] = [];
  const splitLine = evidence.stages.find((s) => s.name === "split")?.line;

  // 1. Preprocessing before split
  for (const stage of evidence.stages) {
    if (stage.name === "preprocess" && splitLine != null && stage.line < splitLine) {
      issues.push({
        id: "DL-001",
        type: "DATA_LEAKAGE",
        severity: "CRITICAL",
        title: "Data Leakage: Preprocessing before Train/Test Split",
        explanation:
          "Scaling or imputing the entire dataset before splitting causes data leakage. Test set statistics influence the training data.",
        suggested_fix:
          "Move the preprocessing step AFTER train_test_split. Fit the scaler on X_train only, then transform X_train and X_test separately.",
        location: loc(stage.line),
        health_impact: 30,
        estimated_quality_impact: "Severely overestimated real-world performance.",
        refactored_code:
          "X_train, X_test, y_train, y_test = train_test_split(X, y)\nscaler = StandardScaler()\nX_train = scaler.fit_transform(X_train)\nX_test = scaler.transform(X_test)",
      });
      break;
    }
  }

  // 2. Target leakage (target/label variable never dropped)
  for (const [variable, lines] of Object.entries(parsed.assignments)) {
    const lower = variable.toLowerCase();
    if ((lower.includes("target") || lower.includes("label")) && !parsed.code.includes("drop")) {
      const xLines = parsed.assignments.X;
      const targetSeparatedLater = !!xLines && xLines.some((l) => l > lines[0]);
      if (!targetSeparatedLater) {
        issues.push({
          id: "DL-002",
          type: "DATA_LEAKAGE",
          severity: "CRITICAL",
          title: "Target Leakage Risk",
          explanation:
            "The target column was not explicitly dropped from the feature set. The model may learn the label itself.",
          suggested_fix: `Ensure X = df.drop(columns=['${variable}']) before training.`,
          location: null,
          health_impact: 35,
          estimated_quality_impact: "Perfect 100% accuracy, but a completely useless model.",
          refactored_code: `X = df.drop(columns=['${variable}'])\ny = df['${variable}']`,
        });
        break;
      }
    }
  }

  // 3. fit() on test data
  const trainCalls = evidence.stages.filter((s) => s.name === "train");
  const evalCalls = evidence.stages.filter((s) => s.name === "evaluate");
  if (trainCalls.length && !evalCalls.length && evidence.hasTrainTestSplit) {
    const codeLines = parsed.code.split("\n");
    for (const call of parsed.callsInOrder) {
      if (call.method !== "fit") continue;
      const source = (codeLines[call.line - 1] ?? "").toLowerCase();
      if (source.includes("test")) {
        issues.push({
          id: "DL-003",
          type: "DATA_LEAKAGE",
          severity: "CRITICAL",
          title: "Training on Test Data",
          explanation:
            "The model's fit() method appears to be training on the test dataset.",
          suggested_fix: "Ensure model.fit() only takes X_train and y_train.",
          location: loc(call.line),
          health_impact: 50,
          estimated_quality_impact: "Catastrophic failure in real-world generalization.",
        });
      }
    }
  }

  return issues;
};

/* ── Rule 2: Overfitting ── */

export const overfittingRule: EngineRule = (parsed, evidence) => {
  const issues: DiagnosisIssue[] = [];

  // 1. Missing validation split
  if (!evidence.hasValidation) {
    issues.push({
      id: "OF-001",
      type: "OVERFITTING",
      severity: "HIGH",
      title: "Missing Validation Data",
      explanation:
        "There is no train_test_split or cross-validation found. Training without validating leads to undetected overfitting.",
      suggested_fix:
        "Use sklearn.model_selection.train_test_split to create a testing baseline.",
      location: null,
      health_impact: 20,
      estimated_quality_impact: "Model operates blindly. Generalization can't be ensured.",
    });
  }

  // 2. Classification metric on a regression model
  if (
    parsed.code.includes("accuracy_score") &&
    evidence.modelTypesDetected.some((t) => t.includes("Regressor"))
  ) {
    issues.push({
      id: "EV-001",
      type: "EVALUATION_ERROR",
      severity: "HIGH",
      title: "Classification Metric on Regression Model",
      explanation: "Accuracy cannot be used to evaluate Regression models.",
      suggested_fix: "Use mean_squared_error or r2_score for regressors.",
      location: null,
      health_impact: 15,
      estimated_quality_impact: "Inaccurate quality assessment.",
    });
  }

  // 3. Deep network with no regularization
  const layers = parsed.callsInOrder.filter((c) =>
    ["Dense", "Linear", "LSTM"].includes(c.function ?? "")
  ).length;
  if (
    layers > 4 &&
    !parsed.code.includes("Dropout") &&
    !parsed.code.includes("EarlyStopping")
  ) {
    issues.push({
      id: "OF-002",
      type: "OVERFITTING",
      severity: "HIGH",
      title: "Overfitting Risk: Deep Network without Regularization",
      explanation:
        "Deep network identified with no Dropout or EarlyStopping. High chance of memorizing noise.",
      suggested_fix:
        "Add Dropout layers between dense layers or implement EarlyStopping callbacks.",
      location: null,
      health_impact: 20,
      estimated_quality_impact:
        "Significant drop in test accuracy compared to train accuracy.",
    });
  }

  // 4. Unconstrained tree depth
  if (
    parsed.code.includes("DecisionTreeClassifier") &&
    !parsed.code.includes("max_depth")
  ) {
    issues.push({
      id: "OF-003",
      type: "OVERFITTING",
      severity: "MEDIUM",
      title: "Overfitting Risk: Unconstrained Tree Depth",
      explanation:
        "Decision trees without max_depth grow until they perfectly memorize the training data.",
      suggested_fix:
        "Set a max_depth constraint (e.g., max_depth=5) or min_samples_split.",
      location: null,
      health_impact: 15,
      estimated_quality_impact: "Poor generalization on unseen data.",
    });
  }

  return issues;
};

/* ── Rule 3: Best practices ── */

const REQUIRES_SCALING = ["SVC", "SVR", "KNeighbors", "LogisticRegression", "Dense", "Linear"];

export const bestPracticesRule: EngineRule = (parsed, evidence) => {
  const issues: DiagnosisIssue[] = [];

  // 1. Missing feature scaling
  if (
    REQUIRES_SCALING.some((m) => parsed.code.includes(m)) &&
    !evidence.hasScaler
  ) {
    issues.push({
      id: "BP-001",
      type: "PREPROCESSING",
      severity: "MEDIUM",
      title: "Missing Feature Scaling",
      explanation:
        "Model relies on distance or gradient descent, but no scaling (e.g., StandardScaler) was found.",
      suggested_fix: "Use sklearn.preprocessing.StandardScaler on training data before fitting.",
      location: null,
      health_impact: 10,
      estimated_quality_impact: "Slower convergence or degraded performance.",
    });
  }

  // 2. Missing value handling
  if (
    !parsed.code.includes("fillna") &&
    !parsed.code.includes("SimpleImputer") &&
    !parsed.code.includes("dropna")
  ) {
    issues.push({
      id: "BP-002",
      type: "DATA_QUALITY",
      severity: "MEDIUM",
      title: "Possible Missing Value Mishandling",
      explanation:
        "No explicit missing value handling (imputation or dropping) was detected.",
      suggested_fix:
        "Check your dataset for NaNs, and use SimpleImputer or df.fillna() if present.",
      location: null,
      health_impact: 5,
      estimated_quality_impact:
        "Model training might crash, or errors will silently propagate.",
    });
  }

  // 3. Missing production logging
  if (
    !parsed.code.includes("logger") &&
    !parsed.code.includes("logging") &&
    evidence.codeType === "production"
  ) {
    issues.push({
      id: "BP-003",
      type: "DEPLOYMENT",
      severity: "LOW",
      title: "Missing Production Logging",
      explanation:
        "Production ML pipelines should use structured logging instead of print statements.",
      suggested_fix: "Import logging and configure a logger.",
      location: null,
      health_impact: 2,
      estimated_quality_impact: "No impact on model metrics, just harder maintainability.",
    });
  }

  // 4. Non-reproducible split
  if (
    parsed.code.includes("train_test_split") &&
    !parsed.code.includes("random_state")
  ) {
    issues.push({
      id: "BP-004",
      type: "DEPLOYMENT",
      severity: "LOW",
      title: "Non-Reproducible Split",
      explanation: "train_test_split used without random_state.",
      suggested_fix: "Add random_state=42 (or any integer) to ensure reproducibility.",
      location: null,
      health_impact: 1,
      estimated_quality_impact: "Results will vary slightly every run.",
      refactored_code:
        "X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)",
    });
  }

  return issues;
};

/* ── Engine ── */

export function runAllRules(
  rules: EngineRule[],
  parsed: ParsedCode,
  evidence: MLEvidence
): DiagnosisIssue[] {
  const issues: DiagnosisIssue[] = [];
  for (const rule of rules) {
    try {
      issues.push(...rule(parsed, evidence));
    } catch (err) {
      console.error("Rule failed:", err);
    }
  }
  return issues;
}

/* ── Scoring ── */

export function calculateScore(issues: DiagnosisIssue[]): number {
  let score = 100;
  let criticalCount = 0;
  let highCount = 0;

  for (const issue of issues) {
    switch (issue.severity) {
      case "CRITICAL":
        criticalCount += 1;
        // First critical is massive; subsequent ones are less impactful.
        score -= criticalCount === 1 ? issue.health_impact : Math.floor(issue.health_impact / 2);
        break;
      case "HIGH":
        highCount += 1;
        score -= highCount <= 2 ? issue.health_impact : Math.floor(issue.health_impact / 2);
        break;
      case "MEDIUM":
      case "LOW":
        score -= issue.health_impact;
        break;
    }
  }

  // A model with critical issues can never be "passing".
  if (criticalCount > 0) score = Math.min(score, 40);

  return Math.max(0, Math.min(100, score));
}
