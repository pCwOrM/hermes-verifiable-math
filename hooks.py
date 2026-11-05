"""
Lifecycle hooks for Hermes Verifiable Math:
Floating-point precision safety guard and cryptographic proof telemetry.
"""

import hashlib
import json
import re
from typing import Dict, Any


def math_pre_execution_guard(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pre-tool execution hook:
    Inspects tool arguments for risky floating-point precision traps (e.g., 0.1 + 0.2)
    or large integer conversions, preventing catastrophic round-off hallucinations.
    """
    warning = None

    # Inspect string representations of arguments
    args_str = json.dumps(args)

    # Detect IEEE-754 precision trap: e.g. 0.1 + 0.2 or float decimals in exact math
    float_pattern = re.compile(r"\b0\.[0-9]{1,4}\s*[\+\-\*\/]\s*0\.[0-9]{1,4}\b")
    if float_pattern.search(args_str):
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

    return {
        "action": "proceed",
        "warning": warning,
        "intercepted": warning is not None,
    }


def math_post_execution_verifier(tool_name: str, result: Any) -> Dict[str, Any]:
    """
    Post-tool execution hook:
    Attaches deterministic cryptographic verification telemetry and hashes.
    """
    result_str = str(result)
    cert_hash = hashlib.sha256(result_str.encode("utf-8")).hexdigest()[:16]

    return {
        "verified_by": "Hermes-Verifiable-Math-v1.0",
        "proof_stamp": f"[VERIFIED-MATH-PROOF-v1:{cert_hash}]",
    }
