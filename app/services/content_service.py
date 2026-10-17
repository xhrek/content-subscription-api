import re
import secrets
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.cache import cache
from app.models import Content, ContentStatus, Role, User
from app.schemas import ContentCreate, ContentListItem, ContentUpdate, Page
from app.services.subscription_service import has_active_subscription

CACHE_PREFIX = "content:"


def _slugify(title: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:200] or "post"
    return f"{base}-{secrets.token_hex(3)}"


def _can_manage(user: User, content: Content) -> bool:
    return user.role == Role.admin or content.author_id == user.id


def _get_or_404(db: Session, content_id: int) -> Content:
    content = db.get(Content, content_id)
    if not content:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content not found")
    return content


def list_published(db: Session, page: int, size: int, q: str | None, premium: bool | None) -> dict:
    key = f"{CACHE_PREFIX}list:{page}:{size}:{q or ''}:{premium}"
    cached = cache.get(key)
    if cached is not None:
        return cached

    stmt = select(Content).where(Content.status == ContentStatus.published)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Content.title.ilike(like), Content.summary.ilike(like)))
    if premium is not None:
        stmt = stmt.where(Content.is_premium.is_(premium))

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Content.published_at.desc(), Content.id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    result = Page[ContentListItem].build(
        [ContentListItem.model_validate(r) for r in rows], total, page, size
    ).model_dump(mode="json")
    cache.set(key, result)
    return result


def list_mine(db: Session, user: User, page: int, size: int) -> tuple[list[Content], int]:
    stmt = select(Content).where(Content.author_id == user.id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Content.created_at.desc()).offset((page - 1) * size).limit(size)).all()
    return list(rows), total


def get_for_reader(db: Session, content_id: int, user: User | None) -> Content:
    content = _get_or_404(db, content_id)
    is_owner = user is not None and _can_manage(user, content)

    if content.status != ContentStatus.published and not is_owner:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Content not found")

    if content.is_premium and not is_owner:
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Login required for premium content")
        if not has_active_subscription(db, user.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "An active subscription is required")
    return content


def create(db: Session, author: User, data: ContentCreate) -> Content:
    content = Content(**data.model_dump(), slug=_slugify(data.title), author_id=author.id)
    db.add(content)
    db.commit()
    db.refresh(content)
    return content


def update(db: Session, user: User, content_id: int, data: ContentUpdate) -> Content:
    content = _get_or_404(db, content_id)
    if not _can_manage(user, content):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed to modify this content")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(content, field, value)
    db.commit()
    db.refresh(content)
    cache.invalidate(CACHE_PREFIX)
    return content


def set_published(db: Session, user: User, content_id: int, publish: bool) -> Content:
    content = _get_or_404(db, content_id)
    if not _can_manage(user, content):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed to modify this content")
    if publish:
        content.status = ContentStatus.published
        content.published_at = content.published_at or datetime.now(timezone.utc)
    else:
        content.status = ContentStatus.draft
    db.commit()
    db.refresh(content)
    cache.invalidate(CACHE_PREFIX)
    return content


def delete(db: Session, user: User, content_id: int) -> None:
    content = _get_or_404(db, content_id)
    if not _can_manage(user, content):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not allowed to delete this content")
    db.delete(content)
    db.commit()
    cache.invalidate(CACHE_PREFIX)
