# -*- coding: utf-8 -*-
"""提交状态分析：从 list-my-submissions / list-challenges 的快照算进度与风险。

真实背景：C5 我曾经提交后被判"未入账"，查了半天才发现是自己的脚本用错了
字段字面量去匹配，平台其实早就入账。所以这个模块只做两件事——
按 challenge_id 归并、把"同一挑战多条提交"和"打回待改"显式标出来，
不做任何猜测性推断。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

# 平台里出现过的状态值；未知值原样保留，不静默丢弃
NEEDS_REWORK_STATES = {"needs_revision", "rejected", "failed"}
DONE_STATES = {"completed", "checked", "pending_teacher_review"}


@dataclass
class Submission:
    submission_id: str
    challenge_id: str
    project_title: str = ""
    status: str = ""
    task_state: str = ""
    submitted_at: str = ""

    @property
    def state(self) -> str:
        return (self.task_state or self.status or "unknown").strip()

    @property
    def needs_rework(self) -> bool:
        return self.state in NEEDS_REWORK_STATES or self.status in NEEDS_REWORK_STATES


@dataclass
class Challenge:
    challenge_id: str
    title: str
    deliverables: str = ""
    deadline: str = ""
    status: str = ""

    def days_left(self, today: date) -> int | None:
        if not self.deadline:
            return None
        try:
            due = datetime.fromisoformat(self.deadline).date()
        except ValueError:
            return None
        return (due - today).days


@dataclass
class ChallengeProgress:
    challenge: Challenge
    submissions: list[Submission] = field(default_factory=list)

    @property
    def latest(self) -> Submission | None:
        if not self.submissions:
            return None
        return max(self.submissions, key=lambda s: s.submitted_at or "")

    @property
    def is_submitted(self) -> bool:
        return bool(self.submissions)

    @property
    def duplicate_risk(self) -> bool:
        """同一挑战两条及以上成功提交记录 = 可能重复计提交次数。"""
        return len(self.submissions) > 1

    @property
    def needs_rework(self) -> bool:
        latest = self.latest
        return bool(latest and latest.needs_rework)


def _unwrap(payload) -> dict:
    """兼容 {ok:..., submissions:[...]} 与 {json:{...}} 两种包装。"""
    if not isinstance(payload, dict):
        return {}
    if "json" in payload and isinstance(payload["json"], dict):
        return payload["json"]
    if "data" in payload and isinstance(payload["data"], dict):
        return payload["data"]
    return payload


def load_submissions(payload) -> list[Submission]:
    data = _unwrap(payload)
    rows = data.get("submissions") or []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out.append(
            Submission(
                submission_id=row.get("submission_id", ""),
                challenge_id=row.get("challenge_id", ""),
                project_title=row.get("project_title", ""),
                status=row.get("status", ""),
                task_state=row.get("task_state", ""),
                submitted_at=row.get("submitted_at", ""),
            )
        )
    return out


def load_challenges(payload) -> list[Challenge]:
    data = _unwrap(payload)
    rows = data.get("challenges") or []
    out = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        cid = row.get("challenge_id") or row.get("id") or ""
        out.append(
            Challenge(
                challenge_id=cid,
                title=row.get("title", ""),
                deliverables=row.get("required_deliverables") or row.get("deliverables") or "",
                deadline=row.get("deadline") or row.get("due_at") or "",
                status=row.get("status", ""),
            )
        )
    return out


def build_progress(challenges: list[Challenge], submissions: list[Submission]) -> list[ChallengeProgress]:
    """按挑战归并提交记录；列表里没有的 challenge_id 也保留，不丢数据。"""
    by_id = {c.challenge_id: ChallengeProgress(challenge=c) for c in challenges}
    for sub in submissions:
        progress = by_id.get(sub.challenge_id)
        if progress is None:
            progress = ChallengeProgress(
                challenge=Challenge(challenge_id=sub.challenge_id, title="（平台未返回此挑战）")
            )
            by_id[sub.challenge_id] = progress
        progress.submissions.append(sub)
    return list(by_id.values())


def summarize(progress_list: list[ChallengeProgress], today: date) -> dict:
    submitted = [p for p in progress_list if p.is_submitted]
    rework = [p for p in progress_list if p.needs_rework]
    dup = [p for p in progress_list if p.duplicate_risk]
    pending = [p for p in progress_list if not p.is_submitted]
    # 未提交的按剩余天数排序，最近截止的排前面；无截止日的排最后
    def _key(p: ChallengeProgress):
        days = p.challenge.days_left(today)
        return (days is None, days if days is not None else 0)

    pending.sort(key=_key)
    return {
        "total_challenges": len(progress_list),
        "submitted": len(submitted),
        "pending": len(pending),
        "needs_rework": [p.challenge.challenge_id for p in rework],
        "duplicate_risk": [
            {
                "challenge_id": p.challenge.challenge_id,
                "title": p.challenge.title,
                "count": len(p.submissions),
                "submission_ids": [s.submission_id for s in p.submissions],
            }
            for p in dup
        ],
        "pending_list": [
            {
                "challenge_id": p.challenge.challenge_id,
                "title": p.challenge.title,
                "deliverables": p.challenge.deliverables,
                "days_left": p.challenge.days_left(today),
            }
            for p in pending
        ],
    }
