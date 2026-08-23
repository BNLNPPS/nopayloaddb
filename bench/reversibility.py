"""Which changes can be undone, and which invalidate an existing baseline.

ANALYZE and VACUUM are one-way: there is no restoring the previous statistics
or dead tuples, so a baseline taken before them is no longer comparable.
"""

import re

REVERSIBLE = "reversible"
IRREVERSIBLE = "irreversible"
ADVISORY = "advisory"
UNKNOWN = "unknown"

_CLASSIFIERS = (
    (re.compile(r"^\s*ANALYZE\b", re.I), IRREVERSIBLE,
     "Table statistics are overwritten; the previous statistics cannot be restored.",
     "DROP/restore is impossible -- capture a fresh baseline after running it."),
    (re.compile(r"^\s*VACUUM\b", re.I), IRREVERSIBLE,
     "Dead tuples are removed and the visibility map is updated; neither can be undone.",
     "Capture a fresh baseline. Note this also changes R7's outcome, since index-only "
     "scans depend on the visibility map."),
    (re.compile(r"^\s*REINDEX\s+CONCURRENTLY\b", re.I), IRREVERSIBLE,
     "The index is physically rebuilt; bloat present in the baseline is gone.",
     "Semantically equivalent afterwards, but the physical state differs -- prefer a "
     "fresh baseline."),
    (re.compile(r"^\s*CREATE\s+INDEX\s+CONCURRENTLY\s+(\w+)", re.I), REVERSIBLE,
     "A new index was created.",
     "Undo with DROP INDEX CONCURRENTLY {name}."),
    (re.compile(r"^\s*ALTER\s+SYSTEM\s+SET\s+([\w.]+)", re.I), REVERSIBLE,
     "A cluster GUC was written to postgresql.auto.conf.",
     "Undo with ALTER SYSTEM RESET {name} followed by pg_reload_conf(). Note this "
     "competes with ConfigMap-managed configuration -- postgresql.auto.conf wins."),
    (re.compile(r"^\s*SET\s+([\w.]+)", re.I), REVERSIBLE,
     "A session-scoped GUC was set.",
     "Undo with RESET {name}."),
    (re.compile(r"^\s*ALTER\s+TABLE\s+\"?(\w+)\"?\s+SET\s*\(", re.I), REVERSIBLE,
     "A per-table storage parameter was changed.",
     "Undo with ALTER TABLE {name} RESET (<parameter>)."),
    (re.compile(r"^\s*ALTER\s+INDEX\b", re.I), REVERSIBLE,
     "An index was renamed.",
     "Undo by renaming it back."),
    (re.compile(r"^\s*CREATE\s+TEMP\s+TABLE\b", re.I), ADVISORY,
     "Session-scoped temp table; never auto-applied and gone at disconnect.",
     "Nothing to undo."),
)


def classify(safe_sql):
    """Classify one statement's reversibility."""
    if not safe_sql or not safe_sql.strip():
        return {
            "safe_sql": safe_sql,
            "reversibility": ADVISORY,
            "requires_fresh_baseline": False,
            "effect": "Advisory suggestion with no SQL to apply.",
            "undo": "Nothing to undo.",
        }

    for pattern, kind, effect, undo in _CLASSIFIERS:
        match = pattern.match(safe_sql)
        if match:
            name = match.group(1) if match.groups() else ""
            return {
                "safe_sql": safe_sql.strip(),
                "reversibility": kind,
                "requires_fresh_baseline": kind == IRREVERSIBLE,
                "effect": effect,
                "undo": undo.format(name=name) if name else undo,
            }

    return {
        "safe_sql": safe_sql.strip(),
        "reversibility": UNKNOWN,
        "requires_fresh_baseline": True,
        "effect": "Statement not recognised by the reversibility classifier.",
        "undo": "Unknown -- treat as irreversible and capture a fresh baseline.",
    }


def baseline_advice(safe_sql) -> str:
    """One line for the operator, printed before a comparison is built."""
    info = classify(safe_sql)
    if info["requires_fresh_baseline"]:
        return (
            f"IRREVERSIBLE ({info['effect']}) Any baseline captured before this was applied "
            f"is no longer a valid comparison point -- {info['undo']}"
        )
    return f"Reversible: {info['undo']}"
