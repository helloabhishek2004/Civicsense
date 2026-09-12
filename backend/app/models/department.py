import datetime
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Integer, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.assignment import ReportAssignment
    from app.models.report import Report


class Department(Base):
    """Canonical registry of municipal operational departments."""

    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    head_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sla_hours_default: Mapped[int] = mapped_column(Integer, default=72, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    # Relationships
    reports: Mapped[list["Report"]] = relationship("Report", back_populates="department_rel")
    assignments: Mapped[list["ReportAssignment"]] = relationship(
        "ReportAssignment", back_populates="department"
    )


DEFAULT_DEPARTMENTS = [
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "name": "Roads & Bridges",
        "code": "ROADS",
        "description": (
            "Responsible for municipal road networks, potholes, asphalt paving, "
            "bridges, flyovers, footpaths, and storm drains."
        ),
        "head_name": "Chief Engineer (Roads)",
        "contact_email": "roads@civicsense.local",
        "contact_phone": "+91 80 2222 1001",
        "sla_hours_default": 48,
        "is_active": True,
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "name": "Solid Waste Management",
        "code": "WASTE",
        "description": (
            "Garbage clearance, municipal dumpster maintenance, public sanitization, "
            "street sweeping, and illegal dumping remediation."
        ),
        "head_name": "Superintendent of Sanitation",
        "contact_email": "waste@civicsense.local",
        "contact_phone": "+91 80 2222 1002",
        "sla_hours_default": 24,
        "is_active": True,
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "name": "Water Supply & Sewerage",
        "code": "WATER",
        "description": (
            "Potable water supply pipelines, manhole overflows, sewage blockages, "
            "water main leaks, and pump maintenance."
        ),
        "head_name": "Executive Engineer (Water)",
        "contact_email": "water@civicsense.local",
        "contact_phone": "+91 80 2222 1003",
        "sla_hours_default": 36,
        "is_active": True,
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "name": "Street Lighting & Electrical",
        "code": "ELECTRICAL",
        "description": (
            "Street light fixtures, high-mast lamps, exposed electrical cables, "
            "feeder pillars, and junction box safety."
        ),
        "head_name": "Divisional Engineer (Electrical)",
        "contact_email": "electrical@civicsense.local",
        "contact_phone": "+91 80 2222 1004",
        "sla_hours_default": 24,
        "is_active": True,
    },
    {
        "id": uuid.UUID("55555555-5555-5555-5555-555555555555"),
        "name": "Town Planning & Enforcement",
        "code": "PLANNING",
        "description": (
            "Encroachments on public right-of-way, unauthorized construction, "
            "footpath obstructions, and zoning violations."
        ),
        "head_name": "Joint Commissioner (Town Planning)",
        "contact_email": "planning@civicsense.local",
        "contact_phone": "+91 80 2222 1005",
        "sla_hours_default": 72,
        "is_active": True,
    },
    {
        "id": uuid.UUID("66666666-6666-6666-6666-666666666666"),
        "name": "General Public Works",
        "code": "PUBLIC_WORKS",
        "description": (
            "Public parks, signage, civic monuments, municipal building maintenance, "
            "and unclassified civil infrastructure."
        ),
        "head_name": "Executive Engineer (Public Works)",
        "contact_email": "publicworks@civicsense.local",
        "contact_phone": "+91 80 2222 1006",
        "sla_hours_default": 48,
        "is_active": True,
    },
]
