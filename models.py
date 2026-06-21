from datetime import datetime
from sqlalchemy import (
    Boolean, create_engine, Column, Integer, String, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import declarative_base, relationship, Session
from config import settings

Base = declarative_base()


class Profile(Base):
    __tablename__ = "profile"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, default="小布")
    breed = Column(String(100), default="")
    age = Column(Integer, default=0)
    appearance = Column(Text, default="")
    personality_tags = Column(JSON, default=list)
    interests = Column(JSON, default=list)
    habits = Column(Text, default="")
    image_api_key = Column(String(200), default="")
    content_preference = Column(String(20), default="caption")
    reference_photos = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True)


class Region(Base):
    __tablename__ = "regions"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")


class Location(Base):
    __tablename__ = "locations"
    id = Column(Integer, primary_key=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    atmosphere = Column(Text, default="")
    adjacent_locations = Column(JSON, default=list)
    region = relationship("Region")
    activities = relationship("Activity", back_populates="location")


class Activity(Base):
    __tablename__ = "activities"
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    name = Column(String(100), nullable=False)
    prompt_template = Column(Text, default="")
    captions = Column(JSON, default=list)
    stories = Column(JSON, default=list)
    location = relationship("Location", back_populates="activities")


class JourneyState(Base):
    __tablename__ = "journey_state"
    id = Column(Integer, primary_key=True)
    current_location_id = Column(Integer, ForeignKey("locations.id"), nullable=True)
    mood = Column(String(50), default="开心")
    day_number = Column(Integer, default=1)
    weather_today = Column(String(50), default="晴")
    last_activity_id = Column(Integer, ForeignKey("activities.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class JourneyLog(Base):
    __tablename__ = "journey_log"
    id = Column(Integer, primary_key=True)
    location_id = Column(Integer, ForeignKey("locations.id"), nullable=False)
    activity_id = Column(Integer, ForeignKey("activities.id"), nullable=False)
    story_text = Column(Text, default="")
    image_path = Column(String(500), default="")
    weather = Column(String(50), default="晴")
    mood = Column(String(50), default="开心")
    generated_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class ScheduledTask(Base):
    __tablename__ = "scheduled_tasks"
    id = Column(Integer, primary_key=True)
    scheduled_at = Column(DateTime, nullable=False)
    executed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="pending")
    retry_count = Column(Integer, default=0)
    journey_log_id = Column(Integer, ForeignKey("journey_log.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    pet_name = Column(String(100), nullable=False, default="")
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    remember_me = Column(Boolean, default=False)
    user_agent = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class CsrfToken(Base):
    __tablename__ = "csrf_tokens"
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("auth_sessions.id"), nullable=False)
    token_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    event = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45), default="")
    user_agent = Column(Text, default="")
    details = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)


def get_engine():
    if settings.DATABASE_URL.startswith("sqlite"):
        return create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
    return create_engine(settings.DATABASE_URL)


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)


def get_session():
    engine = get_engine()
    return Session(engine)
