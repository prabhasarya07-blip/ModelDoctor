"""Layer 3: Gemini LLM Reasoning Service.

Sends the user's code + pre-flagged patterns + data analysis to
Gemini 2.5 Flash and receives a structured JSON diagnosis.

Hardened with:
  - Exponential backoff retry (1s → 2s → 4s)
  - 4-level JSON repair pipeline
  - Response validation and sanitization
  - Structured error recovery
  - Token-aware logging
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any

import google.generativeai as genai
from dotenv import load_dotenv

from models.schemas import DiagnosisIssue, IssueLocation, Severity
from prompts.diagnosis_prompt import SYSTEM_PROMPT, build_user_prompt

load_dotenv()
logger = logging.getLogger("modeldoctor")

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

MAX_RETRIES = 3
BASE_BACKOFF = 1.0  # seconds
MAX_BACKOFF = 8.0

# Valid issue types and severities for validation
VALID_TYPES = {
    "DATA_LEAKAGE", "TRAIN_TEST_SPLIT_ERROR", "OVERFITTING",
    "FEATURE_MISUSE", "GRADIENT_INSTABILITY", "PREPROCESSING_ERROR",
    "CODE_STRUCTURE_ISSUE", "EVALUATION_ERROR", "RESOURCE_ISSUE",
    "DEPLOYMENT_RISK", "UNKNOWN",
}
VALID_SEVERITIES = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}


def _get_model() -> genai.GenerativeModel:
    """Get the configured Gemini model instance."""
    return genai.GenerativeModel(
        model_name="gemini-2.5-flash",
        system_instruction=SYSTEM_PROMPT,
        generation_config=genai.GenerationConfig(
            temperature=0.1,
            top_p=0.8,
            max_output_tokens=16384,
            response_mime_type="application/json",
        ),
    )


def _clean_json_response(text: str) -> str:
    """Strip markdown code fences and extra whitespace from LLM output."""
    text = text.strip()
    # Remove ```json ... ``` wrapping
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _repair_json(text: str) -> str:
    """Attempt to repair malformed JSON from LLM output.

    Common issues:
    - Unescaped newlines inside JSON string values
    - Trailing commas
    - Unescaped backslashes
    """
    # Fix unescaped real newlines inside JSON string values
    # Strategy: walk through the text, track if we're inside a JSON string,
    # and escape raw newlines/tabs found within strings.
    result = []
    in_string = False
    i = 0
    length = len(text)
    while i < length:
        ch = text[i]

        if in_string:
            if ch == '\\' and i + 1 < length:
                # This is an escape sequence — keep both chars as-is
                result.append(ch)
                result.append(text[i + 1])
                i += 2
                continue
            elif ch == '"':
                # Unescaped quote inside string = end of string
                in_string = False
                result.append(ch)
                i += 1
                continue
            elif ch == '\n':
                result.append('\\n')
                i += 1
                continue
            elif ch == '\r':
                # Skip carriage returns
                i += 1
                continue
            elif ch == '\t':
                result.append('\\t')
                i += 1
                continue
            else:
                result.append(ch)
                i += 1
                continue
        else:
            # Not inside a string
            if ch == '"':
                in_string = True
                result.append(ch)
                i += 1
                continue
            else:
                result.append(ch)
                i += 1
                continue

    repaired = ''.join(result)

    # Remove trailing commas before } or ]
    repaired = re.sub(r',\s*([}\]])', r'\1', repaired)

    return repaired


def _analyze_json_structure(text: str) -> tuple[bool, list[str]]:
    """Walk through text tracking JSON nesting state.

    Returns (in_string, stack_of_open_brackets).
    """
    stack: list[str] = []
    in_string = False
    escape_next = False

    for ch in text:
        if escape_next:
            escape_next = False
            continue
        if in_string:
            if ch == '\\':
                escape_next = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch in ('{', '['):
                stack.append(ch)
            elif ch == '}' and stack and stack[-1] == '{':
                stack.pop()
            elif ch == ']' and stack and stack[-1] == '[':
                stack.pop()

    return in_string, stack


def _repair_truncated_json(text: str) -> str:
    """Repair JSON that was truncated mid-generation by closing open structures.

    Handles:
      - Unterminated string values → close them
      - Trailing incomplete key-value pairs → remove them
      - Missing closing brackets/braces → add them

    This is the key fix for Gemini occasionally returning cut-off responses.
    """
    text = text.rstrip()
    in_string, stack = _analyze_json_structure(text)

    if not in_string and not stack:
        return text  # Already structurally complete

    result = text

    # ── Step 1: close unterminated string ──
    if in_string:
        result += '"'

    # ── Step 2: clean trailing garbage outside strings ──
    # After closing a string we may have a dangling comma, colon, or
    # incomplete key that prevents valid JSON.
    # Strip trailing , : whitespace that sit outside of any string.
    result = re.sub(r'[,:\s]+$', '', result)

    # ── Step 3: re-analyze and close all open brackets ──
    _, remaining_stack = _analyze_json_structure(result)
    for bracket in reversed(remaining_stack):
        result += '}' if bracket == '{' else ']'

    # Quick validation
    try:
        json.loads(result)
        return result
    except json.JSONDecodeError:
        pass

    # ── Step 4: more aggressive — trim to last comma outside strings ──
    # Walk backwards to find the last ',' that is outside a string,
    # truncate there, then close structures.
    # This discards the last (incomplete) key-value pair entirely.
    best = text
    if in_string:
        # Find the opening " of the truncated string and cut before it
        last_q = text.rfind('"')
        if last_q > 0:
            before_quote = text[:last_q].rstrip()
            # If preceded by ':', it was a value — remove the key too
            if before_quote.endswith(':'):
                before_colon = before_quote[:-1].rstrip()
                # Remove the key string
                if before_colon.endswith('"'):
                    key_start = before_colon[:-1].rfind('"')
                    if key_start >= 0:
                        best = before_colon[:key_start].rstrip().rstrip(',')
            elif before_quote.endswith(','):
                best = before_quote[:-1]
            else:
                best = before_quote
    else:
        best = re.sub(r',\s*$', '', text)

    _, stack2 = _analyze_json_structure(best)
    for bracket in reversed(stack2):
        best += '}' if bracket == '{' else ']'

    try:
        json.loads(best)
        return best
    except json.JSONDecodeError:
        pass

    # ── Step 5: nuclear — find the last complete '}' outside strings ──
    # Scan for positions of '}' that are outside strings.
    outside_braces: list[int] = []
    s_in_string = False
    s_escape = False
    for i, ch in enumerate(text):
        if s_escape:
            s_escape = False
            continue
        if s_in_string:
            if ch == '\\':
                s_escape = True
            elif ch == '"':
                s_in_string = False
        else:
            if ch == '"':
                s_in_string = True
            elif ch == '}':
                outside_braces.append(i)

    for pos in reversed(outside_braces):
        candidate = text[:pos + 1]
        _, cstack = _analyze_json_structure(candidate)
        closure = ''
        for bracket in reversed(cstack):
            closure += '}' if bracket == '{' else ']'
        try:
            json.loads(candidate + closure)
            return candidate + closure
        except json.JSONDecodeError:
            continue

    return result  # Return best-effort from Step 3


def _safe_parse_json(text: str) -> dict[str, Any]:
    """Try to parse JSON with a 6-level repair pipeline.

    Levels:
      1. Direct parse
      2. Newline/comma repair → parse
      3. Repair + truncation close → parse  ← NEW
      4. Regex-extract outer object → repair + truncation → parse
      5. Scan for last '}' outside strings → repair + truncation → parse
      6. Aggressive trim to last complete value → close → parse
    """
    # ── Level 1: direct parse ──
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        logger.info("L1 direct parse failed at pos %d: %s", e.pos, e.msg)

    # ── Level 2: repair newlines + trailing commas ──
    repaired = _repair_json(text)
    try:
        return json.loads(repaired)
    except json.JSONDecodeError as e:
        logger.info("L2 newline-repair failed at pos %d: %s", e.pos, e.msg)

    # ── Level 3: repair + close truncation ──
    truncation_fixed = _repair_truncated_json(repaired)
    try:
        data = json.loads(truncation_fixed)
        logger.info("L3 truncation repair succeeded (salvaged %d issues)",
                     len(data.get('issues', [])))
        return data
    except json.JSONDecodeError as e:
        logger.warning("L3 truncation repair failed at pos %d: %s", e.pos, e.msg)

    # ── Level 4: regex-extract outermost { ... } ──
    match = re.search(r'\{[\s\S]*\}', text)
    if match:
        extracted = _repair_truncated_json(_repair_json(match.group()))
        try:
            data = json.loads(extracted)
            logger.info("L4 regex-extract succeeded")
            return data
        except json.JSONDecodeError:
            pass

    # ── Level 5: find last '}' outside strings → truncate + repair ──
    # Uses _repair_truncated_json which already has the smart scan
    truncation_from_raw = _repair_truncated_json(_repair_json(text))
    try:
        data = json.loads(truncation_from_raw)
        logger.info("L5 raw truncation repair succeeded")
        return data
    except json.JSONDecodeError:
        pass

    # ── Level 6: last-resort brace scan (original step 4, kept for edge cases) ──
    for end_pos in range(len(repaired) - 1, 0, -1):
        if repaired[end_pos] == '}':
            candidate = repaired[:end_pos + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    raise json.JSONDecodeError("All 6 JSON repair levels failed", text, 0)


def _parse_issues(raw_issues: list[dict[str, Any]]) -> list[DiagnosisIssue]:
    """Parse raw JSON issues into validated Pydantic models with sanitization."""
    parsed: list[DiagnosisIssue] = []
    seen_ids = set()

    for idx, raw in enumerate(raw_issues):
        try:
            location = None
            if raw.get("location"):
                loc = raw["location"]
                location = IssueLocation(
                    line_start=loc.get("line_start"),
                    line_end=loc.get("line_end"),
                    code_snippet=str(loc.get("code_snippet", ""))[:500],  # cap length
                )

            severity_str = str(raw.get("severity", "MEDIUM")).upper().strip()
            if severity_str not in VALID_SEVERITIES:
                severity_str = "MEDIUM"

            issue_type = str(raw.get("type", "UNKNOWN")).upper().strip()
            if issue_type not in VALID_TYPES:
                issue_type = "UNKNOWN"

            # Ensure unique IDs
            issue_id = raw.get("id", f"UNK-{idx + 1:03d}")
            if issue_id in seen_ids:
                issue_id = f"{issue_id}-{idx}"
            seen_ids.add(issue_id)

            # Sanitize health_impact
            impact = raw.get("health_impact", -10)
            if isinstance(impact, (int, float)):
                impact = int(max(-50, min(0, impact)))  # clamp to [-50, 0]
            else:
                impact = -10

            # Validate text fields aren't empty
            title = str(raw.get("title", "Unknown issue")).strip()
            if not title or len(title) < 3:
                title = f"Issue #{idx + 1}"

            explanation = str(raw.get("explanation", "")).strip()
            suggested_fix = str(raw.get("suggested_fix", "")).strip()

            issue = DiagnosisIssue(
                id=issue_id,
                type=issue_type,
                severity=Severity(severity_str),
                title=title[:200],  # cap title length
                explanation=explanation[:2000],  # cap explanation
                suggested_fix=suggested_fix[:3000],  # cap fix length
                location=location,
                health_impact=impact,
            )
            parsed.append(issue)
        except Exception as exc:
            logger.warning("Skipping malformed issue #%d: %s — %s", idx, raw.get("id", "?"), exc)
            continue

    return parsed


async def _call_gemini(model: genai.GenerativeModel, prompt: str) -> str:
    """Call Gemini with exponential backoff retry logic.

    Retry delays: 1s → 2s → 4s (capped at MAX_BACKOFF).
    """
    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Gemini call attempt %d/%d (prompt: %d chars)", attempt, MAX_RETRIES, len(prompt))
            response = await model.generate_content_async(prompt)

            if response.text:
                logger.info("Gemini responded: %d chars", len(response.text))
                return response.text

            # Check for blocked/filtered responses
            if hasattr(response, 'prompt_feedback'):
                feedback = response.prompt_feedback
                logger.warning("Gemini prompt feedback: %s", feedback)

            raise ValueError("Gemini returned empty response")

        except Exception as e:
            last_error = e
            error_type = type(e).__name__
            logger.warning("Gemini attempt %d/%d failed (%s): %s", attempt, MAX_RETRIES, error_type, e)

            if attempt < MAX_RETRIES:
                delay = min(BASE_BACKOFF * (2 ** (attempt - 1)), MAX_BACKOFF)
                logger.info("Retrying in %.1fs...", delay)
                await asyncio.sleep(delay)

    raise last_error or RuntimeError("Gemini call failed after all retries")


async def analyze_with_gemini(
    code: str,
    flagged_patterns_text: str,
    ast_analysis_text: str = "",
) -> dict[str, Any]:
    """Send code to Gemini for deep ML pipeline analysis.

    Layer 3 of ModelDoctor pipeline. Receives evidence from:
      - Layer 1 (Pattern Scanner)    as flagged_patterns_text
      - Layer 2 (AST Deep Analyzer)  as ast_analysis_text

    Returns:
        dict with keys: health_score, issues (list[DiagnosisIssue]), summary, elapsed_ms
    """
    model = _get_model()

    user_prompt = build_user_prompt(
        code=code,
        flagged_patterns=flagged_patterns_text,
        ast_analysis_section=ast_analysis_text,
    )

    start = time.perf_counter()

    try:
        raw_text = await _call_gemini(model, user_prompt)
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        # Debug: log raw response
        logger.info("Raw Gemini response length: %d", len(raw_text))
        logger.debug("Raw Gemini response: %s", raw_text[:500])

        cleaned = _clean_json_response(raw_text)
        data = _safe_parse_json(cleaned)

        # ── Validate response structure ──
        health_score = data.get("health_score", 50)
        if not isinstance(health_score, (int, float)):
            health_score = 50
        health_score = max(0, min(100, int(health_score)))

        raw_issues = data.get("issues", [])
        if not isinstance(raw_issues, list):
            logger.warning("Gemini returned non-list issues: %s", type(raw_issues))
            raw_issues = []

        issues = _parse_issues(raw_issues)

        summary = data.get("summary", "Analysis complete.")
        if not isinstance(summary, str) or len(summary) < 5:
            summary = "Analysis complete. See individual issues for details."

        logger.info(
            "Gemini analysis complete: score=%d, issues=%d, time=%dms",
            health_score, len(issues), elapsed_ms,
        )

        return {
            "health_score": health_score,
            "issues": issues,
            "summary": summary,
            "elapsed_ms": elapsed_ms,
        }

    except json.JSONDecodeError as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error("JSON parse failed after all 6 repair levels: %s", e)
        logger.error("Raw response preview: %s", repr(raw_text[:500]) if 'raw_text' in dir() else "N/A")
        # Return a more honest fallback — score 50 with a clear retry message
        return {
            "health_score": 50,
            "issues": [],
            "summary": (
                "The AI model returned a malformed response that could not be recovered. "
                "Pattern scanner flags are still reflected in the score. Please retry for full analysis."
            ),
            "elapsed_ms": elapsed_ms,
        }
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.error("Gemini analysis failed (%s): %s", type(e).__name__, e)
        return {
            "health_score": 50,
            "issues": [],
            "summary": f"Gemini analysis failed: {str(e)[:200]}",
            "elapsed_ms": elapsed_ms,
        }
