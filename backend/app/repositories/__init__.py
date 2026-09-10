from app.repositories.base import BaseRepository
from app.repositories.issue_repo import IssueRepository, issue_repository
from app.repositories.report_repo import ReportRepository, report_repository

__all__ = [
    "BaseRepository",
    "ReportRepository",
    "report_repository",
    "IssueRepository",
    "issue_repository",
]
