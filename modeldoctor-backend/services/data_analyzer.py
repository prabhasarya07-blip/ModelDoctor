"""Layer 2: Data Analyzer — Scans the actual dataset for issues.

This is ModelDoctor's secret weapon. ChatGPT cannot see your data.
ModelDoctor can. This layer reads a CSV/JSON file and cross-checks it
against the user's code to find issues no LLM alone could ever catch.

Enhanced analysis includes:
  - Dataset profiling (shape, dtypes, distributions, memory)
  - Code ↔ Data cross-checking (column names, types, case mismatches)
  - Data quality (class imbalance, missing values, duplicates, constants)
  - Statistical analysis (outliers, skewness, correlation, cardinality)
  - ML readiness scoring

Runs pure Python — no LLM needed. Instant results.
"""

from __future__ import annotations

import io
import re
import json
import logging
import math
from typing import Any, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger("modeldoctor")


# ─────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────


def analyze_dataset(
    file_content: bytes,
    filename: str,
    code: str,
) -> dict[str, Any]:
    """Analyze an uploaded dataset and cross-check against the user's code.

    Returns a structured analysis dict with:
      - dataset_profile: shape, columns, dtypes, memory, stats
      - cross_check_issues: mismatches between code and data
      - data_quality_issues: class imbalance, missing values, etc.
      - statistical_insights: correlations, outliers, skewness
      - data_summary_for_prompt: text block to feed into the LLM prompt
    """
    try:
        df = _load_dataframe(file_content, filename)
    except Exception as e:
        logger.error("Failed to load dataset: %s", e)
        return {
            "dataset_profile": None,
            "cross_check_issues": [],
            "data_quality_issues": [],
            "statistical_insights": {},
            "data_summary_for_prompt": f"[Dataset upload failed: {str(e)}]",
        }

    profile = _build_profile(df)
    cross_issues = _cross_check_code_vs_data(code, df)
    quality_issues = _check_data_quality(df, code)
    stats = _run_statistical_analysis(df, code)

    # Build the text summary that goes into the Gemini prompt
    prompt_text = _build_prompt_summary(profile, cross_issues, quality_issues, stats)

    return {
        "dataset_profile": profile,
        "cross_check_issues": cross_issues,
        "data_quality_issues": quality_issues,
        "statistical_insights": stats,
        "data_summary_for_prompt": prompt_text,
    }


# ─────────────────────────────────────────────
# Data Loading
# ─────────────────────────────────────────────


def _load_dataframe(content: bytes, filename: str) -> pd.DataFrame:
    """Load CSV or JSON into a pandas DataFrame."""
    fname_lower = filename.lower()

    if fname_lower.endswith(".csv"):
        return pd.read_csv(io.BytesIO(content), nrows=10000)  # cap at 10k rows for speed
    elif fname_lower.endswith(".json"):
        text = content.decode("utf-8")
        data = json.loads(text)
        if isinstance(data, list):
            return pd.DataFrame(data)
        elif isinstance(data, dict):
            # Try common JSON structures
            if "data" in data:
                return pd.DataFrame(data["data"])
            return pd.DataFrame([data]) if not any(isinstance(v, list) for v in data.values()) else pd.DataFrame(data)
        raise ValueError("JSON structure not recognized as tabular data")
    elif fname_lower.endswith((".xls", ".xlsx")):
        return pd.read_excel(io.BytesIO(content), nrows=10000)
    elif fname_lower.endswith(".tsv"):
        return pd.read_csv(io.BytesIO(content), sep="\t", nrows=10000)
    else:
        # Try CSV as default
        return pd.read_csv(io.BytesIO(content), nrows=10000)


# ─────────────────────────────────────────────
# Dataset Profiling
# ─────────────────────────────────────────────


def _build_profile(df: pd.DataFrame) -> dict[str, Any]:
    """Build a structural profile of the dataset."""
    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    # Detect potential datetime columns stored as strings
    potential_date_cols = []
    for col in cat_cols:
        sample = df[col].dropna().head(20).astype(str)
        date_patterns = [
            r"\d{4}-\d{2}-\d{2}",
            r"\d{2}/\d{2}/\d{4}",
            r"\d{2}-\d{2}-\d{4}",
        ]
        if any(sample.str.match(pat).any() for pat in date_patterns):
            potential_date_cols.append(col)

    # Detect potential target columns
    potential_targets = _detect_target_columns(df)

    return {
        "shape": {"rows": int(df.shape[0]), "cols": int(df.shape[1])},
        "columns": df.columns.tolist(),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "numeric_columns": num_cols,
        "categorical_columns": cat_cols,
        "datetime_columns": datetime_cols + potential_date_cols,
        "missing_values": {col: int(count) for col, count in df.isnull().sum().items() if count > 0},
        "missing_pct": {col: round(count / len(df) * 100, 1) for col, count in df.isnull().sum().items() if count > 0},
        "potential_targets": potential_targets,
        "memory_mb": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
        "duplicate_rows": int(df.duplicated().sum()),
        "duplicate_pct": round(df.duplicated().sum() / len(df) * 100, 1) if len(df) > 0 else 0,
    }


def _detect_target_columns(df: pd.DataFrame) -> list[dict[str, Any]]:
    """Detect likely target/label columns."""
    targets = []
    target_names = {"target", "label", "y", "class", "outcome", "result", "is_", "has_", "flag"}

    for col in df.columns:
        col_lower = col.lower().strip()
        is_target_name = any(t in col_lower for t in target_names)
        n_unique = df[col].nunique()

        if is_target_name or (n_unique <= 20 and n_unique >= 2 and df[col].dtype in ["int64", "float64", "object", "bool"]):
            distribution = df[col].value_counts(normalize=True).to_dict()
            # Convert keys to strings for JSON serialization
            distribution = {str(k): round(v * 100, 1) for k, v in list(distribution.items())[:10]}

            targets.append({
                "column": col,
                "n_unique": int(n_unique),
                "distribution": distribution,
                "likely_target": is_target_name,
            })

    return targets


# ─────────────────────────────────────────────
# Cross-Check: Code vs Data
# ─────────────────────────────────────────────


def _cross_check_code_vs_data(code: str, df: pd.DataFrame) -> list[dict[str, Any]]:
    """Find mismatches between what the code references and what the data contains."""
    issues = []
    actual_columns = set(df.columns.tolist())
    actual_columns_lower = {c.lower(): c for c in actual_columns}

    # 1. Extract column names referenced in code
    code_columns = _extract_column_references(code)

    for ref_col in code_columns:
        if ref_col not in actual_columns:
            # Check for case mismatch
            if ref_col.lower() in actual_columns_lower:
                actual_name = actual_columns_lower[ref_col.lower()]
                issues.append({
                    "type": "COLUMN_CASE_MISMATCH",
                    "severity": "CRITICAL",
                    "title": f"Column case mismatch: '{ref_col}' vs '{actual_name}'",
                    "detail": f"Your code references column '{ref_col}' but the dataset has '{actual_name}' (different case). "
                              f"This will cause a KeyError or silently produce wrong results depending on your pandas version.",
                    "code_reference": ref_col,
                    "data_reference": actual_name,
                })
            else:
                # Column doesn't exist at all
                # Find closest match
                close = _find_close_match(ref_col, actual_columns)
                msg = f"Your code references column '{ref_col}' but it does not exist in the dataset."
                if close:
                    msg += f" Did you mean '{close}'?"
                issues.append({
                    "type": "COLUMN_NOT_FOUND",
                    "severity": "CRITICAL",
                    "title": f"Column '{ref_col}' not found in dataset",
                    "detail": msg,
                    "code_reference": ref_col,
                    "data_reference": close,
                })

    # 2. Check if code treats numeric columns as categorical or vice versa
    for ref_col in code_columns:
        if ref_col in actual_columns:
            col_dtype = str(df[ref_col].dtype)
            # Check if code does .astype(int) on a string column
            if "object" in col_dtype:
                if re.search(rf"['\"]?{re.escape(ref_col)}['\"]?\s*\]\s*\.\s*astype\s*\(\s*(?:int|float)", code):
                    issues.append({
                        "type": "DTYPE_MISMATCH",
                        "severity": "HIGH",
                        "title": f"Type cast on non-numeric column '{ref_col}'",
                        "detail": f"Column '{ref_col}' contains text/object data but your code tries to convert it to a number. "
                                  f"This will crash or produce NaN values.",
                        "code_reference": ref_col,
                        "data_reference": col_dtype,
                    })

    return issues


def _extract_column_references(code: str) -> set[str]:
    """Extract column names referenced in Python ML code."""
    columns = set()

    # df['column_name'] or df["column_name"]
    for match in re.finditer(r"""(?:df|data|X|train|test|dataset)\[['"]([^'"]+)['"]\]""", code):
        columns.add(match.group(1))

    # df.column_name (attribute access) — harder, skip common methods
    pandas_methods = {"head", "tail", "describe", "info", "shape", "columns", "dtypes",
                      "dropna", "fillna", "drop", "merge", "groupby", "apply", "map",
                      "values", "index", "reset_index", "set_index", "copy", "to_csv",
                      "to_json", "read_csv", "read_json", "concat", "astype", "iloc",
                      "loc", "isnull", "notnull", "nunique", "value_counts", "plot",
                      "fit", "transform", "fit_transform", "predict", "score"}
    for match in re.finditer(r"(?:df|data)\.\s*([a-zA-Z_]\w*)", code):
        attr = match.group(1)
        if attr not in pandas_methods and not attr.startswith("_"):
            columns.add(attr)

    # Column lists: ['col1', 'col2']
    for match in re.finditer(r"""\[\s*['"]([^'"]+)['"](?:\s*,\s*['"]([^'"]+)['"])*\s*\]""", code):
        for g in match.groups():
            if g:
                columns.add(g)

    return columns


def _find_close_match(target: str, candidates: set[str]) -> Optional[str]:
    """Find the closest matching column name (simple edit distance)."""
    target_lower = target.lower()
    best = None
    best_score = float("inf")

    for c in candidates:
        # Simple similarity: number of differing chars
        c_lower = c.lower()
        if target_lower == c_lower:
            return c
        dist = _edit_distance(target_lower, c_lower)
        if dist < best_score and dist <= 3:  # max 3 edits
            best_score = dist
            best = c

    return best


def _edit_distance(s1: str, s2: str) -> int:
    """Simple Levenshtein edit distance."""
    if len(s1) < len(s2):
        return _edit_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev_row[j + 1] + 1
            deletions = curr_row[j] + 1
            substitutions = prev_row[j] + (c1 != c2)
            curr_row.append(min(insertions, deletions, substitutions))
        prev_row = curr_row
    return prev_row[-1]


# ─────────────────────────────────────────────
# Data Quality Checks
# ─────────────────────────────────────────────


def _check_data_quality(df: pd.DataFrame, code: str) -> list[dict[str, Any]]:
    """Check for data quality issues that affect ML training."""
    issues = []

    # 1. Class Imbalance Detection
    targets = _detect_target_columns(df)
    for t in targets:
        if t["likely_target"] and t["n_unique"] <= 10:
            dist = t["distribution"]
            values = list(dist.values())
            if len(values) >= 2:
                max_pct = max(values)
                min_pct = min(values)
                if max_pct > 80:  # >80% one class
                    # Check if code handles it
                    has_balance = bool(re.search(
                        r"(class_weight|sample_weight|SMOTE|oversamp|undersamp|balanced|StratifiedKFold|stratify)",
                        code, re.IGNORECASE
                    ))
                    if not has_balance:
                        issues.append({
                            "type": "CLASS_IMBALANCE",
                            "severity": "HIGH",
                            "title": f"Severe class imbalance in '{t['column']}' — no handling detected",
                            "detail": f"Target column '{t['column']}' has {max_pct:.0f}% majority class "
                                      f"and {min_pct:.0f}% minority class. Your code has no resampling, "
                                      f"class_weight, or stratified splitting. The model will likely just "
                                      f"predict the majority class and show high accuracy while being useless.",
                            "distribution": dist,
                        })

    # 2. Missing Values Warning
    total_missing = df.isnull().sum().sum()
    total_cells = df.shape[0] * df.shape[1]
    missing_pct = (total_missing / total_cells * 100) if total_cells > 0 else 0

    if missing_pct > 5:
        has_imputation = bool(re.search(
            r"(fillna|dropna|SimpleImputer|impute|interpolate|KNNImputer)",
            code, re.IGNORECASE
        ))
        if not has_imputation:
            issues.append({
                "type": "MISSING_VALUES_UNHANDLED",
                "severity": "HIGH",
                "title": f"{missing_pct:.1f}% missing values — no handling detected in code",
                "detail": f"Dataset has {total_missing:,} missing values ({missing_pct:.1f}% of all cells). "
                          f"Your code does not appear to handle missing values (no fillna, dropna, or imputer found). "
                          f"Many ML models will crash or produce NaN predictions with missing data.",
            })
    elif missing_pct > 0 and missing_pct <= 5:
        has_imputation = bool(re.search(
            r"(fillna|dropna|SimpleImputer|impute|interpolate|KNNImputer)",
            code, re.IGNORECASE
        ))
        if not has_imputation:
            issues.append({
                "type": "MISSING_VALUES_UNHANDLED",
                "severity": "MEDIUM",
                "title": f"{missing_pct:.1f}% missing values — no handling detected",
                "detail": f"Dataset has some missing values. While the percentage is low, "
                          f"not handling them may cause errors with certain models.",
            })

    # 3. Temporal Data + Random Split
    date_cols = []
    for col in df.columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in ["date", "time", "timestamp", "year", "month", "day", "created", "updated"]):
            date_cols.append(col)
    # Also check dtypes
    for col in df.select_dtypes(include=["datetime64"]).columns:
        if col not in date_cols:
            date_cols.append(col)

    if date_cols:
        has_random_split = bool(re.search(r"train_test_split", code))
        has_time_split = bool(re.search(
            r"(TimeSeriesSplit|sort.*date|sort.*time|iloc\[|\.tail|\.head)",
            code, re.IGNORECASE
        ))
        if has_random_split and not has_time_split:
            issues.append({
                "type": "TEMPORAL_LEAKAGE_RISK",
                "severity": "HIGH",
                "title": f"Temporal data detected but using random split",
                "detail": f"Your dataset contains date/time columns ({', '.join(date_cols)}) "
                          f"but your code uses train_test_split (random). This likely causes "
                          f"temporal leakage — the model trains on future data to predict the past. "
                          f"Use TimeSeriesSplit or sort by date and split chronologically.",
            })

    # 4. Dataset Size vs Model Complexity
    n_rows = df.shape[0]
    n_features = len(df.select_dtypes(include=[np.number]).columns)

    # Check if using deep learning on tiny data
    has_deep_learning = bool(re.search(
        r"(Sequential|Dense|Conv[12]D|LSTM|GRU|Transformer|nn\.Module|nn\.Linear|torch)",
        code, re.IGNORECASE
    ))
    if has_deep_learning and n_rows < 1000:
        issues.append({
            "type": "DATA_TOO_SMALL_FOR_MODEL",
            "severity": "HIGH",
            "title": f"Deep learning on tiny dataset ({n_rows} rows)",
            "detail": f"Your dataset has only {n_rows} rows but your code uses a deep learning model. "
                      f"Neural networks typically need thousands to millions of samples. "
                      f"With {n_rows} rows, the model will almost certainly overfit. "
                      f"Consider using simpler models (Random Forest, XGBoost, Logistic Regression).",
        })

    # High feature-to-sample ratio
    if n_features > 0 and n_rows > 0 and n_features > n_rows / 5:
        issues.append({
            "type": "HIGH_DIMENSIONALITY",
            "severity": "MEDIUM",
            "title": f"More features than samples ratio is concerning ({n_features} features, {n_rows} rows)",
            "detail": f"Your dataset has {n_features} numeric features for {n_rows} rows "
                      f"(ratio: {n_rows / n_features:.1f} samples per feature). "
                      f"This makes overfitting very likely. Consider feature selection or PCA.",
        })

    # 5. Duplicate Rows
    dup_count = df.duplicated().sum()
    dup_pct = (dup_count / len(df) * 100) if len(df) > 0 else 0
    if dup_pct > 5:
        issues.append({
            "type": "HIGH_DUPLICATE_ROWS",
            "severity": "MEDIUM",
            "title": f"{dup_pct:.1f}% duplicate rows detected ({dup_count:,} rows)",
            "detail": f"Your dataset has {dup_count:,} exact duplicate rows ({dup_pct:.1f}%). "
                      f"If duplicates span train/test split, the model effectively trains on test data. "
                      f"Consider deduplication before splitting.",
        })

    # 6. Constant Columns (zero variance)
    constant_cols = [col for col in df.columns if df[col].nunique() <= 1]
    if constant_cols:
        issues.append({
            "type": "CONSTANT_COLUMNS",
            "severity": "LOW",
            "title": f"{len(constant_cols)} constant column(s) detected",
            "detail": f"Columns {constant_cols[:5]} have only one unique value. "
                      f"They provide no information for learning and should be removed.",
        })

    # 7. Near-constant columns (>99% one value)
    for col in df.columns:
        if col in constant_cols:
            continue
        top_pct = df[col].value_counts(normalize=True).iloc[0] * 100 if df[col].nunique() > 0 else 0
        if top_pct > 99:
            issues.append({
                "type": "NEAR_CONSTANT_COLUMN",
                "severity": "LOW",
                "title": f"Column '{col}' is near-constant ({top_pct:.1f}% one value)",
                "detail": f"Column '{col}' has {top_pct:.1f}% of values being the same. "
                          f"This feature adds almost no information and can cause numerical instability.",
            })

    # 8. Very high cardinality categorical columns
    for col in df.select_dtypes(include=["object", "category"]).columns:
        n_unique = df[col].nunique()
        n_rows = len(df)
        if n_unique > n_rows * 0.5 and n_unique > 50:
            issues.append({
                "type": "HIGH_CARDINALITY",
                "severity": "MEDIUM",
                "title": f"Very high cardinality: '{col}' has {n_unique} unique values",
                "detail": f"Column '{col}' has {n_unique} unique values out of {n_rows} rows ({n_unique/n_rows*100:.0f}%). "
                          f"One-hot encoding would create {n_unique} columns. Consider target encoding, hashing, or dropping.",
            })

    # 9. Infinite values in numeric columns
    num_cols = df.select_dtypes(include=[np.number]).columns
    inf_cols = []
    for col in num_cols:
        inf_count = np.isinf(df[col]).sum()
        if inf_count > 0:
            inf_cols.append((col, int(inf_count)))
    if inf_cols:
        issues.append({
            "type": "INFINITE_VALUES",
            "severity": "HIGH",
            "title": f"Infinite values found in {len(inf_cols)} column(s)",
            "detail": f"Columns with inf values: {', '.join(f'{c} ({n})' for c, n in inf_cols)}. "
                      f"Infinite values will crash most ML algorithms. Replace with np.nan and impute.",
        })

    return issues


# ─────────────────────────────────────────────
# Statistical Analysis (NEW)
# ─────────────────────────────────────────────


def _run_statistical_analysis(df: pd.DataFrame, code: str) -> dict[str, Any]:
    """Run deeper statistical analysis on the dataset."""
    stats: dict[str, Any] = {}

    num_cols = df.select_dtypes(include=[np.number]).columns.tolist()

    # 1. Numeric column stats
    if num_cols:
        col_stats = {}
        for col in num_cols[:20]:  # cap at 20 columns for speed
            series = df[col].dropna()
            if len(series) == 0:
                continue
            col_stats[col] = {
                "mean": round(float(series.mean()), 4),
                "std": round(float(series.std()), 4),
                "min": round(float(series.min()), 4),
                "max": round(float(series.max()), 4),
                "median": round(float(series.median()), 4),
                "skewness": round(float(series.skew()), 4),
                "kurtosis": round(float(series.kurtosis()), 4),
            }
        stats["numeric_stats"] = col_stats

    # 2. Skewed columns
    skewed = []
    for col in num_cols:
        try:
            skew_val = float(df[col].skew())
            if abs(skew_val) > 2.0:
                skewed.append({"column": col, "skewness": round(skew_val, 2)})
        except Exception:
            pass
    stats["highly_skewed_columns"] = skewed

    # 3. Outlier detection (IQR method, flag columns with >5% outliers)
    outlier_cols = []
    for col in num_cols:
        series = df[col].dropna()
        if len(series) < 10:
            continue
        q1 = series.quantile(0.25)
        q3 = series.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_count = int(((series < lower) | (series > upper)).sum())
        outlier_pct = round(outlier_count / len(series) * 100, 1)
        if outlier_pct > 5:
            outlier_cols.append({
                "column": col,
                "outlier_count": outlier_count,
                "outlier_pct": outlier_pct,
                "range": f"[{round(float(lower), 2)}, {round(float(upper), 2)}]",
            })
    stats["outlier_columns"] = outlier_cols

    # 4. Correlation analysis (find highly correlated feature pairs)
    high_corr_pairs = []
    if len(num_cols) >= 2 and len(num_cols) <= 100:
        try:
            corr_matrix = df[num_cols].corr()
            for i in range(len(num_cols)):
                for j in range(i + 1, len(num_cols)):
                    corr_val = corr_matrix.iloc[i, j]
                    if not math.isnan(corr_val) and abs(corr_val) > 0.9:
                        high_corr_pairs.append({
                            "col1": num_cols[i],
                            "col2": num_cols[j],
                            "correlation": round(float(corr_val), 3),
                        })
        except Exception:
            pass
    stats["high_correlation_pairs"] = high_corr_pairs[:15]  # cap

    # 5. Scale disparity detection (features on wildly different scales)
    scale_issues = []
    if len(num_cols) >= 2:
        ranges = {}
        for col in num_cols:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            col_range = float(series.max() - series.min())
            if col_range > 0:
                ranges[col] = col_range
        if len(ranges) >= 2:
            max_range = max(ranges.values())
            min_range = min(r for r in ranges.values() if r > 0)
            if max_range / min_range > 100:
                biggest = max(ranges, key=ranges.get)
                smallest = min((k for k, v in ranges.items() if v > 0), key=lambda k: ranges[k])
                has_scaling = bool(re.search(r"(StandardScaler|MinMaxScaler|RobustScaler|normalize|Normalizer)", code, re.IGNORECASE))
                scale_issues.append({
                    "biggest": {"column": biggest, "range": round(ranges[biggest], 2)},
                    "smallest": {"column": smallest, "range": round(ranges[smallest], 4)},
                    "ratio": round(max_range / min_range, 0),
                    "scaling_detected": has_scaling,
                })
    stats["scale_disparity"] = scale_issues

    return stats


# ─────────────────────────────────────────────
# Prompt Summary Builder
# ─────────────────────────────────────────────


def _build_prompt_summary(
    profile: dict[str, Any],
    cross_issues: list[dict[str, Any]],
    quality_issues: list[dict[str, Any]],
    stats: dict[str, Any] | None = None,
) -> str:
    """Build a text summary of data analysis for the Gemini prompt."""
    lines = []
    lines.append("=== DATASET ANALYSIS (from actual uploaded file) ===")
    lines.append(f"Shape: {profile['shape']['rows']:,} rows × {profile['shape']['cols']} columns")
    lines.append(f"Columns: {', '.join(profile['columns'][:30])}")

    if profile.get("numeric_columns"):
        lines.append(f"Numeric columns ({len(profile['numeric_columns'])}): {', '.join(profile['numeric_columns'][:20])}")
    if profile.get("categorical_columns"):
        lines.append(f"Categorical columns ({len(profile['categorical_columns'])}): {', '.join(profile['categorical_columns'][:20])}")
    if profile.get("datetime_columns"):
        lines.append(f"Date/time columns: {', '.join(profile['datetime_columns'])}")

    if profile.get("missing_pct"):
        lines.append(f"Missing values: {profile['missing_pct']}")

    if profile.get("potential_targets"):
        for t in profile["potential_targets"][:3]:
            lines.append(f"Potential target '{t['column']}': {t['n_unique']} classes, distribution: {t['distribution']}")

    if profile.get("duplicate_pct", 0) > 1:
        lines.append(f"Duplicate rows: {profile['duplicate_pct']}%")

    lines.append(f"Memory: {profile.get('memory_mb', 0)} MB")

    # ── Statistical insights ──
    if stats:
        if stats.get("highly_skewed_columns"):
            skewed_str = ", ".join(f"{s['column']} (skew={s['skewness']})" for s in stats["highly_skewed_columns"][:5])
            lines.append(f"\nHighly skewed features (|skew|>2): {skewed_str}")

        if stats.get("outlier_columns"):
            outlier_str = ", ".join(f"{o['column']} ({o['outlier_pct']}% outliers)" for o in stats["outlier_columns"][:5])
            lines.append(f"Columns with many outliers (>5% IQR): {outlier_str}")

        if stats.get("high_correlation_pairs"):
            corr_str = ", ".join(f"{p['col1']}↔{p['col2']} (r={p['correlation']})" for p in stats["high_correlation_pairs"][:5])
            lines.append(f"Highly correlated pairs (|r|>0.9): {corr_str}")
            lines.append("  → These redundant features increase multicollinearity and overfit risk. Consider dropping one from each pair.")

        if stats.get("scale_disparity"):
            for sd in stats["scale_disparity"]:
                lines.append(f"Feature scale disparity: {sd['biggest']['column']} range={sd['biggest']['range']} vs "
                             f"{sd['smallest']['column']} range={sd['smallest']['range']} (ratio: {sd['ratio']}x)")
                if not sd["scaling_detected"]:
                    lines.append("  → WARNING: No feature scaling detected in code! Distance-based models (SVM, KNN, NN) will be dominated by large-scale features.")

    if cross_issues:
        lines.append("\n--- CODE vs DATA MISMATCHES (CONFIRMED BUGS) ---")
        for issue in cross_issues:
            lines.append(f"[{issue['severity']}] {issue['title']}: {issue['detail']}")

    if quality_issues:
        lines.append("\n--- DATA QUALITY ISSUES ---")
        for issue in quality_issues:
            lines.append(f"[{issue['severity']}] {issue['title']}: {issue['detail']}")

    if not cross_issues and not quality_issues:
        lines.append("\n--- No data quality issues or code/data mismatches found ---")

    lines.append("=== END DATASET ANALYSIS ===")
    return "\n".join(lines)
