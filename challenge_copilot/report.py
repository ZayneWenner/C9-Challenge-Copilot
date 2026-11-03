# -*- coding: utf-8 -*-
"""把体检结果与进度汇总渲染成 Markdown，方便直接贴进提交说明或复盘。"""

from __future__ import annotations

from .checker import CheckResult
from .submissions import summarize


def render_check(result: CheckResult) -> str:
    lines = []
    lines.append("# 交付物体检报告")
    lines.append("")
    lines.append("- 目录：`%s`" % result.root)
    lines.append("- 模式：%s" % "、".join(result.patterns))
    lines.append("- 结论：**%s**" % ("READY（可以提交）" if result.ready else "NOT READY（有缺口）"))
    lines.append("")

    if result.missing:
        lines.append("## 缺口 %d 项" % len(result.missing))
        lines.append("")
        for pattern in result.missing:
            lines.append("- `%s`" % pattern)
            related = [n for n in result.near_misses if n.pattern == pattern]
            for near in related:
                lines.append("  - 近似但未命中：`%s`（%s）" % (near.path, near.reason))
                lines.append("    - %s" % near.hint)
        lines.append("")

    if result.hits:
        lines.append("## 已命中 %d 项" % len(result.hits))
        lines.append("")
        lines.append("| 模式 | 文件 | 位置 | 字节 |")
        lines.append("| --- | --- | --- | --- |")
        for hit in result.hits:
            where = "根目录" if hit.depth == 0 else "子目录(深度 %d)" % hit.depth
            lines.append("| `%s` | `%s` | %s | %d |" % (hit.pattern, hit.path, where, hit.size))
        lines.append("")

    if result.notes:
        lines.append("## 提示")
        lines.append("")
        for note in result.notes:
            lines.append("- %s" % note)
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def render_status(progress_list, today) -> str:
    summary = summarize(progress_list, today)
    lines = []
    lines.append("# 挑战进度概览")
    lines.append("")
    lines.append("- 统计日期：%s" % today.isoformat())
    lines.append("- 挑战总数：%d，已提交：%d，未提交：%d"
                 % (summary["total_challenges"], summary["submitted"], summary["pending"]))
    lines.append("")

    if summary["needs_rework"]:
        lines.append("## 打回待改（优先处理）")
        lines.append("")
        for cid in summary["needs_rework"]:
            lines.append("- `%s`" % cid)
        lines.append("")

    if summary["duplicate_risk"]:
        lines.append("## 重复提交风险")
        lines.append("")
        for item in summary["duplicate_risk"]:
            lines.append("- %s（`%s`）共 %d 条：%s"
                         % (item["title"] or item["challenge_id"], item["challenge_id"],
                            item["count"], "、".join(item["submission_ids"])))
        lines.append("")

    if summary["pending_list"]:
        lines.append("## 未提交，按剩余天数排序")
        lines.append("")
        lines.append("| 挑战 | 交付物模式 | 剩余天数 |")
        lines.append("| --- | --- | --- |")
        for item in summary["pending_list"]:
            days = item["days_left"]
            days_text = "—" if days is None else str(days)
            lines.append("| %s | `%s` | %s |" % (item["title"] or item["challenge_id"],
                                                item["deliverables"] or "—", days_text))
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
