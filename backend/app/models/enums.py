from enum import Enum


class ReportStatus(str, Enum):
    """Explicit report lifecycle states as defined in canonical architecture."""

    SUBMITTED = "SUBMITTED"
    AI_PROCESSING = "AI_PROCESSING"
    AI_PROCESSED = "AI_PROCESSED"
    VERIFICATION_REQUIRED = "VERIFICATION_REQUIRED"
    VERIFIED = "VERIFIED"
    PRIORITIZED = "PRIORITIZED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    RESOLUTION_VERIFIED = "RESOLUTION_VERIFIED"
    CLOSED = "CLOSED"


class EvidenceType(str, Enum):
    """Types of evidence supporting a citizen report."""

    IMAGE = "IMAGE"
    TEXT = "TEXT"
    METADATA = "METADATA"


class SeverityLevel(str, Enum):
    """Inherent physical defect severity."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class PriorityLevel(str, Enum):
    """Operational administrative priority ranking."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class VerificationDecision(str, Enum):
    """Human reviewer verdict on an AI prediction."""

    CONFIRMED = "CONFIRMED"
    CORRECTED = "CORRECTED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"


class AIJobStatus(str, Enum):
    """Status of an AI processing job."""

    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class AIProcessingStage(str, Enum):
    """Eight-stage AI processing and review pipeline."""

    INTAKE_VALIDATION = "INTAKE_VALIDATION"
    PREPROCESSING = "PREPROCESSING"
    VISION_ANALYSIS = "VISION_ANALYSIS"
    TEXT_ANALYSIS = "TEXT_ANALYSIS"
    FUSION = "FUSION"
    DECISION = "DECISION"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    COMPLETED = "COMPLETED"


class AssignmentStatus(str, Enum):
    """Lifecycle state of an individual department assignment attempt."""

    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class MatchStatus(str, Enum):
    """Lifecycle state of a report-to-issue similarity match."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUPERSEDED = "SUPERSEDED"


class MatchAction(str, Enum):
    """Outcome of similarity scoring against nearby issues."""

    AUTO_LINK = "AUTO_LINK"
    CANDIDATE = "CANDIDATE"
    NEW_ISSUE = "NEW_ISSUE"


class DepartmentRejectionReason(str, Enum):
    """Standardized reasons when a department declines custody of a job."""

    OUT_OF_JURISDICTION = "OUT_OF_JURISDICTION"
    INSUFFICIENT_ACCESS = "INSUFFICIENT_ACCESS"
    DUPLICATE_WORK_ORDER = "DUPLICATE_WORK_ORDER"
    REQUIRES_MAJOR_BUDGET = "REQUIRES_MAJOR_BUDGET"
    INSUFFICIENT_INFORMATION = "INSUFFICIENT_INFORMATION"
    OTHER = "OTHER"
