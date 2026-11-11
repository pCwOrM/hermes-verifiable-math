"""
Verifiable Math Kernel: Community Plugin for Hermes Agent.
Deterministic Symbolic Computation, Integer Factorization with Baillie-PSW Probable-Prime Testing,
Elliptic Curve Invariants, and Formal Proof Auditing.
"""

from __future__ import annotations

import logging
import os
import sys
from typing import Any

# Ensure relative package imports resolve cleanly when imported standalone/by test runners
if not __package__:
    __package__ = __name__
    _curr = sys.modules.get(__name__)
    if _curr and not hasattr(_curr, "__path__"):
        _curr.__path__ = [os.path.dirname(os.path.abspath(__file__))]

from . import schemas, tools, hooks, lean_core

__version__ = "1.0.3"
__author__ = "Volkan Dagli"

logger = logging.getLogger(__name__)


def _read_config(ctx: Any, key: str, default: Any = None) -> Any:
    """Safely read a plugin setting from Hermes PluginContext."""
    getter = getattr(ctx, "get_config", None)
    if callable(getter):
        try:
            val = getter(key, default)
            return default if val is None else val
        except TypeError:
            try:
                val = getter(key)
                return default if val is None else val
            except TypeError:
                try:
                    cfg = getter()
                    if isinstance(cfg, dict):
                        return cfg.get(key, default)
                except Exception:
                    pass
            except Exception:
                pass
        except Exception:
            pass
    cfg_dict = getattr(ctx, "plugin_config", None) or getattr(ctx, "config", None)
    if isinstance(cfg_dict, dict):
        return cfg_dict.get(key, default)
    return default


def register(ctx: Any) -> None:
    """Register all mathematical tools, lifecycle hooks, and slash commands with Hermes Agent."""
    logger.info("Registering Verifiable Math Kernel plugin (v%s)...", __version__)

    # 1. Wire runtime configuration from Hermes profile config (default enable_lean_cli is False)
    enable_lean_cli = bool(_read_config(ctx, "enable_lean_cli", False))
    lean_core.configure_runtime(enable_lean_cli=enable_lean_cli)

    # 2. Register mathematical verification tools
    ctx.register_tool(
        name="verify_math_claim",
        toolset="verifiable_reasoning",
        schema=schemas.VERIFY_MATH_CLAIM_SCHEMA,
        handler=tools.verify_math_claim_handler,
        description="Verify symbolic identities, equation equivalence, and simplify mathematical claims with SymPy CAS.",
    )

    ctx.register_tool(
        name="certified_factorization",
        toolset="verifiable_reasoning",
        schema=schemas.CERTIFIED_FACTORIZATION_SCHEMA,
        handler=tools.certified_factorization_handler,
        description="Factorize integers using multi-stage algebraic sieves and Baillie-PSW probable-prime testing.",
    )

    ctx.register_tool(
        name="elliptic_curve_analyzer",
        toolset="verifiable_reasoning",
        schema=schemas.ELLIPTIC_CURVE_ANALYZER_SCHEMA,
        handler=tools.elliptic_curve_analyzer_handler,
        description="Compute algebraic invariants, discriminants, bad reduction primes, and torsion groups of elliptic curves.",
    )

    ctx.register_tool(
        name="lean4_proof_audit",
        toolset="verifiable_reasoning",
        schema=schemas.LEAN4_PROOF_AUDIT_SCHEMA,
        handler=tools.lean4_proof_audit_handler,
        description="Audit Lean 4 formal math proofs, check for unproven hypotheses ('sorry'), and verify via Lean CLI.",
    )

    # 3. Register lifecycle hooks
    ctx.register_hook(
        event="pre_tool_call",
        handler=hooks.math_pre_execution_guard,
    )

    ctx.register_hook(
        event="post_tool_call",
        handler=hooks.math_post_execution_verifier,
    )

    # 4. Register slash commands
    register_cmd = getattr(ctx, "register_command", None) or getattr(ctx, "register_slash_command", None)
    if callable(register_cmd):
        register_cmd(
            name="verify",
            handler=tools.slash_verify_handler,
            description="Verify an algebraic or arithmetic claim with SymPy CAS.",
        )
        register_cmd(
            name="math",
            handler=tools.slash_math_handler,
            description="Run mathematical verification or integer factorization.",
        )

    logger.info(
        "Verifiable Math Kernel registered 4 tools, 2 hooks, and 2 slash commands (enable_lean_cli=%s).",
        enable_lean_cli,
    )
