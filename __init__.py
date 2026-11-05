"""
Verifiable Math Kernel: Hermes Agent Plugin Entrypoint.
Deterministic Symbolic Computation, Certified Factorization, and Formal Proofs.
"""

try:
    from . import schemas, tools, hooks
except (ImportError, ValueError):
    import schemas, tools, hooks

__version__ = "1.0.0"
__author__ = "pCwOrM"


def register(ctx):
    """
    Register Verifiable Math Kernel tools and lifecycle hooks with Hermes Agent.
    
    Args:
        ctx: The Hermes plugin context instance.
    """
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

    # 3. Register Slash Commands
    if hasattr(ctx, "register_command"):
        ctx.register_command("/verify", tools.math_cli_status)
        ctx.register_command("/math", tools.math_cli_status)
