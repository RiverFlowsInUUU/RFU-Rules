#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把文档里的条数声明同步成产物实际（v10 审查缺陷 2：周更自动化的另一半）。

为什么必须有这个脚本
====================
update.yml 无人值守跑 freeze → regen：上游一旦增删条目，六份产物条数就变，
而 README / SKILL / DetailsReadme 的手写读数若不同步，第 5 段判负 →
regen 非零 → 有 diff 也提交不出去 —— 周更沦为「上游零更新才能绿」的摆设。

分层：构建器管产物，本脚本管读数，**闸门独立复核** —— verify_products.py
不读本脚本的输出，只对文件实际；同步错了照样红，不构成同构互保。

模式清单与 verify_products.py 第 5 段的锚点同源；两边漂移的后果是 CI 红
（锚点未命中或数值不符），不会静默。改版式时两处一起改。

只动「当前状态描述」，不碰 CHANGELOG 等历史记录 —— 历史条目写的是当时条数。

用法
====
    python skill/scripts/sync_doc_counts.py     # 在 regen.sh 内自动调用
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

for _s in ("stdout", "stderr"):
    _f = getattr(sys, _s, None)
    if _f is not None and hasattr(_f, "reconfigure"):
        try:
            _f.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

ROOT = Path(__file__).resolve().parents[2]

PRODUCTS = {
    "ads": ["mihomo-ads.yaml", "surge-ads.list", "sing-box-ads.json"],
    "direct": ["mihomo-direct.yaml", "surge-direct.list", "sing-box-direct.json"],
}


def actual_counts() -> dict[str, int]:
    """以 Surge 产物为口径数条数（与 verify 的 parse_surge 同源：DOMAIN 开头行）。"""
    out = {}
    for fam, names in PRODUCTS.items():
        lines = (ROOT / names[1]).read_text(encoding="utf-8").splitlines()
        out[fam] = sum(1 for l in lines if l.startswith("DOMAIN"))
    return out


def sub_count(text: str, pat: str, value: int, group: int = 2) -> tuple[str, int]:
    """把 pat 捕获的数字组替换成 value，返回（新文本, 替换处数）。"""
    n = 0

    def _r(m: re.Match) -> str:
        nonlocal n
        n += 1
        return m.group(0)[:m.start(group) - m.start(0)] + str(value) + \
            m.group(0)[m.end(group) - m.start(0):]

    return re.sub(pat, _r, text), n


def main() -> int:
    c = actual_counts()
    ads, direct = c["ads"], c["direct"]
    edits: list[str] = []

    def sync(fname: str, pats: list[tuple[str, int]], label: str) -> None:
        p = ROOT / fname
        if not p.is_file():
            return
        text = p.read_text(encoding="utf-8")
        total = 0
        for pat, val in pats:
            text, n = sub_count(text, pat, val)
            total += n
        if total:
            p.write_text(text, encoding="utf-8", newline="")
            edits.append("%-34s %d 处" % (fname, total))

    # ── README：订阅表（形态 B 为主、形态 A 兜底）+ 徽章 + 门面读数 ──
    readme_pats = []
    for fam, names in PRODUCTS.items():
        for name in names:
            nm = re.escape(name)
            readme_pats.append((r'(\[`' + nm + r'`\]\([^)]+\)\s*`?)(\d+)(`?)', c[fam]))
            readme_pats.append((r'(\|\s*`' + nm + r'`\s*\|\s*)(\d+)(\s*\|)', c[fam]))
    readme_pats += [
        (r'(%E6%8B%A6%E6%88%AA-)(\d+)(%20)', ads),        # 徽章：拦截
        (r'(%E6%94%BE%E8%A1%8C-)(\d+)(%20)', direct),     # 徽章：放行
        (r'(\| 🚫 拦截 \| \*\*)(\d+)( 条\*\*)', ads),      # 一目了然
        (r'(\| ✅ 放行 \| \*\*)(\d+)( 条\*\*)', direct),   # 一目了然（5-d 锚同行）
        (r'(拦截 → REJECT\s*← )(\d+)( 条)', ads),          # 拿来即用 · 语义段
    ]
    sync("README.md", readme_pats, "README")

    # ── SKILL：预期读数 / 现读数（两行都是 ads+direct 双数字）──
    for fname in ("skill/SKILL.md",):
        p = ROOT / fname
        if p.is_file():
            text = p.read_text(encoding="utf-8")
            total = 0
            for pat in (r'(预期读数：`ads )(\d+)(` / `direct )(\d+)(`)',
                        r'(\|\s*现读数\s*\|\s*`ads )(\d+)(` / `direct )(\d+)(`\s*\|)'):
                m = re.search(pat, text)
                if m and (int(m.group(2)) != ads or int(m.group(4)) != direct):
                    text = text[:m.start(2)] + str(ads) + text[m.end(2):m.start(4)] \
                        + str(direct) + text[m.end(4):]
                    total += 1
            if total:
                p.write_text(text, encoding="utf-8", newline="")
                edits.append("%-34s %d 处" % (fname, total))

    # ── DetailsReadme：表格 + 汇总句 + 语义段 ──
    details_pats = []
    for fam, names in PRODUCTS.items():
        for name in names:
            nm = re.escape(name)
            details_pats.append((r'(\[`' + nm + r'`\]\([^)]+\)\s*`?)(\d+)(`?)', c[fam]))
            details_pats.append(
                (r'(\|\s*`' + nm + r'`\s*\|[^|]*\|\s*)(\d+)(\s*\|)', c[fam]))
    details_pats += [
        (r'(拦截集 )(\d+)( 条全部是)', ads),
        (r'(共 )(\d+)( 条)', direct),                     # 与第 5 段同口径：全部对 direct
    ]
    sync("DetailsReadme/DetailsReadme.md", details_pats, "Details")

    print("ads %d / direct %d" % (ads, direct))
    if edits:
        print("已同步：")
        for e in edits:
            print("  " + e)
    else:
        print("文档读数与产物一致，无需同步")
    return 0


if __name__ == "__main__":
    sys.exit(main())
