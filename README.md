# 挑战交付管家（Challenge Copilot）

一个**零依赖**的本地 CLI，用来自查两件事：

1. 我的提交目录里，平台的交付物模式（`*proposal*`、`*AAR_W*`、`*AI日志*`）到底命中没有？
2. 我的 N 个挑战，哪些已经提交、哪些被打回、哪些同一挑战提交了两条？

用 Python 3.9+ 直接跑，不需要 `pip install`，不需要联网。

```
python copilot.py check --repo . --deliverables "*proposal*,*AAR_W*,*AI日志*"
```

```
# 交付物体检报告

- 结论：**READY（可以提交）**

## 已命中 3 项

| 模式 | 文件 | 位置 | 字节 |
| --- | --- | --- | --- |
| `*proposal*` | `贾静文_C9_proposal_挑战交付管家.md` | 根目录 | 7576 |
| `*AAR_W*` | `贾静文_C9_AAR_W.md` | 根目录 | 8104 |
| `*AI日志*` | `贾静文_C9_AI日志.md` | 根目录 | 8554 |
```

---

## 为什么要做这个

这不是一个"练手项目"。它来自我连续提交十二个挑战的真实翻车记录：

| 我踩过的坑 | 后果 | 工具现在怎么防 |
| --- | --- | --- |
| 文件叫 `AI协作日志.md`，平台模式是 `*AI日志*` | 预检 `missing=["*AI日志*"]`，白跑一轮提交 | 近失检测：骨架字符齐全但不连续，直接指出来 |
| 用 `AI_LOG.md`、`README.md`、`ATTRIBUTION.md` 交英文名 | 中文模式一个都不命中 | 只做严格匹配，不猜"你是不是想交这个" |
| 脚本用错字段字面量判断"入账"，误判 C5 没提交成功 | 差点重复提交三次 | 状态模块只按 `challenge_id` 归并，未知状态原样保留 |
| 提交返回 `ok:true` 但任务随后 `failed`（漏 `projectSummary`） | 以为成功，实际没入账 | 状态模块把 `failed`/`needs_revision` 列为打回项优先处理 |
| 交付物放在子目录 | 平台在仓库里找文件，容易漏 | `--require-root` 可以把子目录命中降级为提示 |

上面每一条都能在本仓库的 `challenge_copilot/patterns.py` 注释里找到对应的规则编号（R1–R5），测试文件里有对应断言。

---

## 安装与使用

只需要 Python 3.9 或更高。不需要安装任何包。

```bash
git clone <本仓库>
cd challenge-copilot

# 1) 体检一个目录
python copilot.py check --repo . --deliverables "*proposal*,*AAR_W*,*AI日志*"

# 2) 只认根目录命中（更严格，贴近平台行为）
python copilot.py check --repo . --deliverables "*proposal*" --require-root

# 3) 机器可读输出，方便接进别的脚本
python copilot.py check --repo . --deliverables "*proposal*" --json

# 4) 从平台两份快照看整体进度
python copilot.py status \
  --challenges examples/challenges.snapshot.json \
  --submissions examples/submissions.snapshot.json \
  --today 2026-11-03

# 5) 合成一份 Markdown 报告
python copilot.py report \
  --repo . --deliverables "*proposal*,*AAR_W*,*AI日志*" \
  --challenges examples/challenges.snapshot.json \
  --submissions examples/submissions.snapshot.json \
  --out report.md
```

**退出码**：`check` 在 READY 时返回 0，有缺口时返回 1。可以这样用：

```bash
python copilot.py check --repo . --deliverables "$DELIVERABLES" || echo "先补齐再提交"
```

### 三个子命令

| 命令 | 输入 | 输出 |
| --- | --- | --- |
| `check` | 一个目录 + 交付物模式串 | 命中表、缺口、近失清单；`--json` 出结构化结果 |
| `status` | `list-challenges` 与 `list-my-submissions` 的 JSON | 已提交/未提交数量、打回项、重复提交风险、按剩余天数排序的待办 |
| `report` | 以上两组 | 一份可直接贴进提交说明的 Markdown |

`status` 支持三种包装格式：平台原始的 `{"submissions": [...]}`、插件包装的 `{"json": {...}}`、以及 `{"data": {...}}`。这是因为我实际拿到的快照两种都出现过。

---

## 近失检测是怎么判的

平台模式是 glob 语义（`*` 匹配任意串）。所以 `*AI日志*` 本质是"文件名里要**连续**出现 `AI日志` 三个字"。

工具先做严格匹配；对仍然缺失的模式，再判断每个文件是不是"本来想命中"：

| 原因码 | 触发条件 | 例子 |
| --- | --- | --- |
| `R1_NOT_CONTIGUOUS` | 骨架字符全在，但被别的字隔开 | `AI协作日志.md` 对 `*AI日志*` |
| `R3_INVISIBLE` | 零宽字符/全角空格**夹在骨架中间** | `AI<ZWSP>日志.md` |
| `R4_CASE_ONLY` | 只有 ASCII 大小写不同 | `aar_w.md` 对 `*AAR_W*` |

这里有个容易写反的点，我在测试里专门锁住了：对两侧都带 `*` 的模式，骨架**末尾**多出来的不可见字符其实仍能匹配（`.*` 会盖住它）。所以只有夹在骨架中间的不可见字符才算失配——否则会给一堆无意义的告警。对应的测试是 `test_trailing_invisible_still_matches`。

### 为什么大小写按敏感处理

我不确定平台的匹配实现是否忽略 ASCII 大小写。这种情况下我选择**保守**：本地按敏感判，宁可报一个 missing 让人把名字改成完全一致，也不要在本地报 READY、到平台被拒。这是一个有意的取舍，不是遗漏；如果确认平台忽略大小写，把 `matches()` 里的正则加 `re.IGNORECASE` 即可。

---

## 目录结构

```
challenge-copilot/
├── copilot.py                     # 入口，python copilot.py <子命令>
├── challenge_copilot/
│   ├── patterns.py                # 模式匹配 + 近失检测（规则 R1–R5 都在这里）
│   ├── checker.py                 # 目录体检、根目录降级、空文件检测
│   ├── submissions.py             # 按挑战归并提交、打回项、重复提交风险
│   ├── report.py                  # Markdown 渲染
│   └── cli.py                     # argparse 子命令
├── tests/
│   ├── test_patterns.py           # 17 条，锁住真实踩过的坑
│   ├── test_checker.py            # 8 条，临时目录构造真实布局
│   └── test_submissions.py        # 6 条
└── examples/
    ├── challenges.snapshot.json   # 真实快照：21 个挑战
    └── submissions.snapshot.json  # 真实快照：12 条提交
```

跑测试：

```bash
python -m unittest discover -s tests
# Ran 31 tests ... OK
```

---

## 已知边界

- **只读本地文件，不调用平台接口。** 快照需要你自己导出来喂给它。这是有意的：平台接口需要校园网，而我想让这个工具在任何网络下都能跑。
- **不判断"内容质量"。** 它只确认文件存在、非空、命名能命中。写得空洞它查不出来——那是人的责任。
- **不解析 docx/pdf 的内部结构。** 只看文件系统层面的名字与大小。
- **`status` 不做时间推断。** 提交时间按字符串比较取最新一条；如果平台返回的时间格式变了（不是 ISO 8601），排序会退化，但不会崩。

---

## 许可

自用项目，随 EduSeed C9 挑战一起提交。代码可自由取用。
