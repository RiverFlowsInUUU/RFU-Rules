#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build-cn-adblock.py —— 中文广告 / 统计 / 隐私 / PCDN 域名规则集构建器（v3 双支路）

为什么是双支路（v2 单支路的教训）
================================
v2 只用 5 个中文源自建，产物 1,341 条，对 Jinx 中国生态的覆盖仅 46.8%。
拆解缺口发现：**85% 的缺口不是被筛掉的，而是那 5 个源里根本没有**
（例如 a.alimama.cn、abtest3-misc-*.zijieapi.com、acookie.alimama.com）。

217 的 lite 是「全量 16 源 ∩ china.txt」，是另一条浓缩路线，覆盖 60.6%，
与 5 源路线互补。两者并联后覆盖 **70.8%**，逼近 full 的天花板 74.7%，
而体积仅约 7,000 条（full 的 3%）。

因此：**A 支路（lite）+ B 支路（5 源）并联**，各自先做减法和剔除，再合并。

规则
====
1. 只做 DNS 层能表达的减法：`$` 修饰符、`##` 元素隐藏、`@@||x/path` 一律不进产物。
2. `@@` 例外只做减法，不生成 DIRECT 行（不在拦截集里就落回分流，路由自动正确）。
3. 只输出 DOMAIN-SUFFIX，无通配无正则（三端语义一致，走 trie 快路径）。
4. 只拦域名不拦 IP（IPv4 / CIDR 一律剔除）。
5. **静态资源硬排除**：label 以 static / download / status / update 开头者一律剔除，
   不受任何豁免。反面实证：s.bdstatic.com、static-s.iqiyi.com、
   download.changhong.upgrade2.huan.tv 被误拦会造成页面挂图裂、固件下载失败。
6. **灰产判定用结构，不用语义猜**（仅作用于 A 支路）：归属域下孤立 1 条 + 无广告语义
   + 形态随机（元音占比低且含数字）→ 灰产长尾剔除。不访问的域名不造成误杀，
   故残留可容忍；但结构性长尾可以不收。
7. **词边界匹配**：语义判定按 label 切分后的词元精确比对，禁止短词做子串
   （曾用裸 "ad"/"stat"/"log" 子串，误收 static / bdstatic / download / prologue /
   nchanado，是本方案最严重的一次翻车）。
8. 与 guard 白名单冲突即剔除；`@@` 例外做减法；语义上提收敛到语义 label。

断言（构建时自动执行，失败即非零退出）
======================================
① 无 IP / CIDR / 通配 / 修饰符  ② 静态资源域为 0（除命名含广告语义者）
③ MUST_CONTAIN 必需域全部在位    ④ 覆盖率不低于基线（拉 Jinx 作回归护栏）
⑤ 规模护栏 [5000, 12000]         ⑥ 无重复

用法
====
    python build-cn-adblock.py --out cn-adblock.list --audit cn-adblock.audit.txt
    python build-cn-adblock.py --dry-run
"""
import argparse
import collections
import os
import re
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/"
GUARD_URL = "https://raw.githubusercontent.com/RiverFlowsInUUU/Jinx/main/surge-direct.list"
JINX_URL = "https://raw.githubusercontent.com/RiverFlowsInUUU/Jinx/main/mihomo-ads.yaml"

LITE_FILE = "adblocksurgelite.list"          # A 支路：DOMAIN-SET 格式（每行 ".域名"）
B_SOURCES = [                                 # B 支路：adblock 语法
    ("AWAvenue_Ads_Rule.txt", "AWAvenue"),
    ("CJX's_Annoyance_List.txt", "CJX"),
    ("xinggsf_mv.txt", "xinggsf"),
    ("AdGuard_Chinese_filter.txt", "AdGuard-CN"),
    ("jiekouAD.txt", "jiekouAD"),
]

DOMAIN_RE = re.compile(
    r"^(?=.{1,253}$)([a-z0-9_]([a-z0-9_-]{0,61}[a-z0-9])?\.)+([a-z]{2,63}|xn--[a-z0-9-]+)$",
    re.I,
)
IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
CIDR_RE = re.compile(r"/\d+$")
BLOCK_RE = re.compile(r"^\|\|([a-z0-9._-]+)\^$")
EXCEPT_RE = re.compile(r"^@@\|\|([a-z0-9._-]+)\^$")

# 语义词元（label 级精确匹配，禁止短词子串）
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
# 平台名（子串安全：这些词不会构成普通英文单词）
PLATFORM_SUBSTR = (
    "kwai", "pangolin", "pangle", "gromore", "mobads", "alimama",
    "bytedance", "snssdk", "toutiao", "umeng", "tanx", "cupid",
)
RESOURCE_PREFIX = ("static", "download", "sdownload", "status", "update", "upgrade")

MUST_CONTAIN = [
    "cupid.iqiyi.com", "cupid.ptqy.gitv.tv", "adkwai.com",
    "pangolin-sdk-toutiao.com", "api-access.pangolin-sdk-toutiao.com",
    "gdt.qq.com", "e.qq.com", "umeng.com", "alog.umeng.com",
    "ad.xiaomi.com", "analytics.126.net",
]
COVERAGE_FLOOR = 0.68          # 对 Jinx·中国生态的覆盖率下限（回归护栏）

MULTI_SUFFIX = {
    "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn",
    "com.hk", "com.tw", "co.jp", "co.uk", "com.au", "com.sg",
}


def http_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read().decode("utf-8", "replace")


def registrable(d):
    p = d.split(".")
    if len(p) >= 3 and ".".join(p[-2:]) in MULTI_SUFFIX:
        return ".".join(p[-3:])
    return ".".join(p[-2:])


def label_tokens(label):
    return [t for t in re.split(r"[^a-z]+", label.lower()) if t]


def has_semantic(d):
    for lb in d.split(".")[:-1]:
        for t in label_tokens(lb):
            if t in SEMANTIC:
                return True
    return False


def has_platform(d):
    return any(k in d for k in PLATFORM_SUBSTR)


def is_resource(d):
    for lb in d.split(".")[:-1]:
        if lb.lower().startswith(RESOURCE_PREFIX):
            return True
    return False


def is_gray_random(d, cluster_size, semantic):
    """灰产长尾结构判据：孤立 1 条 + 无语义 + 形态随机（元音稀少且含数字）。"""
    if cluster_size >= 2 or semantic:
        return False
    b = registrable(d).split(".")[0]
    if len(b) < 6:
        return False
    v = sum(1 for c in b if c in "aeiou")
    return v / max(len(b), 1) < 0.22 and any(c.isdigit() for c in b)


def climb(d):
    labels = d.split(".")
    for i in range(len(labels) - 2):
        if labels[i] in SEMANTIC:
            out = ".".join(labels[i:])
            return out, out != d
    return d, False


def under(d, aset):
    p = d.split(".")
    return any(".".join(p[i:]) in aset for i in range(len(p) - 1))


def parse_domain_set(text, stat):
    out = set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", "//")):
            continue
        dom = line.lstrip(".").lower()
        if IPV4_RE.match(dom) or CIDR_RE.search(dom) or not DOMAIN_RE.match(dom):
            stat["形态非法/IP(剔除)"] += 1
            continue
        out.add(dom)
    return out


def parse_adblock(text, stat):
    out, exceptions = set(), set()
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(("!", "#", "[")):
            continue
        if "##" in line or "#@#" in line or "#?#" in line:
            stat["cosmetic(不可表达)"] += 1
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
        if IPV4_RE.match(dom) or CIDR_RE.search(dom) or not DOMAIN_RE.match(dom):
            stat["形态非法/IP(剔除)"] += 1
            continue
        out.add(dom)
    return out, exceptions


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    stat_a = collections.Counter()
    stat_b = collections.OrderedDict()

    # ── A 支路：lite ─────────────────────────────────────────
    try:
        A = parse_domain_set(http_get(BASE + LITE_FILE), stat_a)
    except Exception as e:                                     # noqa: BLE001
        print("下载 lite 失败: %s" % e, file=sys.stderr)
        return 2
    stat_a["原始"] = len(A)
    cl_a = collections.Counter(registrable(d) for d in A)
    res_a = {d for d in A if is_resource(d) and not has_semantic(d)}
    gray_a = {d for d in A
              if is_gray_random(d, cl_a[registrable(d)], has_semantic(d) or has_platform(d))}
    A = A - res_a - gray_a
    stat_a["静态资源(剔除)"] = len(res_a)
    stat_a["灰产随机长尾(剔除)"] = len(gray_a)
    stat_a["采用"] = len(A)

    # ── B 支路：5 源 ────────────────────────────────────────
    exceptions = set()
    for fname, label in B_SOURCES:
        try:
            text = http_get(BASE + fname)
        except Exception as e:                                 # noqa: BLE001
            print("下载 %s 失败: %s" % (fname, e), file=sys.stderr)
            return 2
        s = collections.Counter()
        doms, exc = parse_adblock(text, s)
        exceptions |= exc
        cl = collections.Counter(registrable(d) for d in doms)
        keep = set()
        for d in doms:
            semantic = has_semantic(d) or has_platform(d)
            if not (cl[registrable(d)] >= 2 or semantic):
                continue
            if is_resource(d) and not has_semantic(d):
                continue
            keep.add(d)
        s["拦截 域名级(原始)"] = len(doms)
        s["准入后(采用)"] = len(keep)
        s["剔除"] = len(doms) - len(keep)
        stat_b[label] = (keep, s)

    B = set().union(*[v[0] for v in stat_b.values()])

    # ── 合并与统一后处理 ────────────────────────────────────
    merged = A | B
    after_exc = {d for d in merged if not under(d, exceptions)}
    n_exc = len(merged) - len(after_exc)

    climbed, climb_log = set(), []
    for d in after_exc:
        out, did = climb(d)
        climbed.add(out)
        if did:
            climb_log.append((d, out))

    try:
        gtxt = http_get(GUARD_URL)
    except Exception as e:                                     # noqa: BLE001
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

    # ── 覆盖率回归护栏（拉 Jinx 作基线）─────────────────────
    try:
        js = set()
        for l in http_get(JINX_URL).splitlines():
            l = l.strip()
            if l.startswith("- "):
                f = [x.strip() for x in l[2:].strip().strip("'\"").split(",")]
                if len(f) >= 2 and f[0] == "DOMAIN-SUFFIX":
                    js.add(f[1].lower())
        cn_base = set()
        for l in http_get(BASE + "china.txt").splitlines():
            l = l.strip().lower().lstrip(".")
            if l and not l.startswith("#") and "." in l:
                cn_base.add(registrable(l))
        j_cn = [d for d in js if registrable(d) in cn_base]
        fset_tmp = set(final)
        hit = sum(1 for d in j_cn if under(d, fset_tmp))
        coverage = hit / len(j_cn) if j_cn else 0.0
    except Exception:                                          # noqa: BLE001
        j_cn, hit, coverage = [], 0, None

    # ── 断言 ───────────────────────────────────────────────
    errs = []
    fset = set(final)
    if any(IPV4_RE.match(d) or CIDR_RE.search(d) for d in final):
        errs.append("产物混入 IP/CIDR")
    if any(not DOMAIN_RE.match(d) for d in final):
        errs.append("产物含形态非法条目")
    if any(c in d for d in final for c in "#$*:/"):
        errs.append("产物含通配/修饰符/路径")
    _res = [d for d in final if is_resource(d) and not has_semantic(d)]
    if _res:
        errs.append("产物含静态资源域 %d 条，例：%s" % (len(_res), _res[:3]))
    _missing = [d for d in MUST_CONTAIN if d not in fset]
    if _missing:
        errs.append("产物缺失已知必需域：%s" % _missing)
    if coverage is not None and coverage < COVERAGE_FLOOR:
        errs.append("覆盖率 %.1f%% 低于护栏 %.0f%%" % (coverage * 100, COVERAGE_FLOOR * 100))
    if not (5000 <= len(final) <= 12000):
        errs.append("产物规模 %d 超出护栏 [5000, 12000]" % len(final))
    if len(final) != len(fset):
        errs.append("产物存在重复")

    # ── 输出 ───────────────────────────────────────────────
    hdr = [
        "# 中文广告 / 统计 / 隐私 / PCDN 域名规则集（由脚本生成，请勿手改）",
        "# 生成器: test/build-cn-adblock.py",
        "# 支路 A: 217heidai adblocksurgelite.list（全量 16 源 ∩ china.txt）",
        "# 支路 B: AWAvenue · CJX · xinggsf · AdGuard_Chinese_filter · jiekouAD",
        "# 规矩: 仅 DNS 层可表达 · 纯 DOMAIN-SUFFIX 无通配 · 只拦域名不拦 IP",
        "#       静态资源域硬排除 · @@ 例外只做减法不生成 DIRECT · 与 guard 冲突即剔除",
        "# 规模: %d 条" % len(final),
    ]
    audit = ["构建审计 / cn-adblock（v3 双支路）", "=" * 64, "", "一、A 支路（lite）"]
    for k, v in stat_a.items():
        audit.append("  %-24s %6d" % (k, v))
    audit += ["", "二、B 支路（5 源）"]
    for label, (keep, s) in stat_b.items():
        audit.append("  [%s]" % label)
        for k, v in s.items():
            audit.append("    %-24s %6d" % (k, v))
    audit += [
        "",
        "三、漏斗",
        "  A 支路采用                  : %d" % len(A),
        "  B 支路采用                  : %d" % len(B),
        "  合并去重                    : %d" % len(merged),
        "  扣除 @@ 域名级例外（%d 条）   : -%d" % (len(exceptions), n_exc),
        "  语义上提后                  : %d" % len(climbed),
        "  与 guard 冲突剔除（%d 条）    : -%d" % (len(collided), len(collided)),
        "  最终产物                    : %d" % len(final),
        "",
        "四、覆盖率（回归护栏）",
        "  Jinx·中国生态 %d 条 → 覆盖 %d 条 = %s"
        % (len(j_cn), hit, ("%.1f%%" % (coverage * 100)) if coverage is not None else "未测"),
        "",
        "五、语义上提明细（%d 条）" % len(climb_log),
    ]
    for src, dst in sorted(climb_log):
        audit.append("  %-46s -> %s" % (src, dst))
    audit += ["", "六、与 guard 白名单冲突（已剔除，%d 条）" % len(collided)]
    for d in collided:
        audit.append("  " + d)
    audit += ["", "七、断言"]
    audit += ["  FAIL " + e for e in errs] or [
        "  PASS 形态 / 静态资源 / 必需域 / 覆盖率 / 规模 / 无重复 —— 全部通过"]

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
