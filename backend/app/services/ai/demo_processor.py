import datetime
import time

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.ai_analysis import AIAnalysis
from app.models.ai_job import AIJob, AIJobEvent
from app.models.enums import AIJobStatus, AIProcessingStage, ReportStatus
from app.models.report import Report
from app.services.ai.decision_engine import PrototypeDecisionEngine
from app.services.ai.exceptions import AIProcessingError
from app.services.ai.fusion_engine import PrototypeFusionEngine
from app.services.ai.text_analyzer import PrototypeTextPatternAnalyzer
from app.services.ai.vision_analyzer import PrototypeVisionAnalyzer
from app.services.reports.lifecycle import ReportLifecycleManager

logger = get_logger(__name__)


class DeterministicDemoProcessor:
    """Synchronous 8-stage deterministic prototype processor.

    DISCLAIMER: This executes genuine database-backed events and analysis records,
    using clearly disclosed deterministic rule-based algorithms rather than neural networks.
    """

    def __init__(self) -> None:
        self.vision_analyzer = PrototypeVisionAnalyzer()
        self.text_analyzer = PrototypeTextPatternAnalyzer()
        self.fusion_engine = PrototypeFusionEngine()
        self.decision_engine = PrototypeDecisionEngine()

    def process(self, db: Session, job: AIJob, report: Report) -> AIJob:
        """Execute the 8-stage processing pipeline."""
        start_time_all = time.perf_counter()
        job.status = AIJobStatus.PROCESSING
        job.started_at = datetime.datetime.now(datetime.UTC)
        db.commit()

        try:
            # -------------------------------------------------------------
            # Stage 1: INTAKE_VALIDATION
            # -------------------------------------------------------------
            stage_start = time.perf_counter()
            s1_started = datetime.datetime.now(datetime.UTC)
            job.current_stage = AIProcessingStage.INTAKE_VALIDATION
            db.commit()

            coord_valid = (-90.0 <= report.latitude <= 90.0) and (
                -180.0 <= report.longitude <= 180.0
            )
            desc_valid = bool(report.description and len(report.description.strip()) >= 3)

            if not (coord_valid and desc_valid):
                raise ValueError(
                    "Intake validation failed: invalid coordinates or empty description."
                )

            s1_dur_ms = max(1, int((time.perf_counter() - stage_start) * 1000))
            db.add(
                AIJobEvent(
                    job_id=job.id,
                    report_id=report.id,
                    stage=AIProcessingStage.INTAKE_VALIDATION,
                    status="COMPLETED",
                    message="Intake validation passed: coordinates and description verified.",
                    metadata_json={
                        "coordinates_valid": coord_valid,
                        "description_length": len(report.description),
                        "evidence_count": len(report.evidences),
                    },
                    started_at=s1_started,
                    completed_at=datetime.datetime.now(datetime.UTC),
                    duration_ms=s1_dur_ms,
                )
            )
            db.commit()

            # -------------------------------------------------------------
            # Stage 2: PREPROCESSING
            # -------------------------------------------------------------
            stage_start = time.perf_counter()
            s2_started = datetime.datetime.now(datetime.UTC)
            job.current_stage = AIProcessingStage.PREPROCESSING
            db.commit()

            evidence_summary = [
                {
                    "mime_type": ev.mime_type,
                    "size_bytes": ev.file_size_bytes,
                    "has_hash": bool(ev.file_hash),
                    "storage_uri": ev.storage_uri,
                }
                for ev in report.evidences
            ]

            s2_dur_ms = max(1, int((time.perf_counter() - stage_start) * 1000))
            db.add(
                AIJobEvent(
                    job_id=job.id,
                    report_id=report.id,
                    stage=AIProcessingStage.PREPROCESSING,
                    status="COMPLETED",
                    message="Preprocessing completed: Text and evidence cataloged.",
                    metadata_json={
                        "text_token_count_approx": len(report.description.split()),
                        "evidence_catalog": evidence_summary,
                    },
                    started_at=s2_started,
                    completed_at=datetime.datetime.now(datetime.UTC),
                    duration_ms=s2_dur_ms,
                )
            )
            db.commit()

            # -------------------------------------------------------------
            # Stage 3: VISION_ANALYSIS
            # -------------------------------------------------------------
            stage_start = time.perf_counter()
            s3_started = datetime.datetime.now(datetime.UTC)
            job.current_stage = AIProcessingStage.VISION_ANALYSIS
            db.commit()

            vision_res = self.vision_analyzer.analyze(report.evidences)
            s3_dur_ms = max(1, int((time.perf_counter() - stage_start) * 1000))

            db.add(
                AIJobEvent(
                    job_id=job.id,
                    report_id=report.id,
                    stage=AIProcessingStage.VISION_ANALYSIS,
                    status="COMPLETED",
                    message=(
                        f"Vision analysis: predicted '{vision_res['predicted_category']}' "
                        f"({vision_res['confidence']:.2f})."
                        if vision_res["has_image"]
                        else "Vision analysis bypassed: no image attached."
                    ),
                    metadata_json={
                        "engine": vision_res["engine"],
                        "has_image": vision_res["has_image"],
                        "predicted_category": vision_res["predicted_category"],
                        "predicted_severity": (
                            vision_res["predicted_severity"].value
                            if hasattr(vision_res["predicted_severity"], "value")
                            else vision_res["predicted_severity"]
                        ),
                        "confidence": vision_res["confidence"],
                        "features": vision_res["features"],
                    },
                    started_at=s3_started,
                    completed_at=datetime.datetime.now(datetime.UTC),
                    duration_ms=s3_dur_ms,
                )
            )
            db.commit()

            # -------------------------------------------------------------
            # Stage 4: TEXT_ANALYSIS
            # -------------------------------------------------------------
            stage_start = time.perf_counter()
            s4_started = datetime.datetime.now(datetime.UTC)
            job.current_stage = AIProcessingStage.TEXT_ANALYSIS
            db.commit()

            text_res = self.text_analyzer.analyze(report.description)
            s4_dur_ms = max(1, int((time.perf_counter() - stage_start) * 1000))

            db.add(
                AIJobEvent(
                    job_id=job.id,
                    report_id=report.id,
                    stage=AIProcessingStage.TEXT_ANALYSIS,
                    status="COMPLETED",
                    message=(
                        f"Text analysis: category '{text_res['predicted_category']}' "
                        f"({len(text_res['matched_terms'])} matches)."
                    ),
                    metadata_json={
                        "engine": text_res["engine"],
                        "predicted_category": text_res["predicted_category"],
                        "predicted_severity": text_res["predicted_severity"].value,
                        "confidence": text_res["confidence"],
                        "matched_terms": text_res["matched_terms"],
                        "urgency_signals": text_res["urgency_signals"],
                    },
                    started_at=s4_started,
                    completed_at=datetime.datetime.now(datetime.UTC),
                    duration_ms=s4_dur_ms,
                )
            )
            db.commit()

            # -------------------------------------------------------------
            # Stage 5: FUSION
            # -------------------------------------------------------------
            stage_start = time.perf_counter()
            s5_started = datetime.datetime.now(datetime.UTC)
            job.current_stage = AIProcessingStage.FUSION
            db.commit()

            fusion_res = self.fusion_engine.fuse(vision_res, text_res)
            s5_dur_ms = max(1, int((time.perf_counter() - stage_start) * 1000))

            db.add(
                AIJobEvent(
                    job_id=job.id,
                    report_id=report.id,
                    stage=AIProcessingStage.FUSION,
                    status="COMPLETED",
                    message=(
                        f"Multimodal fusion evaluated: concordance agreement = "
                        f"{fusion_res['modality_agreement']:.2f}."
                    ),
                    metadata_json={
                        "engine": fusion_res["engine"],
                        "category_agreement": fusion_res["category_agreement"],
                        "severity_agreement": fusion_res["severity_agreement"],
                        "modality_agreement": fusion_res["modality_agreement"],
                        "conflict_reasons": fusion_res["conflict_reasons"],
                    },
                    started_at=s5_started,
                    completed_at=datetime.datetime.now(datetime.UTC),
                    duration_ms=s5_dur_ms,
                )
            )
            db.commit()

            # -------------------------------------------------------------
            # Stage 6: DECISION
            # -------------------------------------------------------------
            stage_start = time.perf_counter()
            s6_started = datetime.datetime.now(datetime.UTC)
            job.current_stage = AIProcessingStage.DECISION
            db.commit()

            decision_res = self.decision_engine.decide(vision_res, text_res, fusion_res)
            s6_dur_ms = max(1, int((time.perf_counter() - stage_start) * 1000))

            db.add(
                AIJobEvent(
                    job_id=job.id,
                    report_id=report.id,
                    stage=AIProcessingStage.DECISION,
                    status="COMPLETED",
                    message=(
                        f"Decision: '{decision_res['suggested_category']}', "
                        f"Sev='{decision_res['suggested_severity'].value}', "
                        f"Review={decision_res['review_required']}."
                    ),
                    metadata_json={
                        "suggested_category": decision_res["suggested_category"],
                        "suggested_severity": decision_res["suggested_severity"].value,
                        "operational_priority": decision_res["operational_priority"].value,
                        "overall_confidence": decision_res["confidence"],
                        "review_required": decision_res["review_required"],
                        "review_reason": decision_res["review_reason"],
                        "decision_explanation": decision_res["decision_explanation"],
                    },
                    started_at=s6_started,
                    completed_at=datetime.datetime.now(datetime.UTC),
                    duration_ms=s6_dur_ms,
                )
            )
            db.commit()

            # -------------------------------------------------------------
            # Stage 7 & 8: Review Routing and Final Completion
            # -------------------------------------------------------------
            total_dur_ms = max(1, int((time.perf_counter() - start_time_all) * 1000))

            # Store canonical AIAnalysis record
            ai_analysis = AIAnalysis(
                report_id=report.id,
                predicted_category=decision_res["suggested_category"],
                confidence=decision_res["confidence"],
                severity=decision_res["suggested_severity"],
                priority=decision_res["operational_priority"],
                evidence_agreement=fusion_res["modality_agreement"],
                review_required=decision_res["review_required"],
                analysis_metadata={
                    "processor_name": job.processor_name,
                    "execution_mode": job.execution_mode,
                    "disclaimer": "Deterministic Prototype Engine (Not a deep learning model)",
                    "vision_prediction": {
                        "category": vision_res["predicted_category"],
                        "severity": (
                            vision_res["predicted_severity"].value
                            if hasattr(vision_res["predicted_severity"], "value")
                            else vision_res["predicted_severity"]
                        ),
                        "confidence": vision_res["confidence"],
                        "features": vision_res["features"],
                    },
                    "text_prediction": {
                        "category": text_res["predicted_category"],
                        "severity": text_res["predicted_severity"].value,
                        "confidence": text_res["confidence"],
                        "matched_terms": text_res["matched_terms"],
                    },
                    "fusion_metrics": {
                        "modality_agreement": fusion_res["modality_agreement"],
                        "conflict_reasons": fusion_res["conflict_reasons"],
                    },
                    "decision_rationale": decision_res["decision_explanation"],
                    "job_id": str(job.id),
                    "processing_duration_ms": total_dur_ms,
                },
            )
            db.add(ai_analysis)

            # Update Job state according to user requirement
            job.status = AIJobStatus.COMPLETED
            job.completed_at = datetime.datetime.now(datetime.UTC)
            job.review_required = decision_res["review_required"]
            job.review_reason = decision_res["review_reason"]

            if decision_res["review_required"]:
                job.current_stage = AIProcessingStage.HUMAN_REVIEW
                # Log HUMAN_REVIEW event
                db.add(
                    AIJobEvent(
                        job_id=job.id,
                        report_id=report.id,
                        stage=AIProcessingStage.HUMAN_REVIEW,
                        status="STARTED",
                        message=(
                            f"Mandatory human review queued: {decision_res['review_reason']}. "
                            f"Awaiting triage officer inspection."
                        ),
                        metadata_json={
                            "review_reason": decision_res["review_reason"],
                            "confidence": decision_res["confidence"],
                            "decision_explanation": decision_res["decision_explanation"],
                        },
                        started_at=datetime.datetime.now(datetime.UTC),
                        completed_at=None,
                        duration_ms=None,
                    )
                )
                # Advance report status to VERIFICATION_REQUIRED if allowed
                if ReportLifecycleManager.is_valid_transition(
                    report.status, ReportStatus.VERIFICATION_REQUIRED
                ):
                    report.status = ReportStatus.VERIFICATION_REQUIRED
                    report.updated_at = datetime.datetime.now(datetime.UTC)
            else:
                job.current_stage = AIProcessingStage.COMPLETED
                # Log COMPLETED event
                db.add(
                    AIJobEvent(
                        job_id=job.id,
                        report_id=report.id,
                        stage=AIProcessingStage.COMPLETED,
                        status="COMPLETED",
                        message="Automated AI triage completed with high confidence.",
                        metadata_json={
                            "final_category": decision_res["suggested_category"],
                            "confidence": decision_res["confidence"],
                            "total_duration_ms": total_dur_ms,
                        },
                        started_at=datetime.datetime.now(datetime.UTC),
                        completed_at=datetime.datetime.now(datetime.UTC),
                        duration_ms=total_dur_ms,
                    )
                )
                # Advance report status to AI_PROCESSED if allowed
                if ReportLifecycleManager.is_valid_transition(
                    report.status, ReportStatus.AI_PROCESSED
                ):
                    report.status = ReportStatus.AI_PROCESSED
                    report.updated_at = datetime.datetime.now(datetime.UTC)

            db.commit()
            db.refresh(job)
            return job

        except Exception as exc:
            db.rollback()
            logger.exception("AI processing job %s failed: %s", job.id, exc)
            job.status = AIJobStatus.FAILED
            job.failed_at = datetime.datetime.now(datetime.UTC)
            job.error_code = "PROCESSING_FAILURE"
            job.error_message = str(exc)
            db.add(
                AIJobEvent(
                    job_id=job.id,
                    report_id=report.id,
                    stage=job.current_stage,
                    status="FAILED",
                    message=f"Pipeline failed at stage {job.current_stage.value}: {str(exc)}",
                    metadata_json={"exception": str(exc)},
                    started_at=datetime.datetime.now(datetime.UTC),
                    completed_at=datetime.datetime.now(datetime.UTC),
                    duration_ms=None,
                )
            )
            db.commit()
            db.refresh(job)
            raise AIProcessingError(job.current_stage.value, str(exc)) from exc
