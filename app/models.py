import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Role(str, enum.Enum):
    admin = "admin"
    creator = "creator"
    subscriber = "subscriber"


class ContentStatus(str, enum.Enum):
    draft = "draft"
    published = "published"


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    cancelled = "cancelled"
    expired = "expired"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str | None] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(Enum(Role, name="user_role"), default=Role.subscriber, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    contents: Mapped[list["Content"]] = relationship(back_populates="author", cascade="all, delete-orphan")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[float] = mapped_column(Numeric(10, 2))
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Content(Base):
    __tablename__ = "contents"
    __table_args__ = (
        Index("ix_contents_status_published_at", "status", "published_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    summary: Mapped[str | None] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    status: Mapped[ContentStatus] = mapped_column(
        Enum(ContentStatus, name="content_status"), default=ContentStatus.draft
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    author: Mapped[User] = relationship(back_populates="contents")


class Subscription(Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_user_status_end", "user_id", "status", "end_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="RESTRICT"), index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, name="subscription_status"), default=SubscriptionStatus.active
    )
    start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    end_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User] = relationship(back_populates="subscriptions")
    plan: Mapped[Plan] = relationship(lazy="joined")
