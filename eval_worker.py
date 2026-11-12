"""
Isolated evaluation worker for SymPy parsing and simplification.
Runs in a separate child process with bounded resources and hard OS timeout.
"""

from __future__ import annotations

import hashlib
import json
import re
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

_UNSAFE_EXPR_PATTERN = re.compile(
    r"(__|import|eval|exec|open|getattr|setattr|delattr|globals|locals|lambda|\[|\]|\{|\}|\"|\'|;)"
)

_DOMAIN_ASSUMPTIONS: Dict[str, Dict[str, bool]] = {
    "real": {"real": True},
    "integer": {"integer": True, "real": True},
    "rational": {"rational": True, "real": True},
    "complex": {"complex": True},
}


def check_expression_syntax(cleaned: str) -> None:
    """Pre-parse validation to block injection, resource exhaustion, and oversized expressions."""
    if len(cleaned) > 1000:
        raise ValueError("Expression exceeds maximum length (1000 chars).")
    if _UNSAFE_EXPR_PATTERN.search(cleaned):
        raise ValueError("Expression contains disallowed tokens.")
    if re.search(r"(?<![0-9])\.|\.(?![0-9])", cleaned):
        raise ValueError("Attribute access is not permitted in mathematical expressions.")
    # Disallow chained exponentiation (power towers)
    if re.search(r"(?:\*\*|\^)\s*[\w\(\)]+\s*(?:\*\*|\^)", cleaned):
        raise ValueError("Chained exponentiation (power towers) is disallowed to prevent resource exhaustion.")
    # Cap explicit exponents
    for exp_match in re.finditer(r"(?:\*\*|\^)\s*([0-9]+)", cleaned):
        if int(exp_match.group(1)) > 5000:
            raise ValueError("Exponent exceeds maximum allowed limit (5000).")
    # Cap oversized integer literals (limit to 100 digits)
    for m in re.finditer(r"\b[0-9]{101,}\b", cleaned):
        raise ValueError("Integer literal exceeds maximum allowed size (100 digits).")
    # Cap factorial/binomial arguments to prevent explosive combinatorial evaluation
    for m in re.finditer(r"\b(?:factorial|binomial)\s*\(\s*([0-9]+)", cleaned):
        if int(m.group(1)) > 1000:
            raise ValueError("Factorial or binomial argument exceeds limit (1000).")
    # Refuse computed exponents with large literals e.g. 2**(a*10000)
    for m in re.finditer(r"(?:\*\*|\^)\s*\([^\)]*?([0-9]{5,})", cleaned):
        raise ValueError("Computed exponent contains oversized literal (>9999).")


def safe_parse_expr(
    expr_str: str,
    domain: str = "real",
    variables: Optional[List[str]] = None,
) -> sp.Expr:
    """Safely parse a mathematical expression into a SymPy expression."""
    cleaned = expr_str.strip()
    check_expression_syntax(cleaned)

    norm_domain = domain if domain in _DOMAIN_ASSUMPTIONS else "real"
    assumptions = _DOMAIN_ASSUMPTIONS[norm_domain]

    transformations = standard_transformations + (implicit_multiplication_application, convert_xor)
    if norm_domain == "rational":
        transformations = transformations + (rationalize,)

    local_dict: Dict[str, Any] = {}
    if variables and isinstance(variables, list):
        for var_name in variables:
            if isinstance(var_name, str):
                v_clean = var_name.strip()
                if re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", v_clean) and v_clean not in _SAFE_SYMPY_GLOBALS:
                    local_dict[v_clean] = sp.Symbol(v_clean, **assumptions)

    for ident in re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", cleaned):
        if ident not in _SAFE_SYMPY_GLOBALS and ident not in local_dict:
            local_dict[ident] = sp.Symbol(ident, **assumptions)

    return parse_expr(
        cleaned,
        local_dict=local_dict,
        global_dict=dict(_SAFE_SYMPY_GLOBALS),
        transformations=transformations,
        evaluate=True,
    )


def evaluate_math_claim(
    statement: str,
    domain: str = "real",
    variables: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Execute parsing and simplification of an algebraic claim."""
    if "==" in statement or "=" in statement:
        delim = "==" if "==" in statement else "="
        parts = statement.split(delim, 1)
        lhs_expr = safe_parse_expr(parts[0], domain=domain, variables=variables)
        rhs_expr = safe_parse_expr(parts[1], domain=domain, variables=variables)

        diff = sp.simplify(lhs_expr - rhs_expr)
        is_identical = bool(diff == 0)

        all_free = sorted(str(s) for s in (lhs_expr.free_symbols | rhs_expr.free_symbols))

        proof_trace = (
            f"1. Parsed LHS: {lhs_expr}\n"
            f"2. Parsed RHS: {rhs_expr}\n"
            f"3. Difference canonical form: {diff}\n"
            f"4. Identity holds identically: {is_identical}"
        )

        return {
            "verified": is_identical,
            "domain": domain,
            "statement": statement,
            "free_symbols": all_free,
            "difference_canonical": str(diff),
            "proof_trace": proof_trace,
            "lhs_canonical": str(lhs_expr),
            "rhs_canonical": str(rhs_expr),
            "verification_hash": hashlib.sha256(statement.encode("utf-8")).hexdigest()[:16],
        }
    else:
        expr = safe_parse_expr(statement, domain=domain, variables=variables)
        simplified = sp.simplify(expr)
        factored = sp.factor(expr)
        expanded = sp.expand(expr)
        free_syms = sorted(str(s) for s in expr.free_symbols)

        return {
            "expression": statement,
            "domain": domain,
            "free_symbols": free_syms,
            "simplified": str(simplified),
            "factored": str(factored),
            "expanded": str(expanded),
            "latex": sp.latex(simplified),
            "is_constant": bool(simplified.is_constant()),
            "numeric_approx": str(simplified.evalf(30)) if simplified.is_constant() else None,
            "verification_hash": hashlib.sha256(statement.encode("utf-8")).hexdigest()[:16],
        }


def main() -> None:
    raw = sys.stdin.read()
    if not raw.strip():
        sys.stdout.write(json.dumps({"ok": False, "error": "Empty input"}))
        return
    payload = json.loads(raw)
    statement = payload.get("statement", "")
    domain = payload.get("domain", "real")
    variables = payload.get("variables")
    try:
        res = evaluate_math_claim(statement, domain, variables)
        sys.stdout.write(json.dumps({"ok": True, "result": res}))
    except Exception as e:
        sys.stdout.write(json.dumps({"ok": False, "error": str(e)}))


if __name__ == "__main__":
    main()
