"""
Verifiable Math Kernel: Community Plugin for Hermes Agent.
Deterministic Symbolic Computation, Certified Factorization, and Formal Proof Auditing.
"""

from __future__ import annotations

import logging
from typing import Any

try:
    from . import schemas, tools, hooks, lean_core
except (ImportError, ValueError):
    import schemas  # type: ignore
    import tools  # type: ignore
    import hooks  # type: ignore
    import lean_core  # type: ignore

__version__ = "1.0.2"
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
    """
    Register Verifiable Math Kernel tools, lifecycle hooks, and slash commands with Hermes Agent.

    Args:
        ctx: The Hermes plugin context instance.
    """
    enable_lean = _read_config(ctx, "enable_lean_cli", True)
    lean_core.configure_runtime(enable_lean_cli=bool(enable_lean))

    # 1. Register Lifecycle Hooks (Precision Guard & Telemetry)
    if hasattr(ctx, "register_hook"):
        ctx.register_hook("pre_tool_call", hooks.math_pre_execution_guard)
        ctx.register_hook("post_tool_call", hooks.math_post_execution_verifier)

    # 2. Register Interactive Symbolic & Verification Tools
    if hasattr(ctx, "register_tool"):
        ctx.register_tool(
            name="verify_math_claim",
            toolset="verifiable_reasoning",
            schema=schemas.VERIFY_MATH_CLAIM_SCHEMA,
            handler=tools.verify_math_claim_handler,
        )
        ctx.register_tool(
            name="certified_factorization",
            toolset="verifiable_reasoning",
            schema=schemas.CERTIFIED_FACTORIZATION_SCHEMA,
            handler=tools.certified_factorization_handler,
        )
        ctx.register_tool(
            name="elliptic_curve_analyzer",
            toolset="verifiable_reasoning",
            schema=schemas.ELLIPTIC_CURVE_ANALYZER_SCHEMA,
            handler=tools.elliptic_curve_analyzer_handler,
        )
        ctx.register_tool(
            name="lean4_proof_audit",
            toolset="verifiable_reasoning",
            schema=schemas.LEAN4_PROOF_AUDIT_SCHEMA,
            handler=tools.lean4_proof_audit_handler,
        )

    # 3. Register Slash Commands (/verify, /math)
    if hasattr(ctx, "register_command"):
        try:
            ctx.register_command(
                name="/verify",
                handler=tools.math_cli_status,
                description="Verify an algebraic identity or simplify an expression using the Verifiable Math Kernel",
                args_hint="<expression_or_equality>",
            )
            ctx.register_command(
                name="/math",
                handler=tools.math_cli_status,
                description="Alias for /verify — run symbolic verification or display kernel status",
                args_hint="<expression_or_equality>",
            )
        except TypeError:
            ctx.register_command("/verify", tools.math_cli_status)
            ctx.register_command("/math", tools.math_cli_status)

    logger.info("Verifiable Math Kernel v1.0.2 registered with Hermes Agent.")
