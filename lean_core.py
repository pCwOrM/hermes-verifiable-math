"""
Lean 4 Formal Proof Auditor & Theorem Verification Core.
Inspects Lean 4 code snippets, verifies tactic completeness, detects unproven holes (sorry),
and optionally interfaces with the local Lean 4 kernel (`lean --stdin`) when explicitly enabled
with user approval, a minimal execution environment, and an isolated scratch directory.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
from typing import Dict, Any, Optional

# Local Lean CLI invocation is disabled by default for security
_ENABLE_LEAN_CLI: bool = False
_ENABLE_LEAN_CLI_BY_SCOPE: Dict[str, bool] = {}


def _active_scope_key() -> str:
    """Resolve active Hermes profile scope key for multi-profile process isolation."""
    try:
        from hermes_constants import get_hermes_home

        return str(get_hermes_home().expanduser().resolve())
    except Exception:
        return "default"


def _get_scratch_dir() -> str:
    """Resolve and create isolated scratch cwd under plugin's profile data directory."""
    try:
        from hermes_constants import get_hermes_home
        base = Path(get_hermes_home())
    except Exception:
        base = Path.home() / ".hermes"
    scratch = base / "plugins_data" / "verifiable-math-kernel" / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    return str(scratch)


def configure_runtime(enable_lean_cli: Optional[bool] = None) -> None:
    """Configure runtime options from Hermes plugin config (isolated per profile scope)."""
    global _ENABLE_LEAN_CLI
    if enable_lean_cli is not None:
        flag = bool(enable_lean_cli)
        _ENABLE_LEAN_CLI = flag
        _ENABLE_LEAN_CLI_BY_SCOPE[_active_scope_key()] = flag


def is_lean_cli_enabled() -> bool:
    """Return whether local Lean 4 CLI invocation is enabled for the active profile scope."""
    return _ENABLE_LEAN_CLI_BY_SCOPE.get(_active_scope_key(), _ENABLE_LEAN_CLI)


def audit_lean4_code(code: str) -> Dict[str, Any]:
    """
    Audits a Lean 4 source snippet for formal mathematical soundness.
    Static AST/regex checks identify unproven holes (sorry/admit) and axioms.
    When enable_lean_cli is on, requests approval and runs `lean --stdin` in an isolated scratch dir
    with a minimal environment (PATH, HOME, LANG, LEAN_PATH only).
    """
    lines = code.strip().split("\n")
    total_lines = len(lines)

    # 1. Detect holes and unproven assertions (sorry, admit)
    sorry_pattern = re.compile(r"\b(sorry|admit)\b")
    holes = []
    for idx, line in enumerate(lines, 1):
        clean_line = line.split("--")[0]
        match = sorry_pattern.search(clean_line)
        if match:
            holes.append({"line": idx, "keyword": match.group(1), "context": line.strip()})

    # 2. Extract theorem and lemma declarations
    theorem_pattern = re.compile(
        r"\b(theorem|lemma|def)\s+([a-zA-Z0-9_'.]+)\s*(\([^\)]*\)|\{[^\}]*\}|\[[^\]]*\]|\s)*:\s*([\s\S]*?)\s*:="
    )
    theorems = []
    for match in theorem_pattern.finditer(code):
        decl_type = match.group(1)
        name = match.group(2)
        params = match.group(3) or ""
        ret_type = match.group(4) or ""
        theorems.append({
            "decl_type": decl_type,
            "name": name,
            "params": params.strip() if params else "",
            "statement": ret_type.strip(),
        })

    # 3. Detect axiom declarations
    axiom_pattern = re.compile(r"\b(axiom|constant)\s+([a-zA-Z0-9_'.]+)")
    axioms = []
    for match in axiom_pattern.finditer(code):
        axioms.append(match.group(2))

    # 4. Optional Lean 4 CLI execution (disabled by default; approved via pre_tool_call hook, minimal env, scratch cwd)
    compiler_verified = False
    compiler_output = ""

    if is_lean_cli_enabled() and not holes:
        lean_bin = shutil.which("lean")
        if lean_bin:
            minimal_env: Dict[str, str] = {}
            for var in ("PATH", "HOME", "LANG", "LEAN_PATH"):
                if var in os.environ:
                    minimal_env[var] = os.environ[var]
            if os.name == "nt":
                for var in ("SystemRoot", "USERPROFILE", "TEMP", "TMP"):
                    if var in os.environ:
                        minimal_env[var] = os.environ[var]

            try:
                res = subprocess.run(
                    [lean_bin, "--stdin"],
                    input=code,
                    text=True,
                    capture_output=True,
                    timeout=10,
                    cwd=_get_scratch_dir(),
                    env=minimal_env,
                )
                if res.returncode == 0:
                    compiler_verified = True
                    compiler_output = "Lean 4 kernel certified: 0 errors."
                else:
                    compiler_output = res.stderr or res.stdout
            except subprocess.TimeoutExpired:
                compiler_output = "Lean 4 process timed out after 10s."
            except Exception as e:
                compiler_output = f"Lean invocation failed: {str(e)}"
        else:
            compiler_output = "Lean 4 CLI is enabled in config, but `lean` binary was not found on PATH."

    # 5. Certification status (certified is True ONLY if the Lean kernel actually verified it)
    if holes:
        status = "REJECTED_UNPROVEN_HOLES"
        certified = False
    elif compiler_verified:
        status = "MACHINE_CERTIFIED_LEAN4"
        certified = True
    elif axioms:
        status = "UNCHECKED_AXIOM_DEPENDENCY"
        certified = False
    else:
        status = "UNCHECKED_NO_HOLES"
        certified = False

    return {
        "status": status,
        "certified": certified,
        "total_lines": total_lines,
        "theorems_found": len(theorems),
        "theorems": theorems,
        "unproven_holes_count": len(holes),
        "holes": holes,
        "axioms_used": axioms,
        "compiler_verified": compiler_verified,
        "compiler_message": compiler_output or ("Contains unproven holes (sorry/admit)." if holes else "Static inspection: no holes detected (Lean kernel check disabled)."),
    }
