# 🗓️ 更新日志

规则集本身的显著变动，按日期倒序。日期为 UTC+8。

---

## 2026-10-27（二）· 迭代收口：全面审计 20 项全修（含 3 个「闸门说谎」缺口）

> 📌 大改之后做了一次只读审计，结论：结构立住了，但有一批迭代残留，其中 3 项会让闸门在
> 该红的时候保持绿色。本条目全部为修正，**规则内容零变化**（9534 / 49 不变）。

**一、闸门自身的 3 个缺口（最要紧）**

- 🔍 **「12 段」实为 13 段**：`run()` 里有 13 个 section（1,2,3,4,5,5b,6,6b,7,8,9,10,11），
  而文档写「12 段」却在同一段里列了 13 项 —— 自相矛盾。已统一为 13（SKILL 3 处、Details 2 处、脚本 docstring）。
- 🔍 **SKILL 的预期读数此前无人校验**：实测把 `ads 9534` / `direct 49` 改成 `9999` / `1`，
  旧闸门仍 **70 passed / 0 failed** —— 那个判据只验「正则能匹配」，不验数字。
  现并入第 5 段（5-e）逐项比对，并删掉原来那条更弱的同名判据。
- 🔍 **README 能力矩阵的「构成描述」也无人校验**：`43 条精确 + 6 条后缀（含 5 条手工补充）`
  整体改错也不会红。现纳入第 5 段（5-d），四项分别比对（总数 / 精确 / 后缀 / 手补）。
- 🧹 新增的两条判据都做过反向验证：故意写错数字后闸门确实翻红。

**二、脚本与流程**

- 🐛 **`freeze_upstream.py` 的 `bytes` 字段口径错**：它用 `stat().st_size`（原始字节）记体积、
  却用 `read_text()`（换行归一化）算 sha。`AdGuard_Chinese_filter.txt` 原始是 CRLF（754584），
  仓库按 `eol=lf` 归一化后是 732689 —— 清单那一栏对谁都对不上（校验本身不受影响）。
  现两者统一按归一化文本计，`manifest.json` 增加 `hash_basis` 说明，表格列名改为「字节（LF 归一化）」。
  已按仓内快照重建 manifest（不联网，sha 无变化）。
- ✨ **`convert_ruleset.py` 新增 `--label`**：`--src` 的值会原样进产物表头，而 ads 的源是
  中间目录 —— 于是用户下载到的文件头顶一直写着 `# source: build/ads`（对读者毫无意义）。
  现表头固定为 `# source: upstream/(A+B+C)`，源目录可以是任意临时路径。
- ✨ **第 6 段不再往仓库里写文件**：旧版校验时会覆盖 `build/ads/ads-src.txt`（只读断言有副作用）。
  现改为构建到临时目录 + `--label` 固定表头，仓库全程干净。
- ⚡ **`selftest_negative.py` 并发化**：14 条样本各自复制整仓并跑一次完整闸门，串行 74s；
  改 4 路并发后 **26s**，结果不变（13 抓到 / 0 漏报）。
- 🔢 **`build_ads.py` 的护栏可调**：新增 `--coverage-floor` / `--size-min` / `--size-max`，
  加源时不必改源码（但正式产出仍建议把新值写回常量）。
- 🗑️ 删除 `skill/scripts/upload_repo.py`：与 `upload_to_github.py` 功能重叠且无任何引用。

**三、文档与门面**

- 🧬 README 首屏补一句「拦什么、从哪来」：四类域名范围 + 三支路构成 + 直达详情第 1 章的链接。
  （此前首屏只有「三支路合成」四个字，首次来的读者不知道是哪三条。）
- 🏷️ Source 徽章改为 **Frozen**（`Frozen-Jinx 3.2.3`）：数据确实来自 Jinx，但本仓是冻结基线，
  「Source」会让人以为在跟随。对应断言正则与负样本锚点已同步。
- ⚖️ **灰产判据的作用范围写清**：此前 SKILL 第 7 条写成全局规矩，实现却只对 A 支路生效
  （`d in A`）；B 支路用成簇或语义，C 支路完全不过滤。现已按支路分别写明，并给出实测差异
  ——产物里 93 条形态随机域中 40 条来自 C 支路，这是有意保留的。
- ➕ SKILL 补「加一个新平台」一节（description 早就承诺了，正文却没有）：四处改动点 + 三个坑。
- 🧰 修正 `convert_ruleset.py` 用法示例（仍指向已废弃的 `./jinx-rules`）、
  `custom-*.list` 表头（「上游 Jinx」是单源时代措辞）、`.gitignore`（删掉无写入路径的 `out/` `_regen/`）、
  Details 文件结构树（补 `build/`）。
- 🏷️ 仓库简介补齐四类口径，并设置 topics（`adblock` / `mihomo` / `surge` / `egern` / `sing-box` / `openclash`）。

**验收**

- ✅ `verify_products.py`：**72 passed / 0 failed**（新增 3 条判据，删 1 条重复判据）
- ✅ `selftest_negative.py`：**13 抓到 / 0 漏报**，耗时 74s → **26s**
- ✅ `freeze_upstream.py --check`：12 个文件 sha256 全一致

**未完成（唯一一项，受权限阻塞）**

- ⏳ CI 工作流换版：改 `.github/workflows/` 需要 token 具备 `workflow` 权限，当前授权没有。
  现由兼容垫片 `skill/tests/verify_jinx_src.py`（转发到 `verify_products.py`）维持旧 CI 绿色；
  旧工作流仍在每次运行时下载上游明文，与「不再跟随上游」矛盾。
  待 `gh auth refresh -h github.com -s workflow` 后一次性替换并删除垫片。

---

## 2026-10-27（二）· 定位重构：仓库更名 `RFU-Rules`，上游冻结，ads 改为三支路合成

> 📌 触发事件：上游 `VME98/jinx-rules` 自 `3.2.4` 起只发加密包（`new-rules/*.enc`，P-256-ECIES，
> 需接收方私钥），明文 `rules/` 永久停在 `3.2.3`。继续做「格式转换镜像」等于把一份不再更新的
> 数据当新产品交付 —— 而且是不会报错的静默失真。故一次性把定位、数据源、断言全部换掉。

**一、上游冻结，不再跟随**

- 📦 新增 `upstream/`：把 `3.2.3` 明文（钉死 commit `c85751d`）+ 5 个中文源 + 217heidai lite
  + `china.txt` 全部落盘入库，附 `manifest.json`（每个文件的 sha256 与取用日期）。
- 🔒 **构建不联网**：`convert_ruleset.py` / `build_ads.py` 只读 `upstream/` 与 `build/`。
  唯一允许联网的入口是新脚本 `skill/scripts/freeze_upstream.py`（`--check` 只校验）。
- 🚫 不再轮询上游、不尝试解密。`jinx-rules/`（gitignore 的临时下载目录）彻底废弃。

**二、ads 改为三支路合成 `3991 → 9534`**

- 🧬 支路 A：`217heidai/adblocksurgelite.list`（8480）· 支路 B：5 个中文源（1392）·
  支路 C：Jinx `3.2.3` 明文（3815）。
- 🔢 漏斗：合并去重 11914 → `@@` 例外减法 −5 → 静态资源 −60 → 功能域 −349 →
  灰产随机长尾 −1934 → 语义上提 9534。
  其中 C 支路：`*.x.com` 降为后缀 105 条，内嵌星号无法表达 159 条（丢弃并计数）。
- 🎯 覆盖率：对 AWAvenue（独立基线，产物仅部分采用）**94.1%**；对 Jinx·中国生态（参考）**95.4%**。
- 🧱 产物构成变化：**全部 `DOMAIN-SUFFIX`，`DOMAIN-REGEX` / `DOMAIN-WILDCARD` 归零** ——
  三端语义天然一致，也避开了最贵的逐条正则扫描。
- 🚫 明确不做的两件事：不拦 IP（IPv4/CIDR 剔除）；不收录赌博与色情灰产（靠「成簇或语义」
  结构判据排除，不做人工逐条筛选）。
- 🧩 `custom-direct.list` 追加 `*.aspect-upush.umeng.com`（友盟推送建连入口）→ 放行 `48 → 49`。
  拦截集有 `umeng.com` 后缀会罩住它，靠「direct 排在前面」保护，**不从拦截集里删主域**。

**三、仓库更名 `Jinx` → `RFU-Rules`（破坏性：订阅地址变更）**

- 🏷️ GitHub 仓库改名为 `RiverFlowsInUUU/RFU-Rules`，仓库简介同步更新（`gh repo edit --description`）。
- 🔗 六份产物**文件名不变**（`mihomo-ads.yaml` 等本身不含 `jinx`），订阅地址只有仓库名那一段变。
  旧地址由 GitHub 重定向，但 `jsDelivr` 不跟随仓库重定向，需换新前缀。
- 🏷️ 配置示例里的 provider / tag：`jinx-ads` / `jinx-direct` → `rfu-ads` / `rfu-direct`。

**四、断言体系改造（承诺变更）**

- 📌 不再承诺「规则一条不增不减」—— `ads` 是合成集，与任何单一上游都不等长。改为三条：
  三端逐条等价 · 产物 == 生成链重跑结果 · 条数与文档一致。
- 🔁 `verify_jinx_src.py` → **`verify_products.py`**（保留 12 段骨架）：数据源改仓内快照；
  第 6 段 ads 侧先跑 `build_ads.py` 再跑 `convert_ruleset.py`；
  第 6b 段新增 **`upstream/` 全部文件 sha256 vs manifest** 校验（手改上游是唯一无法被
  「重跑一致」发现的失真）。
- 🗑️ `sync_docs.py` 退役：它的职责是「上游滚了、产物没跟上时拒绝改文档」。上游冻结后这个
  风险整体消失，文档读数漂移改由第 5 / 5b 段断言守。
- 🧪 `selftest_negative.py` 扩到 **13 个负样本**，新增「手改 upstream 快照」一条；
  该样本特意选 `china.txt`（只进覆盖率播报、不进产物），以证明 sha 判据是一盘独立的守卫。

**五、清理**

- 🗑️ 删除 `test/`（`build-cn-adblock.py` 及其中间产物）—— 构建器已归位为 `skill/scripts/build_ads.py`。
- ➕ 新增 `skill/scripts/build_ads.py`（三支路构建器 + 审计）、`regen.sh`（一条命令重跑六份产物）。

**验收**

- ✅ `verify_products.py`：**70 passed / 0 failed**（含第 6 段六份产物逐字节可复现、第 6b 段 sha256 全一致）。
- ✅ `selftest_negative.py`：**13 抓到 / 0 漏报**。
- ✅ `freeze_upstream.py --check`：12 个源文件全部与 manifest 一致。

---

## 2026-10-23（五）· 放行 47 → 48：新增 `*.itunes.apple.com`

> 📌 用户指定：任何前缀 + `itunes.apple.com` 都走直连。沿 `skill/SKILL.md` 的手工域名流程执行：
> 改 `custom-direct.list` → 重跑生成 → `sync_docs.py` 推平读数 → 双闸门。本次上游无滚动
> （仍为 `3.2.3`），规则变动全部来自手工放行。

**变更**

- ✅ **放行 47 → 48 条**：`custom-direct.list` 追加 `*.itunes.apple.com`（第 4 条手工补充），生成 `DOMAIN-SUFFIX,itunes.apple.com` —— 覆盖裸域与任意层级子域，语义 = 任何前缀 + `itunes.apple.com`。
  - 依据：上游白名单只有精确条目 `itunes.apple.com` / `pd.itunes.apple.com` / `iosapps.itunes.apple.com`，且 guard 会因它们不与黑名单碰撞而裁掉；其余 `itunes.apple.com` 子域落进兜底走代理。本条目补的正是子域面。
  - 产物构成：`43 条精确 + 5 条后缀`（其中 4 条手工补充）。`from guard 44` 不变，本条落在产物末尾，不参与碰撞裁剪。
- 🐛 **负样本两处硬编码失效修复**：放行集 `47 → 48` 后，`selftest_negative.py` 的「README 订阅表」与「能力矩阵放行行」两个负样本因写死 `47` 而匹配落空（抛出「负样本失效」）。改为正则 / 行首标志动态匹配 —— 条数不再作为锚点，避免规则集条数变化时自测静默失效。
- 🔧 **读数同步**：`README.md` 放行徽章 / 订阅表 3 行 / 矩阵放行行；`DetailsReadme/DetailsReadme.md` 订阅表 3 行 / 「白名单怎么来的」推导句；`skill/SKILL.md` 预期读数行（`sync_docs.py` 写 9 处，推导句 1 处手改）。
- ✅ **闸门**：`verify_jinx_src.py` **68 passed / 0 failed**（含第 6 段三份 direct 产物逐字节可复现）；`selftest_negative.py` **12 抓到 / 0 漏报**。

**验收（对 diff）**

- 三份 direct 产物只多 `DOMAIN-SUFFIX,itunes.apple.com` 一条 + 表头 `# entries`（47 → 48）/ `# extra-white`（3 → 4）行变化；ads 三份产物零改动。
- `custom-direct.list` 新增 1 条域名与对应依据注释，其余 3 条手工条目形制未动。

---

## 2026-10-22（四）· 上游快照同步 `3.2.1 → 3.2.3`

> 📌 距上一次上游同步（2026-10-10）隔了 12 天，上游又滚了两版。本次严格按 `skill/SKILL.md`
> 「上游滚动时的标准流程」四步执行：删干净重取上游源 → 重跑两条生成命令 → `sync_docs.py`
> 推平文档读数 → 跑两道闸门。**规则内容变动全部来自上游，本仓未做任何人工判断。**

**变更**

- 🔄 **上游数据 `3.2.1` → `3.2.3`**（上游 `lastUpdate` `2026-10-18T12:30:33Z`）。上游仓库**无 tag 也无 release**，只有默认分支 `master` 的滚动快照，故快照位仍以「版本号 + 更新日期」双写记录。
  - 🚫 **拦截 3901 → 3991 条（+90）**：上游黑名单 `3726 + 264` 条 → 产物 3991（`sing-box` 侧 `domain_suffix` `3751 → 3833`、`domain_regex` `150 → 158`）。新增 94 条、移除 4 条。
    - 新增含阿里妈妈系一整族（`acookie.alimama.com` / `afpapi.alimama.com` / `afpeng.alimama.com` / `afpssp.alimama.com` / `afptrack.alimama.com`）、字节系（`adcanvas.com` / `adsrvr.cn` / `dsp-ad.yy.com` / `splash.yy.com` / `ysad.yy.com`）、`byteadverts.com`、`fancydsp.com`、搜狐（`ad.seeyouyima.com` / `adshows.21cn.com` / `admarket.21cn.com`）、网易（`adsys.nineton.cn`）、爱奇艺（`ad.h5-cdn.soulapp.cn` / `ad-h5-station-cdn.soulapp.cn`）、腾讯广告（`ads.privacy.qq.com`）、`unityads.unitychina.cn`、快手（`kad.gotokeep.com`）、`adscope.cn` / `adscope.xyz`（与既有 `adscope.com` / `adscope.com.cn` 同族）、`statis.miwuad.com`（小米）等。
    - 通配新增 `adstrategy`、`httpdns` 系列（`^.*httpdns.*$` / `^httpdns.*$`）等 8 条正则。
    - 移除 4 条 —— 上游把它们从黑名单交还直连：`dns.weixin.qq.com`、`httpsdns.baidu.com`、`lf-cdn-tos.bytescm.com`（上游两处名单均已不再收录）、`httpdns.meituan.com`（**上游已将其提进白名单**，本仓放行侧同步收录，见下）。
  - ✅ **放行 47 → 47 条（±2 换血，条数不变）**：上游白名单 `328 → 324` 条，过 guard（与黑名单碰撞裁剪）后留存 `44 → 44` 条，加 3 条手工补充（`*.tange365.com` / `*.wechatos.net` / `*.za.group`）—— 仍为 47 条。
    - 🔀 **换血明细**：新增 `httpdns.qq.com` / `httpdns.yunxinfw.com`（上游提进白名单）；移除 `p.l.qq.com` / `aedns.weixin.qq.com`（上游本轮把这两个域**移入黑名单**）。`sing-box` 侧构成仍为 `domain=43 domain_suffix=4`。
    - 📌 手工补充的 3 条 `custom-direct.list` 条目**形制未动**，仍落在产物末尾。
  - 🔧 **同步了版本号与读数的地方**：`README.md` Source 徽章 / 拦截徽章 / 订阅表 3 行 / 能力矩阵拦截行 / 上游快照行 / 页脚上游行；`DetailsReadme/DetailsReadme.md` 订阅表 3 行 / 「白名单怎么来的」推导句 / 页脚上游行；`skill/SKILL.md` 预期读数行；`.github/workflows/ci.yml` 的「上游快照」注释；`skill/tests/verify_jinx_src.py` 注释里的示例读数。（`sync_docs.py` 写 14 处，其余 2 处为脚本不覆盖的注释，同步惯例一并跟进。）
  - ✅ **闸门**：`verify_jinx_src.py` **68 passed / 0 failed**（含第 6 段六份产物逐字节可复现、第 5b 段文档版本号、第 6b 段合并基线）；`selftest_negative.py` **12 抓到 / 0 漏报**。
  - 📐 **验收（对 diff）**：产物侧只有表头 `# entries` / `# extra-*` 行变化 + 正文中上游实际增删的条目（拦截 +94 −4，放行 +2 −2）；`custom-*.list` 手工条目 3 条形制未动。**未手改任何一条规则内容。**

---

## 2026-10-10（六）· 机制：上游同步从「靠自觉」改为「可执行流程」
> 📌 本日第三条，也是唯一一条**不改任何规则内容**的改动。它源于本日第一条的一次真实失误，此处不粉饰 —— 留痕才有价值。

**事故（先记错，再记修）**

- 🐛 加 `*.za.group` 时，本仓产物停在旧上游 `3.1.9`，而当时上游已滚到 `3.2.1`。CI 第 6 段（产物 == 源头重跑结果）**确实判了红** —— 错不在红没出现，而在**看到红之后的反应**：当时为了把 diff 缩小，把本地源钉回旧版本让红变绿，而不是拉新上游。
- 🎯 用户口径（原话）：「你要从机制上避免这种问题的发生……一定要合并上游仓库最新的版本，而不是用旧版本去合并。要从机制上解决这个问题，实现 AI 驱动化。」

**变更**

- 🛠️ **新增 `skill/scripts/sync_docs.py` —— 把「推平 22 处文档读数」从手工变成一条命令。** 真值只有一个来源：六份产物 + `jinx-rules/version.json` + `custom-*.list`；文档只是它的投影。CLI：`python skill/scripts/sync_docs.py`（演练）/ `--write`（落盘）。
  - 🚧 **写侧门禁（本改动的核心）**：若产物与当前上游不同步（`ads ≠ 黑名单固定+通配+手工`、`direct ≠ guard 留存+手工`），脚本**直接拒绝工作**并提示先重跑生成链。防的正是「产物是旧上游生成的、文档却写新版本号」—— 这种半同步下**所有条数断言都会通过**，读者看到的上游版本是假的，无门禁可发现。
  - 🚧 另加「手工域名名单」交叉校验：Details 简注里列出的域名个数必须等于 `custom-direct.list` 实际条数（条数对、名单漏一个是另一类静默误导）。
  - ✅ **变异测试**：把三个文档 13 处读数全打回旧值，闸门报 15 个 ❌；`--write` 后闸门回到全绿，且三个文件与变异前**逐字节完全复原** —— 证明脚本不是空转。
  - 🐛 踩坑：Windows 控制台默认 GBK，打印 emoji 会 `UnicodeEncodeError: 'gbk' codec can't encode character '\u270f'`，写到一半崩掉会留下「部分同步」状态；已在 `main()` 里 `sys.stdout/stderr.reconfigure(encoding='utf-8', errors='replace')`。写入统一 `newline=''` 钉 LF。
- 🔍 **闸门新增两段（50 → 68 项断言）**：
  - **第 5b 段**：文档声明的上游版本号与快照日期 == `jinx-rules/version.json`（徽章 / 快照行 / 页脚 / 详情文档页脚）。旧闸门只校验条数，于是「条数全对、徽章写着上一个上游版本」可以全绿。
  - **第 6b 段**：合并基线 —— `version.json` 自述计数 == 源文件实际条数（挡「本地源被裁过 / 只取到半个快照」），并显式列出产物与上游应有的条数，让失败原因一眼可读。
  - ⚖️ **诚实边界**：6b 的独立判据只有计数自述那一条。「拿旧版合并」**不是可静态检查的状态，而是一条政策** —— 静态断言抓不住它，因为它取决于人在红面前选哪条路。故它靠三件东西固定：`sync_docs.py` 写侧门禁 · SKILL.md 流程（人的参照）· 5b/6b 把「文档版本号」与「本地源完整性」变成可判定的。
- 🧪 **负样本 6 → 12 条**：新增「半同步（拿旧版合并）」「文档版本号漂移」「残缺上游快照」，另把负样本关键词一律改为**失败时才出现的文案** —— 原先用段标题当关键词，而段标题通过与否都打印，等于样本永远「抓到」＝假绿。
  - 🔬 **独立性反证**：逐一拆掉对应判据，要求恰好那一条翻红。反证顺带发现 6b 的「合并基线」两条被第 6 段逻辑蕴含、**不新增守卫**，仅保留可读性 —— 闸门不假装自己比实际更强。
- 📖 **`skill/SKILL.md` 新增「上游滚动时的标准流程（合并个人规则前必读）」**：四步命令（取上游最新 → 重跑两条生成 → `sync_docs.py` 推平 → 跑两道闸门）+ 「遇到红时的正确反应」表（第 6 / 6b / 5b 段各自的红 → 正确做法 vs 本次犯过的错误做法）。
- 🔧 全仓段数声明同步：`DetailsReadme`（含目录项 8/9 编号归位）· `.github/workflows/ci.yml` 步骤名与注释 · `verify_jinx_src.py` 顶部断言清单。

**验收**

- ✅ `verify_jinx_src.py` **68 passed / 0 failed**；`selftest_negative.py` **12 抓到 / 0 漏报**；`sync_docs.py` 演练 **0 处改写**（即当前文档已是产物投影，无漂移残留）。
- 🔬 **端到端演练**（在临时副本仓里模拟上游滚动，验证机制真能拦住错误流程、放行正确流程）：

| 步骤 | 结果 |
|:---|:---|
| 基线 | verify `exit=0` 68/0 · selftest `exit=0` 12/0 |
| 源头前进、产物未重跑 | verify `exit=1` 63/5 · **`sync_docs.py` `exit=1` 拒绝改文档** · selftest `exit=2` 拒绝在非绿基线上出结论 |
| 重跑两条生成命令（文档仍旧） | verify `exit=1` 60/8（文档声明的条数/版本号对不上） |
| `sync_docs.py --write` | 9 处改写 |
| 推平后 | verify `exit=0` 68/0 · selftest `exit=0` 12/0 |
| 上游正式发版 3.2.2（连版本号一起改） | verify `exit=1` 64/4 → `sync_docs.py --write` 4 处改写 → verify `exit=0` 68/0 |

**演练反哺：当场才发现的两个真 bug（已修）**

- 🐛 **闸门第 6b 段的唯一独立判据会被跳过** —— 原文写成「第 6 段已判负则本条直接判过（只打提示）」，本意是让失败原因可读，实际却把该判据变成摆设，而且**恰恰在最需要它的场景失效**：上游滚动 → 第 6 段红 → 本条被跳 → 负样本「残缺上游快照」开始漏报（11 抓到 / 1 漏报）。修法：提示照打，**判据必跑**（`repro_failed` 只影响附注文案，不影响任何 `judge` 结论）。
- 🐛 **负样本本身是空操作** —— 「残缺上游快照」样本原写 `d['domainBlacklistCount'] += 1`，隐含假设「源文件是干净的」；演练时工作区恰好也给 blacklist 追加过行，两边同时 +1 又相等，样本静默失效。修法：**从副本仓实际数出条数再 +1**，无论副本仓什么状态都保证分歧存在。
- 🧪 **负样本自测新增前置门**：先用副本仓跑一遍闸门，不绿则 `exit=2` 不出结论。负样本是**相对**断言（「破坏 O 后能抓到」隐含「不破坏时是绿的」），在脏工作区上跑出的结果既可能假绿也可能假红 —— 宁可拒绝出结论，也不给一个看似跑过的假绿。

> 📝 这两条 bug 都不可能靠「把它写出来」发现，只可能靠**真跑一遍**。演练的价值就在这里，已固化为本节表格。

---

## 2026-10-10（六）· 规则：白名单新增 `*.za.group`；上游快照同步 `3.1.9 → 3.2.1`

> 📌 本日两条改动。**第一条**只动源头 `custom-direct.list`；**第二条**紧跟上游滚动，重跑生成把两次变动合并进同一份产物。

---

### 一 · 白名单新增 `*.za.group`

> 📌 本日第一条。改前已验证「用上游 `3.1.9` 重跑，六份产物与仓库既有文件逐字节一致」，故本条 diff 不含任何上游漂移。

**变更**

- 🛡️ **白名单 44 → 45 条：新增 `*.za.group`** —— 众安银行 App（ZA Bank）业务域，2026-10-10 实测 + 用户指定放行，语义为 `za.group` 及其全部子域（如 `bankappgw.za.group` / `bank.za.group`），三平台落点分别为 `DOMAIN-SUFFIX,za.group`（mihomo / Surge）与 `domain_suffix: ["za.group"]`（sing-box）。经 `custom-direct.list` 的 `--extra-white` 通道并入，追加在 guard 过滤之后、不参与碰撞裁剪。
  - 🔍 **现象**：大陆使用懒人版时 App 的 `bankappgw.za.group:443` 落进兜底规则走境外代理，登录 / 刷新 / 查余额一直转圈；图片与静态资源正常（`cdn.zaticdn.com` 上游已在直连集）。
  - 🧩 **根因**：上游直连集（Loyalsoldier `direct.txt` 与 Jinx 白名单）均未收录 `za.group`；同族的 `zainvest.group` / `zafinsvc.com` / `zajourney.com` / `zaticdn.com` 上游都已放行，**只有 `za.group` 一族漏网**。实测大陆可直连、未被墙，故在本仓手工补直连，等上游收录后再删本条。
  - 📐 三份产物同一次重跑生成，条数 45 / 45 / 45 一致；`sing-box` 侧字段构成 `domain=41 domain_suffix=4`（原 3 项 + 本次 1 项）。
  - ✅ **验收（对 diff）**：与改动前对拍，**只出现三处允许的变化** —— 表头 `# entries: 44 → 45`、`# extra-white: custom-direct.list(2) → (3)`、末尾按顺序多出 1 条 `DOMAIN-SUFFIX,za.group`；其余正文**逐行不变**（既有 44 条逐字节相同；sing-box JSON 仅 `domain_suffix` 数组末尾追加 1 项）。README 与 `DetailsReadme` 的条数声明同步 44 → 45，`skill/SKILL.md` 预期读数与 `selftest_negative.py` 的条数锚点一并更新。
  - 📌 **上游快照未动**：本次重跑固定在上游 `3.1.9`（commit `3fd15f94`），diff 中不含任何上游漂移。

---

### 二 · 上游快照同步 `3.1.9` → `3.2.1`

> 📌 本日第二条。**这是每条规则集镜像都欠的债** —— 上游只增不减，旧快照躺平即等于拦不住新广告、也放不稳新白名单。

**变更**

- 🔄 **上游数据 `3.1.9` → `3.2.1`**（上游 `lastUpdate` `2026-10-09T11:35:12Z`）。上游仓库**无 tag 也无 release**，只有默认分支 `master` 的滚动快照，故快照位以「版本号 + 更新日期」双写记录（`README.md` 与 `DetailsReadme` 各一处表格 + 各一处页脚）。
  - 🚫 **拦截 3889 → 3901 条（+12）**：`sing-box` 侧 `domain_suffix` `3740 → 3751`、`domain_regex` `149 → 150`。新增含 `umestartup.umetrip.com`（航旅纵横）、`adse-v2.ximalaya.com` / `open.ximalaya.com` / `upos-app.ximalaya.com`（喜马拉雅）、`adservice.kugou.com` 与两条开屏图缓存域（酷狗）、`cpic.fancydsp.com`、`c.l.qq.com` / `u.l.qq.com`、`cfgc.flysleep.cn` / `upc.flysleep.cn`、通配 `*-ad.dcarvod.com` 等。
  - ✅ **放行 45 → 47 条（+2）**：上游白名单 `325 → 328` 条，过 guard（与黑名单碰撞裁剪）后留存 `42 → 44` 条，加 3 条手工补充（`*.tange365.com` / `*.wechatos.net` / `*.za.group`）。`sing-box` 侧构成为 `domain=43 domain_suffix=4`。
  - 🧹 **顺带漂移**：上游本轮把 `log.mmstat.com`、`mmstat.com`、`passengerapi.saicmobility.com` 从黑名单移出（交还回直连），并把 `gm.mmstat.com` / `wgo.mmstat.com` 提进白名单 —— 这正是 `mmstat` 系域在上游自家黑/白名单间反复翻面的老问题，本仓只如实转换，不替上游做判断。
  - 🔧 **同步了版本号与读数的地方**：`README.md` Source 徽章 / 拦截徽章 / 放行徽章 / 订阅表 3 行 / 能力矩阵 2 行 / 页脚上游行；`DetailsReadme/DetailsReadme.md` 订阅表 6 行 / 「白名单怎么来的」推导句 / 页脚上游行；`skill/SKILL.md` 预期读数行；`skill/tests/selftest_negative.py` 的条数锚点（负样本必须跟着真实读数走，否则自测会静默失效）；`skill/tests/verify_jinx_src.py` 注释里的示例读数；`.github/workflows/ci.yml` 的「上游快照」注释。
  - ✅ **闸门**：`verify_jinx_src.py` **59 passed / 0 failed**（含第 6 段六份产物逐字节可复现）；`selftest_negative.py` **9 抓到 / 0 漏报**。
  - 📐 **验收（对 diff）**：产物侧只有表头 `# entries` / `# extra-*` 行变化 + 正文中上游实际增删的条目；`custom-*.list` 手工条目 **3 条形制未动**，仍落在产物末尾。

---

## 2026-10-04（四）· 改名：`*-white-guard.*` → `*-direct.*`

> 📌 本日第四条。**规则内容零改动** —— 三份产物逐字节比对，与新名前完全一致。

**变更**

- 🏷️ **白名单产物改名：`mihomo-white-guard.yaml` → `mihomo-direct.yaml`、`surge-white-guard.list` → `surge-direct.list`、`sing-box-white-guard.json` → `sing-box-direct.json`。** 与源头 `custom-direct.list` 及「白名单 = 直连」的语义对齐 —— 历史名 `white-guard` 是更早一次术语调整（「白名单守卫」→「白名单」）未收尾的遗留。
  - ⚠️ **旧订阅地址失效**：三个旧名文件已删除，旧地址将 404。**已订阅旧地址的需改用新地址。** —— 这是本次改动的已知代价，经确认后执行。
  - 🔧 示例里的 **provider / tag 名**一并由 `jinx-white-guard` 改为 `jinx-direct`（文件名与标识符对齐）。
  - ✅ **内容零改动**：新旧产物**逐字节相同**（1599 / 1326 / 1459 字节，三份全等）—— 纯改名。
  - 📐 产物名由 `convert_ruleset.py --tag <名>` 决定，故**改的是生成参数**（`--tag white-guard` → `--tag direct`）而非手改文件名，`verify_jinx_src.py` 的 `REGEN` / `PRODUCTS` 表随之同步 —— 保证「产物 == 源头重跑结果」这条断言仍然成立。
  - 📝 全仓共 52 处引用随之更新（生成参数 / README / DetailsReadme / SKILL / 断言 / 负样本 / `custom-direct.list` 表头）；**CHANGELOG 的 6 处旧名保留不动** —— 那里记的是"当时叫什么"，改了等于篡改历史。

**纪律入册**

- `skill/SKILL.md`「对外交付」新增一条：**改一个产物的文件名 = 一次改全套，且属破坏性改动**（订阅地址变更）。含代价先想清楚（旧地址 404；无法确认引用方已迁移时宁可保留旧文件标注废弃）、先改 `--tag` 而非 `git mv`、改完必做逐字节比对、五层必查清单、CHANGELOG 一律不改。

---

## 2026-10-04（三）· 修复：行尾跨平台不一致（CI 首跑即抓出）

> 📌 本日第三条。**规则内容零改动** —— 六份产物只有行尾变化（CRLF → LF），逐字节归一化比对已证「仅行尾不同、内容一致」。

**修复**

- 🐛 **`convert_ruleset.py` 写出行尾随平台而变，产物跨平台不可复现** —— 脚本原用 `write_text(text)`，而 Python 的通用换行转换会把 `\n` 按平台写成 `os.linesep`：**Windows 出 CRLF、Linux 出 LF**。后果是仓库内**行尾分裂**（mihomo / Surge 四份产物为 CRLF、sing-box 两份为 LF），且 CI 在 Linux 上重跑生成必得 LF、与仓库内容不符。
  - 修法两条腿：① 写出改为 `write_text(text, encoding='utf-8', newline='')` 显式钉死 LF；② 新增 `.gitattributes`（`* text=auto eol=lf`）管住检出与提交。**缺一不可** —— 只改脚本则仓库内容仍是 CRLF、CI 仍判负；只归一化文件则下次在 Windows 重跑又写回 CRLF。
  - ✅ 六份产物按新脚本重跑，验证方式为「与改动前逐字节归一化行尾后比对」，结果全部为「仅行尾不同、内容一致」。
  - 📌 规则集按行解析、客户端都会 trim 行尾，CRLF 与 LF 对功能等价；本次只为「跨平台产物逐字节可复现」这一工程目标。

**留痕：这次缺陷是 CI 第一次运行当场抓出来的**

- 🔍 推上 CI 后首次运行**判负 6 项** —— 本地全绿、CI 全红，根因正是平台差异（本机 Windows 的 `write_text` 出 CRLF，与仓库内容"碰巧"一致；Linux 出 LF 才暴露真相）。这恰好印证了本仓这条断言的价值：**「产物 == 源头重跑结果」必须跨平台验证**，只在本机跑等于没跑。
- ⚠️ **同时更正一条此前的错误判断**：上一节曾写「仓库内实际存的是 LF，只是 `core.autocrlf=true` 把它检出成 CRLF」。用 `git cat-file -p HEAD:<file>` 直读 blob 核实后确认：**仓库内就是 CRLF**，`core.autocrlf` 不是原因。教训是 —— 判断「仓库里到底存了什么」必须直读 git 对象，**不能看工作区**（工作区会被 autocrlf 改写）。
- 📐 本次同步更新 `skill/SKILL.md` 踩坑记录与 `DetailsReadme` 第 9 节，把平台行尾陷阱的判据与两条腿修法写入，供日后复用。

---

> 📌 本日第二条。规则数据一个字节未改 —— 只加校验。白名单的改动见下方（一）节。

**新增**

- ✅ **`skill/tests/verify_jinx_src.py` —— 一致性断言（9 段 · 50 项）** —— 本仓的立身之本是「六份文件内容等价、规则一条不增不减」，此前**只靠人工对拍**，一次误改即静默破坏且无人察觉。现固化为断言：产物存在性 · 三格式条数一致 · **跨格式逐条语义等价**（归一化比对，非仅比条数）· 表头 `# entries` 自述 · 文档条数声明（README / DetailsReadme）· **产物 == 源头重跑结果**（逐字节，防手改产物与「改了源头忘了重跑」）· `custom-*.list` 落盘 · 文案规范（emoji 行首 + 密度）· 行尾与 BOM。
  - 🔢 退出码沿用全仓四态：`0` 过 / `1` 判负 / `2` 环境不达标 / `3` SKIP。**SKIP 走独立码 3，不借 0 蒙混**（姊妹仓曾因 SKIP 与「环境不达标」同码，把环境故障吞成 SKIP → exit 0 假绿）。
  - 📌 第 6 段需上游源文件，CI 先下载再跑；本地裸跑显示 SKIP 属正常。
  - 📌 该脚本名此前已被 `skill/SKILL.md` 第 280 行引用为「emoji 断言的第 8 段」，但**文件从未存在**（`git log --diff-filter=A` 零命中）—— 本次一并兑现该引用。

- 🧪 **`skill/tests/selftest_negative.py` —— 负样本自测（防闸门空转）** —— 在临时副本仓里制造 6 种典型错误（手改产物 / 只改表头 / 跨格式差异 / 文档漂移 / 源头改了没重跑 / emoji 违规），要求断言脚本逐一判负；**有漏报即判负**。依据是本 skill 记录过的「两半都恒空 = 永远绿的空操作」教训：一个只会全绿的闸门与没有闸门等价。

- 🔁 **`.github/workflows/ci.yml` —— 首次引入 CI** —— push / PR 触发：取上游源文件 → 跑 9 段断言 → 跑负样本自测。取源文件一步**失败即整步失败**（`curl -f`），避免源文件静默缺失导致第 6 段长期 SKIP、CI 退化成空操作。

- 🏷️ README 加 CI 徽章；文档索引补「验收闸门」；DetailsReadme 新增第 9 节「一致性保证与验收」（九段清单、退出码协议、已知行尾不统一）。

**修复**

- 🐛 **`DetailsReadme` 白名单条数漏改**：`mihomo-white-guard.yaml` 一行仍写 `43`（本日第一条改动时只同步了 Surge / sing-box 两行，漏了这一行）。**由新写的断言当场抓出** —— 这正是它存在的意义。
- 📐 **`skill/SKILL.md` 预期读数过期**：「完整生成」节的预期读数写着 `white-guard 43` / `domain_suffix=2`，已随本次白名单改动更新为 `44` / `3`，并注明该行随源头漂、写完必跑闸门核对。

**留痕（编写断言时踩的坑，两条都会给出错误结论）**

- 🐛 **第 6 段比对曾被 `--src` 写法差异误报**：`--src` 会**原样进产物表头**，而 ads 线线上是 `# source: jinx-rules`（无 `./`）、white-guard 线是 `# source: ./jinx-rules`（有 `./`）—— 两条命令写法本就不同，不是笔误。断言脚本因此按产品线分别固化参数，并在 diff 详情里显式提示「仅表头注释行差异」。
- 🐛 **emoji 判定曾漏报句中 emoji**：初版把 `U+2B00-2BFF` 整段当箭头排除（为让 `→` U+2192 不算 emoji），但 `⭐`(U+2B50) 正住在那段里 → `上面用的是 ⭐ 首选 Raw` 这类违规**静默逃过检查**。改为逐码位排除箭头。该漏报由负样本自测当场抓到，并留下一个用 `⭐` 造的负样本长期守它。
- 🐛 **emoji 判定曾给合规内容假红**：`⚖️` = U+2696 + U+FE0F，若把 FE0F 当独立 emoji 匹配，第二轮命中时前缀非结构字符 → 本仓 7 处 `⚖️ / ⏱️ / ⚠️` 行首引导符全被误报。改为 FE0F 随基字符整体消费。

---

## 2026-10-04（二）· 工程：一致性闸门与 CI

> 📌 本日第二条。**规则数据一个字节未改** —— 只加校验。
**新增**

## 2026-10-04（一）· 规则：白名单新增 `*.wechatos.net`

> 📌 本日三条记录中的第一条。本日共三次改动，为同一天内的先后顺序，非版本号。

**变更**

- 🛡️ **白名单 43 → 44 条：新增 `*.wechatos.net`** —— 用户指定放行，语义为 `wechatos.net` 及其全部子域（如 `api.wechatos.net` / `cdn.wechatos.net`），三平台落点分别为 `DOMAIN-SUFFIX,wechatos.net`（mihomo / Surge）与 `domain_suffix: ["wechatos.net"]`（sing-box）。经 `custom-direct.list` 的 `--extra-white` 通道并入，追加在 guard 过滤之后、不参与碰撞裁剪。
  - 📌 **语义口径留痕**：「前缀是 wechatos.net 的所有域名」有歧义，两种解法范围不同 —— 本次取**后缀语义**（`DOMAIN-SUFFIX`，放行该域 + 全部子域）；另一种「任何以 `wechatos.net` 开头的域名」（如 `wechatos.net.abc.com`）需 `DOMAIN-KEYWORD,wechatos.net`，范围更宽，**本次不采用**。日后若要改判，按此口径重议。
  - 📐 三份产物同一次重跑生成，条数 44 / 44 / 44 一致；`sing-box` 侧字段构成 `domain=41 domain_suffix=3`（原 2 项 + 本次 1 项）。
  - ✅ **验收（对 diff）**：与改动前对拍，**只出现三处允许的变化** —— 表头 `# entries: 43 → 44`、`# extra-white: custom-direct.list(1) → (2)`、末尾按顺序多出 1 条 `DOMAIN-SUFFIX,wechatos.net`；其余正文**逐行不变**（sing-box JSON 无表头，仅 `domain_suffix` 数组末尾追加 1 项，既有 41 + 2 项逐项一致）。README 与 `DetailsReadme` 的条数声明同步 43 → 44。

---

## 2026-09-28

**变更**

- 🔵 **新增 sing-box 支持：`sing-box-ads.json`（3889 条）· `sing-box-white-guard.json`（43 条）** —— rule-set 的 **source 格式**（JSON），不是二进制 `.srs`：远程规则集 `format: "source"` 直接消费，订阅即用。格式依据官方文档（内核 **1.14.2** 实测）：顶层 `{"version": 5, "rules": [...]}`，5 是 1.14.0 引入的当前版本；`.json` 扩展名即 source 格式的约定后缀（`format` 在该扩展名下可省略，示例仍显式写出）。条数与 mihomo / Surge 完全一致，同一次重跑生成。
  - 📐 **字段映射**：黑名单条目（域 + 全部子域）→ `domain_suffix`（3740），149 条中缀通配 → `domain_regex`（Go RE2，与 mihomo `DOMAIN-REGEX` 转换式相同）；白名单精确条目 → `domain`（41），强制放行条目 → `domain_suffix`（2）。
  - 🔬 **`domain_suffix` 语义实证**（`sagernet/sing` 的 `common/domain/matcher.go`）：不带点写法命中自身 + 全部子域、域段级边界（`aexample.com` 不误命中）—— 与 mihomo `DOMAIN-SUFFIX` 等价；前导点 `.example.com` 才是「仅子域」，本仓不用。
  - ✅ **1.14.2 内核全链路验证**：两份 JSON `rule-set compile` 通过；本地挂载与远程（`type: remote` + `format: "source"`）两种接入 `sing-box check` 通过；compile → decompile 回读逐条一致（唯一差 17 条重复折叠，见下）。
  - 📌 17 条「重复」来自上游同时存在 `*.x.com` 与 `x.com`（转换后同值），mihomo / Surge 侧同样保留这 17 行 —— 重复匹配无副作用，三平台口径一致；compile 成 `.srs` 时 trie 会折叠它们，属语义无损。
  - 📌 接入示例里 `outbound: "direct"` 按用户自己的直连出站 tag 改；`update_interval` 缺省即 `1d`；1.14 起 `download_detour` 已废弃（1.16 移除），示例不再使用。

- 🧪 `convert_ruleset.py` 同步扩展：黑/白名单两条命令现在各产出 **3 个文件**（mihomo / Surge / sing-box），sing-box 侧元数据只打印到 stdout（source JSON 不支持注释、strict 解析不允许多余字段）。重跑验收：既有 4 个产物 **逐字节不变**（`cmp` 验证），仅新增 2 个 JSON。

- 🤝 **秋风（AWAvenue）订阅清单补齐 sing-box 行** —— 官方本就有现成的 `AWAvenue-Ads-Rule-Singbox.json`（rule-set source 格式，`version: 3`，1.14.2 内核 compile 验证兼容），README 订阅表与地址块各加一行官方直链，三平台对齐。965 条与 `RULE-SET` 版同源（`domain` 949 + `domain_suffix` 12 + `domain_keyword` 4，关键词规则有原生字段、无转换损失）。**本仓不镜像这份文件**：官方每日更新、快照必滞后，且官方已是目标格式、镜像无加工价值 —— 与 Jinx 侧「格式转换镜像」的定位不同（口径入 DetailsReadme 第 3 章）。

- 🎨 **README 整体重排（183 → 253 行）：目录导航 + 自家/第三方分表 + 接入折叠 + 原生 alert** —— 用户原话「逻辑和可视化美观化都是一坨」。四处改动：
  - 🧭 顶部加**目录**（8 条内链，锚点按 github-slugger 规则对拍验证全命中，标题 emoji 无 FE0F）；slogan 补上 sing-box（原「mihomo 和 Surge 也拦得住」漏了新平台）；徽章重排三行（项目 / 平台 / 数据），数据徽章拆「拦截 3889 · 放行 43 · 秋风 965」各配中文色标。
  - 🧱 **订阅节拆两个 `###` 子节**：自家 6 份（两源地址块）与秋风 3 份（官方直链单源）分表 —— 原先 9 行混排一张表，第三方行「官方直链、无备用源」与自家「两源可选」的事实混在一起说不清。
  - 🔌 **接入节三个客户端各收进 `<details>` 折叠块**（mihomo 默认展开）：原先 ~60 行配置怼在正文里，sing-box 一段还连着 4 个 💡📌 堆成整段；折叠后每块内说明**一行一条**。配置一字未改。
  - ⚠️ **两处硬警告升级为 GitHub 原生 alert**（`> [!WARNING]` / `> [!IMPORTANT]`）：GEOSITE,cn 顺序坑、OpenClash `china_ip_route`；uci 命令收进 `<details>`，留一行回滚在外。「叠加秋风排 Jinx 之后」并入秋风节的 WARNING，不再两处重复。
  - ✅ 按既有口径自检：emoji 45 个（≥20）、行首规则（HTML 标签内 / 单元格起始豁免）、标题无 FE0F、目录锚点全命中、条数声明与文件一致。版式规范已同步 `skill/SKILL.md`「对外交付」。

## 2026-09-22

**变更**

- ✂️ **README 去掉一处「我们的选择」辩解** —— AWAvenue 那行原写「…会拦掉 Jinx 白名单里的 8 个域。**由对方托管，缓存不归我们管，故不列备用源。**」后半句是在解释**我们为什么只给 Raw 源**，属决策叙述，不是产品信息 —— 标题行「仅给 Raw 源」已把事实说清。已删，保留前半句（与白名单冲突是使用者要知道的）。
  - 📌 口径入 [`skill/SKILL.md`](skill/SKILL.md) 的分层原则：**README 只写产品当前状态**，不写归类自述 / 决策辩解 / 评审对话。
  - ✅ 地址字符串与条数一字未改，10 个地址照旧。

- 🎨 **emoji 密度补足：铺回行首，不进正文** —— 上一版每份文档只有标题挂 emoji、正文几乎全裸，用户反馈「emoji 不如之前丰富……现在好少」。本轮把 emoji 铺回**行首**：段落引导符（📦 ⭐ 🔁 🔀 🤝 ⚠️ 💡 📌 🔽 📄 📊）、表格单元格起始（规则顺序表 🛡️ / 🚫 / 🚦，文档表 📘 / 🧪 / 🗓️，来源表 📦 / ⚖️ / 📄 / 🧪）、无序列表项（⏳ 🧊 🔍 🎯 🌳 🧱 ⏭️ ✅）、文件结构树的各条目（🔷 / 🔶 / 📝 / 🧪 / 📁）以及详情文档的标题与目录。README **8 → 28** 个，`DetailsReadme` **16 → 56** 个。
  - 📌 **用户口径：emoji 只能出现在行首，不得落在句中**（原话「不得出现在句中，只能句首」）。故正文里不再有「上面用的是 ⭐ 首选 Raw」这类夹在句子中间的写法。
  - 🔍 已把这条口径固化成断言：校验脚本按「emoji 之前只许出现结构字符（标题 / 列表 / 引用标记、表格竖线、`[`、树形框线、缩进）」判定，并设密度下限（README ≥ 20 / `DetailsReadme` ≥ 40）—— 防止下次又被"克制"回去。校验器自测 12 例全对，含 3 个负样本（句中 / 行尾 / 箭头不算 emoji）。
  - 📎 表格单元格里的 emoji 属「单元格起始」，不算句中；标题 emoji 仍只用单码位（见下条 FE0F 坑）。

- 🎨 **标题补回 emoji；秋风规则并进「订阅」清单末尾** —— 上一版为追求克制把标题 emoji 全去掉，本轮补回：**每个标题带一个 emoji** 作视觉锚点（层级仍交给 `##` 与留白，`---` 分隔线继续不用）。同时把第三方 **AWAvenue 秋风广告规则**从独立的 `## 🤝 搭配 AWAvenue-Ads-Rule` 小节移进 `## 📥 订阅`：表格加两行与 Jinx 四份并列（用途列标「拦截 · 秋风」），地址块排在自家两源之后，落在**规则集清单的最下面**。
  - 📌 用户口径：第三方规则属规则集清单的一部分，「应该放到规则集的最下面，而不是 README 的最下边」。
  - ⚠️ **emoji 会改变锚点**：`## 📥 订阅` 的锚点是 `#-订阅`（emoji 被 slug 删掉后余下前导横线），`## 📥 1 规则集与白名单` 是 `#-1-规则集与白名单`。README 徽章里的 `](#-来源与许可)` 与 DetailsReadme 目录 8 条内链已同步，改标题时必须一起改。
  - 🐛 **踩坑：标题 emoji 不能带变体选择符（U+FE0F）** —— `⚙️` / `🛠️` 实际是「基字符 + FE0F」两个码位，而 FE0F 属 Mn 类、会被 slug **保留**，于是 `## ⚙️ OpenClash` 的真实锚点是 `#️-openclash`（`#` 后面跟一个看不见的字符），手写的 `#-openclash` **点不动**。已换成不含变体符的 `🔧` / `🚧`。**校验器第一版也栽在同一个坑里**：它用 `[^\w]` 做字符类，把 FE0F 当非单词字符删掉，于是给了假通过 —— 现已改为对齐 github-slugger 的保留集（L / M / N / Pc / Zs + `-`），并用 `github-slugger` 本体交叉验证（0 未命中）。

- 🧹 **README 精简重做（219 → 145 行），解释性内容整体下沉到 `DetailsReadme/DetailsReadme.md`** —— 原 README 8 个平级小节、每节一个 emoji 标题 + 一条 `---` 分隔线，地址、参数、原理、许可平铺在一起，读起来是「一大堆堆叠」。重做后**标题去掉全部 emoji、不再用 `---` 分隔线**（层级交给 `##` 和留白），小节按使用动线重排：订阅 → 接入 → 规则顺序 → OpenClash → 搭配 AWAvenue → 文档 → 来源与许可。
  - 📦 **新增 [`DetailsReadme/DetailsReadme.md`](DetailsReadme/DetailsReadme.md)**（8 章 145 行）：白名单推导、两个源的前缀与缓存判据（`?v=` 对 raw 无效 · 权威判据是 Contents API · purge 接口）、AWAvenue 的 `RULE-SET` vs 裸域名版（965 / 961 与 4 条 `DOMAIN-KEYWORD` 差额）、规则顺序验证法、转换原理表、OpenClash `china_ip_route` 的机理与回滚、文件结构、来源与许可。
  - 📌 **只搬不删**：所有实质信息一条未丢；地址字符串与条数一字未改，10 个地址照旧，已订阅的地址无需改动。README 里只剩操作信息与结论。

- 📊 **README「📥 规则集」改为表格呈现** —— 原来 4 份文件 × 2 个源 = 8 个 fenced 地址块平铺 70 余行，标题、条数、说明夹在块与块之间，找一份文件要翻半天。改为 **一张总览表**（客户端 / 文件 / 格式 / 条数 / 用途）+ **每个源一个地址块**（⭐ 首选 Raw 一块 4 行、🔁 备用 jsDelivr 一块 4 行）—— 块数 8 → 2。`### 🤝 搭配：AWAvenue-Ads-Rule` 同构处理：表格（客户端 / 格式 / 条数 / 说明）+ 单块 Raw 两行。
  - 📐 `skill/SKILL.md` 的地址版式规范同步改写为「**一张总览表 + 每个源一块 fenced 地址块**」，并把本次返工的理由写进文档（4 份 × 2 源 = 8 块时标题、条数、说明夹在块与块之间，读者找不到头），避免下次又拆成 8 块。
  - 📌 **纯版式重排，地址字符串与条数一字未改** —— 地址总数仍为 10 个（自家 8 + AWAvenue 2），已订阅的地址无需改动。AWAvenue 条数经复核确为其文件头自报值（v1.7.8：`RULE-SET` 965 / 裸域名版 961）。

- 🔗 **规则集地址改以 Raw GitHub 为首选源，CDN 降为备用源**：README 原先六处地址只给 jsDelivr，raw 仅在小字里带一句。改为**每个文件各给一块可复制地址** —— 自家 4 份文件「⭐ 首选 Raw GitHub / 🔁 备用 jsDelivr CDN」两块；**AWAvenue 两处只给 Raw**（第三方规则，由对方托管，其缓存我们 purge 不了，多列一个备用源等于把对方的缓存层写进本文档）。`## 🔷 mihomo / OpenClash` 与 `## 🔶 Surge` 的配置片段同步以 raw 为主，备用源的换法写在片段下方的说明行里；`skill/SKILL.md` 的「引用优先 …」条目与「对外交付 · 双地址」一并翻正（并注明第三方规则集只给 raw）。
  - 📌 **只调整推荐次序与呈现方式，地址字符串本身未变** —— 已订阅的地址一律无需改动。本轮列出的 10 个地址（自家 8 + AWAvenue 2）实测全部 **HTTP 200**。
  - 📌 依据：raw 是官方直读源，不经第三方 CDN，文件增删改名后与仓库一致、无需 purge；jsDelivr 多一层第三方缓存（删文件后不 purge 仍返回旧内容），但国内直连更稳 —— 保留为备用，不再当默认。
  - ⚠️ 实测补充：raw **不是**"推送即生效" —— 本轮推送后 raw 仍返回旧版，约 **3 分钟**才同步，`?v=<日期>` 对它无效。判断是否生效只能看 GitHub Contents API；这一条已写进 README 与 `skill/SKILL.md`。

- 🏷️ **仓库名大小写规范化：`jinx-ads-rules` → `Jinx`** —— 与姊妹仓 `Surge` / `Egern` 的命名风格统一，也与上游项目名（`VME98/jinx-rules` 的 **Jinx**）一致。仓内 19 处引用已更新（README 订阅地址 / skill / 转换脚本）。
  - ⚠️ **旧地址实测全部仍可用**：`raw.githubusercontent.com` 与 jsDelivr 的旧名均 **HTTP 200**、`github.com` 旧名 **HTTP 301** → 新名 ⇒ **已订阅的地址无需改动**。
  - 📌 **文件名与 provider 名保持原样**：`surge-ads.list` / `surge-white-guard.list`、mihomo 侧 provider 名 `jinx-ads` / `jinx-white-guard` 属标识符，未动；上游 `VME98/jinx-rules` 未动。

- 🔧 mihomo 侧文件名 `.list` → `.yaml`，内容改为顶层 `payload` 列表。`.list` 是 Surge / Quantumult 的惯例，mihomo 的 `format` 默认就是 `yaml` —— 沿用 `.list` 会让抄配置的人漏写 `format`（按 yaml 解析直接报错），或被迫写一条多余的 `format: text`。**mihomo 旧地址失效**，Surge 侧文件名不变。
- 🔢 黑名单 3891 → **3889** 条（见下「移除」）。
- 🏷️ 术语调整：「完整版」→「**黑名单**」，「白名单守卫」→「**白名单**」。差集版删除后「完整」已失去对照物 —— 它只是相对差集才显得"完整"，不如按语义直呼。**文件名与订阅地址一个字未改**（`mihomo-ads.yaml` / `surge-ads.list` / `*-white-guard.*` 照旧），已订阅的不受影响。

**移除**

- 🧹 删除差集版（`mihomo-ads-delta.yaml` · `surge-ads-delta.list`）。三条实测否掉了它：① 收益只有「列表少 53 行」（约 1.4% 体积），而规则重复**本身没有副作用** —— 同一域名被两套规则命中，结果都是 REJECT；② 代价是把那 53 条的覆盖面**外包给对方的 16 条「伞」规则**，对方一改这边就静默漏拦；③ 对误杀**零改善** —— 黑名单与差集版对上游白名单的命中数同为 42 条。现只保留黑名单，要叠加第三方列表就直接叠。
- 🧹 `custom-ads.list` 移除 2 条：`msg.qy.net` · `rdelivery.qq.com` —— 两者都躺在上游 `whitelist.txt` 里，上游明确放行。保留 `rmonitor.qq.com`（既不在上游黑名单、也不在其白名单，是干净追加）。

**修复**

- 🐛 补齐 `--extra` 的收录前提：白名单的对照面是**上游黑名单**（`--guard-against-*` 不含 `custom-*.list`），所以追加进来的域名**不会**因为「上游已放行」而被白名单豁免 —— 跟上游白名单对着干 = 静默误杀。这条前提已写进 `custom-ads.list` 表头与 `skill/SKILL.md`，并按它移除了上面 2 个冲突条目。

## 2026-09-21

**变更**

- 🛡️ 白名单 42 → 43 条：新增 `*.tange365.com` —— 相机 App「小鲸看看」的业务域（账户 / 设备 / 云存储），必须直连。

## 2026-09-19

**修复**

- 🐛 普通域名由 `DOMAIN`（精确匹配）改为 `DOMAIN-SUFFIX`。Jinx 的匹配语义是「该域 + 全部子域」，初版按精确转换 —— 列表里写 `bugly.qq.com`，拦不住 `ios.bugly.qq.com`。同一份日志 30 条被拦域名的覆盖率 93% → 100%。

**新增**

- ✨ 新增 3 条上游未收录的广告域：`msg.qy.net` · `rmonitor.qq.com` · `rdelivery.qq.com`，由 `custom-ads.list` 并入。

**移除**

- 🧹 删除早期 `*-domain.list` / `*-domainset.txt` 变体，收敛为两平台各 3 份文件。

## 2026-09-18

**新增**

- 🎉 首次发布：mihomo 与 Surge 各 3 份规则集 —— 黑名单 / 差集版 / 白名单。
