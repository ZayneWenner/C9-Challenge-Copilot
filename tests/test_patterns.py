# -*- coding: utf-8 -*-
"""模式匹配的单元测试：锁定真实踩过的坑，防止回归。"""

import unittest

from challenge_copilot.patterns import (
    core_literal,
    matches,
    near_miss,
    split_patterns,
)


class TestSplitPatterns(unittest.TestCase):
    def test_comma_split(self):
        self.assertEqual(split_patterns("*proposal*,*AAR_W*,*AI日志*"),
                         ["*proposal*", "*AAR_W*", "*AI日志*"])

    def test_mixed_separators_and_spaces(self):
        self.assertEqual(split_patterns(" *a* ， *b* "), ["*a*", "*b*"])

    def test_empty(self):
        self.assertEqual(split_patterns(""), [])


class TestMatches(unittest.TestCase):
    def test_contiguous_chinese(self):
        self.assertTrue(matches("*AI日志*", "贾静文_C9_AI日志.md"))

    def test_not_contiguous_is_rejected(self):
        # R1：C1、C2 踩过的坑
        self.assertFalse(matches("*AI日志*", "AI协作日志.md"))

    def test_plain_word_inside(self):
        self.assertTrue(matches("*proposal*", "贾静文_C9_proposal_提案.md"))

    def test_case_sensitive_by_default(self):
        # R4：保守取舍，宁可报 missing
        self.assertFalse(matches("*AAR_W*", "aar_w.md"))

    def test_wildcard_does_not_cross_dot(self):
        self.assertTrue(matches("*.md", "a.md"))
        self.assertFalse(matches("*.md", "a.md.bak"))


class TestNearMiss(unittest.TestCase):
    def test_detects_gap(self):
        self.assertEqual(near_miss("*AI日志*", "AI协作日志.md"), "R1_NOT_CONTIGUOUS")

    def test_detects_case(self):
        self.assertEqual(near_miss("*AAR_W*", "aar_w.md"), "R4_CASE_ONLY")

    def test_contiguous_is_not_near_miss(self):
        self.assertIsNone(near_miss("*AI日志*", "AI日志.md"))

    def test_unrelated_file_is_not_near_miss(self):
        self.assertIsNone(near_miss("*AI日志*", "README.md"))

    def test_invisible_char(self):
        # 零宽字符夹在骨架中间：从网页复制中文词时常见
        self.assertEqual(near_miss("*AI日志*", "AI\u200b日志.md"), "R3_INVISIBLE")

    def test_trailing_invisible_still_matches(self):
        # 两侧都带通配符时，骨架之后的不可见字符不影响匹配，不该报近失
        self.assertIsNone(near_miss("*AI日志*", "AI日志\u200b.md"))


class TestCoreLiteral(unittest.TestCase):
    def test_strip_wildcards(self):
        self.assertEqual(core_literal("*AAR_W*"), "AAR_W")

    def test_pure_wildcard(self):
        self.assertEqual(core_literal("**"), "")


if __name__ == "__main__":
    unittest.main()
