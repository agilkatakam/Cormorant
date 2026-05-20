"""Tests for RateGate self-throttling logic."""

import time
import unittest
from unittest.mock import patch

from cormorant.llm import RateGate


class TestRateGate(unittest.TestCase):

    def test_allows_calls_within_rpm(self):
        gate = RateGate(rpm=15)
        # Add 14 recent calls — next call should not wait
        now = time.time()
        for _ in range(14):
            gate.calls.append(now)
        # Should not sleep
        with patch("time.sleep") as mock_sleep:
            gate.wait_if_needed()
            mock_sleep.assert_not_called()

    def test_throttles_at_rpm_limit(self):
        gate = RateGate(rpm=15)
        now = time.time()
        # Simulate 15 calls that are clearly within the last 60s (1-15s ago)
        for i in range(1, 16):
            gate.calls.append(now - i)
        with patch("cormorant.llm.time.sleep") as mock_sleep:
            gate.wait_if_needed()
            mock_sleep.assert_called_once()
            sleep_arg = mock_sleep.call_args[0][0]
            self.assertGreater(sleep_arg, 0)

    def test_evicts_expired_calls(self):
        gate = RateGate(rpm=15)
        now = time.time()
        # Add 15 calls that are > 60 seconds old (expired)
        for i in range(15):
            gate.calls.append(now - 70)
        # Add 1 recent call
        gate.calls.append(now)
        # Should evict old calls and not throttle (only 1 recent call)
        with patch("time.sleep") as mock_sleep:
            gate.wait_if_needed()
            mock_sleep.assert_not_called()

    def test_records_new_call_after_wait(self):
        gate = RateGate(rpm=3)
        now = time.time()
        for _ in range(3):
            gate.calls.append(now)
        with patch("time.sleep"):
            gate.wait_if_needed()
        # After waiting, should have 4 calls recorded
        self.assertEqual(len(gate.calls), 4)

    def test_empty_gate_never_sleeps(self):
        gate = RateGate(rpm=15)
        with patch("time.sleep") as mock_sleep:
            gate.wait_if_needed()
            gate.wait_if_needed()
            gate.wait_if_needed()
            mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
