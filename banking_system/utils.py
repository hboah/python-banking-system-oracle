import hashlib
from django.utils.html import format_html

def format_currency(value, currency="₵"):
    if value is None:
        return ""
    try:
        # Ensure value is converted to float or Decimal before formatting
        numeric_value = float(value)
        return format_html(f"{currency}{numeric_value:,.2f}")
    except (ValueError, TypeError):
        return str(value)

# banking_system/utils.py

def oracle_hash_password(password: str) -> str:
    """
    Mimics the Oracle PL/SQL hash function using SHA-256,
    and returns a lowercase hex string.
    """
    return hashlib.sha256(password.encode("utf-8")).hexdigest().lower()

# -----------------------------banking_system/oracle_utils.py
from django.db import connection, DatabaseError
from django.contrib import messages

def call_proc(proc_name, params=None):
    """Call a stored procedure that does not return a refcursor or value.
       params is a list/tuple of positional params."""
    params = params or []
    with connection.cursor() as cur:
        cur.callproc(proc_name, params)


def call_proc_with_one_out_refcursor(proc_name, params=None):
    """
    Calls a proc that returns a single OUT SYS_REFCURSOR as the last param.
    Returns (columns, rows) where columns is list of names, rows is list of tuples.
    Requires cx_Oracle/oracledb available.
    """
    params = params or []
    with connection.cursor() as cur:
        raw_conn = cur.connection
        # raw_conn is the raw DBAPI connection object.
        try:
            import cx_Oracle as oracledb_mod
        except Exception:
            try:
                import oracledb as oracledb_mod
            except Exception as e:
                raise RuntimeError("cx_Oracle/oracledb is required to fetch refcursors: " + str(e))

        raw_cursor = raw_conn.cursor()
        out_ref = raw_cursor.var(oracledb_mod.CURSOR)
        call_args = list(params) + [out_ref]
        cur.callproc(proc_name, call_args)
        result_cursor = out_ref.getvalue()
        rows = result_cursor.fetchall()
        cols = [d[0] for d in result_cursor.description] if result_cursor.description else []
        # close the result cursor
        result_cursor.close()
        raw_cursor.close()
        return cols, rows

def set_cbac_session(request):
    """
    Ensures Oracle session context matches the logged-in Django user.
    """
    if not request.user.is_authenticated:
        return  # skip if no user

    with connection.cursor() as cursor:
        try:
            cursor.callproc("CBAC_SESSION_VARIABLE_PKG.set_current_user", [request.user.user_id])
        except Exception as e:
            # You can log this instead of raising to avoid breaking views
            print(f"[CBAC Session Error] Failed to set session for user {request.user.username}: {e}")
