import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app.auth.jwt import hash_password
from app.cache import cache
from app.config import settings
from app.database import Base, SessionLocal, engine
from app.models import Role, User
from app.routers import auth, content, subscriptions, users

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("api")


def _bootstrap_admin() -> None:
    if not (settings.FIRST_ADMIN_EMAIL and settings.FIRST_ADMIN_PASSWORD):
        return
    with SessionLocal() as db:
        email = settings.FIRST_ADMIN_EMAIL.lower()
        if not db.scalar(select(User.id).where(User.email == email)):
            db.add(User(email=email, full_name="Administrator", role=Role.admin,
                        hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD)))
            db.commit()
            logger.info("Bootstrap admin created: %s", email)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    _bootstrap_admin()
    yield
    engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Secure REST API for users, content publishing and subscriptions.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_and_timing(request: Request, call_next):
    start = time.perf_counter()
    if request.url.path.startswith(settings.API_PREFIX):
        client = request.client.host if request.client else "anonymous"
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        limit = settings.RATE_LIMIT_REQUESTS
        bucket = int(time.time() // window)
        count, reset = cache.hit(f"ratelimit:{client}:{bucket}", window)
        remaining = max(limit - count, 0)
        if count > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": str(reset), "X-RateLimit-Limit": str(limit), "X-RateLimit-Remaining": "0"},
            )
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
    else:
        response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.2f}"
    return response


for r in (auth.router, users.router, content.router, subscriptions.router):
    app.include_router(r, prefix=settings.API_PREFIX)


@app.get("/health", tags=["Health"])
def health():
    db_ok = True
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "redis": cache.client is not None}
