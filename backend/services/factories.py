from __future__ import annotations

from sqlalchemy.orm import Session

from .profile import ProfileService
from .sqlalchemy_repositories import (
    SqlAlchemyUserRepository,
    SqlAlchemyProfileRepository,
)


def get_profile_service(db: Session) -> ProfileService:
    return ProfileService(SqlAlchemyUserRepository(db), SqlAlchemyProfileRepository(db))


def get_profile_repository(db: Session) -> SqlAlchemyProfileRepository:
    return SqlAlchemyProfileRepository(db)
