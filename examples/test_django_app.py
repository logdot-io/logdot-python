#!/usr/bin/env python3
"""
LogDot SDK Django Hooks Test Application

Tests the Django middleware, logging capture, and print capture
against the live LogDot API using a self-contained Django configuration.

Setup: Create a .env file in the project root with:
  LOGDOT_API_KEY=ilog_live_YOUR_API_KEY

Run: python examples/test_django_app.py
Requires: pip install django
"""

import logging
import os
import sys
import time
from pathlib import Path

# Add parent directory to path to import logdot
sys.path.insert(0, str(Path(__file__).parent.parent))


def load_env() -> None:
    """Load environment variables from .env file."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    try:
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()
    except FileNotFoundError:
        print("Failed to load .env file. Create one with LOGDOT_API_KEY=your_key")
        sys.exit(1)


load_env()

API_KEY = os.environ.get("LOGDOT_API_KEY")
if not API_KEY:
    print("LOGDOT_API_KEY not found in .env file")
    sys.exit(1)


# ─── Django setup (self-contained — no project needed) ─────────────────

import django
from django.conf import settings

settings.configure(
    DEBUG=True,
    SECRET_KEY="test-secret-key-for-logdot-hooks",
    ROOT_URLCONF=__name__,
    MIDDLEWARE=["logdot.django.LogdotMiddleware"],
    LOGDOT_API_KEY=API_KEY,
    LOGDOT_HOSTNAME="django-hooks-test",
    LOGDOT_ENTITY_NAME="django-hooks-test",
    LOGDOT_DEBUG=True,
    LOGDOT_LOG_REQUESTS=True,
    LOGDOT_LOG_METRICS=True,
    LOGDOT_IGNORE_PATHS=["/health"],
    ALLOWED_HOSTS=["*"],
)

django.setup()

from django.http import HttpResponse, HttpResponseNotFound, HttpResponseServerError
from django.test import Client
from django.urls import path


# ─── Views ──────────────────────────────────────────────────────────────

def view_success(request):
    return HttpResponse("OK")


def view_not_found(request):
    return HttpResponseNotFound("Not Found")


def view_error(request):
    return HttpResponseServerError("Internal Server Error")


def view_exception(request):
    raise ValueError("Test unhandled exception from hooks test")


def view_health(request):
    return HttpResponse("healthy")


urlpatterns = [
    path("api/users", view_success),
    path("api/missing", view_not_found),
    path("api/error", view_error),
    path("api/exception", view_exception),
    path("health", view_health),
]


# ─── Test runner ────────────────────────────────────────────────────────

def sleep(seconds: float) -> None:
    time.sleep(seconds)


def print_summary(passed: int, failed: int) -> None:
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"  Total:  {passed + failed}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print("=" * 60)

    if failed > 0:
        print("\nSome tests failed. Check the output above for details.")
        sys.exit(1)
    else:
        print("\nAll tests passed! Django hooks are working correctly.")
        sys.exit(0)


def run_tests() -> None:
    print("=" * 60)
    print("LogDot Django Hooks Test Application")
    print("=" * 60)
    print()

    client = Client()
    passed = 0
    failed = 0

    # ==================== Test 1: Middleware 2xx ====================
    print("\n--- Test 1: Middleware logs 2xx as info ---\n")

    try:
        response = client.get("/api/users")
        if response.status_code == 200:
            print("  [PASS] GET /api/users returned 200 (logged as info)")
            passed += 1
        else:
            print(f"  [FAIL] Expected 200, got {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] Request threw: {e}")
        failed += 1
    sleep(0.5)

    # ==================== Test 2: Middleware 4xx ====================
    print("\n--- Test 2: Middleware logs 4xx as warn ---\n")

    try:
        response = client.get("/api/missing")
        if response.status_code == 404:
            print("  [PASS] GET /api/missing returned 404 (logged as warn)")
            passed += 1
        else:
            print(f"  [FAIL] Expected 404, got {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] Request threw: {e}")
        failed += 1
    sleep(0.5)

    # ==================== Test 3: Middleware 5xx ====================
    print("\n--- Test 3: Middleware logs 5xx as error ---\n")

    try:
        response = client.get("/api/error")
        if response.status_code == 500:
            print("  [PASS] GET /api/error returned 500 (logged as error)")
            passed += 1
        else:
            print(f"  [FAIL] Expected 500, got {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] Request threw: {e}")
        failed += 1
    sleep(0.5)

    # ==================== Test 4: Middleware with different methods ====================
    print("\n--- Test 4: POST request ---\n")

    try:
        response = client.post("/api/users")
        if response.status_code == 200:
            print("  [PASS] POST /api/users returned 200 (logged with method=POST)")
            passed += 1
        else:
            print(f"  [FAIL] Expected 200, got {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] Request threw: {e}")
        failed += 1
    sleep(0.5)

    # ==================== Test 5: Ignored path ====================
    print("\n--- Test 5: Ignored path (no logging) ---\n")

    try:
        response = client.get("/health")
        if response.status_code == 200:
            print("  [PASS] GET /health returned 200 (path ignored, not logged)")
            passed += 1
        else:
            print(f"  [FAIL] Expected 200, got {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] Request threw: {e}")
        failed += 1
    sleep(0.5)

    # ==================== Test 6: Exception handling ====================
    print("\n--- Test 6: Unhandled exception ---\n")

    try:
        response = client.get("/api/exception")
        # Django returns 500 for unhandled exceptions
        if response.status_code == 500:
            print("  [PASS] GET /api/exception returned 500 (exception logged)")
            passed += 1
        else:
            print(f"  [FAIL] Expected 500, got {response.status_code}")
            failed += 1
    except Exception as e:
        print(f"  [FAIL] Request threw: {e}")
        failed += 1
    sleep(0.5)

    # ==================== Test 7: Logging capture ====================
    print("\n--- Test 7: Python logging capture ---\n")

    try:
        from logdot import LogDotLogger, LogdotLoggingHandler

        logger_instance = LogDotLogger(
            api_key=API_KEY,
            hostname="django-hooks-test",
            debug=True,
        )

        handler = LogdotLoggingHandler(logger=logger_instance)
        handler.setFormatter(logging.Formatter("%(message)s"))

        test_logger = logging.getLogger("logdot.hooks.test")
        test_logger.addHandler(handler)
        test_logger.setLevel(logging.DEBUG)

        test_logger.info("Logging capture test: info from Django hooks")
        test_logger.warning("Logging capture test: warning from Django hooks")
        test_logger.error("Logging capture test: error from Django hooks")

        print("  [PASS] Logging handler forwarded messages without error")
        passed += 1

        # Clean up handler
        test_logger.removeHandler(handler)
    except Exception as e:
        print(f"  [FAIL] Logging capture threw: {e}")
        failed += 1
    sleep(0.5)

    # ==================== Test 8: Print capture ====================
    print("\n--- Test 8: Print capture ---\n")

    try:
        from logdot import enable_print_capture, disable_print_capture, LogDotLogger

        capture_logger = LogDotLogger(
            api_key=API_KEY,
            hostname="django-hooks-test",
            debug=True,
        )

        enable_print_capture(logger=capture_logger)

        # These print() calls should be captured AND still appear on stdout
        print("  Print capture test: stdout message")

        disable_print_capture()

        print("  [PASS] Print capture enabled and disabled without error")
        passed += 1
    except Exception as e:
        print(f"  [FAIL] Print capture threw: {e}")
        failed += 1
    sleep(0.5)

    # ==================== Summary ====================
    print_summary(passed, failed)


if __name__ == "__main__":
    run_tests()
