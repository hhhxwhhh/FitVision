from rest_framework.throttling import SimpleRateThrottle


class AuthRateThrottle(SimpleRateThrottle):
    """Stricter per-IP limit for login/registration endpoints."""

    scope = "auth"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}
