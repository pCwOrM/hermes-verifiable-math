"""Hermes Agent plugin specification compliance tests for verifiable-math-kernel."""

from __future__ import annotations

import importlib.util
import inspect
import sys
import tomllib
from pathlib import Path
from typing import Any, Dict, List

import yaml

PLUGIN_DIR = Path(__file__).resolve().parent.parent

KNOWN_MANIFEST_KEYS = frozenset(
    {
        "name",
        "version",
        "description",
        "author",
        "requires_env",
        "provides_tools",
        "provides_hooks",
        "hooks",
        "provides_middleware",
        "kind",
        "requires_hermes",
        "capabilities",
        "manifest_version",
        "api_version",
        "requires_plugins",
        "python_dependencies",
        "pip_dependencies",
        "python_runtime",
        "config_schema",
        "license",
        "homepage",
        "tags",
        "emits",
        "listens",
        "provides_locales",
        "config_keys",
        "oauth",
        "requires_auth",
        "mcp_servers",
        "runtime",
    }
)


class _RecordingCtx:
    plugin_config: Dict[str, Any] = {}

    def __init__(self) -> None:
        self.tools: List[Dict[str, Any]] = []
        self.hooks: Dict[str, Any] = {}
        self.commands: Dict[str, Any] = {}

    def register_tool(self, name: str, toolset: str, schema: Dict[str, Any], handler: Any, **kwargs: Any) -> None:
        self.tools.append({"name": name, "toolset": toolset, "schema": schema, "handler": handler, "kwargs": kwargs})

    def register_hook(self, hook_name: str, callback: Any, **kwargs: Any) -> None:
        self.hooks[hook_name] = callback

    def register_command(self, name: str, handler: Any, **kwargs: Any) -> None:
        self.commands[name] = handler


def _load_plugin():
    mod_name = "hermes_vmk_compliance_probe"
    spec = importlib.util.spec_from_file_location(
        mod_name,
        PLUGIN_DIR / "__init__.py",
        submodule_search_locations=[str(PLUGIN_DIR)],
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_openai_tool_schemas_have_name_description_and_parameters() -> None:
    mod = _load_plugin()
    ctx = _RecordingCtx()
    mod.register(ctx)

    assert len(ctx.tools) == 4
    for entry in ctx.tools:
        schema = entry["schema"]
        assert isinstance(schema, dict)
        assert schema.get("name") == entry["name"]
        assert isinstance(schema.get("description"), str) and schema["description"].strip()
        params = schema.get("parameters")
        assert isinstance(params, dict)
        assert params.get("type") == "object"
        assert isinstance(params.get("properties"), dict) and len(params["properties"]) >= 1
        assert "properties" not in schema

        sig = inspect.signature(entry["handler"])
        assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()), (
            f"Tool handler {entry['name']} must accept **kwargs"
        )

    for cmd_name, cmd_handler in ctx.commands.items():
        sig = inspect.signature(cmd_handler)
        assert any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()), (
            f"Slash command /{cmd_name} must accept **kwargs"
        )


def test_manifest_and_pyproject_compliance() -> None:
    manifest = yaml.safe_load((PLUGIN_DIR / "plugin.yaml").read_text(encoding="utf-8-sig"))
    unknown = set(manifest.keys()) - KNOWN_MANIFEST_KEYS
    assert not unknown, f"Unexpected keys in plugin.yaml: {sorted(unknown)}"
    assert manifest.get("requires_hermes") == ">=0.21.0"

    pyproj = tomllib.loads((PLUGIN_DIR / "pyproject.toml").read_text(encoding="utf-8-sig"))
    assert "build-system" not in pyproj
    for dep in pyproj["project"].get("dependencies", []):
        assert "<" in dep, f"Runtime dependency missing upper bound: {dep}"
    for group_deps in pyproj["project"].get("optional-dependencies", {}).values():
        for dep in group_deps:
            assert "<" in dep, f"Optional dependency missing upper bound: {dep}"
