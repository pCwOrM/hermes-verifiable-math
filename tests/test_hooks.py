"""Unit tests for Hermes Verifiable Math lifecycle hooks."""

import os
import sys

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import hooks


def test_pre_hook_precision_trap_detection():
    # Detect 0.1 + 0.2 floating point trap
    res = hooks.math_pre_execution_guard("bash", {"command": "python -c 'print(0.1 + 0.2)'"})
    assert res["action"] == "proceed"
    assert res["intercepted"] is True
    assert "precision loss" in res["warning"]


def test_pre_hook_clean_call():
    # Clean call without precision trap
    res = hooks.math_pre_execution_guard("bash", {"command": "ls -la"})
    assert res["action"] == "proceed"
    assert res["intercepted"] is False
    assert res["warning"] is None


def test_post_hook_proof_stamp():
    res = hooks.math_post_execution_verifier("verify_math_claim", {"verified": True})
    assert res["verified_by"] == "Hermes-Verifiable-Math-v1.0"
    assert res["proof_stamp"].startswith("[VERIFIED-MATH-PROOF-v1:")
