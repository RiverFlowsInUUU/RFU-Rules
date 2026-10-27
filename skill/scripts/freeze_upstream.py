#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把全部上游源冻结到 upstream/ —— 构建完全离线的固定输入。

为什么要有这个脚本
==================
构建要可复现，输入就必须钉死：全部上游源落盘 `upstream/`，带 sha256 与取用
日期；构建只读 `upstream/`，不联网。要更新就显式跑本脚本，让 diff 里看得见
「这次换了什么」。

源策略分两档（2026-10-27 起）：
  · jinx：钉死。上游自 3.2.4 转为加密发布（new-rules/*.enc，需接收方私钥），
    明文 rules/ 停在 3.2.3 —— 用 JINX_COMMIT 钉住，任何情况下不动。
  · 其余五个中文源：活源。由每周定时工作流
    （.github/workflows/update.yml）刷新，也可手动跑；任一源抓取失败
    即不落盘 manifest、退出非零，仓内不会出现半新半旧的快照。

用法
====
    python skill/scripts/freeze_upstream.py            # 抓取并落盘（会改 upstream/）
    python skill/scripts/freeze_upstream.py --check    # 只校验：仓内快照与 manifest 是否一致
    python skill/scripts/freeze_upstream.py --list     # 列出源清单，不联网

`--check` 的用途：CI 与 verify 用它确认「快照没被人手改过」。手动编辑 upstream/
下的文件会让 --check 判负 —— 那正是本仓要防的「静默失真」。

退出码沿用全仓四态：0 过 / 1 判负 / 2 环境不达标 / 3 SKIP
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

for _s in ("stdout", "stderr"):
    _f = getattr(sys, _s, None)
    if _f is not None and hasattr(_f, "reconfigure"):
        try:
            _f.reconfigure(encoding="utf-8", errors="replace")
        except (ValueError, OSError):
            pass

EXIT_PASS, EXIT_FAIL, EXIT_ENV, EXIT_SKIP = 0, 1, 2, 3
UA = "Mozilla/5.0 (compatible; rfu-rules-freeze/1.0)"
ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = ROOT / "upstream"

# Jinx 明文通道的最后一个版本。钉死 commit，不用 master ——
# master 上 rules/ 与 new-rules/ 并存，用 commit 才能保证「取到的就是 3.2.3」。
JINX_COMMIT = "c85751d"
JINX_RAW = "https://raw.githubusercontent.com/VME98/jinx-rules/%s/rules/" % JINX_COMMIT

_ADB = "https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/"

# (分组, 目标相对路径, URL, 说明)
SOURCES = [
    # ── Jinx 3.2.3 明文（本仓的基线支路 C）──────────────────────────
    ("jinx-3.2.3", "blacklist.txt", JINX_RAW + "blacklist.txt", "上游黑名单（后缀语义）"),
    ("jinx-3.2.3", "blacklist_wildcard.txt", JINX_RAW + "blacklist_wildcard.txt", "上游黑名单通配"),
    ("jinx-3.2.3", "whitelist.txt", JINX_RAW + "whitelist.txt", "上游白名单（精确语义）"),
    ("jinx-3.2.3", "whitelist_wildcard.txt", JINX_RAW + "whitelist_wildcard.txt", "上游白名单通配"),
    ("jinx-3.2.3", "version.json", JINX_RAW + "version.json", "上游版本自述"),
    # ── 217heidai：支路 A 的来源与其筛选器 ──────────────────────────
    ("217heidai", "adblocksurgelite.list", _ADB + "adblocksurgelite.list",
     "16 源聚合后 ∩ china.txt 的 lite 档（DOMAIN-SET 格式）"),
    ("217heidai", "china.txt", _ADB + "china.txt", "中国域名清单（判定「中国生态」的基准）"),
    # ── 中文广告源：支路 B ─────────────────────────────────────────
    ("cn", "AdGuard_Chinese_filter.txt", _ADB + "AdGuard_Chinese_filter.txt", "AdGuard 官方中文过滤器"),
    ("cn", "AWAvenue_Ads_Rule.txt", _ADB + "AWAvenue_Ads_Rule.txt", "秋风广告规则"),
    ("cn", "jiekouAD.txt", _ADB + "jiekouAD.txt", "接口广告源（灰产长尾多，靠准入规则滤）"),
    ("cn", "CJX_Annoyance_List.txt", _ADB + "CJX's_Annoyance_List.txt", "CJX 中文骚扰+广告"),
    ("cn", "xinggsf_mv.txt", _ADB + "xinggsf_mv.txt", "xinggsf（优酷等）"),
    # 「独立第二覆盖率基线」方案（v11 审查 3.1，AdGuard DNS filter）经实测否决：
    # 该列表是国际通用向，与 CN 向产物仅 3.1% 交集、CN 子集仅 17 条，无统计力。
    # 改用 build_ads 的「B 支路采纳率带宽 + 单源哨兵」直接守准入判据本身。
]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def http_get(url: str, attempts: int = 3) -> str:
    """带指数退避重试的 GET（v11 审查 3.3）：网络抖动不再单发即挂周更。

    attempts=3，间隔 2s / 4s；全部失败抛最后一个异常，由调用方按源粒度
    记入 failed（任一源失败 ⇒ 不落盘 manifest ⇒ 工作流失败 ⇒ 不提交）。
    """
    last: Exception = RuntimeError("unreachable")
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:                                   # noqa: BLE001
            last = e
            if i < attempts - 1:
                time.sleep(2 ** (i + 1))
    raise last


def read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def write_text(p: Path, text: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    # newline='' 钉死 LF：Windows 的通用换行会把 \n 写成 \r\n，
    # 产物跨平台就不可复现了（SKILL.md「踩坑记录」第一条）。
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def manifest_path() -> Path:
    return UPSTREAM / "manifest.json"


def build_manifest(rows: list[dict]) -> dict:
    return {
        "frozen_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "policy": "上游快照落盘，构建只读 upstream/，不联网。jinx 钉死 3.2.3，"
                  "其余源每周由定时工作流刷新。要更新跑 "
                  "skill/scripts/freeze_upstream.py。",
        "hash_basis": "bytes 与 sha256 均按换行归一化（LF）后的文本计算，"
                      "与仓库内 .gitattributes 的 eol=lf 一致。",
        "jinx_commit": JINX_COMMIT,
        "sources": rows,
    }


def cmd_list() -> int:
    print("%-12s %-34s %s" % ("分组", "目标路径", "URL"))
    print("-" * 118)
    for group, rel, url, note in SOURCES:
        print("%-12s %-34s %s" % (group, group + "/" + rel, url))
    print("\n共 %d 个源文件，分 %d 组。" % (len(SOURCES), len({s[0] for s in SOURCES})))
    return EXIT_PASS


def cmd_freeze() -> int:
    rows, failed = [], []
    for group, rel, url, note in SOURCES:
        dest = UPSTREAM / group / rel
        try:
            text = http_get(url)
        except Exception as e:                                   # noqa: BLE001
            failed.append((group + "/" + rel, str(e)[:80]))
            continue
        lines = [l for l in text.splitlines() if l.strip() and not l.startswith("#")]
        write_text(dest, text)
        # ⚠️ 体积与 sha 必须同基准：一律按「换行归一化后的文本」计。
        #    曾用 stat().st_size（原始字节）记体积、却用 read_text()（归一化）算 sha ——
        #    AdGuard_Chinese_filter 原始是 CRLF（754584 字节），仓库里经
        #    .gitattributes 的 eol=lf 归一化后是 732689 字节，清单那一栏于是对谁都对不上
        #    （校验本身不受影响，因为两边都按归一化文本算）。
        norm = read_text(dest)
        rows.append({
            "group": group,
            "path": group + "/" + rel,
            "url": url,
            "sha256": sha256_text(norm),
            "bytes": len(norm.encode("utf-8")),
            "lines": len(lines),
            "note": note,
        })
        print("  ✅ %-46s %8d 字节  %6d 行"
              % (group + "/" + rel, len(norm.encode("utf-8")), len(lines)))

    if failed:
        print("\n❌ 以下源抓取失败，未落盘：")
        for n, e in failed:
            print("   %-46s %s" % (n, e))
        return EXIT_FAIL

    mf = build_manifest(rows)
    write_text(manifest_path(), json.dumps(mf, ensure_ascii=False, indent=2) + "\n")
    write_text(UPSTREAM / "MANIFEST.md", render_manifest_md(mf))
    print("\n冻结完成：%d 个文件 → upstream/（manifest.json + MANIFEST.md 已更新）" % len(rows))
    print("⚠️ upstream/ 下的文件是构建输入，勿手改；要换源请改本脚本的 SOURCES 再跑一次。")
    return EXIT_PASS


def render_manifest_md(mf: dict) -> str:
    out = [
        "# 📌 上游快照清单",
        "",
        "> [!IMPORTANT]",
        "> 本目录是**构建输入**，不是产物。**不要手改这里的任何文件** ——",
        "> 手改会破坏「产物 == 源头重跑」的可复现断言（`verify_products.py` 会判负）。",
        "> 要更新上游，跑 `python skill/scripts/freeze_upstream.py`，让改动留在 git diff 里可审计。",
        "",
        "## 源策略",
        "",
        "jinx 上游自 `3.2.4` 起改为加密发布（`new-rules/*.enc`，需接收方 P-256 私钥），",
        "明文 `rules/` 停在 `3.2.3` —— 用 commit 钉住，任何情况下不动；",
        "其余中文源为活源，由每周定时工作流（`.github/workflows/update.yml`）刷新，",
        "任一源抓取失败即不落盘、不提交，仓内不出现半新半旧的快照。",
        "",
        "构建只读本目录、**不联网**。",
        "",
        "## 快照信息",
        "",
        "| 项 | 值 |",
        "|---|---|",
        "| 取用时间（UTC） | `%s` |" % mf["frozen_at"],
        "| Jinx 明文通道锚点 | `VME98/jinx-rules@%s`（对应版本见 `jinx-3.2.3/version.json`） |" % mf["jinx_commit"],
        "| 源文件数 | %d |" % len(mf["sources"]),
        "",
        "## 文件明细",
        "",
        "| 分组 | 文件 | 字节（LF 归一化） | 非注释行 | sha256 前 12 位 | 用途 |",
        "|---|---|---|---|---|---|",
    ]
    for s in mf["sources"]:
        out.append("| %s | `%s` | %d | %d | `%s` | %s |"
                   % (s["group"], s["path"].split("/", 1)[1], s["bytes"], s["lines"],
                      s["sha256"][:12], s["note"]))
    out += [
        "",
        "## 取用方式",
        "",
        "构建产物（不联网，只读本目录）：",
        "",
        "```bash",
        "bash skill/scripts/regen.sh           # 一条命令：快照校验 → direct → ads → 六份产物 → 双闸门",
        "bash skill/scripts/regen.sh --build   # 只重建，不跑闸门",
        "```",
        "",
        "更新上游（唯一允许联网的入口）：",
        "",
        "```bash",
        "python skill/scripts/freeze_upstream.py --check   # 先确认当前快照未被手改",
        "python skill/scripts/freeze_upstream.py           # 抓取新版并更新本清单",
        "```",
        "",
        "## 来源与许可",
        "",
    ]
    for group in sorted({s["group"] for s in mf["sources"]}):
        urls = sorted({s["url"].rsplit("/", 1)[0] for s in mf["sources"] if s["group"] == group})
        out.append("- **%s**：%s" % (group, "、".join("<%s>" % u for u in urls)))
    out += [
        "",
        "上游均未声明开源许可。本仓只做格式转换与合并，不主张对规则数据的任何权利；",
        "任一上游作者提出异议即删除相关来源。",
        "",
    ]
    return "\n".join(out)


def cmd_check() -> int:
    mp = manifest_path()
    if not mp.exists():
        print("❌ 缺 upstream/manifest.json —— 先跑 python skill/scripts/freeze_upstream.py")
        return EXIT_ENV
    mf = json.loads(read_text(mp))
    bad, missing = [], []
    for s in mf["sources"]:
        p = UPSTREAM / s["path"]
        if not p.exists():
            missing.append(s["path"])
            continue
        got = sha256_text(read_text(p))
        if got != s["sha256"]:
            bad.append((s["path"], s["sha256"][:12], got[:12]))
    print("── upstream 快照校验 ─────────────────────────────────────")
    if missing:
        print("  ❌ 缺失 %d 个文件：%s" % (len(missing), missing[:3]))
    if bad:
        print("  ❌ %d 个文件被改动（sha256 不符）：" % len(bad))
        for path, want, got in bad:
            print("       %-46s 期望 %s，实际 %s" % (path, want, got))
        print("     → 若是有意更新上游，重跑 freeze_upstream.py 更新 manifest；")
        print("       若是手滑，git checkout -- upstream/ 还原。")
    if not missing and not bad:
        print("  ✅ %d 个文件全部与 manifest 一致（快照未被手改）" % len(mf["sources"]))
        return EXIT_PASS
    return EXIT_FAIL


def main() -> int:
    ap = argparse.ArgumentParser(description="冻结上游源到 upstream/")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="只校验快照与 manifest 是否一致")
    g.add_argument("--list", action="store_true", help="列出源清单（不联网）")
    args = ap.parse_args()

    if args.list:
        return cmd_list()
    if not UPSTREAM.parent.exists():
        print("❌ 仓根定位异常：%s" % UPSTREAM.parent, file=sys.stderr)
        return EXIT_ENV
    return cmd_check() if args.check else cmd_freeze()


if __name__ == "__main__":
    sys.exit(main())
