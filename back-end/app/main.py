from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import admin, applications, auth, health, keys, sdu_auth, templates, venues
from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=settings.api_v1_prefix)
    app.include_router(auth.router, prefix=settings.api_v1_prefix)
    app.include_router(sdu_auth.router, prefix=settings.api_v1_prefix)
    app.include_router(venues.router, prefix=settings.api_v1_prefix)
    app.include_router(keys.router, prefix=settings.api_v1_prefix)
    app.include_router(applications.router, prefix=settings.api_v1_prefix)
    app.include_router(templates.router, prefix=settings.api_v1_prefix)
    app.include_router(admin.router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
