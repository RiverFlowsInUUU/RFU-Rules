#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""规则集一致性断言 —— 守「产物只能是生成物、且三端等价」这条立仓之本。

本仓自 2026-10-27 起由「上游格式转换镜像」转为「合成规则集」：
ads 由三支路（217heidai lite · 5 个中文源 · Jinx 3.2.3 明文快照）合成，
direct 仍由上游白名单瘦身而来。两者都只读 `upstream/`，**构建不联网**。

承诺相应改成三条，全部可判定：
  ① 三平台内容等价 —— 同一域名集在 mihomo / Surge / sing-box 三端逐条一致；
  ② 产物 == 生成链重跑结果 —— 防手改产物、防改了源头忘了重跑；
  ③ 条数与文档声明一致 —— 防「产物变了、文档还写着旧数」。

⚠️ 不再承诺「规则一条不增不减」：ads 是合成集，与任何单一上游都不等长。
   那条承诺只对 direct 成立（上游白名单瘦身后的 49 条）。

退出码（全仓统一四态，勿改语义）:
  0  全部断言通过
  1  存在判负项
  2  前置环境不达标（仓根不对 / 必需文件缺失，判据无法执行）
  3  SKIP（依赖项缺失，未验证 ≠ 绿）

用法:
  python skill/tests/verify_products.py          # 在仓根执行
  python skill/tests/verify_products.py --root . # 显式指定仓根

断言清单（16 段，执行顺序）:
  1. 六份产物存在且非空
  2. 三格式条数一致（ads 三份互等 / direct 三份互等）
  3. 跨格式语义等价（归一化后逐条比对，不是只比条数）
  4. 文件头 # entries 自述 == 实际条数
  5. 文档声明的条数 == 文件实际条数（README / DetailsReadme）
 5b. 文档声明的**上游版本号与快照日期** == upstream/jinx-3.2.3/version.json
     （上游已冻结，本段防「产物换了新版、徽章还写着旧版本」这类门面失真。）
  6. 产物 == 生成链重跑的结果（ads 先跑 build_ads.py，再跑 convert_ruleset.py）
 6b. 冻结上游自述自检：version.json 自述计数 == 源文件实际（挡「快照被裁过 /
     只取到半个」），并显式列出 direct 应有的条数。
 6c. 白名单瘦身留痕（WHITELIST-SLIM.md）== 独立复算 —— 摘要三项（总/留/裁）
     + 保留集合、裁掉集合逐条相等。判据对象是「生成物」，不是上游自述，
     故与 6b 分段（v4 审查 4.2：段标与内容漂移，本仓第三次踩这类坑）。
  7. 源头文件（custom-*.list）的表头 extra 声明与实际条数一致
  8. 文案规范：emoji 只出现在行首 + 密度下限
  9. 行尾符与 BOM（BOM 硬判负；行尾只做同族一致性与事实播报）
 10. 平台清单齐备 —— 面向外部的说明（仓库简介来源 / README / DetailsReadme / SKILL）
     必须列全所有平台。实证：sing-box 曾从仓库简介里漏了一周无人发现。
 11. 表格内 emoji 宽度一致 —— 同一表格的 emoji 码位数必须相同，
     否则带 U+FE0F 的那个会占两格、该行在宽字符字体下错位。
 12. 白名单 × 拦截集重叠清单（OVERLAP.md）与当前产物一致 —— 独立复算，
     防「清单写的和产物算的不是一回事」。这是本仓唯一对外可见的风险清单。
 13. 段号引用与段数声明 == 真实段标/段数 —— ①「第 N 段」的 N 必须在段标里
     （数字限两位，与②护栏对齐）；②声明位文件里的裸「N 段」必须等于编号段总数。
     两类都是手写常量、随拆分漂移，此类失真已发生五次且前四次全靠外部审查抓出
     （v5 3.3 提议 · v6 2.1 补②型 · v7 收窄②型范围并对齐护栏）。

闸门自身可信度由 skill/tests/selftest_negative.py 保证：它在临时副本仓里
制造 18 种典型错误，要求本脚本逐一判负 —— 防止闸门退化成「永远绿的空操作」。
其中每条负样本都经过「拆掉对应判据后必须翻红」的独立性反证，确保它是真的在
测那一盘守卫，而不是靠另一次判负顺带被「抓到」。

第 8 段的 emoji 判定按「emoji 之前只许出现结构字符（标题 / 列表 / 引用标记、
表格竖线、`[`、树形框线、缩进）」—— 这条口径来自 2026-09-22 用户要求，
SKILL.md 第 280 行引用本脚本为该断言的实现。
"""
import argparse
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Windows 中文环境（ACP=936）下子进程 stdout 走管道时 Python 用 cp936 编码，
# print 一个非 GBK 字符（✅/❌/⚠️）就 UnicodeEncodeError 并以退出码 1 结束 ——
# 而 1 恰是本仓「判负」的码，崩溃会被读成「判负」。必须在任何输出前兜底。
for _s in ('stdout', 'stderr'):
    _f = getattr(sys, _s, None)
    if _f is not None and hasattr(_f, 'reconfigure'):
        try:
            _f.reconfigure(encoding='utf-8', errors='replace')
        except (ValueError, OSError):
            pass

EXIT_PASS, EXIT_FAIL, EXIT_ENV, EXIT_SKIP = 0, 1, 2, 3

# 六份产物的固定名（与 convert_ruleset.py --naming repo 一致）
PRODUCTS = {
    'ads': {
        'mihomo': 'mihomo-ads.yaml',
        'surge': 'surge-ads.list',
        'singbox': 'sing-box-ads.json',
    },
    # 2026-10-04 由 `direct` 改名为 `direct`：与源头 `custom-direct.list`
    # 及「白名单 = 直连」的语义对齐（历史名 `direct` 是「白名单守卫」的遗留）。
    # ⚠️ 改名 = 订阅地址变更，旧地址 404（用户已确认接受）。
    'direct': {
        'mihomo': 'mihomo-direct.yaml',
        'surge': 'surge-direct.list',
        'singbox': 'sing-box-direct.json',
    },
}

# 生成命令的固定参数（与 skill/scripts/regen.sh 一致）。
#
# ⚠️ `--src` 的写法会**原样进产物表头**（除非给了 `--label`），所以这里刻意
#    把 `--src` 从参数表里移出，单独管理：
#      · direct：`--src upstream/jinx-3.2.3` 既是路径也是表头文案，直接用它；
#      · ads   ：源是构建器的**临时**产物，路径每次不同，故必须配 `--label`
#                把表头钉成固定文案，否则「可复现」会把路径差异误报成内容差异。
#    ⚠️ 别为了「统一」给 direct 加 `./` 前缀：表头会跟着变，第 6 段立刻判负。
SRC_OF = {'ads': None, 'direct': 'upstream/jinx-3.2.3'}   # ads 的 src 是临时目录
# 表头文案不在这里写死 —— 由 build_ads.py 从 upstream/version.json 派生并写入
# build/ads/label.txt，本脚本与 regen.sh 都读同一份。两处各写一遍必然漂移，
# 而漂移会被第 6 段当成「产物不可复现」报错（见 seg_reproducible）。
REGEN = {
    # ads 的输入是 build_ads.py 的产物（ads-src.txt），本表只描述「最后一步」；
    # 完整生成链见 regen.sh（先 build_ads.py 再本表）。
    'ads': ['--fixed', 'ads-src.txt',
            '--tag', 'ads', '--mode', 'suffix', '--extra', 'custom-ads.list'],
    'direct': ['--fixed', 'whitelist.txt', '--wild', 'whitelist_wildcard.txt',
               '--tag', 'direct', '--mode', 'exact',
               '--guard-against-fixed', 'blacklist.txt',
               '--guard-against-wild', 'blacklist_wildcard.txt',
               '--extra-white', 'custom-direct.list'],
}
SRC_DIR = 'upstream/jinx-3.2.3'
MANIFEST = 'upstream/manifest.json'

# sing-box 字段名 -> 规范化类型名（与 mihomo / Surge 对齐）
SB_FIELD = {
    'domain': 'DOMAIN',
    'domain_suffix': 'DOMAIN-SUFFIX',
    'domain_keyword': 'DOMAIN-KEYWORD',
    'domain_regex': 'DOMAIN-REGEX',
}
# Surge 独有写法 -> mihomo 等价类型
SURGE_ALIAS = {
    'HOST': 'DOMAIN',
    'HOST-SUFFIX': 'DOMAIN-SUFFIX',
    'HOST-KEYWORD': 'DOMAIN-KEYWORD',
    'DOMAIN-WILDCARD': 'DOMAIN-REGEX',
    'DOMAIN-SET': 'DOMAIN-SUFFIX',
}


class Report:
    def __init__(self):
        self.rows = []          # (ok, section, msg)

    def judge(self, cond, section, msg, detail=''):
        self.rows.append((bool(cond), section, msg, detail))
        return bool(cond)

    def section(self, name):
        self.rows.append((None, name, '', ''))

    @property
    def failed(self):
        return [r for r in self.rows if r[0] is False]

    def render(self):
        out = []
        sec = '?'
        for ok, s, msg, detail in self.rows:
            if ok is None:
                sec = s
                out.append('')
                out.append(f'── {s} ' + '─' * max(0, 56 - len(s)))
                continue
            mark = '✅' if ok else '❌'
            out.append(f'  {mark} {msg}')
            if detail and not ok:
                for line in str(detail).splitlines():
                    out.append(f'       {line}')
        return '\n'.join(out)


# ---------------------------------------------------------------- 解析

def _strip_quotes(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "'\"":
        s = s[1:-1]
    return s.strip()


def parse_mihomo(path):
    """mihomo rule-provider：顶层 payload 列表，条目形如 `  - 'DOMAIN,x.com'`。"""
    out = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        s = line.strip()
        if s.startswith('- '):
            out.append(_strip_quotes(s[2:]))
    return out


def parse_surge(path):
    """Surge RULE-SET：一行一条，`#` 开头为注释。"""
    out = []
    for line in Path(path).read_text(encoding='utf-8').splitlines():
        s = line.strip()
        if s and not s.startswith('#') and not s.startswith('//'):
            out.append(s)
    return out


def parse_singbox(path):
    """sing-box rule-set source JSON：{"version":5,"rules":[{字段: [...]}]}。

    返回扁平化的 (规范化类型, 值) 列表。
    """
    doc = json.loads(Path(path).read_text(encoding='utf-8'))
    out = []
    for rule in doc.get('rules', []):
        for field, values in rule.items():
            kind = SB_FIELD.get(field)
            if kind is None:
                continue
            for v in values:
                out.append((kind, str(v)))
    return out


def normalize_rule(entry, alias):
    """把一行规则归一化成 (类型, 小写值)，用于跨格式比对。

    值本身不做语义化（正则 vs 通配的差异在 compare() 里单独处理）。
    """
    parts = [p.strip() for p in entry.split(',')]
    kind = parts[0].upper()
    kind = alias.get(kind, kind)
    val = parts[1].lower() if len(parts) > 1 else ''
    return (kind, val)


def glob_to_regex(g):
    """与 convert_ruleset.py 的 glob_to_regex 保持同一实现（勿各写一套）。"""
    return '^' + re.escape(g).replace(r'\*', '.*').replace(r'\?', '.') + '$'


def canon_set(rules, alias, wildcard_to_regex=False):
    """归一化集合。wildcard_to_regex=True 时把 Surge DOMAIN-WILDCARD 转成正则形态，
    以便与 mihomo 的 DOMAIN-REGEX 逐条对上（否则类型不同会被误判成差异）。"""
    out = set()
    for e in rules:
        kind, val = normalize_rule(e, alias)
        if wildcard_to_regex and kind == 'DOMAIN-REGEX' and not val.startswith('^'):
            val = glob_to_regex(val)
        out.add((kind, val))
    return out


# ---------------------------------------------------------------- 各段断言

def seg_products_exist(root, rep):
    rep.section('1. 产物存在性')
    for fam, files in PRODUCTS.items():
        for kind, name in files.items():
            p = root / name
            ok = p.is_file() and p.stat().st_size > 0
            rep.judge(ok, 'prod', f'{name} 存在且非空' if ok else f'{name} 缺失或为空',
                      '产物是订阅地址的落点，缺失会让客户端拉取 404')


def seg_counts_consistent(root, rep, counts):
    rep.section('2. 三格式条数一致')
    for fam, files in PRODUCTS.items():
        vals = {k: counts[fam][k] for k in ('mihomo', 'surge', 'singbox')}
        uniq = set(vals.values())
        rep.judge(len(uniq) == 1,
                  'count',
                  f'{fam}: mihomo {vals["mihomo"]} / surge {vals["surge"]} / sing-box {vals["singbox"]}'
                  + ('  一致' if len(uniq) == 1 else '  不一致'),
                  '三平台必须内容等价 —— 本仓承诺「规则一条不增不减」')


def seg_cross_format(root, rep):
    rep.section('3. 跨格式语义等价')
    families = {
        'ads': (root / PRODUCTS['ads']['mihomo'],
                root / PRODUCTS['ads']['surge'],
                root / PRODUCTS['ads']['singbox']),
        'direct': (root / PRODUCTS['direct']['mihomo'],
                        root / PRODUCTS['direct']['surge'],
                        root / PRODUCTS['direct']['singbox']),
    }
    for fam, (pm, ps, pb) in families.items():
        mi = parse_mihomo(pm)
        su = parse_surge(ps)
        sb = parse_singbox(pb)
        A = canon_set(mi, {})
        B = canon_set(su, SURGE_ALIAS, wildcard_to_regex=True)
        C = set((k, v.lower()) for k, v in sb)

        # mihomo vs sing-box：两侧都能表达精确语义，应逐条完全相等
        only_a, only_c = sorted(A - C), sorted(C - A)
        rep.judge(not only_a and not only_c, 'cross',
                  f'{fam}: mihomo vs sing-box 逐条等价（{len(A)} 条）'
                  if not (only_a or only_c) else
                  f'{fam}: mihomo vs sing-box 有差异（仅 mihomo {len(only_a)} / 仅 sing-box {len(only_c)}）',
                  '\n'.join([f'仅 mihomo: {x}' for x in only_a[:4]] +
                            [f'仅 sing-box: {x}' for x in only_c[:4]]))

        # mihomo vs surge：通配已统一成正则形态
        only_ab, only_ba = sorted(A - B), sorted(B - A)
        rep.judge(not only_ab and not only_ba, 'cross',
                  f'{fam}: mihomo vs surge 逐条等价（{len(A)} 条）'
                  if not (only_ab or only_ba) else
                  f'{fam}: mihomo vs surge 有差异（仅 mihomo {len(only_ab)} / 仅 surge {len(only_ba)}）',
                  '\n'.join([f'仅 mihomo: {x}' for x in only_ab[:4]] +
                            [f'仅 surge: {x}' for x in only_ba[:4]]))


def seg_header_selfcount(root, rep, counts):
    rep.section('4. 文件头 # entries 自述')
    for fam, files in PRODUCTS.items():
        for kind in ('mihomo', 'surge'):
            p = root / files[kind]
            head = p.read_text(encoding='utf-8')[:400]
            m = re.search(r'^#\s*entries:\s*(\d+)\s*$', head, re.M)
            real = counts[fam][kind]
            if not m:
                rep.judge(False, 'hdr', f'{p.name}: 表头缺 # entries 行',
                          '产物表头契约由 convert_ruleset.py 输出，勿手改')
                continue
            rep.judge(int(m.group(1)) == real, 'hdr',
                      f'{p.name}: 自述 {m.group(1)} == 实际 {real}'
                      if int(m.group(1)) == real else
                      f'{p.name}: 自述 {m.group(1)} != 实际 {real}',
                      '表头自述与实际不符 = 产物被手改过，或改了源头没重跑')


def seg_doc_counts(root, rep, counts):
    """文档声明的条数必须等于文件实际条数。

    只在「当前状态描述」里找（订阅表 / 徽章），**不碰 CHANGELOG 等历史记录** ——
    历史条目写的是当时的条数，改了就是篡改历史。
    """
    rep.section('5. 文档条数声明 == 文件实际')
    readme = root / 'README.md'
    details = root / 'DetailsReadme' / 'DetailsReadme.md'

    # 5-a: README 订阅表里每份文件的条数单元格
    #
    # 表格有两种合法呈现形态（2026-10-04 起以形态 B 为主）：
    #   A 独立单元格：  | \`file.yaml\` | 3991 | 拦截 |
    #   B 内嵌链接：    | ... | [\`file.yaml\`](RAW_URL) \`3991\` | ... |
    #     形态 B 是向姊妹仓看齐的做法 —— 文件名本身就是指向 raw 地址的链接，
    #     读者右键「复制链接地址」即得订阅 URL，不必回头对照下方的地址块。
    # 判据不变：**文件名必须出现，且紧随其后的条数必须等于产物实际**。
    if readme.is_file():
        text = readme.read_text(encoding='utf-8')

        def readme_count_of(name):
            """返回 (匹配到的条数字符串, 形态) 或 (None, None)。"""
            nm = re.escape(name)
            # 形态 B：链接文本 + 紧随的条数
            m = re.search(r'\[`' + nm + r'`\]\([^)]+\)\s*`?(\d+)`?', text)
            if m:
                return m.group(1), 'B'
            # 形态 A：独立单元格
            m = re.search(r'\|\s*`' + nm + r'`\s*\|\s*(\d+)\s*\|', text)
            if m:
                return m.group(1), 'A'
            return None, None

        for fam, files in PRODUCTS.items():
            for kind, name in files.items():
                real = counts[fam][kind]
                got, shape = readme_count_of(name)
                if got is None:
                    rep.judge(False, 'doc', f'README: 订阅表缺 {name} 行',
                              '订阅表是使用者的选文件依据，六份文件都要列出')
                    continue
                rep.judge(int(got) == real, 'doc',
                          f'README 表 {name}: {got} == {real}（形态{shape}）'
                          if int(got) == real else
                          f'README 表 {name}: 声明 {got} != 实际 {real}',
                          '改了产物必须同步改文档条数')

        # 5-b: README 数据徽章（放行 = direct 条数，拦截 = ads 条数）
        badge = {'%E6%94%BE%E8%A1%8C': 'direct', '%E6%8B%A6%E6%88%AA': 'ads'}
        for enc, fam in badge.items():
            real = counts[fam]['mihomo']
            m = re.search(re.escape(enc) + r'-(\d+)%20', text)
            rep.judge(bool(m) and int(m.group(1)) == real, 'doc',
                      f'README 徽章 {fam}: {m.group(1) if m else "(缺)"} == {real}'
                      if m and int(m.group(1)) == real else
                      f'README 徽章 {fam}: 声明 {m.group(1) if m else "(缺)"} != 实际 {real}',
                      '徽章是门面读数，与实际不符会被读者当场看出')
        # 5-d: 能力矩阵里的「构成描述」—— 这类文字最容易被改判据时漏掉。
        # 实测：把「43 条精确 + 6 条后缀（含 5 条手工补充）」整体改错，旧闸门全绿。
        surge_lines = parse_surge(root / PRODUCTS['direct']['surge'])
        n_exact = sum(1 for e in surge_lines if e.upper().startswith('DOMAIN,'))
        n_suffix = sum(1 for e in surge_lines if e.upper().startswith('DOMAIN-SUFFIX,'))
        n_other = len(surge_lines) - n_exact - n_suffix
        manual = len([l for l in (root / 'custom-direct.list').read_text(encoding='utf-8').splitlines()
                      if l.strip() and not l.strip().startswith('#')])
        m = re.search(r'\|\s*✅ 放行\s*\|\s*\*\*(\d+) 条\*\*\s*\|\s*'
                      r'(\d+) 条精确 \+ (\d+) 条后缀（含 (\d+) 条手工补充）\s*\|', text)
        if not m:
            rep.judge(False, 'doc', 'README 能力矩阵：放行构成描述未命中（版式变了？）',
                      '这行写的是 direct 的构成，判据锚在它上面')
        else:
            got = tuple(int(x) for x in m.groups())
            want = (counts['direct']['mihomo'], n_exact, n_suffix, manual)
            rep.judge(got == want and n_other == 0, 'doc',
                      f'README 能力矩阵 放行构成: {got} == {want}'
                      if got == want and n_other == 0 else
                      f'README 能力矩阵 放行构成: 声明 {got} != 实际 {want}'
                      + (f'（另有 {n_other} 条非 DOMAIN/DOMAIN-SUFFIX 条目）' if n_other else ''),
                      '条数对了不代表构成对了 —— 精确/后缀/手补三项都要对上')
    else:
        rep.judge(False, 'doc', 'README.md 缺失', '对外交付必须写 README')

    # 5-e: SKILL 的预期读数。
    # ⚠️ 旧版只判「正则可解析」、不比数值 —— 实测把 9534/49 改成 9999/1，闸门仍 70/0 全绿。
    #    这是典型的「断言与被检对象不同构」：它证明版式没变，不证明数字是对的。
    sk = root / 'skill' / 'SKILL.md'
    if sk.is_file():
        stext = sk.read_text(encoding='utf-8')
        for pat, label in (
                (r'预期读数：`ads (\d+)` / `direct (\d+)`', 'SKILL 预期读数行'),
                (r'\|\s*现读数\s*\|\s*`ads (\d+)` / `direct (\d+)`\s*\|', 'SKILL 现读数行')):
            mm = re.search(pat, stext)
            if not mm:
                rep.judge(False, 'doc', f'{label}: 锚点未命中（版式变了？）',
                          'SKILL 的读数是人肉参照，锚点失效等于这行没人看')
                continue
            got = (int(mm.group(1)), int(mm.group(2)))
            want = (counts['ads']['mihomo'], counts['direct']['mihomo'])
            rep.judge(got == want, 'doc',
                      f'{label}: {got} == {want}' if got == want else
                      f'{label}: 声明 {got} != 实际 {want}',
                      '§SKILL 里的数字是照着产物写的，产物变了要同步改')
    else:
        rep.judge(False, 'doc', 'skill/SKILL.md 缺失', '面向 agent 的施工图必须存在')

    # 5-c: DetailsReadme 表格里的条数，以及「白名单怎么来的」推导式
    if details.is_file():
        dtext = details.read_text(encoding='utf-8')
        for fam, files in PRODUCTS.items():
            for kind, name in files.items():
                real = counts[fam][kind]
                nm = re.escape(name)
                m = (re.search(r'\[`' + nm + r'`\]\([^)]+\)\s*`?(\d+)`?', dtext)
                     or re.search(r'\|\s*`' + nm + r'`\s*\|[^|]*\|\s*(\d+)\s*\|', dtext))
                if m:
                    rep.judge(int(m.group(1)) == real, 'doc',
                              f'Details 表 {name}: {m.group(1)} == {real}'
                              if int(m.group(1)) == real else
                              f'Details 表 {name}: 声明 {m.group(1)} != 实际 {real}',
                              '同一读数在两个文档里必须一致')
        # 「共 N 条」这类汇总句
        real_w = counts['direct']['mihomo']
        for m in re.finditer(r'共\s*(\d+)\s*条', dtext):
            rep.judge(int(m.group(1)) == real_w, 'doc',
                      f'Details「共 {m.group(1)} 条」== {real_w}'
                      if int(m.group(1)) == real_w else
                      f'Details「共 {m.group(1)} 条」!= 白名单实际 {real_w}',
                      '白名单推导的结论数必须等于产物条数')
    else:
        rep.judge(False, 'doc', 'DetailsReadme/DetailsReadme.md 缺失', '下沉文档必须存在')


def seg_upstream_pin(root, rep, counts, repro_failed=0):
    """冻结上游自述自检：version.json 的计数必须等于源文件实际条数。

    上游自 3.2.4 起转加密发布，明文停在 3.2.3 —— 本仓把这份明文钉死成
    `upstream/jinx-3.2.3/`，作为支路 C 的输入，**不再跟随上游**。
    于是「拿旧版合并」这条风险整体消失，本段只剩一个职责：

        确认 `upstream/jinx-3.2.3/` 确实是一份**完整**的 3.2.3 明文快照 ——
        而不是被裁过、只取到半个、或掺了别的版本的文件。

    判据独立于第 6 段：version.json 自述的 domainBlacklistCount /
    domainWhitelistCount 必须等于源文件实际条数。源被裁过时，第 6 段照样能
    全绿（源与产物彼此自洽，只是两者都不可信），唯独本段能发现。

    另外把 direct 应有的条数显式写出来（上游白名单瘦身后的留存 + 手工追加），
    让失败原因一眼可读 —— 它不是新增守卫，第 6 段已蕴含它。
    """
    rep.section('6b. 冻结上游自述 == 源文件实际')
    src = root / SRC_DIR
    if not (src / 'version.json').is_file():
        rep.judge(False, 'pin', '缺 %s/version.json —— 无法判定冻结快照' % SRC_DIR,
                  '先跑 python skill/scripts/freeze_upstream.py；未验证 ≠ 绿')
        return

    ver = json.loads((src / 'version.json').read_text(encoding='utf-8'))
    version, date = ver['version'], ver['lastUpdate'][:10]

    def entries(name):
        out = []
        for line in (src / name).read_text(encoding='utf-8').splitlines():
            t = line.strip()
            if t and not t.startswith('#'):
                out.append(t)
        return out

    blk = len(entries('blacklist.txt')) + len(entries('blacklist_wildcard.txt'))
    wl = len(entries('whitelist.txt')) + len(entries('whitelist_wildcard.txt'))

    hint = (f'（注：第 6 段已判负 {repro_failed} 项，本条判负常与它同因）'
            if repro_failed else '')
    for field, label, actual in (('domainBlacklistCount', 'blacklist', blk),
                                 ('domainWhitelistCount', 'whitelist', wl)):
        declared = ver.get(field)
        rep.judge(declared == actual, 'pin',
                  (f'冻结快照计数 {label}: version.json {declared} == 源文件实际 {actual}'
                   if declared == actual else
                   f'冻结快照计数 {label}: version.json {declared} != 源文件实际 {actual}'),
                  '快照与上游官方自述不符 —— 可能被手工裁过、只取了半个、'
                  '或混入了其它版本的文件。此时产物再自洽也不可信。\n'
                  '修正：python skill/scripts/freeze_upstream.py 重取并更新 manifest' + hint)

    # direct 应有条数：上游白名单里会被黑名单误杀的部分 + 手工追加
    sys.path.insert(0, str(root / 'skill' / 'scripts'))
    from convert_ruleset import build_blacklist_matcher  # noqa: E402
    collides = build_blacklist_matcher(
        [str(src / 'blacklist.txt')], [str(src / 'blacklist_wildcard.txt')])
    wl_all = entries('whitelist.txt') + entries('whitelist_wildcard.txt')
    kept = sum(1 for e in wl_all if collides(e))
    n_custom = len([l for l in (root / 'custom-direct.list').read_text(encoding='utf-8').splitlines()
                    if l.strip() and not l.strip().startswith('#')])
    want = kept + n_custom
    real = counts['direct']['mihomo']
    rep.judge(real == want, 'pin',
              f'direct 应有条数: 产物 {real} == 瘦身留存 {kept} + 手工追加 {n_custom}'
              if real == want else
              f'direct 应有条数: 产物 {real} != 瘦身留存 {kept} + 手工追加 {n_custom}',
              'direct 不是由当前白名单 + custom-direct.list 生成的 —— '
              '重跑 bash skill/scripts/regen.sh')

    # 瘦身留痕（WHITELIST-SLIM.md）与独立复算比对（v3 审查发现 5.2，v4 拆为独立段 6c）。
    # 279 条被裁的白名单此前只打印在 stdout、仓内零记录；现在落盘了，
    # 就必须被校验 —— 否则它和产物一样可能"声称 ≠ 实际"。
    # 判据：摘要三项（总/留/裁）+ 保留集合、裁掉集合逐条相等（不复用 convert 的结果）。
    # ⚠️ 本段原先挤在 6b 里，而 6b 的段标是「冻结上游自述 == 源文件实际」——
    #    瘦身留痕比对的是「生成物 == 独立复算」，跟上游自述不是一回事（v4 审查 4.2）。
    rep.section('6c. 白名单瘦身留痕（WHITELIST-SLIM.md）== 独立复算')
    slim = root / 'WHITELIST-SLIM.md'
    if not slim.is_file():
        rep.judge(False, 'pin', 'WHITELIST-SLIM.md 缺失',
                  '瘦身留痕是 direct 的生成记录：重跑 bash skill/scripts/regen.sh')
    else:
        stext = slim.read_text(encoding='utf-8')
        _norm = lambda s: s.strip().lstrip('-').strip().lstrip('.').lower()

        def _section_rows(text, header):
            seg = text.split(header, 1)[1] if header in text else ''
            seg = seg.split('\n## ', 1)[0]
            return set(re.findall(r'^\| `([^`]+)` \|', seg, re.M))

        kept_re = { _norm(e) for e in wl_all if collides(e) }
        dropped_re = { _norm(e) for e in wl_all } - kept_re
        # ⚠️ 摘要的"总"必须按**消费口径**（小写归一去重后）对账，不是原始口径：
        #   上游冻结快照含一对大小写变体（LOG-AUTH.FLYSLEEP.CN），version.json 的
        #   domainWhitelistCount=324 是上游原始口径（上面 pin 已校验）；
        #   而 convert 构建前先 dedup（323）—— 留痕报告记的是构建实际消费的集合，
        #   两个口径各有用途，混用任何一个都会让本断言永远对不上或永远放空。
        wl_dedup = []
        _seen = set()
        for e in wl_all:
            k = e.lower()
            if k not in _seen:
                _seen.add(k)
                wl_dedup.append(k)
        want3 = (len(wl_dedup), len(kept_re), len(dropped_re))
        kept_doc = { _norm(e) for e in _section_rows(stext, '## 一、保留') }
        dropped_doc = { _norm(e) for e in _section_rows(stext, '## 二、裁掉') }

        m = re.search(r'\*\*共 (\d+) 条上游白名单 → 保留 (\d+)（会被黑名单误杀）'
                      r'\+ 裁掉 (\d+)（不被黑名单覆盖）\*\*', stext)
        if not m:
            rep.judge(False, 'pin', 'WHITELIST-SLIM.md 摘要行未命中（版式变了？）',
                      '判据锚在「**共 N 条上游白名单 → 保留 A（…）+ 裁掉 B（…）**」')
        else:
            got = tuple(int(x) for x in m.groups())
            rep.judge(got == want3, 'pin',
                      f'瘦身留痕摘要: {got} == {want3}' if got == want3 else
                      f'瘦身留痕摘要: 声明 {got} != 复算 {want3}',
                      '（总, 保留, 裁掉）三项都要对上')
        for name, doc, re_ in (('保留集合', kept_doc, kept_re),
                               ('裁掉集合', dropped_doc, dropped_re)):
            extra, missing = sorted(doc - re_), sorted(re_ - doc)
            rep.judge(not extra and not missing, 'pin',
                      f'瘦身留痕 {name}逐条一致（{len(doc)} 条）'
                      if not extra and not missing else
                      f'瘦身留痕 {name}与复算不一致：多 {len(extra)} / 缺 {len(missing)}',
                      ('多出: ' + ', '.join(extra[:4]) if extra else '') +
                      ('；缺失: ' + ', '.join(missing[:4]) if missing else ''))

    rep.judge(True, 'pin',
              f'冻结基线：Jinx {version}（{date}）· '
              f'blacklist {blk} / whitelist {wl}')

    # 快照完整性：upstream/ 下每个文件的 sha256 必须与 manifest.json 一致。
    # 这条挡的是「有人手改了 upstream/ 里的文件」—— 手改上游等于悄悄换了合并基线，
    # 而第 6 段只会照着被改过的源重跑，照样全绿。
    mpath = root / MANIFEST
    if not mpath.is_file():
        rep.judge(False, 'pin', '缺 upstream/manifest.json —— 快照完整性无法判定',
                  '跑 python skill/scripts/freeze_upstream.py 生成')
        return
    try:
        mf = json.loads(mpath.read_text(encoding='utf-8'))
    except Exception as e:                                     # noqa: BLE001
        rep.judge(False, 'pin', 'upstream/manifest.json 解析失败', str(e)[:200])
        return
    import hashlib
    drift, absent = [], []
    for item in mf.get('sources', []):
        f = root / 'upstream' / item['path']
        if not f.is_file():
            absent.append(item['path'])
            continue
        got = hashlib.sha256(f.read_text(encoding='utf-8', errors='replace')
                             .encode('utf-8')).hexdigest()
        if got != item['sha256']:
            drift.append((item['path'], item['sha256'][:10], got[:10]))
    rep.judge(not absent, 'pin',
              f'上游快照 {len(mf.get("sources", []))} 个文件齐备'
              if not absent else f'上游快照缺 {len(absent)} 个文件：{absent[:3]}',
              'upstream/ 不完整，构建输入缺失')
    rep.judge(not drift, 'pin',
              f'上游快照 {len(mf.get("sources", []))} 个文件 sha256 与 manifest 一致'
              if not drift else f'上游快照 {len(drift)} 个文件被改动（疑似手改）',
              '\n'.join('%s 期望 %s 实际 %s' % d for d in drift[:4]) +
              '\n有意更新请跑 freeze_upstream.py；手滑则 git checkout -- upstream/')


def seg_upstream_doc(root, rep):
    """文档里声明的上游版本号/快照日期必须等于冻结快照的 version.json。

    上游已冻结，这不再是「跟不跟得上」的问题，而是**门面读数对不对**：
    产物换了、徽章还写着旧版本，读者据以判断的数据就是假的 —— 而条数断言
    照样可能全绿（条数与产物自洽）。
    """
    rep.section('5b. 文档声明的上游版本号 == 冻结快照')
    vpath = root / SRC_DIR / 'version.json'
    if not vpath.is_file():
        rep.judge(False, 'ver', '缺 %s/version.json —— 无法校验文档版本号' % SRC_DIR,
                  '先跑 freeze_upstream.py；未验证 ≠ 绿')
        return
    ver = json.loads(vpath.read_text(encoding='utf-8'))
    version, date = ver['version'], ver['lastUpdate'][:10]

    targets = [
        ('README.md', 'README 冻结徽章',
         r'badge/Frozen-Jinx%20([0-9][0-9.]*)', version),
        ('README.md', 'README 上游快照行',
         r'\| 📌 上游快照 \| 冻结于 `([0-9][0-9.]*)` · `(\d{4}-\d{2}-\d{2})` \|',
         (version, date)),
        ('README.md', 'README 页脚上游行',
         r'\| 📄 上游 \| .*?数据 `([0-9][0-9.]*)` · `(\d{4}-\d{2}-\d{2})` \|',
         (version, date)),
        ('DetailsReadme/DetailsReadme.md', 'Details 页脚上游行',
         r'\| 📦 上游 \| .*?数据 `([0-9][0-9.]*)` · `(\d{4}-\d{2}-\d{2})` \|',
         (version, date)),
    ]
    for rel, label, pattern, want in targets:
        p = root / rel
        if not p.is_file():
            rep.judge(False, 'ver', f'{label}: {rel} 缺失', '对外文档必须存在')
            continue
        m = re.search(pattern, p.read_text(encoding='utf-8'))
        if not m:
            rep.judge(False, 'ver', f'{label}: 锚点未命中（版式变了？）',
                      '文档版式变更后须同步更新 verify_products.py 的锚点')
            continue
        got = m.group(1) if isinstance(want, str) else m.group(1, 2)
        ok = (got == want) if isinstance(want, str) else (tuple(got) == tuple(want))
        rep.judge(ok, 'ver',
                  f'{label}: {got} == {want}' if ok else
                  f'{label}: 声明 {got} != 冻结快照 {want}',
                  '文档是上游版本的门面读数，写错就是让读者以为在用别的版本')

    # SKILL 的读数数值比对放在第 5 段（5-e）—— 这里原本只判「正则可解析」，
    # 与真实的数值校验重复且更弱，已移除，避免两条同名判据让人误读成双保险。


def seg_reproducible(root, rep, counts=None):
    """产物 == 源头重跑的结果。这是「产物是生成物、不是手改物」的最终判据。

    需要 upstream/ 快照与两个脚本。缺快照时判 SKIP（未验证 ≠ 绿），
    但**绝不静默跳过** —— 本仓构建不联网，缺快照说明 freeze_upstream.py 没跑。
    """
    rep.section('6. 产物可复现（源头重跑）')
    script = root / 'skill' / 'scripts' / 'convert_ruleset.py'
    srcdir = root / SRC_DIR
    if not script.is_file():
        rep.rows.append((None, 'SKIP: 6. 产物可复现', '', ''))
        return 'skip'
    if not srcdir.is_dir():
        rep.rows.append((None, 'SKIP: 6. 产物可复现', '', ''))
        return 'skip'

    import tempfile
    build = root / 'skill' / 'scripts' / 'build_ads.py'

    with tempfile.TemporaryDirectory() as tmp:
        # ads 的输入是 build_ads.py 的产物 —— 先跑构建器，**输出到临时目录**。
        # 这样校验本身不写仓库（旧版会覆盖 build/ads/ads-src.txt，属于"只读断言有副作用"）。
        # 这也是「产物 == 生成链重跑」里 ads 那半段的完整含义：构建器 + 转换器两步。
        build_ok = True
        ads_src_dir = Path(tmp) / 'ads'
        if build.is_file():
            proc = subprocess.run(
                [sys.executable, str(build), '--out', str(ads_src_dir / 'ads-src.txt')],
                cwd=str(root), capture_output=True, text=True)
            if proc.returncode != 0:
                build_ok = False
                rep.judge(False, 'repro', 'build_ads.py 构建失败（exit %d）' % proc.returncode,
                          (proc.stderr or proc.stdout or '')[-400:])
        else:
            build_ok = False
            rep.judge(False, 'repro', '缺 skill/scripts/build_ads.py', 'ads 生成链的第一步')

        for fam, extra in REGEN.items():
            if fam == 'ads' and not build_ok:
                continue
            if fam == 'ads':
                src = str(ads_src_dir)
            else:
                src = SRC_OF[fam]
            cmd = ([sys.executable, str(script), '--out', tmp, '--naming', 'repo',
                    '--src', src] + extra)
            if fam == 'ads':
                lab = (ads_src_dir / 'label.txt').read_text(encoding='utf-8').strip()
                cmd += ['--label', lab]
            proc = subprocess.run(cmd, cwd=str(root), capture_output=True, text=True)
            if proc.returncode != 0:
                rep.judge(False, 'repro', f'{fam}: 重跑生成失败（exit {proc.returncode}）',
                          (proc.stderr or proc.stdout or '')[-400:])
                continue
            for kind, name in PRODUCTS[fam].items():
                gen = Path(tmp) / name
                cur = root / name
                if not gen.is_file():
                    rep.judge(False, 'repro', f'{fam}/{kind}: 重跑未产出 {name}', '')
                    continue
                if gen.read_bytes() == cur.read_bytes():
                    rep.judge(True, 'repro', f'{name}: 重跑结果与仓库文件逐字节一致')
                    continue
                # 差异行定位：区分「表头 --src 写法不同」与「内容真的不同」
                a = cur.read_text(encoding='utf-8').splitlines()
                b = gen.read_text(encoding='utf-8').splitlines()
                only_hdr = (len(a) == len(b)
                            and all(x == y or (x.startswith('#') and y.startswith('#'))
                                    for x, y in zip(a, b)))
                detail = [f'仓库: {x}' for x, y in zip(a, b) if x != y][:3] + \
                         [f'重跑: {y}' for x, y in zip(a, b) if x != y][:3]
                rep.judge(False, 'repro',
                          f'{name}: 重跑结果与仓库文件**不一致**'
                          + ('（仅表头注释行差异：核对 REGEN 表的 --src 写法）' if only_hdr else ''),
                          '\n'.join(detail) or '行数不同，见 diff')
    return 'ran'


def seg_source_headers(root, rep, counts):
    """源头 custom-*.list 的 extra 声明与实际条数，以及它是否真的进了产物。"""
    rep.section('7. 源头 custom-*.list')
    pairs = [('custom-ads.list', 'ads', '# extra:'),
             ('custom-direct.list', 'direct', '# extra-white:')]
    for name, fam, header_key in pairs:
        p = root / name
        if not p.is_file():
            rep.judge(False, 'src', f'{name} 缺失', '手工追加域名的唯一入口')
            continue
        entries = [l.strip() for l in p.read_text(encoding='utf-8').splitlines()
                   if l.strip() and not l.strip().startswith('#')]
        # 产物表头里应出现 `<name>(<N>)`，N == 源头实际条数
        prod_header = (root / PRODUCTS[fam]['surge']).read_text(encoding='utf-8')[:400]
        m = re.search(re.escape(name) + r'\((\d+)\)', prod_header)
        if not m:
            rep.judge(False, 'src', f'{name}: 产物表头未声明 {name}(N)',
                      f'预期在 {PRODUCTS[fam]["surge"]} 表头出现 {header_key} {name}(N)')
            continue
        rep.judge(int(m.group(1)) == len(entries), 'src',
                  f'{name}: 表头声明 {m.group(1)} == 源头实际 {len(entries)}'
                  if int(m.group(1)) == len(entries) else
                  f'{name}: 表头声明 {m.group(1)} != 源头实际 {len(entries)}',
                  '源头加了条目但没重跑，或重跑时漏了 --extra / --extra-white')

        # 源头每条都应真实出现在产物里（防止「写进源头但没进产物」）
        prod_rules = set()
        for kind in ('mihomo', 'surge'):
            for e in (parse_mihomo(root / PRODUCTS[fam][kind])
                      if kind == 'mihomo' else parse_surge(root / PRODUCTS[fam][kind])):
                prod_rules.add(normalize_rule(e, SURGE_ALIAS))
        missing = []
        for e in entries:
            base = e[2:] if e.startswith('*.') else e.lstrip('.')
            if ('DOMAIN-SUFFIX', base.lower()) not in prod_rules:
                missing.append(e)
        rep.judge(not missing, 'src',
                  f'{name}: {len(entries)} 条全部落入产物'
                  if not missing else
                  f'{name}: {len(missing)} 条未进入产物',
                  '\n'.join(f'未落盘: {x}' for x in missing[:6]))


# emoji 判定：只认「行首结构位」——SKILL.md §对外交付 的口径是
# 「emoji 只许出现在行首，不得落在句中」，允许的位置包括：
#   标题（#）、段落引导符、无序列表项、表格单元格起始、目录条目、树形框线、缩进。
#
# 判定分三层，且刻意「宽进」——宁可漏报也不给假红：
#   假红会让人把闸门关掉，比漏报更糟（假绿的教训见 SKILL.md 的 0930 事故）。
#
# ① 箭头/数学符号不是 emoji：本仓正文用它们作「流向」标记（`A → B`、
#    `base64 解码后比对`），须排除。SKILL.md 的既有口径亦写明「箭头不算 emoji」。
#    ⚠️ 必须**逐个码位**排除，不能整段排除 —— 实测踩坑：U+2B00-2BFF 段里同时住着
#    箭头（→ U+2192 属 2190 段；⬅⬆⬇ 在 2B05 等）与**真 emoji**（⭐ U+2B50、
#    ⬛ U+2B1B）。整段排除会让 `上面用的是 ⭐ 首选 Raw` 这种句中 emoji 逃过检查
#    —— 负样本自测当场抓到该漏报。
# ② FE0F（变体选择符）必须并入**前一个** emoji 整体消费，不能单独算一个 emoji：
#    `⚖️` = U+2696 + U+FE0F，若拆开匹配，第一轮在行首命中 `⚖` 通过，第二轮又命中
#    `FE0F`（此时前缀是 `⚖`，非结构字符）→ **对完全合规的段首引导符给出假红**。
#    实测踩过：本仓 7 处 `⚖️ / ⏱️ / ⚠️` 行首引导符全被此 bug 误报。
# ③ 前缀是纯结构字符 → 合法（行首 / 列表 / 引用 / 树形框线）。
# ④ 前缀含表格竖线、HTML 标签、序号 → 属「单元格起始」或「标题标签内」，合法。
ARROW_CHARS = set(
    [chr(c) for c in range(0x2190, 0x21FF + 1)] +      # ← ↑ → ↓ ↔ ↕ 等全部箭头
    ['\u2b05', '\u2b06', '\u2b07', '\u2b08', '\u2b09', '\u2b0a', '\u2b0b',
     '\u2b0c', '\u2b0d', '\u2b0e', '\u2b0f', '\u2b10', '\u2b11']  # 二维箭头
)
_VS = '\U0000FE0F'
EMOJI_RE = re.compile(
    '[\U0001F300-\U0001FAFF'          # 各类图形 emoji
    '\U0001F000-\U0001F2FF'
    '\U00002B00-\U00002BFF'           # ⭐ ⬛ ⬜ 等（箭头由 ARROW_CHARS 单独剔除）
    '\U00002600-\U000027BF]'          # 杂项符号与装饰（⚖ ⏱ ⚠ 🛡 🚫 🗓 等）
    + _VS + '?')                      # 变体选择符随基字符一起消费
ARROW_RE = re.compile('[' + re.escape(''.join(sorted(ARROW_CHARS))) + ']')

# 纯结构前缀：行首缩进 / 标题 / 引用 / 列表 / 树形框线 / 单元格竖线
STRUCT_OK = re.compile(
    r'^[\s>#\-*+|\[\]`\\/()（）0-9.\u2500-\u257F]*$')

# HTML 标签（含属性）：`<div align="center">` / `<summary>` / `</b>` / `<br>`
HTML_TAG_RE = re.compile(r'</?[a-zA-Z][a-zA-Z0-9]*(?:\s[^<>]*)?/?>')


def emoji_prefix_ok(prefix):
    """判断 emoji 之前的前缀是否属「结构位」。

    判定分两种版式语境，**表格必须单独处理**：

    ① 非表格行：剥掉全部 HTML 标签（标签属版式结构，其中的 align / center
       等属性文字不是正文），余下部分须**只由结构符号构成**。
    ② 表格行：只取**本单元格内**的内容来判 —— 即最后一个未闭合的 `|` 之后
       的部分。因为 `| 客户端 | 🚫 拦截 |` 里，"客户端"是**上一个单元格**的
       内容，与 🚫 无关；不切开就会把完全合规的「单元格起始」误报成句中。

    ⚠️ 踩坑史（同一类误报发生过两次，故此处写清）：
      - 2026-10-04 首例：`<summary>🔷 <b>mihomo</b></summary>` —— 未剥标签。
      - 2026-10-04 次例：`| <div align="center">🚫 拦截</div> |` —— 剥了标签
        但跨单元格判定，把上一格的"客户端"当成了本格正文。
    """
    # ② 表格行：截到本单元格开头
    if prefix.lstrip().startswith('|') or '|' in prefix:
        cell = prefix.rsplit('|', 1)[-1]
    else:
        cell = prefix

    for candidate in (prefix, cell):
        if STRUCT_OK.match(candidate):
            return True
        stripped = HTML_TAG_RE.sub('', candidate)
        if STRUCT_OK.match(stripped):
            return True
    return False


def find_stray_emoji(text):
    """返回「落在句中」的 emoji 行号与内容。

    逐行取**最后一个** emoji 之后是否还有实质文字：
    口径是「emoji 只能在行首结构位」，因此 emoji 后面跟正文是允许的
    （段落引导符 `⏱️ **缓存…**`、单元格 `| 1 | 🛡️ 白名单 |` 都属此类）；
    判负的是 **emoji 前面出现了正文**（`上面用的是 ⭐ 首选 Raw` 那种）。
    """
    bad = []
    for i, line in enumerate(text.splitlines(), 1):
        for m in EMOJI_RE.finditer(line):
            if ARROW_RE.match(m.group()):
                continue
            if not emoji_prefix_ok(line[:m.start()]):
                bad.append((i, line.strip()[:70]))
                break
    return bad


def count_emoji(text):
    n = 0
    for line in text.splitlines():
        for m in EMOJI_RE.finditer(line):
            if not ARROW_RE.match(m.group()):
                n += 1
    return n


def seg_style(root, rep):
    """文案规范：emoji 只在行首 + 密度下限（2026-09-22 用户口径）。"""
    rep.section('8. 文案规范（emoji 行首 + 密度）')
    targets = [('README.md', 20), ('DetailsReadme/DetailsReadme.md', 40)]
    for rel, floor in targets:
        p = root / rel
        if not p.is_file():
            rep.judge(False, 'style', f'{rel} 缺失', '')
            continue
        text = p.read_text(encoding='utf-8')
        bad = find_stray_emoji(text)
        n_emoji = count_emoji(text)
        rep.judge(not bad, 'style',
                  f'{rel}: emoji 全部位于行首结构位（{n_emoji} 个）'
                  if not bad else
                  f'{rel}: {len(bad)} 行 emoji 落在句中',
                  '\n'.join(f'第 {i} 行: {t}' for i, t in bad[:5]))
        rep.judge(n_emoji >= floor, 'style',
                  f'{rel}: emoji 密度 {n_emoji} >= {floor}'
                  if n_emoji >= floor else
                  f'{rel}: emoji 密度 {n_emoji} < {floor}（显得光秃）',
                  '密度下限防止下次又被"克制"回去')


def _autocrlf(root):
    """读本仓生效的 core.autocrlf（只用于行尾段的读数说明，缺失即 'unset'）。"""
    try:
        proc = subprocess.run(['git', 'config', '--get', 'core.autocrlf'],
                              cwd=str(root), capture_output=True, text=True,
                              encoding='utf-8', errors='replace')
        return (proc.stdout or '').strip() or 'unset'
    except Exception:
        return 'unavailable'


def seg_lineendings(root, rep):
    """第 9 段：行尾符与 BOM —— 报告事实，并守住「不得引入 BOM」这条硬线。

    ⚠️ 本段的定位是**事实播报 + 有限判负**，不是全面合规检查。原因：
    本仓当前行尾是**不统一**的 —— mihomo / Surge 四份产物是 CRLF，
    sing-box 两份 JSON 与全部手写文件是 LF（根因：产物由 convert_ruleset.py
    在 Windows 上写出，仓库又缺 .gitattributes，core.autocrlf=true 把 \n 转成了
    CRLF；手写文件当初以 LF 提交）。这是既存状态，**对功能无影响**
    （各客户端按行解析并 trim 行尾），故不在此判负 —— 否则 CI 一上线就是红的。

    真正判负的只有两条明确有害的情形：
      ① 引入 BOM：BOM 会让部分解析器把首行 `# auto-converted…` 读成带 U+FEFF
         的键，属静默故障面；
      ② 同一「族」内行尾分裂（如 mihomo 与 surge 产物行尾不同）—— 那会让
         跨格式逐行比对失真。
    """
    rep.section('9. 行尾符与 BOM')
    targets = [n for fam in PRODUCTS.values() for n in fam.values()]

    # ① BOM：硬判负
    bom = []
    for name in targets:
        raw = (root / name).read_bytes()
        if raw.startswith(b'\xef\xbb\xbf'):
            bom.append(name)
    rep.judge(not bom, 'eol',
              f'六份产物均无 BOM'
              if not bom else f'{len(bom)} 份产物带 BOM（首行会混入 U+FEFF）',
              'BOM 属静默故障面：解析器可能把首行注释读成带不可见字符的键')

    # ② 同族内行尾一致性 + 事实播报
    eol = {}
    for fam, files in PRODUCTS.items():
        fam_kinds = {}
        for kind, name in files.items():
            raw = (root / name).read_bytes()
            nl = raw.count(b'\r\n')
            fam_kinds[kind] = 'CRLF' if nl and nl == raw.count(b'\n') else (
                'LF' if not nl else '混合')
        eol[fam] = fam_kinds
        same = len(set(fam_kinds.values())) == 1
        rep.judge(same, 'eol',
                  f'{fam}: 三格式行尾一致（{list(set(fam_kinds.values()))[0]}）'
                  if same else
                  f'{fam}: 三格式行尾不一致（{fam_kinds}）',
                  '同族内行尾分裂会让跨格式逐行比对失真')
    # 事实播报（不判负）：让 CI 日志里可见，便于日后统一
    # ⚠️ 本段读的是**工作区**字节，故读数依赖本地 git 配置：Windows 上
    #    core.autocrlf=true（本机即是）会把 LF 检出成 CRLF，CI（Linux）则是 LF。
    #    要判断「仓库内实际存的是什么」，须用 `git cat-file -p HEAD:<file>`
    #    直读 blob，绕过工作区转换 —— 两者的差异本身就是 autocrlf 的证据。
    rep.judge(True, 'eol',
              '行尾现状（工作区口径，非判负）：'
              + '；'.join(f'{k}={v}' for k, v in
                          [(f, '/'.join(sorted(set(d.values())))) for f, d in eol.items()])
              + '｜仓库内真实行尾以 git blob 为准（本机 core.autocrlf='
              + str(_autocrlf(root)) + '）',
              '')


# ---------------------------------------------------------------- 第 10 段

# 平台识别：**显式登记**每个对外支持的客户端名。
#
# ⚠️ 为什么不从产物文件名派生：Egern **没有独立产物** —— 它与 Surge 同格式，
#    直接复用 `surge-*.list`（依据：姊妹仓 Self-Configuration 的四份现役 Egern
#    profile 全部引用 `Jinx/main/surge-*.list`，并把这两份登记为「共用规则集」）。
#    从产物派生会让 Egern 永远不被检查 —— 这正是「无产物端的说明最容易漏」。
PLATFORM_LABEL = {
    'mihomo': ['mihomo'],
    'surge': ['Surge', 'surge'],
    'egern': ['Egern', 'egern'],
    'singbox': ['sing-box'],
}

# 面向外部的「平台清单类位置」—— 这些是**结构性位置**（徽章行 / 表格行 /
# 折叠块标头），漏一端就会让读者以为不支持该端。
#
# ⚠️ 判据必须锚定这类位置，**不能只判"全文出现过平台名"**：
#    实测（2026-10-04）—— 初版判全文出现，把 README 徽章里的 sing-box 行删掉
#    或 DetailsReadme 订阅表里删掉两行，断言**照样全绿**，因为别处（接入节、
#    转换原理表）仍有 "sing-box" 字样。那样的判据等于没判。
#
# 每个条目 = (文件, 描述, 定位正则)。
#
# ⚠️ 定位正则必须**只依赖「这是一行客户端的清单行」这个事实**，不能依赖单元格
#    的排版细节（加粗、反引号、几个文件名）—— 实测（2026-10-04）踩过两次：
#      · 初版 `^\|\s*[^|]+\|\s*`[^`]+`\s*\|` 要求**第二格**是单个反引号词，
#        Egern 行写成「`a` · `b`」（两个文件名）后**整行不被定位**，
#        于是"缺 egern"的判负看上去像是误报，实为判据漏掉了该行。
#      · 加粗版 `^\|\s*\*\*[^|]*\*\*[^|]*\|` 同理，换个排版就失效。
#    改为**按平台名开头**定位 —— 既稳，又与判据意图（平台是否在场）一致。
PLATFORM_ROW = r'^\|\s*\**\s*(mihomo|Surge|Egern|sing-box)\b'
EXTERNAL_POSITIONS = [
    ('README.md', '顶部平台徽章行',
     r'^\[!\[[^\]]*\]\([^)]*img\.shields\.io[^)]*\)\]'),
    ('README.md', '订阅表「Jinx 规则集」行', PLATFORM_ROW),
    ('README.md', '接入节折叠块标头',
     r'<summary>[^\n]*</summary>'),
    ('DetailsReadme/DetailsReadme.md', '订阅表行', PLATFORM_ROW),
    ('DetailsReadme/DetailsReadme.md', '转换原理表表头',
     r'^\|\s*(?:上游|产物侧)写法[^\n]*$'),
    ('skill/scripts/upload_to_github.py', '仓库简介默认值（GitHub 页面顶部显示的就是它）',
     r"'--description',\s*default="),
]


def seg_platform_coverage(root, rep):
    """第 10 段：面向外部的说明，每个平台都必须在「清单类位置」露面。

    动机（2026-10-04 实证）：09-28 给本仓加了 sing-box，README 订阅表 /
    接入节 / 徽章都更新了，但**仓库简介漏了整整一周**无人发现 —— 因为简介存在
    建仓脚本的 `--description` 默认值里，平时没人看，却出现在 GitHub 页面顶部、
    仓库列表与搜索结果里。漏一端 = 使用者以为不支持该端。

    做法：对每个「清单类位置」，取其**同一族的所有行**（如 README 全部徽章行、
    接入节全部 summary、订阅表全部数据行），要求每个平台至少命中一行。
    """
    rep.section('10. 平台清单齐备（面向外部的说明）')

    for rel, where, pat in EXTERNAL_POSITIONS:
        p = root / rel
        if not p.is_file():
            rep.judge(False, 'plat', f'{rel} 缺失（{where}）', '')
            continue
        text = p.read_text(encoding='utf-8', errors='replace')
        # 用 search 而非 match：这些正则描述的是**行内特征**（表格行首是 `|`、
        # Python 实参前有缩进），强行锚行首会让「有缩进就定位不到」。
        # ⚠️ 实测踩坑：`--description` 那行前有 4 空格，用 match 恒不命中，
        #    触发了下面「定位不到」的保护 —— 保护本身是对的（它拒绝静默通过），
        #    但根因是这里选错了匹配方式。
        lines = [l for l in text.splitlines() if re.search(pat, l)]

        # 该位置必须**确实存在**（避免正则写飞了导致空集恒绿）
        if not lines:
            rep.judge(False, 'plat', f'{rel}: 定位不到「{where}」',
                      '正则未命中任何行 —— 版式可能已变，需同步更新本段的正则')
            continue

        missing = [plat for plat, names in PLATFORM_LABEL.items()
                   if not any(any(n in l for n in names) for l in lines)]
        rep.judge(not missing, 'plat',
                  f'{rel}「{where}」：平台列全（{len(lines)} 行）'
                  if not missing else
                  f'{rel}「{where}」：缺 {", ".join(missing)}',
                  '漏一端会让使用者以为不支持该端；'
                  '实证：sing-box 曾从仓库简介里漏了一周')

    # 仓库简介是唯一「不在仓库里」的对外说明 —— 本仓只能校验脚本里的默认值
    rep.judge(True, 'plat',
              '提示：本段校验的是 `upload_to_github.py` 的**默认值**；'
              '已建仓库的**线上简介**须另行核对 `gh repo view --json description`，'
              '不一致时用 `gh repo edit --description` 覆盖（线上值不在本仓，'
              '断言无法直接校验）')


def seg_table_emoji_width(root, rep):
    """第 11 段：同一表格内的 emoji 必须码位数一致（否则纵向不对齐）。

    动机（2026-10-04 用户实测反馈）：能力矩阵表的「放行」行看起来比别的行右移。
    根因是 `🛡️` = **U+1F6E1 + U+FE0F**（两码位，带变体选择符），而同行其他
    emoji（`🚫` `🧩` `🎯` `🔄` `📌`）都是**单码位**。宽字符字体下 `🛡️` 占两格，
    该行的文字整体后移，表格看起来就是没对齐。

    ⚠️ 这类问题**肉眼容易漏**：GitHub 的默认字体里两者宽度相近，但在等宽字体、
       终端预览、部分移动端字体下差异明显。故用码位数机械判定。
    ⚠️ 只判**同一表格内**的一致性 —— 段落引导符（如 `⚠️` 开头的独立段落）
       不参与纵向对齐，各自独立，不属本段范围。

    口径：同一表格的所有数据行，其行首（或任一单元格起始）emoji 的码位数
    必须一致。稳妥做法是**全用单码位 emoji**（避开 FE0F）。
    """
    rep.section('11. 表格内 emoji 宽度一致（对齐）')
    targets = ['README.md', 'DetailsReadme/DetailsReadme.md']
    VS = '\ufe0f'
    bad_tables = 0
    checked = 0

    for rel in targets:
        p = root / rel
        if not p.is_file():
            continue
        lines = p.read_text(encoding='utf-8').splitlines()
        i = 0
        while i < len(lines):
            is_head = (lines[i].strip().startswith('|') and i + 1 < len(lines)
                       and re.match(r'^\|[\s:|-]+\|$', lines[i + 1].strip()))
            if not is_head:
                i += 1
                continue
            body, j = [], i + 2
            while j < len(lines) and lines[j].strip().startswith('|'):
                body.append(lines[j])
                j += 1

            widths = []
            for line in [lines[i]] + body:
                for cell in line.strip().strip('|').split('|'):
                    c = cell.strip()
                    if c and ord(c[0]) > 0x2000:
                        widths.append(2 if (len(c) > 1 and c[1] == VS) else 1)
            if widths:
                checked += 1
                if len(set(widths)) > 1:
                    bad_tables += 1
                    rep.judge(False, 'emoji',
                              f'{rel} 第 {i + 1} 行起的表格：emoji 码位数不一致 {widths}',
                              '带 FE0F 的 emoji 占两格，会让该行在宽字符字体下错位；'
                              '同表内统一用单码位 emoji（避开 U+FE0F）')
            i = j

    if not checked:
        rep.judge(False, 'emoji', '未定位到任何带 emoji 的表格',
                  '定位失败说明版式已变，需同步本段逻辑')
    elif not bad_tables:
        rep.judge(True, 'emoji', f'{checked} 个表格的 emoji 码位数均一致')
        rep.judge(True, 'emoji',
                  '段落引导符（如 ⚠️）带 FE0F 属正常，不在本段范围 —— '
                  '它们各自独立成行，不参与纵向对齐')


def seg_overlap(root, rep):
    """第 12 段：OVERLAP.md 必须与当前产物一致（独立复算，不复用构建器结果）。

    动机（2026-10-27 外部审查）：这份清单此前只落在 `build/ads/ads-audit.txt`，
    而 `build/` 在 .gitignore 里 —— 订阅者看不到、CI 不校验。可它恰恰是本仓
    最该被看见的风险：这几十条放行条目只能靠"放行行更早命中"存活；消费端一旦
    把 REJECT 提前（Surge 的 pre-matching 就是），它们全部失效，症状是推送收不到、
    微信登录转圈。

    判据刻意做成**独立复算**：直接从两份产物重算，再与文件里的清单逐条比对。
    不复用 build_ads 的中间结果，这样"生成器写错"也会被抓到。
    """
    rep.section('12. 白名单 × 拦截集重叠清单（OVERLAP.md）')
    md = root / 'OVERLAP.md'
    if not md.is_file():
        rep.judge(False, 'ovl', 'OVERLAP.md 缺失',
                  '它是本仓唯一对外可见的风险清单：重跑 bash skill/scripts/regen.sh 生成')
        return
    text = md.read_text(encoding='utf-8')

    ads = parse_surge(root / PRODUCTS['ads']['surge'])
    ads_suf = {e.split(',', 1)[1].strip().lower()
               for e in ads if e.upper().startswith('DOMAIN-SUFFIX,')}
    direct = parse_surge(root / PRODUCTS['direct']['surge'])

    def covered(v):
        q = v.split('.')
        return any('.'.join(q[i:]) in ads_suf for i in range(len(q) - 1))

    same, above = set(), set()
    for e in direct:
        t, _, v = e.partition(',')
        v = v.strip().lower()
        if not v:
            continue
        # 同域同名 vs 被上层覆盖，判据只看"值本身是不是拦截集里的那一条"：
        # direct 侧有 DOMAIN（精确）与 DOMAIN-SUFFIX 两种写法，但 ads 侧全是后缀，
        # 所以只要值本身在 ads 后缀集合里，就属「同名」—— 别按 direct 的类型分支，
        # 否则 `DOMAIN,jpush.cn` 这种会被漏掉（既不进 same 也不进 above）。
        if v in ads_suf:
            same.add(v)
        elif covered(v):
            above.add(v)

    m = re.search(r'\*\*共 (\d+) 条\*\*：(\d+) 条同域同名 \+ (\d+) 条上层后缀覆盖'
                  r'（白名单共 (\d+) 条，其余 (\d+) 条与拦截集无关）', text)
    if not m:
        rep.judge(False, 'ovl', 'OVERLAP.md 摘要行未命中（版式变了？）',
                  '判据锚在「**共 N 条**：A 条同域同名 + B 条上层后缀覆盖（白名单共 C 条…）」')
        return
    got = tuple(int(x) for x in m.groups())
    want = (len(same) + len(above), len(same), len(above), len(direct),
            len(direct) - len(same) - len(above))
    rep.judge(got == want, 'ovl',
              f'重叠摘要: {got} == {want}' if got == want else
              f'重叠摘要: 声明 {got} != 复算 {want}',
              '（共, 同域同名, 上层覆盖, 白名单总数, 无关）五项都要对上')

    # README 里也报了这个数（「当前是 **42 条**，逐条列在 OVERLAP.md」）——
    # 那是订阅者唯一会读到的地方，必须跟着产物走。同一类"文档数字无人校验"
    # 的坑今天已经踩过两次（SKILL 读数、能力矩阵构成），这里一次补齐。
    rd = root / 'README.md'
    if rd.is_file():
        m2 = re.search(r'当前是 \*\*(\d+) 条\*\*，逐条列在', rd.read_text(encoding='utf-8'))
        if not m2:
            rep.judge(False, 'ovl', 'README 的重叠条数句未命中（版式变了？）',
                      '判据锚在「当前是 **N 条**，逐条列在 [OVERLAP.md]」')
        else:
            rep.judge(int(m2.group(1)) == want[0], 'ovl',
                      f'README 重叠条数: {m2.group(1)} == {want[0]}'
                      if int(m2.group(1)) == want[0] else
                      f'README 重叠条数: 声明 {m2.group(1)} != 复算 {want[0]}',
                      'README 是订阅者唯一会读到这个数的地方')

    listed = set(re.findall(r'^\| `([^`]+)` \|', text, re.M))
    extra = sorted(listed - (same | above))
    missing = sorted((same | above) - listed)
    rep.judge(not extra and not missing, 'ovl',
              f'重叠清单逐条一致（{len(listed)} 条）'
              if not extra and not missing else
              f'重叠清单与产物不一致：多 {len(extra)} / 缺 {len(missing)}',
              '\n'.join(['多出: ' + ', '.join(extra[:5])] if extra else []) +
              ('\n' if extra and missing else '') +
              ('缺失: ' + ', '.join(missing[:5]) if missing else ''))


def seg_section_refs(root, rep):
    """第 13 段：仓内所有「第 N 段」引用必须指向真实段标。

    动机（2026-10-27 v5 审查 3.3）：「第 N 段」是散落在文档与生成器里的**手写常量**，
    而段号随拆分/新增而变 —— 这类漂移已发生四次（总段数与段标数不一致 ×2、
    段标与内容不符、生成器硬编码段号在同一次拆分中失效），前三次都靠外部审查抓出。
    本段让第四类「自己叫」。

    判据两型（v6 审查 2.1/2.2/2.3）：
      ① 段号引用：每处「第 N 段」的 N 必须在 rep.section 段标真值里；
      ② 段数声明：去掉①的匹配后，残余文本里的裸「N 段」必须等于编号段总数
        （编号段 = 段标去掉前置 0 后的个数）。「段数 12 实为 13」「OVERLAP 写共 14」
        这两类已发生过的漂移都属此型 —— 其中生成物/生成器里的声明手改会被覆盖，
        此前完全无人守。
    扫描排除 CHANGELOG 历史记录、upstream/、build/、.git/。
    """
    rep.section('13. 段号引用与段数声明 == 真实段标/段数')
    src = Path(__file__).read_text(encoding='utf-8')
    labels = set(re.findall(r"rep\.section\('([0-9]+[a-z]?)\.", src))
    if not labels:
        rep.judge(False, 'seg', '无法从本脚本提取段标（源码版式变了？）',
                  "判据依赖 rep.section('N. ...') 的字面量形式")
        return

    def _key(n):
        m = re.match(r'(\d+)([a-z]?)', n)
        return (int(m.group(1)), m.group(2))

    n_seg = len([k for k in labels if k != '0'])   # 编号段总数（前置 0 不计）
    # 段数声明的「声明位文件」。判断标准：这份文件的读者需要知道「一共几段」。
    # 段号引用（①型）仍全仓扫描 —— 「第 N 段」语义无歧义，不存在措辞税。
    DECL_FILES = {
        'OVERLAP.md', 'WHITELIST-SLIM.md',          # 生成物（CI 比对对象）
        'README.md', 'NOTICE.md',
        'skill/SKILL.md', 'DetailsReadme/DetailsReadme.md',
        'skill/scripts/build_ads.py',               # 生成器模板
        'skill/tests/verify_products.py',           # 判据自身的清单头
        '.github/workflows/ci.yml',
    }
    bad, bad_count, scanned = [], [], 0
    for p in root.rglob('*'):
        if not p.is_file():
            continue
        rel = p.relative_to(root).as_posix()
        if (rel.startswith(('upstream/', 'build/', '.git/', '.workbuddy/'))
                or rel == 'CHANGELOG.md'):      # 历史记录描述的是当时状态，不参与
            continue
        if p.suffix not in ('.md', '.py', '.sh', '.yml', '.yaml', '.txt', '.json', '.list'):
            continue
        try:
            text = p.read_text(encoding='utf-8', errors='replace')
        except Exception:                       # noqa: BLE001
            continue
        # ① 段号引用。数字限 1-2 位：与②型护栏对齐（v7 审查 2.2）——
        #   「第 2190 段」这类 Unicode 区段引用不该被判负；段标最大两位（13）。
        for m in re.finditer(r'第\s*([0-9]{1,2}[a-z]?)\s*段', text):
            scanned += 1
            if m.group(1) not in labels:
                bad.append((rel, m.group(1)))
        # ② 段数声明：只扫「声明位文件」里的裸「N 段」（v7 审查 2.1）。
        #    全文一刀切是措辞税 —— 「分三段讲清楚」这类正常中文会被判红，
        #    误报多了人会绕着判据写文档，它就变成下一个没人看的地方。
        #    声明只应出现在下列文件；新文件开始携带段数声明时把它加进来。
        if rel not in DECL_FILES:
            continue
        residue = re.sub(r'第\s*[0-9]{1,2}[a-z]?\s*段', '', text)
        for m in re.finditer(r'(?<!\d)(\d{1,2})\s*段', residue):
            scanned += 1
            if int(m.group(1)) != n_seg:
                bad_count.append((rel, m.group(1)))

    rep.judge(not bad, 'seg',
              '段号引用一致（真实段标 %d 个：%s）'
              % (len(labels), ' '.join(sorted(labels, key=_key)))
              if not bad else
              '%d 处「第 N 段」指向不存在的段标' % len(bad),
              '\n'.join('  %s → 第 %s 段（现有段标：%s）'
                        % (r, n, ' '.join(sorted(labels, key=_key)))
                        for r, n in bad[:6]) +
              '\n段号是手写常量：拆分/新增段时必须同步改全部引用，'
              '或直接以段名相称（如「瘦身留痕段」）避免硬编码')
    rep.judge(not bad_count, 'seg',
              '段数声明一致（编号段 %d 个，扫描 %d 处引用/声明）' % (n_seg, scanned)
              if not bad_count else
              '%d 处段数声明与实际不符（实际编号段 %d 个）' % (len(bad_count), n_seg),
              '\n'.join('  %s → 写着 %s 段' % (r, n) for r, n in bad_count[:6]) +
              '\n段数声明同样会随拆分漂移，且生成物/生成器里的声明手改会被覆盖 —— '
              '本仓「段数 12 实为 13」「OVERLAP 写共 14」两次都属此型')


# ---------------------------------------------------------------- main

def collect_counts(root):
    counts = {}
    for fam, files in PRODUCTS.items():
        counts[fam] = {
            'mihomo': len(parse_mihomo(root / files['mihomo'])),
            'surge': len(parse_surge(root / files['surge'])),
            'singbox': len(parse_singbox(root / files['singbox'])),
        }
    return counts


def run(root):
    rep = Report()
    rep.section('0. 前置检查')
    missing = [n for fam in PRODUCTS.values() for n in fam.values()
               if not (root / n).is_file()]
    if missing:
        print(f'❌ 前置不达标：缺 {len(missing)} 份产物 → {missing[:4]}')
        print('   本脚本必须在 RFU-Rules 仓根执行；产物缺失时判据无意义。')
        return EXIT_ENV
    rep.judge(True, 'env', f'仓根定位正确（{root}），六份产物齐备')

    counts = collect_counts(root)
    seg_products_exist(root, rep)
    seg_counts_consistent(root, rep, counts)
    seg_cross_format(root, rep)
    seg_header_selfcount(root, rep, counts)
    seg_doc_counts(root, rep, counts)
    seg_upstream_doc(root, rep)
    repro = seg_reproducible(root, rep, counts)
    repro_failed = len([r for r in rep.rows if r[0] is False and r[1] == 'repro'])
    seg_upstream_pin(root, rep, counts, repro_failed=repro_failed)
    seg_source_headers(root, rep, counts)
    seg_style(root, rep)
    seg_lineendings(root, rep)
    seg_platform_coverage(root, rep)
    seg_table_emoji_width(root, rep)
    seg_overlap(root, rep)
    seg_section_refs(root, rep)

    print(rep.render())
    print()
    total = len([r for r in rep.rows if r[0] is not None])
    failed = len(rep.failed)
    print(f'{"─" * 62}')
    if failed:
        print(f'TOTAL: {total - failed} passed, {failed} failed')
        return EXIT_FAIL
    if repro == 'skip':
        # SKIP 必须走独立退出码 3，不能借 0 蒙混过关 —— 「未验证 ≠ 绿」。
        # 姊妹仓 0930 事故：SKIP 曾复用 2，与「环境不达标」同码双义，
        # 导致汇总脚本把环境故障吞成 SKIP → exit 0 假绿。此处按四态协议分离。
        print('⚠️  第 6 段「产物可复现」已 SKIP（缺 upstream/ 快照或脚本）')
        print('   未验证 ≠ 绿。补测：python skill/scripts/freeze_upstream.py')
        print('   落盘上游后重跑本脚本；或直接 bash skill/scripts/regen.sh。')
        print(f'TOTAL: {total - failed} passed, 0 failed, 1 SKIPPED（exit 3）')
        return EXIT_SKIP
    print(f'TOTAL: {total - failed} passed, {failed} failed')
    return EXIT_PASS


def main():
    ap = argparse.ArgumentParser(description='RFU 规则集一致性断言')
    ap.add_argument('--root', default=None, help='仓根（默认：本脚本上溯两级）')
    args = ap.parse_args()
    if args.root:
        root = Path(args.root).resolve()
    else:
        root = Path(__file__).resolve().parents[2]
    if not (root / 'README.md').is_file():
        print(f'❌ 前置不达标：{root} 下没有 README.md，不像 RFU-Rules 仓根')
        return EXIT_ENV
    return run(root)


if __name__ == '__main__':
    sys.exit(main())
