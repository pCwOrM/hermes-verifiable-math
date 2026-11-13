"""Compliance and manifest integrity tests for Hermes Plugin Doctor."""

import os
import sys
import yaml

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

from conftest import plugin_module


class MockHermesContext:
    def __init__(self):
        self.hooks = {}
        self.tools = {}
        self.commands = {}

    def register_hook(self, hook_name, callback, **kwargs):
        self.hooks[hook_name] = callback

    def register_tool(self, name, handler=None, **kwargs):
        self.tools[name] = {"handler": handler, **kwargs}

    def register_command(self, name, handler, **kwargs):
        self.commands[name] = handler


def test_manifest_structure():
    manifest_path = os.path.join(PLUGIN_DIR, "plugin.yaml")
    assert os.path.exists(manifest_path)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    assert manifest["name"] == "verifiable-math-kernel"
    assert manifest["version"] == "1.0.5"
    assert manifest["maintainer"] == "pCwOrM"
    assert manifest["category"] == "tools"
    assert "pre_tool_call" in manifest["provides_hooks"]
    assert "verify_math_claim" in manifest["provides_tools"]
    assert "certified_factorization" in manifest["provides_tools"]
    assert "elliptic_curve_analyzer" in manifest["provides_tools"]
    assert "lean4_proof_audit" in manifest["provides_tools"]
    assert manifest["requires_env"] == []
    assert manifest["config_schema"]["enable_lean_cli"]["default"] is False


def test_register_context_wiring():
    ctx = MockHermesContext()
    plugin_module.register(ctx)

    # Verify hooks registered
    assert "pre_tool_call" in ctx.hooks
    assert "post_tool_call" in ctx.hooks

    # Verify tools registered
    assert "verify_math_claim" in ctx.tools
    assert "certified_factorization" in ctx.tools
    assert "elliptic_curve_analyzer" in ctx.tools
    assert "lean4_proof_audit" in ctx.tools

    # Verify command registered
    assert "verify" in ctx.commands
    assert "math" in ctx.commands
