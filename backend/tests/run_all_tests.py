"""Master Test Runner for FarmShield Backend.
Discovers and executes all unit, integration, and API endpoint test suites.

Usage:
    cd backend
    python tests/run_all_tests.py
"""

import sys
import unittest
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def run_tests():
    loader = unittest.TestLoader()
    tests_dir = BACKEND_DIR / "tests"
    suite = loader.discover(start_dir=str(tests_dir), pattern="test_*.py")

    print("=" * 70)
    print("FARMSHIELD BACKEND AUTOMATED TEST SUITE")
    print(f"Discovered test cases across: {tests_dir}")
    print("=" * 70)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("=" * 70)
    print(f"TESTS RUN: {result.testsRun}")
    print(f"FAILURES : {len(result.failures)}")
    print(f"ERRORS   : {len(result.errors)}")
    print("=" * 70)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(run_tests())
