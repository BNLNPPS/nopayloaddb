"""Load the rule engine without importing cdb_rest, which pulls Django in."""

import importlib.util
import os

_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "cdb_rest", "query_optimization", "explain_plan_rule_engine.py",
)

_spec = importlib.util.spec_from_file_location("_rule_engine", _PATH)
rule_engine = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rule_engine)
