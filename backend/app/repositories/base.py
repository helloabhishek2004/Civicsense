from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD helpers using modern SQLAlchemy 2.x syntax."""

    def __init__(self, model: type[ModelType]) -> None:
        self.model = model

    def get_by_id(self, db: Session, id_val: Any) -> ModelType | None:
        stmt = select(self.model).where(self.model.id == id_val)  # type: ignore[attr-defined]
        return db.scalars(stmt).first()

    def list_paginated(
        self, db: Session, skip: int = 0, limit: int = 20
    ) -> tuple[list[ModelType], int]:
        count_stmt = select(func.count()).select_from(self.model)
        total = db.scalar(count_stmt) or 0

        stmt = select(self.model).offset(skip).limit(limit)
        items = list(db.scalars(stmt).all())
        return items, total
