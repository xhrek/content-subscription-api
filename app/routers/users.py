from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.auth.jwt import hash_password
from app.database import get_db
from app.models import Role, User
from app.schemas import Page, RoleUpdate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])
admin_only = require_roles(Role.admin)


@router.patch("/me", response_model=UserOut)
def update_me(data: UserUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.password:
        user.hashed_password = hash_password(data.password)
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=Page[UserOut], dependencies=[Depends(admin_only)])
def list_users(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: Role | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(User)
    if role:
        stmt = stmt.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(User.id).offset((page - 1) * size).limit(size)).all()
    return Page[UserOut].build(list(items), total, page, size)


@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(admin_only)])
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return user


@router.patch("/{user_id}/role", response_model=UserOut)
def change_role(
    user_id: int, data: RoleUpdate,
    admin: User = Depends(admin_only), db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own role")
    user.role = data.role
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(user_id: int, admin: User = Depends(admin_only), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    if user.id == admin.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot deactivate yourself")
    user.is_active = False
    db.commit()
