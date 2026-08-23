"""Combine latency and mechanism evidence into one verdict.

VERIFIED requires both: latency improved beyond the noise floor AND the
predicted mechanism was observed. Latency alone is correlation, not causation.

    latency \\ mechanism   confirmed     refuted       unverifiable/not_checked
    improved              VERIFIED      INCONCLUSIVE  INCONCLUSIVE
    regressed             REGRESSED     REGRESSED     REGRESSED
    within_noise          INCONCLUSIVE  INCONCLUSIVE  INCONCLUSIVE
    unknown               INCONCLUSIVE  INCONCLUSIVE  INCONCLUSIVE
"""

from dataclasses import dataclass, field
from typing import Optional

from .plan_evidence import CONFIRMED, NOT_CHECKED, REFUTED, UNVERIFIABLE

VERIFIED = "VERIFIED"
REGRESSED = "REGRESSED"
INCONCLUSIVE = "INCONCLUSIVE"


@dataclass
class Verdict:
    status: str
    latency_status: str
    mechanism_status: str
    rationale: str
    caveats: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "latency_status": self.latency_status,
            "mechanism_status": self.mechanism_status,
            "rationale": self.rationale,
            "caveats": self.caveats,
        }


def evaluate(
    latency_comparison: dict,
    postcondition=None,
    repetitions: int = 0,
    workload_artificially_cacheable: bool = False,
    cacheability_reason: Optional[str] = None,
    db_metrics: Optional[dict] = None,
    experiment_mode: str = "cumulative",
    applied_suggestions=(),
    baseline_state_matches: Optional[bool] = None,
    reversibility: Optional[dict] = None,
) -> Verdict:
    latency_status = (latency_comparison or {}).get("status", "unknown")
    mechanism_status = postcondition.status if postcondition is not None else NOT_CHECKED

    caveats = []
    if repetitions < 2:
        caveats.append(
            f"Only {repetitions} repetition(s) per condition: there is no noise floor to "
            "compare against, so no difference here can be called real."
        )
    if workload_artificially_cacheable:
        caveats.append(
            "Workload is effectively single-tuple, so cache-sensitive rules (R5, R7, R8) "
            "cannot be judged fairly on it"
            + (f": {cacheability_reason}" if cacheability_reason else ".")
        )
    if baseline_state_matches is False:
        caveats.append(
            "The baseline was captured against a different database state than this run "
            "started from (schema, GUCs, or table statistics changed). Non-reversible "
            "operations such as ANALYZE/VACUUM invalidate an older baseline; recapture one."
        )
    if experiment_mode == "cumulative" and len(applied_suggestions) > 1:
        caveats.append(
            "Cumulative experiment: this measures the MARGINAL effect of the newest "
            f"suggestion given {list(applied_suggestions)[:-1]} already applied, not its "
            "independent effect. Do not quote it as a standalone number."
        )
    if reversibility and reversibility.get("requires_fresh_baseline"):
        caveats.append(
            f"This change is {reversibility.get('reversibility')}: "
            f"{reversibility.get('effect')} The next experiment cannot reuse the baseline "
            f"this one was compared against -- capture a new one. {reversibility.get('undo')}"
        )
    if db_metrics and db_metrics.get("stats_reset_detected"):
        caveats.append(
            "PostgreSQL statistics were reset during the window; database-side deltas for "
            "this run are not trustworthy."
        )

    if latency_status == "regressed":
        return Verdict(
            REGRESSED, latency_status, mechanism_status,
            _regression_rationale(latency_comparison, postcondition), caveats)

    if latency_status == "improved" and mechanism_status == CONFIRMED and repetitions >= 2:
        return Verdict(
            VERIFIED, latency_status, mechanism_status,
            f"Latency improved by {_pct(latency_comparison)} beyond the measured noise floor, "
            f"and the predicted mechanism was observed: {postcondition.detail}",
            caveats)

    return Verdict(
        INCONCLUSIVE, latency_status, mechanism_status,
        _inconclusive_rationale(latency_status, mechanism_status, latency_comparison, postcondition,
                                repetitions),
        caveats)


def _pct(comparison: dict) -> str:
    pct = (comparison or {}).get("pct_change")
    return f"{abs(pct):.1f}%" if pct is not None else "an unquantified amount"


def _regression_rationale(comparison, postcondition) -> str:
    base = (f"Latency got worse by {_pct(comparison)}, beyond the measured noise floor. "
            "The change should be rolled back or re-examined.")
    if postcondition is not None and postcondition.status == CONFIRMED:
        base += (f" The predicted mechanism did occur ({postcondition.detail}) -- the mechanism "
                 "itself is counterproductive on this workload.")
    return base


def _inconclusive_rationale(latency_status, mechanism_status, comparison, postcondition,
                            repetitions) -> str:
    detail = postcondition.detail if postcondition is not None else "no postcondition was evaluated"

    if repetitions < 2:
        return ("Not enough repetitions to separate signal from noise; no claim can be made "
                "about this suggestion either way.")

    if latency_status == "improved" and mechanism_status == REFUTED:
        return (f"Latency improved by {_pct(comparison)}, but the predicted mechanism did NOT "
                f"occur: {detail} The improvement is therefore not attributable to this "
                "suggestion -- treat it as ambiguous, not as a success.")

    if latency_status == "improved" and mechanism_status in (UNVERIFIABLE, NOT_CHECKED):
        return (f"Latency improved by {_pct(comparison)}, but the mechanism could not be "
                f"verified: {detail} Improvement is unattributed, so this is not a "
                "confirmed win.")

    if latency_status == "within_noise" and mechanism_status == CONFIRMED:
        return (f"Useful null result: the predicted mechanism DID occur ({detail}) but latency "
                "did not move beyond run-to-run noise. The change works as designed and buys "
                "nothing measurable on this workload.")

    if latency_status == "within_noise":
        return (f"No latency change beyond noise, and the mechanism was not confirmed: {detail}")

    if latency_status == "unknown":
        reason = (comparison or {}).get("reason") or "insufficient samples"
        return f"Latency comparison could not be computed ({reason}); mechanism: {detail}"

    return f"Latency {latency_status}; mechanism {mechanism_status}: {detail}"
