from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    """Stable error envelope; do not expose tracebacks or SQL to the browser."""
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {"error": {"status": response.status_code, "details": response.data}}
    return response
