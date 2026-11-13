"""Only a compiled SPA entrypoint is served; source files and secrets are never roots."""

from pathlib import PurePosixPath

from django.conf import settings
from django.http import FileResponse, Http404
from django.views.decorators.http import require_safe


@require_safe
def frontend_entry(request, path=""):
    route = PurePosixPath(path)
    if route.suffix or any(part.startswith(".") for part in route.parts):
        raise Http404
    # Always open the fixed entrypoint, never join an untrusted URL into a filesystem path.
    response = FileResponse(
        (settings.FRONTEND_DIST / "index.html").open("rb"), content_type="text/html; charset=utf-8"
    )
    response["Cache-Control"] = "no-store"
    return response


def unavailable(request):
    raise Http404
