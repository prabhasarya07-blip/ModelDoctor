/* ────────────────────────────────────────
   Layer 2: ML Pipeline Analyzer.
   Port of services/pipeline_analyzer.py
   ──────────────────────────────────────── */

import { ParsedCode } from "./parser";

export interface PipelineStage {
  name: "preprocess" | "split" | "train" | "inference" | "evaluate";
  line: number;
  details: Record<string, unknown>;
}

export interface MLEvidence {
  codeType: "research" | "production" | "unknown";
  frameworks: string[];
  stages: PipelineStage[];
  hasTrainTestSplit: boolean;
  hasValidation: boolean;
  hasScaler: boolean;
  modelTypesDetected: string[];
}

const PREPROCESSING = new Set([
  "fit_transform", "transform", "StandardScaler", "MinMaxScaler",
  "LabelEncoder", "OneHotEncoder", "SimpleImputer",
]);
const SPLIT = new Set([
  "train_test_split", "StratifiedKFold", "KFold", "TimeSeriesSplit", "cross_val_score",
]);
const TRAIN = new Set(["fit", "train"]);
const INFERENCE = new Set(["predict", "predict_proba", "forward"]);
const EVALUATE = new Set([
  "score", "evaluate", "accuracy_score", "f1_score", "r2_score",
  "mean_squared_error", "roc_auc_score",
]);

const SCALERS = new Set(["StandardScaler", "MinMaxScaler", "RobustScaler"]);

export function analyzePipeline(parsed: ParsedCode): MLEvidence {
  if (!parsed.parseSuccess) {
    return {
      codeType: "unknown",
      frameworks: [],
      stages: [],
      hasTrainTestSplit: false,
      hasValidation: false,
      hasScaler: false,
      modelTypesDetected: [],
    };
  }

  const stages: PipelineStage[] = [];
  const modelTypesDetected = new Set<string>();

  for (const call of parsed.callsInOrder) {
    const method = call.method ?? call.function ?? "";
    const line = call.line;

    if (PREPROCESSING.has(method)) {
      stages.push({ name: "preprocess", line, details: { method } });
    } else if (SPLIT.has(method)) {
      stages.push({ name: "split", line, details: { method } });
    } else if (TRAIN.has(method)) {
      stages.push({ name: "train", line, details: { method } });
    } else if (INFERENCE.has(method)) {
      stages.push({ name: "inference", line, details: { method } });
    } else if (EVALUATE.has(method)) {
      stages.push({ name: "evaluate", line, details: { method } });
    }

    if (
      method.includes("Classifier") ||
      method.includes("Regressor") ||
      ["LSTM", "GRU", "Dense", "Conv2d"].includes(method)
    ) {
      modelTypesDetected.add(method);
    }
  }

  // Research vs Production script
  let codeType: MLEvidence["codeType"] = "research";
  const hasDeployImport = parsed.imports.importList.some((i) =>
    i.module.includes("deployment_readiness")
  );
  const hasSaveCall = parsed.callsInOrder.some((c) =>
    ["save", "dump", "export"].includes(c.function ?? "")
  );
  if (hasDeployImport || hasSaveCall) codeType = "production";

  const hasTrainTestSplit = stages.some((s) => s.name === "split");
  const hasValidation =
    hasTrainTestSplit ||
    Object.keys(parsed.assignments).some((k) => k.toLowerCase().includes("val"));
  const hasScaler = stages.some(
    (s) => SCALERS.has(String(s.details.method))
  );

  return {
    codeType,
    frameworks: parsed.imports.frameworks,
    stages,
    hasTrainTestSplit,
    hasValidation,
    hasScaler,
    modelTypesDetected: Array.from(modelTypesDetected),
  };
}
