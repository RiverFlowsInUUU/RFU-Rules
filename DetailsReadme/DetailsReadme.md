# 📘 RFU-Rules 详情

📖 本文是 [README](../README.md) 之外的补充材料：不常用的操作、需要展开的解释、上游取值与取舍。文中数字标注了取值日期。

## 📑 目录

- [🧬 1 · 三个支路与取值](#-1-三个支路与取值)
- [🔗 2 · 订阅地址、缓存与生效判据](#-2-订阅地址缓存与生效判据)
- [🤝 3 · 搭配 AWAvenue（可选）](#-3-搭配-awavenue可选)
- [📋 4 · 规则顺序](#-4-规则顺序)
- [🔄 5 · 构建与转换原理](#-5-构建与转换原理)
- [🚧 6 · OpenClash：绕过中国大陆 IP](#-6-openclash绕过中国大陆-ip)
- [📁 7 · 文件结构](#-7-文件结构)
- [✅ 8 · 一致性保证与验收](#-8-一致性保证与验收)
- [📚 9 · 来源与许可](#-9-来源与许可)

---

## 🧬 1 三个支路与取值

🧱 拦截集不是任何单一上游的翻版，是**三个支路合成**后的结果。每个支路解决另一个支路解决不了的问题。

| 支路 | 来源 | 原始条数 | 解决什么 |
|:-:|:--|-----:|:--|
| A | `217heidai/adblockfilters` 的 lite 档 | 8480 | 16 个源聚合后按中国域名清单裁剪，中文覆盖面广、质量稳定 |
| B | AdGuard Chinese · 秋风 · jiekouAD · CJX · xinggsf | 1392 | 国内 App 广告的一手来源，含 A 支路漏掉的平台主域 |
| C | Jinx `3.2.3` 明文快照 | 3815 | A/B 缺的国际广告网络与长尾，补齐召回 |

🔢 合成漏斗（2026-10-27 取值）：

```
A 8480  +  B 1392  +  C 3815
  合并去重            11914
  @@ 例外减法            -5
  静态资源剔除          -60
  功能域剔除           -349
  灰产随机长尾剔除    -1934
  语义上提后           9534
  后缀剪枝             -412
  最终交付             9122
```

⚖️ **为什么必须三支路**：只用 B 支路时对 Jinx·中国生态的覆盖率是 46.8%。拆开数了一遍，缺口里 **85% 不是被筛掉，而是那 5 个源里根本没有**（`a.alimama.cn`、`acookie.alimama.com` 之类）。lite 是 16 源浓缩的另一条路线，Jinx 是第三条，三者互补——并联后覆盖率 95.4%。

🚫 **灰产怎么被挡在外面**：不靠人逐条判断，靠结构判据。灰产的形态是「随机域名 + 归属域下孤立 1 条」，而真平台至少满足「归属域成簇（≥2 条）」或「名称含广告/统计/PCDN 语义词元」之一。

⚖️ 三个支路**不等权**，判据也不同：

| 支路 | 施加的过滤 |
|:-:|:--|
| A 217heidai lite | 剔「孤立 1 条 + 元音比例低 + 含数字」的随机域（本轮剔除 1934 条） |
| B 5 个中文源 | 准入 = 成簇(≥2) **或** 含语义，两者皆无者出局 |
| C Jinx 3.2.3 | **不过滤** —— 它是人工维护的成品清单，再筛一遍会误删真广告 |

📌 因此产物里仍有 93 条形态随机的域名（占 1.0%），其中 40 条来自 C 支路。这是有意的取舍：宁可留一点噪声，不动可信源的判断。

🧩 **白名单怎么来的**：上游白名单（324 条）中会被黑名单命中的 **44 条**，加 **5 条**手工补充（`*.tange365.com`，「小鲸看看」相机 App 的账户 / 设备 / 云存储域；`*.wechatos.net`，用户指定放行；`*.za.group`，众安银行 App 业务域，2026-10-10 实测；`*.itunes.apple.com`，用户指定「任何前缀 + itunes.apple.com」直连；`*.aspect-upush.umeng.com`，友盟推送建连入口，2026-10-27 追加），共 50 条。

⚖️ 白名单的对照面是**上游黑名单** —— 生成时不把 `custom-*.list` 算进去，所以手工追加的域名**不会**因为「上游已放行」而被白名单豁免。跟上游白名单对着干等于静默误杀，这条前提见 [`skill/SKILL.md`](../skill/SKILL.md)。

> [!IMPORTANT]
> 拦截集里有 `umeng.com`、`tanx.com`、`getui.net` 这类平台主域，它们的后缀范围覆盖了放行清单中的功能子域。**不要为了「去重」把这些主域从拦截集里删掉，也不要把白名单那行删掉** —— 正确机制是白名单排在拦截之前，更具体的规则先命中 DIRECT。删任何一侧都会造成推送或登录失效。

| 客户端 | 文件 | 格式 | 条数 | 用途 |
|:-------|:-----|:-----|-----:|:-----|
| mihomo / OpenClash | `mihomo-ads.yaml` | `classical` | 9141 | 拦截 |
| mihomo / OpenClash | `mihomo-direct.yaml` | `classical` | 50 | 放行 |
| Surge / Egern | `surge-ads.list` | `RULE-SET` / `rule_set` | 9141 | 拦截 |
| Surge / Egern | `surge-direct.list` | `RULE-SET` / `rule_set` | 50 | 放行 |
| sing-box | `sing-box-ads.json` | `source` | 9141 | 拦截 |
| sing-box | `sing-box-direct.json` | `source` | 50 | 放行 |

🔵 **Egern 复用 Surge 那份文件**：两者规则集格式同源（`DOMAIN-SUFFIX` / `DOMAIN` 逐字相同），无需独立产物。引用位置有两处：`rules` 段的 `rule_set`（连接阶段）、`forward` 段的 `proxy_rule_set`（DNS 阶段）。依据：姊妹仓 [Self-Configuration](https://github.com/RiverFlowsInUUU/Self-Configuration) 四份现役 Egern profile 均如此引用，并将这两份登记为「共用规则集」。

---

## 🔗 2 订阅地址、缓存与生效判据

🔀 两个源内容完全一致，路径一一对应，**只换前缀**：

| 源 | 前缀 | 特点 |
|:---|:-----|:-----|
| Raw GitHub | `raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/` | 官方直读源，不经第三方 CDN；文件增删改名后与仓库一致、删文件无需 purge。**国内常被墙。** |
| jsDelivr | `cdn.jsdelivr.net/gh/RiverFlowsInUUU/RFU-Rules@main/` | 国内直连更稳；多一层第三方缓存，删文件后不 purge 仍返回旧内容。 |

⏱️ **缓存与生效判据**（2026-09-22 实测）：

- ⏳ `raw` 自己也有边缘缓存 —— 推送后约 **3 分钟**才返回新内容，且 `?v=<日期>`、`Cache-Control: no-cache` 对它**都无效**。别拿 raw 当「已生效」的判据。
- 🧊 jsDelivr 缓存更厚。急用加 `?v=<日期>`，或走 purge 接口：
  `https://purge.jsdelivr.net/gh/RiverFlowsInUUU/RFU-Rules@main/<文件>` —— 返回 `"status": "finished"` 即生效。
- 🔍 **判断「是否生效」的权威判据只有 GitHub Contents API**（直读 git 对象，不过 CDN）：
  `GET /repos/RiverFlowsInUUU/RFU-Rules/contents/<路径>?ref=main` → base64 解码后比对本地 md5。
  中文路径要 `urllib.parse.quote`。raw / jsDelivr 的滞后**不等于**推送失败。

📛 **旧地址**：仓库 2026-10-27 由 `Jinx` 改名为 `RFU-Rules`，GitHub 会为旧路径保留重定向，但**不要依赖它** —— 重定向在有人用旧名重建仓库时会失效。请把客户端里的地址换成新前缀。

---

## 🤝 3 搭配 AWAvenue（可选）

➕ **AWAvenue 秋风广告规则** —— 独立的第三方去广告规则集。**本仓拦截集已内含其绝大部分**（969 条中收了 912 条），所以叠加是**可选项**，不是必需项。

⚠️ 叠加的收益只剩「补上那 57 条」，代价是几百条重复（重复命中同样是 REJECT，无副作用）。如果你只是想让某个漏拦的广告消失，先看它在不在本仓规则集里，再决定要不要加这一层。

📎 **只给 Raw 源**：它由对方托管，缓存我们 purge 不了 —— 列一个 jsDelivr 备用等于把别人的缓存层写进本文档，出问题也解释不清。

📌 **要 `RULE-SET`，不要裸域名版**：`Filters/` 下另有一份 `AWAvenue-Ads-Rule-Surge.list`，那是**裸域名**格式（`.8le8le.com` 这类带前导点，DOMAIN-SET 语义），与 `RULE-SET` 的消费方式不匹配。两份条数也不同：裸域名版 **961** 条，`RULE-SET` 版 **965** 条 —— 差额正好是它写不出的 4 条 `DOMAIN-KEYWORD`。

🔢 条数以它文件头的 `#Total lines` 为准（2026-09-22 为 v1.7.8：`RULE-SET` 965 / 裸域名 961 / `Clash-Classical` 965）。上游每日更新，**别用自己数的行数去否定它的自报值**。

🔵 **sing-box 侧用官方现成的 `AWAvenue-Ads-Rule-Singbox.json`**（2026-09-28 实测）：

- 📐 它已是 rule-set 的 **source 格式**（`version: 3`，1.14.2 内核 `rule-set compile` 验证兼容），订阅即用。
- 🔍 条数 965 与 `RULE-SET` 版同源：`domain` 949 + `domain_suffix` 12 + `domain_keyword` 4 —— 4 条关键词规则在 sing-box 里有原生 `domain_keyword` 字段，无转换损失。
- 🚫 本仓不镜像这份文件：官方每日更新，快照必然滞后，且官方已是目标格式、镜像无加工价值。

🔗 由 [TG-Twilight/AWAvenue-Ads-Rule](https://github.com/TG-Twilight/AWAvenue-Ads-Rule) 维护（GPL-3.0）· 更多格式见[官方订阅生成器](https://awavenue.top/Sub.html)。

---

## 📋 4 规则顺序

🔽 自上而下，先匹配先赢。

| 顺序 | 规则 | 去向 |
|:-:|:-----|:-----|
| 1 | ✅ 白名单 | `DIRECT` |
| 2 | 🚫 广告拦截 | `REJECT` |
| 3 | 🚦 常规分流（`GEOSITE,cn` / `GEOIP,cn`） | `DIRECT` |

⚠️ 国内广告域名多数同时属于「中国大陆域名」。`GEOSITE,cn` 排在 `REJECT` 之前会先命中放行，广告规则不再有机会执行。

✅ **验证**：打开一个带广告的 App，面板中出现 `rfu-ads` 命中即顺序正确；只看到 `cn` / `DIRECT` / `Final`，则把 `REJECT` 提前。

---

## 🔄 5 构建与转换原理

🏗️ 生成链是三段，顺序不可交换（`bash skill/scripts/regen.sh` 一次跑完）：

| 段 | 命令 | 产出 |
|:-:|:--|:--|
| 1 | `skill/scripts/freeze_upstream.py` | `upstream/` 六个源 + `manifest.json`（sha256） |
| 2 | `skill/scripts/build_ads.py` | `build/ads/ads-src.txt` + 审计（三支路合成） |
| 3 | `skill/scripts/convert_ruleset.py` | 六份产物（三平台 × 拦截/放行） |

🔒 **构建不联网**：构建链第 3 步只读 `upstream/` 与 `build/`。上游要更新时，唯一允许联网的入口是 `freeze_upstream.py`，改动会留在 git diff 里可审计。这样「产物 == 生成链重跑」才是个能成立的断言，而不是对着远程源赌运气。

🔄 **转换语义**：

| 产物侧写法 | 含义 | mihomo | Surge | Egern | sing-box |
|:---------|:-----|:-------|:------|:------|:---------|
| 拦截集 `x.com` | 该域 + 全部子域 | `DOMAIN-SUFFIX` | `DOMAIN-SUFFIX` | 同 Surge | `domain_suffix` |
| 放行集 `x.com` | 仅精确，不继承子域 | `DOMAIN` | `DOMAIN` | 同 Surge | `domain` |
| 放行集 `*.x.com` | 该域 + 全部子域 | `DOMAIN-SUFFIX` | `DOMAIN-SUFFIX` | 同 Surge | `domain_suffix` |

- 🎯 **本仓产物已无通配**：拦截集 9141 条全部是 `DOMAIN-SUFFIX`，`DOMAIN-REGEX` / `DOMAIN-WILDCARD` 为 0。上游里那些内嵌星号规则（159 条）在 DNS 层无法表达，已在构建阶段丢弃并计数；能无损降为后缀的（105 条 `*.x.com`）则降为后缀 —— 于是三端语义天然一致，不需要写法映射。
- 🌳 `DOMAIN-SUFFIX` / `domain_suffix` 覆盖整个子域树；误杀用白名单放行。
- 🧱 仅域名级拦截，同域内嵌广告需 MITM / URL 级规则。
- ⏭️ 上游 `url_*` / `mitm_skip_domains` 依赖 MITM 上下文，未转换。
- 🧹 带 `$` 修饰符的规则（`||x^$third-party` 这类）一律不进产物 —— DNS 层没有「第三方」「资源类型」概念，强行降级等于把条件拦截变成无差别拦截。

🔬 **sing-box 侧的语义实证**（内核 1.14.2 · 2026-09-28）：

- 📐 `domain_suffix: ["example.com"]`（不带点）命中自身 + 全部子域，**域段级边界**（`aexample.com` 不误命中）—— 实证 `sagernet/sing` 的 `common/domain/matcher.go`：trie 按「`.` 段边界 + 叶子」判定，与 mihomo `DOMAIN-SUFFIX` 等价；前导点写法 `.example.com` 才是「仅子域、不含自身」，本仓不用。
- 🧊 文件是 rule-set 的 **source 格式**（JSON，`"version": 2` = sing-box 1.10+；本集只用 `domain_suffix`，不需要 5 = 1.14+ 的专有字段，写 5 会把 1.10~1.13 的用户挡在门外），不是二进制 `.srs` —— 远程规则集 `format: "source"` 直接消费，订阅即用无需本地编译。

---

## 🚧 6 OpenClash：绕过中国大陆 IP

📌 `china_ip_route`（默认常开）把中国大陆域名集写入 `fake-ip-filter`：这些域名解析到真实 IP，防火墙判定目标属大陆后直接放行，**连接不进入内核** —— 规则不生效，日志里也没有记录。国内 App 的广告 / 埋点 SDK 多挂在大厂域名下（`*.volces.com`、`*.bytedns.com`），天然落进该域名集。

关闭：

```bash
uci set openclash.config.china_ip_route='0'
uci commit openclash
/etc/init.d/openclash restart
```

📎 `fake-ip-filter` 里 NTP / STUN / 局域网等硬编码条目不受影响；域名访问多一跳内核，纯 IP 直连不受影响。回滚：`'0'` → `'1'`。

---

## 📁 7 文件结构

```
RFU-Rules/
├── 🔷 mihomo-*.yaml    # 2 份：拦截 / 放行
├── 🔶 surge-*.list     # 2 份，与 mihomo 一一对应
├── 🔵 sing-box-*.json  # 2 份，与 mihomo 一一对应（rule-set source 格式）
├── 📝 custom-*.list    # 2 份人工维护源（--extra / --extra-white）
├── 🧷 OVERLAP.md        # 白名单 × 拦截集重叠清单（构建生成，CI 校验）
├── 📄 WHITELIST-SLIM.md # 白名单瘦身留痕：44 保留 + 279 裁掉的逐条依据（CI 校验）
├── 📄 NOTICE.md        # 来源与使用条件（数据 / 脚本分开授权）
├── 📦 upstream/        # 冻结的上游快照 + manifest.json（构建输入，勿手改）
├── 🏗️ build/           # 三支路合成的中间结果（gitignore，不入库；产物在根目录）
├── 🧪 skill/
│   ├── 📄 scripts/     # freeze_upstream.py · build_ads.py · convert_ruleset.py · regen.sh
│   └── ✅ tests/       # verify_products.py（16 段断言）· selftest_negative.py（负样本）
├── 🔁 .github/         # CI：每次提交自动跑上述两个脚本
├── 📐 .gitattributes   # 全仓文本 eol=lf（跨平台产物逐字节可复现）
└── 📁 DetailsReadme/   # 本文档
```

📌 `mihomo-*.yaml` 是顶层 `payload` 列表，`surge-*.list` 是 RULE-SET 文本，`sing-box-*.json` 是 rule-set source 格式，**内容不可互换**。`custom-*.list` 与 `upstream/` 是输入，其余是生成物 —— 生成物重跑一次即被覆盖。

---

## ✅ 8 一致性保证与验收

🧱 本仓对外承诺三条：**三端逐条等价、产物只能由生成链产出、条数与文档一致**。它由 `.github/workflows/ci.yml` 在每次 push / PR 自动校验，闸门是 [`skill/tests/verify_products.py`](../skill/tests/verify_products.py)（16 段）：

| 段 | 守什么 |
|:-:|:-------|
| 1 | 六份产物存在且非空 |
| 2 | 三格式条数一致（ads 三份互等 / direct 三份互等） |
| 3 | **跨格式逐条语义等价** —— 归一化后比对，不是只比条数 |
| 4 | 文件头 `# entries` 自述 == 实际条数 |
| 5 | README / DetailsReadme 的条数声明 == 文件实际 |
| 5b | 文档声明的**上游版本号与快照日期** == `upstream/jinx-3.2.3/version.json` |
| 6 | **产物 == 生成链重跑结果**（先跑构建器，再跑转换器） |
| 6b | 冻结快照自述计数 == 源文件实际；且 `upstream/` 全部文件 sha256 与 manifest 一致 |
| 6c | `WHITELIST-SLIM.md` == 独立复算：摘要三项（总/留/裁）+ 保留、裁掉两个集合逐条相等 |
| 7 | `custom-*.list` 的表头声明与实际条数一致，且每条都真的落进产物 |
| 8 | 文案规范：emoji 只在行首结构位 + 密度下限 |
| 9 | 行尾符与 BOM |
| 10 | 平台清单齐备（仓库简介 / README / 本文档 / SKILL 都要列全平台） |
| 11 | 表格内 emoji 宽度一致（带 `U+FE0F` 的会占两格、导致该行错位） |
| 12 | `OVERLAP.md` 与当前产物一致 —— 独立复算重叠集合，摘要五项 + 逐条清单都要对上 |
| 13 | 仓内「第 N 段」引用 == 真实段标 —— 段号是手写常量，已四次随拆分漂移 |

🔒 **6b 段为什么重要**：它挡的是「有人手改了 `upstream/` 里的文件」。手改上游等于悄悄换了合并基线，而第 6 段只会照着被改过的源重跑 —— 照样全绿。所以快照完整性必须单独校验。

🔢 退出码沿用姊妹仓的四态协议：`0` 过 / `1` 判负 / `2` 环境不达标 / `3` SKIP。**SKIP 用独立码 3，不借 0 蒙混** —— 姊妹仓记录过一次事故：SKIP 与「环境不达标」并成同码，导致汇总脚本把环境故障吞成 SKIP、以 exit 0 假绿。

🧷 构建不联网，`upstream/` 已入库，所以第 6 段在 CI 与本地都会真正执行，不再有 SKIP 这一态。

⚠️ 闸门自身也可能退化。`selftest_negative.py` 专治这个：它在临时副本仓里制造十余种典型错误，要求闸门**逐一判负**，有漏报即判负。一个只会全绿的闸门与没有闸门等价 —— 这是本仓踩过的「永远绿的空操作」教训。

🧪 已记录的两次自证教训，留痕备查：

- ① 覆盖率断言曾用「Jinx 当基线」，而 Jinx 本身就是支路 C —— 91.5% 等于自己证自己。现改用 AWAvenue（产物只部分采用）作基线，护栏 85%。
- ② 语义准入的断言曾与准入规则同构（「产物不得含孤立且无语义条目」），必然全绿。现改为三条**独立可失败**的断言：静态资源域为 0、必需域在位、规模护栏。

📏 **行尾统一（2026-10-04 修复）**：根本原因是 `convert_ruleset.py` 曾用 `write_text(text)` 写出，Python 的通用换行转换会把 `\n` 按平台写成 `os.linesep` —— **Windows 出 CRLF、Linux 出 LF**。修法两条腿：脚本改为 `newline=''` 钉死 LF；新增 `.gitattributes` 声明全仓文本 `eol=lf`。

📌 规则集按行解析、客户端都会 trim 行尾，故 CRLF 与 LF 对功能等价 —— 归一化只为「跨平台产物逐字节可复现」这一工程目标，不改任何语义。

---

## 📚 9 来源与许可

| 项 | 值 |
|:---|:---|
| 📦 上游 | [`VME98/jinx-rules`](https://github.com/VME98/jinx-rules) · 数据 `3.2.3` · `2026-10-18` |
| 🧩 数据源 | `217heidai/adblockfilters` · AdGuard Chinese · 秋风 AWAvenue · CJX · xinggsf · jiekouAD |
| 📜 上游许可 | 均未声明（`license: null`） |
| 📄 规则数据 | 版权归各上游及其原始来源，不主张任何权利 |
| 🧪 `skill/` | 构建脚本与方法论，不含上游数据，可自由取用、修改、再分发 |

📮 上游自 `3.2.4` 起转为加密发布（`new-rules/*.enc`，需接收方私钥），明文 `rules/` 冻结在 `3.2.3`。本仓以该明文快照为基线、**不再跟随**，也不尝试解密。任一上游作者或权利人如有异议，开 issue 即下架对应来源。

---

[🏠 回到 README](../README.md)
