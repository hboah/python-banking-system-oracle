from django.db import connection
from django.contrib.auth.signals import user_logged_in, user_logged_out

def set_client_identifier(sender, request, user, **kwargs):
    identifier = f"{user.username}:{user.user_id}"  # ✅ your custom field
    with connection.cursor() as cur:
        # Use callproc instead of execute
        cur.callproc("DBMS_SESSION.SET_IDENTIFIER", [identifier])

def clear_client_identifier(sender, request, user, **kwargs):
    with connection.cursor() as cur:
        cur.callproc("DBMS_SESSION.CLEAR_IDENTIFIER")

user_logged_in.connect(set_client_identifier)
user_logged_out.connect(clear_client_identifier)
