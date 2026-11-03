# -*- coding: utf-8 -*-
"""命令行入口。

子命令：
  check   体检一个目录是否满足交付物模式（可给近似未命中提示）
  status  从两份快照算进度、打回项、重复提交风险
  report  体检 + 进度合成一份 Markdown
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime

from .checker import check_dir
from .report import render_check, render_status
from .submissions import build_progress, load_challenges, load_submissions


def _read_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _today(value: str | None) -> date:
    if not value:
        return date.today()
    return datetime.fromisoformat(value).date()


def _emit(text: str, as_json: bool, payload=None, out=None):
    body = json.dumps(payload, ensure_ascii=False, indent=2) if as_json else text
    if out:
        with open(out, "w", encoding="utf-8") as handle:
            handle.write(body if body.endswith("\n") else body + "\n")
        print("WROTE %s" % out)
    else:
        print(body)


def cmd_check(args) -> int:
    result = check_dir(args.repo, args.deliverables, require_root=args.require_root)
    if args.json:
        _emit("", True, result.to_dict(), args.out)
    else:
        _emit(render_check(result), False, None, args.out)
    return 0 if result.ready else 1


def cmd_status(args) -> int:
    challenges = load_challenges(_read_json(args.challenges))
    submissions = load_submissions(_read_json(args.submissions))
    progress = build_progress(challenges, submissions)
    today = _today(args.today)
    if args.json:
        from .submissions import summarize

        _emit("", True, summarize(progress, today), args.out)
    else:
        _emit(render_status(progress, today), False, None, args.out)
    return 0


def cmd_report(args) -> int:
    parts = []
    if args.repo and args.deliverables:
        result = check_dir(args.repo, args.deliverables, require_root=args.require_root)
        parts.append(render_check(result))
    if args.challenges and args.submissions:
        challenges = load_challenges(_read_json(args.challenges))
        submissions = load_submissions(_read_json(args.submissions))
        parts.append(render_status(build_progress(challenges, submissions), _today(args.today)))
    if not parts:
        print("report 需要至少一组输入：--repo/--deliverables 或 --challenges/--submissions")
        return 2
    _emit("\n---\n\n".join(parts), False, None, args.out)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="copilot",
        description="挑战交付管家：交付物模式体检 + 提交状态核查（零依赖）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="体检目录是否满足交付物模式")
    p_check.add_argument("--repo", required=True, help="要体检的目录")
    p_check.add_argument("--deliverables", required=True, help='形如 "*proposal*,*AAR_W*,*AI日志*"')
    p_check.add_argument("--require-root", action="store_true", help="只认根目录命中")
    p_check.add_argument("--json", action="store_true", help="输出 JSON")
    p_check.add_argument("--out", help="写入文件")
    p_check.set_defaults(func=cmd_check)

    p_status = sub.add_parser("status", help="从快照算进度与风险")
    p_status.add_argument("--challenges", required=True, help="list-challenges 返回的 JSON")
    p_status.add_argument("--submissions", required=True, help="list-my-submissions 返回的 JSON")
    p_status.add_argument("--today", help="统计日期 YYYY-MM-DD，默认今天")
    p_status.add_argument("--json", action="store_true")
    p_status.add_argument("--out", help="写入文件")
    p_status.set_defaults(func=cmd_status)

    p_report = sub.add_parser("report", help="合成 Markdown 报告")
    p_report.add_argument("--repo")
    p_report.add_argument("--deliverables")
    p_report.add_argument("--require-root", action="store_true")
    p_report.add_argument("--challenges")
    p_report.add_argument("--submissions")
    p_report.add_argument("--today")
    p_report.add_argument("--out", help="写入文件")
    p_report.set_defaults(func=cmd_report)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
