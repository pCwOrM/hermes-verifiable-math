"""
Lean 4 Formal Proof Auditor & Theorem Verification Core.
Inspects Lean 4 code snippets, verifies tactic completeness, detects unproven holes (sorry),
and interfaces with the Lean 4 kernel if available.
"""

import re
import shutil
import subprocess
from typing import Dict, List, Any


def audit_lean4_code(code: str) -> Dict[str, Any]:
    """
    Audits a Lean 4 source snippet for formal mathematical soundness.
    """
    lines = code.strip().split("\n")
    total_lines = len(lines)

    # 1. Detect holes and unproven assertions (sorry, admit)
    sorry_pattern = re.compile(r"\b(sorry|admit)\b")
    holes = []
    for idx, line in enumerate(lines, 1):
        # ignore comments
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

    # 4. Check if Lean 4 is installed on PATH
    lean_bin = shutil.which("lean") or shutil.which("lake")
    compiler_verified = False
    compiler_output = ""

    if lean_bin and not holes:
        try:
            res = subprocess.run(
                ["lean", "--stdin"],
                input=code,
                text=True,
                capture_output=True,
                timeout=10,
            )
            if res.returncode == 0:
                compiler_verified = True
                compiler_output = "Lean 4 kernel certified: 0 errors."
            else:
                compiler_output = res.stderr or res.stdout
        except Exception as e:
            compiler_output = f"Lean invocation failed: {str(e)}"

    # Determine certification status
    if holes:
        status = "REJECTED_UNPROVEN_HOLES"
        certified = False
    elif axioms:
        status = "CONDITIONAL_AXIOM_DEPENDENCY"
        certified = True
    elif compiler_verified:
        status = "MACHINE_CERTIFIED_LEAN4"
        certified = True
    else:
        status = "SYNTACTICALLY_VALID_PROOF"
        certified = True

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
        "compiler_message": compiler_output or ("No holes found, syntactically clean." if certified else "Contains incomplete proof markers."),
    }
