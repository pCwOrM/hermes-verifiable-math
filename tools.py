"""
Tool handlers for Hermes Verifiable Math.
Implements exact symbolic mathematics, factorization, elliptic curve analysis, and Lean 4 auditing.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from typing import Dict, Any, List, Optional

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
    rationalize,
)

from . import eval_worker, sieve_core, elliptic_core, lean_core

_check_expression_syntax = eval_worker.check_expression_syntax
_safe_parse_expr = eval_worker.safe_parse_expr

# Safe mathematical globals for SymPy expression parsing (no builtins)
_SAFE_SYMPY_GLOBALS: Dict[str, Any] = {
    "__builtins__": {},
    "Integer": sp.Integer,
    "Rational": sp.Rational,
    "Float": sp.Float,
    "Symbol": sp.Symbol,
    "pi": sp.pi,
    "E": sp.E,
    "I": sp.I,
    "oo": sp.oo,
    "sin": sp.sin,
    "cos": sp.cos,
    "tan": sp.tan,
    "cot": sp.cot,
    "sec": sp.sec,
    "csc": sp.csc,
    "asin": sp.asin,
    "acos": sp.acos,
    "atan": sp.atan,
    "sinh": sp.sinh,
    "cosh": sp.cosh,
    "tanh": sp.tanh,
    "exp": sp.exp,
    "log": sp.log,
    "ln": sp.ln,
    "sqrt": sp.sqrt,
    "Abs": sp.Abs,
    "abs": sp.Abs,
    "factorial": sp.factorial,
    "binomial": sp.binomial,
    "gcd": sp.gcd,
    "lcm": sp.lcm,
}

_UNSAFE_EXPR_PATTERN = re.compile(r"(__|import|eval|exec|open|getattr|setattr|delattr|globals|locals|lambda|\[|\]|\{|\}|\"|\'|;)")

_DOMAIN_ASSUMPTIONS: Dict[str, Dict[str, bool]] = {
    "real": {"real": True},
    "integer": {"integer": True, "real": True},
    "rational": {"rational": True, "real": True},
    "complex": {"complex": True},
}


def verify_math_claim_handler(args: Dict[str, Any]) -> str:
    """
    Evaluates and formally verifies an algebraic statement or equation.
    Runs parsing and simplification in an isolated child process with an enforced 5.0s timeout.
    """
    statement = str(args.get("statement", "")).strip()
    if not statement:
        return json.dumps({"error": "No statement provided."}, indent=2)

    raw_domain = str(args.get("domain", "real")).strip().lower()
    domain = raw_domain if raw_domain in _DOMAIN_ASSUMPTIONS else "real"
    variables = args.get("variables")
    var_list = [str(v) for v in variables] if isinstance(variables, list) else None

    # Pre-flight syntax validation before spawning child process
    try:
        if "==" in statement or "=" in statement:
            delim = "==" if "==" in statement else "="
            for p in statement.split(delim, 1):
                eval_worker.check_expression_syntax(p.strip())
        else:
            eval_worker.check_expression_syntax(statement)
    except ValueError as e:
        return json.dumps({"error": f"Symbolic evaluation failed: {str(e)}"}, indent=2)

    worker_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "eval_worker.py")
    payload = json.dumps({"statement": statement, "domain": domain, "variables": var_list})

    try:
        proc = subprocess.run(
            [sys.executable, worker_file],
            input=payload,
            text=True,
            capture_output=True,
            timeout=5.0,
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
        if proc.returncode != 0:
            err = proc.stderr.strip() or f"Worker process failed with code {proc.returncode}"
            return json.dumps({"error": f"Symbolic evaluation failed: {err}"}, indent=2)
        out = proc.stdout.strip()
        if not out:
            return json.dumps({"error": "Empty response from evaluation worker."}, indent=2)
        resp = json.loads(out)
        if resp.get("ok"):
            return json.dumps(resp["result"], indent=2)
        else:
            return json.dumps({"error": f"Symbolic evaluation failed: {resp.get('error')}"}, indent=2)

    except subprocess.TimeoutExpired:
        return json.dumps({
            "error": "Expression evaluation timed out (5.0s computation limit exceeded)."
        }, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Symbolic evaluation failed: {str(e)}"}, indent=2)


def certified_factorization_handler(args: Dict[str, Any]) -> str:
    """
    Factors integer n and performs Baillie-PSW probable-prime testing.
    """
    n = args.get("n")
    if n is None:
        return json.dumps({"error": "Integer 'n' is required."}, indent=2)

    generate_certificates = bool(args.get("generate_certificates", True))

    try:
        n_int = int(n)
        fact_result = sieve_core.factorize_integer(
            n_int,
            generate_certificates=generate_certificates,
        )
        fact_result["sieve_method"] = "Werr 4-Stage Multi-Layer Algebraic Sieve & Baillie-PSW"
        return json.dumps(fact_result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Factorization failed: {str(e)}"}, indent=2)


def elliptic_curve_analyzer_handler(args: Dict[str, Any]) -> str:
    """
    Computes exact arithmetic geometry invariants and Mazur torsion classification.
    """
    coeffs = args.get("weierstrass", [])
    if not coeffs or len(coeffs) not in (2, 5):
        return json.dumps({"error": "Weierstrass coefficients must be 5 integers [a1,a2,a3,a4,a6] or 2 integers [a,b]."}, indent=2)

    compute_torsion = bool(args.get("compute_torsion", True))

    try:
        if len(coeffs) == 2:
            a, b = coeffs
            curve = elliptic_core.EllipticCurve(0, 0, 0, a, b)
        else:
            curve = elliptic_core.EllipticCurve(*coeffs)

        analysis = curve.analyze(compute_torsion=compute_torsion)
        analysis["framework"] = "NSF ICARM Conformal Elliptic Curve Invariant Kernel"
        return json.dumps(analysis, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Elliptic curve analysis failed: {str(e)}"}, indent=2)


def lean4_proof_audit_handler(args: Dict[str, Any]) -> str:
    """
    Audits Lean 4 code snippets for unproven holes (sorry) and formal soundness.
    """
    lean_code = str(args.get("lean_code", "")).strip()
    if not lean_code:
        return json.dumps({"error": "No Lean 4 code provided."}, indent=2)

    try:
        audit_result = lean_core.audit_lean4_code(lean_code)
        return json.dumps(audit_result, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Lean 4 audit failed: {str(e)}"}, indent=2)


def math_cli_status(args_str: str = "") -> str:
    """
    Interactive CLI status and quick verification command for /verify.
    """
    if not args_str.strip():
        return (
            "Hermes Verifiable Math Kernel [v1.0.3]\n"
            "Engine: SymPy CAS + Werr Multi-Layer Sieve + Baillie-PSW + Lean 4\n"
            "Usage: /verify <math_expression_or_equality>"
        )
    return verify_math_claim_handler({"statement": args_str.strip()})


def slash_verify_handler(args_str: str = "") -> str:
    """Handler for /verify slash command."""
    return math_cli_status(args_str)


def slash_math_handler(args_str: str = "") -> str:
    """Handler for /math slash command."""
    return math_cli_status(args_str)
