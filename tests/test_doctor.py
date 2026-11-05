"""Compliance and manifest integrity tests for Hermes Plugin Doctor."""

import os
import sys
import yaml

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

import __init__ as plugin_module


class MockHermesContext:
    def __init__(self):
        self.hooks = {}
        self.tools = {}
        self.commands = {}

    def register_hook(self, event_name, callback):
        self.hooks[event_name] = callback

    def register_tool(self, name, toolset, schema, handler):
        self.tools[name] = {"toolset": toolset, "schema": schema, "handler": handler}

    def register_command(self, cmd_name, callback):
        self.commands[cmd_name] = callback


def test_manifest_structure():
    manifest_path = os.path.join(PLUGIN_DIR, "plugin.yaml")
    assert os.path.exists(manifest_path)

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = yaml.safe_load(f)

    assert manifest["name"] == "verifiable-math-kernel"
    assert manifest["maintainer"] == "pCwOrM"
    assert manifest["category"] == "reasoning"
    assert "pre_tool_call" in manifest["capabilities"]["provides_hooks"]
    assert "verify_math_claim" in manifest["capabilities"]["provides_tools"]
    assert "certified_factorization" in manifest["capabilities"]["provides_tools"]
    assert "elliptic_curve_analyzer" in manifest["capabilities"]["provides_tools"]
    assert "lean4_proof_audit" in manifest["capabilities"]["provides_tools"]


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
    assert "/verify" in ctx.commands
    assert "/math" in ctx.commands
