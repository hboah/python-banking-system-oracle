# banking_system/auth_backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.db import connection
from django.contrib import messages

UserModel = get_user_model()

class CBACAuthBackend(BaseBackend):
    """
    Custom backend:
    - Calls Oracle PL/SQL cbac_user_mgmt_pkg.login_user()
    - Records login in Oracle login_logs
    - Falls back to Django superuser/staff authentication
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        try:
            # 🔹 Call Oracle PL/SQL login_user
            with connection.cursor() as cursor:
                out_user_id = cursor.callfunc(
                    "cbac_user_mgmt_pkg.login_user",
                    int,  # return type (user_id number)
                    [username, password]
                )

            # If login succeeds, ensure a Django user exists
            user, created = UserModel.objects.get_or_create(
                username=username,
                defaults={"is_active": True}
            )
            if created:
                # New users default as non-staff unless promoted
                user.is_staff = False
                user.is_superuser = False
                user.save()

            return user

        except Exception as e:
            # Authentication failed at Oracle level
            if request:
                messages.error(request, f"Login failed: {e}")
            return None

    def get_user(self, user_id):
        try:
            return UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

    # -----------------------------
    # Permissions (keep minimal)
    # -----------------------------
    def get_user_permissions(self, user_obj, obj=None):
        return set()

    def get_group_permissions(self, user_obj, obj=None):
        return set()

    def get_all_permissions(self, user_obj, obj=None):
        if not user_obj or not getattr(user_obj, "is_active", False):
            return set()
        if getattr(user_obj, "is_superuser", False):
            return set()  # Superusers handled in has_perm
        return set()

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj or not getattr(user_obj, "is_active", False):
            return False
        if getattr(user_obj, "is_superuser", False):
            return True
        return False

    def has_module_perms(self, user_obj, app_label):
        if not user_obj or not getattr(user_obj, "is_active", False):
            return False
        if getattr(user_obj, "is_superuser", False):
            return True
        return False
