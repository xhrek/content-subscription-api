from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.cache import cache
from app.models import Plan, Subscription, SubscriptionStatus, User
from app.schemas import PlanCreate, PlanOut

PLANS_CACHE_KEY = "plans:active"


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ---------- Plans ----------
def list_active_plans(db: Session) -> list[dict]:
    cached = cache.get(PLANS_CACHE_KEY)
    if cached is not None:
        return cached
    plans = db.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price)).all()
    data = [PlanOut.model_validate(p).model_dump(mode="json") for p in plans]
    cache.set(PLANS_CACHE_KEY, data)
    return data


def create_plan(db: Session, data: PlanCreate) -> Plan:
    if db.scalar(select(Plan.id).where(Plan.name == data.name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Plan name already exists")
    plan = Plan(**data.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    cache.invalidate("plans:")
    return plan


# ---------- Subscriptions ----------
def expire_stale(db: Session, user_id: int | None = None) -> None:
    stmt = (
        update(Subscription)
        .where(Subscription.status == SubscriptionStatus.active, Subscription.end_date <= _now())
        .values(status=SubscriptionStatus.expired)
    )
    if user_id is not None:
        stmt = stmt.where(Subscription.user_id == user_id)
    db.execute(stmt)
    db.commit()


def get_active_subscription(db: Session, user_id: int) -> Subscription | None:
    return db.scalar(
        select(Subscription)
        .where(
            Subscription.user_id == user_id,
            Subscription.status == SubscriptionStatus.active,
            Subscription.end_date > _now(),
        )
        .order_by(Subscription.end_date.desc())
        .limit(1)
    )


def has_active_subscription(db: Session, user_id: int) -> bool:
    key = f"sub:active:{user_id}"
    cached = cache.get(key)
    if cached is not None:
        return bool(cached)
    active = get_active_subscription(db, user_id) is not None
    cache.set(key, active, ttl=30)
    return active


def subscribe(db: Session, user: User, plan_id: int) -> Subscription:
    plan = db.get(Plan, plan_id)
    if not plan or not plan.is_active:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    expire_stale(db, user.id)
    if get_active_subscription(db, user.id):
        raise HTTPException(status.HTTP_409_CONFLICT, "You already have an active subscription")
    now = _now()
    sub = Subscription(
        user_id=user.id, plan_id=plan.id, status=SubscriptionStatus.active,
        start_date=now, end_date=now + timedelta(days=plan.duration_days),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    cache.invalidate(f"sub:active:{user.id}")
    return sub


def list_user_subscriptions(db: Session, user_id: int) -> list[Subscription]:
    expire_stale(db, user_id)
    return list(
        db.scalars(
            select(Subscription).where(Subscription.user_id == user_id).order_by(Subscription.start_date.desc())
        ).all()
    )


def list_all_subscriptions(
    db: Session, page: int, size: int, status_filter: SubscriptionStatus | None
) -> tuple[list[Subscription], int]:
    base = select(Subscription)
    if status_filter:
        base = base.where(Subscription.status == status_filter)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = db.scalars(
        base.order_by(Subscription.id.desc()).offset((page - 1) * size).limit(size)
    ).unique().all()
    return list(items), total


def cancel_subscription(db: Session, user: User, subscription_id: int) -> Subscription:
    sub = db.get(Subscription, subscription_id)
    if not sub or (sub.user_id != user.id and user.role.value != "admin"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Subscription not found")
    if sub.status != SubscriptionStatus.active:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Subscription is not active")
    sub.status = SubscriptionStatus.cancelled
    sub.cancelled_at = _now()
    db.commit()
    db.refresh(sub)
    cache.invalidate(f"sub:active:{sub.user_id}")
    return sub
