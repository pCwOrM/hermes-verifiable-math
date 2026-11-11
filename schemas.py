"""
JSON Schemas for Hermes Verifiable Math tools.
"""

VERIFY_MATH_CLAIM_SCHEMA = {
    "type": "object",
    "properties": {
        "statement": {
            "type": "string",
            "description": "Mathematical identity, equation (e.g. 'sin(x)**2 + cos(x)**2 == 1'), or algebraic expression to prove/simplify.",
        },
        "domain": {
            "type": "string",
            "enum": ["real", "integer", "rational", "complex"],
            "default": "real",
            "description": "Assumed mathematical domain for variables.",
        },
        "variables": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional explicit list of free symbols/variables.",
        },
    },
    "required": ["statement"],
}

CERTIFIED_FACTORIZATION_SCHEMA = {
    "type": "object",
    "properties": {
        "n": {
            "type": "integer",
            "description": "Integer to decompose into prime factors verified via Baillie-PSW probable-prime testing.",
        },
        "generate_certificates": {
            "type": "boolean",
            "default": True,
            "description": "Whether to attach Baillie-PSW probable-prime test results for each factor.",
        },
    },
    "required": ["n"],
}

ELLIPTIC_CURVE_ANALYZER_SCHEMA = {
    "type": "object",
    "properties": {
        "weierstrass": {
            "type": "array",
            "items": {"type": "integer"},
            "description": "Weierstrass coefficients: either [a1, a2, a3, a4, a6] for general model, or [a, b] for short model y^2 = x^3 + ax + b.",
        },
        "compute_torsion": {
            "type": "boolean",
            "default": True,
            "description": "Whether to compute rational torsion points and classify the Mazur torsion subgroup.",
        },
    },
    "required": ["weierstrass"],
}

LEAN4_PROOF_AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "lean_code": {
            "type": "string",
            "description": "Lean 4 source code snippet containing theorem statements, tactics, or proofs to audit for unproven holes (sorry) and formal soundness.",
        },
    },
    "required": ["lean_code"],
}
