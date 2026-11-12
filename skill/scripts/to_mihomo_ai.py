#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""surge-ai.list → mihomo-ai.yaml：逐条复制成 mihomo classical payload。

为什么不能用本仓 ads/direct 的 convert_ruleset.py：AI 清单含 DOMAIN-KEYWORD 与
URL-REGEX，那两条支路只吃「纯域名 + exact/suffix」两种语义。这里保持逐条复制，
不改写任何规则形态 —— 与迁入前 Self-Conf 的 build_rules.py 同口径。

⚠️ 引用方必须声明 behavior: classical。domain 行为下 KEYWORD / URL-REGEX
   就是一串永远匹配不上的字符（Self-Conf rulesets.md 已实测记录）。

用法：
    python skill/scripts/to_mihomo_ai.py            # 生成
    python skill/scripts/to_mihomo_ai.py --check    # 只查是否最新
    python skill/scripts/to_mihomo_ai.py --src X --out Y   # 可复现校验用
"""
from __future__ import annotations

import argparse
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

HEADER = '''# mihomo-ai.yaml
# ⚠️ 由 skill/scripts/to_mihomo_ai.py 从 surge-ai.list 生成，请勿手工编辑。
#    真源链：ai_sources/（10 份上游快照）→ build_ai.py → surge-ai.list → 本文件。
#
# 条数：%d
# 格式：mihomo rule-provider（format: yaml / behavior: classical）
#
# ⚠️ 含 DOMAIN-KEYWORD 与 URL-REGEX，必须用 classical；domain 行为下它们永不命中。
# ⚠️ 纯域名集、零 IP 条目 ⇒ 引用方不写规则级 no-resolve。
#########################################
'''


def read_rules(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def render(rules: list[str]) -> str:
    body = "payload:\n" + "".join("  - '%s'\n" % r.replace("'", "''") for r in rules)
    return (HEADER % len(rules)) + "\n" + body


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(ROOT / "surge-ai.list"))
    ap.add_argument("--out", default=str(ROOT / "mihomo-ai.yaml"))
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    src, out = Path(a.src), Path(a.out)
    if not src.is_file():
        print("❌ 真源缺失：%s" % src)
        return 2
    want = render(read_rules(src))
    have = out.read_text(encoding="utf-8") if out.is_file() else None

    if have == want:
        print("  OK %s（%d 条，已是最新）" % (out.name, len(read_rules(src))))
        return 0
    if a.check:
        print("❌ %s 已过期 —— 真源 %s 有更新，跑 regen.sh 重建" % (out.name, src.name))
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(want, encoding="utf-8", newline="\n")
    print("  ++ %s ← %s（%d 条）" % (out.name, src.name, len(read_rules(src))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
