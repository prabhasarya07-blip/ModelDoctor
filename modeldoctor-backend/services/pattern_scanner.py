"""Layer 1: Static Pattern Scanner — Heuristic analysis of ML code.

Scans code for known anti-patterns using regex and line-by-line analysis.
Runs in <10ms. Flags suspects for the LLM reasoning layer.

30+ rules covering:
  - Data Leakage (DL)
  - Train/Test Split Errors (TS)
  - Overfitting (OF)
  - Feature Misuse (FM)
  - Preprocessing Errors (PE)
  - Gradient / Training Instability (GI)
  - Evaluation & Metric Errors (EV)
  - Resource & Performance (RP)
"""

from __future__ import annotations

import re
from models.schemas import PatternFlag, Severity


# ───── Pattern Definitions ─────

PATTERNS: list[dict] = [
    # ═══════════════════════════════════════
    # DATA LEAKAGE (DL)
    # ═══════════════════════════════════════
    {
        "id": "DL-SCALE-BEFORE-SPLIT",
        "name": "Scaler fitted before train/test split",
        "severity": Severity.CRITICAL,
        "description": "StandardScaler/MinMaxScaler/RobustScaler fitted on full dataset before split. Test data statistics leak into training.",
        "regex": r"(fit_transform|\.fit)\s*\(\s*(X|data|df|features)",
        "requires_split_after": True,
    },
    {
        "id": "DL-ENCODE-BEFORE-SPLIT",
        "name": "Encoding applied before train/test split",
        "severity": Severity.CRITICAL,
        "description": "Label encoding or one-hot encoding applied to full dataset before splitting. Category mappings leak from test to train.",
        "regex": r"(LabelEncoder|OneHotEncoder|OrdinalEncoder|get_dummies)\s*\(",
        "requires_split_after": True,
    },
    {
        "id": "DL-IMPUTE-BEFORE-SPLIT",
        "name": "Imputation before train/test split",
        "severity": Severity.HIGH,
        "description": "Missing value imputation on full dataset before splitting leaks test distribution into training.",
        "regex": r"(SimpleImputer|fillna|interpolate|KNNImputer)\s*\(",
        "requires_split_after": True,
    },
    {
        "id": "DL-PCA-BEFORE-SPLIT",
        "name": "Dimensionality reduction before split",
        "severity": Severity.CRITICAL,
        "description": "PCA/SVD/feature selection fitted on full dataset before split. Components capture test data variance.",
        "regex": r"(PCA|TruncatedSVD|SelectKBest|VarianceThreshold|TSNE|UMAP)\s*\(",
        "requires_split_after": True,
    },
    {
        "id": "DL-SMOTE-BEFORE-SPLIT",
        "name": "SMOTE/oversampling before train/test split",
        "severity": Severity.CRITICAL,
        "description": "Synthetic samples generated from full dataset may create test-like training samples, causing massive leakage.",
        "regex": r"(SMOTE|RandomOverSampler|ADASYN|BorderlineSMOTE)\s*\(",
        "requires_split_after": True,
    },
    {
        "id": "DL-FEATURE-SELECT-BEFORE-SPLIT",
        "name": "Feature selection using target before split",
        "severity": Severity.CRITICAL,
        "description": "Selecting features using correlation with target on full dataset leaks test relationships into feature selection.",
        "regex": r"(SelectKBest|mutual_info_classif|chi2|f_classif|f_regression)\s*\(",
        "requires_split_after": True,
    },
    {
        "id": "DL-TFIDF-BEFORE-SPLIT",
        "name": "TF-IDF / text vectorizer fitted before split",
        "severity": Severity.CRITICAL,
        "description": "Text vectorizers fitted on full corpus before splitting leak vocabulary and IDF weights from test documents.",
        "regex": r"(TfidfVectorizer|CountVectorizer|HashingVectorizer)\s*\(",
        "requires_split_after": True,
    },

    # ═══════════════════════════════════════
    # TRAIN/TEST SPLIT ERRORS (TS)
    # ═══════════════════════════════════════
    {
        "id": "TS-NO-SPLIT",
        "name": "No train/test split detected",
        "severity": Severity.HIGH,
        "description": "No train_test_split or manual splitting found. Model may be evaluated on training data.",
        "regex": None,
        "check_absence": r"(train_test_split|\.split|X_train|x_train|X_test|x_test|cross_val|KFold|StratifiedKFold|TimeSeriesSplit)",
    },
    {
        "id": "TS-SHUFFLE-TIMESERIES",
        "name": "Shuffling time-series data",
        "severity": Severity.HIGH,
        "description": "shuffle=True on data that may be temporal. Future data could leak into training set.",
        "regex": r"train_test_split\s*\([^)]*shuffle\s*=\s*True",
    },
    {
        "id": "TS-NO-RANDOM-STATE",
        "name": "No random_state in split",
        "severity": Severity.MEDIUM,
        "description": "train_test_split without random_state makes results non-reproducible across runs.",
        "regex": r"train_test_split\s*\([^)]*\)(?!.*random_state)",
    },
    {
        "id": "TS-NO-STRATIFY",
        "name": "Classification split without stratification",
        "severity": Severity.MEDIUM,
        "description": "train_test_split without stratify= on classification tasks can create unbalanced test sets that misrepresent real-world performance.",
        "regex": r"train_test_split\s*\([^)]*\)(?!.*stratify)",
        "requires_classification": True,
    },
    {
        "id": "TS-TINY-TEST-SIZE",
        "name": "Very small test set",
        "severity": Severity.MEDIUM,
        "description": "Test size below 15% leaves too few samples for reliable evaluation. Standard is 20-30%.",
        "regex": r"test_size\s*=\s*(0\.0[0-9]|0\.1[0-4])\b",
    },
    {
        "id": "TS-HUGE-TEST-SIZE",
        "name": "Very large test set (>50%)",
        "severity": Severity.MEDIUM,
        "description": "Test size above 50% leaves too few training samples. The model won't learn enough patterns.",
        "regex": r"test_size\s*=\s*(0\.[5-9]|[1-9]\.)",
    },

    # ═══════════════════════════════════════
    # OVERFITTING (OF)
    # ═══════════════════════════════════════
    {
        "id": "OF-NO-REGULARIZATION",
        "name": "No regularization detected",
        "severity": Severity.MEDIUM,
        "description": "No L1/L2 regularization, dropout, or early stopping found. Model may memorize training data.",
        "regex": None,
        "check_absence": r"(regulariz|l1_ratio|l2|dropout|Dropout|early_stop|EarlyStopping|Ridge|Lasso|ElasticNet|weight_decay|penalty|alpha\s*=)",
    },
    {
        "id": "OF-NO-VALIDATION",
        "name": "No validation or cross-validation",
        "severity": Severity.HIGH,
        "description": "No validation set or cross-validation detected. You have no way to detect overfitting during training.",
        "regex": None,
        "check_absence": r"(validation|val_|cross_val|cv\s*=|KFold|StratifiedKFold|validation_split|eval_set|valid_|dev_set)",
    },
    {
        "id": "OF-DEEP-NO-DROPOUT",
        "name": "Deep neural network without dropout",
        "severity": Severity.HIGH,
        "description": "Neural network layers detected without any dropout layers. High overfitting risk on small/medium datasets.",
        "regex": r"(Dense|Linear|Conv[12]d|LSTM|GRU)\s*\(",
        "requires_absence": r"(Dropout|dropout|BatchNorm|batch_norm|LayerNorm)",
    },
    {
        "id": "OF-TREE-NO-DEPTH-LIMIT",
        "name": "Decision tree / forest with no max_depth",
        "severity": Severity.MEDIUM,
        "description": "Tree-based model without max_depth constraint can grow until perfectly memorizing training data.",
        "regex": r"(DecisionTree|RandomForest|GradientBoosting|ExtraTrees)(Classifier|Regressor)\s*\([^)]*\)(?!.*max_depth)",
    },
    {
        "id": "OF-HIGH-EPOCHS-NO-EARLYSTOP",
        "name": "High epoch count without early stopping",
        "severity": Severity.MEDIUM,
        "description": "Training for many epochs without early stopping risks overfitting as the model memorizes training noise.",
        "regex": r"epochs?\s*=\s*([5-9]\d{2,}|[1-9]\d{3,})",
        "requires_absence": r"(EarlyStopping|early_stop|patience)",
    },

    # ═══════════════════════════════════════
    # FEATURE MISUSE (FM)
    # ═══════════════════════════════════════
    {
        "id": "FM-TARGET-IN-FEATURES",
        "name": "Potential target leakage in features",
        "severity": Severity.CRITICAL,
        "description": "The target column may still be present in the feature set, giving near-perfect but useless predictions.",
        "regex": r"\.drop\s*\(\s*['\"](?:target|label|y|class|output)['\"]",
        "context_check": True,
    },
    {
        "id": "FM-ID-IN-FEATURES",
        "name": "ID column likely used as feature",
        "severity": Severity.HIGH,
        "description": "Columns named 'id', 'index', 'uuid' should not be features — they're unique identifiers with no predictive value but can cause overfitting.",
        "regex": r"""['\"](?:id|index|uuid|row_?num|record_?id|pk|key)['\"]""",
    },
    {
        "id": "FM-FUTURE-FEATURE",
        "name": "Potential future-looking feature",
        "severity": Severity.HIGH,
        "description": "Columns like 'outcome', 'result', 'revenue', 'profit' may not be available at prediction time — using them is label leakage.",
        "regex": r"""['\"](?:outcome|result|revenue|profit|total_sales|final_|post_)['\"]""",
    },

    # ═══════════════════════════════════════
    # PREPROCESSING ERRORS (PE)
    # ═══════════════════════════════════════
    {
        "id": "PE-NO-NULL-HANDLING",
        "name": "No missing value handling",
        "severity": Severity.MEDIUM,
        "description": "No null/NaN handling detected. Missing values may cause silent errors, biased results, or model crashes.",
        "regex": None,
        "check_absence": r"(dropna|fillna|isnull|isna|notna|notnull|SimpleImputer|impute|missing|KNNImputer)",
    },
    {
        "id": "PE-FIT-TRANSFORM-ON-TEST",
        "name": "fit_transform() called on test data",
        "severity": Severity.CRITICAL,
        "description": "Using fit_transform on test/validation data recomputes statistics from test data, invalidating everything.",
        "regex": r"(X_test|x_test|test_data|val_data|X_val).*\.?fit_transform",
    },
    {
        "id": "PE-LABEL-ENCODE-ORDINAL",
        "name": "LabelEncoder used on features (not target)",
        "severity": Severity.MEDIUM,
        "description": "LabelEncoder creates arbitrary ordinal relationships between categories. Use OneHotEncoder or OrdinalEncoder instead.",
        "regex": r"LabelEncoder\(\)\.fit_transform\s*\(\s*(X|data|df|features|train)",
    },
    {
        "id": "PE-NO-SCALING",
        "name": "No feature scaling detected",
        "severity": Severity.MEDIUM,
        "description": "No StandardScaler / MinMaxScaler / normalize. Many models (SVM, KNN, neural nets, logistic regression) require scaled features.",
        "regex": None,
        "check_absence": r"(StandardScaler|MinMaxScaler|RobustScaler|normalize|Normalizer|MaxAbsScaler|scale\()",
        "requires_presence": r"(SVM|SVC|SVR|KNeighbors|LogisticRegression|MLPClassifier|Dense|Linear|nn\.Module|SGDClassifier)",
    },

    # ═══════════════════════════════════════
    # GRADIENT / TRAINING INSTABILITY (GI)
    # ═══════════════════════════════════════
    {
        "id": "GI-HIGH-LEARNING-RATE",
        "name": "Suspiciously high learning rate",
        "severity": Severity.HIGH,
        "description": "Learning rate ≥1.0 will almost certainly cause loss to diverge. Standard range is 1e-4 to 1e-2.",
        "regex": r"(?:lr|learning_rate)\s*=\s*([1-9]\d*\.?\d*|0\.[5-9]\d*)",
    },
    {
        "id": "GI-TINY-LEARNING-RATE",
        "name": "Very small learning rate",
        "severity": Severity.LOW,
        "description": "Learning rate below 1e-6 means training will be extremely slow and may get stuck in suboptimal solutions.",
        "regex": r"(?:lr|learning_rate)\s*=\s*(1e-[7-9]|1e-\d{2,}|0\.0{6,})",
    },
    {
        "id": "GI-NO-GRADIENT-CLIP",
        "name": "RNN/LSTM without gradient clipping",
        "severity": Severity.MEDIUM,
        "description": "Recurrent networks (LSTM, GRU) are prone to exploding gradients. Gradient clipping is essential.",
        "regex": r"(LSTM|GRU|RNN)\s*\(",
        "requires_absence": r"(clip_grad|grad_clip|max_norm|clipnorm|clipvalue|gradient_clip)",
    },
    {
        "id": "GI-NO-BATCHNORM",
        "name": "Deep network without batch/layer normalization",
        "severity": Severity.LOW,
        "description": "Deep networks (>3 layers) without normalization layers train slower and are less stable.",
        "regex": None,
        "check_deep_no_norm": True,
    },
    {
        "id": "GI-EVAL-MODE-MISSING",
        "name": "PyTorch model not set to eval() for inference",
        "severity": Severity.HIGH,
        "description": "In PyTorch, not calling model.eval() before inference keeps dropout and batch norm in training mode, giving wrong predictions.",
        "regex": r"with\s+torch\.\s*no_grad",
        "requires_presence": r"import\s+torch|from\s+torch",
        "requires_absence": r"\.eval\s*\(",
    },

    # ═══════════════════════════════════════
    # EVALUATION & METRIC ERRORS (EV)
    # ═══════════════════════════════════════
    {
        "id": "EV-ACCURACY-IMBALANCED",
        "name": "Using accuracy on imbalanced data",
        "severity": Severity.HIGH,
        "description": "Accuracy is misleading on imbalanced datasets. A model predicting only the majority class gets high accuracy. Use F1, precision, recall, or AUC.",
        "regex": r"accuracy_score|['\"]accuracy['\"]|scoring\s*=\s*['\"]accuracy['\"]",
        "requires_absence": r"(f1_score|precision_score|recall_score|roc_auc|balanced_accuracy|classification_report|confusion_matrix)",
    },
    {
        "id": "EV-TRAIN-SCORE-ONLY",
        "name": "Scoring on training data only",
        "severity": Severity.HIGH,
        "description": "model.score(X_train, y_train) measures memorization, not generalization. Always evaluate on held-out data.",
        "regex": r"\.score\s*\(\s*(X_train|x_train|train_X)",
        "requires_absence": r"\.score\s*\(\s*(X_test|x_test|test_X|X_val|val_X)",
    },
    {
        "id": "EV-NO-METRICS",
        "name": "No evaluation metrics computed",
        "severity": Severity.MEDIUM,
        "description": "No scoring or evaluation metrics found. Without metrics, you have no idea if the model works.",
        "regex": None,
        "check_absence": r"(accuracy|precision|recall|f1|roc_auc|score|confusion_matrix|classification_report|mean_squared|r2_score|mae|mse|log_loss|evaluate)",
    },
    {
        "id": "EV-R2-NEGATIVE-POSSIBLE",
        "name": "Using R² without understanding it can be negative",
        "severity": Severity.LOW,
        "description": "R² score can be negative (worse than predicting the mean). Always check the actual value, not just that it exists.",
        "regex": r"r2_score",
    },

    # ═══════════════════════════════════════
    # RESOURCE & PERFORMANCE (RP)
    # ═══════════════════════════════════════
    {
        "id": "RP-NO-RANDOM-SEED",
        "name": "No global random seed set",
        "severity": Severity.LOW,
        "description": "No random seed set (numpy, torch, random, tensorflow). Results won't be reproducible.",
        "regex": None,
        "check_absence": r"(random\.seed|np\.random\.seed|torch\.manual_seed|tf\.random\.set_seed|set_random_seed|random_state|SEED|RANDOM_SEED)",
    },
    {
        "id": "RP-GPU-NO-DEVICE",
        "name": "PyTorch model without device management",
        "severity": Severity.MEDIUM,
        "description": "PyTorch code without .to(device) or .cuda(). Model may run on CPU when GPU is available, wasting time.",
        "regex": r"(nn\.Module|torch\.nn|nn\.Linear|nn\.Conv)",
        "requires_absence": r"(\.to\(|\.cuda\(\)|device\s*=|torch\.device)",
    },
    {
        "id": "RP-PANDAS-INPLACE-CHAIN",
        "name": "Pandas chained assignment warning risk",
        "severity": Severity.LOW,
        "description": "Setting values on a copy of a slice can silently fail. Use .loc[] for safe assignment.",
        "regex": r"\[.*\]\[.*\]\s*=",
    },
]


def scan_code(code: str) -> list[PatternFlag]:
    """Run all pattern checks against the provided code.

    Returns a list of PatternFlag objects for issues found.
    """
    flags: list[PatternFlag] = []
    lines = code.split("\n")

    # Pre-compute line positions for common patterns
    split_line = _find_split_line(code, lines)
    has_model_fit = bool(re.search(r"\.(fit|train|compile)\s*\(", code))

    for pattern in PATTERNS:
        result = _check_pattern(pattern, code, lines, split_line, has_model_fit)
        if result:
            flags.extend(result)

    # Deduplicate: same pattern_id should appear at most once
    seen_ids: set[str] = set()
    deduped = []
    for f in flags:
        if f.pattern_id not in seen_ids:
            seen_ids.add(f.pattern_id)
            deduped.append(f)

    return deduped


def _find_split_line(code: str, lines: list[str]) -> int | None:
    """Find the line number where train_test_split is called."""
    for i, line in enumerate(lines, 1):
        if re.search(r"train_test_split\s*\(", line):
            return i
    return None


def _count_layer_definitions(code: str) -> int:
    """Count how many NN layer definitions (Dense, Linear, Conv, etc.) appear."""
    return len(re.findall(r"(Dense|Linear|Conv[12]d|LSTM|GRU|TransformerEncoder)\s*\(", code, re.IGNORECASE))


def _check_pattern(
    pattern: dict,
    code: str,
    lines: list[str],
    split_line: int | None,
    has_model_fit: bool,
) -> list[PatternFlag] | None:
    """Check a single pattern definition against the code."""

    # Skip patterns that require a model fit if there's no model training
    if pattern.get("requires_classification"):
        if not re.search(r"(Classifier|LogisticRegression|SVC\b|categorical_crossentropy|cross_entropy|softmax)", code, re.IGNORECASE):
            return None

    # ── Deep network without normalization (custom check) ──
    if pattern.get("check_deep_no_norm"):
        n_layers = _count_layer_definitions(code)
        if n_layers >= 4:
            has_norm = bool(re.search(r"(BatchNorm|LayerNorm|GroupNorm|InstanceNorm|batch_norm|layer_norm)", code, re.IGNORECASE))
            if not has_norm:
                return [
                    PatternFlag(
                        pattern_id=pattern["id"],
                        pattern_name=pattern["name"],
                        severity=pattern["severity"],
                        description=f"{pattern['description']} ({n_layers} layers found, 0 normalization layers)",
                        confidence=0.7,
                    )
                ]
        return None

    # ── Conditional absence check: only flag if pattern is missing AND a trigger is present ──
    if pattern.get("requires_presence"):
        trigger = pattern["requires_presence"]
        if not re.search(trigger, code, re.IGNORECASE):
            return None  # Trigger not present, skip this check

    # ── Absence check: flag if pattern is NOT found ──
    if "check_absence" in pattern and pattern.get("regex") is None:
        if not re.search(pattern["check_absence"], code, re.IGNORECASE):
            # Only flag if there's actually ML code worth checking
            if has_model_fit or re.search(r"(import\s+sklearn|import\s+torch|import\s+tensorflow|import\s+keras|import\s+xgboost|import\s+lightgbm)", code):
                return [
                    PatternFlag(
                        pattern_id=pattern["id"],
                        pattern_name=pattern["name"],
                        severity=pattern["severity"],
                        description=pattern["description"],
                        confidence=0.7,
                    )
                ]
        return None

    # ── Regex match with split ordering check ──
    if pattern.get("regex"):
        matches = []
        for i, line in enumerate(lines, 1):
            # Skip comments
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue

            if re.search(pattern["regex"], line, re.IGNORECASE):
                # If this pattern requires a split to come AFTER it
                if pattern.get("requires_split_after"):
                    if split_line is not None and i < split_line:
                        matches.append(
                            PatternFlag(
                                pattern_id=pattern["id"],
                                pattern_name=pattern["name"],
                                severity=pattern["severity"],
                                description=pattern["description"],
                                line_number=i,
                                matched_code=line.strip(),
                                confidence=0.9,
                            )
                        )
                elif pattern.get("requires_absence"):
                    if not re.search(pattern["requires_absence"], code, re.IGNORECASE):
                        matches.append(
                            PatternFlag(
                                pattern_id=pattern["id"],
                                pattern_name=pattern["name"],
                                severity=pattern["severity"],
                                description=pattern["description"],
                                line_number=i,
                                matched_code=line.strip(),
                                confidence=0.75,
                            )
                        )
                else:
                    matches.append(
                        PatternFlag(
                            pattern_id=pattern["id"],
                            pattern_name=pattern["name"],
                            severity=pattern["severity"],
                            description=pattern["description"],
                            line_number=i,
                            matched_code=line.strip(),
                            confidence=0.8,
                        )
                    )
        return matches if matches else None

    return None


def format_flags_for_prompt(flags: list[PatternFlag]) -> str:
    """Format pattern flags into a readable string for the LLM prompt."""
    if not flags:
        return "No suspicious patterns detected by static analysis."

    lines = []
    for flag in flags:
        loc = f" (line {flag.line_number})" if flag.line_number else ""
        code = f" → `{flag.matched_code}`" if flag.matched_code else ""
        lines.append(
            f"[{flag.severity.value}] {flag.pattern_name}{loc}{code}\n"
            f"  {flag.description} (confidence: {flag.confidence:.0%})"
        )

    header = f"Static scanner found {len(flags)} potential issue(s):"
    return header + "\n" + "\n".join(lines)
