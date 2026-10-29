---
name: rfu-rules-maintain
description: 维护 RFU-Rules 这份「中文广告 / 统计 / 隐私 / PCDN 域名规则集」—— 冻结上游快照、三支路合成、三平台产物生成、16 段一致性断言与负样本自测，以及加新源 / 加新平台 / 改文件名三类结构性改动的一次性全套清单。含跨平台规则语义映射（mihomo / Surge / Egern / sing-box）、白名单瘦身与顺序保护、Surge pre-matching 与 extended-matching 的硬约束、README 交付规范。触发词：RFU-Rules、规则集维护、加规则源、三支路合成、freeze_upstream、build_ads、convert_ruleset、DOMAIN-SUFFIX、rule-provider、RULE-SET、去广告规则仓库、白名单瘦身、快照冻结。
agent_created: true
---

# RFU-Rules 维护手册

## 适用

本仓交付一份**中文广告 / 统计 / 隐私采集 / PCDN 域名规则集**，同时输出 mihomo(OpenClash) / Surge / Egern / sing-box 四端格式。本文件是它的施工图：怎么重跑、怎么加源、怎么改结构、哪些线不能越。

## 本仓是什么（2026-10-27 起的身份）

| 项 | 值 |
|---|---|
| 仓库 | `RiverFlowsInUUU/RFU-Rules`（原名 `Jinx`） |
| 性质 | **合成规则集** —— 三支路合并后裁剪 |
| 上游 | 六个源全部落盘 `upstream/`，构建不联网；jinx 钉死 3.2.3，其余每周定时刷新 |
| 产物 | 六份：三平台 × 拦截(`ads`) / 放行(`direct`) |
| 现读数 | `ads 9141` / `direct 50` |

⚠️ **它不再是「上游的格式转换镜像」。** 2026-10-27 之前它只做格式转换、承诺「规则一条不增不减」；现在 `ads` 是三支路合成，与任何单一上游都不等长。这条承诺只对 `direct` 还成立。**改任何东西之前先分清你动的是哪一半。**

⚠️ **jinx 钉死在 3.2.3；其余上游每周刷新，但构建永远只读快照。** jinx 自 `3.2.4` 起只发加密包（`new-rules/*.enc`，需接收方 P-256 私钥），明文 `rules/` 停在 `3.2.3` —— 本仓把那份明文钉成 `upstream/jinx-3.2.3/`，不跟随、不解密；明文通道若哪天恢复，按「新增一个源」处理。其余五个中文源由每周定时工作流（`.github/workflows/update.yml`）拉最新重建。刷新归刷新，架构不变：任何时刻构建只读 `upstream/` 快照、不联网，CI 的可复现断言对着提交进仓的快照跑，与上游怎么滚动无关。

## 铁律

1. **先量化，再动手。** 判断「某 App 广告漏拦」不要靠试错：先把该域拿去比对三支路，看它是「源里没有」还是「被准入规则筛掉」—— 这两者的修法完全不同（前者加源，后者改判据）。
2. **构建只读 `upstream/`，不联网。** 唯一允许联网的入口是 `freeze_upstream.py`。任何「跑脚本时顺手拉一下远程」的写法都会让「产物可复现」这条断言失去意义。
3. **不手改产物。** 六份文件是生成物，重跑一次即被覆盖。要改内容就改输入（`custom-*.list` / `upstream/` / 构建器判据）。
4. **不手改 `upstream/`。** 它有 sha256 清单（`upstream/manifest.json`）。手改上游等于悄悄换掉合并基线，而第 6 段只会照着被改过的源重跑、照样全绿 —— 这类失真只能靠第 6b 段挡。
5. **规则顺序是生死线。** `direct` 必须排在 `ads` 之前。拦截集里有平台主域（`umeng.com` / `tanx.com` / `getui.net`）覆盖了放行清单的功能子域，靠「更具体的规则先命中 DIRECT」保护。顺序颠倒 = 推送和登录失效。
6. **不给拦截行加 `pre-matching`。** 它会把 REJECT 抽到所有规则之前评估，`direct` 那行永远轮不到。
7. **改完必跑两层闸门**，缺一不可：`verify_products.py` 判对错，`selftest_negative.py` 证明闸门自己还能抓错。
8. **本仓不发版；上游快照每周自动刷新，jinx 除外。** 订阅地址钉在 `main`，客户端自行按 `update-interval` 拉取；社区同类规则仓（blackmatrix7 / hagezi / Sukka）均如此，Release/tag 与滚动数据模型不匹配 —— 唯一的 `v3.2.3-2026.10.27` 孤版 Release 已于 2026-10-27 删除，本仓无任何发版物。快照刷新只走 `.github/workflows/update.yml`（每周一 03:00 UTC，可手动触发）或手动跑 `freeze_upstream.py`，**有 diff 才提交，无 diff 静默结束**；抓取失败即整体失败，不提交半新半旧的快照。jinx 的 `JINX_COMMIT` 任何情况下不动。

## 构建链（三步，顺序不可交换）

```bash
# ① 冻结上游（唯一联网步骤；已有快照时可用 --check 只校验）
python skill/scripts/freeze_upstream.py --check    # 先确认快照未被手改
python skill/scripts/freeze_upstream.py            # 需要更新时

# ② 三支路合成 → build/ads/ads-src.txt + 审计
python skill/scripts/build_ads.py

# ③ 六份产物
python skill/scripts/convert_ruleset.py --src upstream/jinx-3.2.3 --out . \
    --fixed whitelist.txt --wild whitelist_wildcard.txt \
    --tag direct --mode exact --naming repo \
    --guard-against-fixed blacklist.txt \
    --guard-against-wild blacklist_wildcard.txt \
    --extra-white custom-direct.list
python skill/scripts/convert_ruleset.py --src build/ads --out . \
    --fixed ads-src.txt --tag ads --mode suffix --naming repo \
    --extra custom-ads.list
```

**日常等价于一条：**

```bash
bash skill/scripts/regen.sh          # 校验快照 → direct → ads → 读数同步 → 闸门
bash skill/scripts/regen.sh --build  # 只重建，不跑闸门
```

⚠️ **读数同步（v10 审查缺陷 2）**：`regen.sh` 在闸门前跑 `sync_doc_counts.py`，
把 README / SKILL / DetailsReadme 的条数声明对齐产物实际 —— 没有它，周更工作流
会在上游条目一变时就死于第 5 段判负（有 diff 也提交不出去）。闸门不读同步脚本
的输出、只对文件实际，同步错了照样红，不构成同构互保。模式清单与第 5 段锚点
同源，改版式时两处一起改。

落盘物：仓库根六份产物 + `OVERLAP.md`（白名单 × 拦截集重叠清单）+ `WHITELIST-SLIM.md`（白名单瘦身留痕）。
后者不是附带产物 —— 那 40 来条域名只能靠「放行行更早命中」存活，
消费端一旦把 REJECT 提前（Surge `pre-matching`），它们全部失效。所以它必须
**入库、可被订阅者看到、被 CI 校验**，而不是躺在 gitignore 的 `build/` 里。

预期读数：`ads 9141` / `direct 50`。⚠️ 这行读数随 `upstream/` 与判据变化，写完必跑闸门核对 —— 它同时校验文档声明与产物实际。

⚠️ `--src` 的写法会**原样进产物表头**（`# source: build/ads` / `# source: upstream/jinx-3.2.3`）。这两条命令写法本就不同，**不是笔误**；别为了「统一」给其中一条加 `./`，否则表头变、第 6 段立刻判负。

⚠️ `--extra` / `--extra-white` 是 `nargs='*'`：**必须放在命令末尾**，或后面紧跟另一个 `--选项`；否则会把后面的位置参数当成文件名吞掉。

## 三支路的职责划分

| 支路 | 输入 | 解决什么 | 别指望它 |
|:-:|:--|:--|:--|
| A | `upstream/217heidai/adblocksurgelite.list` | 16 源聚合 ∩ 中国域名清单，中文面广 | 广告子域系统性缺失（清单按主机名枚举，广告域天然不被收录） |
| B | `upstream/cn/*`（5 个中文源） | 国内 App 广告的一手来源 | 国际广告网络、平台主域 |
| C | `upstream/jinx-3.2.3/blacklist*.txt` | 补 A/B 的国际广告与长尾 | 已冻结，不会再有新条目 |

⚠️ **A 支路的方向性缺陷要记住**：lite 是「全量 ∩ china.txt」，而 `china.txt` 是**分流用的直连清单**，收的是用户会访问的功能域。拿功能域白名单去筛广告黑名单，方向是反的 —— 所以它既漏广告子域，又混进功能域（`c.uaa.iqiyi.com` 统一账号认证、`cm.passport.iqiyi.com` 登录）。这两类问题分别靠 B/C 补漏、靠功能域判据剔除。

## 七条构建规矩（全部确定性、可断言）

| # | 规矩 | 依据 |
|:-:|:--|:--|
| 1 | 只做 DNS 层能表达的减法 | `$` 修饰符、`##` 元素隐藏、`@@\|\|x/path` 不进产物 —— 强行降级等于把条件拦截变成无差别拦截 |
| 2 | `@@` 例外只做减法，**不生成 DIRECT 行** | 不在拦截集里就落回常规分流，路由自动正确。塞进 `direct` 反而引入顺序依赖 |
| 3 | 只输出 `DOMAIN-SUFFIX` | 三端语义天然一致，不需要写法映射；且避开最贵的逐条正则扫描 |
| 4 | 只拦域名，不拦 IP | IPv4 / CIDR 在提取阶段剔除 |
| 5 | 静态资源硬排除 | label 以 `static` / `download` / `status` / `update` 开头者剔除，**不受成簇豁免**。实证：`s.bdstatic.com`、`static-s.iqiyi.com` 被拦会让页面挂图裂 |
| 6 | 功能域排除要留豁免 | 含 `push`/`passport`/`login`/`uaa`/`doh`/`im`/`subscription` 等词元且无广告语义者剔除；但 `ad` 词根（`advertising-api.amazon.com`）与平台痕迹（`unity3d`/`snssdk`）必须豁免 |
| 7 | 灰产靠结构，不靠语义 —— **但三支路不等权** | A 支路：剔「孤立 1 条 + 元音比例低 + 含数字」的随机域；B 支路：准入 =「成簇(≥2) **或** 含语义」；**C 支路不做过滤**（它是人工维护的成品清单，再筛会误删真广告）。实测：产物里 93 条形态随机域中 40 条来自 C 支路，这是有意的 |

⚠️ **语义判定必须词元级，不许子串。** 曾用裸 `"ad"` / `"stat"` / `"log"` 做子串匹配，把 `static`、`bdstatic`、`download`、`prologue` 全命中，误收 276 条静态资源域。现在按 label 切词元精确比对。

⚠️ **`api` / `sdk` / `gateway` / `openapi` 不是功能词。** 它们几乎出现在每个广告 SDK 端点里（`api-spe.isnssdk.com`、`o-sdk.mediation.unity3d.com`），不具备区分力，曾因此误删一批真广告。

## 加一个新源（可复用的方法论）

1. **先看形态**：拿到源文件，数它有几类写法（`||x^` / 裸域名 / `hosts` / `##` 元素隐藏 / `$` 修饰符），DNS 层能表达的只有前两类。
2. **再看语义**：黑名单一般是后缀语义（子域也拦），白名单一般是精确语义。搞反的后果都是灾难性的 —— 黑名单用精确会漏光子域，白名单用后缀会整族放行。
3. **量化独占贡献**：新源对现有并集的**独占**条数是多少？实测过 EasyList_China 对核心四源的独占贡献是 **0**（与 AdGuard Chinese 完全重叠），于是整源排除。不做这一步会白养一个源。
4. **量误杀面**：拿 `surge-direct.list` 去撞，看新源会打到多少条功能域。
5. **加进 `freeze_upstream.py` 的 `SOURCES`**，跑一次重新冻结 + `regen.sh`，看漏斗数字与覆盖率断言。

⚠️ **别从 `full` 反筛。** 「从 24 万条里筛出中文广告域」没有权威判据：「中文广告域」不是字符属性，广告与功能同族（`cupid.iqiyi.com` 广告 / `c.uaa.iqiyi.com` 登录），粒度也不可从规则本身推。要么取源原件，要么加源。

## 加一个新平台（客户端）

新平台 ≠ 新源。加一端的产物要动四处，漏一处就变成「只支持一半」：

| # | 位置 | 改什么 |
|:-:|:--|:--|
| 1 | `convert_ruleset.py` | 照现有三个写出函数（`mihomo_yaml` / `surge_ruleset` / `singbox_json`）的形状加一个，并挂进 `outputs` 列表 |
| 2 | `verify_products.py` | `PRODUCTS` 加文件名；加 `parse_xxx`；`seg_cross_format` 的类型映射（`SB_FIELD` / `SURGE_ALIAS` 之类）补齐 |
| 3 | 面向外部的五处清单 | README 徽章行 / 订阅表行 / 接入节 `<summary>` / DetailsReadme 订阅表行 / `upload_to_github.py` 的 `--description` 默认值。第 10 段逐一检查，缺一处就红 |
| 4 | 文档示例 | README 接入示例 + DetailsReadme 转换原理表加一列，否则读者不知道怎么配 |

⚠️ 平台名要用**固定写法**（`sing-box` 而不是 `Singbox`）—— 第 10 段按名字匹配，写歪了等于没加。
⚠️ 若新平台复用已有格式（Egern 复用 Surge），**不要造产物**，把它加进 `PLATFORM_LABEL` 的别名表即可。
⚠️ 加完回头跑 `selftest_negative.py`：两条「平台清单缺一端」样本锚在表头与简介默认值上，版式一改就会抛「负样本失效」—— 那是提醒，不是漏报。

## 匹配语义与通配映射（接新源时用）

| 源写法 | mihomo | Surge | sing-box | 说明 |
|---|---|---|---|---|
| `x.com`（黑名单） | `DOMAIN-SUFFIX,x.com` | `DOMAIN-SUFFIX,x.com` | `domain_suffix: ["x.com"]` | 后缀语义：域名 + 全部子域 |
| `x.com`（白名单） | `DOMAIN,x.com` | `DOMAIN,x.com` | `domain: ["x.com"]` | 精确语义：仅该域名本身 |
| `*.x.com` | `DOMAIN-SUFFIX,x.com` 或 `+.x.com` | `DOMAIN-SUFFIX,x.com` | `domain_suffix: ["x.com"]` | mihomo 的 `*.x.com` **只匹配一级且不跨点**，直接用会漏多级子域 |
| `p*-ad.x.com` | `DOMAIN-REGEX,^p.*-ad\.x\.com$` | `DOMAIN-WILDCARD,p*-ad.x.com` | `domain_regex: [...]` | mihomo 不支持星号内嵌；sing-box 用 Go RE2，转换式同 mihomo |
| `.x.com` | `.x.com`（多级子域，不含裸域） | — | `domain_suffix: [".x.com"]` | mihomo 专有 |
| `+.x.com` | `+.x.com`（多级子域含裸域） | — | `domain_suffix: ["x.com"]` | mihomo 专有 |

**官方依据**：mihomo `wiki.metacubex.one/handbook/syntax/`；Surge `manual.nssurge.com/rules/domain.html`（`*` 跨点匹配、`?` 单字符、支持 `[...]` 字符类）；sing-box `sing-box.sagernet.org` rule-set。sing-box 的 `domain_suffix` 不带点 = 自身 + 全部子域（域段级边界，`aexample.com` 不误命中），前导点 = 仅子域。

⚠️ **本仓产物目前零通配**（全部 `DOMAIN-SUFFIX`），上表是接新源 / 新格式时的参照。上游里内嵌星号的 159 条在构建阶段丢弃并计数 —— 这是有意的取舍，不是遗漏。

## 白名单瘦身与顺序保护

上游白名单里有大量「为别的规则集准备的」域名（`github.com` / `dns.google` / `jsdelivr.net` / `dropbox.com` / `icloud.com`），整份前插等于把它们全部强制直连，在国内网络下是负优化。

只保留**会被当前黑名单误杀**的条目，判据三种关系：`exact`（等于黑名单精确条目）、`glob`（被通配规则匹配）、`sub`（是黑名单条目的子域 —— 黑名单按后缀拦截，子域同样被误杀）。

```bash
python skill/scripts/convert_ruleset.py --src upstream/jinx-3.2.3 --out . \
    --fixed whitelist.txt --wild whitelist_wildcard.txt --tag direct --mode exact --naming repo \
    --guard-against-fixed blacklist.txt --guard-against-wild blacklist_wildcard.txt
```

⚠️ 白名单**必须** `--mode exact`。用 suffix 会把整片广告域放行。

⚠️ **`guard` 是动作名，产物叫 `*-direct.*`。** 本仓 2026-10-04 已把 `*-white-guard.*` 改名为 `*-direct.*`，脚本里的变量也跟着叫 `direct` —— 别再把动作名当文件名用。

### 平台主域覆盖了功能子域时，怎么办

**正确做法：保留上层域 + 靠顺序保护。** 错误做法：把上层域从拦截集里删掉。

```
拦截集有 umeng.com（后缀）
放行集有 aspect-upush.umeng.com（友盟推送通道）
→ direct 排在前，更具体的规则先命中 DIRECT，推送不受影响
```

曾试过「删掉覆盖了放行条目的上层域」，结果 `tanx.com` / `getui.net` / `gepush.com` 整个平台后缀被删 —— 为保一个子域牺牲其余全部，漏拦面积远大于收益。`build_ads.py` 的审计第六节会列出全部重叠项，**只报告不删除**。

## 引用配置

**mihomo / OpenClash**

```yaml
rule-providers:
  rfu-ads:
    type: http
    behavior: classical        # 不能改 domain：文件是逐条规则，不是纯域名列表
    format: yaml
    url: "https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/mihomo-ads.yaml"
    path: ./rule_provider/rfu-ads.yaml
    interval: 604800
  rfu-direct:
    type: http
    behavior: classical
    format: yaml
    url: "https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/mihomo-direct.yaml"
    path: ./rule_provider/rfu-direct.yaml
    interval: 604800

rules:
  - RULE-SET,rfu-direct,DIRECT
  - RULE-SET,rfu-ads,REJECT
```

**Surge**

```
[Rule]
RULE-SET,https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-direct.list,DIRECT,extended-matching
RULE-SET,https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-ads.list,REJECT,extended-matching
```

| 参数 | 作用 | 最低版本 |
|---|---|---|
| `extended-matching` | 额外用 TLS SNI / HTTP Host 匹配，解决 App 直连 IP 导致域名规则失效 | iOS 5.8 / Mac 5.4 |
| `pre-matching` | REJECT 提前到 DNS / TCP 握手阶段 | iOS 5.14 / Mac 5.9 |
| `update-interval=<秒>` | 覆盖默认 86400 | — |

**Surge 参数三条硬约束**（官方文档原文，易踩）：

1. `pre-matching` **只支持 REJECT 系策略** —— 写在 `DIRECT` 行上无意义。
2. `pre-matching` **只能写在 profile 顶层的 `RULE-SET` / `DOMAIN-SET` 行上**，写进规则集文件内部会被忽略（文件内允许逐行写 `no-resolve` / `extended-matching`）。
3. 同一个 URL **不能**既当 `RULE-SET` 又当 `DOMAIN-SET`。

⚠️ **`pre-matching` 与本仓的白名单互斥。** 它把 REJECT 抽到所有规则之前评估，`direct` 那行永远轮不到 —— 表现是推送收不到、微信登录转圈。本仓配置一律用 `extended-matching`。

**sing-box**

```json
{
  "route": {
    "rule_set": [
      { "type": "remote", "tag": "rfu-direct", "format": "source",
        "url": "https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/sing-box-direct.json",
        "update_interval": "7d" },
      { "type": "remote", "tag": "rfu-ads", "format": "source",
        "url": "https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/sing-box-ads.json",
        "update_interval": "7d" }
    ],
    "rules": [
      { "rule_set": ["rfu-direct"], "outbound": "direct" },
      { "rule_set": ["rfu-ads"], "action": "reject" }
    ]
  }
}
```

⚠️ `download_detour` 自 1.14 废弃、1.16 移除，新配置不要写。

## 断言口径

```bash
python skill/tests/verify_products.py      # 16 段，与 CI 同源
python skill/tests/selftest_negative.py    # 负样本：证明闸门本身能抓错
```

16 段：产物存在 · 三格式条数一致 · **跨格式逐条语义等价** · 表头自述 · 文档条数 · **文档上游版本号** · **产物 == 生成链重跑** · **冻结快照自述 + sha256 完整性** · **瘦身留痕（WHITELIST-SLIM.md）== 独立复算** · `custom-*.list` 落盘 · 文案规范 · 行尾与 BOM · 平台清单齐备 · 表格 emoji 宽度 ·
**`OVERLAP.md` 与产物一致** · **段号引用 == 真实段标**。

退出码四态：`0` 过 / `1` 判负 / `2` 环境不达标 / `3` SKIP。**SKIP 走独立码，不借 0 蒙混** —— 「未验证 ≠ 绿」。

⚠️ **`selftest_negative.py` 要求先有绿基线。** 它是相对断言 —— 验证「破坏 O 后闸门能抓到」，前提是「不破坏时闸门是绿的」。工作区已脏时它会拒绝出结论（`exit=2`），先让 `verify_products.py` 回 0 再跑它。

⚠️ **断言最容易犯的错：与它要检的东西同构。** 本仓踩过两次：

| 事故 | 症状 | 修法 |
|---|---|---|
| 准入规则与断言同构 | 「产物不得含孤立且无语义条目」与准入判据完全同构，必然全绿 | 换成独立可失败的：静态资源为 0 / 必需域在位 / 规模护栏 |
| 基线与支路同构 | 拿 Jinx 当覆盖率基线，而 Jinx 就是支路 C，91.5% 等于自证 | 换成 AWAvenue（产物只部分采用）作基线 |

写新断言前先问一句：**「如果这里真的坏了，这条断言会不会因为定义相同而依然通过？」**

⚠️ **覆盖率护栏的边界与补强（v11 审查 3.1 落地）**：现行基线 AWAvenue 同时是 B 支路输入源之一（`COVERAGE_BASELINE` ∈ `B_SOURCES`），并非完全独立。该护栏防的是「上游内容退化 / 丢失」——AWAvenue 覆盖率骤降说明源文件坏了；它**不防「准入逻辑失效」**。「AdGuard DNS filter 当独立基线」的方案经实测否决（国际通用向，与 CN 向产物仅 3.1% 交集、CN 子集仅 17 条，无统计力）。实际落地的是 **⑤b 采纳率护栏**：B 支路全局采纳率带宽 (0.03, 0.60) + 单源哨兵（>98% 或恒 0），直接测准入判据本身——判据恒真/恒假当场自爆，与上游内容变化天然解耦。

## 改文件名 = 破坏性改动（订阅地址会变）

2026-10-04 那次 `*-white-guard.*` → `*-direct.*` 涉及 52 处引用；2026-10-27 仓库改名 `Jinx` → `RFU-Rules` 涉及全仓 URL。

流程：

1. **先想清代价**：改名 = 旧订阅地址失效。无法确认引用方已迁移时，宁可保留旧文件并标注废弃。
2. **单一真源是生成参数**：产物名由 `convert_ruleset.py --tag <名>` 决定。先改 `--tag`，再让 `verify_products.py` 的 `REGEN` / `PRODUCTS` 表同步，然后重跑 —— **不要用 `git mv` 手改文件名**，否则产物与生成器脱节，可复现断言会红。
3. **改完验证内容零改动**：新旧产物逐字节比对。纯改名不该动一个字节。
4. **仓库改名后立刻验证重定向**：`curl -sI` 旧 raw 地址，确认 301 到新路径；jsDelivr 需显式换前缀（它不跟随仓库重定向）。

必查清单（按最容易漏排序）：生成参数与断言表 → README 订阅表 / 接入示例 / 目录锚点 → DetailsReadme 订阅表与原理表 → 本文件的生成命令与映射表 → `custom-*.list` 表头那句「不要手改」→ 示例里的 provider / tag 名 → 仓库简介（`gh repo edit --description`）。

⚠️ **CHANGELOG 一律不改**：那里写的是「当时叫什么」，改了就是篡改历史。

## 对外交付：README 规范

- **README 只承载「怎么用」**：拿地址、贴配置、照做即生效。解释性的、需要展开的、会随上游变动的数字，一律下沉到 `DetailsReadme/`。**README 不写「我们怎么改的」** —— 改动记录进 `CHANGELOG.md`，判据与原理进 `DetailsReadme/`。
- **emoji 只许出现在行首**，不得落在句中。可用位置：标题、段落引导符、列表项、表格单元格起始、目录条目、树形框线。标题 emoji 一个就够。
- **标题带 emoji 后锚点多一个前导横线**：`## 📥 订阅` → `#-订阅`。改标题必须同步全仓 `](#...)`。
- **标题 emoji 绝不能带变体选择符 U+FE0F**：`⚙️` / `⚠️` 会让锚点混进不可见字符，手写链接点不动。只用单码位 emoji。
- **双地址，Raw 在前**：一张总览表 + 两块地址块（⭐ Raw 一块、🔁 jsDelivr 一块）。别每个文件各拆一块。
- **例外：第三方规则集只给 Raw 源** —— 缓存我们 purge 不了，多列一个备用源等于把对方的缓存层写进本文档。

## 踩坑记录

- ⚠️ **`write_text()` 会按平台改行尾，产物因此跨平台不可复现。** 必须 `write_text(text, encoding='utf-8', newline='')` 钉死 LF，再加 `.gitattributes` 声明 `* text=auto eol=lf`。两条腿缺一不可：只改脚本，仓库里仍是 CRLF，CI 判负；只归一化文件，Windows 重跑又写回 CRLF。
- ⚠️ **mihomo YAML 里的 `DOMAIN-REGEX` 要用单引号包**：正则含反斜杠，双引号会把 `\` 当转义吃掉。本仓产物已无正则，但接新源时仍会遇到。
- ⚠️ **超广通配会误杀，且白名单救不了。** `ad.*`、`ad-*` 这类一条覆盖几百条（实测 `ad.*` 单条吃掉 855 条精确条目）。这类误杀对象不在白名单里 → 白名单预知不了，只能靠运行观察。本仓的处理是**不产出通配**。
- ⚠️ **脏数据不要整条丢。** 源里会混 URL 式条目（`https://us.l.qq.com/exapp`），用正则取出 host 后照常处理。
- ⚠️ **`raw` 不能当「已生效」的判据。** 它自己有边缘缓存，推送后约 3 分钟才同步，`?v=` 无效。权威判据是 GitHub Contents API（直读 git 对象）：`GET /repos/<owner>/<repo>/contents/<path>?ref=main` → base64 解码后比对本地 md5。
- ⚠️ **Windows 快照命名别用 URL 当文件名。** URL 里的 `:` 在 Windows 非法，曾生成一个名为 `https` 的目录、快照全丢。用 `basename + sha1 前 8 位`。
- ⚠️ **`reduce-memory` 不是 mihomo 配置项**（SEO 站编的）；`GOMEMLIMIT` 只能注入环境变量，不是 YAML 字段。

## 客户端开关（规则对了也可能不生效）

**OpenClash / mihomo**：`china_ip_route=1`（绕过中国大陆 IP，默认常开）会把 `oc-cn-domain` 注入 `dns.fake-ip-filter` → 命中域解析出真实 IP → 防火墙判定属大陆直接放行 → **流量不进内核，规则引擎没机会执行**。

判据：某域名在规则集里查得到，但客户端日志 `grep` 返回 0 条（没进内核 = 没日志）。

```bash
uci set openclash.config.china_ip_route='0'
uci commit openclash
/etc/init.d/openclash restart
```

**通用验收三步**：① DNS 应答从真实 IP 变 fake-ip；② 请求被拒（连接 / TLS 失败）；③ 日志出现 `match RuleSet(<名字>) … using REJECT`。

## 定位规则源（拿不到 HTTPS 路径时）

抓包只能拿到域名（SNI / DNS），路径在 TLS 内。成本更低的办法：拿 App 侧强特征（更新时的文件名、版本号、目录结构、报错文案）去搜 GitHub 代码搜索，再用其中的数据（版本号、条目数）与 App UI 显示交叉校验 —— 从「像」升级为「就是」。
