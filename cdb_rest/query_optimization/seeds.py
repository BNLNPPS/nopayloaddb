# Five high-priority query fingerprints watched from day one, independent of the latency/IO threshold.

from dataclasses import dataclass


@dataclass(frozen=True)
class SeededFingerprint:
    name: str
    endpoint: str
    # Matched against pg_stat_statements.query with ILIKE.
    pattern: str
    explainable: bool


SEEDED_FINGERPRINTS = (
    SeededFingerprint(
        name="payloadiovs_lateral_join",
        endpoint="GET /api/cdb_rest/payloadiovs/",
        pattern='%JOIN LATERAL%"PayloadIOV"%',
        explainable=True,
    ),
    SeededFingerprint(
        name="payloadiovs_orm_orderby",
        endpoint="GET /api/cdb_rest/payloadiovs_orm_orderby/",
        pattern='%SELECT DISTINCT ON%"PayloadIOV"%',
        explainable=True,
    ),
    SeededFingerprint(
        name="payloadiovs_orm_max",
        endpoint="GET /api/cdb_rest/payloadiovs_orm_max/",
        pattern='%MAX("PayloadIOV"."comb_iov")%',
        explainable=True,
    ),
    SeededFingerprint(
        name="bulk_payload_iov_insert",
        endpoint="POST /api/cdb_rest/bulk_piov",
        pattern='INSERT INTO "PayloadIOV"%',
        explainable=False,
    ),
    SeededFingerprint(
        name="global_tag_clone",
        endpoint="POST /api/cdb_rest/cloneGlobalTag/{source}/{target}",
        pattern='INSERT INTO "PayloadList"%',
        explainable=False,
    ),
)

SEED_PATTERNS = [seed.pattern for seed in SEEDED_FINGERPRINTS]

_EXPLAINABLE_PATTERNS = frozenset(
    seed.pattern for seed in SEEDED_FINGERPRINTS if seed.explainable
)


def match(query_text):
    # The seeded fingerprint for this statement, or None. Mirrors the collector's ILIKE.
    if not query_text:
        return None
    haystack = query_text.upper()
    for seed in SEEDED_FINGERPRINTS:
        if _ilike(haystack, seed.pattern.upper()):
            return seed
    return None


def _ilike(haystack, pattern):
    """Minimal ILIKE for the '%'-delimited patterns above (no _ wildcards)."""
    parts = pattern.split("%")
    position = 0

    if parts[0]:
        if not haystack.startswith(parts[0]):
            return False
        position = len(parts[0])

    trailing = parts[-1]
    middles = parts[1:-1] if len(parts) > 1 else []

    for part in middles:
        if not part:
            continue
        found = haystack.find(part, position)
        if found == -1:
            return False
        position = found + len(part)

    if trailing:
        if not haystack.endswith(trailing) or len(haystack) - len(trailing) < position:
            return False

    return True


def is_explainable(query_text):
    # True when a plan can safely be captured: a plain SELECT, not a write-path seed.
    if not query_text:
        return False

    normalized = query_text.lstrip().lower()
    if not normalized.startswith("select "):
        return False
    if ";" in query_text:
        return False

    seed = match(query_text)
    if seed is not None and not seed.explainable:
        return False

    return True
