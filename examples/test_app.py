#!/usr/bin/env python3
"""
LogDot SDK Test Application

This script tests all SDK functionality against the live LogDot API.

Setup: Create a .env file in the project root with:
  LOGDOT_API_KEY=ilog_live_YOUR_API_KEY
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import logdot
sys.path.insert(0, str(__file__).rsplit("examples", 1)[0])

from logdot import LogDotLogger, LogDotMetrics


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
        print("\nAll tests passed! The Python SDK is working correctly.")
        sys.exit(0)


def run_tests() -> None:
    print("=" * 60)
    print("LogDot Python SDK Test Application")
    print("=" * 60)
    print()

    # Create separate logger and metrics clients
    logger = LogDotLogger(
        api_key=API_KEY,
        hostname="python-test-app",
        debug=True,
    )

    metrics = LogDotMetrics(
        api_key=API_KEY,
        debug=True,
    )

    passed = 0
    failed = 0

    # ==================== Test 1: Single Logs ====================
    print("\n--- Test 1: Single Logs (all levels) ---\n")

    # Debug
    result = logger.debug("Test debug message from Python SDK")
    if result:
        print("  [PASS] debug log sent successfully")
        passed += 1
    else:
        print("  [FAIL] debug log failed")
        failed += 1
    sleep(0.5)

    # Info
    result = logger.info("Test info message from Python SDK")
    if result:
        print("  [PASS] info log sent successfully")
        passed += 1
    else:
        print("  [FAIL] info log failed")
        failed += 1
    sleep(0.5)

    # Warn
    result = logger.warn("Test warn message from Python SDK")
    if result:
        print("  [PASS] warn log sent successfully")
        passed += 1
    else:
        print("  [FAIL] warn log failed")
        failed += 1
    sleep(0.5)

    # Error
    result = logger.error("Test error message from Python SDK")
    if result:
        print("  [PASS] error log sent successfully")
        passed += 1
    else:
        print("  [FAIL] error log failed")
        failed += 1
    sleep(0.5)

    # ==================== Test 2: Logs with Tags ====================
    print("\n--- Test 2: Logs with Tags ---\n")

    tag_result = logger.info(
        "Log with structured tags",
        {
            "sdk": "python",
            "version": "1.0.0",
            "test": True,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )

    if tag_result:
        print("  [PASS] Log with tags sent successfully")
        passed += 1
    else:
        print("  [FAIL] Log with tags failed")
        failed += 1
    sleep(0.5)

    # ==================== Test 3: Context-aware Logging ====================
    print("\n--- Test 3: Context-aware Logging ---\n")

    user_logger = logger.with_context({"user_id": 123, "session": "abc-123"})
    context_result = user_logger.info("User performed action", {"action": "login"})

    if context_result:
        print("  [PASS] Context-aware log sent successfully")
        print(f"  Context: {user_logger.get_context()}")
        passed += 1
    else:
        print("  [FAIL] Context-aware log failed")
        failed += 1
    sleep(0.5)

    # ==================== Test 4: Chained Context ====================
    print("\n--- Test 4: Chained Context ---\n")

    # Chain contexts - add more context to existing context
    request_logger = user_logger.with_context({"request_id": "req-456", "endpoint": "/api/users"})
    chained_result = request_logger.info("Processing request")

    if chained_result:
        print("  [PASS] Chained context log sent successfully")
        print(f"  Original context: {user_logger.get_context()}")
        print(f"  Chained context: {request_logger.get_context()}")
        passed += 1
    else:
        print("  [FAIL] Chained context log failed")
        failed += 1

    # Test context value overwriting
    overwrite_logger = user_logger.with_context({"user_id": 456})  # Overwrite user_id
    print(f"  Overwrite test - new user_id: {overwrite_logger.get_context()['user_id']}")
    sleep(0.5)

    # ==================== Test 5: Batch Logs ====================
    print("\n--- Test 5: Batch Logs (all levels) ---\n")

    logger.begin_batch()
    print("  Started batch mode")

    # Test all severity levels in batch
    logger.debug("Batch debug message", {"level": "debug"})
    logger.info("Batch info message", {"level": "info"})
    logger.warn("Batch warn message", {"level": "warn"})
    logger.error("Batch error message", {"level": "error"})
    print(f"  Added 4 messages (all levels) to batch (size: {logger.get_batch_size()})")

    batch_result = logger.send_batch()
    if batch_result:
        print("  [PASS] Batch logs sent successfully")
        passed += 1
    else:
        print("  [FAIL] Batch logs failed")
        failed += 1

    logger.end_batch()
    print("  Ended batch mode")
    sleep(0.5)

    # ==================== Test 6: Clear Batch ====================
    print("\n--- Test 6: Clear Batch ---\n")

    logger.begin_batch()
    logger.info("This message will be cleared")
    logger.info("This one too")
    print(f"  Batch size before clear: {logger.get_batch_size()}")

    logger.clear_batch()
    print(f"  Batch size after clear: {logger.get_batch_size()}")

    if logger.get_batch_size() == 0:
        print("  [PASS] clear_batch works correctly")
        passed += 1
    else:
        print("  [FAIL] clear_batch did not clear the batch")
        failed += 1

    logger.end_batch()
    sleep(0.5)

    # ==================== Test 7: Create/Get Metrics Entity ====================
    print("\n--- Test 7: Create/Get Metrics Entity ---\n")

    entity = metrics.get_or_create_entity(
        name="python-test-entity",
        description="Python SDK Test Entity",
        metadata={
            "sdk": "python",
            "environment": "test",
            "created_at": datetime.utcnow().isoformat() + "Z",
        },
    )

    if entity:
        print(f"  [PASS] Entity created/found (ID: {entity.id})")
        passed += 1
    else:
        print(f"  [FAIL] Entity creation failed: {metrics.get_last_error()}")
        failed += 1
        # Cannot continue without entity
        print_summary(passed, failed)
        return
    sleep(0.5)

    # ==================== Test 8: Single Metrics (using for_entity) ====================
    print("\n--- Test 8: Single Metrics ---\n")

    metrics_client = metrics.for_entity(entity.id)

    metric_result = metrics_client.send(
        "cpu_usage",
        45.5,
        "percent",
        {"host": "python-test", "core": 0},
    )

    if metric_result:
        print("  [PASS] Single metric sent successfully")
        passed += 1
    else:
        print(f"  [FAIL] Single metric failed: {metrics_client.get_last_error()}")
        failed += 1
    sleep(0.5)

    # ==================== Test 9: Batch Metrics (Same Metric) ====================
    print("\n--- Test 9: Batch Metrics (Same Metric) ---\n")

    metrics_client.begin_batch("temperature", "celsius")
    print('  Started batch mode for "temperature"')

    temperatures = [23.5, 24.1, 23.8, 24.5, 25.0]
    for temp in temperatures:
        metrics_client.add(temp, {"location": "server_room"})
    print(f"  Added {len(temperatures)} values (size: {metrics_client.get_batch_size()})")

    metric_batch_result = metrics_client.send_batch()
    if metric_batch_result:
        print("  [PASS] Metric batch sent successfully")
        passed += 1
    else:
        print(f"  [FAIL] Metric batch failed: {metrics_client.get_last_error()}")
        failed += 1

    metrics_client.end_batch()
    print("  Ended batch mode")
    sleep(0.5)

    # ==================== Test 10: Multi-Metric Batch ====================
    print("\n--- Test 10: Multi-Metric Batch ---\n")

    metrics_client.begin_multi_batch()
    print("  Started multi-metric batch mode")

    metrics_client.add_metric("memory_used", 2048, "MB", {"type": "heap"})
    metrics_client.add_metric("disk_free", 50.5, "GB", {"mount": "/"})
    metrics_client.add_metric("network_latency", 12.3, "ms", {"interface": "eth0"})
    print(f"  Added 3 different metrics (size: {metrics_client.get_batch_size()})")

    multi_batch_result = metrics_client.send_batch()
    if multi_batch_result:
        print("  [PASS] Multi-metric batch sent successfully")
        passed += 1
    else:
        print(f"  [FAIL] Multi-metric batch failed: {metrics_client.get_last_error()}")
        failed += 1

    metrics_client.end_batch()
    print("  Ended batch mode")

    # ==================== Summary ====================
    print_summary(passed, failed)


if __name__ == "__main__":
    run_tests()
