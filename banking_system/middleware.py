from django.shortcuts import redirect
from django.urls import reverse
from django.db import connection
import logging

logger = logging.getLogger(__name__)

class OracleSessionUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                with connection.cursor() as cur:
                    cur.execute("BEGIN CBAC_SESSION_VARIABLE_PKG.set_current_user(:1); END;", [request.user.user_id])
            except Exception as e:
                logger.warning("Failed to set CBAC session user: %s", e)
        return self.get_response(request)


EXEMPT_URLS = [
    "login",
    "logout",
    "register_customer",  # add other public routes here
]

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            # Only redirect if not hitting an exempt URL
            if request.resolver_match and request.resolver_match.url_name not in EXEMPT_URLS:
                return redirect(reverse("login"))
        return self.get_response(request)

from django.db import connection
from django.utils.deprecation import MiddlewareMixin

class OracleClientIdentifierMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            identifier = f"{request.user.username}:{request.user.user_id}"
            with connection.cursor() as cur:
                cur.callproc("DBMS_SESSION.SET_IDENTIFIER", [identifier])

# ============================================MIDDLEWARE FOR SESSION EXPIRY========================
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth import logout
from django.db import connection

class OracleSessionMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            # Refresh Oracle session timestamp if active
            with connection.cursor() as cursor:
                try:
                    cursor.callproc("cbac_user_mgmt_pkg.refresh_session", [request.user.username])
                except Exception:
                    pass

    def process_response(self, request, response):
        # If user was logged out, tell Oracle
        if not request.user.is_authenticated and request.session.get("_oracle_logged_out") is not True:
            username = request.session.get("last_username")
            if username:
                with connection.cursor() as cursor:
                    try:
                        cursor.callproc("cbac_user_mgmt_pkg.logout_user", [username])
                    except Exception:
                        pass
            request.session["_oracle_logged_out"] = True
        return response

    
