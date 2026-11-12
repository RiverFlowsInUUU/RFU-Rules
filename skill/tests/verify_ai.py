#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RFU-AI 清单的独立闸门（离线，不联网）。

为什么不塞进 verify_products.py 的 16 段：那 16 段全部围绕 ads/direct 两组
「纯域名 → 三平台等价」的产物族，而 AI 清单含 DOMAIN-KEYWORD 与 URL-REGEX，
是 classical 语义、只有 mihomo / Surge(Egern) 两端，且由另一组上游快照驱动。
硬并进去要改段号引用、段数声明、负样本计数与文档读数，收益为负。
本闸门独立挂在 regen.sh 末尾与 ci.yml，与 16 段互不干扰。

断言清单：
  1. ai_sources/ 快照与 MANIFEST.json 一致（复用 freeze_ai.py --check）
  2. surge-ai.list / mihomo-ai.yaml 存在且非空
  3. 两端逐条、有序、完全等价
  4. 两端头注条数声明 == 实际条数
  5. 零 IP 条目（AI 集纪律：纯域名集不触发解析，无 DNS 泄露面）
  6. 人工裁定仍在：googleapis.com 宽后缀不得出现；-pa 关键字兜底、googleusercontent
     宽后缀、play.googleapis.com 精确项必须在；GENERIC_INFRA_EXACT 里的通用基础
     设施主机不得回流（周更带回新域时最容易绕过裁定的一类）
  7. 规模护栏：单份上游快照 ≤ 5000 行、产物 100–1000 条 —— 上游突然改成整站
     dump 或返回错误页时，周更应当判负而不是把垃圾发布出去
  8. 可复现：临时目录重跑 build_ai.py + to_mihomo_ai.py，与仓内两份产物逐字比对

退出码：0 全过 / 1 有判负 / 2 环境不达标
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

for _s in ("stdout", "stderr"):
    _f = getattr(sys, _s, None)
    if _f is not None and hasattr(_f, "reconfigure"):
        try:
            _f.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

ROOT = Path(__file__).resolve().parents[2]
SURGE = ROOT / "surge-ai.list"
MIHOMO = ROOT / "mihomo-ai.yaml"
AI_DIR = ROOT / "ai_sources"

ok: list[str] = []
bad: list[str] = []

# ⚠️ 周更护栏的期望清单 —— **故意不从 build_ai.py 导入**。
#   2026-11-12 二次核查实测：原实现 `from build_ai import GENERIC_INFRA_EXACT`，
#   再用这个集合去检查产物里有没有回流 —— 典型的同构互保。把 build_ai.py 里的
#   常量删掉一条、重跑生成链让该主机回流后，判据拿同一个被删空的集合复核，
#   14 项断言照样全绿（假绿）。⇒ 判据必须独立持有一份期望值；改 build_ai.py
#   忘了同步这里会立刻判负，两处一起改则属明显的人为破坏（不在自动化防线内）。
#   与 build_ai.py 的 GENERIC_INFRA_EXACT 必须逐项一致，改任一处都要同步另一处。
GUARDED_HOSTS = {
    'fonts.googleapis.com', 'fonts.gstatic.com', 'ssl.gstatic.com',
    'maps.googleapis.com', 'maps.gstatic.com', 'play.google.com', 'ogs.google.com',
    'lh3.google.com', 'csp.withgoogle.com', 'content-autofill.googleapis.com',
    'jnn-pa.googleapis.com', 'optimizationguide-pa.googleapis.com',
    'streetviewpixels-pa.googleapis.com',
    'encrypted-tbn0.gstatic.com', 'encrypted-tbn1.gstatic.com',
    'encrypted-tbn2.gstatic.com', 'encrypted-tbn3.gstatic.com',
    'gspe1-ssl.ls.apple.com', 'apple-relay.cloudflare.com', 'apple-relay.fastly-edge.com',
    'cp4.cloudflare.com',
    'q.eu-central-1.amazonaws.com', 'q.us-east-1.amazonaws.com',
}
EXPECTED_GUARD_COUNT = 23


def judge(cond: bool, msg_ok: str, msg_bad: str) -> None:
    (ok if cond else bad).append(msg_ok if cond else msg_bad)


def rules_from_surge(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def rules_from_mihomo(path: Path) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s.startswith("- "):
            continue
        v = s[2:].strip()
        if len(v) >= 2 and v[0] == v[-1] == "'":
            v = v[1:-1].replace("''", "'")
        out.append(v)
    return out


def declared_count(path: Path, prefix: str) -> int | None:
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if s.startswith(prefix):
            tail = s[len(prefix):].strip()
            num = "".join(c for c in tail.split(" ")[0] if c.isdigit())
            return int(num) if num else None
    return None


def main() -> int:
    print("RFU-AI 清单闸门（离线）")
    print("-" * 72)

    if not SURGE.is_file() or not MIHOMO.is_file():
        print("❌ 产物缺失 —— 先跑 bash skill/scripts/regen.sh")
        return 2

    # 1. 上游快照未被手改
    r = subprocess.run([sys.executable, str(ROOT / "skill/scripts/freeze_ai.py"), "--check"],
                       capture_output=True, text=True, cwd=str(ROOT))
    judge(r.returncode == 0, "AI 上游快照与 MANIFEST.json 一致",
          "AI 上游快照校验失败：%s" % (r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr.strip()[:120]))

    # 2. 产物存在
    judge(SURGE.stat().st_size > 0 and MIHOMO.stat().st_size > 0,
          "两份 AI 产物存在且非空", "AI 产物为空文件")

    a, b = rules_from_surge(SURGE), rules_from_mihomo(MIHOMO)

    # 3. 逐条有序等价
    judge(a == b and bool(a),
          "surge-ai.list ↔ mihomo-ai.yaml 逐条有序等价（%d 条）" % len(a),
          "两端条目不一致（surge %d / mihomo %d）" % (len(a), len(b)))

    # 4. 条数自述
    c1 = declared_count(SURGE, "# 合计:")
    c2 = declared_count(MIHOMO, "# 条数：")
    judge(c1 == len(a), "surge-ai.list 头注条数 %s == 实际 %d" % (c1, len(a)),
          "surge-ai.list 头注条数 %s ≠ 实际 %d" % (c1, len(a)))
    judge(c2 == len(b), "mihomo-ai.yaml 头注条数 %s == 实际 %d" % (c2, len(b)),
          "mihomo-ai.yaml 头注条数 %s ≠ 实际 %d" % (c2, len(b)))

    # 5. 零 IP
    ip = [x for x in a if x.split(",")[0].upper() in ("IP-CIDR", "IP-CIDR6", "IP-ASN")]
    judge(not ip, "零 IP 条目", "出现 %d 条 IP 规则：%s" % (len(ip), ip[:3]))

    # 6. 人工裁定守卫
    judge("DOMAIN-SUFFIX,googleapis.com" not in a,
          "googleapis.com 宽后缀未回流（YouTube 误伤防护）",
          "googleapis.com 宽后缀回流 —— 人工裁定被上游冲掉了")
    for needle, why in (("DOMAIN-KEYWORD,-pa.googleapis.com", "-pa 动态命名空间兜底"),
                        ("DOMAIN-SUFFIX,googleusercontent.com", "静态 CDN 宽后缀（用户拍板保留）"),
                        ("DOMAIN,play.googleapis.com", "GMS 主网关精确项")):
        judge(needle in a, "%s 仍在" % why, "%s 丢失（%s）" % (why, needle))

    # 6b. 周更护栏：通用基础设施域不得回流（期望清单由本判据独立持有）
    judge(len(GUARDED_HOSTS) == EXPECTED_GUARD_COUNT,
          "周更护栏清单完整（%d 项）" % len(GUARDED_HOSTS),
          "周更护栏清单被删减：%d 项，应为 %d 项" % (len(GUARDED_HOSTS), EXPECTED_GUARD_COUNT))
    leaked = [x for x in a if x.split(",", 1)[-1] in GUARDED_HOSTS]
    judge(not leaked,
          "周更护栏：%d 个通用基础设施主机未回流" % len(GUARDED_HOSTS),
          "通用基础设施域回流（人工裁定被上游冲掉）：%s" % leaked[:5])

    # 7. 规模护栏
    big = [(p.name, len(p.read_text(encoding="utf-8").splitlines()))
           for p in sorted(AI_DIR.glob("*.list"))]
    over = [x for x in big if x[1] > 5000]
    judge(not over, "10 份上游快照行数均在护栏内（最大 %d）" % max((n for _, n in big), default=0),
          "上游快照异常膨胀：%s" % over[:3])
    judge(100 <= len(a) <= 1000, "产物条数 %d 在 100–1000 护栏内" % len(a),
          "产物条数 %d 越界 —— 上游可能返回了错误页或整站 dump" % len(a))

    # 8. 可复现（临时目录重跑整条生成链）
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        s2, m2 = tmp / "surge-ai.list", tmp / "mihomo-ai.yaml"
        r1 = subprocess.run([sys.executable, str(ROOT / "skill/scripts/build_ai.py"),
                             "--src-dir", str(AI_DIR), "--out", str(s2)],
                            capture_output=True, text=True, cwd=str(ROOT))
        r2 = subprocess.run([sys.executable, str(ROOT / "skill/scripts/to_mihomo_ai.py"),
                             "--src", str(s2), "--out", str(m2)],
                            capture_output=True, text=True, cwd=str(ROOT))
        same = (r1.returncode == 0 and r2.returncode == 0 and s2.is_file() and m2.is_file()
                and rules_from_surge(s2) == a and m2.read_text(encoding="utf-8") == MIHOMO.read_text(encoding="utf-8"))
        judge(same, "从 ai_sources/ 重跑生成链与仓内产物逐字一致",
              "产物不可复现（build_ai exit=%d / to_mihomo exit=%d）%s"
              % (r1.returncode, r2.returncode, (r1.stdout + r1.stderr + r2.stdout + r2.stderr)[-200:]))

    for m in ok:
        print("  ✅", m)
    for m in bad:
        print("  ❌", m)
    print("-" * 72)
    print("TOTAL: %d passed, %d failed" % (len(ok), len(bad)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
