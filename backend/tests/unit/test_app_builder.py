import importlib
from pathlib import Path
from typing import Protocol, cast

from httpx import ASGITransport, AsyncClient

_app_builder = importlib.import_module("app_builder")
build_web_app = _app_builder.build_web_app
create_rest_api = _app_builder.create_rest_api
wrap_standard_middleware = _app_builder.wrap_standard_middleware


class RouteWithPath(Protocol):
    path: str


class MonkeyPatchLike(Protocol):
    def setattr(self, target: str, value: object, raising: bool = True) -> None: ...


def test_create_rest_api_registers_shared_routes():
    app = create_rest_api(title="Test API")
    paths = {
        cast(RouteWithPath, cast(object, route)).path
        for route in app.routes
        if hasattr(route, "path")
    }

    assert "/health" in paths
    assert "/browse/node" in paths
    assert "/review/groups" in paths
    assert "/maintenance/orphans" in paths
    assert "/settings" in paths
    assert app.title == "Test API"


async def test_wrap_standard_middleware_excludes_health_from_auth(
    monkeypatch: MonkeyPatchLike,
):
    monkeypatch.setattr("auth.get_api_token", lambda: "secret-token")
    app = wrap_standard_middleware(
        create_rest_api(title="Wrapped API"),
        excluded_paths=["/health"],
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        health = await client.get("/health")
        browse = await client.get("/browse/domains")

    assert health.status_code in {200, 503}
    assert browse.status_code == 401


async def test_build_web_app_routes_backend_prefixes_before_spa(tmp_path: Path):
    frontend_dir = tmp_path / "dist"
    frontend_dir.mkdir()
    _ = (frontend_dir / "index.html").write_text(
        "<main>Nocturne</main>",
        encoding="utf-8",
    )

    app = build_web_app(frontend_dir=frontend_dir)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        health = await client.get("/health")
        spa = await client.get("/memory/core")

    assert health.status_code in {200, 503}
    assert "Nocturne" in spa.text
