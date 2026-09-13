"""CivicSense Dynamic Issue Priority Ranking Engine.

Computes a transparent, normalized priority score for each Issue based on:
- severity_score:       max severity across linked reports' AI analyses
- report_volume_score:  log-scaled report count with saturation
- unique_reporter_score: count of distinct citizen identities
- recency_score:        exponential decay from most recent report
- persistence_score:    how long the issue has remained active

All components are normalized to [0, 1]. The final score is 0-100.
"""

import datetime
import math
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.ai_analysis import AIAnalysis
from app.models.enums import PriorityLevel, SeverityLevel
from app.models.issue import Issue
from app.models.report import Report

logger = get_logger(__name__)

FORMULA_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Severity normalization (conservative mapping)
# ---------------------------------------------------------------------------

_SEVERITY_MAP: dict[str, float] = {
    SeverityLevel.LOW.value: 0.25,
    SeverityLevel.MEDIUM.value: 0.50,
    SeverityLevel.HIGH.value: 0.75,
    SeverityLevel.CRITICAL.value: 1.00,
}

# Default severity when no AI analysis exists for any report
_DEFAULT_SEVERITY = 0.25

# How much repeated severe reports contribute beyond the max.
# After the first CRITICAL report, additional reports add at most this fraction.
_SEVERITY_REPEAT_CEILING = 0.10


@dataclass
class PriorityBreakdown:
    """Detailed breakdown of how the priority score was computed."""

    severity_score: float
    report_volume_score: float
    unique_reporter_score: float
    recency_score: float
    persistence_score: float
    weighted_sum: float
    final_score_0_100: float
    priority_level: str
    formula_version: str
    report_count: int
    unique_reporter_count: int
    latest_report_at: str | None
    issue_age_days: float
    max_severity: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity_score": round(self.severity_score, 4),
            "report_volume_score": round(self.report_volume_score, 4),
            "unique_reporter_score": round(self.unique_reporter_score, 4),
            "recency_score": round(self.recency_score, 4),
            "persistence_score": round(self.persistence_score, 4),
            "weighted_sum": round(self.weighted_sum, 4),
            "final_score_0_100": round(self.final_score_0_100, 2),
            "priority_level": self.priority_level,
            "formula_version": self.formula_version,
            "report_count": self.report_count,
            "unique_reporter_count": self.unique_reporter_count,
            "latest_report_at": self.latest_report_at,
            "issue_age_days": round(self.issue_age_days, 2),
            "max_severity": self.max_severity,
        }


@dataclass
class PriorityConfig:
    severity_weight: float
    volume_weight: float
    unique_reporter_weight: float
    recency_weight: float
    persistence_weight: float
    volume_saturation: int
    recency_half_life_days: float
    persistence_max_days: float
    high_threshold: float
    medium_threshold: float
    low_threshold: float


def _load_config() -> PriorityConfig:
    s = get_settings()
    return PriorityConfig(
        severity_weight=s.PRIORITY_SEVERITY_WEIGHT,
        volume_weight=s.PRIORITY_VOLUME_WEIGHT,
        unique_reporter_weight=s.PRIORITY_UNIQUE_REPORTER_WEIGHT,
        recency_weight=s.PRIORITY_RECENCY_WEIGHT,
        persistence_weight=s.PERSISTENCE_WEIGHT,
        volume_saturation=s.PRIORITY_VOLUME_SATURATION,
        recency_half_life_days=s.PRIORITY_RECENCY_HALF_LIFE_DAYS,
        persistence_max_days=s.PERSISTENCE_MAX_DAYS,
        high_threshold=s.PRIORITY_HIGH_THRESHOLD,
        medium_threshold=s.PRIORITY_MEDIUM_THRESHOLD,
        low_threshold=s.PRIORITY_LOW_THRESHOLD,
    )


# ---------------------------------------------------------------------------
# Component: severity_score
# ---------------------------------------------------------------------------

def severity_score(
    db: Session,
    issue: Issue,
) -> tuple[float, str | None, int]:
    """Compute severity score from the max severity across linked reports' AI analyses.

    Uses a conservative aggregation: the maximum severity dominates, with a
    small ceiling bonus for repeated severe reports.

    Returns (score, max_severity_label, report_count_with_severity).
    """
    stmt = (
        select(AIAnalysis.severity)
        .join(Report, AIAnalysis.report_id == Report.id)
        .where(
            Report.issue_id == issue.id,
            AIAnalysis.severity.isnot(None),
        )
    )
    severities = [s for s in db.scalars(stmt).all() if s is not None]

    if not severities:
        return _DEFAULT_SEVERITY, None, 0

    # Map to numeric values
    numeric = [
        _SEVERITY_MAP.get(s.value if hasattr(s, "value") else str(s), 0.25)
        for s in severities
    ]
    max_val = max(numeric)
    max_sev = severities[numeric.index(max_val)]
    max_label = max_sev.value if hasattr(max_sev, "value") else str(max_sev)

    # Conservative ceiling: repeated severe reports add at most _SEVERITY_REPEAT_CEILING
    severe_count = sum(1 for v in numeric if v >= 0.75)
    if severe_count > 1 and max_val >= 0.75:
        bonus = min(_SEVERITY_REPEAT_CEILING, (severe_count - 1) * 0.02)
        max_val = min(1.0, max_val + bonus)

    return max_val, max_label, len(numeric)


# ---------------------------------------------------------------------------
# Component: report_volume_score
# ---------------------------------------------------------------------------

def report_volume_score(report_count: int, saturation: int) -> float:
    """Log-scaled report volume with saturation.

    At saturation count, score approaches 0.95.
    Formula: 1 - exp(-count / (saturation / 3))
    """
    if report_count <= 0:
        return 0.0
    decay = saturation / 3.0
    return 1.0 - math.exp(-report_count / decay)


# ---------------------------------------------------------------------------
# Component: unique_reporter_score
# ---------------------------------------------------------------------------

def unique_reporter_score(
    db: Session,
    issue: Issue,
    report_count: int,
) -> tuple[float, int]:
    """Count distinct citizen identities and normalize.

    Anonymous reports (citizen_id IS NULL) are counted once as a single
    "anonymous contributor" — they do NOT inflate the unique reporter count.

    Returns (score, unique_count).
    """
    # Count distinct non-null citizen_ids
    stmt = (
        select(func.count(func.distinct(Report.citizen_id)))
        .where(
            Report.issue_id == issue.id,
            Report.citizen_id.isnot(None),
            Report.citizen_id != "",
        )
    )
    distinct_citizens = db.scalar(stmt) or 0

    # Check if there are any anonymous reports
    anon_stmt = (
        select(func.count())
        .select_from(Report)
        .where(
            Report.issue_id == issue.id,
            (Report.citizen_id.is_(None)) | (Report.citizen_id == ""),
        )
    )
    has_anonymous = (db.scalar(anon_stmt) or 0) > 0

    unique_count = distinct_citizens + (1 if has_anonymous else 0)

    # Normalize: 1 reporter = 0.3, 5 reporters = ~0.85, 10+ = ~0.98
    if unique_count <= 0:
        return 0.0, 0
    score = 1.0 - math.exp(-unique_count / 3.0)
    return score, unique_count


# ---------------------------------------------------------------------------
# Component: recency_score
# ---------------------------------------------------------------------------

def recency_score(
    latest_report_at: datetime.datetime | None,
    half_life_days: float,
    now: datetime.datetime | None = None,
) -> float:
    """Exponential decay from the most recent report timestamp.

    Half-life is configurable (default 7 days).
    A report from today scores ~1.0; one half-life ago scores 0.5.
    """
    if latest_report_at is None:
        return 0.0

    now = now or datetime.datetime.now(datetime.UTC)
    if latest_report_at.tzinfo is None:
        latest_report_at = latest_report_at.replace(tzinfo=datetime.UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.UTC)

    age_seconds = (now - latest_report_at).total_seconds()
    age_days = age_seconds / 86400.0

    # Half-life decay: score = 0.5^(age / half_life)
    decay_constant = math.log(2) / half_life_days
    return math.exp(-decay_constant * age_days)


# ---------------------------------------------------------------------------
# Component: persistence_score
# ---------------------------------------------------------------------------

def persistence_score(
    issue_created_at: datetime.datetime,
    latest_report_at: datetime.datetime | None,
    issue_status: str,
    max_days: float,
    now: datetime.datetime | None = None,
) -> float:
    """Measure how long the issue has remained active.

    - Increases with age up to a cap (max_days).
    - Closed/resolved issues get a penalty (score frozen at their persistence at closure).
    - Recent reports boost the score (active issues score higher).
    """
    now = now or datetime.datetime.now(datetime.UTC)
    if issue_created_at.tzinfo is None:
        issue_created_at = issue_created_at.replace(tzinfo=datetime.UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=datetime.UTC)

    age_days = (now - issue_created_at).total_seconds() / 86400.0

    # Base persistence: saturates at max_days
    base = 1.0 - math.exp(-age_days / (max_days / 3.0))

    # Closed issues: freeze at their persistence level, no recency boost
    if issue_status in ("CLOSED", "RESOLVED", "RESOLUTION_VERIFIED"):
        return base

    # Active issues: recency of latest report boosts persistence
    if latest_report_at and latest_report_at.tzinfo is None:
        latest_report_at = latest_report_at.replace(tzinfo=datetime.UTC)

    if latest_report_at:
        recency_days = (now - latest_report_at).total_seconds() / 86400.0
        recency_factor = math.exp(-recency_days / (max_days / 2.0))
        return min(1.0, base * 0.7 + 0.3 * recency_factor)

    return base


# ---------------------------------------------------------------------------
# Priority level mapping
# ---------------------------------------------------------------------------

def _score_to_level(score: float, config: PriorityConfig) -> str:
    """Map a 0-100 priority score to PriorityLevel using configurable thresholds."""
    if score >= config.high_threshold:
        return PriorityLevel.CRITICAL
    if score >= config.medium_threshold:
        return PriorityLevel.HIGH
    if score >= config.low_threshold:
        return PriorityLevel.MEDIUM
    return PriorityLevel.LOW


# ---------------------------------------------------------------------------
# Main computation
# ---------------------------------------------------------------------------

def compute_issue_priority(
    db: Session,
    issue: Issue,
    config: PriorityConfig | None = None,
) -> PriorityBreakdown:
    """Compute the full priority breakdown for a single Issue.

    This is the core function. It queries the database for linked reports
    and their AI analyses, then computes all 5 normalized components.
    """
    cfg = config or _load_config()
    now = datetime.datetime.now(datetime.UTC)

    # --- Severity ---
    sev_score, max_sev_label, sev_report_count = severity_score(db, issue)

    # --- Report count and latest report ---
    report_count = issue.report_count

    latest_stmt = (
        select(func.max(Report.created_at))
        .where(Report.issue_id == issue.id)
    )
    latest_report_at = db.scalar(latest_stmt)

    # SQLite may return naive datetimes; ensure timezone-aware
    if latest_report_at is not None and latest_report_at.tzinfo is None:
        latest_report_at = latest_report_at.replace(tzinfo=datetime.UTC)

    # --- Volume ---
    vol_score = report_volume_score(report_count, cfg.volume_saturation)

    # --- Unique reporters ---
    ur_score, unique_count = unique_reporter_score(db, issue, report_count)

    # --- Recency ---
    rec_score = recency_score(latest_report_at, cfg.recency_half_life_days, now)

    # --- Persistence ---
    created_at = issue.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=datetime.UTC)
    issue_age_days = (now - created_at).total_seconds() / 86400.0
    pers_score = persistence_score(
        created_at, latest_report_at, issue.status,
        cfg.persistence_max_days, now,
    )

    # --- Weighted combination ---
    weighted = (
        cfg.severity_weight * sev_score
        + cfg.volume_weight * vol_score
        + cfg.unique_reporter_weight * ur_score
        + cfg.recency_weight * rec_score
        + cfg.persistence_weight * pers_score
    )

    # Clamp and scale to 0-100
    final_score = max(0.0, min(1.0, weighted)) * 100.0
    priority_level = _score_to_level(final_score, cfg)

    breakdown = PriorityBreakdown(
        severity_score=sev_score,
        report_volume_score=vol_score,
        unique_reporter_score=ur_score,
        recency_score=rec_score,
        persistence_score=pers_score,
        weighted_sum=weighted,
        final_score_0_100=final_score,
        priority_level=priority_level,
        formula_version=FORMULA_VERSION,
        report_count=report_count,
        unique_reporter_count=unique_count,
        latest_report_at=(
            latest_report_at.isoformat().replace("+00:00", "Z")
            if latest_report_at else None
        ),
        issue_age_days=issue_age_days,
        max_severity=max_sev_label,
    )

    return breakdown


def apply_priority_to_issue(
    db: Session,
    issue: Issue,
    config: PriorityConfig | None = None,
) -> PriorityBreakdown:
    """Compute priority and write it to the Issue record.

    This is the function called by recomputation triggers.
    Returns the breakdown for audit/logging.
    """
    breakdown = compute_issue_priority(db, issue, config)

    issue.priority_score = breakdown.final_score_0_100
    issue.priority_level = breakdown.priority_level
    issue.priority_computed_at = datetime.datetime.now(datetime.UTC)
    issue.priority_breakdown = breakdown.to_dict()
    db.flush()

    logger.info(
        "Priority computed: issue=%s score=%.2f level=%s reports=%d severity=%s",
        issue.id, breakdown.final_score_0_100, breakdown.priority_level,
        breakdown.report_count, breakdown.max_severity,
    )

    return breakdown


# ---------------------------------------------------------------------------
# Batch recomputation
# ---------------------------------------------------------------------------

def recompute_all_priorities(
    db: Session,
    *,
    batch_size: int = 100,
    status_filter: str | None = "OPEN",
) -> dict[str, Any]:
    """Recompute priority for all issues in batches.

    Safe to run concurrently — each issue is computed independently.
    Returns summary statistics.
    """
    cfg = _load_config()

    stmt = select(Issue.id)
    if status_filter:
        stmt = stmt.where(Issue.status == status_filter)
    stmt = stmt.order_by(Issue.created_at)

    issue_ids = list(db.scalars(stmt).all())
    total = len(issue_ids)
    processed = 0
    errors = 0
    level_counts: dict[str, int] = {}

    for i in range(0, total, batch_size):
        batch_ids = issue_ids[i : i + batch_size]
        for issue_id in batch_ids:
            issue = db.get(Issue, issue_id)
            if issue is None:
                errors += 1
                continue
            try:
                breakdown = apply_priority_to_issue(db, issue, cfg)
                level_counts[breakdown.priority_level] = (
                    level_counts.get(breakdown.priority_level, 0) + 1
                )
                processed += 1
            except Exception as exc:
                logger.warning("Priority recompute failed for issue %s: %s", issue_id, exc)
                errors += 1

        db.flush()

    summary = {
        "total": total,
        "processed": processed,
        "errors": errors,
        "level_distribution": level_counts,
        "batch_size": batch_size,
        "status_filter": status_filter,
    }

    logger.info(
        "Batch priority recompute complete: total=%d processed=%d errors=%d distribution=%s",
        total, processed, errors, level_counts,
    )

    return summary
