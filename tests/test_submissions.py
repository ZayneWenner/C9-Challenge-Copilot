# -*- coding: utf-8 -*-
"""提交状态分析的单元测试。"""

import unittest
from datetime import date

from challenge_copilot.submissions import (
    build_progress,
    load_challenges,
    load_submissions,
    summarize,
)

CHALLENGES = {
    "json": {
        "challenges": [
            {"challenge_id": "c1", "title": "C1", "required_deliverables": "*a*", "deadline": "2026-12-31T23:59"},
            {"challenge_id": "c2", "title": "C2", "required_deliverables": "*b*", "deadline": "2026-11-10T23:59"},
        ]
    }
}

SUBMISSIONS = {
    "json": {
        "submissions": [
            {"submission_id": "s1", "challenge_id": "c1", "status": "checked",
             "task_state": "pending_teacher_review", "submitted_at": "2026-11-01T10:00:00Z"},
            {"submission_id": "s2", "challenge_id": "c1", "status": "checked",
             "task_state": "needs_revision", "submitted_at": "2026-11-02T10:00:00Z"},
            {"submission_id": "s3", "challenge_id": "c9", "status": "checked",
             "task_state": "pending_teacher_review", "submitted_at": "2026-11-03T10:00:00Z"},
        ]
    }
}


class TestLoad(unittest.TestCase):
    def test_load_challenges(self):
        rows = load_challenges(CHALLENGES)
        self.assertEqual([c.challenge_id for c in rows], ["c1", "c2"])
        self.assertEqual(rows[0].deliverables, "*a*")

    def test_load_submissions(self):
        rows = load_submissions(SUBMISSIONS)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0].state, "pending_teacher_review")

    def test_unwraps_bare_dict(self):
        rows = load_submissions({"submissions": [{"submission_id": "x", "challenge_id": "c"}]})
        self.assertEqual(len(rows), 1)


class TestProgress(unittest.TestCase):
    def setUp(self):
        self.progress = build_progress(load_challenges(CHALLENGES), load_submissions(SUBMISSIONS))

    def test_unknown_challenge_kept(self):
        ids = [p.challenge.challenge_id for p in self.progress]
        self.assertIn("c9", ids)

    def test_latest_picks_newest(self):
        c1 = next(p for p in self.progress if p.challenge.challenge_id == "c1")
        self.assertEqual(c1.latest.submission_id, "s2")

    def test_duplicate_risk_on_two_subs(self):
        c1 = next(p for p in self.progress if p.challenge.challenge_id == "c1")
        self.assertTrue(c1.duplicate_risk)

    def test_rework_flagged_from_latest(self):
        c1 = next(p for p in self.progress if p.challenge.challenge_id == "c1")
        self.assertTrue(c1.needs_rework)

    def test_summary_counts_and_order(self):
        summary = summarize(self.progress, date(2026, 11, 3))
        self.assertEqual(summary["total_challenges"], 3)
        self.assertEqual(summary["submitted"], 2)
        self.assertEqual(summary["pending"], 1)
        self.assertEqual(summary["needs_rework"], ["c1"])
        self.assertEqual(summary["pending_list"][0]["challenge_id"], "c2")
        self.assertEqual(summary["pending_list"][0]["days_left"], 7)


if __name__ == "__main__":
    unittest.main()
