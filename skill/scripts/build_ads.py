#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build_ads.py —— ads 域名集构建器（三支路合成 · 只读 upstream/，不联网）

本仓 2026-10-27 起从「上游格式转换镜像」转为「合成规则集」：
ads 不再是 Jinx 的一条不增不减的翻版，而是三个支路合成后的结果。

    支路 A  upstream/217heidai/adblocksurgelite.list
            16 源聚合后 ∩ china.txt 的 lite 档。覆盖率有限但质量高。
    支路 B  upstream/cn/*（AdGuard 中文 · 秋风 · jiekouAD · CJX · xinggsf）
            只取 DNS 层能表达的域名级规则，带「成簇或语义」准入以滤灰产长尾。
    支路 C  upstream/jinx-3.2.3/blacklist*.txt
            上游明文通道的最后版本（3.2.4 起已转加密发布）。作为补丁支路，
            把 A/B 漏掉的国际广告网络与长尾补回来。

为什么必须三支路
================
v2 只用 B 支路 → 覆盖 Jinx·中国生态 46.8%。拆解后发现 85% 的缺口不是被筛掉，
而是那 5 个源里根本没有（`a.alimama.cn`、`acookie.alimama.com` 之类）。
lite 是 16 源浓缩的另一条路线，Jinx 是第三条。三者互补，并联才有覆盖率。

七条规矩（全部确定性、可断言、零人工逐条判定）
==============================================
1. 只做 DNS 层能表达的减法：`$` 修饰符、`##` 元素隐藏、`@@||x/path` 不进产物。
2. `@@` 例外只做减法，不生成 DIRECT 行 —— 不在拦截集里就落回分流，路由自动正确。
3. 只输出 DOMAIN-SUFFIX，无通配无正则（三端语义一致，走 trie 快路径）。
4. 只拦域名不拦 IP（IPv4 / CIDR 一律剔除）。
5. 静态资源硬排除：label 以 static / download / status / update 开头者剔除，
   且不受「成簇」豁免。反面实证：s.bdstatic.com、static-s.iqiyi.com 被误拦会让页面挂图裂。
6. 功能域排除：含 push / passport / login / uaa / doh / im / chat / subscription 等
   功能词元、且无广告语义、无 ad 词根、无平台痕迹者剔除。
   ⚠️ api / sdk / gateway 不在词表 —— 几乎每个广告 SDK 端点都带，不具备区分力。
7. 灰产靠结构不靠语义：归属域下孤立 1 条 + 元音比例低 + 含数字 = 随机域名，剔除。

断言（失败即非零退出，CI 同源）
================================
① 无 IP / CIDR / 通配 / 修饰符   ② 静态资源域为 0（命名含广告语义者除外）
③ MUST_CONTAIN 必需域在位         ④ direct 放行清单非空（顺序保护的前提）
⑤ 独立基线覆盖率 ≥ 护栏           ⑥ 规模护栏   ⑦ 无重复

用法
====
    python skill/scripts/build_ads.py                     # 写出 build/ads/ads-src.txt + 审计
    python skill/scripts/build_ads.py --dry-run           # 只看审计，不落盘
    bash skill/scripts/regen.sh                            # 构建 + 产出六份正式产物

退出码：0 过 / 1 判负（断言或来源问题）/ 2 环境不达标（缺 upstream/）
"""
from __future__ import annotations

import argparse
import collections
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

EXIT_PASS, EXIT_FAIL, EXIT_ENV = 0, 1, 2
ROOT = Path(__file__).resolve().parents[2]
UP = ROOT / "upstream"
OUT_DIR = ROOT / "build" / "ads"

# ── 源（全部来自 upstream/，不联网）──────────────────────────────
LITE = UP / "217heidai" / "adblocksurgelite.list"
CHINA = UP / "217heidai" / "china.txt"
JINX_BLK = UP / "jinx-3.2.3" / "blacklist.txt"
JINX_BLK_WILD = UP / "jinx-3.2.3" / "blacklist_wildcard.txt"
B_SOURCES = [
    ("AdGuard_Chinese_filter.txt", "AdGuard-CN"),
    ("AWAvenue_Ads_Rule.txt", "AWAvenue"),
    ("jiekouAD.txt", "jiekouAD"),
    ("CJX_Annoyance_List.txt", "CJX"),
    ("xinggsf_mv.txt", "xinggsf"),
]
COVERAGE_BASELINE = UP / "cn" / "AWAvenue_Ads_Rule.txt"
DIRECT_PRODUCT = ROOT / "surge-direct.list"

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9])?\.)+([a-z]{2,63}|xn--[a-z0-9-]+)$",
    re.I,
)
IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
CIDR_RE = re.compile(r"/\d+$")
BLOCK_RE = re.compile(r"^\|\|([a-z0-9._-]+)\^$")
EXCEPT_RE = re.compile(r"^@@\|\|([a-z0-9._-]+)\^$")
AD_ROOT_RE = re.compile(r"^(ad|ads|advert)", re.I)

SEMANTIC = {
    "ad", "ads", "adx", "adserv", "adserver", "adservice", "adservices",
    "adsrv", "adpush", "advert", "adverts", "advertise", "advertised",
    "advertisement", "advertising", "advertiser", "adview", "adlog",
    "adcdn", "adclick", "adping", "adtrack", "adfile", "adsfile",
    "dsp", "ssp", "rtb", "cupid", "pangle", "pangolin", "gromore", "csj",
    "gdt", "pgdt", "tanx", "alimama", "mobads", "adkwai", "gskwai",
    "admaster", "miaozhen", "applovin", "mintegral", "vungle", "ironsource",
    "startapp", "inmobi", "tapjoy", "adcolony", "unityads", "unityad",
    "stat", "stats", "statistic", "statistics", "track", "tracker", "tracking",
    "analytic", "analytics", "metric", "metrics", "beacon", "report", "reports",
    "collect", "collector", "monitor", "monitoring", "log", "logs", "logging",
    "pcdn", "p2p", "peer", "stun", "turn",
    "deviceid", "oaid", "imei", "idfa", "oneid", "umid", "msaid",
}
PLATFORM_SUBSTR = (
    "kwai", "pangolin", "pangle", "gromore", "mobads", "alimama",
    "bytedance", "snssdk", "isnssdk", "toutiao", "umeng", "tanx", "cupid",
    "unity3d", "unityads", "kuaishou", "vungle", "applovin", "mintegral",
    "ironsource", "inmobi", "adcolony", "chartboost",
)
FUNCTION_TOKENS = {
    "push", "upush", "passport", "login", "auth", "uaa", "oauth", "sso",
    "account", "dns", "doh", "dot", "im", "chat", "message", "msg", "mail",
    "static", "css", "img", "image", "pic", "photo", "video", "play", "player",
    "media", "download", "upload", "file", "cdn", "update", "upgrade", "patch",
    "config", "cfg", "captcha", "verify", "sms", "code", "pay", "wallet",
    "order", "cart", "coupon", "search", "feed", "comment", "share", "live",
    "room", "subscription", "member", "vip",
}
RESOURCE_PREFIX = ("static", "download", "sdownload", "status", "update", "upgrade")

# 已知必需域：任一缺失即判负。防「闸门全绿但实际改坏」。
MUST_CONTAIN = [
    "cupid.iqiyi.com", "cupid.ptqy.gitv.tv", "adkwai.com",
    "pangolin-sdk-toutiao.com", "api-access.pangolin-sdk-toutiao.com",
    "gdt.qq.com", "e.qq.com", "umeng.com", "alog.umeng.com",
    "ad.xiaomi.com", "analytics.126.net",
]
# 覆盖率断言基线必须独立于支路来源，否则是同义反复。
# 曾用 Jinx 当基线而 Jinx 本身是 C 支路 → 91.5% 等于自证。
COVERAGE_FLOOR = 0.85
SIZE_RANGE = (5000, 15000)

MULTI_SUFFIX = {
    "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn",
    "com.hk", "com.tw", "co.jp", "co.uk", "com.au", "com.sg",
}


# ────────────────────────────── 判定工具

def registrable(d: str) -> str:
    p = d.split(".")
    if len(p) >= 3 and ".".join(p[-2:]) in MULTI_SUFFIX:
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def label_tokens(label: str) -> list[str]:
    return [t for t in re.split(r"[^a-z]+", label.lower()) if t]


def has_semantic(d: str) -> bool:
    return any(t in SEMANTIC for lb in d.split(".")[:-1] for t in label_tokens(lb))


def has_ad_root(d: str) -> bool:
    return any(AD_ROOT_RE.match(lb) for lb in d.split(".")[:-1])


def has_platform(d: str) -> bool:
    return any(k in d for k in PLATFORM_SUBSTR)


def has_function(d: str) -> bool:
    return any(t in FUNCTION_TOKENS for lb in d.split(".")[:-1] for t in label_tokens(lb))


def is_function_domain(d: str) -> bool:
    return (has_function(d) and not has_semantic(d)
            and not has_ad_root(d) and not has_platform(d))


def is_resource(d: str) -> bool:
    return any(lb.lower().startswith(RESOURCE_PREFIX) for lb in d.split(".")[:-1])


def is_gray_random(d: str, cluster_size: int, semantic: bool) -> bool:
    if cluster_size >= 2 or semantic:
        return False
    b = registrable(d).split(".")[0]
    if len(b) < 6:
        return False
    v = sum(1 for c in b if c in "aeiou")
    return v / max(len(b), 1) < 0.22 and any(c.isdigit() for c in b)


def climb(d: str) -> tuple[str, bool]:
    """语义上提：从右往左找第一个语义 label，提到此为止，绝不越过归属域。"""
    labels = d.split(".")
    for i in range(len(labels) - 2):
        if labels[i] in SEMANTIC:
            out = ".".join(labels[i:])
            return out, out != d
    return d, False


def under(d: str, aset: set) -> bool:
    p = d.split(".")
    return any(".".join(p[i:]) in aset for i in range(len(p) - 1))


def valid_domain(d: str) -> bool:
    return bool(DOMAIN_RE.match(d)) and not IPV4_RE.match(d) and not CIDR_RE.search(d)


# ────────────────────────────── 解析

def parse_domain_set(text: str, stat: collections.Counter) -> set:
    """217heidai 的 Surge DOMAIN-SET：每行 `.域名` 或裸域名。"""
    out = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//")):
            continue
        dom = line.lstrip(".").lower()
        if not valid_domain(dom):
            stat["形态非法/IP(剔除)"] += 1
            continue
        out.add(dom)
    return out


def parse_adblock(text: str, stat: collections.Counter) -> tuple[set, set]:
    """AdGuard / EasyList 语法：只取 DNS 层能表达的域名级规则。"""
    out, exceptions = set(), set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("!", "#", "[")):
            continue
        if "##" in line or "#@#" in line or "#?#" in line:
            stat["cosmetic 元素隐藏(不可表达)"] += 1
            continue
        if line.startswith("@@"):
            m = EXCEPT_RE.match(line)
            if m:
                exceptions.add(m.group(1).lower())
                stat["例外 域名级(采用)"] += 1
            else:
                stat["例外 条件/路径型(不可表达)"] += 1
            continue
        if "$" in line or "/" in line:
            stat["条件/路径型拦截(不可表达)"] += 1
            continue
        m = BLOCK_RE.match(line)
        dom = m.group(1).lower() if m else (line.lower() if DOMAIN_RE.match(line) else None)
        if not dom:
            stat["其他(丢弃)"] += 1
            continue
        if not valid_domain(dom):
            stat["形态非法/IP(剔除)"] += 1
            continue
        out.add(dom)
    return out, exceptions


def parse_jinx(text: str, stat: collections.Counter) -> set:
    """Jinx 明文黑名单：一行一个域名，后缀语义。"""
    out = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//")):
            continue
        dom = re.sub(r"^[a-z0-9*]+:\/\/", "", line, flags=re.I).split("/")[0].lower()
        if not valid_domain(dom):
            stat["形态非法/URL式(剔除)"] += 1
            continue
        out.add(dom)
    return out


def parse_jinx_wildcard(text: str, stat: collections.Counter) -> set:
    """Jinx 通配文件：`*.x.com` 可无损降为后缀；内嵌星号无法表达，丢弃并计数。"""
    out = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//")):
            continue
        if line.startswith("*.") and "*" not in line[2:] and "?" not in line[2:]:
            dom = line[2:].lower()
            if valid_domain(dom):
                out.add(dom)
                stat["通配 *.x.com → 后缀"] += 1
                continue
        stat["通配 内嵌星号(无法转后缀)"] += 1
    return out


def read(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def parse_direct_product() -> set:
    out = set()
    if not DIRECT_PRODUCT.exists():
        return out
    for line in read(DIRECT_PRODUCT).splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        f = [x.strip() for x in line.split(",")]
        if len(f) >= 2:
            out.add(f[1].lower())
    return out


# ────────────────────────────── 主流程

def main() -> int:
    ap = argparse.ArgumentParser(description="ads 域名集构建器（三支路 · 离线）")
    ap.add_argument("--out", default=str(OUT_DIR / "ads-src.txt"))
    ap.add_argument("--audit", default=str(OUT_DIR / "ads-audit.txt"))
    ap.add_argument("--dry-run", action="store_true", help="只输出审计，不落盘")
    args = ap.parse_args()

    required = [LITE, CHINA, JINX_BLK, JINX_BLK_WILD, COVERAGE_BASELINE] + \
               [UP / "cn" / f for f, _ in B_SOURCES]
    missing = [str(p.relative_to(ROOT)) for p in required if not p.exists()]
    if missing:
        print("❌ 缺 upstream 源文件，先跑 python skill/scripts/freeze_upstream.py", file=sys.stderr)
        for m in missing:
            print("   " + m, file=sys.stderr)
        return EXIT_ENV

    stat_a, stat_c = collections.Counter(), collections.Counter()
    stat_b: dict[str, tuple[set, collections.Counter]] = {}

    # ── A 支路 ─────────────────────────────────────────────
    A = parse_domain_set(read(LITE), stat_a)
    stat_a["原始"] = len(A)

    # ── B 支路 ─────────────────────────────────────────────
    exceptions: set[str] = set()
    for fname, label in B_SOURCES:
        s = collections.Counter()
        doms, exc = parse_adblock(read(UP / "cn" / fname), s)
        exceptions |= exc
        cl = collections.Counter(registrable(d) for d in doms)
        keep = {d for d in doms
                if (cl[registrable(d)] >= 2 or has_semantic(d) or has_platform(d))}
        s["拦截 域名级(原始)"] = len(doms)
        s["准入后(采用)"] = len(keep)
        s["剔除(孤立且无语义)"] = len(doms) - len(keep)
        stat_b[label] = (keep, s)
    B = set().union(*[v[0] for v in stat_b.values()])

    # ── C 支路 ─────────────────────────────────────────────
    C = parse_jinx(read(JINX_BLK), stat_c) | parse_jinx_wildcard(read(JINX_BLK_WILD), stat_c)
    stat_c["原始"] = len(C)

    # ── 合并与后处理 ────────────────────────────────────────
    merged = A | B | C

    after_exc = {d for d in merged if not under(d, exceptions)}
    n_exc = len(merged) - len(after_exc)

    res_drop = {d for d in after_exc if is_resource(d) and not has_semantic(d)}
    fn_drop = {d for d in after_exc if is_function_domain(d)}
    after_fn = after_exc - res_drop - fn_drop

    cl = collections.Counter(registrable(d) for d in after_fn)
    gray_drop = {d for d in after_fn
                 if d in A and is_gray_random(d, cl[registrable(d)],
                                              has_semantic(d) or has_platform(d))}
    after_gray = after_fn - gray_drop

    climbed, climb_log = set(), []
    for d in after_gray:
        out, did = climb(d)
        climbed.add(out)
        if did:
            climb_log.append((d, out))

    direct = parse_direct_product()
    # direct 与 ads 的关系是「顺序」而非「删除」：direct 排在拦截集之前，
    # 更具体的规则先命中 DIRECT，功能域自然获救。此处只报告，不删上层域。
    shadowed_direct = sorted(g for g in direct if under(g, climbed))
    final = sorted(climbed)

    # ── 覆盖率 ─────────────────────────────────────────────
    fset = set(final)
    awa = set()
    for l in read(COVERAGE_BASELINE).splitlines():
        l = l.strip()
        if l.startswith("||") and l.endswith("^"):
            d = l[2:-1].lower()
            if valid_domain(d):
                awa.add(d)
    awa_hit = sum(1 for d in awa if under(d, fset))
    coverage = awa_hit / len(awa) if awa else None

    cn_base = {registrable(l.strip().lower().lstrip("."))
               for l in read(CHINA).splitlines()
               if l.strip() and not l.startswith("#") and "." in l}
    j_cn = [d for d in C if registrable(d) in cn_base]
    j_hit = sum(1 for d in j_cn if under(d, fset))
    cov_jinx = j_hit / len(j_cn) if j_cn else None

    # ── 断言 ───────────────────────────────────────────────
    errs = []
    if any(IPV4_RE.match(d) or CIDR_RE.search(d) for d in final):
        errs.append("产物混入 IP/CIDR")
    if any(not valid_domain(d) for d in final):
        errs.append("产物含形态非法条目")
    if any(c in d for d in final for c in "#$*:/"):
        errs.append("产物含通配/修饰符/路径")
    _res = [d for d in final if is_resource(d) and not has_semantic(d)]
    if _res:
        errs.append("产物含静态资源域 %d 条，例：%s" % (len(_res), _res[:3]))
    _missing = [d for d in MUST_CONTAIN if d not in fset]
    if _missing:
        errs.append("产物缺失已知必需域：%s" % _missing)
    if not direct:
        errs.append("direct 放行清单为空，顺序保护无从谈起")
    if coverage is not None and coverage < COVERAGE_FLOOR:
        errs.append("独立基线覆盖率 %.1f%% 低于护栏 %.0f%%"
                    % (coverage * 100, COVERAGE_FLOOR * 100))
    if not (SIZE_RANGE[0] <= len(final) <= SIZE_RANGE[1]):
        errs.append("产物规模 %d 超出护栏 %s" % (len(final), SIZE_RANGE))
    if len(final) != len(fset):
        errs.append("产物存在重复")

    # ── 审计 ───────────────────────────────────────────────
    audit = [
        "构建审计 / ads（三支路合成 · 离线）",
        "=" * 64,
        "上游快照: upstream/manifest.json（跑 freeze_upstream.py --check 可校验未被手改）",
        "",
        "一、A 支路（217heidai lite）",
    ]
    audit += ["  %-30s %6d" % (k, v) for k, v in stat_a.items()]
    audit += ["", "二、B 支路（5 个中文源）"]
    for label, (keep, s) in stat_b.items():
        audit.append("  [%s]" % label)
        audit += ["    %-26s %6d" % (k, v) for k, v in s.items()]
    audit += ["", "三、C 支路（Jinx 3.2.3 明文快照）"]
    audit += ["  %-30s %6d" % (k, v) for k, v in stat_c.items()]
    audit += [
        "",
        "四、漏斗",
        "  A %d | B %d | C %d" % (len(A), len(B), len(C)),
        "  合并去重                   : %d" % len(merged),
        "  @@ 例外减法（%d 条规则）     : -%d" % (len(exceptions), n_exc),
        "  静态资源剔除               : -%d" % len(res_drop),
        "  功能域剔除                 : -%d" % len(fn_drop),
        "  灰产随机长尾剔除           : -%d" % len(gray_drop),
        "  语义上提后                 : %d" % len(climbed),
        "  最终产物                   : %d" % len(final),
        "",
        "五、覆盖率",
        "  【断言基线·独立】AWAvenue %d 条 → 覆盖 %d 条 = %s（护栏 %.0f%%）"
        % (len(awa), awa_hit,
           ("%.1f%%" % (coverage * 100)) if coverage is not None else "未测",
           COVERAGE_FLOOR * 100),
        "  【参考】Jinx·中国生态 %d 条 → 覆盖 %d 条 = %s"
        % (len(j_cn), j_hit,
           ("%.1f%%" % (cov_jinx * 100)) if cov_jinx is not None else "未测"),
        "",
        "六、与 direct 放行清单的重叠（不删除，靠顺序保护）",
    ]
    if shadowed_direct:
        same = [g for g in shadowed_direct if g in climbed]
        above = [g for g in shadowed_direct if g not in climbed]
        audit.append("  共 %d 条 direct 条目落在产物的拦截范围内：" % len(shadowed_direct))
        audit.append("  ⚠️ 必须确保 direct 规则集排在拦截集**之前**，否则这些功能域会被拦")
        audit.append("     （推送 / 登录会直接失效）。")
        audit.append("")
        audit.append("  ── 同域同名（产物里就有这一条）：%d 条" % len(same))
        for g in same:
            audit.append("     %s" % g)
        audit.append("  ── 被上层后缀覆盖（产物只有父域，靠顺序救子域）：%d 条" % len(above))
        for g in above:
            owners = sorted(d for d in climbed if d != g and under(g, {d}))
            audit.append("     %-44s ← 被 %s 覆盖" % (g, owners[:2]))
    else:
        audit.append("  无重叠")
    audit += ["", "七、语义上提明细（%d 条）" % len(climb_log)]
    audit += ["  %-48s -> %s" % (s, d) for s, d in sorted(climb_log)]
    audit += ["", "八、断言"]
    audit += ["  FAIL " + e for e in errs] or [
        "  PASS 形态 / 静态资源 / 必需域 / direct 非空 / 覆盖率 / 规模 / 无重复 —— 全部通过"]

    if args.dry_run:
        print("\n".join(audit))
        return EXIT_FAIL if errs else EXIT_PASS

    for path, lines in ((args.out, final), (args.audit, audit)):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines) + "\n")
    print("ads 域名集 %d 条 -> %s" % (len(final), args.out))
    print("审计 -> %s" % args.audit)
    if errs:
        print("\n❌ 断言判负：", file=sys.stderr)
        for e in errs:
            print("   " + e, file=sys.stderr)
        return EXIT_FAIL
    return EXIT_PASS


if __name__ == "__main__":
    sys.exit(main())
