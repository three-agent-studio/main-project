"""Axes integration; keep identifiers consistent with Django's authentication form."""

from django.contrib.auth import get_user_model


def normalized_login_username(request, credentials=None):
    value = (credentials or {}).get("username", request.POST.get("username", ""))
    # UsernameField normalizes Unicode and strips whitespace before authentication.
    # Apply the same rule to lockout lookup: padded names must not bypass the counter.
    return get_user_model().normalize_username(value or "").strip()


def no_client_ip(request):
    # Account-wide lockout works across IP changes and does not lock a whole campus NAT.
    # Do not trust arbitrary X-Forwarded-For headers or retain IPs unnecessarily.
    return None
