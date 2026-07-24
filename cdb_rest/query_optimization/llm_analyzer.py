"""Layer 3 of the AI analysis engine: LLM-augmented analysis.

Only invoked when a query plan is a genuine candidate (already crossed the
collector's latency/IO threshold) but Layer 2's 13 deterministic rules found
nothing to say about it. The LLM's job here is narrow: name a bottleneck and,
optionally, propose one safe, pre-approved-shape SQL statement. Every
safe_sql value is re-validated against the same allow-list the rule engine
uses before it is ever stored -- the system prompt telling the model "never
suggest schema changes" is a hint, not a guarantee.
"""

import logging
from typing import Optional

from .explain_plan_rule_engine import PlanNode, RuleContext, Suggestion, validate_safe_sql
from .llm_backend import BaseLLMBackend

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are a PostgreSQL optimization expert for a HEP conditions database.\n"
    "The schema has: GlobalTag -> PayloadList -> PayloadIOV "
    "(covering_idx on payload_list_id, comb_iov DESC NULLS LAST). "
    "PayloadIOV has ~15M rows.\n"
    "NEVER suggest DROP, TRUNCATE, ALTER TABLE, or schema changes.\n"
    'Return ONLY valid JSON: {"bottleneck": "...", "suggestion": "...", '
    '"safe_sql": "..." or null}'
)

# The LLM only sees cases that already defeated 13 hand-derived, domain-grounded
# rules -- by definition a novel pattern, which is exactly where an LLM is least
# reliable. Its output is therefore trusted less than a rule-engine suggestion
# (0.5 vs. typically 0.7-0.95) so operators triage it accordingly, and it always
# still requires human approval before anything is applied.
LLM_SUGGESTION_CONFIDENCE = 0.5


def _flatten_plan(node: PlanNode, depth: int = 0) -> str:
    label = node.node_type
    if node.relation:
        label += f" on {node.relation}"
    line = (
        f"{'  ' * depth}{label} "
        f"(plan_rows={node.plan_rows}, actual_rows={node.actual_rows}, "
        f"time_ms={node.actual_time_ms:.2f}, shared_hit={node.shared_hit_blocks}, "
        f"shared_read={node.shared_read_blocks})"
    )
    child_lines = [_flatten_plan(child, depth + 1) for child in node.children]
    return "\n".join([line, *child_lines])


def build_user_prompt(root: PlanNode, context: RuleContext) -> str:
    return (
        f"Query took {context.mean_exec_time:.2f}ms across {context.calls} calls.\n"
        f"EXPLAIN (ANALYZE, BUFFERS) plan:\n{_flatten_plan(root)}"
    )


def analyze_with_llm(
    root: PlanNode, context: RuleContext, backend: Optional[BaseLLMBackend]
) -> Optional[Suggestion]:
    """Escalate a rule-less plan to the LLM layer. Returns None if the backend
    is absent, fails, or returns something that doesn't parse as a usable
    suggestion -- callers should treat that identically to "nothing found"."""
    if backend is None:
        return None

    user_prompt = build_user_prompt(root, context)
    try:
        raw = backend.complete_json(SYSTEM_PROMPT, user_prompt)
    except Exception:
        logger.exception("LLM backend raised while analyzing plan for queryid=%s", context.queryid)
        return None

    if not isinstance(raw, dict):
        return None

    bottleneck = raw.get("bottleneck")
    suggestion_text = raw.get("suggestion")
    if not bottleneck or not suggestion_text:
        return None

    raw_safe_sql = raw.get("safe_sql")
    validated_sql = validate_safe_sql(raw_safe_sql) if raw_safe_sql else None

    return Suggestion(
        rule_id="LLM",
        category="OTHER",
        priority="MEDIUM",
        message=f"{bottleneck} -- {suggestion_text}",
        safe_sql=validated_sql,
        confidence=LLM_SUGGESTION_CONFIDENCE,
        source="llm",
    )
