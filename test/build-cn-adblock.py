#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build-cn-adblock.py —— 中文广告 / 统计 / 隐私 / PCDN 域名规则集构建器

设计原则（对齐社区标准做法：AdGuard HostlistCompiler、hagezi 编译流程）
=====================================================================
1. **只做 DNS 层能表达的减法。** 凡需资源类型、路径、元素选择器才能表达的规则
   （`$third-party`、`##` 元素隐藏、`@@||x/path`）一律不进入产物 —— DNS 层无法
   区分它们，强行降级会造成无差别拦截（误杀）。宁可漏拦，不可拦错。
2. **`@@` 例外只做减法，不生成任何 DIRECT/白名单行。** 域名不在拦截集里就会
   自然落回既有分流规则（国内→DIRECT、国际→FINAL→代理），路由结果自动正确。
   写成 DIRECT 属补丁式做法，会引入规则顺序依赖与 pre-matching 冲突。
3. **只输出 DOMAIN-SUFFIX（纯后缀）。** 不带通配、不带正则 —— 三端语义一致，
   可走 mihomo `behavior: domain` / Surge DOMAIN-SET / sing-box `domain_suffix`
   的最快路径，不存在跨平台通配语义差异。
4. **只拦域名，不拦 IP。** IPv4 字面量与 CIDR 一律剔除（DNS 层拦 IP 无效，
   且可能切断正常连接）。该条已固化为断言，防回潮。
5. **灰产不靠逐条判断，靠结构判据。** 赌博/色情导流的形态特征是「随机域名 +
   归属域下只有孤立 1 条」。因此对所有源统一施加准入：
   仅保留「归属域成簇（≥2，说明是某平台的多个子域）」或「名称含广告/统计/PCDN
   语义（说明是广告类命名）」的条目。真正的广告平台天然满足其一，
   灰产随机长尾两者都不满足，自动出局。判据是数据 + 算法，无人工逐条决定。

来源与取舍
==========
取用：AWAvenue（国内 App 广告）、CJX's Annoyance（中文骚扰广告）、
      xinggsf_mv（优酷等）、AdGuard_Chinese_filter（官方中文广告+跟踪）、
      jiekouAD（用于补平台主域，如 adkwai.com；其灰产长尾由准入规则剔除）。
排除：EasyList_China —— 实测对上述并集的独占贡献为 0（与 AdGuard Chinese 完全重叠）。

用法
====
    python build-cn-adblock.py --out cn-adblock.list --audit cn-adblock.audit.txt
    python build-cn-adblock.py --dry-run          # 只打印审计，不写文件

退出码：0 成功 / 1 断言失败 / 2 环境或网络问题
"""
import argparse
import collections
import os
import re
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/"
GUARD_URL = "https://raw.githubusercontent.com/RiverFlowsInUUU/Jinx/main/surge-direct.list"

# (文件名, 显示名) —— 全部源统一施加「成簇或语义」准入（见文件头第 5 条）
SOURCES = [
    ("AWAvenue_Ads_Rule.txt", "AWAvenue"),
    ("CJX's_Annoyance_List.txt", "CJX"),
    ("xinggsf_mv.txt", "xinggsf"),
    ("AdGuard_Chinese_filter.txt", "AdGuard-CN"),
    ("jiekouAD.txt", "jiekouAD"),
]

# ── 形态：域名准入 ────────────────────────────────────────────────
DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9])?\.)+([a-z]{2,63}|xn--[a-z0-9-]+)$",
    re.I,
)
IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
CIDR_RE = re.compile(r"/\d+$")
BLOCK_RE = re.compile(r"^\|\|([a-z0-9._-]+)\^$")       # 纯域名拦截，无修饰符无路径
EXCEPT_RE = re.compile(r"^@@\|\|([a-z0-9._-]+)\^$")    # 纯域名例外，无修饰符无路径

# ── 语义 label 词表（数据，非判断）────────────────────────────────
# 用途一：语义上提 —— 把 t7z.cupid.iqiyi.com 收敛到 cupid.iqiyi.com
# 用途二：灰产源准入 —— 只有含这些语义的条目才可能来自 strict 源
SEMANTIC = {
    "ad", "ads", "adx", "adserv", "adserver", "adservice", "adsrv", "adpush",
    "advert", "adverts", "advertise", "advertisement", "adview", "adlog",
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

# strict 源的关键词（子串级）。比 SEMANTIC 宽，用于识别「名字里带广告语义词的
# 平台域」（如 adkwai.com、pangolin-sdk-toutiao.com），同时灰产随机域不会命中。
AD_SUBSTR = (
    "ad", "ads", "kwai", "pangolin", "pangle", "gdt", "tanx", "alimama",
    "csj", "gromore", "mobads", "umeng", "stat", "track", "log", "pcdn",
    "p2p", "beacon", "collect", "cupid", "bytedance", "snssdk", "toutiao",
)

MULTI_SUFFIX = {
    "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn",
    "com.hk", "com.tw", "co.jp", "co.uk", "com.au", "com.sg",
}


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read().decode("utf-8", "replace")


def registrable(d):
    """粗略归属域（eTLD+1），用于成簇与上提边界。不引入额外依赖。"""
    p = d.split(".")
    if len(p) >= 3 and ".".join(p[-2:]) in MULTI_SUFFIX:
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def climb(d):
    """语义上提：从右往左找第一个语义 label，上提到该 label 为止。

    例：t7z.cupid.iqiyi.com → cupid.iqiyi.com（cupid 是语义 label，到此停）
        api.ad.xiaomi.com   → ad.xiaomi.com
    绝不跨到平台主域（iqiyi.com 本身不会被生成）。
    """
    labels = d.split(".")
    for i in range(len(labels) - 2):
        if labels[i] in SEMANTIC:
            out = ".".join(labels[i:])
            return out, out != d
    return d, False


def has_semantic(d):
    return any(seg in SEMANTIC for seg in d.split(".")[:-1])


def under(d, aset):
    p = d.split(".")
    return any(".".join(p[i:]) in aset for i in range(len(p) - 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    per_source = collections.OrderedDict()
    exceptions = set()

    for fname, label in SOURCES:
        try:
            text = http_get(BASE + fname)
        except Exception as e:                                   # noqa: BLE001
            print("下载失败 %s: %s" % (fname, e), file=sys.stderr)
            return 2
        doms, s = set(), collections.Counter()
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith(("!", "#", "[")):
                continue
            if "##" in line or "#@#" in line or "#?#" in line:
                s["cosmetic(不可表达)"] += 1
                continue
            if line.startswith("@@"):
                m = EXCEPT_RE.match(line)
                if m:
                    exceptions.add(m.group(1).lower())
                    s["例外 域名级(采用)"] += 1
                else:
                    s["例外 条件/路径型(不可表达)"] += 1
                continue
            if "$" in line or "/" in line:
                s["条件/路径型拦截(不可表达)"] += 1
                continue
            m = BLOCK_RE.match(line)
            dom = m.group(1).lower() if m else (line.lower() if DOMAIN_RE.match(line) else None)
            if not dom:
                s["其他(丢弃)"] += 1
                continue
            if IPV4_RE.match(dom) or CIDR_RE.search(dom):
                s["IP/CIDR(剔除)"] += 1
                continue
            if not DOMAIN_RE.match(dom):
                s["形态非法(剔除)"] += 1
                continue
            doms.add(dom)
        per_source[label] = [doms, s]

    # ── 统一准入：归属域成簇(≥2) 或 名称含广告/统计/PCDN 语义 ──
    for label, (doms, s) in per_source.items():
        cl = collections.Counter(registrable(d) for d in doms)
        keep, by_cl, by_sem = set(), 0, 0
        for d in doms:
            clustered = cl[registrable(d)] >= 2
            semantic = has_semantic(d) or any(k in d for k in AD_SUBSTR)
            if clustered:
                by_cl += 1
            if semantic:
                by_sem += 1
            if clustered or semantic:
                keep.add(d)
        s["拦截 域名级(原始)"] = len(doms)
        s["  └ 成簇命中"] = by_cl
        s["  └ 语义命中"] = by_sem
        s["孤立且无语义(剔除)"] = len(doms) - len(keep)
        s["拦截 域名级(采用)"] = len(keep)
        per_source[label][0] = keep

    block = set().union(*[v[0] for v in per_source.values()])

    # ── 规矩：例外只做减法 ─────────────────────────────────────
    after_exc = {d for d in block if not under(d, exceptions)}
    n_exc = len(block) - len(after_exc)

    # ── 规矩：语义上提 ────────────────────────────────────────
    climbed, climb_log = set(), []
    for d in after_exc:
        out, did = climb(d)
        climbed.add(out)
        if did:
            climb_log.append((d, out))

    # ── 规矩：与 guard 白名单冲突即剔除 ────────────────────────
    try:
        gtxt = http_get(GUARD_URL)
    except Exception as e:                                       # noqa: BLE001
        print("下载 guard 失败: %s" % e, file=sys.stderr)
        return 2
    guard = set()
    for line in gtxt.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        f = [x.strip() for x in line.split(",")]
        if len(f) >= 2:
            guard.add(f[1].lower())
    collided = sorted(d for d in climbed if under(d, guard))
    final = sorted(climbed - set(collided))

    # ── 断言（固化，防回潮）────────────────────────────────────
    errs = []
    if any(IPV4_RE.match(d) or CIDR_RE.search(d) for d in final):
        errs.append("产物混入 IP/CIDR")
    if any(not DOMAIN_RE.match(d) for d in final):
        errs.append("产物含形态非法条目")
    if any("#" in d or "$" in d or "*" in d or "/" in d for d in final):
        errs.append("产物含通配/修饰符/路径")
    if any(under(d, exceptions) for d in final):
        errs.append("产物与例外集重叠（减法失败）")
    if any(under(d, set(collided)) for d in final):
        errs.append("产物与 guard 冲突")
    if len(final) != len(set(final)):
        errs.append("产物存在重复")
    _cl = collections.Counter(registrable(d) for d in final)
    _stray = [d for d in final
              if _cl[registrable(d)] == 1
              and not has_semantic(d)
              and not any(k in d for k in AD_SUBSTR)]
    if _stray:
        errs.append("产物含 %d 条孤立且无语义条目（灰产准入失效）" % len(_stray))

    # ── 输出 ─────────────────────────────────────────────────
    hdr = [
        "# 中文广告 / 统计 / 隐私 / PCDN 域名规则集（由脚本生成，请勿手改）",
        "# 生成器: test/build-cn-adblock.py",
        "# 源: AWAvenue · CJX's Annoyance · xinggsf_mv · AdGuard_Chinese_filter · jiekouAD(严格准入)",
        "# 排除: EasyList_China（对并集独占贡献实测为 0）",
        "# 规矩: 仅 DNS 层可表达 · 只收无 $ 修饰符无路径 · 纯 DOMAIN-SUFFIX 无通配",
        "#       @@ 例外只做减法不生成 DIRECT · 只拦域名不拦 IP · 与 guard 冲突即剔除",
        "# 规模: %d 条" % len(final),
    ]
    audit = ["构建审计 / cn-adblock", "=" * 62, "", "一、各源解析明细"]
    for label, (doms, s) in per_source.items():
        audit.append("  [%s]" % label)
        for k, v in s.items():
            audit.append("    %-28s %6d" % (k, v))
    audit += [
        "",
        "二、漏斗",
        "  各源采用合计（去重前）      : %d" % sum(len(v[0]) for v in per_source.values()),
        "  去重后拦截集                : %d" % (len(block)),
        "  扣除 @@ 域名级例外（%d 条）   : -%d" % (len(exceptions), n_exc),
        "  语义上提后                  : %d" % len(climbed),
        "  与 guard 冲突剔除（%d 条）    : -%d" % (len(collided), len(collided)),
        "  最终产物                    : %d" % len(final),
        "",
        "三、语义上提明细（%d 条）" % len(climb_log),
    ]
    for src, dst in sorted(climb_log):
        audit.append("  %-46s -> %s" % (src, dst))
    audit += ["", "四、与 guard 白名单冲突（已剔除，%d 条）" % len(collided)]
    for d in collided:
        audit.append("  " + d)
    audit += ["", "五、断言"]
    audit += ["  FAIL " + e for e in errs] or [
        "  PASS 形态 / 无通配 / 例外减法 / guard 一致 / 无重复 / 灰产准入 —— 全部通过"]

    if args.dry_run:
        print("\n".join(audit))
        return 1 if errs else 0

    for path, lines in ((args.out, hdr + final), (args.audit, audit)):
        d = os.path.dirname(os.path.abspath(path))
        if d:
            os.makedirs(d, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write("\n".join(lines) + "\n")
    print("产物 %d 条 -> %s" % (len(final), args.out))
    print("审计 -> %s" % args.audit)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
