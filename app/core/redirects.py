from typing import cast

from starlette.applications import Starlette
from starlette.datastructures import URL
from starlette.requests import Request
from starlette.routing import Match


def safe_next(url: str | None, default: str = "/passages") -> str:
    if url and url.startswith("/") and not url.startswith("//"):
        return url
    return default


def return_path(request: Request, default: str = "/passages") -> str:
    """This page's path and query, for a form that should bring the user back here.

    A page rendered by a POST (a form shown again with an error) has a URL that may only
    accept POST, so it points back to the page the form was sent from: the Referer, if
    it is on this site and opens with GET. Without one, `default`.
    """
    if request.method == "GET":
        url = request.url
    else:
        referer = request.headers.get("referer")
        if referer is None:
            return default
        url = URL(referer)
        if url.netloc != request.url.netloc or not _opens_with_get(request, url.path):
            return default
    return url.path + (f"?{url.query}" if url.query else "")


def _opens_with_get(request: Request, path: str) -> bool:
    scope = {"type": "http", "method": "GET", "path": path, "root_path": ""}
    app = cast(Starlette, request.app)
    return any(route.matches(scope)[0] == Match.FULL for route in app.router.routes)
