"""Layer 1: Code Parser Layer — Structural code intelligence."""

from __future__ import annotations

import ast
import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("modeldoctor")

@dataclass
class ParsedCode:
    tree: ast.AST
    code: str
    parse_success: bool
    error: str | None
    imports: dict[str, Any]
    assignments: dict[str, list[int]]
    usages: dict[str, list[int]]
    calls_in_order: list[dict[str, Any]]
    function_defs: list[dict[str, Any]]
    classes: list[dict[str, Any]]

def parse_code(code: str) -> ParsedCode:
    """Parse code into an AST and extract structural metadata."""
    try:
        tree = ast.parse(code)
    except Exception as e:
        logger.warning(f"AST parse failed: {e}")
        return ParsedCode(
            tree=None, code=code, parse_success=False, error=str(e),
            imports={}, assignments={}, usages={}, calls_in_order=[],
            function_defs=[], classes=[]
        )

    imports = _analyze_imports(tree)
    assignments, usages = _analyze_variable_flow(tree)
    calls_in_order, function_defs, classes = _analyze_structure(tree)

    return ParsedCode(
        tree=tree,
        code=code,
        parse_success=True,
        error=None,
        imports=imports,
        assignments=assignments,
        usages=usages,
        calls_in_order=calls_in_order,
        function_defs=function_defs,
        classes=classes
    )

def _analyze_imports(tree: ast.AST) -> dict[str, Any]:
    imports: list[dict] = []
    frameworks: set[str] = set()

    ML_LIBS = {"sklearn", "xgboost", "lightgbm", "catboost", "statsmodels", "scipy"}
    DL_LIBS = {"tensorflow", "keras", "torch", "pytorch", "transformers", "jax"}
    DATA_LIBS = {"pandas", "numpy", "polars", "dask"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                imports.append({"module": alias.name, "alias": alias.asname, "line": node.lineno})
                if root in ML_LIBS | DL_LIBS | DATA_LIBS: frameworks.add(root)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                for alias in node.names:
                    imports.append({"module": f"{node.module}.{alias.name}", "alias": alias.asname, "line": node.lineno})
                if root in ML_LIBS | DL_LIBS | DATA_LIBS: frameworks.add(root)

    return {
        "import_list": imports,
        "frameworks": sorted(frameworks),
    }

def _analyze_variable_flow(tree: ast.AST) -> tuple[dict[str, list[int]], dict[str, list[int]]]:
    assignments: dict[str, list[int]] = defaultdict(list)
    usages: dict[str, list[int]] = defaultdict(list)

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
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            usages[node.id].append(node.lineno)

    return dict(assignments), dict(usages)


def _analyze_structure(tree: ast.AST) -> tuple[list[dict], list[dict], list[dict]]:
    calls_in_order = []
    function_defs = []
    classes = []

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
            })
        elif isinstance(node, ast.ClassDef):
            classes.append({
                "name": node.name,
                "line": node.lineno,
            })

    calls_in_order.sort(key=lambda c: c.get("line", 0))
    return calls_in_order, function_defs, classes

def _extract_call_info(node: ast.Call) -> dict | None:
    info: dict[str, Any] = {"line": float(node.lineno)} # Use float to sort safely if needed
    if isinstance(node.func, ast.Attribute):
        info["method"] = node.func.attr
        if isinstance(node.func.value, ast.Name):
            info["object"] = node.func.value.id
        return info
    elif isinstance(node.func, ast.Name):
        info["function"] = node.func.id
        return info
    return None
