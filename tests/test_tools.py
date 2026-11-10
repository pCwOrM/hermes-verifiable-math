"""Unit tests for Hermes Verifiable Math tools."""

import json
import os
import sys

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import tools


def test_verify_trig_identity():
    res_str = tools.verify_math_claim_handler({"statement": "sin(x)**2 + cos(x)**2 == 1"})
    data = json.loads(res_str)
    assert data["verified"] is True
    assert "proof_trace" in data
    assert "verification_hash" in data


def test_verify_algebraic_identity():
    res_str = tools.verify_math_claim_handler({"statement": "(a + b)**3 == a**3 + 3*a**2*b + 3*a*b**2 + b**3"})
    data = json.loads(res_str)
    assert data["verified"] is True


def test_verify_false_statement():
    res_str = tools.verify_math_claim_handler({"statement": "x + 1 == x + 2"})
    data = json.loads(res_str)
    assert data["verified"] is False


def test_expression_simplification():
    res_str = tools.verify_math_claim_handler({"statement": "(x**2 - 1) / (x - 1)"})
    data = json.loads(res_str)
    assert data["simplified"] == "x + 1"


def test_certified_factorization():
    # 2026 = 2 * 1013
    res_str = tools.certified_factorization_handler({"n": 2026})
    data = json.loads(res_str)
    assert data["certified"] is True
    assert data["factors"] == [[2, 1], [1013, 1]]
    assert data["invariants"]["euler_totient"] == 1 * 1012


def test_certified_factorization_prime():
    # 1000000007 is a well-known prime
    res_str = tools.certified_factorization_handler({"n": 1000000007})
    data = json.loads(res_str)
    assert data["certified"] is True
    assert data["factors"] == [[1000000007, 1]]


def test_elliptic_curve_analyzer():
    # y^2 = x^3 - x  (short model: a=-1, b=0)
    res_str = tools.elliptic_curve_analyzer_handler({"weierstrass": [-1, 0]})
    data = json.loads(res_str)
    assert data["is_singular"] is False
    assert data["discriminant"] == 64
    assert data["bad_primes"] == [2]
    assert "Z/2Z" in data["torsion_group"]


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


def test_lean4_audit_complete_proof():
    lean_code = """
    theorem add_comm (a b : Nat) : a + b = b + a := by
      rw [Nat.add_comm]
    """
    res_str = tools.lean4_proof_audit_handler({"lean_code": lean_code})
    data = json.loads(res_str)
    assert data["certified"] is True
    assert data["unproven_holes_count"] == 0
    assert data["theorems_found"] == 1


def test_safe_parse_blocks_injection():
    res_str = tools.verify_math_claim_handler({"statement": "__import__('os').system('echo pwn')"})
    data = json.loads(res_str)
    assert "error" in data

