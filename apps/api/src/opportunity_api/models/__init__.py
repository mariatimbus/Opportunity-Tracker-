"""SQLAlchemy models. Importing this package registers all tables on Base.metadata."""

from .application import Application, ApplicationStatus
from .opportunity import Opportunity, OpportunityDegreeLevel, OpportunityType
from .profile import DegreeLevel, Profile
from .skill import Skill, opportunity_skills, user_skills
from .user import User

__all__ = [
    "Application",
    "ApplicationStatus",
    "DegreeLevel",
    "Opportunity",
    "OpportunityDegreeLevel",
    "OpportunityType",
    "Profile",
    "Skill",
    "User",
    "opportunity_skills",
    "user_skills",
]
