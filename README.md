# 🔬 Hermes Verifiable Math Kernel

> **Deterministic Symbolic Computation, Certified Factorization, Elliptic Curve Arithmetic, and Formal Lean 4 Proof Verification for [Hermes Agent](https://hermes-agent.nousresearch.com) (Nous Research).**

[![Hermes Agent Plugin v2](https://img.shields.io/badge/Hermes%20Plugin-v2%20Compliant-blue.svg)](https://hermes-agent.nousresearch.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests: 14 Passed](https://img.shields.io/badge/Tests-14%2F14%20Passed-brightgreen.svg)](#testing)
[![Category: Reasoning](https://img.shields.io/badge/Category-Reasoning%20%26%20Math-purple.svg)](plugin.yaml)

---

## 🎯 Overview

Large Language Models (LLMs) and autonomous agents are notorious for **mathematical hallucinations**:
1. **False Algebraic Claims:** Silent sign errors, invalid cancellations, and hallucinated identities.
2. **Factorization Failures:** Blindly guessing primes or asserting incorrect prime factorizations for integers beyond $10^{12}$.
3. **Floating-Point Precision Traps:** Incurring IEEE-754 precision loss (`0.1 + 0.2 != 0.3`) in financial and quantitative reasoning.
4. **Unverified Proofs:** Claiming theorems are proven while relying on hidden assumptions or unproven axioms.

The **Hermes Verifiable Math Kernel** (`verifiable-math-kernel`) transforms Hermes Agent into a **machine-verified computational reasoning engine**. By uniting computer algebra systems (SymPy), the **Werr Multi-Layer Algebraic Sieve & Baillie-PSW engine**, arithmetic geometry algorithms (Tate reduction, Mazur torsion bounds), and **Lean 4 formal proof auditing**, Hermes can now verify mathematical claims with **100% deterministic certainty**.

---

## 🏗️ Architecture

```
                    ┌───────────────────────────────────────────────┐
                    │            Hermes Agent Core                  │
                    │   (User Prompt / Tool Call / Planning Loop)   │
                    └───────────────────────┬───────────────────────┘
                                            │
               ┌────────────────────────────┴────────────────────────────┐
               │                                                         │
   [pre_tool_call Hook]                                       [Interactive Tools]
   • Intercepts IEEE-754 traps                                • verify_math_claim
   • Flags precision loss                                     • certified_factorization
   • Auto-suggests exact fractions                            • elliptic_curve_analyzer
               │                                              • lean4_proof_audit
               ▼                                                         │
 ┌────────────────────────────────────────────────────────┐              ▼
 │           Hermes Verifiable Math Plugin Core           │ ◄────────────┘
 ├────────────────────────────────────────────────────────┤
 │ 1. Symbolic CAS (Exact Rational & Identity Reducer)   │
 │ 2. Werr Sieve & Baillie-PSW Deterministic Primality   │
 │ 3. Elliptic Curve Tate & Mazur Torsion Classifier      │
 │ 4. Lean 4 Formal Proof Auditor & Hole (sorry) Linter   │
 └────────────────────────────┬───────────────────────────┘
                              │
                    [post_tool_call Hook]
                    • Emits SHA-256 Proof Stamp:
                      [VERIFIED-MATH-PROOF-v1:<hash>]
```

---

## 🛠️ Provided Tools

### 1. `verify_math_claim`
Verifies algebraic identities, equations, and simplifies expressions with exact symbolic reduction steps.
* **Input:** `statement: "sin(x)**2 + cos(x)**2 == 1"`
* **Output:**
```json
{
  "statement": "sin(x)**2 + cos(x)**2 == 1",
  "verified": true,
  "lhs_canonical": "sin(x)**2 + cos(x)**2",
  "rhs_canonical": "1",
  "difference_canonical": "0",
  "proof_trace": "LHS - RHS evaluated to 0 identically.",
  "latex": "\\sin^{2}{\\left(x \\right)} + \\cos^{2}{\\left(x \\right)} = 1",
  "verification_hash": "a1b2c3d4..."
}
```

### 2. `certified_factorization`
Factors composite integers and certifies every prime factor using the **Baillie-PSW deterministic primality test** (Miller-Rabin base 2 + strong Lucas-Selfridge). Also computes Euler's totient $\phi(N)$, divisor count $d(N)$, and sum of divisors $\sigma(N)$.
* **Input:** `n: 2026`
* **Output:**
```json
{
  "n": 2026,
  "bit_length": 11,
  "factors": [[2, 1], [1013, 1]],
  "factor_string": "2 * 1013",
  "certified": true,
  "certificates": [
    {"prime": 2, "exponent": 1, "is_prime": true, "cert": "small_prime"},
    {"prime": 1013, "exponent": 1, "is_prime": true, "cert": "Baillie-PSW_Deterministic"}
  ],
  "invariants": {
    "euler_totient": 1012,
    "divisor_count": 4,
    "sum_of_divisors": 3042
  }
}
```

### 3. `elliptic_curve_analyzer`
Computes exact arithmetic geometry invariants for elliptic curves over $\mathbb{Q}$ in generalized Weierstrass form $[a_1, a_2, a_3, a_4, a_6]$ or short model $[a, b]$:
* Minimal discriminant $\Delta$ and Tate invariants $b_2, b_4, b_6, b_8, c_4, c_6$.
* $j$-invariant $j(E)$.
* Bad prime conductor reduction factors.
* Rational torsion subgroup classification via **Mazur's Torsion Theorem** and Lutz-Nagell root bracketing.
* **Input:** `weierstrass: [-1, 0]` ($y^2 = x^3 - x$)
* **Output:**
```json
{
  "weierstrass_coeffs": [0, 0, 0, -1, 0],
  "discriminant": 64,
  "bad_primes": [2],
  "j_invariant": "1728",
  "torsion_order": 4,
  "torsion_group": "Z/2Z x Z/2Z",
  "nsf_icarm_conformant": true
}
```

### 4. `lean4_proof_audit`
Audits Lean 4 formal code snippets, extracts theorem declarations, verifies tactic syntax, checks for classical axioms, and detects unproven holes (`sorry` / `admit`).
* **Input:**
```lean
theorem ferma_last (n : Nat) (hn : n > 2) : 
  ∀ x y z : Nat, x^n + y^n = z^n → x * y * z = 0 := by
  sorry
```
* **Output:**
```json
{
  "status": "REJECTED_UNPROVEN_HOLES",
  "certified": false,
  "unproven_holes_count": 1,
  "holes": [{"line": 3, "keyword": "sorry", "context": "sorry"}],
  "compiler_message": "Contains incomplete proof markers."
}
```

---

## ⚡ Lifecycle Hooks & Safety Guardrails

* **`pre_tool_call` (Precision Guard):** Intercepts floating-point expressions (like `0.1 + 0.2`) across tool calls, warning Hermes against IEEE 754 precision loss and advising exact rational arithmetic.
* **`post_tool_call` (Proof Telemetry):** Stamps verified calculations with a cryptographic SHA-256 certificate proof tag:
  `[VERIFIED-MATH-PROOF-v1:<hash>]`

---

## 🚀 Installation & Usage

### 1. Install via Hermes Marketplace CLI
```bash
hermes plugins install verifiable-math-kernel
hermes plugins enable verifiable-math-kernel
```

### 2. Manual / Developer Installation
Clone into your Hermes plugins directory:
```bash
git clone https://github.com/pCwOrM/hermes-verifiable-math.git ~/.hermes/plugins/hermes-verifiable-math
cd ~/.hermes/plugins/hermes-verifiable-math
pip install -e .
```

Validate with Hermes Plugin Doctor:
```bash
hermes plugins validate . --install-deps
```

### 3. Quick Slash Commands
In Hermes CLI or Desktop:
```bash
/verify sin(x)**2 + cos(x)**2 == 1
/verify (x^2 - 1)/(x - 1)
```

---

## 🧪 Testing

Run the full automated test suite:
```bash
python -m pytest tests/ -v
```
Output:
```text
tests/test_doctor.py::test_manifest_structure PASSED
tests/test_doctor.py::test_register_context_wiring PASSED
tests/test_hooks.py::test_pre_hook_precision_trap_detection PASSED
tests/test_hooks.py::test_pre_hook_clean_call PASSED
tests/test_hooks.py::test_post_hook_proof_stamp PASSED
tests/test_tools.py::test_verify_trig_identity PASSED
tests/test_tools.py::test_verify_algebraic_identity PASSED
tests/test_tools.py::test_verify_false_statement PASSED
tests/test_tools.py::test_expression_simplification PASSED
tests/test_tools.py::test_certified_factorization PASSED
tests/test_tools.py::test_certified_factorization_prime PASSED
tests/test_tools.py::test_elliptic_curve_analyzer PASSED
tests/test_tools.py::test_lean4_audit_with_sorry PASSED
tests/test_tools.py::test_lean4_audit_complete_proof PASSED
==================== 14 passed in 1.83s ====================
```

---

## 📜 Intellectual Attribution & Background

This plugin is part of the **Werr Open Science Ecosystem** and builds directly upon methodologies verified on the **NSF Institute for Computer-Aided Reasoning in Mathematics (ICARM)** Elliptic Curve Rank Leaderboard under **U.S. National Science Foundation Grant DMS-2425401** and CERN Zenodo permanent research archives ([DOI: 10.5281/zenodo.23436282](https://doi.org/10.5281/zenodo.23436282)).

* **Author:** Volkan Dağlı ([@pCwOrM](https://github.com/pCwOrM))
* **Organization:** ITouch Systems Research & Development
* **License:** [MIT License](LICENSE)
