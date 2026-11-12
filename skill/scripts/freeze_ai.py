#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""冻结 AI 清单的 10 个上游源到 ai_sources/（周更唯一联网入口）。

与 freeze_upstream.py 的分工：那边管广告/放行的 12 份快照与 upstream/manifest.json；
本脚本只管 AI 这一组的 ai_sources/ 与 ai_sources/MANIFEST.json，互不干扰
（freeze_upstream.py --check 只按自己 manifest 的 sources 列表校验，不扫全目录）。

纪律（与仓内一致）：
  · 任一源抓取失败 ⇒ 整体失败、一个字节都不落盘 ⇒ update.yml 失败 ⇒ 不提交半新半旧；
  · 4xx 不重试（404 是永久错），其余指数退避 3 次；
  · 内容未变的源沿用上次取用时间 ⇒ 上游零变化的那一周 manifest 字节不变、不空转；
  · --check 离线校验：快照与 manifest 逐个 sha256 对账，且不许有未登记的 .list。
  10 个源均已于 2026-11-12 实测 200；ACL4SSR 是停更基线（内容长期不变，仍按周探活）。

用法：
    python skill/scripts/freeze_ai.py            # 抓取并更新快照 + MANIFEST.json
    python skill/scripts/freeze_ai.py --check    # 离线校验（CI 用）
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

for _s in ("stdout", "stderr"):
    _f = getattr(sys, _s, None)
    if _f is not None and hasattr(_f, "reconfigure"):
        try:
            _f.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

ROOT = Path(__file__).resolve().parents[2]
AI_DIR = ROOT / "ai_sources"
MANIFEST = AI_DIR / "MANIFEST.json"
UA = "Mozilla/5.0 (compatible; rfu-rules-freeze-ai/1.0)"

BM7 = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/"
SOURCES = [
    ("repcz-ai.list", "https://raw.githubusercontent.com/Repcz/Tool/X/Surge/Rules/AI.list",
     "Repcz/Tool · 主参考集（滚动）"),
    ("my-ai.list", "https://ddgksf2013.top/filter/Ai.yaml",
     "ddgksf2013.top 墨鱼 Ai.yaml · 伴生域基线"),
    ("acl4ssr-ai.list", "https://raw.githubusercontent.com/ACL4SSR/ACL4SSR/master/Clash/Ruleset/AI.list",
     "ACL4SSR · 停更基线（长期无增量）"),
    ("bm7-OpenAI.list", BM7 + "OpenAI/OpenAI.list", "blackmatrix7 OpenAI"),
    ("bm7-Gemini.list", BM7 + "Gemini/Gemini.list", "blackmatrix7 Gemini"),
    ("bm7-Claude.list", BM7 + "Claude/Claude.list", "blackmatrix7 Claude"),
    ("bm7-Copilot.list", BM7 + "Copilot/Copilot.list", "blackmatrix7 Copilot"),
    ("bm7-BardAI.list", BM7 + "BardAI/BardAI.list", "blackmatrix7 BardAI"),
    ("meta-ai.list", "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/category-ai-!cn.list",
     "MetaCubeX geosite category-ai-!cn · 最大覆盖源"),
    ("dler-ai.list", "https://raw.githubusercontent.com/dler-io/Rules/main/Surge/Surge%203/Provider/AI%20Suite.list",
     "dler-io/Rules AI Suite · 高质量补漏"),
]


def norm(text: str) -> str:
    """与 freeze_upstream.py 同口径：换行归一化为 LF 后再算 hash / 字节 / 行。"""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def digest(text: str) -> str:
    return hashlib.sha256(norm(text).encode("utf-8")).hexdigest()


def http_get(url: str, attempts: int = 3) -> str:
    last: Exception = RuntimeError("unreachable")
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            last = e
            if 400 <= e.code < 500 and e.code != 429:
                raise
            if i < attempts - 1:
                time.sleep(2 ** (i + 1))
        except Exception as e:  # noqa: BLE001
            last = e
            if i < attempts - 1:
                time.sleep(2 ** (i + 1))
    raise last


def load_manifest() -> dict | None:
    if not MANIFEST.is_file():
        return None
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def cmd_check() -> int:
    mf = load_manifest()
    if mf is None:
        print("❌ 缺 ai_sources/MANIFEST.json —— 先跑 python skill/scripts/freeze_ai.py")
        return 2
    bad = []
    seen = set()
    for s in mf["sources"]:
        p = AI_DIR / s["path"]
        seen.add(s["path"])
        if not p.is_file():
            bad.append("缺文件 %s" % s["path"])
            continue
        t = norm(p.read_text(encoding="utf-8"))
        if digest(t) != s["sha256"]:
            bad.append("sha256 不符（疑似手改）%s" % s["path"])
        if len(t.encode("utf-8")) != s["bytes"]:
            bad.append("字节数不符 %s" % s["path"])
    for p in sorted(AI_DIR.glob("*.list")):
        if p.name not in seen:
            bad.append("未登记的快照 %s —— 手塞源文件同样判负" % p.name)
    if bad:
        print("❌ AI 上游快照校验失败：")
        for b in bad:
            print("   ·", b)
        return 1
    print("✅ %d 份 AI 上游快照与 MANIFEST.json 一致（frozen_at=%s）"
          % (len(mf["sources"]), mf.get("frozen_at", "?")))
    return 0


def cmd_fetch() -> int:
    if not AI_DIR.is_dir():
        print("❌ 缺 ai_sources/ 目录")
        return 2
    old = {s["path"]: s for s in (load_manifest() or {}).get("sources", [])}
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    fetched: dict[str, str] = {}
    failed = []

    for name, url, note in SOURCES:
        try:
            text = norm(http_get(url))
            if not text.strip():
                raise RuntimeError("空响应")
            fetched[name] = text
            print("  ✅ %-22s %6d B / %5d 行  %s" % (name, len(text.encode("utf-8")),
                                                     len(text.splitlines()), note))
        except Exception as e:  # noqa: BLE001
            failed.append((name, url, str(e)[:120]))
            print("  ❌ %-22s %s" % (name, str(e)[:120]))

    if failed:
        print("\n❌ %d 个源抓取失败 —— 一个字节都不落盘，快照保持上次成功状态。" % len(failed))
        for n, u, e in failed:
            print("   · %s  %s  (%s)" % (n, u, e))
        return 1

    entries, changed = [], 0
    for name, url, note in SOURCES:
        text = fetched[name]
        d = digest(text)
        prev = old.get(name, {})
        if prev.get("sha256") == d:
            when = prev.get("fetched_at", now)   # 零变化沿用旧取用时间，不空转
        else:
            when = now
            changed += 1
        entries.append({
            "path": name, "url": url, "note": note, "sha256": d,
            "bytes": len(text.encode("utf-8")), "lines": len(text.splitlines()),
            "fetched_at": when,
        })

    # 全部成功才落盘
    for name, _, _ in SOURCES:
        (AI_DIR / name).write_text(fetched[name], encoding="utf-8", newline="\n")
    frozen_at = max(e["fetched_at"] for e in entries)
    mf = {
        "frozen_at": frozen_at,
        "policy": "AI 清单的 10 份上游快照；由 update.yml 每周刷新，build_ai.py 只读本目录离线归并。"
                  "人工裁定（googleapis 收窄 / -pa 关键字 / 黑名单主机）在 build_ai.py 常量里，"
                  "刷新上游不会冲掉它们。要手改数据请改 build_ai.py 后重跑 regen.sh。",
        "sources": entries,
    }
    MANIFEST.write_text(json.dumps(mf, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8", newline="\n")
    print("\n落盘 %d 份快照（%d 份内容有变化），frozen_at=%s" % (len(entries), changed, frozen_at))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="冻结 AI 上游源到 ai_sources/")
    ap.add_argument("--check", action="store_true", help="离线校验快照与 manifest")
    a = ap.parse_args()
    return cmd_check() if a.check else cmd_fetch()


if __name__ == "__main__":
    sys.exit(main())
