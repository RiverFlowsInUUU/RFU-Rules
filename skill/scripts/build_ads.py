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
7. 灰产靠结构不靠语义。**注意作用范围——三个支路不等权：**
   A 支路（lite）：剔除「归属域下孤立 1 条 + 元音比例低 + 含数字」的随机域名。
   B 支路（5 个中文源）：准入 = 成簇(≥2) **或** 含语义，两者皆无者出局。
   C 支路（Jinx 3.2.3）：**不做任何灰产过滤** —— 它本身是人工维护的成品清单，
     再筛一遍会误删真广告，收益不抵风险。
   实测差异：产物里 93 条形态随机的域名中，40 条来自 C 支路。这是有意的。

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
import json
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
# 反向熔断清单（v10 审查三-2 / 缺陷 3）：任一条**精确**出现在产物即判非零退出。
# 两类成员，各防一种事故：
#   · 民生根域 —— 上游投毒/合并失误把整域收进黑名单时，构建当场失败，
#     而不是带着「全国断网级」条目发布。只判精确命中：拦
#     hectorstatic.baidu.com 这类**子域**是正常业务，不在此列。
#   · 规矩 5 反面实证钉子 —— 独立于 is_resource 判据的具体域。判据与断言
#     同构时（SKILL「断言最容易犯的错」）互相看不见失真，钉子看得见。
MUST_NOT_BLOCK = {
    "baidu.com", "qq.com", "weixin.qq.com", "alipay.com", "taobao.com",
    "tmall.com", "jd.com", "apple.com", "microsoft.com", "google.com",
    "bilibili.com", "weibo.com", "163.com", "sohu.com", "douyin.com",
    "zhihu.com",
    "s.bdstatic.com", "static-s.iqiyi.com",
}
# 覆盖率断言基线必须独立于支路来源，否则是同义反复。
# 曾用 Jinx 当基线而 Jinx 本身是 C 支路 → 91.5% 等于自证。
# ⚠️ 这两个护栏是「防抖」用的，加源/改判据后要跟着调 —— 命令行可覆盖，
#    但正式产出请把新值写回这里，别只靠临时参数。
COVERAGE_FLOOR = 0.85
SIZE_RANGE = (5000, 15000)

MULTI_SUFFIX = {
    "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn",
    "com.hk", "org.hk", "net.hk", "com.tw", "org.tw", "co.jp",
    "ne.jp", "co.uk", "com.au", "com.sg", "com.mo", "co.kr", "or.kr",
    # 中国省级行政区二级域（v10 审查二-3）：缺了它们，x.sh.cn 会被
    # registrable() 错当成「主域 = sh.cn」，灰产判据与成簇统计随之失真。
    "bj.cn", "tj.cn", "sh.cn", "cq.cn", "he.cn", "sx.cn", "ln.cn",
    "jl.cn", "hl.cn", "js.cn", "zj.cn", "ah.cn", "fj.cn", "jx.cn",
    "sd.cn", "ha.cn", "hb.cn", "hn.cn", "gd.cn", "gx.cn", "sc.cn",
    "gz.cn", "yn.cn", "xz.cn", "sn.cn", "gs.cn", "qh.cn", "nx.cn",
    "xj.cn",
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
    """灰产形态判据（SKILL.md 规矩 7 的量化实现）。

    阈值来源与取舍：
      - cluster_size >= 2 —— 真平台天然成簇，灰产是「归属域下孤立 1 条」；
      - len(b) >= 6 —— 主标签过短不足以判随机性，直接放过；
      - 元音占比 < 0.22 且含数字 —— 正常单词元音占比远高于此，
        随机串（x7k2m9q 型）几乎无元音。误差方向是「漏放灰产」，
        不影响真实广告域入选，故阈值可以偏保守。
    """
    if cluster_size >= 2 or semantic:
        return False
    b = registrable(d).split(".")[0]
    if len(b) < 6:
        return False
    v = sum(1 for c in b if c in "aeiou")
    return v / max(len(b), 1) < 0.22 and any(c.isdigit() for c in b)


def climb(d: str) -> tuple[str, bool]:
    """语义上提：从左往右找第一个语义 label，提到此为止，绝不越过归属域。

    ⚠️ 方向是**左优先**（v10 审查二-1：docstring 曾写「从右往左」，与实现不符，
    如实改注释）。左命中即返回 = 上提最少 = 保守方向；若改右优先（更激进，
    如 ad.track.x.com → track.x.com），拦截面会扩大，属判据级变更，须单独评审。
    归属域边界按「末尾两段」近似，对三段式 ccTLD 理论上存在把 SLD 当边界的
    空档（v10 审查二-1.3）；现行词表无会命中该位置的词根，暂不为此加复杂度。
    """
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

def render_overlap(same, above, ads_final, n_direct, label_text):
    """渲染 OVERLAP.md —— 白名单与拦截集的重叠清单。

    为什么要落盘：这份清单此前只出现在 build/ads/ads-audit.txt，而 build/ 被
    .gitignore 挡住 —— 订阅者看不到、CI 不校验。可它恰恰是本仓最该被看见的风险：
    这 42 条域名只能靠"放行行更早命中"存活，一旦消费端把 REJECT 提前
    （Surge 的 pre-matching 就是这么干的），它们全部失效。
    """
    lines = [
        "# ⚠️ 白名单 × 拦截集 重叠清单",
        "",
        "> 本文件由 `skill/scripts/build_ads.py` 生成，**勿手改**。",
        "> 生成依据：%s" % label_text,
        "> CI 会独立复算并与此文件比对（verify_products.py 第 12 段 · 共 16 段），数字或清单不符即判负。",
        "",
        "**共 %d 条**：%d 条同域同名 + %d 条上层后缀覆盖（白名单共 %d 条，其余 %d 条与拦截集无关）。"
        % (len(same) + len(above), len(same), len(above), n_direct,
           n_direct - len(same) - len(above)),
        "",
        "## 这是什么",
        "",
        "`surge-direct.list`（放行）与 `surge-ads.list`（拦截）**不是互斥的两个集合**。",
        "拦截集收了平台主域（`umeng.com`、`umeng` 系、`tanx.com`、`getui.net`、`jpush.cn` …），",
        "而放行集要保的是同族里的功能子域（推送建连、微信登录、一键登录）。",
        "域名规则只能整棵树一起拦或一起放，所以两者必然重叠 —— 重叠本身不是 bug。",
        "",
        "## 所以：放行必须排在拦截之前",
        "",
        "重叠域名的处置完全依赖**规则顺序**：更具体的那条先命中。",
        "",
        "| 客户端 | 靠什么保证 |",
        "|:--|:--|",
        "| mihomo / OpenClash | `rules` 列表顺序，`rfu-direct` 那条写在 `rfu-ads` 之前 |",
        "| Surge / Egern | `[Rule]` 顺序同上；**拦截行不得加 `pre-matching`**（见下） |",
        "| sing-box | `rules` 数组顺序，`rfu-direct` 的元素排在 `rfu-ads` 之前 |",
        "",
        "⚠️ **Surge 的 `pre-matching` 会破坏这个顺序。** 官方文档：",
        "「Rules tagged with `pre-matching` are extracted and checked before everything else」",
        "「Pre-matched rules have the highest priority」，且该参数**只支持 REJECT 系策略** ——",
        "放行行无法用同一参数自救。给拦截行加上它，下面这 %d 条会全部失效，"
        % (len(same) + len(above)),
        "表现出来就是推送收不到、微信登录转圈。",
        "",
        "## 一、同域同名（%d 条）" % len(same),
        "",
        "拦截集里就有这一条，靠放行行先命中救回。",
        "",
        "| 域名 | 备注 |",
        "|:--|:--|",
    ]
    for g in same:
        lines.append("| `%s` | 同名 |" % g)

    lines += [
        "",
        "## 二、上层后缀覆盖（%d 条）" % len(above),
        "",
        "拦截集只有父域，子域被连带；同样靠放行行先命中。",
        "",
        "| 放行条目 | 覆盖它的拦截规则 |",
        "|:--|:--|",
    ]
    for g in above:
        owners = sorted(d for d in ads_final if d != g and under(g, {d}))
        lines.append("| `%s` | %s |" % (g, " / ".join("`%s`" % o for o in owners[:2])))

    lines += [
        "",
        "## 改判据时注意",
        "",
        "- 想让这份清单变短，只能从拦截集里剔除对应**上层域** —— 但那会连带放过整个平台，",
        "  历史上试过（删 `tanx.com` 保一个子域），结果漏拦面积远大于收益，已回退。",
        "  `build_ads.py` 因此**只报告、不删除**。",
        "- 新增放行条目时，先看它是否落在这里：若是，说明它已经在靠顺序保护，",
        "  不需要额外动作；若不是，才需要考虑是否要改拦截集。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="ads 域名集构建器（三支路 · 离线）")
    ap.add_argument("--out", default=str(OUT_DIR / "ads-src.txt"))
    ap.add_argument("--audit", default=str(OUT_DIR / "ads-audit.txt"))
    ap.add_argument("--overlap", default=None,
                    help="把「白名单∩拦截集」重叠清单写成 markdown（regen.sh 传 OVERLAP.md）。"
                         "不给则只在审计里打印 —— 校验时的临时构建不该写仓库。")
    ap.add_argument("--dry-run", action="store_true", help="只输出审计，不落盘")
    ap.add_argument("--coverage-floor", type=float, default=COVERAGE_FLOOR,
                    help="独立基线覆盖率下限（默认 %(default)s）")
    ap.add_argument("--size-min", type=int, default=SIZE_RANGE[0],
                    help="产物规模下限（默认 %(default)s）")
    ap.add_argument("--size-max", type=int, default=SIZE_RANGE[1],
                    help="产物规模上限（默认 %(default)s）")
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
    # 硬熔断：MUST_NOT_BLOCK 里的精确域无条件出局，不受语义/成簇豁免（v10）。
    hard_drop = {d for d in after_exc if d in MUST_NOT_BLOCK}
    after_fn = after_exc - res_drop - fn_drop - hard_drop

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

    # ── 后缀剪枝（v10 审查缺陷 4）────────────────────────────────
    # DOMAIN-SUFFIX 语义：父域命中 ⇒ 其全部子域命中。父域已在集内时，子域行
    # 是纯冗余（实测 412 条 / 4.3%）—— 剪除不改变任何拦截行为（四端语义一致），
    # 只省体积与审计噪声。剪枝必须在 direct 顺序分析**之前**：
    # ov_same/ov_above 的口径是「final 里的 ads」，口径错了 OVERLAP 分类会虚增同名。
    pruned, prune_log = set(), []
    for d in sorted(climbed, key=lambda x: (len(x.split(".")), x)):
        parts = d.split(".")
        if any(".".join(parts[i:]) in pruned for i in range(1, len(parts))):
            prune_log.append(d)
        else:
            pruned.add(d)

    direct = parse_direct_product()
    # direct 与 ads 的关系是「顺序」而非「删除」：direct 排在拦截集之前，
    # 更具体的规则先命中 DIRECT，功能域自然获救。此处只报告，不删上层域。
    shadowed_direct = sorted(g for g in direct if under(g, pruned))
    ov_same = [g for g in shadowed_direct if g in pruned]
    ov_above = [g for g in shadowed_direct if g not in pruned]
    final = sorted(pruned)

    # 产物表头 `# source:` 的文案。为什么由这里出而不是写死在 regen.sh / verify：
    # 两处各写一遍必然漂移，而表头不一致会被第 6 段当成"产物不可复现"报错。
    # 这里从 upstream 的 version.json 派生，写进 label.txt，两边都读同一份。
    try:
        _ver = json.loads(read(UP / "jinx-3.2.3" / "version.json"))
        label_text = "upstream/(A+B+C) · jinx %s (%s)" % (
            _ver["version"], _ver["lastUpdate"][:10])
    except Exception:                                          # noqa: BLE001
        label_text = "upstream/(A+B+C)"

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
    _forbidden = [d for d in final if d in MUST_NOT_BLOCK]
    if _forbidden:
        errs.append("产物含熔断清单域名 %d 条：%s" % (len(_forbidden), _forbidden[:5]))
    # 必需域按「覆盖」语义判（v10）：剪枝后子域条目被父域连带是预期行为，
    # 只要该域仍会命中拦截（自身在集，或任一父域在集）即算在位 —— 精确命中
    # 会把「被父域覆盖」误报成缺失。
    _missing = [d for d in MUST_CONTAIN if d not in fset and not under(d, fset)]
    if _missing:
        errs.append("产物缺失已知必需域：%s" % _missing)
    if not direct:
        errs.append("direct 放行清单为空，顺序保护无从谈起")
    size_range = (args.size_min, args.size_max)
    if coverage is not None and coverage < args.coverage_floor:
        errs.append("独立基线覆盖率 %.1f%% 低于护栏 %.0f%%"
                    % (coverage * 100, args.coverage_floor * 100))
    if not (size_range[0] <= len(final) <= size_range[1]):
        errs.append("产物规模 %d 超出护栏 %s" % (len(final), size_range))
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
        "  硬熔断（MUST_NOT_BLOCK）    : -%d" % len(hard_drop),
        "  语义上提后                 : %d" % len(climbed),
        "  后缀剪枝（父域已覆盖）      : -%d" % len(prune_log),
        "  最终产物                   : %d" % len(final),
        "",
        "五、覆盖率",
        "  【断言基线·独立】AWAvenue %d 条 → 覆盖 %d 条 = %s（护栏 %.0f%%）"
        % (len(awa), awa_hit,
           ("%.1f%%" % (coverage * 100)) if coverage is not None else "未测",
           args.coverage_floor * 100),
        "  【参考】Jinx·中国生态 %d 条 → 覆盖 %d 条 = %s"
        % (len(j_cn), j_hit,
           ("%.1f%%" % (cov_jinx * 100)) if cov_jinx is not None else "未测"),
        "",
        "六、与 direct 放行清单的重叠（不删除，靠顺序保护）",
    ]
    if shadowed_direct:
        same = [g for g in shadowed_direct if g in pruned]
        above = [g for g in shadowed_direct if g not in pruned]
        audit.append("  共 %d 条 direct 条目落在产物的拦截范围内：" % len(shadowed_direct))
        audit.append("  ⚠️ 必须确保 direct 规则集排在拦截集**之前**，否则这些功能域会被拦")
        audit.append("     （推送 / 登录会直接失效）。")
        audit.append("")
        audit.append("  ── 同域同名（产物里就有这一条）：%d 条" % len(same))
        for g in same:
            audit.append("     %s" % g)
        audit.append("  ── 被上层后缀覆盖（产物只有父域，靠顺序救子域）：%d 条" % len(above))
        for g in above:
            owners = sorted(d for d in pruned if d != g and under(g, {d}))
            audit.append("     %-44s ← 被 %s 覆盖" % (g, owners[:2]))
    else:
        audit.append("  无重叠")
    audit += ["", "七、语义上提明细（%d 条）" % len(climb_log)]
    audit += ["  %-48s -> %s" % (s, d) for s, d in sorted(climb_log)]
    audit += ["", "八、断言"]
    audit += ["  FAIL " + e for e in errs] or [
        "  PASS 形态 / 静态资源 / 熔断清单 / 必需域 / direct 非空 / 覆盖率 / 规模 / 无重复 —— 全部通过"]

    if args.dry_run:
        print("\n".join(audit))
        return EXIT_FAIL if errs else EXIT_PASS

    for path, lines in ((args.out, final), (args.audit, audit)):
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines) + "\n")

    # 表头文案单独落盘，供 regen.sh / verify 共用（见上面的注释）
    with open(Path(args.out).parent / "label.txt", "w", encoding="utf-8", newline="") as f:
        f.write(label_text + "\n")

    if args.overlap:
        Path(args.overlap).write_text(
            render_overlap(ov_same, ov_above, pruned, len(direct), label_text),
            encoding="utf-8", newline="")
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
