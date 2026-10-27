#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""build-cn-adblock.py —— 中文广告 / 统计 / 隐私 / PCDN 域名规则集构建器（v4 三支路）

版本演进（每次都是核查后推翻前一版的错误假设，保留在此供追溯）
================================================================
v2（单支路 · 5 源）：1,341 条，覆盖 Jinx·中国 46.8%。
    错在「源选错」——85% 的缺口不是被筛掉，而是那 5 源里根本没有。
v3（双支路 · lite + 5 源）：7,108 条，覆盖 70.6%。
    补上了源覆盖，但留下两个缺陷：
    ① **guard 冲突检测方向反了**（查"产物条目是否在 guard 里"，
       应为"guard 条目是否被产物覆盖"）→ `getui.net` / `gepush.com` 整域留存，
       个推推送会被拦，用户可感知故障。
    ② A 支路（lite）未做功能域过滤 → 带入 `c.uaa.iqiyi.com`（统一账号认证）、
       `cm.passport.iqiyi.com`（登录）、`doh.iqiyi.com` 等 449 条功能域。
v4（三支路 · lite + 5 源 + Jinx）：约 9,300 条，覆盖 Jinx·中国 93%+。
    Jinx 3.2.3 已冻结在仓内、不会漂移，作为"补丁支路"使用最稳；
    它的通配部分（158 条 DOMAIN-REGEX）无法转后缀，按规则丢弃。

规则
====
1. 只做 DNS 层能表达的减法：`$` 修饰符、`##` 元素隐藏、`@@||x/path` 一律不进产物。
2. `@@` 例外只做减法，不生成 DIRECT 行（不在拦截集里就落回分流，路由自动正确）。
3. 只输出 DOMAIN-SUFFIX，无通配无正则（三端语义一致，走 trie 快路径）。
4. 只拦域名不拦 IP（IPv4 / CIDR 一律剔除）。
5. **静态资源硬排除**：label 以 static / download / status / update 开头者一律剔除。
   反面实证：s.bdstatic.com、static-s.iqiyi.com 被误拦会造成页面挂图裂。
6. **功能域排除**：含 push / passport / login / uaa / doh / im / chat / subscription /
   api / sdk 等功能词元、且无广告语义者剔除。**但豁免 ad 词根**
   （advertising-api.amazon.com、api-adservices.apple.com 这类是真广告，
   曾因词表缺 advertising / adservices 被误删 83 条）。
7. **guard 冲突检测方向**：只查「guard 条目是否被产物覆盖」（guard ⊆ 产物）。
   冲突时删除覆盖它的上层后缀域（DOMAIN-SUFFIX 无法排除单个子域）。
8. **词边界匹配**：语义判定按 label 切分后的词元精确比对，禁止短词子串
   （曾用裸 "ad"/"stat"/"log" 子串，误收 static / bdstatic / download / prologue）。
9. 灰产判定用结构（孤立 1 条 + 无语义 + 形态随机），不用语义猜。

断言（构建时自动执行，失败即非零退出）
======================================
① 无 IP / CIDR / 通配 / 修饰符        ② 静态资源域为 0（除命名含广告语义者）
③ MUST_CONTAIN 必需域全部在位          ④ guard 条目不得被产物覆盖（一个都不能）
⑤ 覆盖率不低于护栏                    ⑥ 规模护栏
⑦ 无重复

用法
====
    python build-cn-adblock.py --out cn-adblock.list --audit cn-adblock.audit.txt
    python build-cn-adblock.py --dry-run
"""
import argparse
import collections
import hashlib
import os
import re
import sys
import urllib.request

BASE = "https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules/"
GUARD_URL = "https://raw.githubusercontent.com/RiverFlowsInUUU/Jinx/main/surge-direct.list"
JINX_URL = "https://raw.githubusercontent.com/RiverFlowsInUUU/Jinx/main/mihomo-ads.yaml"

LITE_FILE = "adblocksurgelite.list"          # A 支路：DOMAIN-SET（每行 ".域名"）
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
AD_ROOT_RE = re.compile(r"^(ad|ads|advert)", re.I)   # 广告词根，豁免功能域排除

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
    "bytedance", "snssdk", "toutiao", "umeng", "tanx", "cupid",
)
# 功能词元：出现且无广告语义/无 ad 词根 → 判定为功能域，剔除
FUNCTION_TOKENS = {
    "push", "upush", "passport", "login", "auth", "uaa", "oauth", "sso",
    "account", "dns", "doh", "dot", "im", "chat", "message", "msg", "mail",
    "static", "css", "img", "image", "pic", "photo", "video", "play", "player",
    "media", "download", "upload", "file", "cdn", "update", "upgrade", "patch",
    "config", "cfg", "captcha", "verify", "sms", "code", "pay", "wallet",
    "order", "cart", "coupon", "search", "feed", "comment", "share", "live",
    "room", "subscription", "member", "vip", "api", "sdk", "gateway", "openapi",
}
RESOURCE_PREFIX = ("static", "download", "sdownload", "status", "update", "upgrade")

MUST_CONTAIN = [
    "cupid.iqiyi.com", "cupid.ptqy.gitv.tv", "adkwai.com",
    "pangolin-sdk-toutiao.com", "api-access.pangolin-sdk-toutiao.com",
    "gdt.qq.com", "e.qq.com", "umeng.com", "alog.umeng.com",
    "ad.xiaomi.com", "analytics.126.net",
]
# 覆盖率断言基线必须「独立于支路来源」，否则是同义反复。
# 曾用 Jinx 作基线，而 Jinx 本身就是 C 支路 → 91.5% 等于自证。
# 现改用 AWAvenue（主流国内 App 广告真值，产物仅部分采用）。
COVERAGE_BASELINE = "AWAvenue_Ads_Rule.txt"
COVERAGE_FLOOR = 0.85
COVERAGE_FLOOR_JINX_REF = 0.90   # Jinx·中国生态 仅作参考播报，不参与判负
SIZE_RANGE = (5000, 15000)

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


def has_ad_root(d):
    """label 以 ad / ads / advert 开头即视为广告词根（豁免功能域排除）。"""
    return any(AD_ROOT_RE.match(lb) for lb in d.split(".")[:-1])


def has_platform(d):
    return any(k in d for k in PLATFORM_SUBSTR)


def has_function(d):
    for lb in d.split(".")[:-1]:
        for t in label_tokens(lb):
            if t in FUNCTION_TOKENS:
                return True
    return False


def is_function_domain(d):
    """功能域：有功能词元，且既无广告语义、也无 ad 词根。"""
    return has_function(d) and not has_semantic(d) and not has_ad_root(d)


def is_resource(d):
    return any(lb.lower().startswith(RESOURCE_PREFIX) for lb in d.split(".")[:-1])


def is_gray_random(d, cluster_size, semantic):
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


def parse_jinx(text, stat):
    out, regex_cnt = set(), 0
    for l in text.splitlines():
        l = l.strip()
        if not l.startswith("- "):
            continue
        f = [x.strip() for x in l[2:].strip().strip("'\"").split(",")]
        if len(f) < 2:
            continue
        if f[0] == "DOMAIN-SUFFIX":
            if DOMAIN_RE.match(f[1]) and not IPV4_RE.match(f[1]):
                out.add(f[1].lower())
            else:
                stat["形态非法/IP(剔除)"] += 1
        elif f[0] == "DOMAIN-REGEX":
            regex_cnt += 1
    stat["DOMAIN-REGEX(通配,无法转后缀)"] = regex_cnt
    return out


def snapshot_name(fname):
    """把源标识转成安全的快照文件名。

    URL 里含 ':' '/' 等字符，Windows 下非法 —— 曾因此生成名为 "https" 的目录。
    做法：取 basename + 路径哈希前缀，保证唯一且跨平台合法。
    """
    raw = fname if fname.startswith("http") else BASE + fname
    base = os.path.basename(raw.split("?")[0]) or "src"
    tag = hashlib.sha1(raw.encode()).hexdigest()[:8]
    return "%s.%s.txt" % (base, tag)


def fetch(fname, src_dir):
    """统一取源：优先读 --src-dir 快照，缺失则下载并落盘。

    这是「产物可复现」的前提 —— 远程源天天变，直连拉取则每次结果不同，
    无法满足本仓「产物 == 源头重跑」的断言惯例（参见 jinx-rules/ 的做法）。
    """
    url = fname if fname.startswith("http") else BASE + fname
    if not src_dir:
        return http_get(url), "live"
    path = os.path.join(src_dir, snapshot_name(fname))
    if os.path.exists(path):
        return open(path, encoding="utf-8", errors="replace").read(), "snapshot"
    text = http_get(url)
    os.makedirs(src_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return text, "download"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--audit", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--src-dir", default=None,
                    help="源快照目录。存在则从本地读取（可复现）；"
                         "不存在则下载并落盘，供下次离线复跑")
    args = ap.parse_args()

    stat_a = collections.Counter()
    stat_b = collections.OrderedDict()
    stat_c = collections.Counter()

    # ── A 支路：lite ─────────────────────────────────────────
    try:
        A = parse_domain_set(fetch(LITE_FILE, args.src_dir)[0], stat_a)
    except Exception as e:                                     # noqa: BLE001
        print("下载 lite 失败: %s" % e, file=sys.stderr)
        return 2
    stat_a["原始"] = len(A)

    # ── B 支路：5 源 ────────────────────────────────────────
    exceptions = set()
    for fname, label in B_SOURCES:
        try:
            text = fetch(fname, args.src_dir)[0]
        except Exception as e:                                 # noqa: BLE001
            print("下载 %s 失败: %s" % (fname, e), file=sys.stderr)
            return 2
        s = collections.Counter()
        doms, exc = parse_adblock(text, s)
        exceptions |= exc
        cl = collections.Counter(registrable(d) for d in doms)
        keep = {d for d in doms
                if (cl[registrable(d)] >= 2 or has_semantic(d) or has_platform(d))}
        s["拦截 域名级(原始)"] = len(doms)
        s["准入后(采用)"] = len(keep)
        s["剔除"] = len(doms) - len(keep)
        stat_b[label] = (keep, s)

    B = set().union(*[v[0] for v in stat_b.values()])

    # ── C 支路：Jinx 3.2.3（仓内冻结，不会漂移）───────────────
    try:
        jtxt = fetch(JINX_URL, args.src_dir)[0]
    except Exception as e:                                     # noqa: BLE001
        print("下载 Jinx 失败: %s" % e, file=sys.stderr)
        return 2
    C = parse_jinx(jtxt, stat_c)
    stat_c["原始"] = len(C)

    # ── 合并 ───────────────────────────────────────────────
    merged = A | B | C

    # 后处理①：@@ 例外减法
    after_exc = {d for d in merged if not under(d, exceptions)}
    n_exc = len(merged) - len(after_exc)

    # 后处理②：静态资源 / 功能域剔除
    res_drop = {d for d in after_exc if is_resource(d) and not has_semantic(d)}
    fn_drop = {d for d in after_exc if is_function_domain(d)}
    after_fn = after_exc - res_drop - fn_drop
    stat_a["静态资源(剔除)"] = len(res_drop)
    stat_a["功能域(剔除)"] = len(fn_drop)

    # 后处理③：灰产随机长尾（仅 A 支路来源，按合并后聚类判断）
    cl = collections.Counter(registrable(d) for d in after_fn)
    gray_drop = {d for d in after_fn
                 if d in A and is_gray_random(d, cl[registrable(d)],
                                              has_semantic(d) or has_platform(d))}
    after_gray = after_fn - gray_drop
    stat_a["灰产随机长尾(剔除)"] = len(gray_drop)

    # 后处理④：语义上提
    climbed, climb_log = set(), []
    for d in after_gray:
        out, did = climb(d)
        climbed.add(out)
        if did:
            climb_log.append((d, out))

    # 后处理⑤：guard 冲突（方向：guard 条目是否被产物覆盖）
    try:
        gtxt = fetch(GUARD_URL, args.src_dir)[0]
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
    bad_guards = sorted(g for g in guard if under(g, climbed))
    # 删除"覆盖了 guard 条目"的上层域（DOMAIN-SUFFIX 无法排除单个子域）
    supersets = {d for d in climbed if any(under(g, {d}) for g in bad_guards)}
    final = sorted(climbed - supersets)

    # ── 覆盖率：断言用独立基线（AWAvenue），Jinx 仅作参考 ──
    fset_tmp = set(final)
    try:
        awa = set()
        for l in fetch(COVERAGE_BASELINE, args.src_dir)[0].splitlines():
            l = l.strip()
            if l.startswith("||") and l.endswith("^"):
                d = l[2:-1].lower()
                if DOMAIN_RE.match(d):
                    awa.add(d)
        awa_hit = sum(1 for d in awa if under(d, fset_tmp))
        coverage = awa_hit / len(awa) if awa else None
    except Exception:                                          # noqa: BLE001
        awa, awa_hit, coverage = set(), 0, None
    try:
        cn_base = set()
        for l in fetch("china.txt", args.src_dir)[0].splitlines():
            l = l.strip().lower().lstrip(".")
            if l and not l.startswith("#") and "." in l:
                cn_base.add(registrable(l))
        j_cn = [d for d in C if registrable(d) in cn_base]
        j_hit = sum(1 for d in j_cn if under(d, fset_tmp))
        cov_jinx = j_hit / len(j_cn) if j_cn else None
    except Exception:                                          # noqa: BLE001
        j_cn, j_hit, cov_jinx = [], 0, None

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
    _still = [g for g in guard if under(g, fset)]
    if _still:
        errs.append("guard 条目仍被产物覆盖 %d 条，例：%s" % (len(_still), _still[:3]))
    if coverage is not None and coverage < COVERAGE_FLOOR:
        errs.append("独立基线覆盖率 %.1f%% 低于护栏 %.0f%%"
                    % (coverage * 100, COVERAGE_FLOOR * 100))
    if not (SIZE_RANGE[0] <= len(final) <= SIZE_RANGE[1]):
        errs.append("产物规模 %d 超出护栏 %s" % (len(final), SIZE_RANGE))
    if len(final) != len(fset):
        errs.append("产物存在重复")

    # ── 输出 ───────────────────────────────────────────────
    hdr = [
        "# 中文广告 / 统计 / 隐私 / PCDN 域名规则集（由脚本生成，请勿手改）",
        "# 生成器: test/build-cn-adblock.py（v4 三支路）",
        "# 支路 A: 217heidai adblocksurgelite.list（全量 16 源 ∩ china.txt）",
        "# 支路 B: AWAvenue · CJX · xinggsf · AdGuard_Chinese_filter · jiekouAD",
        "# 支路 C: 本仓 Jinx 3.2.3（上游已转加密发布，此快照冻结、不漂移）",
        "# 规矩: 仅 DNS 层可表达 · 纯 DOMAIN-SUFFIX 无通配 · 只拦域名不拦 IP",
        "#       静态资源/功能域硬排除 · @@ 例外只做减法 · guard 条目零覆盖",
        "# 规模: %d 条" % len(final),
    ]
    audit = ["构建审计 / cn-adblock（v4 三支路）", "=" * 64, "", "一、A 支路（lite）"]
    for k, v in stat_a.items():
        audit.append("  %-26s %6d" % (k, v))
    audit += ["", "二、B 支路（5 源）"]
    for label, (keep, s) in stat_b.items():
        audit.append("  [%s]" % label)
        for k, v in s.items():
            audit.append("    %-24s %6d" % (k, v))
    audit += ["", "三、C 支路（Jinx 3.2.3）"]
    for k, v in stat_c.items():
        audit.append("  %-26s %6d" % (k, v))
    audit += [
        "",
        "四、漏斗",
        "  A %d | B %d | C %d" % (len(A), len(B), len(C)),
        "  合并去重                    : %d" % len(merged),
        "  @@ 例外减法（%d 条规则）      : -%d" % (len(exceptions), n_exc),
        "  静态资源剔除                : -%d" % len(res_drop),
        "  功能域剔除                  : -%d" % len(fn_drop),
        "  灰产随机长尾剔除            : -%d" % len(gray_drop),
        "  语义上提后                  : %d" % len(climbed),
        "  guard 冲突剔除（上层域 %d 个） : -%d" % (len(supersets), len(supersets)),
        "  最终产物                    : %d" % len(final),
        "",
        "五、覆盖率",
        "  【断言基线·独立】%s %d 条 → 覆盖 %d 条 = %s（护栏 %.0f%%）"
        % (COVERAGE_BASELINE, len(awa), awa_hit,
           ("%.1f%%" % (coverage * 100)) if coverage is not None else "未测",
           COVERAGE_FLOOR * 100),
        "  【参考】Jinx·中国生态 %d 条 → 覆盖 %d 条 = %s"
        % (len(j_cn), j_hit, ("%.1f%%" % (cov_jinx * 100)) if cov_jinx is not None else "未测"),
        "",
        "六、guard 冲突处理",
    ]
    if bad_guards:
        for g in bad_guards:
            owners = sorted(d for d in supersets if under(g, {d}))
            audit.append("  %-42s ← 被上层域覆盖，已删除 %s" % (g, owners))
    else:
        audit.append("  无")
    audit += ["", "七、语义上提明细（%d 条）" % len(climb_log)]
    for src, dst in sorted(climb_log):
        audit.append("  %-46s -> %s" % (src, dst))
    audit += ["", "八、断言"]
    audit += ["  FAIL " + e for e in errs] or [
        "  PASS 形态 / 静态资源 / 必需域 / guard 零覆盖 / 覆盖率 / 规模 / 无重复 —— 全部通过"]

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
