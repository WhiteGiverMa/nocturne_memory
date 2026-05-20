from __future__ import annotations

import importlib
from collections.abc import Iterable, Sequence
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Callable, cast

from fastapi import APIRouter, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.applications import Starlette
from starlette.responses import FileResponse, PlainTextResponse
from starlette.routing import Mount, Route
from starlette.types import ASGIApp, Receive, Scope, Send

_api_module = importlib.import_module("api")
_auth_module = importlib.import_module("auth")
_config_module = importlib.import_module("config")
_health_module = importlib.import_module("health")
_namespace_module = importlib.import_module("namespace_middleware")

browse_router = cast(APIRouter, getattr(_api_module, "browse_router"))
maintenance_router = cast(APIRouter, getattr(_api_module, "maintenance_router"))
review_router = cast(APIRouter, getattr(_api_module, "review_router"))
settings_router = cast(APIRouter, getattr(_api_module, "settings_router"))

BearerTokenAuthMiddleware = getattr(_auth_module, "BearerTokenAuthMiddleware")
get_cors_config = getattr(_auth_module, "get_cors_config")
ConfigWriteError = cast(type[Exception], getattr(_config_module, "ConfigWriteError"))
health_check = getattr(_health_module, "health_check")
health_router = cast(APIRouter, getattr(_health_module, "router"))
NamespaceMiddleware = getattr(_namespace_module, "NamespaceMiddleware")

REST_AUTH_EXCLUDED_PATHS = ("/health",)
WEB_AUTH_EXCLUDED_PATHS = ("/api/health", "/health")


def create_rest_api(
    *,
    title: str = "Nocturne Memory API",
    description: str | None = None,
    version: str | None = None,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
    docs_url: str = "/docs",
    openapi_url: str = "/openapi.json",
) -> FastAPI:
    """Build the REST API app with the shared router and error-handler set."""

    app = FastAPI(
        title=title,
        description=description or "",
        version=version or "0.1.0",
        lifespan=lifespan,
        docs_url=docs_url,
        openapi_url=openapi_url,
    )

    @app.exception_handler(ConfigWriteError)
    async def config_write_error_handler(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    app.include_router(health_router)
    app.include_router(review_router)
    app.include_router(browse_router)
    app.include_router(maintenance_router)
    app.include_router(settings_router)

    return app


def add_standard_middleware(
    app: FastAPI,
    *,
    excluded_paths: Iterable[str] = REST_AUTH_EXCLUDED_PATHS,
) -> None:
    """Add CORS → Namespace → Auth middleware using FastAPI's stack semantics.

    FastAPI/Starlette `add_middleware()` makes the last added middleware the
    outermost layer. Adding Auth, then Namespace, then CORS preserves the
    intended request flow: CORS → Namespace → Auth → App.
    """

    app.add_middleware(
        BearerTokenAuthMiddleware,
        excluded_paths=list(excluded_paths),
    )
    app.add_middleware(NamespaceMiddleware)
    app.add_middleware(
        CORSMiddleware,
        **get_cors_config(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def wrap_standard_middleware(
    app: ASGIApp,
    *,
    excluded_paths: Iterable[str] = WEB_AUTH_EXCLUDED_PATHS,
) -> ASGIApp:
    """Wrap a raw ASGI app as CORS → Namespace → Auth → App."""

    return CORSMiddleware(
        NamespaceMiddleware(
            BearerTokenAuthMiddleware(app, excluded_paths=list(excluded_paths))
        ),
        **get_cors_config(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


class SPAFallback:
    """Route backend prefixes to the backend app; serve everything else as SPA."""

    def __init__(self, backend: ASGIApp, dist: Path, backend_prefixes: Iterable[str]):
        self.backend: ASGIApp = backend
        self.dist: Path = dist
        self.backend_prefixes: tuple[str, ...] = tuple(backend_prefixes)

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] != "http":
            await self.backend(scope, receive, send)
            return

        path = str(scope.get("path", "/"))
        if any(
            path == prefix or path.startswith(f"{prefix}/")
            for prefix in self.backend_prefixes
        ):
            await self.backend(scope, receive, send)
            return

        if not self.dist.is_dir():
            await PlainTextResponse(
                "Admin UI is building or missing. Please refresh in a moment...",
                status_code=503,
            )(scope, receive, send)
            return

        try:
            requested_file = (self.dist / path.lstrip("/")).resolve()
            if (
                path != "/"
                and requested_file.is_file()
                and requested_file.is_relative_to(self.dist)
            ):
                await FileResponse(requested_file)(scope, receive, send)
                return
        except (ValueError, OSError):
            pass

        index_file = self.dist / "index.html"
        if index_file.is_file():
            await FileResponse(index_file)(scope, receive, send)
            return

        await PlainTextResponse("Admin UI missing index.html.", status_code=404)(
            scope, receive, send
        )


def build_web_app(
    *,
    frontend_dir: Path,
    extra_routes: Sequence[Route | Mount] | None = None,
    extra_prefixes: Sequence[str] | None = None,
    lifespan: Callable[[Starlette], AbstractAsyncContextManager[None]] | None = None,
) -> ASGIApp:
    """Build REST API + optional extra routes + frontend SPA fallback."""

    api = create_rest_api(title="Nocturne Memory API")

    routes: list[Route | Mount] = list(extra_routes or [])
    routes.append(Mount("/api", app=api))

    async def _health_endpoint(request: Request):
        return await health_check()

    routes.append(Route("/health", endpoint=_health_endpoint))

    inner = Starlette(routes=routes, lifespan=lifespan)
    wrapped = wrap_standard_middleware(inner, excluded_paths=WEB_AUTH_EXCLUDED_PATHS)
    backend_prefixes = tuple(["/api", "/health"] + list(extra_prefixes or []))

    return SPAFallback(wrapped, frontend_dir, backend_prefixes)
