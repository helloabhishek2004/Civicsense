import uuid

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.issue import Issue
from app.repositories.base import BaseRepository


class IssueRepository(BaseRepository[Issue]):
    """Data access repository for civic issues."""

    def __init__(self) -> None:
        super().__init__(Issue)

    def create(
        self,
        db: Session,
        title: str,
        category: str,
        latitude: float,
        longitude: float,
    ) -> Issue:
        """Create a new civic issue grouping."""
        issue = Issue(
            id=uuid.uuid4(),
            title=title,
            category=category,
            status="OPEN",
            primary_latitude=latitude,
            primary_longitude=longitude,
            report_count=1,
        )
        db.add(issue)
        db.commit()
        db.refresh(issue)
        return issue

    def get_by_id_with_reports(self, db: Session, issue_id: uuid.UUID) -> Issue | None:
        """Fetch issue with its associated reports."""
        stmt = (
            select(Issue)
            .options(joinedload(Issue.reports), joinedload(Issue.resolutions))
            .where(Issue.id == issue_id)
        )
        return db.scalars(stmt).unique().first()

    def list_issues(self, db: Session, skip: int = 0, limit: int = 20) -> tuple[list[Issue], int]:
        """List issues sorted descending by creation date."""
        count_stmt = select(func.count()).select_from(Issue)
        total = db.scalar(count_stmt) or 0

        stmt = select(Issue).order_by(desc(Issue.created_at)).offset(skip).limit(limit)
        items = list(db.scalars(stmt).all())
        return items, total


issue_repository = IssueRepository()
