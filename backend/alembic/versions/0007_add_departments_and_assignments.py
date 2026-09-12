"""add departments and report assignments

Revision ID: 0007_add_departments_and_assignments
Revises: 0006_add_report_category
Create Date: 2026-09-12 15:55:00.000000

"""
import datetime
import uuid
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0007_add_departments_and_assignments'
down_revision: str | None = '0006_add_report_category'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_DEPARTMENTS = [
    {
        "id": uuid.UUID("11111111-1111-1111-1111-111111111111"),
        "name": "Roads & Bridges",
        "code": "ROADS",
        "description": "Potholes, asphalt fractures, road collapses, and bridge joint repairs.",
        "head_name": "Shri K. Ramanathan (Chief Engineer)",
        "contact_email": "roads@civicsense.gov.in",
        "contact_phone": "0471-2334411",
        "sla_hours_default": 72,
        "is_active": True,
    },
    {
        "id": uuid.UUID("22222222-2222-2222-2222-222222222222"),
        "name": "Solid Waste Management",
        "code": "WASTE",
        "description": "Commercial dumping, garbage overflow, and debris clearance.",
        "head_name": "Dr. Meenakshi Sundaram (Director)",
        "contact_email": "waste@civicsense.gov.in",
        "contact_phone": "0471-2334422",
        "sla_hours_default": 24,
        "is_active": True,
    },
    {
        "id": uuid.UUID("33333333-3333-3333-3333-333333333333"),
        "name": "Water Supply & Sewerage",
        "code": "WATER",
        "description": "Pipeline bursts, valve leaks, drain desilting, and sewerage overflows.",
        "head_name": "Er. Anand V. (Executive Engineer)",
        "contact_email": "water@civicsense.gov.in",
        "contact_phone": "0471-2334433",
        "sla_hours_default": 48,
        "is_active": True,
    },
    {
        "id": uuid.UUID("44444444-4444-4444-4444-444444444444"),
        "name": "Street Lighting & Electrical",
        "code": "ELECTRICAL",
        "description": "Faulty luminaires, cable faults, pole damage, and switchgear failures.",
        "head_name": "P. Venkatraman (Assistant Engineer)",
        "contact_email": "electrical@civicsense.gov.in",
        "contact_phone": "0471-2334444",
        "sla_hours_default": 48,
        "is_active": True,
    },
    {
        "id": uuid.UUID("55555555-5555-5555-5555-555555555555"),
        "name": "Town Planning & Enforcement",
        "code": "PLANNING",
        "description": (
            "Footpath encroachments, unauthorized hoardings, and public right-of-way issues."
        ),
        "head_name": "Smt. Kavitha Pillai (Zonal Commissioner)",
        "contact_email": "planning@civicsense.gov.in",
        "contact_phone": "0471-2334455",
        "sla_hours_default": 120,
        "is_active": True,
    },
    {
        "id": uuid.UUID("66666666-6666-6666-6666-666666666666"),
        "name": "General Public Works",
        "code": "PUBLIC_WORKS",
        "description": (
            "Multi-jurisdiction civic maintenance, public park repairs, and boundary works."
        ),
        "head_name": "Devraj Menon (Superintending Engineer)",
        "contact_email": "publicworks@civicsense.gov.in",
        "contact_phone": "0471-2334466",
        "sla_hours_default": 72,
        "is_active": True,
    },
]


def upgrade() -> None:
    # 1. Create departments table
    op.create_table(
        'departments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=64), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('head_name', sa.String(length=128), nullable=True),
        sa.Column('contact_email', sa.String(length=255), nullable=True),
        sa.Column('contact_phone', sa.String(length=32), nullable=True),
        sa.Column('sla_hours_default', sa.Integer(), nullable=False, server_default='72'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_departments_name'), 'departments', ['name'], unique=True)
    op.create_index(op.f('ix_departments_code'), 'departments', ['code'], unique=True)

    # 2. Seed the 6 default municipal departments idempotently
    bind = op.get_bind()
    departments_table = sa.table(
        'departments',
        sa.column('id', sa.Uuid),
        sa.column('name', sa.String),
        sa.column('code', sa.String),
        sa.column('description', sa.Text),
        sa.column('head_name', sa.String),
        sa.column('contact_email', sa.String),
        sa.column('contact_phone', sa.String),
        sa.column('sla_hours_default', sa.Integer),
        sa.column('is_active', sa.Boolean),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )
    now = datetime.datetime.now(datetime.UTC)
    for dept in DEFAULT_DEPARTMENTS:
        bind.execute(
            departments_table.insert().values(
                id=dept['id'],
                name=dept['name'],
                code=dept['code'],
                description=dept['description'],
                head_name=dept['head_name'],
                contact_email=dept['contact_email'],
                contact_phone=dept['contact_phone'],
                sla_hours_default=dept['sla_hours_default'],
                is_active=dept['is_active'],
                created_at=now,
                updated_at=now,
            )
        )

    # 3. Add department_id and reassignment_required to reports
    with op.batch_alter_table('reports') as batch_op:
        batch_op.add_column(sa.Column('department_id', sa.Uuid(), nullable=True))
        batch_op.add_column(
            sa.Column('reassignment_required', sa.Boolean(), nullable=False, server_default='false')
        )
        batch_op.create_foreign_key(
            'fk_reports_department_id',
            'departments',
            ['department_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_index('ix_reports_department_id', ['department_id'], unique=False)

    # 4. Backfill department_id for existing reports matching department names
    reports_table = sa.table(
        'reports',
        sa.column('department_id', sa.Uuid()),
        sa.column('department', sa.String()),
    )
    for dept in DEFAULT_DEPARTMENTS:
        bind.execute(
            reports_table.update()
            .where(reports_table.c.department == dept['name'])
            .where(reports_table.c.department_id.is_(None))
            .values(department_id=dept['id'])
        )

    # 5. Create report_assignments table
    op.create_table(
        'report_assignments',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('report_id', sa.Uuid(), nullable=False),
        sa.Column('department_id', sa.Uuid(), nullable=True),
        sa.Column('department_name', sa.String(length=64), nullable=False),
        sa.Column('assigned_by', sa.String(length=128), nullable=False),
        sa.Column('assigned_to_officer', sa.String(length=128), nullable=True),
        sa.Column(
            'status',
            sa.Enum('ASSIGNED', 'IN_PROGRESS', 'COMPLETED', 'REJECTED', name='assignmentstatus'),
            nullable=False,
            server_default='ASSIGNED'
        ),
        sa.Column(
            'rejection_reason',
            sa.Enum(
                'OUT_OF_JURISDICTION',
                'INSUFFICIENT_ACCESS',
                'DUPLICATE_WORK_ORDER',
                'REQUIRES_MAJOR_BUDGET',
                'INSUFFICIENT_INFORMATION',
                'OTHER',
                name='departmentrejectionreason'
            ),
            nullable=True
        ),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['report_id'], ['reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_report_assignments_report_id'),
        'report_assignments',
        ['report_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_report_assignments_department_id'),
        'report_assignments',
        ['department_id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_report_assignments_status'),
        'report_assignments',
        ['status'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_report_assignments_status'), table_name='report_assignments')
    op.drop_index(op.f('ix_report_assignments_department_id'), table_name='report_assignments')
    op.drop_index(op.f('ix_report_assignments_report_id'), table_name='report_assignments')
    op.drop_table('report_assignments')

    with op.batch_alter_table('reports') as batch_op:
        batch_op.drop_index('ix_reports_department_id')
        batch_op.drop_constraint('fk_reports_department_id', type_='foreignkey')
        batch_op.drop_column('reassignment_required')
        batch_op.drop_column('department_id')

    op.drop_index(op.f('ix_departments_code'), table_name='departments')
    op.drop_index(op.f('ix_departments_name'), table_name='departments')
    op.drop_table('departments')
