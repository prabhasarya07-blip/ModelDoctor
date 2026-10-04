/* ────────────────────────────────────────
   Layer 1: Static Pattern Scanner.
   Port of services/pattern_scanner.py — regex heuristics, <10ms.
   ──────────────────────────────────────── */

import { QuickScanFlag, Severity } from "@/lib/types";

export interface PatternDef {
  id: string;
  name: string;
  severity: Severity;
  description: string;
  /** Matched per-line, case-insensitive. */
  regex?: RegExp;
  /** Flag only when this is NOT found anywhere in the code. */
  checkAbsence?: RegExp;
  /** Only evaluate `checkAbsence` when this IS found. */
  requiresPresence?: RegExp;
  /** Flag only when this is NOT found. */
  requiresAbsence?: RegExp;
  /** Only apply to classification code. */
  requiresClassification?: boolean;
  /** Custom check: >=4 NN layers and no normalization layers. */
  checkDeepNoNorm?: boolean;
  /** Only flag when the match appears BEFORE the train/test split. */
  requiresSplitAfter?: boolean;
}

const rx = (source: string) => new RegExp(source, "i");

export const PATTERNS: PatternDef[] = [
  /* ── Data leakage ── */
  { id: "DL-SCALE-BEFORE-SPLIT", name: "Scaler fitted before train/test split", severity: "CRITICAL",
    description: "StandardScaler/MinMaxScaler/RobustScaler fitted on full dataset before split. Test data statistics leak into training.",
    regex: rx("(fit_transform|\\.fit)\\s*\\(\\s*(X|data|df|features)"), requiresSplitAfter: true },
  { id: "DL-ENCODE-BEFORE-SPLIT", name: "Encoding applied before train/test split", severity: "CRITICAL",
    description: "Label encoding or one-hot encoding applied to full dataset before splitting. Category mappings leak from test to train.",
    regex: rx("(LabelEncoder|OneHotEncoder|OrdinalEncoder|get_dummies)\\s*\\("), requiresSplitAfter: true },
  { id: "DL-IMPUTE-BEFORE-SPLIT", name: "Imputation before train/test split", severity: "HIGH",
    description: "Missing value imputation on full dataset before splitting leaks test distribution into training.",
    regex: rx("(SimpleImputer|fillna|interpolate|KNNImputer)\\s*\\("), requiresSplitAfter: true },
  { id: "DL-PCA-BEFORE-SPLIT", name: "Dimensionality reduction before split", severity: "CRITICAL",
    description: "PCA/SVD/feature selection fitted on full dataset before split. Components capture test data variance.",
    regex: rx("(PCA|TruncatedSVD|SelectKBest|VarianceThreshold|TSNE|UMAP)\\s*\\("), requiresSplitAfter: true },
  { id: "DL-SMOTE-BEFORE-SPLIT", name: "SMOTE/oversampling before train/test split", severity: "CRITICAL",
    description: "Synthetic samples generated from full dataset may create test-like training samples, causing massive leakage.",
    regex: rx("(SMOTE|RandomOverSampler|ADASYN|BorderlineSMOTE)\\s*\\("), requiresSplitAfter: true },
  { id: "DL-FEATURE-SELECT-BEFORE-SPLIT", name: "Feature selection using target before split", severity: "CRITICAL",
    description: "Selecting features using correlation with target on full dataset leaks test relationships into feature selection.",
    regex: rx("(SelectKBest|mutual_info_classif|chi2|f_classif|f_regression)\\s*\\("), requiresSplitAfter: true },
  { id: "DL-TFIDF-BEFORE-SPLIT", name: "TF-IDF / text vectorizer fitted before split", severity: "CRITICAL",
    description: "Text vectorizers fitted on full corpus before splitting leak vocabulary and IDF weights from test documents.",
    regex: rx("(TfidfVectorizer|CountVectorizer|HashingVectorizer)\\s*\\("), requiresSplitAfter: true },

  /* ── Train/test split ── */
  { id: "TS-NO-SPLIT", name: "No train/test split detected", severity: "HIGH",
    description: "No train_test_split or manual splitting found. Model may be evaluated on training data.",
    checkAbsence: rx("(train_test_split|\\.split|X_train|x_train|X_test|x_test|cross_val|KFold|StratifiedKFold|TimeSeriesSplit)") },
  { id: "TS-SHUFFLE-TIMESERIES", name: "Shuffling time-series data", severity: "HIGH",
    description: "shuffle=True on data that may be temporal. Future data could leak into training set.",
    regex: rx("train_test_split\\s*\\([^)]*shuffle\\s*=\\s*True") },
  { id: "TS-NO-RANDOM-STATE", name: "No random_state in split", severity: "MEDIUM",
    description: "train_test_split without random_state makes results non-reproducible across runs.",
    regex: rx("train_test_split\\s*\\([^)]*\\)(?!.*random_state)") },
  { id: "TS-NO-STRATIFY", name: "Classification split without stratification", severity: "MEDIUM",
    description: "train_test_split without stratify= on classification tasks can create unbalanced test sets that misrepresent real-world performance.",
    regex: rx("train_test_split\\s*\\([^)]*\\)(?!.*stratify)"), requiresClassification: true },
  { id: "TS-TINY-TEST-SIZE", name: "Very small test set", severity: "MEDIUM",
    description: "Test size below 15% leaves too few samples for reliable evaluation. Standard is 20-30%.",
    regex: rx("test_size\\s*=\\s*(0\\.0[0-9]|0\\.1[0-4])\\b") },
  { id: "TS-HUGE-TEST-SIZE", name: "Very large test set (>50%)", severity: "MEDIUM",
    description: "Test size above 50% leaves too few training samples. The model won't learn enough patterns.",
    regex: rx("test_size\\s*=\\s*(0\\.[5-9]|[1-9]\\.)") },

  /* ── Overfitting ── */
  { id: "OF-NO-REGULARIZATION", name: "No regularization detected", severity: "MEDIUM",
    description: "No L1/L2 regularization, dropout, or early stopping found. Model may memorize training data.",
    checkAbsence: rx("(regulariz|l1_ratio|l2|dropout|Dropout|early_stop|EarlyStopping|Ridge|Lasso|ElasticNet|weight_decay|penalty|alpha\\s*=)") },
  { id: "OF-NO-VALIDATION", name: "No validation or cross-validation", severity: "HIGH",
    description: "No validation set or cross-validation detected. You have no way to detect overfitting during training.",
    checkAbsence: rx("(validation|val_|cross_val|cv\\s*=|KFold|StratifiedKFold|validation_split|eval_set|valid_|dev_set)") },
  { id: "OF-DEEP-NO-DROPOUT", name: "Deep neural network without dropout", severity: "HIGH",
    description: "Neural network layers detected without any dropout layers. High overfitting risk on small/medium datasets.",
    regex: rx("(Dense|Linear|Conv[12]d|LSTM|GRU)\\s*\\("),
    requiresAbsence: rx("(Dropout|dropout|BatchNorm|batch_norm|LayerNorm)") },
  { id: "OF-TREE-NO-DEPTH-LIMIT", name: "Decision tree / forest with no max_depth", severity: "MEDIUM",
    description: "Tree-based model without max_depth constraint can grow until perfectly memorizing training data.",
    regex: rx("(DecisionTree|RandomForest|GradientBoosting|ExtraTrees)(Classifier|Regressor)\\s*\\([^)]*\\)(?!.*max_depth)") },
  { id: "OF-HIGH-EPOCHS-NO-EARLYSTOP", name: "High epoch count without early stopping", severity: "MEDIUM",
    description: "Training for many epochs without early stopping risks overfitting as the model memorizes training noise.",
    regex: rx("epochs?\\s*=\\s*([5-9]\\d{2,}|[1-9]\\d{3,})"),
    requiresAbsence: rx("(EarlyStopping|early_stop|patience)") },

  /* ── Feature misuse ── */
  { id: "FM-TARGET-IN-FEATURES", name: "Potential target leakage in features", severity: "CRITICAL",
    description: "The target column may still be present in the feature set, giving near-perfect but useless predictions.",
    regex: rx("\\.drop\\s*\\(\\s*['\\\"](?:target|label|y|class|output)['\\\"]") },
  { id: "FM-ID-IN-FEATURES", name: "ID column likely used as feature", severity: "HIGH",
    description: "Columns named 'id', 'index', 'uuid' should not be features — they're unique identifiers with no predictive value but can cause overfitting.",
    regex: rx("['\\\"](?:id|index|uuid|row_?num|record_?id|pk|key)['\\\"]") },
  { id: "FM-FUTURE-FEATURE", name: "Potential future-looking feature", severity: "HIGH",
    description: "Columns like 'outcome', 'result', 'revenue', 'profit' may not be available at prediction time — using them is label leakage.",
    regex: rx("['\\\"](?:outcome|result|revenue|profit|total_sales|final_|post_)['\\\"]") },

  /* ── Preprocessing ── */
  { id: "PE-NO-NULL-HANDLING", name: "No missing value handling", severity: "MEDIUM",
    description: "No null/NaN handling detected. Missing values may cause silent errors, biased results, or model crashes.",
    checkAbsence: rx("(dropna|fillna|isnull|isna|notna|notnull|SimpleImputer|impute|missing|KNNImputer)") },
  { id: "PE-FIT-TRANSFORM-ON-TEST", name: "fit_transform() called on test data", severity: "CRITICAL",
    description: "Using fit_transform on test/validation data recomputes statistics from test data, invalidating everything.",
    regex: rx("(X_test|x_test|test_data|val_data|X_val).*\\.?fit_transform") },
  { id: "PE-LABEL-ENCODE-ORDINAL", name: "LabelEncoder used on features (not target)", severity: "MEDIUM",
    description: "LabelEncoder creates arbitrary ordinal relationships between categories. Use OneHotEncoder or OrdinalEncoder instead.",
    regex: rx("LabelEncoder\\(\\)\\.fit_transform\\s*\\(\\s*(X|data|df|features|train)") },
  { id: "PE-NO-SCALING", name: "No feature scaling detected", severity: "MEDIUM",
    description: "No StandardScaler / MinMaxScaler / normalize. Many models (SVM, KNN, neural nets, logistic regression) require scaled features.",
    checkAbsence: rx("(StandardScaler|MinMaxScaler|RobustScaler|normalize|Normalizer|MaxAbsScaler|scale\\()"),
    requiresPresence: rx("(SVM|SVC|SVR|KNeighbors|LogisticRegression|MLPClassifier|Dense|Linear|nn\\.Module|SGDClassifier)") },

  /* ── Gradient / training instability ── */
  { id: "GI-HIGH-LEARNING-RATE", name: "Suspiciously high learning rate", severity: "HIGH",
    description: "Learning rate >=1.0 will almost certainly cause loss to diverge. Standard range is 1e-4 to 1e-2.",
    regex: rx("(?:lr|learning_rate)\\s*=\\s*([1-9]\\d*\\.?\\d*|0\\.[5-9]\\d*)") },
  { id: "GI-TINY-LEARNING-RATE", name: "Very small learning rate", severity: "LOW",
    description: "Learning rate below 1e-6 means training will be extremely slow and may get stuck in suboptimal solutions.",
    regex: rx("(?:lr|learning_rate)\\s*=\\s*(1e-[7-9]|1e-\\d{2,}|0\\.0{6,})") },
  { id: "GI-NO-GRADIENT-CLIP", name: "RNN/LSTM without gradient clipping", severity: "MEDIUM",
    description: "Recurrent networks (LSTM, GRU) are prone to exploding gradients. Gradient clipping is essential.",
    regex: rx("(LSTM|GRU|RNN)\\s*\\("),
    requiresAbsence: rx("(clip_grad|grad_clip|max_norm|clipnorm|clipvalue|gradient_clip)") },
  { id: "GI-NO-BATCHNORM", name: "Deep network without batch/layer normalization", severity: "LOW",
    description: "Deep networks (>3 layers) without normalization layers train slower and are less stable.",
    checkDeepNoNorm: true },
  { id: "GI-EVAL-MODE-MISSING", name: "PyTorch model not set to eval() for inference", severity: "HIGH",
    description: "In PyTorch, not calling model.eval() before inference keeps dropout and batch norm in training mode, giving wrong predictions.",
    regex: rx("with\\s+torch\\.\\s*no_grad"),
    requiresPresence: rx("import\\s+torch|from\\s+torch"),
    requiresAbsence: rx("\\.eval\\s*\\(") },

  /* ── Evaluation ── */
  { id: "EV-ACCURACY-IMBALANCED", name: "Using accuracy on imbalanced data", severity: "HIGH",
    description: "Accuracy is misleading on imbalanced datasets. A model predicting only the majority class gets high accuracy. Use F1, precision, recall, or AUC.",
    regex: rx("accuracy_score|['\\\"]accuracy['\\\"]|scoring\\s*=\\s*['\\\"]accuracy['\\\"]"),
    requiresAbsence: rx("(f1_score|precision_score|recall_score|roc_auc|balanced_accuracy|classification_report|confusion_matrix)") },
  { id: "EV-TRAIN-SCORE-ONLY", name: "Scoring on training data only", severity: "HIGH",
    description: "model.score(X_train, y_train) measures memorization, not generalization. Always evaluate on held-out data.",
    regex: rx("\\.score\\s*\\(\\s*(X_train|x_train|train_X)"),
    requiresAbsence: rx("\\.score\\s*\\(\\s*(X_test|x_test|test_X|X_val|val_X)") },
  { id: "EV-NO-METRICS", name: "No evaluation metrics computed", severity: "MEDIUM",
    description: "No scoring or evaluation metrics found. Without metrics, you have no idea if the model works.",
    checkAbsence: rx("(accuracy|precision|recall|f1|roc_auc|score|confusion_matrix|classification_report|mean_squared|r2_score|mae|mse|log_loss|evaluate)") },
  { id: "EV-R2-NEGATIVE-POSSIBLE", name: "Using R² without understanding it can be negative", severity: "LOW",
    description: "R² score can be negative (worse than predicting the mean). Always check the actual value, not just that it exists.",
    regex: rx("r2_score") },

  /* ── Resource & performance ── */
  { id: "RP-NO-RANDOM-SEED", name: "No global random seed set", severity: "LOW",
    description: "No random seed set (numpy, torch, random, tensorflow). Results won't be reproducible.",
    checkAbsence: rx("(random\\.seed|np\\.random\\.seed|torch\\.manual_seed|tf\\.random\\.set_seed|set_random_seed|random_state|SEED|RANDOM_SEED)") },
  { id: "RP-GPU-NO-DEVICE", name: "PyTorch model without device management", severity: "MEDIUM",
    description: "PyTorch code without .to(device) or .cuda(). Model may run on CPU when GPU is available, wasting time.",
    regex: rx("(nn\\.Module|torch\\.nn|nn\\.Linear|nn\\.Conv)"),
    requiresAbsence: rx("(\\.to\\(|\\.cuda\\(\\)|device\\s*=|torch\\.device)") },
  { id: "RP-PANDAS-INPLACE-CHAIN", name: "Pandas chained assignment warning risk", severity: "LOW",
    description: "Setting values on a copy of a slice can silently fail. Use .loc[] for safe assignment.",
    regex: rx("\\[.*\\]\\[.*\\]\\s*=") },
];

/* ── Scanner ── */

function findSplitLine(lines: string[]): number | null {
  for (let i = 0; i < lines.length; i++) {
    if (/train_test_split\s*\(/i.test(lines[i])) return i + 1;
  }
  return null;
}

function countLayerDefinitions(code: string): number {
  const matches = code.match(/(Dense|Linear|Conv[12]d|LSTM|GRU|TransformerEncoder)\s*\(/gi);
  return matches ? matches.length : 0;
}

const ML_IMPORT_RE = /import\s+sklearn|import\s+torch|import\s+tensorflow|import\s+keras|import\s+xgboost|import\s+lightgbm/i;

function checkPattern(
  pattern: PatternDef,
  code: string,
  lines: string[],
  splitLine: number | null,
  hasModelFit: boolean
): QuickScanFlag[] | null {
  if (pattern.requiresClassification) {
    if (!/(Classifier|LogisticRegression|SVC\b|categorical_crossentropy|cross_entropy|softmax)/i.test(code)) {
      return null;
    }
  }

  // Deep network without normalization
  if (pattern.checkDeepNoNorm) {
    const nLayers = countLayerDefinitions(code);
    if (nLayers >= 4) {
      const hasNorm = /(BatchNorm|LayerNorm|GroupNorm|InstanceNorm|batch_norm|layer_norm)/i.test(code);
      if (!hasNorm) {
        return [{
          pattern_id: pattern.id,
          pattern_name: pattern.name,
          severity: pattern.severity,
          description: `${pattern.description} (${nLayers} layers found, 0 normalization layers)`,
          line_number: null,
          matched_code: null,
          confidence: 0.7,
        }];
      }
    }
    return null;
  }

  // Conditional absence: only flag if the trigger is present
  if (pattern.requiresPresence && !pattern.requiresPresence.test(code)) {
    return null;
  }

  // Absence check: flag only if the pattern is NOT found
  if (pattern.checkAbsence && !pattern.regex) {
    if (!pattern.checkAbsence.test(code)) {
      if (hasModelFit || ML_IMPORT_RE.test(code)) {
        return [{
          pattern_id: pattern.id,
          pattern_name: pattern.name,
          severity: pattern.severity,
          description: pattern.description,
          line_number: null,
          matched_code: null,
          confidence: 0.7,
        }];
      }
    }
    return null;
  }

  // Regex match, line by line
  if (pattern.regex) {
    const matches: QuickScanFlag[] = [];
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const lineNo = i + 1;
      if (line.trimStart().startsWith("#")) continue;
      if (!pattern.regex.test(line)) continue;

      if (pattern.requiresSplitAfter) {
        if (splitLine !== null && lineNo < splitLine) {
          matches.push({
            pattern_id: pattern.id,
            pattern_name: pattern.name,
            severity: pattern.severity,
            description: pattern.description,
            line_number: lineNo,
            matched_code: line.trim(),
            confidence: 0.9,
          });
        }
      } else if (pattern.requiresAbsence) {
        if (!pattern.requiresAbsence.test(code)) {
          matches.push({
            pattern_id: pattern.id,
            pattern_name: pattern.name,
            severity: pattern.severity,
            description: pattern.description,
            line_number: lineNo,
            matched_code: line.trim(),
            confidence: 0.75,
          });
        }
      } else {
        matches.push({
          pattern_id: pattern.id,
          pattern_name: pattern.name,
          severity: pattern.severity,
          description: pattern.description,
          line_number: lineNo,
          matched_code: line.trim(),
          confidence: 0.8,
        });
      }
    }
    return matches.length ? matches : null;
  }

  return null;
}

/** Run all pattern checks. Each pattern_id is reported at most once. */
export function scanCode(code: string): QuickScanFlag[] {
  const flags: QuickScanFlag[] = [];
  const lines = code.split("\n");
  const splitLine = findSplitLine(lines);
  const hasModelFit = /\.(fit|train|compile)\s*\(/i.test(code);

  for (const pattern of PATTERNS) {
    try {
      const result = checkPattern(pattern, code, lines, splitLine, hasModelFit);
      if (result) flags.push(...result);
    } catch (err) {
      console.error(`Pattern ${pattern.id} failed:`, err);
    }
  }

  const seen = new Set<string>();
  return flags.filter((f) => {
    if (seen.has(f.pattern_id)) return false;
    seen.add(f.pattern_id);
    return true;
  });
}
