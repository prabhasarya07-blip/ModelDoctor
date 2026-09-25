"""Layer 2: ML Pipeline Analyzer — Map code into a high-level pipeline abstraction."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any
from services.parser import ParsedCode

logger = logging.getLogger("modeldoctor")

@dataclass
class PipelineStage:
    name: str # e.g., 'split', 'scale', 'impute', 'fit', 'predict', 'score'
    line: int
    details: dict[str, Any]

@dataclass
class MLEvidence:
    code_type: str # 'research' vs 'production'
    frameworks: list[str]
    stages: list[PipelineStage]
    has_train_test_split: bool
    has_validation: bool
    has_scaler: bool
    model_types_detected: set[str]

def analyze_pipeline(parsed: ParsedCode) -> MLEvidence:
    """Analyze the parsed code to reconstruct the logical ML pipeline."""
    if not parsed.parse_success:
        return MLEvidence("unknown", [], [], False, False, False, set())

    stages: list[PipelineStage] = []
    
    # 1. Detect Frameworks
    frameworks = parsed.imports.get("frameworks", [])
    
    # 2. Extract Pipeline Stages from calls
    # Known method signatures
    PREPROCESSING = {"fit_transform", "transform", "StandardScaler", "MinMaxScaler", "LabelEncoder", "OneHotEncoder", "SimpleImputer"}
    SPLIT = {"train_test_split", "StratifiedKFold", "KFold", "TimeSeriesSplit", "cross_val_score"}
    TRAIN = {"fit", "train"}
    INFERENCE = {"predict", "predict_proba", "forward"}
    EVALUATE = {"score", "evaluate", "accuracy_score", "f1_score", "r2_score", "mean_squared_error", "roc_auc_score"}
    
    model_types_detected = set()

    for call in parsed.calls_in_order:
        method = call.get("method", call.get("function", ""))
        line = int(call.get("line", 0))
        
        if method in PREPROCESSING:
            stages.append(PipelineStage("preprocess", line, {"method": method}))
        elif method in SPLIT:
            stages.append(PipelineStage("split", line, {"method": method}))
        elif method in TRAIN:
            stages.append(PipelineStage("train", line, {"method": method}))
        elif method in INFERENCE:
            stages.append(PipelineStage("inference", line, {"method": method}))
        elif method in EVALUATE:
            stages.append(PipelineStage("evaluate", line, {"method": method}))
        
        # Detect model instantiations/imports loosely
        # For simplicity, if we see known model names ending in Classifier/Regressor
        if "Classifier" in method or "Regressor" in method or method in ("LSTM", "GRU", "Dense", "Conv2d"):
            model_types_detected.add(method)

    # 3. Detect Research vs Production script
    code_type = "research"
    if "deployment_readiness" in parsed.imports or any(c.get("function") in ("save", "dump", "export") for c in parsed.calls_in_order):
        code_type = "production"
    
    # Simple heuristics for flags
    has_train_test_split = any(s.name == "split" for s in stages)
    has_validation = has_train_test_split or any("val" in k.lower() for k in parsed.assignments.keys())
    has_scaler = any(s.details.get("method") in {"StandardScaler", "MinMaxScaler", "RobustScaler"} for s in stages)

    return MLEvidence(
        code_type=code_type,
        frameworks=frameworks,
        stages=stages,
        has_train_test_split=has_train_test_split,
        has_validation=has_validation,
        has_scaler=has_scaler,
        model_types_detected=model_types_detected
    )
