"""Presentation-only handling for browser page errors during development."""
from urllib.parse import urlsplit

from django.conf import settings
from django.template.loader import render_to_string


class BrowserNotFoundMiddleware:
    """Use the branded page for local HTML 404s without disabling debug mode."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            not settings.DEBUG
            or response.status_code != 404
            or request.method not in {"GET", "HEAD"}
            or response.streaming
            or response.headers.get("Content-Encoding")
            or response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower() != "text/html"
            or not request.accepts("text/html")
        ):
            return response

        path = request.path_info
        if path == "/api" or path.startswith("/api/"):
            return response
        for asset_url in (settings.STATIC_URL, settings.MEDIA_URL):
            asset_path = urlsplit(asset_url or "").path.strip("/")
            if asset_path and path.startswith(f"/{asset_path}/"):
                return response

        # Preserve status, cookies and headers supplied by the view. Outer
        # security/session middleware still runs normally on this response.
        response.content = render_to_string("404.html", request=request)
        if response.has_header("Content-Length"):
            response["Content-Length"] = str(len(response.content))
        response.headers.pop("ETag", None)
        return response
