from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.errors import install_error_handlers
from app.logging_conf import configure_logging
from app.routers import auth, projects, runs

configure_logging()
log = logging.getLogger("devteam.http")
settings = get_settings()

app = FastAPI(title="DevTeam AI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
install_error_handlers(app)


@app.middleware("http")
async def access_log(request: Request, call_next):
    rid, start = uuid.uuid4().hex[:12], time.monotonic()
    response = await call_next(request)
    log.info(
        "request",
        extra={
            "request_id": rid,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "ms": round((time.monotonic() - start) * 1000),
        },
    )
    response.headers["X-Request-ID"] = rid
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


for r in (auth.router, projects.router, runs.router):
    app.include_router(r, prefix="/api")
