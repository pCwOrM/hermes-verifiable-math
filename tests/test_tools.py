"""Unit tests for Hermes Verifiable Math tools."""

import json
import os
import sys

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

from conftest import tools, lean_core


def test_verify_trig_identity():
    res_str = tools.verify_math_claim_handler({"statement": "sin(x)**2 + cos(x)**2 == 1"})
    data = json.loads(res_str)
    assert data["verified"] is True
    assert data["domain"] == "real"
    assert data["free_symbols"] == ["x"]
    assert "proof_trace" in data
    assert "verification_hash" in data


def test_verify_algebraic_identity():
    res_str = tools.verify_math_claim_handler({"statement": "(a + b)**3 == a**3 + 3*a**2*b + 3*a*b**2 + b**3"})
    data = json.loads(res_str)
    assert data["verified"] is True
    assert data["free_symbols"] == ["a", "b"]


def test_verify_rational_domain_exact_decimal():
    # In exact rational domain, 0.1 + 0.2 == 0.3 is parsed as 1/10 + 1/5 == 3/10 -> True
    res_str = tools.verify_math_claim_handler({
        "statement": "0.1 + 0.2 == 0.3",
        "domain": "rational",
    })
    data = json.loads(res_str)
    assert data["verified"] is True
    assert data["domain"] == "rational"
    assert data["difference_canonical"] == "0"


def test_verify_domain_and_variables_wiring():
    res_str = tools.verify_math_claim_handler({
        "statement": "sqrt(n**2)",
        "domain": "integer",
        "variables": ["n"],
    })
    data = json.loads(res_str)
    assert data["domain"] == "integer"
    assert data["free_symbols"] == ["n"]
    assert data["simplified"] == "Abs(n)"


def test_verify_false_statement():
    res_str = tools.verify_math_claim_handler({"statement": "x + 1 == x + 2"})
    data = json.loads(res_str)
    assert data["verified"] is False


def test_expression_simplification():
    res_str = tools.verify_math_claim_handler({"statement": "(x**2 - 1) / (x - 1)"})
    data = json.loads(res_str)
    assert data["simplified"] == "x + 1"


def test_power_tower_resource_bounding():
    # Disallow chained exponentiation / power towers
    res_str = tools.verify_math_claim_handler({"statement": "2**2**100"})
    data = json.loads(res_str)
    assert "error" in data
    assert "power towers" in data["error"].lower()


def test_large_exponent_bounding():
    # Cap exponents above limit (5000)
    res_str = tools.verify_math_claim_handler({"statement": "2**99999"})
    data = json.loads(res_str)
    assert "error" in data
    assert "exponent exceeds" in data["error"].lower()


def test_certified_factorization():
    # 2026 = 2 * 1013
    res_str = tools.certified_factorization_handler({"n": 2026})
    data = json.loads(res_str)
    assert data["certified"] is True
    assert data["factors"] == [[2, 1], [1013, 1]]
    assert len(data["certificates"]) == 2
    assert "probable_prime_tests" in data
    assert data["invariants"]["euler_totient"] == 1 * 1012


def test_certified_factorization_without_certificates():
    res_str = tools.certified_factorization_handler({"n": 2026, "generate_certificates": False})
    data = json.loads(res_str)
    assert data["certified"] is True
    assert data["factors"] == [[2, 1], [1013, 1]]
    assert data["certificates"] == []


def test_certified_factorization_prime():
    # 1000000007 is a well-known prime
    res_str = tools.certified_factorization_handler({"n": 1000000007})
    data = json.loads(res_str)
    assert data["certified"] is True
    assert data["factors"] == [[1000000007, 1]]
    assert data["probable_prime_tests"][0]["test"] == "Baillie-PSW_Probable_Prime"


def test_elliptic_curve_analyzer():
    # y^2 = x^3 - x  (short model: a=-1, b=0)
    res_str = tools.elliptic_curve_analyzer_handler({"weierstrass": [-1, 0]})
    data = json.loads(res_str)
    assert data["is_singular"] is False
    assert data["discriminant"] == 64
    assert data["bad_primes"] == [2]
    assert data["torsion_computed"] is True
    assert "Z/2Z" in data["torsion_group"]


def test_elliptic_curve_analyzer_skip_torsion():
    res_str = tools.elliptic_curve_analyzer_handler({"weierstrass": [-1, 0], "compute_torsion": False})
    data = json.loads(res_str)
    assert data["discriminant"] == 64
    assert data["torsion_computed"] is False
    assert data["torsion_order"] is None
    assert data["torsion_generators"] == []


def test_lean4_audit_with_sorry():
    lean_code = """
    theorem ferma_last (n : Nat) (hn : n > 2) : 
      ∀ x y z : Nat, x^n + y^n = z^n → x * y * z = 0 := by
      sorry
    """
    res_str = tools.lean4_proof_audit_handler({"lean_code": lean_code})
    data = json.loads(res_str)
    assert data["certified"] is False
    assert data["unproven_holes_count"] == 1
    assert data["status"] == "REJECTED_UNPROVEN_HOLES"


def test_lean4_audit_unchecked_no_holes_by_default():
    # With enable_lean_cli defaulting to False, clean snippets return certified=False with UNCHECKED_NO_HOLES
    lean_core.configure_runtime(enable_lean_cli=False)
    lean_code = """
    theorem add_comm (a b : Nat) : a + b = b + a := by
      rw [Nat.add_comm]
    """
    res_str = tools.lean4_proof_audit_handler({"lean_code": lean_code})
    data = json.loads(res_str)
    assert data["certified"] is False
    assert data["status"] == "UNCHECKED_NO_HOLES"
    assert data["unproven_holes_count"] == 0
    assert data["theorems_found"] == 1


def test_safe_parse_blocks_injection():
    res_str = tools.verify_math_claim_handler({"statement": "__import__('os').system('echo pwn')"})
    data = json.loads(res_str)
    assert "error" in data


def test_oversized_integer_literal_bounding():
    # Integer literal > 100 digits is rejected
    res_str = tools.verify_math_claim_handler({"statement": "1" + "0" * 105})
    data = json.loads(res_str)
    assert "error" in data
    assert "integer literal exceeds" in data["error"].lower()


def test_evaluation_process_timeout(monkeypatch):
    import subprocess
    def mock_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=5.0)
    monkeypatch.setattr(subprocess, "run", mock_run)
    res_str = tools.verify_math_claim_handler({"statement": "x + 1 == x + 1"})
    data = json.loads(res_str)
    assert "error" in data
    assert "timed out" in data["error"].lower()
