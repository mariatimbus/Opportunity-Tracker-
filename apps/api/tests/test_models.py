"""Model tests: tables, relationships, and constraints on in-memory sqlite."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from opportunity_api.core.database import Base
from opportunity_api.models import (
    Application,
    ApplicationStatus,
    Opportunity,
    OpportunityType,
    Profile,
    Skill,
    User,
)


@pytest.fixture()
def session():
    # StaticPool keeps a single in-memory database across connections.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as s:
        yield s


def _make_user(email: str = "ada@example.com") -> User:
    return User(email=email, password_hash="x", full_name="Ada Lovelace")


def _make_opportunity(url: str = "https://example.com/job/1", source_id: str = "1") -> Opportunity:
    return Opportunity(
        title="Backend Intern",
        organization="Example Corp",
        opportunity_type=OpportunityType.internship,
        url=url,
        source="example",
        source_id=source_id,
    )


def test_user_profile_one_to_one(session: Session):
    user = _make_user()
    user.profile = Profile(headline="Student", bio="CS junior", location="Berlin")
    session.add(user)
    session.commit()

    fetched = session.scalar(select(User).where(User.email == "ada@example.com"))
    assert fetched is not None
    assert fetched.profile.headline == "Student"
    assert fetched.profile.user_id == fetched.id
    assert fetched.profile.user is fetched


def test_user_skills_many_to_many(session: Session):
    python = Skill(name="python")
    sql = Skill(name="sql")
    user = _make_user()
    user.skills.extend([python, sql])
    session.add_all([user, python, sql])
    session.commit()

    fetched = session.scalar(select(Skill).where(Skill.name == "python"))
    assert fetched is not None
    assert [u.email for u in fetched.users] == ["ada@example.com"]
    assert len(session.scalar(select(User).where(User.email == "ada@example.com")).skills) == 2


def test_opportunity_application_relationships(session: Session):
    user = _make_user()
    opp = _make_opportunity()
    user.applications.append(
        Application(opportunity=opp, status=ApplicationStatus.applied, notes="via referral")
    )
    session.add_all([user, opp])
    session.commit()

    fetched_user = session.scalar(select(User).where(User.email == "ada@example.com"))
    assert len(fetched_user.applications) == 1
    app = fetched_user.applications[0]
    assert app.status == ApplicationStatus.applied
    assert app.opportunity.title == "Backend Intern"
    assert app.opportunity.applications[0] is app


def test_application_unique_per_user_and_opportunity(session: Session):
    user = _make_user()
    opp = _make_opportunity()
    session.add_all([user, opp, Application(user=user, opportunity=opp)])
    session.commit()
    session.add(Application(user=user, opportunity=opp))
    with pytest.raises(IntegrityError):  # duplicate (user_id, opportunity_id)
        session.commit()


def test_opportunity_source_source_id_unique_together(session: Session):
    session.add(_make_opportunity())
    session.commit()
    session.add(_make_opportunity(url="https://example.com/job/2"))
    with pytest.raises(IntegrityError):  # duplicate (source, source_id)
        session.commit()


def test_enums_round_trip(session: Session):
    user = _make_user()
    opp = _make_opportunity()
    app = Application(user=user, opportunity=opp, status=ApplicationStatus.interview)
    session.add_all([user, opp, app])
    session.commit()

    fetched = session.scalar(select(Application))
    assert fetched.status == ApplicationStatus.interview
    assert fetched.opportunity.opportunity_type == OpportunityType.internship


def test_alembic_migration_files_exist():
    versions = (
        Path(__file__).resolve().parents[3] / "database" / "migrations" / "versions"
    )
    migrations = [p for p in versions.glob("*.py") if p.name != ".gitkeep"]
    assert len(migrations) >= 1, "expected at least one alembic migration file"
