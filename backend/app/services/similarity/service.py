"""CivicSense Similarity Engine (multimodal visual + hardening).

Implements Report-to-Issue matching via multimodal similarity scoring:
- Text cosine similarity (MiniLM embeddings or fallback)
- Visual cosine similarity (MobileNetV3-Small embeddings — auxiliary signal only)
- Geographic proximity (Haversine distance decay)
- Category compatibility (exact, Other bridge, or mismatch)

Visual similarity is an auxiliary matching signal. The current vision model
is trained for classification; retrieval/duplicate quality is not yet validated.
Human review is required for uncertain matches.

Three-tier routing:
  score >= HIGH_THRESHOLD  -> AUTO_LINK   (report linked to existing issue)
  score >= MEDIUM_THRESHOLD -> CANDIDATE   (pending human review, no issue created)
  score < MEDIUM_THRESHOLD  -> NEW_ISSUE   (new issue created)

Safety policy:
  In strict mode, visual similarity cannot independently promote to AUTO_LINK.
  If visual causes AUTO_LINK but text-only score is below the threshold,
  the match is downgraded to CANDIDATE for human review.

Every scoring decision produces a persistent ReportIssueMatch audit record.
"""

import math
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.issue import Issue
from app.models.report import Report
from app.models.report_issue_match import ReportIssueMatch

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MatchAction:
    AUTO_LINK = "AUTO_LINK"
    CANDIDATE = "CANDIDATE"
    NEW_ISSUE = "NEW_ISSUE"


class MatchStatus:
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class MatchComponent:
    text_similarity: float
    distance_meters: float
    category_match: float
    visual_similarity: float
    raw_score: float
    weighted_score: float


@dataclass
class SimilarityMatch:
    issue_id: uuid.UUID | None
    action: str
    score: float
    components: MatchComponent
    reasoning: list[str]
    text_only_score: float = 0.0
    multimodal_score: float = 0.0
    visual_used: bool = False
    visual_influenced_decision: bool = False
    routing_reason: str = ""


@dataclass
class SimilarityConfig:
    text_weight: float
    distance_weight: float
    category_weight: float
    radius_meters: float
    high_threshold: float
    medium_threshold: float
    embedding_model_version: str
    visual_weight: float = 0.0
    model_dir: Any = None  # Path, resolved from config


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------

def _load_config() -> SimilarityConfig:
    s = get_settings()
    # Use original weights for text-only mode; multimodal weights only when visual is available
    return SimilarityConfig(
        text_weight=s.SIMILARITY_TEXT_WEIGHT,
        distance_weight=s.SIMILARITY_DISTANCE_WEIGHT,
        category_weight=s.SIMILARITY_CATEGORY_WEIGHT,
        visual_weight=s.SIMILARITY_VISUAL_WEIGHT if s.VISION_ENABLED else 0.0,
        radius_meters=s.SIMILARITY_RADIUS_METERS,
        high_threshold=s.SIMILARITY_HIGH_THRESHOLD,
        medium_threshold=s.SIMILARITY_MEDIUM_THRESHOLD,
        embedding_model_version=s.SIMILARITY_EMBEDDING_MODEL_VERSION,
        model_dir=s.similarity_model_path,
    )


# ---------------------------------------------------------------------------
# Math utilities (all outputs proven in [0, 1])
# ---------------------------------------------------------------------------

def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points in meters."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors.  Returns 0.0 for invalid inputs."""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def _running_average(
    old_avg: list[float] | None,
    new_embedding: list[float],
    old_count: int,
) -> list[float]:
    """Compute true running average of embeddings with L2 re-normalization.

    Uses the formula: new_avg = (old_avg * old_count + new_embedding) / (old_count + 1)

    When old_avg is None or old_count <= 0, returns a copy of new_embedding.
    The result is L2-normalized to maintain unit norm for cosine similarity.
    """
    if old_avg is None or old_count <= 0:
        return list(new_embedding)

    if len(old_avg) != len(new_embedding):
        logger.warning(
            "Embedding dimension mismatch during averaging: old=%d new=%d; using new embedding",
            len(old_avg), len(new_embedding),
        )
        return list(new_embedding)

    count = max(old_count, 1)
    avg = [
        (a * count + b) / (count + 1)
        for a, b in zip(old_avg, new_embedding, strict=True)
    ]

    # Re-normalize to unit L2 norm for cosine similarity compatibility
    norm = math.sqrt(sum(x * x for x in avg))
    if norm > 1e-9:
        avg = [x / norm for x in avg]

    return avg


def distance_score(distance_meters: float, radius_meters: float) -> float:
    """Exponential decay mapping distance to [0, 1] similarity.

    Returns 1.0 at zero distance, approaches 0.0 beyond radius.
    """
    if distance_meters <= 0:
        return 1.0
    decay_rate = radius_meters / 3.0
    return math.exp(-distance_meters / decay_rate)


def category_score(report_cat: str | None, issue_cat: str) -> float:
    """Category compatibility: exact=1.0, 'Other' bridge=0.5, mismatch=0.0."""
    if not report_cat:
        return 0.0
    if report_cat == issue_cat:
        return 1.0
    if issue_cat == "Other" or report_cat == "Other":
        return 0.5
    return 0.0


def generate_issue_title(description: str, category: str | None) -> str:
    """Short issue title from report description."""
    first_line = description.strip().split("\n")[0][:120]
    if category:
        return f"{category}: {first_line}"
    return first_line


# ---------------------------------------------------------------------------
# Bounding-box candidate search
# ---------------------------------------------------------------------------

def _find_nearby_issues(
    db: Session,
    latitude: float,
    longitude: float,
    radius_meters: float,
    category: str | None = None,
) -> list[Issue]:
    """Find OPEN issues within bounding box, refined by exact Haversine."""
    # Defensive check: Null Island (0.0, 0.0) or unlocalized reports cannot be spatially matched.
    if abs(latitude) < 1e-5 and abs(longitude) < 1e-5:
        logger.warning("Rejecting spatial candidate search at (0, 0) Null Island coordinates")
        return []

    lat_delta = radius_meters / 111_320.0
    lon_delta = radius_meters / (111_320.0 * max(math.cos(math.radians(latitude)), 0.01))

    lat_min = latitude - lat_delta
    lat_max = latitude + lat_delta
    lon_min = longitude - lon_delta
    lon_max = longitude + lon_delta

    stmt = select(Issue).where(
        Issue.status == "OPEN",
        Issue.primary_latitude >= lat_min,
        Issue.primary_latitude <= lat_max,
        Issue.primary_longitude >= lon_min,
        Issue.primary_longitude <= lon_max,
    )

    candidates = list(db.scalars(stmt).all())

    nearby = []
    for issue in candidates:
        dist = haversine_distance_meters(
            latitude, longitude,
            issue.primary_latitude, issue.primary_longitude,
        )
        if dist <= radius_meters:
            nearby.append(issue)

    return nearby


# ---------------------------------------------------------------------------
# Embedding (graceful fallback when MiniLM unavailable)
# ---------------------------------------------------------------------------

def _get_encoder_model_dir() -> str:
    """Return the resolved MiniLM model directory path string."""
    cfg = _load_config()
    return str(cfg.model_dir)


def _compute_text_embedding(description: str) -> list[float] | None:
    """Compute a text embedding using MiniLM if available.

    Returns None silently when the model directory is missing, unloadable,
    or raises any exception — the engine degrades to distance+category only.
    """
    try:
        from app.services.ai.semantic_text_encoder import MiniLMTextEncoder

        model_dir = _get_encoder_model_dir()
        encoder = MiniLMTextEncoder(model_dir=model_dir)
        if encoder.status.value == "READY":
            emb = encoder.embed(description, normalize=True)
            result: list[float] = [float(x) for x in emb]
            return result
    except Exception:
        logger.debug("MiniLM encoder unavailable; falling back to no embedding")
    return None


def _generate_visual_embedding(report: Report) -> None:
    """Generate visual embedding from the first evidence image attached to the report.

    Sets report.image_embedding and report.vision_model_version if successful.
    Gracefully degrades to no embedding on any failure.
    """
    settings = get_settings()
    if not settings.VISION_ENABLED:
        return

    # Find the first IMAGE evidence with a storage_uri
    image_evidence = None
    for ev in report.evidences:
        if ev.storage_uri and ev.mime_type and ev.mime_type.startswith("image/"):
            image_evidence = ev
            break

    if image_evidence is None:
        return

    try:
        from app.services.ai.visual_embedding_service import get_visual_embedding_service

        service = get_visual_embedding_service()
        if not service.is_ready:
            logger.info(
                "Visual embedding skipped for report %s: service not ready (%s)",
                report.tracking_id,
                service.status.get("load_error", "unknown"),
            )
            return

        embedding = service.extract_embedding_from_storage_uri(
            image_evidence.storage_uri, uploads_dir=settings.UPLOADS_DIR
        )
        if embedding is not None:
            report.image_embedding = embedding
            ckpt_name = settings.VISION_MODEL_CHECKPOINT or "exp_b"
            report.vision_model_version = f"mobilenet_v3_small-{ckpt_name}"
            logger.debug(
                "Visual embedding generated for report %s: dim=%d",
                report.tracking_id,
                len(embedding),
            )
        else:
            logger.info(
                "Visual embedding extraction returned None for report %s (evidence=%s)",
                report.tracking_id,
                image_evidence.storage_uri,
            )
    except Exception as exc:
        logger.warning(
            "Visual embedding generation failed for report %s: %s",
            report.tracking_id,
            exc,
        )


def validate_model_availability() -> dict[str, Any]:
    """Validate MiniLM and vision models at startup and return status report.

    Returns a dict with: model_dir, exists, status, embedding_dim, degraded_mode,
    vision_model status.
    """
    cfg = _load_config()
    model_dir = cfg.model_dir
    report: dict[str, Any] = {
        "model_dir": str(model_dir),
        "model_dir_exists": model_dir.is_dir(),
        "status": "UNAVAILABLE",
        "embedding_dim": None,
        "degraded_mode": True,
    }

    if not model_dir.is_dir():
        logger.warning(
            "MiniLM model directory not found: %s — running in degraded mode (no text embeddings)",
            model_dir,
        )
        return report

    try:
        from app.services.ai.semantic_text_encoder import MiniLMTextEncoder

        encoder = MiniLMTextEncoder(model_dir=str(model_dir))
        report["status"] = encoder.status.value
        if encoder.status.value == "READY":
            report["embedding_dim"] = 384
            report["degraded_mode"] = False
            logger.info(
                "MiniLM model loaded: dir=%s version=%s dim=%d status=READY",
                model_dir,
                cfg.embedding_model_version,
                384,
            )
        else:
            report["load_error"] = encoder.load_error
            logger.warning(
                "MiniLM model load failed: dir=%s error=%s — degraded mode",
                model_dir,
                encoder.load_error,
            )
    except Exception as exc:
        report["status"] = "LOAD_FAILED"
        report["load_error"] = str(exc)
        logger.warning(
            "MiniLM model validation exception: %s — degraded mode",
            exc,
        )

    # Check vision model status
    try:
        from app.services.ai.visual_embedding_service import get_visual_embedding_service

        vision_service = get_visual_embedding_service()
        report["vision_model"] = vision_service.status
    except Exception as exc:
        report["vision_model"] = {"model_ready": False, "load_error": str(exc)}

    return report


# ---------------------------------------------------------------------------
# Core scoring
# ---------------------------------------------------------------------------

def match_report_to_issue(
    db: Session,
    report: Report,
    config: SimilarityConfig | None = None,
) -> SimilarityMatch | None:
    """Score the new report against all nearby OPEN issues.

    Returns the best SimilarityMatch or None when no candidates exist.
    All component scores are provably in [0, 1].
    """
    cfg = config or _load_config()

    candidates = _find_nearby_issues(
        db,
        latitude=report.latitude,
        longitude=report.longitude,
        radius_meters=cfg.radius_meters,
        category=report.category,
    )

    if not candidates:
        return None

    report_emb = report.text_embedding
    best_match: SimilarityMatch | None = None
    best_score = -1.0

    settings = get_settings()
    visual_safety_mode = getattr(settings, "VISUAL_SAFETY_MODE", "strict")

    for issue in candidates:
        # Text similarity (normalized cosine)
        if report_emb and issue.text_embedding:
            text_sim = cosine_similarity(report_emb, issue.text_embedding)
        else:
            text_sim = 0.0

        # Visual similarity (cosine of image embeddings)
        vis_sim = 0.0
        has_visual = (
            cfg.visual_weight > 0
            and report.image_embedding
            and issue.image_embedding
        )
        if has_visual:
            vis_sim = cosine_similarity(report.image_embedding, issue.image_embedding)

        # Distance (exponential decay, output in [0, 1])
        dist = haversine_distance_meters(
            report.latitude, report.longitude,
            issue.primary_latitude, issue.primary_longitude,
        )
        dist_sc = distance_score(dist, cfg.radius_meters)

        # Category (output in {0.0, 0.5, 1.0})
        cat_sc = category_score(report.category, issue.category)

        # Dynamic weight normalization:
        # When visual embeddings are available, normalize all 4 weights to sum to 1.0
        # When visual is missing, use only text+distance+category
        if has_visual:
            total_w = (
                cfg.text_weight + cfg.distance_weight
                + cfg.category_weight + cfg.visual_weight
            )
            if total_w > 0:
                norm_tw = cfg.text_weight / total_w
                norm_dw = cfg.distance_weight / total_w
                norm_cw = cfg.category_weight / total_w
                norm_vw = cfg.visual_weight / total_w
            else:
                norm_tw, norm_dw, norm_cw, norm_vw = 0.40, 0.35, 0.25, 0.0
        else:
            total_w = cfg.text_weight + cfg.distance_weight + cfg.category_weight
            if total_w > 0:
                norm_tw = cfg.text_weight / total_w
                norm_dw = cfg.distance_weight / total_w
                norm_cw = cfg.category_weight / total_w
            else:
                norm_tw, norm_dw, norm_cw = 0.40, 0.35, 0.25
            norm_vw = 0.0

        # Multimodal score (includes visual when available)
        weighted = (
            norm_tw * text_sim
            + norm_dw * dist_sc
            + norm_cw * cat_sc
            + norm_vw * vis_sim
        )
        weighted = max(0.0, min(1.0, weighted))

        # Text-only score (visual excluded, weights re-normalized)
        text_only_total = cfg.text_weight + cfg.distance_weight + cfg.category_weight
        if text_only_total > 0:
            text_only_score = (
                (cfg.text_weight / text_only_total) * text_sim
                + (cfg.distance_weight / text_only_total) * dist_sc
                + (cfg.category_weight / text_only_total) * cat_sc
            )
        else:
            text_only_score = 0.0
        text_only_score = max(0.0, min(1.0, text_only_score))

        # Visual safety policy: determine if visual influenced routing
        visual_used = has_visual and vis_sim > 0
        visual_influenced = False
        routing_reason = ""

        reasoning_parts: list[str] = []
        if report_emb and issue.text_embedding:
            reasoning_parts.append(f"text_similarity={text_sim:.4f}")
        else:
            reasoning_parts.append("text_similarity=N/A(no_embeddings)")
        if has_visual:
            reasoning_parts.append(f"visual_similarity={vis_sim:.4f}")
        else:
            reasoning_parts.append("visual_similarity=N/A(no_image_embeddings)")
        reasoning_parts.append(f"distance={dist:.1f}m,dist_score={dist_sc:.4f}")
        reasoning_parts.append(
            f"category_match={cat_sc:.1f}(report={report.category},issue={issue.category})"
        )
        reasoning_parts.append(f"weighted_score={weighted:.4f}")
        reasoning_parts.append(f"text_only_score={text_only_score:.4f}")

        components = MatchComponent(
            text_similarity=text_sim,
            distance_meters=dist,
            category_match=cat_sc,
            visual_similarity=vis_sim,
            raw_score=weighted,
            weighted_score=weighted,
        )

        if weighted > best_score:
            best_score = weighted
            # Safety gate: Incompatible categories (both explicitly specified, non-Other,
            # and distinct) must NEVER be AUTO_LINKED or treated as duplicate candidates.
            is_category_conflict = (
                report.category is not None
                and issue.category is not None
                and report.category != "Other"
                and issue.category != "Other"
                and report.category != issue.category
            )
            if is_category_conflict:
                action = MatchAction.NEW_ISSUE
                routing_reason = "category_mismatch"
                reasoning_parts.append(
                    f"ACTION=NEW_ISSUE(category_mismatch: {report.category} vs {issue.category})"
                )
            elif weighted >= cfg.high_threshold:
                # Visual safety policy (strict mode):
                # If visual similarity promoted this to AUTO_LINK but text-only
                # would not have reached AUTO_LINK threshold, downgrade to CANDIDATE.
                if (
                    visual_safety_mode == "strict"
                    and visual_used
                    and text_only_score < cfg.high_threshold
                    and text_only_score < (weighted - 0.01)
                ):
                    action = MatchAction.CANDIDATE
                    visual_influenced = True
                    routing_reason = "visual_downgraded_to_candidate"
                    reasoning_parts.append(
                        f"ACTION=CANDIDATE(visual_safety: text_only={text_only_score:.4f} "
                        f"< high_threshold={cfg.high_threshold}, "
                        f"multimodal={weighted:.4f} downgraded from AUTO_LINK)"
                    )
                else:
                    action = MatchAction.AUTO_LINK
                    routing_reason = "multimodal_threshold"
                    reasoning_parts.append(f"ACTION=AUTO_LINK(threshold={cfg.high_threshold})")
            elif weighted >= cfg.medium_threshold:
                action = MatchAction.CANDIDATE
                routing_reason = "below_high_threshold"
                reasoning_parts.append(f"ACTION=CANDIDATE(threshold={cfg.medium_threshold})")
            else:
                action = MatchAction.NEW_ISSUE
                routing_reason = "below_medium_threshold"
                reasoning_parts.append(f"ACTION=NEW_ISSUE(below={cfg.medium_threshold})")

            best_match = SimilarityMatch(
                issue_id=issue.id,
                action=action,
                score=weighted,
                components=components,
                reasoning=reasoning_parts,
                text_only_score=text_only_score,
                multimodal_score=weighted,
                visual_used=visual_used,
                visual_influenced_decision=visual_influenced,
                routing_reason=routing_reason,
            )

    return best_match


# ---------------------------------------------------------------------------
# Audit record creation
# ---------------------------------------------------------------------------

def _create_match_record(
    db: Session,
    report: Report,
    match: SimilarityMatch,
    *,
    status: str = MatchStatus.PENDING,
) -> ReportIssueMatch:
    """Persist a ReportIssueMatch audit row."""
    record = ReportIssueMatch(
        id=uuid.uuid4(),
        report_id=report.id,
        issue_id=match.issue_id,
        action=match.action,
        status=status,
        combined_score=match.score,
        text_similarity=match.components.text_similarity,
        distance_meters=match.components.distance_meters,
        category_match=match.components.category_match,
        visual_similarity=match.components.visual_similarity,
        reasoning=match.reasoning,
        embedding_model_version=report.embedding_model_version,
    )
    db.add(record)
    return record


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def process_similarity_match(
    db: Session,
    report: Report,
    config: SimilarityConfig | None = None,
) -> SimilarityMatch:
    """Full similarity pipeline: embed, score, decide, and persist.

    Every report submission produces exactly one ReportIssueMatch audit row.
    CANDIDATE matches do NOT create a new Issue — the report remains unlinked
    until a human approves or rejects the candidate.
    """
    cfg = config or _load_config()

    # Generate text embedding if report doesn't have one
    if report.text_embedding is None and report.description:
        embedding = _compute_text_embedding(report.description)
        if embedding is not None:
            report.text_embedding = embedding
            report.embedding_model_version = cfg.embedding_model_version
            db.flush()

    # Generate visual embedding from evidence image if available and not already present
    if report.image_embedding is None and report.evidences:
        _generate_visual_embedding(report)

    # Find best match
    match = match_report_to_issue(db, report, cfg)

    if match is None:
        # No nearby issues -> create new issue
        new_issue = Issue(
            id=uuid.uuid4(),
            title=generate_issue_title(report.description, report.category),
            category=report.category or "Other",
            status="OPEN",
            primary_latitude=report.latitude,
            primary_longitude=report.longitude,
            report_count=1,
            text_embedding=report.text_embedding,
            embedding_model_version=cfg.embedding_model_version,
            image_embedding=report.image_embedding,
            vision_model_version=report.vision_model_version,
        )
        db.add(new_issue)
        db.flush()
        report.issue_id = new_issue.id
        db.flush()

        # Audit record: score=0.0, no candidates found
        match = SimilarityMatch(
            issue_id=new_issue.id,
            action=MatchAction.NEW_ISSUE,
            score=0.0,
            components=MatchComponent(
                text_similarity=0.0, distance_meters=0.0,
                category_match=0.0, visual_similarity=0.0,
                raw_score=0.0, weighted_score=0.0,
            ),
            reasoning=["No nearby issues found. Created new issue."],
        )
        _create_match_record(db, report, match, status=MatchStatus.APPROVED)
        db.flush()

        # Recompute priority for new issue
        try:
            from app.services.priority.service import apply_priority_to_issue
            apply_priority_to_issue(db, new_issue)
        except Exception:
            logger.debug("Priority recompute skipped for new issue %s", new_issue.id)

        logger.info(
            "New issue created: issue_id=%s category=%s lat=%.6f lon=%.6f",
            new_issue.id, new_issue.category,
            new_issue.primary_latitude, new_issue.primary_longitude,
        )
        return match

    # Execute the action based on match quality
    if match.action == MatchAction.AUTO_LINK:
        issue = db.get(Issue, match.issue_id)
        if issue is None:
            raise ValueError(f"Issue {match.issue_id} not found")

        report.issue_id = issue.id
        issue.report_count += 1
        issue.updated_at = report.updated_at

        # Update issue text embedding as running average
        if report.text_embedding:
            issue.text_embedding = _running_average(
                issue.text_embedding,
                report.text_embedding,
                issue.report_count - 1,
            )

        # Update issue image embedding as running average
        if report.image_embedding:
            if issue.image_embedding:
                issue.image_embedding = _running_average(
                    issue.image_embedding,
                    report.image_embedding,
                    issue.report_count - 1,
                )
            else:
                issue.image_embedding = list(report.image_embedding)
                issue.vision_model_version = report.vision_model_version

        db.flush()
        count = issue.report_count
        match.reasoning.append(f"AUTO_LINKED to issue {issue.id} (report_count={count})")
        _create_match_record(db, report, match, status=MatchStatus.APPROVED)
        db.flush()

        # Recompute priority after new report linked
        try:
            from app.services.priority.service import apply_priority_to_issue
            apply_priority_to_issue(db, issue)
        except Exception:
            logger.debug("Priority recompute skipped for issue %s", issue.id)

        logger.info(
            "Auto-linked report %s to issue %s (score=%.4f, count=%d)",
            report.id, issue.id, match.score, issue.report_count,
        )

    elif match.action == MatchAction.CANDIDATE:
        # Do NOT create a new issue or link the report (report.issue_id remains None).
        # Store a PENDING candidate match recording the candidate issue ID for human review.
        candidate_issue_id = match.issue_id
        match.reasoning.append(
            f"CANDIDATE match to issue {candidate_issue_id} "
            f"(score={match.score:.4f}, pending human review)"
        )
        _create_match_record(db, report, match, status=MatchStatus.PENDING)
        db.flush()

        logger.info(
            "Candidate match recorded: report=%s candidate_issue=%s score=%.4f (PENDING)",
            report.id, candidate_issue_id, match.score,
        )

    else:  # NEW_ISSUE
        new_issue = Issue(
            id=uuid.uuid4(),
            title=generate_issue_title(report.description, report.category),
            category=report.category or "Other",
            status="OPEN",
            primary_latitude=report.latitude,
            primary_longitude=report.longitude,
            report_count=1,
            text_embedding=report.text_embedding,
            embedding_model_version=cfg.embedding_model_version,
            image_embedding=report.image_embedding,
            vision_model_version=report.vision_model_version,
        )
        db.add(new_issue)
        db.flush()
        report.issue_id = new_issue.id
        db.flush()

        match.issue_id = new_issue.id
        score_str = f"{match.score:.4f}"
        if any("category_mismatch" in r for r in match.reasoning):
            match.reasoning.append(
                f"NEW_ISSUE created {new_issue.id} (category mismatch with nearby issue)"
            )
        else:
            match.reasoning.append(
                f"NEW_ISSUE created {new_issue.id} (score={score_str} below thresholds)"
            )
        _create_match_record(db, report, match, status=MatchStatus.APPROVED)
        db.flush()

        logger.info(
            "New issue created (low match): issue_id=%s score=%.4f",
            new_issue.id, match.score,
        )

    return match


# ---------------------------------------------------------------------------
# Metadata serialization
# ---------------------------------------------------------------------------

def store_match_metadata(
    report: Report,
    match: SimilarityMatch,
) -> dict[str, Any]:
    """Serialize match results for storage in report.edge_metadata."""
    return {
        "similarity_match": {
            "action": match.action,
            "score": round(match.score, 4),
            "matched_issue_id": str(match.issue_id) if match.issue_id else None,
            "components": {
                "text_similarity": round(match.components.text_similarity, 4),
                "visual_similarity": round(match.components.visual_similarity, 4),
                "distance_meters": round(match.components.distance_meters, 1),
                "category_match": round(match.components.category_match, 1),
            },
            "text_only_score": round(match.text_only_score, 4),
            "multimodal_score": round(match.multimodal_score, 4),
            "visual_used": match.visual_used,
            "visual_influenced_decision": match.visual_influenced_decision,
            "routing_reason": match.routing_reason,
            "reasoning": match.reasoning,
            "embedding_model_version": report.embedding_model_version,
            "vision_model_version": report.vision_model_version,
        }
    }
