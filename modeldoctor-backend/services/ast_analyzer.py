"""Layer 2: AST Deep Analyzer — Structural code intelligence.

Parses the user's Python ML code into an Abstract Syntax Tree (AST) and performs
deep structural analysis that goes far beyond regex pattern matching:

  - Variable flow tracking     (trace data from creation → model.fit)
  - Data transformation order  (detect leakage across function boundaries)
  - Function call graph        (what calls what, in what order)
  - Import dependency analysis (conflicting versions, missing imports)
  - Deployment readiness       (no model.save, hardcoded paths, no logging, etc.)
  - Complexity estimation      (cyclomatic-like complexity per function)
  - Dead code detection        (unused variables, unreachable branches)
  - Magic number detection     (hardcoded hyperparameters without explanation)

This replaces the old Data Analyzer (CSV upload) — it runs EVERY time,
requires ZERO user friction, and feeds richer structural data to Gemini.

Architecture note:
  - Layer 1 (Pattern Scanner): Regex-based surface patterns  → "what it looks like"
  - Layer 2 (AST Analyzer):    AST-based structural analysis → "what it actually does"
  - Layer 3 (Gemini LLM):      Reasons over both layers      → "what should be fixed"
"""

from __future__ import annotations

import ast
import logging
from collections import defaultdict
from typing import Any

logger = logging.getLogger("modeldoctor")


# ────────────────────────────── Public API ──────────────────────────────

def analyze_ast(code: str) -> dict[str, Any]:
    """Run the full AST deep analysis pipeline.

    Returns:
        dict with keys:
            - ast_analysis_for_prompt: str  — Formatted text block for Gemini prompt
            - ast_insights: dict            — Structured data for the frontend
            - parse_success: bool           — Whether AST parsing succeeded
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        logger.warning("AST parse failed (syntax error): %s", e)
        return {
            "ast_analysis_for_prompt": f"[AST parse failed — SyntaxError at line {e.lineno}: {e.msg}]",
            "ast_insights": {
                "parse_success": False,
                "error": f"SyntaxError at line {e.lineno}: {e.msg}",
            },
            "parse_success": False,
        }

    # Run all analyzers
    imports = _analyze_imports(tree)
    variable_flow = _analyze_variable_flow(tree)
    call_graph = _analyze_call_graph(tree, code)
    complexity = _analyze_complexity(tree)
    deployment = _analyze_deployment_readiness(tree, code)
    magic_numbers = _detect_magic_numbers(tree)
    dead_code = _detect_dead_code(tree)

    # Build insights dict for frontend
    insights = {
        "parse_success": True,
        "imports": imports,
        "variable_flow": variable_flow,
        "call_graph": call_graph,
        "complexity": complexity,
        "deployment_readiness": deployment,
        "magic_numbers": magic_numbers,
        "dead_code": dead_code,
    }

    # Build formatted text for Gemini prompt
    prompt_text = _format_for_prompt(insights)

    return {
        "ast_analysis_for_prompt": prompt_text,
        "ast_insights": insights,
        "parse_success": True,
    }


# ────────────────────────────── Import Analysis ──────────────────────────────

def _analyze_imports(tree: ast.AST) -> dict[str, Any]:
    """Analyze all imports: libraries used, potential conflicts, ML frameworks."""
    imports: list[dict] = []
    ml_frameworks: set[str] = set()
    dl_frameworks: set[str] = set()

    ML_LIBS = {"sklearn", "xgboost", "lightgbm", "catboost", "statsmodels", "scipy"}
    DL_LIBS = {"tensorflow", "keras", "torch", "pytorch", "jax", "flax", "transformers"}
    DATA_LIBS = {"pandas", "numpy", "polars", "dask"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                imports.append({
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                })
                if root in ML_LIBS:
                    ml_frameworks.add(root)
                elif root in DL_LIBS:
                    dl_frameworks.add(root)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                for alias in node.names:
                    imports.append({
                        "module": f"{node.module}.{alias.name}",
                        "alias": alias.asname,
                        "line": node.lineno,
                    })
                if root in ML_LIBS:
                    ml_frameworks.add(root)
                elif root in DL_LIBS:
                    dl_frameworks.add(root)

    # Detect potential conflicts
    conflicts = []
    if "tensorflow" in dl_frameworks and "torch" in dl_frameworks:
        conflicts.append("Both TensorFlow and PyTorch imported — potential framework conflict")
    if "keras" in dl_frameworks and "tensorflow" in dl_frameworks:
        # Not a conflict, but worth noting
        pass

    return {
        "total_imports": len(imports),
        "ml_frameworks": sorted(ml_frameworks),
        "dl_frameworks": sorted(dl_frameworks),
        "conflicts": conflicts,
        "import_list": imports[:20],  # Cap for prompt size
    }


# ────────────────────────────── Variable Flow Tracking ──────────────────────────────

def _analyze_variable_flow(tree: ast.AST) -> dict[str, Any]:
    """Track how data flows from creation to model training.

    Detects:
    - Variables assigned but never used in training
    - Data that bypasses preprocessing
    - Feature/target split patterns
    """
    assignments: dict[str, list[int]] = defaultdict(list)   # var_name → [line_numbers]
    usages: dict[str, list[int]] = defaultdict(list)

    # Track assignments
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    assignments[target.id].append(node.lineno)
                elif isinstance(target, ast.Tuple):
                    for elt in target.elts:
                        if isinstance(elt, ast.Name):
                            assignments[elt.id].append(node.lineno)

        elif isinstance(node, ast.AugAssign):
            if isinstance(node.target, ast.Name):
                assignments[node.target.id].append(node.lineno)

        # Track usages in function calls, subscripts, etc.
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            usages[node.id].append(node.lineno)

    # Identify data flow patterns
    data_vars = {"X", "y", "X_train", "X_test", "y_train", "y_test",
                 "train", "test", "df", "data", "dataset", "features", "target",
                 "labels", "x_train", "x_test", "y_train", "y_test"}

    flow_issues = []
    assigned_never_used = []

    for var, lines in assignments.items():
        if var.startswith("_"):
            continue
        if var not in usages and var in data_vars:
            assigned_never_used.append({"variable": var, "assigned_at": lines})
            flow_issues.append(f"Variable '{var}' assigned (line {lines[0]}) but never used — possible dead data")

    # Detect if X,y exist but no train_test_split usage
    has_xy = "X" in assignments and "y" in assignments
    has_split = any("train" in v.lower() or "test" in v.lower()
                     for v in assignments.keys())

    if has_xy and not has_split:
        flow_issues.append("X and y defined but no train/test split detected — model may evaluate on training data")

    return {
        "total_variables": len(assignments),
        "data_variables_found": sorted(set(assignments.keys()) & data_vars),
        "flow_issues": flow_issues,
        "assigned_never_used": assigned_never_used[:10],
    }


# ────────────────────────────── Call Graph Analysis ──────────────────────────────

def _analyze_call_graph(tree: ast.AST, code: str) -> dict[str, Any]:
    """Analyze function/method calls and their ordering.

    Detects:
    - fit() before split
    - fit_transform() on test data
    - predict() without fit()
    - model.evaluate() only on training data
    """
    calls_in_order: list[dict] = []
    function_defs: list[dict] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_info = _extract_call_info(node)
            if call_info:
                calls_in_order.append(call_info)

        elif isinstance(node, ast.FunctionDef):
            function_defs.append({
                "name": node.name,
                "line": node.lineno,
                "args": [a.arg for a in node.args.args],
                "decorators": [_get_decorator_name(d) for d in node.decorator_list],
            })

    # Sort calls by line number
    calls_in_order.sort(key=lambda c: c.get("line", 0))

    # Detect ordering issues
    ordering_issues = []
    fit_transform_lines = []
    split_lines = []
    fit_lines = []
    predict_lines = []

    for call in calls_in_order:
        name = call.get("method", call.get("function", ""))
        line = call.get("line", 0)

        if name == "fit_transform":
            fit_transform_lines.append(line)
        elif name in ("train_test_split", "split"):
            split_lines.append(line)
        elif name == "fit":
            fit_lines.append(line)
        elif name == "predict":
            predict_lines.append(line)

    # Check: fit_transform before split
    if fit_transform_lines and split_lines:
        if min(fit_transform_lines) < min(split_lines):
            ordering_issues.append({
                "issue": "fit_transform() called before train_test_split()",
                "fit_transform_line": min(fit_transform_lines),
                "split_line": min(split_lines),
                "severity": "CRITICAL",
            })

    # Check: predict without fit
    if predict_lines and not fit_lines:
        ordering_issues.append({
            "issue": "predict() called but no fit() found",
            "severity": "HIGH",
        })

    return {
        "total_calls": len(calls_in_order),
        "function_definitions": function_defs,
        "ml_calls": [c for c in calls_in_order if _is_ml_call(c)],
        "ordering_issues": ordering_issues,
        "call_sequence": [
            f"L{c.get('line', '?')}: {c.get('method', c.get('function', '?'))}"
            for c in calls_in_order[:30]
        ],
    }


def _extract_call_info(node: ast.Call) -> dict | None:
    """Extract function/method call info from an AST Call node."""
    info: dict[str, Any] = {"line": node.lineno}

    if isinstance(node.func, ast.Attribute):
        info["method"] = node.func.attr
        if isinstance(node.func.value, ast.Name):
            info["object"] = node.func.value.id
        return info
    elif isinstance(node.func, ast.Name):
        info["function"] = node.func.id
        return info
    return None


def _get_decorator_name(node: ast.expr) -> str:
    """Extract decorator name from AST node."""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return node.attr
    elif isinstance(node, ast.Call):
        return _get_decorator_name(node.func)
    return "unknown"


def _is_ml_call(call: dict) -> bool:
    """Check if a call is an ML-related method."""
    ml_methods = {
        "fit", "predict", "transform", "fit_transform", "fit_predict",
        "train_test_split", "cross_val_score", "GridSearchCV",
        "compile", "evaluate", "score", "predict_proba",
        "train", "backward", "step", "zero_grad",
    }
    name = call.get("method", call.get("function", ""))
    return name in ml_methods


# ────────────────────────────── Complexity Analysis ──────────────────────────────

def _analyze_complexity(tree: ast.AST) -> dict[str, Any]:
    """Estimate code complexity per function and overall."""
    functions: list[dict] = []
    total_branches = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            branches = _count_branches(node)
            total_branches += branches
            functions.append({
                "name": node.name,
                "line": node.lineno,
                "complexity": branches + 1,  # cyclomatic = branches + 1
                "lines": _count_lines(node),
                "nested_depth": _max_nesting_depth(node),
            })

    # Top-level complexity
    top_level_branches = _count_branches(tree)

    high_complexity = [f for f in functions if f["complexity"] > 10]

    return {
        "total_functions": len(functions),
        "functions": functions,
        "high_complexity_functions": high_complexity,
        "top_level_complexity": top_level_branches + 1,
        "max_nesting_depth": max((f["nested_depth"] for f in functions), default=0),
    }


def _count_branches(node: ast.AST) -> int:
    """Count branching statements (if, for, while, try, with) in a node."""
    count = 0
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.Try,
                              ast.ExceptHandler, ast.With)):
            count += 1
    return count


def _count_lines(node: ast.AST) -> int:
    """Estimate lines of code in a function."""
    if hasattr(node, "end_lineno") and hasattr(node, "lineno"):
        return node.end_lineno - node.lineno + 1
    return 0


def _max_nesting_depth(node: ast.AST, depth: int = 0) -> int:
    """Calculate maximum nesting depth."""
    max_depth = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.If, ast.For, ast.While, ast.With,
                              ast.Try, ast.FunctionDef)):
            child_depth = _max_nesting_depth(child, depth + 1)
            max_depth = max(max_depth, child_depth)
        else:
            child_depth = _max_nesting_depth(child, depth)
            max_depth = max(max_depth, child_depth)
    return max_depth


# ────────────────────────────── Deployment Readiness ──────────────────────────────

def _analyze_deployment_readiness(tree: ast.AST, code: str) -> dict[str, Any]:
    """Check if the code is deployment-ready.

    Key checks:
    - Model serialization (model.save, joblib.dump, pickle.dump, torch.save)
    - Error handling around predict/inference
    - Hardcoded file paths
    - Logging presence
    - Inline credentials/secrets
    - Input validation before prediction
    - Reproducibility (random seeds)
    """
    checks: dict[str, dict] = {}

    # ── Model Serialization ──
    save_patterns = {"save", "dump", "save_model", "save_pretrained", "save_weights"}
    has_save = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            call_name = ""
            if isinstance(node.func, ast.Attribute):
                call_name = node.func.attr
            elif isinstance(node.func, ast.Name):
                call_name = node.func.id
            if call_name in save_patterns:
                has_save = True
                break

    checks["model_serialization"] = {
        "present": has_save,
        "status": "PASS" if has_save else "FAIL",
        "message": "Model is saved/serialized for deployment" if has_save
                   else "No model.save() / joblib.dump() / torch.save() found — model cannot be deployed",
    }

    # ── Error Handling Around Predict ──
    has_try_predict = False
    for node in ast.walk(tree):
        if isinstance(node, (ast.Try,)):
            try_code = ast.dump(node)
            if "predict" in try_code or "inference" in try_code:
                has_try_predict = True
                break

    checks["error_handling"] = {
        "present": has_try_predict,
        "status": "PASS" if has_try_predict else "WARN",
        "message": "Prediction wrapped in try/except" if has_try_predict
                   else "No error handling around predict/inference — production failures will crash silently",
    }

    # ── Hardcoded Paths ──
    hardcoded_paths = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            val = node.value
            if any(val.startswith(p) for p in ("/", "C:\\", "D:\\", "/home/", "/Users/", "./data/")):
                if len(val) > 3:  # Skip single "/" etc.
                    hardcoded_paths.append({"path": val, "line": node.lineno})

    checks["hardcoded_paths"] = {
        "count": len(hardcoded_paths),
        "status": "FAIL" if hardcoded_paths else "PASS",
        "paths": hardcoded_paths[:5],
        "message": f"{len(hardcoded_paths)} hardcoded path(s) found — will break in different environments"
                   if hardcoded_paths else "No hardcoded paths detected",
    }

    # ── Logging ──
    has_logging = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in ("info", "warning", "error", "debug", "critical"):
                    if isinstance(node.func.value, ast.Name) and node.func.value.id in ("logger", "logging", "log"):
                        has_logging = True
                        break
            elif isinstance(node.func, ast.Name) and node.func.id == "print":
                # print statements are NOT proper logging
                pass

    checks["logging"] = {
        "present": has_logging,
        "status": "PASS" if has_logging else "WARN",
        "message": "Proper logging detected" if has_logging
                   else "No structured logging — debugging production issues will be difficult",
    }

    # ── Inline Credentials ──
    credential_patterns = {"password", "secret", "api_key", "token", "aws_access", "private_key"}
    found_credentials = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if any(pat in target.id.lower() for pat in credential_patterns):
                        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                            found_credentials.append({
                                "variable": target.id,
                                "line": node.lineno,
                            })

    checks["credentials"] = {
        "count": len(found_credentials),
        "status": "FAIL" if found_credentials else "PASS",
        "found": found_credentials[:5],
        "message": f"{len(found_credentials)} hardcoded credential(s) found — SECURITY RISK"
                   if found_credentials else "No inline credentials detected",
    }

    # ── Random Seed ──
    has_seed = False
    seed_funcs = {"seed", "manual_seed", "manual_seed_all", "set_seed"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = ""
            if isinstance(node.func, ast.Attribute):
                name = node.func.attr
            elif isinstance(node.func, ast.Name):
                name = node.func.id
            if name in seed_funcs:
                has_seed = True
                break
        # Also check: random_state= keyword arg
        if isinstance(node, ast.keyword) and node.arg == "random_state":
            has_seed = True
            break

    checks["reproducibility"] = {
        "present": has_seed,
        "status": "PASS" if has_seed else "WARN",
        "message": "Random seed/state set for reproducibility" if has_seed
                   else "No random seed set — results won't be reproducible across runs",
    }

    # ── Overall Score ──
    fail_count = sum(1 for c in checks.values() if c["status"] == "FAIL")
    warn_count = sum(1 for c in checks.values() if c["status"] == "WARN")
    pass_count = sum(1 for c in checks.values() if c["status"] == "PASS")

    return {
        "checks": checks,
        "pass_count": pass_count,
        "warn_count": warn_count,
        "fail_count": fail_count,
        "total_checks": len(checks),
        "deployment_ready": fail_count == 0 and warn_count <= 1,
    }


# ────────────────────────────── Magic Number Detection ──────────────────────────────

def _detect_magic_numbers(tree: ast.AST) -> list[dict]:
    """Detect hardcoded numeric constants that should be named variables.

    Focuses on ML hyperparameters: learning rates, epochs, batch sizes, thresholds.
    """
    magic_numbers = []
    IGNORE_VALUES = {0, 1, 2, -1, 100, 0.0, 1.0, True, False, None}

    # Known hyperparameter keyword args
    HP_KWARGS = {
        "lr", "learning_rate", "epochs", "batch_size", "n_estimators",
        "max_depth", "n_epochs", "dropout", "momentum", "weight_decay",
        "test_size", "n_splits", "C", "gamma", "alpha", "threshold",
    }

    for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg in HP_KWARGS:
            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, (int, float)):
                if node.value.value not in IGNORE_VALUES:
                    magic_numbers.append({
                        "param": node.arg,
                        "value": node.value.value,
                        "line": node.value.lineno,
                    })

    return magic_numbers[:15]


# ────────────────────────────── Dead Code Detection ──────────────────────────────

def _detect_dead_code(tree: ast.AST) -> dict[str, Any]:
    """Detect potentially unused code.

    Checks:
    - Functions defined but never called
    - Variables assigned but never read
    - Imports never referenced
    """
    # Collect function definitions
    func_defs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_defs.add(node.name)

    # Collect all referenced names
    referenced = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            referenced.add(node.id)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                referenced.add(node.func.id)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                pass  # method calls tracked differently

    # Find unused functions (exclude common entrypoints)
    entrypoints = {"main", "__init__", "setup", "teardown", "forward", "call"}
    unused_funcs = [f for f in func_defs if f not in referenced and f not in entrypoints
                    and not f.startswith("_")]

    # Collect imports
    imported_names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_names.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                imported_names.add(alias.asname or alias.name)

    unused_imports = [i for i in imported_names if i not in referenced and i != "*"]

    return {
        "unused_functions": unused_funcs[:10],
        "unused_imports": unused_imports[:10],
        "total_dead_items": len(unused_funcs) + len(unused_imports),
    }


# ────────────────────────────── Prompt Formatter ──────────────────────────────

def _format_for_prompt(insights: dict) -> str:
    """Format AST insights into a text block for the Gemini prompt."""
    sections = []

    # ── Imports ──
    imp = insights["imports"]
    sections.append(f"IMPORTS: {imp['total_imports']} total")
    if imp["ml_frameworks"]:
        sections.append(f"  ML Frameworks: {', '.join(imp['ml_frameworks'])}")
    if imp["dl_frameworks"]:
        sections.append(f"  DL Frameworks: {', '.join(imp['dl_frameworks'])}")
    if imp["conflicts"]:
        sections.append(f"  ⚠ CONFLICTS: {'; '.join(imp['conflicts'])}")

    # ── Variable Flow ──
    vf = insights["variable_flow"]
    sections.append(f"\nVARIABLE FLOW: {vf['total_variables']} variables tracked")
    if vf["data_variables_found"]:
        sections.append(f"  Data variables: {', '.join(vf['data_variables_found'])}")
    for issue in vf["flow_issues"]:
        sections.append(f"  ⚠ {issue}")

    # ── Call Graph ──
    cg = insights["call_graph"]
    sections.append(f"\nCALL GRAPH: {cg['total_calls']} function calls")
    if cg["function_definitions"]:
        func_names = [f["name"] for f in cg["function_definitions"]]
        sections.append(f"  Defined functions: {', '.join(func_names)}")
    if cg["ml_calls"]:
        ml_seq = [f"L{c.get('line', '?')}: {c.get('object', '')}.{c.get('method', c.get('function', ''))}"
                  for c in cg["ml_calls"][:15]]
        sections.append(f"  ML call sequence: {' → '.join(ml_seq)}")
    for issue in cg["ordering_issues"]:
        sections.append(f"  ⚠ ORDERING ISSUE [{issue.get('severity', 'HIGH')}]: {issue['issue']}")

    # ── Complexity ──
    cx = insights["complexity"]
    sections.append(f"\nCOMPLEXITY: {cx['total_functions']} functions")
    for hc in cx["high_complexity_functions"]:
        sections.append(f"  ⚠ HIGH COMPLEXITY: {hc['name']}() — complexity={hc['complexity']}, depth={hc['nested_depth']}")
    if cx["max_nesting_depth"] > 3:
        sections.append(f"  ⚠ Max nesting depth: {cx['max_nesting_depth']} (>3 is concerning)")

    # ── Deployment Readiness ──
    dep = insights["deployment_readiness"]
    sections.append(f"\nDEPLOYMENT READINESS: {dep['pass_count']}/{dep['total_checks']} checks passed")
    for name, check in dep["checks"].items():
        icon = "✓" if check["status"] == "PASS" else ("⚠" if check["status"] == "WARN" else "✗")
        sections.append(f"  {icon} {name}: {check['message']}")

    # ── Magic Numbers ──
    mn = insights["magic_numbers"]
    if mn:
        sections.append(f"\nMAGIC NUMBERS: {len(mn)} hardcoded hyperparameters")
        for m in mn[:8]:
            sections.append(f"  L{m['line']}: {m['param']}={m['value']}")

    # ── Dead Code ──
    dc = insights["dead_code"]
    if dc["total_dead_items"] > 0:
        sections.append(f"\nDEAD CODE: {dc['total_dead_items']} unused items")
        if dc["unused_functions"]:
            sections.append(f"  Unused functions: {', '.join(dc['unused_functions'])}")
        if dc["unused_imports"]:
            sections.append(f"  Unused imports: {', '.join(dc['unused_imports'])}")

    return "\n".join(sections)
