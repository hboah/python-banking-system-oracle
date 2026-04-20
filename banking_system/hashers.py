from django.contrib.auth.hashers import BasePasswordHasher
from django.utils.crypto import constant_time_compare
from django.db import connection

class OracleCBACPasswordHasher(BasePasswordHasher):
    """
    Custom password hasher that delegates hashing to Oracle package CBAC_UTILS_PKG.hash_password.
    """
    algorithm = "oracle_cbac"

    def salt(self):
        # Oracle package handles hashing, no salt on Django side
        return ""

    def encode(self, password, salt=None, iterations=None):
        if password is None:
            raise ValueError("Password must not be None")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT CBAC_UTILS_PKG.hash_password(:pw) FROM dual",
                {"pw": password}
            )
            oracle_hashed, = cursor.fetchone()

        # store as algorithm$hash so Django knows what hasher was used
        return f"{self.algorithm}${oracle_hashed}"

    def verify(self, password, encoded):
        algorithm, oracle_hashed = encoded.split("$", 1)
        if algorithm != self.algorithm:
            return False

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT CBAC_UTILS_PKG.hash_password(:pw) FROM dual",
                {"pw": password}
            )
            check_hash, = cursor.fetchone()

        return constant_time_compare(oracle_hashed, check_hash)

    def must_update(self, encoded):
        return False  # no need to update — Oracle hashing is stable

    def harden_runtime(self, password, encoded):
        pass  # no-op
