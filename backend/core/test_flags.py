"""
Test-environment flags that live in process memory and are safely accessible
across the WSGI boundary (i.e. from within FastAPI route handlers and model
properties during integration tests).

Usage in conftest.py:

    import tests.test_flags as test_flags   # or backend.core.test_flags
    test_flags.ENFORCE_ONBOARDING.value = True   # for test_recruiter_onboarding
    test_flags.ENFORCE_ONBOARDING.value = False  # for all other tests

Usage in backend code (models, deps, etc.):

    import os
    if os.getenv("TESTING") == "true":
        from core.test_flags import ENFORCE_ONBOARDING
        if not ENFORCE_ONBOARDING.value:
            return True   # bypass onboarding check for non-onboarding tests
"""

import threading

class _Flag:
    """A process-wide (not thread-local) boolean flag with a default value."""
    def __init__(self, default: bool = False):
        self._lock = threading.Lock()
        self._value = default

    @property
    def value(self) -> bool:
        with self._lock:
            return self._value

    @value.setter
    def value(self, v: bool) -> None:
        with self._lock:
            self._value = v


# When True, the onboarding check is fully enforced (no bypass).
# Set to True only when running test_recruiter_onboarding.py tests.
ENFORCE_ONBOARDING = _Flag(default=False)

# When True, we bypass email verification checks for recruiters and candidates in tests.
# Set to False only when testing verification lockouts (e.g. test_auth_hardening, test_candidate_verification).
BYPASS_EMAIL_VERIFICATION = _Flag(default=True)
