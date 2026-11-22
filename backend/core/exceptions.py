from rest_framework.exceptions import NotAuthenticated
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Stable error envelope; do not expose tracebacks or SQL to the browser."""
    response = exception_handler(exc, context)
    if response is not None:
        error = {"status": response.status_code, "details": response.data}
        # The browser must distinguish an expired session from a role or CSRF denial.
        if isinstance(exc, NotAuthenticated):
            error["code"] = "not_authenticated"
        response.data = {"error": error}
    return response
