"""Pytest configuration and test import bootstrap for hermes-verifiable-math."""

import importlib.util
import os
import sys

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PLUGIN_DIR not in sys.path:
    sys.path.insert(0, PLUGIN_DIR)

# Ensure the plugin module is loaded as a package
import __init__ as plugin_module

tools = plugin_module.tools
hooks = plugin_module.hooks
schemas = plugin_module.schemas
lean_core = plugin_module.lean_core
sieve_core = plugin_module.sieve_core
elliptic_core = plugin_module.elliptic_core
