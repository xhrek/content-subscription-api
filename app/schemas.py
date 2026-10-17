import math
from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models import ContentStatus, Role, SubscriptionStatus

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def build(cls, items: list, total: int, page: int, size: int) -> "Page[T]":
        return cls(items=items, total=total, page=page, size=size, pages=math.ceil(total / size) if size else 0)


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


# ---------- Users ----------
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, max_length=120)
    password: str | None = Field(default=None, min_length=8, max_length=128)


class RoleUpdate(BaseModel):
    role: Role


class UserOut(ORMModel):
    id: int
    email: EmailStr
    full_name: str | None
    role: Role
    is_active: bool
    created_at: datetime


# ---------- Plans ----------
class PlanCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    description: str | None = None
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    duration_days: int = Field(default=30, ge=1, le=3650)


class PlanOut(ORMModel):
    id: int
    name: str
    description: str | None
    price: Decimal
    duration_days: int
    is_active: bool


# ---------- Content ----------
class ContentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    body: str = Field(min_length=1)
    is_premium: bool = False


class ContentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=200)
    summary: str | None = Field(default=None, max_length=500)
    body: str | None = Field(default=None, min_length=1)
    is_premium: bool | None = None


class ContentListItem(ORMModel):
    id: int
    title: str
    slug: str
    summary: str | None
    is_premium: bool
    status: ContentStatus
    author_id: int
    published_at: datetime | None
    created_at: datetime


class ContentOut(ContentListItem):
    body: str
    updated_at: datetime


# ---------- Subscriptions ----------
class SubscriptionCreate(BaseModel):
    plan_id: int


class SubscriptionOut(ORMModel):
    id: int
    user_id: int
    plan: PlanOut
    status: SubscriptionStatus
    start_date: datetime
    end_date: datetime
    cancelled_at: datetime | None
