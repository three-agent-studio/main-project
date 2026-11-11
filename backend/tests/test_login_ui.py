"""Exercise the session choice through the real CSRF-protected login endpoint."""
import pytest
from django.conf import settings
from django.test import Client

from accounts.models import User


@pytest.mark.django_db
@pytest.mark.parametrize("remember", [False, True])
def test_login_session_lifetime_and_safe_redirect(remember):
    User.objects.create_user(username="login_ui_student", password="synthetic-login-only")
    client = Client(enforce_csrf_checks=True)
    page = client.get("/auth/login/?next=/profile")
    assert page.status_code == 200
    data = {
        "username": "login_ui_student",
        "password": "synthetic-login-only",
        "next": "/profile",
        "csrfmiddlewaretoken": client.cookies["csrftoken"].value,
    }
    if remember:
        data["remember_me"] = "on"
    response = client.post("/auth/login/", data)
    assert response.status_code == 302
    assert response["Location"] == "/profile"
    assert client.get("/api/v1/me/").status_code == 200
    cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert client.session.get_expire_at_browser_close() is not remember
    if remember:
        assert int(cookie["max-age"]) == settings.SESSION_COOKIE_AGE
    else:
        assert cookie["max-age"] == ""
        assert cookie["expires"] == ""


@pytest.mark.django_db
def test_failed_login_preserves_username_and_choice_but_never_password():
    client = Client()
    response = client.post("/auth/login/", {
        "username": "synthetic_unknown_student",
        "password": "must-not-render-this-password",
        "remember_me": "on",
    })
    html = response.content.decode()
    assert response.status_code == 200
    assert 'role="alert"' in html
    assert 'value="synthetic_unknown_student"' in html
    assert 'name="remember_me" checked' in html
    assert "must-not-render-this-password" not in html
    assert client.get("/api/v1/me/").status_code == 403
