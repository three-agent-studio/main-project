"""Guard the boundary between compiled UI routes and private server endpoints."""

import pytest


@pytest.fixture
def preview(settings, tmp_path):
    settings.ROOT_URLCONF = "config.urls_team_preview"
    settings.FRONTEND_DIST = tmp_path
    (tmp_path / "index.html").write_text("<html>compiled-ui</html>")


@pytest.mark.parametrize("path", ["/", "/profile", "/requests/42"])
def test_ui_navigation_serves_fixed_entrypoint(client, preview, path):
    response = client.get(path)
    assert response.status_code == 200
    assert b"compiled-ui" in b"".join(response.streaming_content)
    assert response["Cache-Control"] == "no-store"


@pytest.mark.parametrize(
    "path",
    [
        "/.env",
        "/nested/.secret",
        "/scripts/team_preview.py",
        "/assets/missing.js",
        "/static/missing.css",
        "/api/unknown/",
        "/auth/unknown/",
        "/health/unknown/",
        "/admin/",
        "/admin/login/",
    ],
)
def test_preview_never_falls_back_for_server_or_file_paths(client, preview, path):
    assert client.get(path).status_code == 404


def test_preview_rejects_ui_writes(client, preview):
    assert client.post("/profile").status_code == 405


def test_preview_keeps_api_authentication(client, preview):
    response = client.get("/api/v1/me/")
    assert response.status_code == 403
    assert "no-store" in response["Cache-Control"]


def test_compiled_assets_are_served_by_whitenoise(client, preview, settings, tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "app.123.js").write_text("export const synthetic = true;")
    settings.WHITENOISE_ROOT = tmp_path
    settings.WHITENOISE_AUTOREFRESH = False
    settings.WHITENOISE_USE_FINDERS = False
    settings.STATIC_ROOT = tmp_path / "collected"
    settings.STATIC_ROOT.mkdir()
    settings.MIDDLEWARE = [
        "whitenoise.middleware.WhiteNoiseMiddleware",
        *settings.MIDDLEWARE,
    ]
    response = client.get("/assets/app.123.js")
    assert response.status_code == 200
    assert "javascript" in response["Content-Type"]
    assert b"export const synthetic" in b"".join(response.streaming_content)
    assert client.get("/assets/missing.js").status_code == 404


def test_proxy_https_header_does_not_cause_redirect_loop(client, preview, settings):
    settings.SECURE_SSL_REDIRECT = True
    settings.SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    assert client.get("/", HTTP_X_FORWARDED_PROTO="https").status_code == 200
    response = client.get("/", HTTP_X_FORWARDED_PROTO="http")
    assert response.status_code == 301
    assert response["Location"] == "https://testserver/"


def test_static_gzip_negotiation_preserves_complete_javascript(client, preview, settings, tmp_path):
    import gzip

    body = b"// synthetic compiled JavaScript\n" * 1000
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "compiled-1234abcd.js").write_bytes(body)
    (assets / "compiled-1234abcd.js.gz").write_bytes(gzip.compress(body))
    settings.WHITENOISE_IMMUTABLE_FILE_TEST = r"^/assets/[^/]+-[A-Za-z0-9_-]{8}\.(?:js|css)$"
    settings.WHITENOISE_ROOT = tmp_path
    settings.WHITENOISE_AUTOREFRESH = False
    settings.WHITENOISE_USE_FINDERS = False
    settings.STATIC_ROOT = tmp_path / "collected"
    settings.STATIC_ROOT.mkdir()
    settings.MIDDLEWARE = ["whitenoise.middleware.WhiteNoiseMiddleware", *settings.MIDDLEWARE]
    response = client.get("/assets/compiled-1234abcd.js", HTTP_ACCEPT_ENCODING="gzip")
    content = b"".join(response.streaming_content)
    assert response.status_code == 200
    assert response["Content-Encoding"] == "gzip"
    assert "immutable" in response["Cache-Control"]
    assert "Accept-Encoding" in response["Vary"]
    assert len(content) < len(body)
    assert gzip.decompress(content) == body
