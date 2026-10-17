from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_roles
from app.database import get_db
from app.models import Role, SubscriptionStatus, User
from app.schemas import Page, PlanCreate, PlanOut, SubscriptionCreate, SubscriptionOut
from app.services import subscription_service as svc

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
admin_only = require_roles(Role.admin)


@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    return svc.list_active_plans(db)


@router.post("/plans", response_model=PlanOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(admin_only)])
def create_plan(data: PlanCreate, db: Session = Depends(get_db)):
    return svc.create_plan(db, data)


@router.post("", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
def subscribe(data: SubscriptionCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.subscribe(db, user, data.plan_id)


@router.get("/me", response_model=list[SubscriptionOut])
def my_subscriptions(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.list_user_subscriptions(db, user.id)


@router.post("/{subscription_id}/cancel", response_model=SubscriptionOut)
def cancel(subscription_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return svc.cancel_subscription(db, user, subscription_id)


@router.get("", response_model=Page[SubscriptionOut], dependencies=[Depends(admin_only)])
def list_all(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status_filter: SubscriptionStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    items, total = svc.list_all_subscriptions(db, page, size, status_filter)
    return Page[SubscriptionOut].build(items, total, page, size)
