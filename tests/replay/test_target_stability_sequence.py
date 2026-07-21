#!/usr/bin/env python3
# encoding: utf-8

import sys
import unittest
from pathlib import Path


REPLAY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(REPLAY_DIR))

from replay_target_stability_sequence import (  # noqa: E402
    run_generation_sequence,
    run_interrupted_sequence,
    run_state_sequence,
    validate_run,
)


POSITIONS = [
    (0.050, 0.040, 0.457),
    (0.051, 0.041, 0.456),
    (0.052, 0.040, 0.458),
    (0.050, 0.039, 0.456),
    (0.051, 0.040, 0.457),
    (0.052, 0.041, 0.456),
]


class TargetStabilitySequenceTest(unittest.TestCase):
    def make_run(self):
        return {
            "main_sequence": run_state_sequence(POSITIONS),
            "interrupted_sequence": run_interrupted_sequence(POSITIONS),
            "generation_sequence": run_generation_sequence(),
        }

    def test_present_empty_reappear_sequence(self):
        run = self.make_run()
        self.assertTrue(validate_run(run))

        main = run["main_sequence"]
        self.assertEqual([item["count"] for item in main], [1, 2, 3, 0, 1, 2, 3])
        self.assertIsNone(main[3]["target"])

    def test_frames_cannot_bridge_an_empty_observation(self):
        interrupted = self.make_run()["interrupted_sequence"]
        self.assertEqual([item["count"] for item in interrupted], [1, 2, 0, 1])
        self.assertFalse(interrupted[-1]["stable"])
        self.assertIsNone(interrupted[-1]["target"])

    def test_reset_rejects_queued_and_inflight_old_frames(self):
        generation = run_generation_sequence()
        self.assertFalse(generation["inflight_old_generation_accepted"])
        self.assertFalse(generation["queued_old_timestamp_accepted"])
        self.assertTrue(generation["fresh_new_generation_accepted"])

    def test_sequence_is_deterministic(self):
        first = self.make_run()
        second = self.make_run()
        third = self.make_run()
        self.assertEqual(first, second)
        self.assertEqual(second, third)


if __name__ == "__main__":
    unittest.main()
