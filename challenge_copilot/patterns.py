# -*- coding: utf-8 -*-
"""交付物模式匹配核心。

EduSeed 挑战的 deliverables 字段是形如 ``*proposal*,*AAR_W*,*AI日志*`` 的
通配模式串。本模块负责把它落到真实文件名上，并且把"差一点就命中"的文件单独
挑出来——这是本工具存在的核心理由。

所有规则都来自真实踩坑，不是推测：

R1  平台匹配的是**连续**子串。``*AI日志*`` 不命中 ``AI协作日志.md``（C1、C2 各踩一次）。
R2  英文命名不命中中文模式。``AI_LOG.md`` / ``ATTRIBUTION.md`` 对 ``*AI日志*`` 无效（C4D、C5）。
R3  全角空格、零宽字符、首尾空格会让"肉眼一样"的名字失配。
R4  ASCII 大小写默认按**敏感**处理：宁可报 missing 让人去改成完全一致，也不
    要在本地报 ready、到平台被拒。这是有意的保守取舍。
R5  平台最终在仓库里找文件；子目录里的命中会在报告里降级提示，建议移到根目录。
"""

from __future__ import annotations

import os
import re

# R3：肉眼不可见但会让匹配失败的字符
_INVISIBLE = "\u200b\u200c\u200d\ufeff\u00a0"

# 通配符到正则；* 和 ? 以外全部字面量
_GLOB_SPECIAL = set("*?")


def split_patterns(raw: str) -> list[str]:
    """把 ``*a*,*b*`` 拆成模式列表，去掉空项与首尾空格。"""
    if not raw:
        return []
    out = []
    for part in re.split(r"[,，;；]", raw):
        part = part.strip()
        if part:
            out.append(part)
    return out


def core_literal(pattern: str) -> str:
    """取出模式里的字面骨架：``*AAR_W*`` -> ``AAR_W``。

    近失检测需要一段"应该连续出现"的文字，纯通配符模式取不到骨架，返回空串。
    """
    return "".join(ch for ch in pattern if ch not in _GLOB_SPECIAL).strip()


def _glob_to_regex(pattern: str) -> str:
    buf = []
    for ch in pattern:
        if ch == "*":
            buf.append(".*")
        elif ch == "?":
            buf.append(".")
        else:
            buf.append(re.escape(ch))
    return "^" + "".join(buf) + "$"


def matches(pattern: str, name: str) -> bool:
    """模式是否命中文件名（R1 连续子串、R4 大小写敏感）。"""
    return re.match(_glob_to_regex(pattern), name) is not None


def sanitize_probe(name: str) -> str:
    """去掉不可见字符与首尾空白，得到"人以为它长这样"的名字。"""
    cleaned = name
    for ch in _INVISIBLE:
        cleaned = cleaned.replace(ch, "")
    return cleaned.strip()


def is_subsequence(needle: str, haystack: str) -> bool:
    """needle 的字符是否按顺序出现在 haystack 里（不要求连续）。"""
    it = iter(haystack)
    return all(ch in it for ch in needle)


def near_miss(pattern: str, name: str) -> str | None:
    """判断文件名是否是"本来想命中却没命中"，返回原因码，否则 None。

    原因码：
      R1_NOT_CONTIGUOUS  字面骨架的字符都在，但不是连续出现（AI协作日志）
      R3_INVISIBLE       含零宽/全角空格等不可见字符，且夹在骨架中间
      R4_CASE_ONLY       只有 ASCII 大小写不同

    注意一个容易写错的地方：对 ``*AI日志*`` 这种两侧都是通配符的模式，
    骨架**末尾**多出来的不可见字符仍然能匹配（``.*`` 盖住了它），所以只有
    夹在骨架中间的不可见字符才是真失配。这里据此判定，不做无用告警。
    """
    core = core_literal(pattern)
    if not core:
        return None
    if matches(pattern, name):
        return None

    stem = os.path.splitext(name)[0]
    probe = sanitize_probe(stem)

    # 不可见字符夹在骨架中间：清理后能命中，说明问题就在这些字符上
    if probe != stem and matches(pattern, probe + os.path.splitext(name)[1]):
        return "R3_INVISIBLE"

    # 只有大小写差异
    if matches(pattern.lower(), name.lower()):
        return "R4_CASE_ONLY"

    # 骨架字符齐全但被别的字隔开：AI协作日志 vs AI日志
    if len(core) >= 3 and is_subsequence(core, probe) and core not in probe:
        return "R1_NOT_CONTIGUOUS"

    # 英文下划线/连字符写法：AI_LOG、AAR-W 这类
    squashed = re.sub(r"[\s_\-]+", "", probe)
    if core not in squashed and is_subsequence(core, squashed):
        return "R1_NOT_CONTIGUOUS"

    return None


NEAR_MISS_HINTS = {
    "R1_NOT_CONTIGUOUS": "骨架文字被其它字隔开，平台要求连续出现；请改成骨架原样相邻的命名。",
    "R3_INVISIBLE": "文件名里夹着零宽字符或全角空格，肉眼看不出来；请重新命名。",
    "R4_CASE_ONLY": "只有 ASCII 大小写不同；请改成与模式完全一致。",
    "R2_ENGLISH_SUFFIX": "英文别名对中文模式无效；请用中文模式里的原词。",
}
