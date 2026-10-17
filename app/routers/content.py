from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_user, require_roles
from app.database import get_db
from app.models import Role, User
from app.schemas import ContentCreate, ContentListItem, ContentOut, ContentUpdate, Page
from app.services import content_service

router = APIRouter(prefix="/content", tags=["Content"])
author_roles = require_roles(Role.admin, Role.creator)


@router.get("", response_model=Page[ContentListItem])
def list_content(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100, description="Search in title and summary"),
    premium: bool | None = None,
    db: Session = Depends(get_db),
):
    return content_service.list_published(db, page, size, q, premium)


@router.get("/mine", response_model=Page[ContentListItem])
def my_content(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: User = Depends(author_roles),
    db: Session = Depends(get_db),
):
    items, total = content_service.list_mine(db, user, page, size)
    return Page[ContentListItem].build(items, total, page, size)


@router.get("/{content_id}", response_model=ContentOut)
def get_content(content_id: int, user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    return content_service.get_for_reader(db, content_id, user)


@router.post("", response_model=ContentOut, status_code=status.HTTP_201_CREATED)
def create_content(data: ContentCreate, user: User = Depends(author_roles), db: Session = Depends(get_db)):
    return content_service.create(db, user, data)


@router.patch("/{content_id}", response_model=ContentOut)
def update_content(
    content_id: int, data: ContentUpdate, user: User = Depends(author_roles), db: Session = Depends(get_db)
):
    return content_service.update(db, user, content_id, data)


@router.post("/{content_id}/publish", response_model=ContentOut)
def publish_content(content_id: int, user: User = Depends(author_roles), db: Session = Depends(get_db)):
    return content_service.set_published(db, user, content_id, True)


@router.post("/{content_id}/unpublish", response_model=ContentOut)
def unpublish_content(content_id: int, user: User = Depends(author_roles), db: Session = Depends(get_db)):
    return content_service.set_published(db, user, content_id, False)


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_content(content_id: int, user: User = Depends(author_roles), db: Session = Depends(get_db)):
    content_service.delete(db, user, content_id)
