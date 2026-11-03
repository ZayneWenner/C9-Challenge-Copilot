# -*- coding: utf-8 -*-
"""目录体检的单元测试：用临时目录构造真实文件布局。"""

import os
import tempfile
import unittest

from challenge_copilot.checker import check_dir


def touch(root, relative, content="x"):
    path = os.path.join(root, relative.replace("/", os.sep))
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)
    return path


class TestCheckDir(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def test_all_hit_is_ready(self):
        touch(self.tmp, "张三_C9_proposal.md")
        touch(self.tmp, "张三_C9_AAR_W.md")
        touch(self.tmp, "张三_C9_AI日志.md")
        result = check_dir(self.tmp, "*proposal*,*AAR_W*,*AI日志*")
        self.assertTrue(result.ready)
        self.assertEqual(result.missing, [])
        self.assertEqual(len(result.hits), 3)

    def test_missing_reported(self):
        touch(self.tmp, "张三_C9_proposal.md")
        result = check_dir(self.tmp, "*proposal*,*AAR_W*,*AI日志*")
        self.assertFalse(result.ready)
        self.assertEqual(result.missing, ["*AAR_W*", "*AI日志*"])

    def test_near_miss_surfaces_for_missing(self):
        touch(self.tmp, "AI协作日志.md")
        result = check_dir(self.tmp, "*AI日志*")
        self.assertIn("*AI日志*", result.missing)
        self.assertEqual(len(result.near_misses), 1)
        self.assertEqual(result.near_misses[0].reason, "R1_NOT_CONTIGUOUS")

    def test_empty_file_blocks_ready(self):
        touch(self.tmp, "AI日志.md", "")
        result = check_dir(self.tmp, "*AI日志*")
        self.assertFalse(result.ready)
        self.assertEqual(result.empty_files, ["AI日志.md"])

    def test_subdir_hit_downgraded_when_require_root(self):
        touch(self.tmp, "docs/AI日志.md")
        loose = check_dir(self.tmp, "*AI日志*")
        self.assertTrue(loose.ready)
        strict = check_dir(self.tmp, "*AI日志*", require_root=True)
        self.assertFalse(strict.ready)
        self.assertTrue(any("子目录" in n for n in strict.notes))

    def test_skips_node_modules(self):
        touch(self.tmp, "node_modules/x/AI日志.md")
        result = check_dir(self.tmp, "*AI日志*")
        self.assertFalse(result.ready)

    def test_missing_dir(self):
        result = check_dir(os.path.join(self.tmp, "nope"), "*AI日志*")
        self.assertFalse(result.ready)
        self.assertEqual(result.missing, ["*AI日志*"])


if __name__ == "__main__":
    unittest.main()
