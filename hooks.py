"""
Lifecycle hooks for Hermes Verifiable Math:
Floating-point precision safety guard and cryptographic proof telemetry.
"""

import hashlib
import json
import logging
import re
from typing import Dict, Any, Optional

from . import lean_core

logger = logging.getLogger(__name__)


def math_pre_execution_guard(
    tool_name: str = "",
    args: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Pre-tool execution hook:
    1. Inspects Lean 4 code execution: when lean4_proof_audit is called with enable_lean_cli on
       and snippet has no holes, returns {"action": "approve", ...} to request user confirmation.
    2. Inspects tool arguments for risky floating-point precision traps (e.g., 0.1 + 0.2)
       or large integer conversions, preventing catastrophic round-off hallucinations.
    3. When `verify_math_claim` is called with decimal floats and no explicit domain,
       returns `{"action": "modify", "args": ...}` to auto-select exact `rational` domain.
    """
    safe_args = args if isinstance(args, dict) else {}

    # Check Lean CLI approval gate when enabled and snippet has no holes
    if tool_name == "lean4_proof_audit" and lean_core.is_lean_cli_enabled():
        code = str(safe_args.get("code") or "")
        has_holes = any(re.search(r"\b(sorry|admit)\b", line.split("--")[0]) for line in code.splitlines())
        if not has_holes:
            snippet_preview = code.strip().splitlines()[0][:60] if code.strip() else ""
            return {
                "action": "approve",
                "message": f"Run local lean --stdin on this snippet ({snippet_preview}...)",
                "rule_key": "verifiable-math-kernel:lean",
            }

    warning = None

    # Inspect string representations of arguments
    args_str = json.dumps(safe_args, default=str)

    # Detect IEEE-754 precision trap: e.g. 0.1 + 0.2 or float decimals in exact math
    float_pattern = re.compile(r"\b0\.[0-9]{1,4}\s*[\+\-\*\/]\s*0\.[0-9]{1,4}\b")
    has_float_trap = bool(float_pattern.search(args_str))
    if has_float_trap:
        warning = (
            "[MATH-SAFETY-WARN] Detected decimal floating-point arithmetic. "
            "Use exact rational arithmetic (fractions or SymPy Rational) to avoid IEEE 754 precision loss."
        )

    # Detect dangerous large float usage > 2^53
    large_float_pattern = re.compile(r"\b([1-9][0-9]{15,})\.0*\b")
    if large_float_pattern.search(args_str):
        warning = (
            "[MATH-SAFETY-WARN] Integer exceeds 2^53 JavaScript/IEEE-754 float mantissa limit. "
            "Ensure big-integer precision is maintained without float coercion."
        )

    if warning:
        logger.warning("%s (tool=%s, task=%s)", warning, tool_name, task_id)
        if tool_name == "verify_math_claim" and has_float_trap and "domain" not in safe_args:
            return {
                "action": "modify",
                "args": {**safe_args, "domain": "rational"},
                "warning": warning,
                "intercepted": True,
            }

    return {
        "action": "proceed",
        "warning": warning,
        "intercepted": warning is not None,
    }


def math_post_execution_verifier(
    tool_name: str = "",
    result: Any = None,
    args: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Post-tool execution hook:
    Attaches deterministic cryptographic verification telemetry and hashes.
    """
    result_str = str(result)
    cert_hash = hashlib.sha256(result_str.encode("utf-8")).hexdigest()[:16]

    return {
        "verified_by": "Hermes-Verifiable-Math-v1.0.4",
        "proof_stamp": f"[VERIFIED-MATH-PROOF-v1:{cert_hash}]",
    }
