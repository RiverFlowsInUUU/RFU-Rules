#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_products.py 的负样本自测 —— 证明闸门真能抓错，不是空转。

**为什么必须有这个文件**：一个只会全绿的闸门与没有闸门等价。本仓
`skill/SKILL.md` 记录过一次真实事故：某个检查「两半都恒空/恒 0」，
长期以绿形态存在，实际什么都没验 —— 被称为「永远绿的空操作」。
本脚本就是防这类退化的：它在临时副本仓里逐一制造典型错误，
要求 `verify_products.py` **判负**且命中预期分段。任何一种错误没被抓到，
本脚本即判负 —— 提示闸门出现了漏报。

退出码：0=全部抓到 / 1=有漏报（闸门不可信）。

用法:
  python skill/tests/selftest_negative.py
"""
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

for _s in ('stdout', 'stderr'):
    _f = getattr(sys, _s, None)
    if _f is not None and hasattr(_f, 'reconfigure'):
        try:
            _f.reconfigure(encoding='utf-8', errors='replace')
        except (ValueError, OSError):
            pass

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / 'skill' / 'tests' / 'verify_products.py'

CASES = []


def case(label, expect):
    """注册一个负样本：label 说明制造的错误，expect 是应命中的分段关键词。"""
    def deco(fn):
        CASES.append((label, expect, fn))
        return fn
    return deco


@case('手改产物：白名单 mihomo 删掉一条', '条数一致')
def _(w):
    p = w / 'mihomo-direct.yaml'
    lines = p.read_text(encoding='utf-8').splitlines()
    idx = next(i for i, l in enumerate(lines) if l.strip().startswith('- '))
    lines.pop(idx)
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')


@case('手改产物：只把表头自述条数改掉', '文件头 # entries')
def _(w):
    p = w / 'surge-direct.list'
    t = p.read_text(encoding='utf-8').replace('# entries: ', '# entries: 99 # ')
    lines = [l for l in t.splitlines()]
    for i, l in enumerate(lines):
        if l.startswith('# entries:'):
            lines[i] = '# entries: 99'
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')


@case('手改产物：sing-box 少一条（跨格式差异）', '跨格式语义等价')
def _(w):
    p = w / 'sing-box-direct.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    for rule in d['rules']:
        for v in rule.values():
            if v:
                v.pop()
                break
        break
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


@case('文档漂移：README 订阅表条数写错', '文档条数声明')
def _(w):
    """把订阅表里某个文件的条数改错。

    兼容两种合法表格形态（见 verify_products.py 第 5 段）：
      A 独立单元格： | `f` | 47 |
      B 内嵌链接：   [`f`](URL) `47`
    两种都试，确保本负样本在版式演进后依然有效。
    实测教训（2026-10-04）：只匹配形态 A 时，README 改成形态 B 后本负样本
    静默失效（改不动文件 → 断言自然不报错 → 被误读成「漏报」）。
    实测教训（2026-10-23）：条数曾硬编码 `47`，放行集长到 `48` 后两串再次
    全部落空；改为正则匹配任意条数，只把捕获到的数字替换成 `50`。
    """
    p = w / 'README.md'
    t = p.read_text(encoding='utf-8')
    pats = [
        (r'(\[`surge-direct\.list`\]\(https://raw\.githubusercontent\.com/'
         r'RiverFlowsInUUU/RFU-Rules/main/surge-direct\.list\)\s*`)'
         r'(\d+)(`)'),
        (r'(\| `surge-direct\.list` \| )(\d+)( \|)'),
    ]
    for pat in pats:
        m = re.search(pat, t)
        if m:
            want = str(int(m.group(2)) + 7)      # 改成任意一个不等于实际的数
            t = t[:m.start(2)] + want + t[m.end(2):]
            break
    else:
        raise AssertionError('负样本失效：README 订阅表两种形态都没匹配到')
    p.write_text(t, encoding='utf-8')


@case('源头改了没重跑：custom-direct.list 追加一条', '源头 custom')
def _(w):
    p = w / 'custom-direct.list'
    p.write_text(p.read_text(encoding='utf-8') + '*.selftest-not-real.net\n',
                 encoding='utf-8')


@case('文案违规：emoji 落在句中', '文案规范')
def _(w):
    """在正文句子中间塞一个 emoji。

    用 ⭐（U+2B50）—— 它与箭头（→ U+2192、⬅ U+2B05）同处一位区段，
    专门守「把整段当箭头排除」这类漏报（2026-10-04 真实踩过）。

    ⚠️ 锚点必须选**当前 README 里真实存在**的行。实测教训：本负样本原锚在
    `⭐ **Raw GitHub** · 首选` 上，该行随裸 URL 块一起被删除后，负样本静默
    失效（`replace` 无命中 → 文件没被改 → 断言不报错 → 被误读成「漏报」）。
    故此处改为**动态选择**：取第一个非空、非标题、不含 emoji 的正文行来注入。
    """
    p = w / 'README.md'
    lines = p.read_text(encoding='utf-8').split('\n')
    for i, l in enumerate(lines):
        s = l.strip()
        if not s or s.startswith(('#', '|', '>', '```', '<', '- ', '*')):
            continue
        if v := __import__('re').search(
                '[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U00002B00-\U00002BFF]', s):
            continue
        lines[i] = '上面用的是 ⭐ 首选 Raw，' + s
        break
    else:
        raise AssertionError('负样本失效：README 里找不到可注入的正文行')
    p.write_text('\n'.join(lines), encoding='utf-8')


@case('平台清单缺一端：仓库简介漏 sing-box（第 10 段）', '平台清单齐备')
def _(w):
    """把建仓脚本里的简介默认值还原成漏 sing-box 的旧值。

    这是**真实发生过的缺陷**：2026-09-28 加入 sing-box 后，README / 接入节 /
    徽章都更新了，但仓库简介（GitHub 页面顶部、列表、搜索结果都显示它）漏了
    整整一周无人发现 —— 因为它存在建仓脚本的 `--description` 默认值里，
    平时没人会打开那个文件看。
    """
    p = w / 'skill' / 'scripts' / 'upload_to_github.py'
    t = p.read_text(encoding='utf-8')
    # ⚠️ 锚点会随平台增删而过期 —— 这里断言必须命中，否则抛错而非静默通过
    #    （实测：加入 Egern 后本锚点曾失效并被自测当场抓出）。
    old = 'mihomo / Surge / Egern / sing-box'
    assert old in t, '负样本失效：简介默认值里已无预期文本（平台清单可能又变了）'
    p.write_text(t.replace(old, 'mihomo / Surge / Egern', 1), encoding='utf-8')


@case('平台清单缺一端：转换原理表头去掉 sing-box 列（第 10 段）', '平台清单齐备')
def _(w):
    """表格表头少一个平台列 —— 属「清单类位置」的平台缺失。

    ⚠️ 本条守的是第 10 段的**判据强度**：早期实现只判「全文出现过平台名」，
    这种删表格列的做法照样全绿（别处仍有 sing-box 字样）。现已锚定到
    结构性位置（徽章行 / 订阅表行 / 折叠块标头 / 表头 / 简介默认值）。
    """
    p = w / 'DetailsReadme' / 'DetailsReadme.md'
    t = p.read_text(encoding='utf-8')
    old = '| 产物侧写法 | 含义 | mihomo | Surge | Egern | sing-box |'
    assert old in t, '负样本失效：转换原理表头已改版（平台列可能又变了）'
    p.write_text(t.replace(old, '| 产物侧写法 | 含义 | mihomo | Surge | Egern |', 1),
                 encoding='utf-8')


@case('表格 emoji 宽度不一致：放行行换回带 FE0F 的 🛡️（第 11 段）', '表格内 emoji 宽度')
def _(w):
    """把能力矩阵的「✅ 放行」换回 `🛡️ 放行`。

    `🛡️` = U+1F6E1 + **U+FE0F**（两码位），同表其他 emoji 都是单码位 ⇒
    宽字符字体下该行占两格、文字整体后移，表格看起来「没对齐」——
    这是用户 2026-10-04 实际反馈的现象。

    ⚠️ 这类缺陷肉眼在 GitHub 默认字体下几乎看不出（宽度相近），
       只有终端 / 等宽字体 / 部分移动端才明显 —— 故必须机械判定，
       本负样本守的就是这条判据。

    📌 条数不硬编码：2026-10-23 放行集 47 → 48 时此处曾因写死 `**47 条**`
       而失效；改为只替换行首的「✅ 放行」标志，条数随当前表格保留。
    """
    p = w / 'README.md'
    t = p.read_text(encoding='utf-8')
    old = '| ✅ 放行 |'
    assert old in t, '负样本失效：能力矩阵的放行行已改版'
    p.write_text(t.replace(old, '| 🛡️ 放行 |', 1), encoding='utf-8')


@case('半同步：上游源前进了但产物没重跑（拿旧版合并）', '重跑结果与仓库文件')
def _(w):
    """模拟「拿上游旧版本合并」：上游源又发了新规则，产物却还是旧的。

    ⚠️ **诚实记录本样本的实际判别力**：它通常被第 6 段（产物可复现）
    抓到，而非 6b 段 —— 因为「产物与源不符」对第 6 段而言是直接可见的。
    这正是 2026-10-10 我看到的那个红：**问题不在于红没出现，而在于我
    选择把本地源钉回旧版本让红变绿**。「拿旧版合并」是一条政策违反，
    不是一种静态状态，故本样本守的是「这条链路上的红确实会被报出来」，
    而不是「6b 能独立识别它」（6b 在有源变动时也会同时报 6b 条数不符）。
    真正只有 6b 能抓的是上面那条「残缺上游快照」样本。

    故 expect 取第 6 段失败时才出现的文案，不取段标题。
    """
    src = w / 'upstream' / 'jinx-3.2.3' / 'blacklist.txt'
    assert src.is_file(), '负样本失效：临时仓里没有 upstream/jinx-3.2.3/，无法制造半同步'
    src.write_text(src.read_text(encoding='utf-8') + 'selftest-half-sync.example.com\n',
                   encoding='utf-8')


@case('文档版本号漂移：README 徽章写回旧上游版本（第 5b 段）',
      '声明 0.0.0 != 冻结快照')
def _(w):
    """把 README 的 Source 徽章改成一个不是当前上游的版本号。

    旧闸门只校验**条数**，从不看版本号 ⇒ 这种漂移全绿。读者看到的
    「Source-Jinx 3.1.9」是假读数，而且产物其实已经是新版。

    ⚠️ expect 用失败时才出现的文案，不能用段标题（段标题通过与否都会打印，
    拿它当关键词会让样本永远“抓到”，即使判据已被改坏）。

    ⚠️ 版本号动态从 version.json 读，不硬编码 —— 否则上游每次滚动
    本负样本都要跟着改，很容易变成一条“忘了维护所以静默通过”的假绿。
    """
    import re
    p = w / 'README.md'
    t = p.read_text(encoding='utf-8')
    ver = json.loads((w / 'upstream' / 'jinx-3.2.3' / 'version.json').read_text(
        encoding='utf-8'))['version']
    pat = r'badge/Frozen-Jinx%20' + re.escape(ver)
    assert re.search(pat, t), '负样本失效：README 冻结徽章里没有当前上游版本号'
    p.write_text(re.sub(pat, 'badge/Frozen-Jinx%200.0.0', t, count=1),
                 encoding='utf-8')


@case('残缺上游快照：version.json 自述计数与源文件不符（第 6b 段）',
      '!= 源文件实际')
def _(w):
    """只改动 version.json 的自述计数，让它与源文件实际对不上。

    这是**只有 6b 段能抓到**的一类错误（6 段的独立性反证就靠本样本）：
    它模拟的是「本地 upstream/ 不是一份完整/可信任的上游快照」——
    比如手工裁过、只取到半个快照、或混入了上一个版本的残留文件。

    此时产物与源彼此“自洽”，第 6 段重跑可以全绿，但**两个东西都不可信**；
    若拿这份源去同步文档，读者看到的版本号与条数都是错的。

    ⚠️ 锚定 version.json 自述值而非源文件本身：自述值是上游官方对
    本快照的承诺，改动它才能制造「快照完整性」分歧。

    ⚠️ 2026-10-10 修正：原写 `d['domainBlacklistCount'] += 1`，隐含假设
    「源文件是干净的」——若工作区恰好也给 blacklist 追加过行（演练时就这么发生了），
    两边同时 +1 又变得相等，样本静默变成空操作（漏报）。现在改为**从副本仓
    实际数出条数再 +1**，无论副本仓是什么状态都保证分歧存在。
    """
    src = w / 'upstream' / 'jinx-3.2.3'
    actual = sum(1 for line in (src / 'blacklist.txt').read_text(encoding='utf-8').splitlines()
                 if line.strip() and not line.strip().startswith('#'))
    actual += sum(1 for line in (src / 'blacklist_wildcard.txt').read_text(encoding='utf-8').splitlines()
                  if line.strip() and not line.strip().startswith('#'))
    p = src / 'version.json'
    d = json.loads(p.read_text(encoding='utf-8'))
    d['domainBlacklistCount'] = actual + 1
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


@case('手改冻结上游：往 upstream/ 加一行，不动 manifest（第 6b 段 sha256）', '被改动')
def _(w):
    """往 upstream/jinx-3.2.3/blacklist.txt 追加一条，但不更新 manifest.json。

    这是 2026-10-27 新增的守卫：手改上游等于悄悄换掉合并基线，而第 6 段
    只会照着被改过的源重跑、照样全绿 —— 只有 sha256 校验能发现它。
    """
    src = w / 'upstream' / '217heidai' / 'china.txt'
    assert src.is_file(), '负样本失效：临时仓里没有 upstream/217heidai/china.txt'
    # 选 china.txt 是为了**独立性**：它只参与覆盖率参考播报，不进产物 ——
    # 于是本样本只触发 sha256 判据，不会顺带把第 6 段也弄红，
    # 从而真正证明「6b 的 sha 校验」是一盘独立的守卫。
    src.write_text(src.read_text(encoding='utf-8') + 'selftest-drift.example.cn\n',
                   encoding='utf-8')


@case('重叠清单数字写错（第 12 段摘要）', '重叠摘要: 声明')
def _(w):
    """把 OVERLAP.md 摘要行的「共 N 条」改成一个不对的数。

    守第 12 段的**计数判据**：它独立复算两份产物，再与文件里的五项数字比对。
    """
    p = w / 'OVERLAP.md'
    t = p.read_text(encoding='utf-8')
    m = re.search(r'\*\*共 (\d+) 条\*\*', t)
    assert m, '负样本失效：OVERLAP.md 摘要行版式变了'
    p.write_text(t[:m.start(1)] + str(int(m.group(1)) + 1) + t[m.end(1):], encoding='utf-8')


@case('重叠清单漏一条（第 12 段逐条比对）', '重叠清单与产物不一致')
def _(w):
    """删掉 OVERLAP.md 里的一行表格 —— 数字仍自洽，但清单少了一条。

    守第 12 段的**逐条判据**：只对数字不对清单的话，这一条会被漏掉。
    """
    p = w / 'OVERLAP.md'
    lines = p.read_text(encoding='utf-8').splitlines()
    idx = max(i for i, l in enumerate(lines) if re.match(r'^\| `[^`]+` \|', l))
    del lines[idx]
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')


@case('README 重叠条数与产物不符（第 12 段）', 'README 重叠条数: 声明')
def _(w):
    """改 README 里「当前是 **42 条**」这个数 —— OVERLAP.md 不动。

    守的是"订阅者读到的那份数字"：OVERLAP.md 对了不代表 README 对，反之亦然。
    同一类"文档数字无人校验"今天已经栽过两次，所以两边各有一条负样本。
    """
    p = w / 'README.md'
    t = p.read_text(encoding='utf-8')
    m = re.search(r'当前是 \*\*(\d+) 条\*\*', t)
    assert m, '负样本失效：README 的重叠条数句版式变了'
    p.write_text(t[:m.start(1)] + str(int(m.group(1)) - 1) + t[m.end(1):], encoding='utf-8')


@case('瘦身留痕摘要数字写错（第 6c 段）', '瘦身留痕摘要: 声明')
def _(w):
    """改 WHITELIST-SLIM.md 摘要行的保留数。

    守第 6c 段的瘦身留痕判据：摘要三项（总/留/裁）与独立复算比对。
    """
    p = w / 'WHITELIST-SLIM.md'
    t = p.read_text(encoding='utf-8')
    m = re.search(r'\*\*共 (\d+) 条上游白名单 → 保留 (\d+)（会被黑名单误杀）'
                  r'\+ 裁掉 (\d+)（不被黑名单覆盖）\*\*', t)
    assert m, '负样本失效：WHITELIST-SLIM.md 摘要行版式变了'
    p.write_text(t[:m.start(2)] + str(int(m.group(2)) + 1) + t[m.end(2):],
                 encoding='utf-8')


@case('瘦身留痕漏一条保留行（第 6c 段）', '瘦身留痕 保留集合与复算不一致')
def _(w):
    """删掉 WHITELIST-SLIM.md「保留」节的一行表格。

    只对数字不对清单的话，这一条会被漏掉 —— 与 OVERLAP 的同名样本同理，
    摘要与逐条是两盘独立的守卫，各配一条。
    """
    p = w / 'WHITELIST-SLIM.md'
    lines = p.read_text(encoding='utf-8').splitlines()
    head = [l for l in lines if l.startswith('## 一、保留')][0]
    i = lines.index(head)
    j = next(k for k in range(i + 1, len(lines)) if lines[k].startswith('| `'))
    del lines[j]
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')


@case('段号引用指向不存在的段（第 13 段）', '指向不存在的段标')
def _(w):
    """往 README 里塞一处「第 99 段」。

    守第 13 段：段号是手写常量、已四次随拆分漂移（前三次全靠外部审查抓出），
    本判据让这类失真自己叫。选 NOTICE 表格行下刀 —— 不碰任何被第 5 段
    正则锚定的读数，保证样本只触发本段。
    """
    p = w / 'README.md'
    t = p.read_text(encoding='utf-8')
    old = '（数据 vs 脚本分开授权） |'
    assert old in t, '负样本失效：README 的 NOTICE 行版式变了'
    p.write_text(t.replace(old, '（数据 vs 脚本分开授权）（第 99 段） |', 1),
                 encoding='utf-8')


def main():
    if not TARGET.is_file():
        print(f'❌ 前置不达标：找不到 {TARGET}')
        return 2
    print(f'被检脚本: {TARGET}')

    # 前置：副本仓本身必须先跑绿。负样本自测是**相对**断言 ——
    # 它验证的是「破坏 O 后闸门能抓到」，前提是「不破坏时闸门是绿的」。
    # 若工作区已经处于脏状态（例如调试时往 upstream/ 追加了一行），
    # 每条负样本都会在“已经红”的底子上运行，结果既可能假绿也可能假红，
    # 自测结论完全不可信。2026-10-10 演练时就撞上过这个陷阱。
    # 宁可拒绝出结论（退出码 2），也不给一个看似跑过的假绿。
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / 'repo'
        shutil.copytree(ROOT, base, ignore=shutil.ignore_patterns('.git', '__pycache__', '_regen'))
        proc = subprocess.run(
            [sys.executable, str(TARGET), '--root', str(base)],
            capture_output=True, text=True, encoding='utf-8', errors='replace')
        if proc.returncode != 0:
            print(f'❌ 前置不达标：副本仓本身就没跑绿（exit={proc.returncode}），'
                  '负样本自测在非绿基线上无意义。')
            print('   先让 `python skill/tests/verify_products.py` 在仓根回到 0，再跑本自测。')
            tail = [l for l in (proc.stdout or '').splitlines() if '❌' in l][:5]
            for l in tail:
                print('   ' + l.strip())
            return 2
    print(f'负样本数: {len(CASES)}\n')

    # 每条样本各建一个临时副本并跑一次完整闸门 —— 互不依赖，故并发执行。
    # 串行时 14 条要 70s 以上（每条 4-5s，主要是 python 启动 + 三支路重建），
    # CI 上更慢；并发 4 路后约 1/3。
    def run_one(case):
        label, expect, sabotage = case
        try:
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp) / 'repo'
                # upstream/ 必须复制：第 5b / 6b 段要读它断言「快照完整且未被手改」。
                # 排除它会让这两段对所有样本一律判负，于是每条都"抓到"，自测失去区分力。
                # build/ 是中间目录，不进副本 —— 第 6 段会自己重建到临时目录。
                shutil.copytree(ROOT, work,
                                ignore=shutil.ignore_patterns('.git', '__pycache__',
                                                              '_regen', 'build'))
                sabotage(work)
                proc = subprocess.run(
                    [sys.executable, str(TARGET), '--root', str(work)],
                    capture_output=True, text=True, encoding='utf-8', errors='replace')
        except Exception as e:                                   # noqa: BLE001
            return label, expect, 'raised', str(e)[:300]
        return label, expect, proc.returncode, (proc.stdout or '') + (proc.stderr or '')

    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=min(4, len(CASES))) as pool:
        results = list(pool.map(run_one, CASES))

    caught = missed = 0
    for label, expect, code, out in results:
        if code == 'raised':
            missed += 1
            print(f'  ❌ {label}')
            print(f'      **负样本自身失效**：{out}')
            continue
        ok = code == 1 and expect in out
        if ok:
            caught += 1
            hits = [l.strip() for l in out.splitlines() if l.strip().startswith('❌')]
            print(f'  ✅ {label}')
            print(f'      exit=1，命中「{expect}」｜{hits[0] if hits else ""}')
        else:
            missed += 1
            print(f'  ❌ {label}')
            print(f'      **漏报**：预期 exit=1 且命中「{expect}」，实际 exit={code}')
            for l in (out or '').strip().splitlines()[-6:]:
                print(f'      | {l}')

    print(f'\n负样本结果: {caught} 抓到, {missed} 漏报')
    if missed:
        print('⚠️  存在漏报 —— 闸门的判据有盲区，不可信。请修 verify_products.py。')
        return 1
    print('✅ 全部典型错误都能被判负 —— 闸门不是空转。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
