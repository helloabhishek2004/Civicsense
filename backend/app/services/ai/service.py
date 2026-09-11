import datetime
import uuid

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.orm import Session, joinedload

from app.core.errors import EntityNotFoundError
from app.core.logging import get_logger
from app.models.ai_analysis import AIAnalysis
from app.models.ai_job import AIJob, AIJobEvent
from app.models.enums import AIJobStatus, AIProcessingStage, ReportStatus, VerificationDecision
from app.models.report import Report
from app.models.verification import Verification
from app.repositories.report_repo import report_repository
from app.schemas.ai_analysis import AIAnalysisRead
from app.schemas.ai_job import AIHealthResponse, AIJobRead, ReportAIResult
from app.schemas.ai_metrics import AIMetricsResponse, MetricItem
from app.schemas.verification import VerificationRead
from app.services.ai.demo_processor import DeterministicDemoProcessor
from app.services.reports.lifecycle import ReportLifecycleManager

logger = get_logger(__name__)


class AIService:
    """Domain service managing AI pipeline orchestration, jobs, event audits, and analytics."""

    def __init__(self) -> None:
        self.processor = DeterministicDemoProcessor()

    def _resolve_report(self, db: Session, identifier: str) -> Report:
        """Fetch report by UUID or tracking ID."""
        try:
            r_uuid = uuid.UUID(identifier)
            report = report_repository.get_by_id_with_relations(db, r_uuid)
            if report:
                return report
        except ValueError:
            pass

        report = report_repository.get_by_tracking_id(db, identifier)
        if not report:
            raise EntityNotFoundError("Report", identifier)
        return report

    def process_report(self, db: Session, identifier: str) -> AIJob:
        """Trigger deterministic AI processing on a report."""
        report = self._resolve_report(db, identifier)

        # Idempotency check: prevent duplicate active jobs
        active_stmt = (
            select(AIJob)
            .where(
                AIJob.report_id == report.id,
                AIJob.status.in_([AIJobStatus.QUEUED, AIJobStatus.PROCESSING]),
            )
            .order_by(desc(AIJob.created_at))
        )
        existing_active = db.scalars(active_stmt).first()
        if existing_active:
            logger.info(
                "Report %s already has active AI job %s", report.tracking_id, existing_active.id
            )
            return existing_active

        # Transition report to AI_PROCESSING if allowed
        if ReportLifecycleManager.is_valid_transition(report.status, ReportStatus.AI_PROCESSING):
            report_repository.update_status(db, report, ReportStatus.AI_PROCESSING)

        # Create new AIJob
        job = AIJob(
            report_id=report.id,
            status=AIJobStatus.QUEUED,
            current_stage=AIProcessingStage.INTAKE_VALIDATION,
            execution_mode="synchronous_demo",
            processor_name="Deterministic Demo Processor",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Execute processor synchronously
        completed_job = self.processor.process(db, job, report)
        return completed_job

    def get_report_ai(self, db: Session, identifier: str) -> ReportAIResult:
        """Fetch the latest AI assessment, active job status, and human verification summary."""
        report = self._resolve_report(db, identifier)

        # Fetch latest job with events
        job_stmt = (
            select(AIJob)
            .options(joinedload(AIJob.events))
            .where(AIJob.report_id == report.id)
            .order_by(desc(AIJob.created_at))
        )
        latest_job = db.scalars(job_stmt).unique().first()

        latest_ai = report.ai_analyses[0] if report.ai_analyses else None
        latest_ver = report.verifications[0] if report.verifications else None

        return ReportAIResult(
            report_id=report.id,
            tracking_id=report.tracking_id,
            report_status=report.status.value,
            latest_job=AIJobRead.model_validate(latest_job) if latest_job else None,
            ai_analysis=AIAnalysisRead.model_validate(latest_ai) if latest_ai else None,
            verification=VerificationRead.model_validate(latest_ver) if latest_ver else None,
            execution_mode="synchronous_prototype",
            processor_name="CivicSense Prototype AI (Deterministic Demo Processor)",
        )

    def get_report_events(self, db: Session, identifier: str) -> list[AIJobEvent]:
        """Fetch all persistent AI job events for a report in chronological order."""
        report = self._resolve_report(db, identifier)
        stmt = (
            select(AIJobEvent)
            .where(AIJobEvent.report_id == report.id)
            .order_by(AIJobEvent.created_at.asc())
        )
        return list(db.scalars(stmt).all())

    def list_jobs(
        self,
        db: Session,
        status: AIJobStatus | None = None,
        stage: AIProcessingStage | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[AIJob], int]:
        """List AI jobs paginated with optional filtering."""
        count_stmt = select(func.count()).select_from(AIJob)
        stmt = select(AIJob).options(joinedload(AIJob.events)).order_by(desc(AIJob.created_at))

        if status:
            count_stmt = count_stmt.where(AIJob.status == status)
            stmt = stmt.where(AIJob.status == status)
        if stage:
            count_stmt = count_stmt.where(AIJob.current_stage == stage)
            stmt = stmt.where(AIJob.current_stage == stage)

        total = db.scalar(count_stmt) or 0
        items = list(db.scalars(stmt.offset(skip).limit(limit)).unique().all())
        return items, total

    def get_metrics(self, db: Session) -> AIMetricsResponse:
        """Compute real database-backed operational AI metrics without hardcoded values."""
        now = datetime.datetime.now(datetime.UTC)

        # 1. Job counts
        total_jobs_count = db.scalar(select(func.count()).select_from(AIJob)) or 0
        completed_jobs_count = (
            db.scalar(
                select(func.count()).select_from(AIJob).where(AIJob.status == AIJobStatus.COMPLETED)
            )
            or 0
        )
        failed_jobs_count = (
            db.scalar(
                select(func.count()).select_from(AIJob).where(AIJob.status == AIJobStatus.FAILED)
            )
            or 0
        )
        active_jobs_count = (
            db.scalar(
                select(func.count())
                .select_from(AIJob)
                .where(AIJob.status.in_([AIJobStatus.QUEUED, AIJobStatus.PROCESSING]))
            )
            or 0
        )
        awaiting_review_count = (
            db.scalar(
                select(func.count())
                .select_from(AIJob)
                .where(
                    AIJob.current_stage == AIProcessingStage.HUMAN_REVIEW,
                    AIJob.review_completed.is_(False),
                )
            )
            or 0
        )

        # 2. Average Latency (from AIJob completed duration in seconds converted to ms)
        completed_jobs = list(
            db.scalars(
                select(AIJob).where(
                    AIJob.status == AIJobStatus.COMPLETED,
                    AIJob.started_at.isnot(None),
                    AIJob.completed_at.isnot(None),
                )
            ).all()
        )
        if completed_jobs:
            total_lat_ms = sum(
                max(1.0, (j.completed_at - j.started_at).total_seconds() * 1000.0)
                for j in completed_jobs
            )
            avg_latency = total_lat_ms / len(completed_jobs)
        else:
            avg_latency = None

        # 3. AI Analysis counts & rates (sample size threshold >= 5)
        total_analyses = db.scalar(select(func.count()).select_from(AIAnalysis)) or 0
        if total_analyses >= 5:
            low_conf_count = (
                db.scalar(
                    select(func.count()).select_from(AIAnalysis).where(AIAnalysis.confidence < 0.70)
                )
                or 0
            )
            low_conf_rate = round((low_conf_count / total_analyses) * 100.0, 1)

            disagree_count = (
                db.scalar(
                    select(func.count())
                    .select_from(AIAnalysis)
                    .where(AIAnalysis.evidence_agreement < 0.60)
                )
                or 0
            )
            disagree_rate = round((disagree_count / total_analyses) * 100.0, 1)
        else:
            low_conf_rate = None
            disagree_rate = None

        # 4. Human Override Rate (comparing verifications with ai_analyses
        # on same report, threshold >= 5)
        total_ai_verifications = (
            db.scalar(
                select(func.count(distinct(Verification.id)))
                .select_from(Verification)
                .join(Report, Verification.report_id == Report.id)
                .join(AIAnalysis, AIAnalysis.report_id == Report.id)
            )
            or 0
        )
        if total_ai_verifications >= 5:
            override_stmt = (
                select(func.count(distinct(Verification.id)))
                .select_from(Verification)
                .join(Report, Verification.report_id == Report.id)
                .join(AIAnalysis, AIAnalysis.report_id == Report.id)
                .where(
                    Verification.decision.in_(
                        [VerificationDecision.CORRECTED, VerificationDecision.REJECTED]
                    ),
                )
            )
            override_count = db.scalar(override_stmt) or 0
            human_override_rate = round((override_count / total_ai_verifications) * 100.0, 1)
        else:
            human_override_rate = None

        return AIMetricsResponse(
            total_jobs=MetricItem(
                value=total_jobs_count,
                sample_size=total_jobs_count,
                display_state="AVAILABLE",
            ),
            completed_jobs=MetricItem(
                value=completed_jobs_count,
                sample_size=total_jobs_count,
                display_state="AVAILABLE",
            ),
            failed_jobs=MetricItem(
                value=failed_jobs_count,
                sample_size=total_jobs_count,
                display_state="AVAILABLE",
            ),
            active_jobs=MetricItem(
                value=active_jobs_count,
                sample_size=total_jobs_count,
                display_state="AVAILABLE",
            ),
            awaiting_human_review=MetricItem(
                value=awaiting_review_count,
                sample_size=total_jobs_count,
                display_state="AVAILABLE",
            ),
            avg_processing_latency_ms=MetricItem(
                value=round(avg_latency, 1) if avg_latency is not None else None,
                sample_size=completed_jobs_count,
                display_state="AVAILABLE" if avg_latency is not None else "INSUFFICIENT_DATA",
            ),
            low_confidence_rate=MetricItem(
                value=low_conf_rate,
                sample_size=total_analyses,
                display_state="AVAILABLE" if low_conf_rate is not None else "INSUFFICIENT_DATA",
            ),
            modality_disagreement_rate=MetricItem(
                value=disagree_rate,
                sample_size=total_analyses,
                display_state="AVAILABLE" if disagree_rate is not None else "INSUFFICIENT_DATA",
            ),
            human_override_rate=MetricItem(
                value=human_override_rate,
                sample_size=total_ai_verifications,
                display_state="AVAILABLE"
                if human_override_rate is not None
                else "INSUFFICIENT_DATA",
            ),
            time_window="ALL_TIME",
            generated_at=now,
        )

    def get_health(self, db: Session) -> AIHealthResponse:
        """Truthful capability and health disclosure."""
        now = datetime.datetime.now(datetime.UTC)
        active_count = (
            db.scalar(
                select(func.count())
                .select_from(AIJob)
                .where(AIJob.status.in_([AIJobStatus.QUEUED, AIJobStatus.PROCESSING]))
            )
            or 0
        )
        total_completed = (
            db.scalar(
                select(func.count()).select_from(AIJob).where(AIJob.status == AIJobStatus.COMPLETED)
            )
            or 0
        )
        last_completed = db.scalar(select(func.max(AIJob.completed_at)).select_from(AIJob))

        stages = [s.value for s in AIProcessingStage]

        return AIHealthResponse(
            status="available",
            execution_mode="synchronous_prototype",
            processor_mode="deterministic_demo",
            processor_name="CivicSense Prototype AI (Deterministic Demo Processor)",
            production_model_available=False,
            background_worker_available=False,
            supported_stages=stages,
            active_jobs_count=active_count,
            total_jobs_processed=total_completed,
            last_processed_at=last_completed,
            timestamp=now,
        )


ai_service = AIService()
