import base64
import datetime
import hashlib
import uuid
from pathlib import Path

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.logging import get_logger
from app.models.enums import PriorityLevel, ReportStatus
from app.models.evidence import Evidence
from app.models.report import Report
from app.repositories.base import BaseRepository
from app.schemas.report import ReportCreate

logger = get_logger(__name__)


def generate_tracking_id() -> str:
    """Generate human-readable report tracking ID, e.g. REP-202609-A1B2C3."""
    now = datetime.datetime.now(datetime.UTC)
    month_prefix = now.strftime("%Y%m")
    unique_suffix = uuid.uuid4().hex[:6].upper()
    return f"REP-{month_prefix}-{unique_suffix}"


class ReportRepository(BaseRepository[Report]):
    """Data access repository for citizen reports."""

    def __init__(self) -> None:
        super().__init__(Report)

    def create(self, db: Session, schema: ReportCreate) -> tuple[Report, bool]:
        """Create a new report in SUBMITTED state with attached evidence.

        Returns a tuple of (report, is_created). If client_report_id was already
        ingested, returns (existing_report, False) for idempotent replay.
        """
        if schema.client_report_id is not None:
            existing = self.get_by_id_with_relations(db, schema.client_report_id)
            if existing is not None:
                return existing, False

        tracking_id = generate_tracking_id()
        report_id = schema.client_report_id or uuid.uuid4()

        edge_metadata_dump = (
            schema.edge_metadata.model_dump() if schema.edge_metadata is not None else None
        )

        category = schema.category
        if not category and schema.edge_metadata and schema.edge_metadata.category_hint:
            category = schema.edge_metadata.category_hint

        report = Report(
            id=report_id,
            tracking_id=tracking_id,
            category=category,
            citizen_id=schema.citizen_id,
            citizen_name=schema.citizen_name,
            citizen_phone=schema.citizen_phone,
            citizen_email=schema.citizen_email,
            citizen_postal_code=schema.citizen_postal_code,
            status=ReportStatus.SUBMITTED,
            latitude=schema.location.latitude,
            longitude=schema.location.longitude,
            address_hint=schema.location.address_hint,
            description=schema.description,
            edge_metadata=edge_metadata_dump,
        )

        for ev in schema.evidence:
            storage_uri = ev.storage_uri
            file_hash = ev.file_hash
            mime_type = ev.mime_type or "image/jpeg"
            file_size_bytes = ev.file_size_bytes

            if ev.data_base64:
                try:
                    raw_bytes = base64.b64decode(ev.data_base64)
                    file_size_bytes = len(raw_bytes)
                    file_hash = hashlib.sha256(raw_bytes).hexdigest()

                    ext = ".jpg"
                    if raw_bytes.startswith(b"\x89PNG"):
                        ext = ".png"
                        mime_type = "image/png"
                    elif raw_bytes.startswith(b"RIFF") and b"WEBP" in raw_bytes[:16]:
                        ext = ".webp"
                        mime_type = "image/webp"

                    settings = get_settings()
                    upload_dir = Path(settings.UPLOADS_DIR)
                    upload_dir.mkdir(parents=True, exist_ok=True)

                    stem = Path(storage_uri).stem[:24] if storage_uri else "img"
                    clean_stem = "".join(c for c in stem if c.isalnum() or c in ("-", "_"))
                    filename = f"rep_{report.id}_{clean_stem}_{uuid.uuid4().hex[:6]}{ext}"
                    filepath = upload_dir / filename
                    with open(filepath, "wb") as f:
                        f.write(raw_bytes)

                    storage_uri = f"/uploads/{filename}"
                except Exception as exc:
                    logger.warning(
                        "Evidence storage failed for report %s: %s — "
                        "report will be created without persisted evidence file",
                        report.id,
                        exc,
                    )

            evidence_model = Evidence(
                report_id=report.id,
                evidence_type=ev.evidence_type,
                storage_uri=storage_uri,
                file_hash=file_hash,
                mime_type=mime_type,
                file_size_bytes=file_size_bytes,
                metadata_json=ev.metadata_json,
            )
            report.evidences.append(evidence_model)

        db.add(report)
        db.commit()
        db.refresh(report)
        return report, True

    def get_by_id_with_relations(self, db: Session, report_id: uuid.UUID) -> Report | None:
        """Fetch report with eagerly loaded relations."""
        stmt = (
            select(Report)
            .options(
                joinedload(Report.evidences),
                joinedload(Report.ai_analyses),
                joinedload(Report.verifications),
                joinedload(Report.ai_jobs),
                joinedload(Report.assignments),
            )
            .where(Report.id == report_id)
        )
        return db.scalars(stmt).unique().first()

    def get_by_tracking_id(self, db: Session, tracking_id: str) -> Report | None:
        """Fetch report by human-readable tracking ID."""
        stmt = (
            select(Report)
            .options(
                joinedload(Report.evidences),
                joinedload(Report.ai_analyses),
                joinedload(Report.verifications),
                joinedload(Report.ai_jobs),
                joinedload(Report.assignments),
            )
            .where(Report.tracking_id == tracking_id)
        )
        return db.scalars(stmt).unique().first()

    def list_reports(
        self,
        db: Session,
        skip: int = 0,
        limit: int = 20,
        citizen_id: str | None = None,
        department: str | None = None,
        department_id: uuid.UUID | None = None,
        status: ReportStatus | None = None,
        category: str | None = None,
        priority: PriorityLevel | None = None,
        reassignment_required: bool | None = None,
        issue_id: uuid.UUID | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Report], int]:
        """List reports with total count, supporting dynamic sorting and filtering."""
        count_stmt = select(func.count()).select_from(Report)
        if citizen_id is not None:
            count_stmt = count_stmt.where(Report.citizen_id == citizen_id)
        if department_id is not None:
            count_stmt = count_stmt.where(Report.department_id == department_id)
        elif department is not None:
            count_stmt = count_stmt.where(Report.department == department)
        if status is not None:
            count_stmt = count_stmt.where(Report.status == status)
        if category is not None:
            count_stmt = count_stmt.where(Report.category == category)
        if priority is not None:
            count_stmt = count_stmt.where(Report.priority == priority)
        if reassignment_required is not None:
            count_stmt = count_stmt.where(Report.reassignment_required == reassignment_required)
        if issue_id is not None:
            count_stmt = count_stmt.where(Report.issue_id == issue_id)

        total = db.scalar(count_stmt) or 0

        stmt = select(Report).options(
            joinedload(Report.evidences),
            joinedload(Report.ai_analyses),
            joinedload(Report.verifications),
            joinedload(Report.ai_jobs),
            joinedload(Report.assignments),
        )
        if citizen_id is not None:
            stmt = stmt.where(Report.citizen_id == citizen_id)
        if department_id is not None:
            stmt = stmt.where(Report.department_id == department_id)
        elif department is not None:
            stmt = stmt.where(Report.department == department)
        if status is not None:
            stmt = stmt.where(Report.status == status)
        if category is not None:
            stmt = stmt.where(Report.category == category)
        if priority is not None:
            stmt = stmt.where(Report.priority == priority)
        if reassignment_required is not None:
            stmt = stmt.where(Report.reassignment_required == reassignment_required)
        if issue_id is not None:
            stmt = stmt.where(Report.issue_id == issue_id)

        order_col = Report.created_at
        clean_sort_by = (sort_by or "created_at").lower()
        if clean_sort_by in ("tracking_id", "trackingid"):
            order_col = Report.tracking_id
        elif clean_sort_by in ("category",):
            order_col = Report.category
        elif clean_sort_by in ("status",):
            order_col = Report.status
        elif clean_sort_by in ("priority",):
            order_col = Report.priority
        elif clean_sort_by in ("updated_at", "updatedat"):
            order_col = Report.updated_at
        elif clean_sort_by in ("address_hint", "addresshint"):
            order_col = Report.address_hint

        is_asc = (sort_order or "desc").lower() == "asc"
        primary_order = asc(order_col) if is_asc else desc(order_col)
        stmt = stmt.order_by(primary_order, desc(Report.created_at)).offset(skip).limit(limit)
        items = list(db.scalars(stmt).unique().all())
        return items, total

    def update_status(
        self,
        db: Session,
        report: Report,
        new_status: ReportStatus,
        department: str | None = None,
        department_id: uuid.UUID | None = None,
        assigned_officer: str | None = None,
        priority: PriorityLevel | None = None,
        reassignment_required: bool | None = None,
    ) -> Report:
        """Update report status, department assignment, and commit timestamp."""
        report.status = new_status
        if department is not None:
            report.department = department
        if department_id is not None:
            report.department_id = department_id
        if assigned_officer is not None:
            report.assigned_officer = assigned_officer
        if priority is not None:
            report.priority = priority
        if reassignment_required is not None:
            report.reassignment_required = reassignment_required
        report.updated_at = datetime.datetime.now(datetime.UTC)
        db.commit()
        db.refresh(report)
        return report


report_repository = ReportRepository()
