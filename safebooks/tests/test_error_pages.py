"""Local and production 404 checks with synthetic clients and isolated data."""
from django.conf import settings
from django.http import Http404, HttpResponse, StreamingHttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.views.defaults import page_not_found

from safebooks.middleware import BrowserNotFoundMiddleware
from safebooks.models import BookkeeperAccount, Client
from safebooks.tests.session_helpers import bind_authenticated_session
from safebooks.views import SESSION_BOOKKEEPER_ID_KEY


@override_settings(DEBUG=False)
class NotFoundPageTests(SimpleTestCase):
    def test_unknown_url_uses_branded_page_and_keeps_404_status(self):
        response = self.client.get("/this-page-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "SafeBooks | Page Not Found", status_code=404)
        self.assertContains(response, '<h1 id="notFoundTitle">Page not found</h1>', status_code=404)
        self.assertContains(response, f'class="not-found-home" href="{reverse("home")}"', status_code=404)
        self.assertContains(response, "Back to Home", status_code=404)
        self.assertContains(response, "css/not_found.css", status_code=404)
        self.assertContains(response, "images/Logo_safebooks.png", status_code=404)
        self.assertNotContains(response, "prefers-color-scheme", status_code=404)
        self.assertNotContains(response, "Logo_safebooks_dark.png", status_code=404)
        self.assertNotContains(response, "<script", status_code=404)

    def test_error_does_not_reflect_request_or_exception_details(self):
        request = RequestFactory().get("/private-client-marker/<script>/", {"token": "private-query-marker"})
        response = page_not_found(request, Http404("Private exception marker: No Client matches the given query."))

        self.assertEqual(response.status_code, 404)
        for private_detail in ("private-client-marker", "private-query-marker", "Private exception marker", "No Client matches", "<script>", "URL patterns"):
            self.assertNotContains(response, private_detail, status_code=404)

    def test_missing_page_head_request_keeps_404_without_response_body(self):
        response = self.client.head("/this-page-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.content, b"")

    @override_settings(DEBUG=True)
    def test_local_debug_404_uses_branded_page_without_disabling_debug(self):
        response = self.client.get("/this-page-does-not-exist/")

        self.assertTrue(settings.DEBUG)
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Back to Home", status_code=404)
        self.assertNotContains(response, "URL patterns", status_code=404)

    @override_settings(DEBUG=True)
    def test_local_head_request_also_keeps_404_without_response_body(self):
        response = self.client.head("/this-page-does-not-exist/")

        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertEqual(response.content, b"")


@override_settings(DEBUG=True)
class BrowserNotFoundMiddlewareTests(SimpleTestCase):
    def test_non_page_and_non_404_responses_are_unchanged(self):
        cases = (
            ("/api/missing/", "GET", "text/html", "text/html", 404),
            ("/api", "GET", "text/html", "text/html", 404),
            ("/static/missing.css", "GET", "text/html", "text/html", 404),
            ("/media/missing.png", "GET", "text/html", "text/html", 404),
            ("/missing/", "GET", "application/json", "text/html", 404),
            ("/missing/", "GET", "text/html", "application/json", 404),
            ("/missing/", "POST", "text/html", "text/html", 404),
            ("/valid/", "GET", "text/html", "text/html", 200),
            ("/failed/", "GET", "text/html", "text/html", 500),
        )
        for path, method, accept, content_type, status in cases:
            with self.subTest(path=path, method=method, status=status, content_type=content_type):
                request = RequestFactory().generic(method, path, HTTP_ACCEPT=accept)
                response = HttpResponse("original response", status=status, content_type=content_type)
                result = BrowserNotFoundMiddleware(lambda request: response)(request)
                self.assertIs(result, response)
                self.assertEqual(result.content, b"original response")

    def test_replaced_page_preserves_status_cookies_and_security_headers(self):
        request = RequestFactory().get("/missing/")
        response = HttpResponse("diagnostic details", status=404)
        response["Cache-Control"] = "no-store"
        response["Content-Length"] = len(response.content)
        response["ETag"] = '"original-body"'
        response.set_cookie("synthetic-cookie", "synthetic-value", httponly=True)

        result = BrowserNotFoundMiddleware(lambda request: response)(request)

        self.assertEqual(result.status_code, 404)
        self.assertContains(result, "Back to Home", status_code=404)
        self.assertNotContains(result, "diagnostic details", status_code=404)
        self.assertEqual(result["Cache-Control"], "no-store")
        self.assertEqual(int(result["Content-Length"]), len(result.content))
        self.assertNotIn("ETag", result)
        self.assertEqual(result.cookies["synthetic-cookie"].value, "synthetic-value")
        self.assertTrue(result.cookies["synthetic-cookie"]["httponly"])

    @override_settings(DEBUG=False)
    def test_production_response_is_not_replaced(self):
        request = RequestFactory().get("/missing/")
        response = HttpResponse("production response", status=404)
        result = BrowserNotFoundMiddleware(lambda request: response)(request)
        self.assertIs(result, response)
        self.assertEqual(result.content, b"production response")

    @override_settings(STATIC_URL="/assets/", MEDIA_URL="/uploads/")
    def test_configured_asset_prefixes_and_encoded_responses_are_preserved(self):
        for path in ("/assets/missing.css", "/uploads/missing.png"):
            request = RequestFactory().get(path)
            response = HttpResponse("asset response", status=404)
            self.assertEqual(BrowserNotFoundMiddleware(lambda request: response)(request).content, b"asset response")
        request = RequestFactory().get("/missing/")
        response = HttpResponse(b"encoded body", status=404)
        response["Content-Encoding"] = "gzip"
        self.assertEqual(BrowserNotFoundMiddleware(lambda request: response)(request).content, b"encoded body")
        streaming = StreamingHttpResponse([b"streaming body"], status=404, content_type="text/html")
        self.assertIs(BrowserNotFoundMiddleware(lambda request: streaming)(request), streaming)
        streaming.close()


@override_settings(DEBUG=False)
class ClientNotFoundPageTests(TestCase):
    def setUp(self):
        self.owner = BookkeeperAccount.objects.create(
            full_name="Error Page Owner", username="error-owner", email="error-owner@example.test",
            password_hash="not-used-in-test", status=BookkeeperAccount.STATUS_APPROVED,
            client_details_password_required=False,
        )
        other = BookkeeperAccount.objects.create(
            full_name="Other Owner", username="error-other", email="error-other@example.test",
            password_hash="not-used-in-test", status=BookkeeperAccount.STATUS_APPROVED,
        )
        self.foreign_client = Client.objects.create(
            bookkeeper=other, client_name="Private Foreign Client", tin_number="123456789001",
            location="Private Location", email_password="SyntheticPrivateValue",
        )
        session = self.client.session
        session[SESSION_BOOKKEEPER_ID_KEY] = self.owner.id
        bind_authenticated_session(session)
        session.save()

    def test_missing_and_foreign_clients_show_the_same_generic_404(self):
        for debug in (False, True):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                foreign = self.client.get(reverse("client_details", args=[self.foreign_client.id]))
                missing = self.client.get(reverse("client_details", args=[self.foreign_client.id + 10000]))

                for response in (foreign, missing):
                    self.assertEqual(response.status_code, 404)
                    self.assertTemplateUsed(response, "404.html")
                    for private_detail in (self.foreign_client.client_name, self.foreign_client.location, self.foreign_client.email_password, "URL patterns", "No Client matches"):
                        self.assertNotContains(response, private_detail, status_code=404)
                self.assertEqual(foreign.content, missing.content)

    def test_existing_client_api_errors_remain_json(self):
        for debug in (False, True):
            with self.subTest(debug=debug), override_settings(DEBUG=debug):
                response = self.client.get(reverse("api_client_detail", args=[self.foreign_client.id]))

                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.headers["Content-Type"], "application/json")
                self.assertFalse(response.json()["ok"])
                self.assertEqual(response.json()["message"], "Client not found.")
