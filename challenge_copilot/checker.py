# -*- coding: utf-8 -*-
"""目录体检：把交付物模式跑到一个真实目录上，给出可执行的缺口清单。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .patterns import matches, near_miss, split_patterns, NEAR_MISS_HINTS

# 默认忽略的目录，避免把 node_modules / .git 里的文件当交付物
SKIP_DIRS = {
    ".git", ".github", "node_modules", "__pycache__", ".venv", "venv",
    ".idea", ".vscode", "dist", "build", ".pytest_cache", ".mypy_cache",
}

MAX_DEPTH = 4


@dataclass
class Hit:
    pattern: str
    path: str          # 相对目录的路径
    depth: int         # 0 = 根目录
    size: int


@dataclass
class NearMiss:
    pattern: str
    path: str
    reason: str
    hint: str


@dataclass
class CheckResult:
    root: str
    patterns: list[str]
    ready: bool = False
    hits: list[Hit] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    near_misses: list[NearMiss] = field(default_factory=list)
    empty_files: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "root": self.root,
            "patterns": self.patterns,
            "ready": self.ready,
            "missing": self.missing,
            "hit_count": len(self.hits),
            "hits": [
                {"pattern": h.pattern, "path": h.path, "depth": h.depth, "size": h.size}
                for h in self.hits
            ],
            "near_misses": [
                {"pattern": n.pattern, "path": n.path, "reason": n.reason, "hint": n.hint}
                for n in self.near_misses
            ],
            "empty_files": self.empty_files,
            "notes": self.notes,
        }


def _walk(root: str):
    """产出 (相对路径, 深度, 字节数)，按目录层级广度优先，根目录优先。"""
    root = os.path.abspath(root)
    queue = [(root, 0)]
    while queue:
        cur, depth = queue.pop(0)
        if depth > MAX_DEPTH:
            continue
        try:
            entries = sorted(os.scandir(cur), key=lambda e: e.name)
        except OSError:
            continue
        for entry in entries:
            rel = os.path.relpath(entry.path, root).replace("\\", "/")
            if entry.is_dir(follow_symlinks=False):
                if entry.name.lower() in SKIP_DIRS or entry.name.startswith("."):
                    continue
                queue.append((entry.path, depth + 1))
            elif entry.is_file(follow_symlinks=False):
                try:
                    size = entry.stat().st_size
                except OSError:
                    size = 0
                yield rel, depth, size


def check_dir(root: str, deliverables: str | list[str], require_root: bool = False) -> CheckResult:
    """体检一个目录。

    require_root=True 时，只有根目录的命中才算数（子目录命中降级为提示）。
    """
    patterns = split_patterns(deliverables) if isinstance(deliverables, str) else list(deliverables)
    result = CheckResult(root=os.path.abspath(root), patterns=patterns)

    if not os.path.isdir(result.root):
        result.notes.append("目录不存在：%s" % result.root)
        result.missing = list(patterns)
        return result

    files = list(_walk(result.root))
    basenames = [(rel, depth, size, os.path.basename(rel)) for rel, depth, size in files]

    for pattern in patterns:
        matched_any = False
        for rel, depth, size, base in basenames:
            if not matches(pattern, base):
                continue
            matched_any = True
            if require_root and depth > 0:
                result.notes.append(
                    "模式 %s 只在子目录命中（%s），平台在仓库里找文件，建议移到根目录。" % (pattern, rel)
                )
                continue
            result.hits.append(Hit(pattern=pattern, path=rel, depth=depth, size=size))
            if size == 0:
                result.empty_files.append(rel)
        if not matched_any or not any(h.pattern == pattern for h in result.hits):
            if pattern not in result.missing:
                result.missing.append(pattern)

    # 近失：只针对仍然 missing 的模式找"差一点"
    for pattern in list(result.missing):
        for rel, depth, size, base in basenames:
            reason = near_miss(pattern, base)
            if reason:
                result.near_misses.append(
                    NearMiss(pattern=pattern, path=rel, reason=reason,
                             hint=NEAR_MISS_HINTS.get(reason, ""))
                )

    if result.empty_files:
        result.notes.append("命中但文件为空：%s" % "、".join(result.empty_files))

    result.ready = bool(patterns) and not result.missing and not result.empty_files
    if not patterns:
        result.notes.append("没有给出任何交付物模式，无法判定。")
        result.ready = False
    return result
