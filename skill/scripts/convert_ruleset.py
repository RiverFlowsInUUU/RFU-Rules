#!/usr/bin/env python3
"""把第三方域名规则源转换为 mihomo / Surge / sing-box 可用格式。

用法（本仓 RFU-Rules 的实况；换别的源只改 --src 即可）:
  # 拦截集：源已是纯域名列表（build_ads.py 的产物）
  python convert_ruleset.py --src build/ads --out . --naming repo \
      --fixed ads-src.txt --tag ads --mode suffix \
      --label "upstream/(A+B+C)" --extra custom-ads.list

  # 放行集：上游白名单瘦身（guard = 只保留真正会被黑名单误杀的条目）
  python convert_ruleset.py --src upstream/jinx-3.2.3 --out . --naming repo \
      --fixed whitelist.txt --wild whitelist_wildcard.txt --tag direct --mode exact \
      --guard-against-fixed blacklist.txt --guard-against-wild blacklist_wildcard.txt \
      --extra-white custom-direct.list

  # 语义开关
  --mode suffix (默认) 普通条目 => DOMAIN-SUFFIX, 复刻 Jinx 等 DNS 过滤器的"域名+全部子域"语义
  --mode exact           普通条目 => DOMAIN, 仅精确匹配

  # 自定义追加(让手工补的规则在上游更新后依然存活)
  --extra ./custom-ads.list
      把该文件里的域名并入条目池末尾, 再参与 guard 过滤, 与上游条目同等对待。
      上游没有、但你需要拦的域名请写在这里, 而不是手改 mihomo-*.yaml(重跑即被覆盖)。

  --extra-white ./custom-direct.list
      直连域, 追加在 guard 之后, 强制 DOMAIN-SUFFIX, 不参与任何裁剪。
      上游没放行、但实测必须直连的功能域写在这里(写 *.x.com 即放行 x.com 及全部子域)。

  # 表头 `# source:` 的文案（默认取 --src 的值）
  # 源目录是临时/中间路径时（如 build/ads）用它，别让内部路径写进用户会下载的产物。
  --label "upstream/(A+B+C)"

  # 输出命名
  --naming classic (默认)  mihomo-<tag>-classical.yaml / surge-<tag>-ruleset.list
  --naming repo             mihomo-<tag>.yaml / surge-<tag>.list
                            (本仓用这个：文件名即订阅地址，稳定可引用)

产出:
  mihomo-<tag>-classical.yaml   behavior: classical, format: yaml, 100% 保真
  surge-<tag>-ruleset.list      Surge RULE-SET, 100% 保真
  sing-box-<tag>(-classical).json  sing-box rule-set source 格式, 100% 保真

后缀约定(2026-09-22 修正):
  mihomo 侧一律 .yaml, 内容是顶层 payload 列表。依据: 官方文档 rule-providers 的
  format "可选 yaml/text/mrs, 默认 yaml" —— 即 .yaml 才是默认路径, .list 反而
  需要显式写 format: text。社区规则仓库(mihomo 侧)也一律 .yaml / .mrs。
  .list 是 Surge/Quantumult 的惯例: mihomo 侧沿用会让抄配置的人要么漏写 format
  (默认按 yaml 解析 -> 报错或空规则), 要么被迫写一条多余的 format: text。
  Surge 侧维持 .list 不变。

sing-box 侧约定(2026-09-28 新增, 依据官方文档 rule-set 页, 内核 1.14.2):
  格式为 rule-set 的 source 格式(JSON), 不用二进制 .srs —— 远程规则集
  format: "source" 即可直接消费 JSON, 无需本地编译。
  * 顶层 {"version": 5, "rules": [...]}: version 5 是 1.14.0 引入的当前格式
    版本(新增 package_name_regex 规则项); 只用 domain 族老字段, 1.14 内核
    全部接受。
  * 扩展名用 .json: 官方文档明确 format 字段 "Optional when path or url
    uses json or srs as extension", .json 即 source 格式的约定扩展名。
  * 域名语义(实证 sagernet/sing common/domain/matcher.go 的 trie 实现):
    - domain_suffix: ["example.com"]  => example.com 自身 + 全部子域,
      域段级边界(aexample.com 不命中) —— 与 mihomo DOMAIN-SUFFIX 等价;
      前导点写法 ".example.com" 才是"仅子域、不含自身", 我们不用它。
    - domain: ["example.com"]         => 仅精确, 不继承子域 —— 白名单用。
    - domain_regex: ["^...$"]         => Go RE2 正则, 与 mihomo 的
      DOMAIN-REGEX 同语法, 中缀通配的转换式可直接复用。
  * 单条 rules 项内 domain_suffix / domain_regex 等域名族字段互为 OR,
    不同 rules 项之间也是 OR —— 全部条目放同一项即可。
  * source JSON 不支持注释, strict 解析不允许多余字段: 元数据(来源/条数)
    不写进文件, 只打印到 stdout。

语义要点(踩过的坑, 见 SKILL.md):
  * 黑名单类规则源(Jinx)通常按"域名+子域"拦截, 必须用 --mode suffix。
    用 DOMAIN 精确匹配会漏掉所有未显式列出的子域。
  * 白名单类规则源通常只做精确放行(实测 Jinx: 白名单含 qq.com, 但 sdk.e.qq.com 仍被拦),
    必须用 --mode exact 且放在 REJECT 之前; 若误用 suffix, 会整片放行广告域。
"""
import argparse
import collections
import json
import pathlib
import re


def read_text(src):
    """只读本地文件。

    ⚠️ 这里曾有一条「src 是 http(s) 就从网上拉」的分支，2026-10-27 删除。
    两条原因：
      ① 它是**不可达的死代码** —— 所有调用方传进来的都是 pathlib.Path，
         而 `Path('https://x/y')` 会被折叠成 `https:/x/y`，永远进不了那个分支；
      ② 它和本仓的铁律「构建只读 upstream/，不联网；唯一联网入口是
         freeze_upstream.py」直接矛盾。死代码也是承诺的一部分：读者看到它，
         就会以为"写 --src https://… 也能用"，而那恰好会毁掉"产物可复现"。
    要更新上游，请走 freeze_upstream.py —— 它会让改动留在 git diff 里。
    """
    return pathlib.Path(src).read_text(encoding='utf-8', errors='replace')


def load_entries(path):
    out = []
    for line in read_text(path).splitlines():
        line = line.strip().lstrip('-').strip()
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        out.append(line)
    return out


def host_of(entry):
    """从 https://host/path?q 里取出 host; 非 URL 返回 None。"""
    m = re.match(r'^https?://([^/?#]+)', entry, re.I)
    return m.group(1).lower().split(':')[0] if m else None


def classify(entry):
    """exact / suffix(*.x) / glob(含中缀星) / url"""
    if '://' in entry:
        return 'url'
    if '*' not in entry and '?' not in entry:
        return 'exact'
    if entry.startswith('*.') and not re.search(r'[*?]', entry[2:]):
        return 'suffix'
    return 'glob'


def glob_to_regex(g):
    return '^' + re.escape(g).replace(r'\*', '.*').replace(r'\?', '.') + '$'


def dedup(seq):
    seen, out = set(), []
    for x in seq:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out


def singbox_json(sb_suffix, sb_domain, sb_regex):
    """把 sing-box 条目包装成 rule-set source 格式(version 5)。

    单条 rules 项内域名族字段互为 OR —— 三类条目并排放同一项,
    任一命中即命中, 与 mihomo / Surge 逐条规则的语义一致(三端同源)。
    空字段整体省略(空数组会被 strict 解析拒绝)。
    """
    rule = {}
    if sb_domain:
        rule['domain'] = sb_domain
    if sb_suffix:
        rule['domain_suffix'] = sb_suffix
    if sb_regex:
        rule['domain_regex'] = sb_regex
    doc = {'version': 5, 'rules': [rule]}
    return json.dumps(doc, ensure_ascii=False, indent=2) + '\n'


def mihomo_yaml(header, rules):
    """把规则行包装成 mihomo rule-provider 的 YAML 形态(顶层 payload 列表)。

    每项用单引号包裹: 规则含 DOMAIN-REGEX 的正则(形如 ^p.*\\-ad\\.x\\.com$),
    单引号是 YAML 里唯一"完全字面"的写法 —— 双引号会把 \\ 当转义序列吃掉,
    裸写则要赌内容里没有 : # 之类的元字符(现在没有, 但上游更新不可控)。
    单引号内只需把 ' 写成 ''。
    """
    body = ''.join("  - '%s'\n" % r.replace("'", "''") for r in rules)
    return header + 'payload:\n' + body


def build_blacklist_matcher(fixed_paths, wild_paths):
    """构造黑名单碰撞检测器: 判断某白名单条目是否会被这套黑名单误杀。

    命中判定(从严到宽):
      exact  白名单条目 == 黑名单精确条目
      glob   白名单条目被黑名单通配规则匹配 (Jinx 的 * 跨点)
      sub    白名单条目是黑名单精确条目的子域 (黑名单按后缀拦截, 故计入)
    """
    exact, globs = set(), []
    for p in (fixed_paths or []):
        for line in load_entries(p):
            e = line.lstrip('.').lower()
            if '://' not in e and e:
                exact.add(e)
    for p in (wild_paths or []):
        for line in load_entries(p):
            e = line.lstrip('.').lower()
            if '://' not in e and e:
                globs.append((e, re.compile(glob_to_regex(e))))

    def collides(entry):
        e = entry.lstrip('.').lower()
        if e.startswith('*.'):
            e = e[2:]
        if e in exact:
            return 'exact'
        for pat, rx in globs:
            if rx.match(e):
                return 'glob:' + pat
        for b in exact:
            if e.endswith('.' + b):
                return 'sub:' + b
        return None

    return collides


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='源目录或文件路径')
    ap.add_argument('--label', default=None,
                    help='写进产物表头 `# source:` 的文案（默认取 --src 的值）。'
                         '源是临时/中间目录时用它，避免内部路径出现在用户下载的文件里')
    ap.add_argument('--out', required=True, help='输出目录')
    ap.add_argument('--fixed', help='精确域名文件名(在 src 目录下)')
    ap.add_argument('--wild', help='通配域名文件名(在 src 目录下)')
    ap.add_argument('--tag', default='rules', help='输出文件标签, 如 ads / white')
    ap.add_argument('--naming', choices=['classic', 'repo'], default='classic',
                    help='输出命名: classic=mihomo-<tag>-classical.yaml / surge-<tag>-ruleset.list; '
                         'repo=mihomo-<tag>.yaml / surge-<tag>.list (与已托管仓库的文件名一致, 便于直接覆盖)')
    ap.add_argument('--mode', choices=['suffix', 'exact'], default='suffix',
                    help='普通条目的匹配语义; 黑名单用 suffix, 白名单用 exact')
    ap.add_argument('--extra', nargs='*',
                    help='手工追加的域名文件(相对 cwd, 或相对 --src 目录)。'
                         '内容并入条目池末尾, 参与后续 guard 过滤。'
                         '用途: 让"自己补的规则"在上游更新、重新生成后依然存活')
    ap.add_argument('--extra-white', nargs='*',
                    help='手工追加的直连域名文件(路径解析同 --extra)。'
                         '在 guard 之后追加, 强制 DOMAIN-SUFFIX, 不参与任何裁剪。'
                         '用途: 上游未放行、但实测必须直连的功能域')
    ap.add_argument('--guard-against-fixed', nargs='*', help='黑名单精确域名文件, 给出则只保留会被其误杀的白名单条目')
    ap.add_argument('--guard-against-wild', nargs='*', help='黑名单通配域名文件, 同上')
    args = ap.parse_args()

    src = pathlib.Path(args.src)
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    entries = []
    for name in [args.fixed, args.wild]:
        if not name:
            continue
        p = src / name if src.is_dir() else pathlib.Path(name)
        entries.extend(load_entries(p))
    entries = dedup(entries)

    extra_names = []
    if args.extra:
        added = []
        for name in args.extra:
            p = pathlib.Path(name)
            if not p.exists() and src.is_dir() and (src / name).exists():
                p = src / name
            if not p.exists():
                print('!! --extra 文件不存在, 已跳过: %s' % name)
                continue
            got = load_entries(p)
            added.extend(got)
            extra_names.append('%s(%d)' % (pathlib.Path(name).name, len(got)))
        before = len(entries)
        entries = dedup(entries + added)          # 追加项落在末尾, 便于 diff 校验
        print('追加(--extra): %s, 新增 %d 条, 合计 %d 条'
              % (', '.join(extra_names) or '(无)', len(entries) - before, len(entries)))

    if args.guard_against_fixed or args.guard_against_wild:
        def _abs(names):
            if not names:
                return []
            return [str(src / n) if src.is_dir() else n for n in names]
        collides = build_blacklist_matcher(
            _abs(args.guard_against_fixed), _abs(args.guard_against_wild))
        before = len(entries)
        kept = [(e, collides(e)) for e in entries]
        kept = [k for k in kept if k[1]]
        print('guard 模式: %d 条白名单 -> %d 条真正冲突(需保留), 裁掉 %d 条'
              % (before, len(kept), before - len(kept)))
        entries = [k[0] for k in kept]

    # --extra-white: 直连域, 追加在 guard 之后, 不参与任何裁剪
    forced, extra_white_names = [], []
    if args.extra_white:
        for name in args.extra_white:
            p = pathlib.Path(name)
            if not p.exists() and src.is_dir() and (src / name).exists():
                p = src / name
            if not p.exists():
                print('!! --extra-white 文件不存在, 已跳过: %s' % name)
                continue
            got = load_entries(p)
            extra_white_names.append('%s(%d)' % (pathlib.Path(name).name, len(got)))
            forced.extend(got)
        forced = dedup(forced)
        print('追加(--extra-white): %s, 共 %d 条(强制 DOMAIN-SUFFIX, 不参与裁剪)'
              % (', '.join(extra_white_names) or '(无)', len(forced)))

    counter = collections.Counter()
    mihomo_classical, surge_ruleset = [], []
    sb_suffix, sb_domain, sb_regex = [], [], []
    recovered = []

    for e in entries:
        kind = classify(e)
        counter[kind] += 1
        if kind == 'url':
            h = host_of(e)
            if h:
                recovered.append(h)
                e, kind = h, 'exact'
            else:
                continue
        if kind == 'exact':
            if args.mode == 'suffix':
                mihomo_classical.append('DOMAIN-SUFFIX,' + e)
                surge_ruleset.append('DOMAIN-SUFFIX,' + e)
                sb_suffix.append(e)
            else:
                mihomo_classical.append('DOMAIN,' + e)
                surge_ruleset.append('DOMAIN,' + e)
                sb_domain.append(e)
        elif kind == 'suffix':
            base = e[2:]
            mihomo_classical.append('DOMAIN-SUFFIX,' + base)
            surge_ruleset.append('DOMAIN-SUFFIX,' + base)
            sb_suffix.append(base)
        else:
            mihomo_classical.append('DOMAIN-REGEX,' + glob_to_regex(e))
            surge_ruleset.append('DOMAIN-WILDCARD,' + e)
            sb_regex.append(glob_to_regex(e))

    # --extra-white 条目: 强制 DOMAIN-SUFFIX, 追加在末尾(与已有条目去重)
    if forced:
        seen = set(r.lower() for r in mihomo_classical)
        dup = 0
        for e in forced:
            base = e[2:] if e.startswith('*.') else e.lstrip('.')
            line = 'DOMAIN-SUFFIX,' + base
            if line.lower() in seen:
                dup += 1
                continue
            seen.add(line.lower())
            mihomo_classical.append(line)
            surge_ruleset.append(line)
            sb_suffix.append(base)
        if dup:
            print('  (--extra-white 中 %d 条与已有条目重复, 已跳过)' % dup)

    header = ('# auto-converted by adblock-ruleset-port\n'
              '# source: %s\n# mode: %s\n# entries: %d\n'
              % (args.label or args.src, args.mode, len(mihomo_classical)))
    if extra_names:
        header += '# extra: %s\n' % ', '.join(extra_names)
    if extra_white_names:
        header += '# extra-white: %s\n' % ', '.join(extra_white_names)
    if args.naming == 'repo':
        names = ('mihomo-%s.yaml' % args.tag, 'surge-%s.list' % args.tag,
                 'sing-box-%s.json' % args.tag)
    else:
        names = ('mihomo-%s-classical.yaml' % args.tag, 'surge-%s-ruleset.list' % args.tag,
                 'sing-box-%s-classical.json' % args.tag)
    sb_text = singbox_json(sb_suffix, sb_domain, sb_regex)
    sb_total = len(sb_suffix) + len(sb_domain) + len(sb_regex)
    outputs = [
        (names[0], mihomo_yaml(header, mihomo_classical), len(mihomo_classical)),
        (names[1], header + '\n'.join(surge_ruleset) + '\n', len(surge_ruleset)),
        (names[2], sb_text, sb_total),
    ]
    for name, text, n in outputs:
        # newline='' 关掉 Python 的通用换行转换 —— 否则 write_text 会把 \n
        # 按平台写成 os.linesep：Windows 出 CRLF、Linux 出 LF，**同一脚本
        # 跨平台产出不同字节**，产物在 CI（Linux）上重跑必然与 Windows
        # 提交的版本不一致。显式钉死 LF，产出才可复现。
        # （实测 2026-10-04：仓库内 mihomo / Surge 四份产物原为 CRLF、
        #   sing-box 两份为 LF，正是该转换造成的分裂；CI 第 6 段当场判负。）
        (out / name).write_text(text, encoding='utf-8', newline='')
        print('  %-32s %6d 行' % (name, n))

    print('\n分类: exact=%d suffix=%d glob=%d url=%d (其中 %d 条 URL 已还原为 host)'
          % (counter['exact'], counter['suffix'], counter['glob'], counter['url'], len(recovered)))
    print('语义: --mode %s => 普通条目输出为 %s'
          % (args.mode, 'DOMAIN-SUFFIX' if args.mode == 'suffix' else 'DOMAIN'))
    print('sing-box: domain=%d domain_suffix=%d domain_regex=%d (version 5, source 格式)'
          % (len(sb_domain), len(sb_suffix), len(sb_regex)))


if __name__ == '__main__':
    main()
