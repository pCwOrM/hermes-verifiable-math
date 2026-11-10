"""
Tool handlers for Hermes Verifiable Math.
Implements exact symbolic mathematics, factorization, elliptic curve analysis, and Lean 4 auditing.
"""

import hashlib
import json
import re
from typing import Dict, Any

import sympy as sp
from sympy.parsing.sympy_parser import (
    parse_expr,
    standard_transformations,
    implicit_multiplication_application,
    convert_xor,
)

try:
    from . import sieve_core, elliptic_core, lean_core
except (ImportError, ValueError):
    import sieve_core, elliptic_core, lean_core

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


def _safe_parse_expr(expr_str: str) -> sp.Expr:
    """Safely parse a mathematical expression without exposing Python builtins or attribute access."""
    cleaned = expr_str.strip()
    if len(cleaned) > 1000:
        raise ValueError("Expression exceeds maximum length (1000 chars).")
    if _UNSAFE_EXPR_PATTERN.search(cleaned):
        raise ValueError("Expression contains disallowed tokens.")
    # Reject attribute access (dots not flanked by digits)
    if re.search(r"(?<![0-9])\.|\.(?![0-9])", cleaned):
        raise ValueError("Attribute access is not permitted in mathematical expressions.")

    transformations = standard_transformations + (implicit_multiplication_application, convert_xor)
    # Pre-populate single-letter and standard identifier symbols in local_dict
    local_dict: Dict[str, Any] = {}
    for ident in re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", cleaned):
        if ident not in _SAFE_SYMPY_GLOBALS:
            local_dict[ident] = sp.Symbol(ident)

    return parse_expr(
        cleaned,
        local_dict=local_dict,
        global_dict=dict(_SAFE_SYMPY_GLOBALS),
        transformations=transformations,
        evaluate=True,
    )


def verify_math_claim_handler(args: Dict[str, Any]) -> str:
    """
    Evaluates and formally verifies an algebraic statement or equation.
    """
    statement = args.get("statement", "").strip()
    if not statement:
        return json.dumps({"error": "No statement provided."}, indent=2)

    try:
        # Check for equality statement
        if "==" in statement or "=" in statement:
            delim = "==" if "==" in statement else "="
            parts = statement.split(delim, 1)
            lhs_expr = _safe_parse_expr(parts[0])
            rhs_expr = _safe_parse_expr(parts[1])

            diff = sp.simplify(lhs_expr - rhs_expr)
            is_zero = diff.is_zero
            if is_zero is None:
                # Try trigsimp, expand, factor
                diff = sp.trigsimp(sp.expand(diff))
                is_zero = (diff == 0)

            result = {
                "statement": statement,
                "verified": bool(is_zero),
                "lhs_canonical": str(lhs_expr),
                "rhs_canonical": str(rhs_expr),
                "difference_canonical": str(diff),
                "proof_trace": "LHS - RHS evaluated to 0 identically." if is_zero else f"Non-zero residue: {str(diff)}",
                "latex": f"{sp.latex(lhs_expr)} = {sp.latex(rhs_expr)}",
                "verification_hash": hashlib.sha256(statement.encode("utf-8")).hexdigest()[:16],
            }
        else:
            # Single expression simplification / evaluation
            expr = _safe_parse_expr(statement)
            simplified = sp.simplify(expr)
            factored = sp.factor(expr)
            expanded = sp.expand(expr)

            result = {
                "expression": statement,
                "simplified": str(simplified),
                "factored": str(factored),
                "expanded": str(expanded),
                "latex": sp.latex(simplified),
                "is_constant": bool(simplified.is_constant()),
                "numeric_approx": str(simplified.evalf(30)) if simplified.is_constant() else None,
                "verification_hash": hashlib.sha256(statement.encode("utf-8")).hexdigest()[:16],
            }

        return json.dumps(result, indent=2)

    except Exception as e:
        return json.dumps({"error": f"Symbolic evaluation failed: {str(e)}"}, indent=2)


def certified_factorization_handler(args: Dict[str, Any]) -> str:
    """
    Factors integer n and produces Baillie-PSW primality proof certificates.
    """
    n = args.get("n")
    if n is None:
        return json.dumps({"error": "Integer 'n' is required."}, indent=2)

    try:
        n_int = int(n)
        fact_result = sieve_core.factorize_integer(n_int)
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

    try:
        if len(coeffs) == 2:
            a, b = coeffs
            curve = elliptic_core.EllipticCurve(0, 0, 0, a, b)
        else:
            curve = elliptic_core.EllipticCurve(*coeffs)

        analysis = curve.analyze()
        analysis["framework"] = "NSF ICARM Conformal Elliptic Curve Invariant Kernel"
        return json.dumps(analysis, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Elliptic curve analysis failed: {str(e)}"}, indent=2)


def lean4_proof_audit_handler(args: Dict[str, Any]) -> str:
    """
    Audits Lean 4 code snippets for unproven holes (sorry) and formal soundness.
    """
    lean_code = args.get("lean_code", "").strip()
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
            "Hermes Verifiable Math Kernel [v1.0.1]\n"
            "Engine: SymPy CAS + Werr Multi-Layer Sieve + Baillie-PSW + Lean 4\n"
            "Usage: /verify <math_expression_or_equality>"
        )
    return verify_math_claim_handler({"statement": args_str.strip()})
