<div align="center">

# 🛑 RFU 去广告规则

**广告 · 统计 · 隐私采集 · PCDN —— 四端同一份，逐条等价**

[![Frozen](https://img.shields.io/badge/Frozen-Jinx%203.2.3-8250df?style=flat-square)](https://github.com/VME98/jinx-rules)
[![CI](https://github.com/RiverFlowsInUUU/RFU-Rules/actions/workflows/ci.yml/badge.svg)](https://github.com/RiverFlowsInUUU/RFU-Rules/actions/workflows/ci.yml)
[![Ads](https://img.shields.io/badge/%E6%8B%A6%E6%88%AA-9534%20%E6%9D%A1-0969da?style=flat-square)](#-订阅)
[![White](https://img.shields.io/badge/%E6%94%BE%E8%A1%8C-49%20%E6%9D%A1-2da44e?style=flat-square)](#-订阅)

[![mihomo](https://img.shields.io/badge/mihomo-OpenClash-1f6feb?style=flat-square)](#-接入)
[![Surge](https://img.shields.io/badge/Surge-RULE--SET-orange?style=flat-square)](#-接入)
[![Egern](https://img.shields.io/badge/Egern-%E5%A4%8D%E7%94%A8%20Surge%20%E6%A0%BC%E5%BC%8F-8957e5?style=flat-square)](#-接入)
[![sing-box](https://img.shields.io/badge/sing--box-source%20JSON-blue?style=flat-square)](#-接入)

</div>

> 🧬 **只拦四类**：广告、统计、隐私采集、PCDN。不拦赌博色情灰产，也不拦 IP。
> 规则由三支路合成——217heidai lite · 5 个中文源 · 冻结的 Jinx 3.2.3 明文基线，取舍见[详情第 1 章](DetailsReadme/DetailsReadme.md#-1-三个支路与取值)。

> 🤖 **AI agent 请从这里开始** → [`skill/SKILL.md`](skill/SKILL.md)：构建链、断言口径、七条不要越的线。

## 📥 订阅

🔗 **文件名即订阅地址**，右键「复制链接地址」即可取用：

| <div align="center">客户端</div> | <div align="center">🚫 拦截规则集</div> | <div align="center">✅ 放行规则集</div> |
|:--|:--|:--|
| **mihomo** / OpenClash | [`mihomo-ads.yaml`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/mihomo-ads.yaml) `9534` | [`mihomo-direct.yaml`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/mihomo-direct.yaml) `49` |
| **Surge** / **Egern** | [`surge-ads.list`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-ads.list) `9534` | [`surge-direct.list`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-direct.list) `49` |
| **sing-box** | [`sing-box-ads.json`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/sing-box-ads.json) `9534` | [`sing-box-direct.json`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/sing-box-direct.json) `49` |

📌 Raw 优先，每行一个完整地址：

```
https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/mihomo-ads.yaml
https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/mihomo-direct.yaml
https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-ads.list
https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-direct.list
https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/sing-box-ads.json
https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/sing-box-direct.json
```

🔁 备用 jsDelivr：前缀换成 `https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/RFU-Rules@main/`，路径不变。

🏷️ **版本从哪看**：mihomo / Surge 产物头注第二行是 `# source: upstream/(A+B+C) · jinx <版本> (<快照日期>)`；sing-box 的 JSON 容不下注释，那两份不带版本标记，以 [Release tag](https://github.com/RiverFlowsInUUU/RFU-Rules/releases) 为准（四端同源，同一 tag 下逐字节一致）。

<details>
<summary>🍂 <b>搭配 AWAvenue（可选）</b> —— 本仓拦截集已含其 969 条中的 912 条</summary>

只有想要「秋风全量」时才额外叠加；代价是多几百条重复（重复对结果是 REJECT，无副作用）。

| <div align="center">客户端</div> | <div align="center">🚫 拦截规则集</div> |
|:--|:--|
| **mihomo** / OpenClash | [`AWAvenue-Ads-Rule-Clash-Classical.yaml`](https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Clash-Classical.yaml) `965` |
| **Surge** | [`AWAvenue-Ads-Rule-Surge-RULE-SET.list`](https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Surge-RULE-SET.list) `965` |
| **sing-box** | [`AWAvenue-Ads-Rule-Singbox.json`](https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Singbox.json) `965` |

第三方规则由对方托管，只给官方 Raw 地址、不列备用镜像 —— 缓存我们 purge 不了。

</details>

## 🔌 接入

### 🚦 三原则（先读这个）

| <div align="center">顺序</div> | <div align="center">规则</div> | <div align="center">去向</div> |
|:-:|:-----|:-----|
| 1 | ✅ 白名单 | `DIRECT` |
| 2 | 🚫 广告拦截 | `REJECT` |
| 3 | 🚦 常规分流（`GEOSITE,cn` / `GEOIP,cn`） | `DIRECT` |

> [!IMPORTANT]
> 白名单必须排在拦截之前，而且**不能因为「拦截集里也有这个域」就把白名单那行删掉**。拦截集里有 `umeng.com`、`tanx.com`、`getui.net` 这类平台主域，覆盖了放行清单里的功能子域；靠的就是更具体的规则先命中 DIRECT。顺序颠倒 = 推送和登录直接失效。
>
> 重叠本身是必然的（主域拦、子域放），当前是 **42 条**，逐条列在 [`OVERLAP.md`](OVERLAP.md) —— 那份文件由构建生成、CI 校验，改判据时会同步更新。

> [!WARNING]
> **Surge 拦截行不得加 `pre-matching`**。官方文档：`pre-matching` 规则会被抽出来**先于一切其它规则**求值（"Pre-matched rules have the highest priority"），且该参数只支持 REJECT 系策略 —— 放行行无法用同一参数自救。加上它，重叠清单里的域名全部失效，症状正是推送收不到、微信登录转圈。

📋 「放行在前」在各端的落点：

| 客户端 | 靠什么保证顺序 |
|:--|:--|
| mihomo / OpenClash | `rules` 列表顺序 —— `RULE-SET,rfu-direct,DIRECT` 写在 `rfu-ads` 之前 |
| Surge / Egern | `[Rule]` 行序同上；拦截行**不得加 `pre-matching`**（见上） |
| sing-box | `rules` 数组顺序 —— `rfu-direct` 的元素排在 `rfu-ads` 之前 |

<details open>
<summary>🔷 <b>mihomo / OpenClash</b> · rule-providers</summary>

```yaml
rule-providers:
  rfu-ads:
    type: http
    behavior: classical          # 不用 domain：文件是逐条规则，不是纯域名列表
    format: yaml                 # 文件是顶层 payload 列表
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
  # 其余规则接在后面
```

💡 `interval` 一周即可 —— 上游已冻结，本仓不会自己变；跟进新版是我们这边重跑发布。产物已无任何 `DOMAIN-REGEX` / `DOMAIN-WILDCARD`，最贵的逐条正则扫描不会发生。

#### 🚧 OpenClash 专用开关

> [!IMPORTANT]
> `绕过中国大陆 IP`（`china_ip_route`）默认常开：目标属大陆的连接直接放行、**不进入内核**，规则不生效、日志无记录。用本规则集必须关掉它。

```bash
uci set openclash.config.china_ip_route='0'
uci commit openclash
/etc/init.d/openclash restart
```

🔁 回滚：把 `'0'` 改回 `'1'` 再重启即可。

</details>

<details>
<summary>🔶 <b>Surge</b> · RULE-SET</summary>

```
[Rule]
# 白名单（精确放行）
RULE-SET,https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-direct.list,DIRECT,extended-matching
# 广告拦截
RULE-SET,https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-ads.list,REJECT,extended-matching
# 其余规则接在后面
```

💡 `extended-matching` 让规则在 App 直连 IP 时按 TLS SNI / HTTP Host 兜底匹配 —— 缺了它，域名规则会大批失效。

</details>

<details>
<summary>🟣 <b>Egern</b> · 直接复用 Surge 那份 <code>.list</code></summary>

✨ **不用另找文件** —— 规则集格式与 Surge 同源，两份原样可用：

✨ 与 Surge 同源，`surge-direct.list` / `surge-ads.list` 原样可用，**不用另找文件**：

```yaml
# ① 连接阶段：走规则匹配（白名单在前、拦截在后）
rules:
- rule_set:
    name: RFU-Direct
    match: https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-direct.list
    policy: DIRECT
    update_interval: 604800
- rule_set:
    name: RFU-Ads
    match: https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-ads.list
    policy: AD
    update_interval: 604800
    # 其余规则接在后面
```

```yaml
# ② DNS 阶段：广告域在解析阶段就拒答（可选，推荐）
forward:
- proxy_rule_set:
    match: https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-direct.list
    value: Domestic-DNS
- proxy_rule_set:
    match: https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-ads.list
    value: reject
- domain_wildcard: '*'          # 兜底必须指向「代理没起来时也能用」的加密组
  value: Domestic-DNS
```

💡 `update_interval: 604800` 是一周（秒）—— Egern 官方**未文档化**该键缺省值，建议显式钉死。组名（`AD` / `Direct` / `Domestic-DNS`）按你自己的配置改。两处引用同一份文件：`rules` 管连接、`forward` 管 DNS；文件是**纯域名、零 IP 条目**。

</details>

<details>
<summary>🔷 <b>sing-box</b> · rule_set（1.14.2 实测）</summary>

```json
{
  "route": {
    "rule_set": [
      {
        "type": "remote",
        "tag": "rfu-direct",
        "format": "source",
        "url": "https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/sing-box-direct.json",
        "update_interval": "7d"
      },
      {
        "type": "remote",
        "tag": "rfu-ads",
        "format": "source",
        "url": "https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/sing-box-ads.json",
        "update_interval": "7d"
      }
    ],
    "rules": [
      { "rule_set": ["rfu-direct"], "outbound": "direct" },
      { "rule_set": ["rfu-ads"], "action": "reject" }
    ]
  }
}
```

💡 `format: "source"` 是 JSON 源格式，不用二进制 `.srs`，订阅即用。`outbound` 的 `direct` 按自己的直连出站 tag 改。`update_interval` 缺省 `1d`；1.14 起 `download_detour` 已废弃（1.16 移除），不要再用。

</details>

## 🧬 规则集速览

| <div align="center">维度</div> | <div align="center">本仓规则集</div> | <div align="center">说明</div> |
|:--|:--|:--|
| 🚫 拦截 | **9534 条** | 全部 `DOMAIN-SUFFIX`，零通配、零正则 |
| ✅ 放行 | **49 条** | 43 条精确 + 6 条后缀（含 5 条手工补充） |
| 🧩 各端一致 | **逐条等价** | mihomo / Surge / Egern / sing-box 归一化后零差异，CI 对拍 |
| 🎯 生成物 | **逐字节可复现** | 产物 == 生成链重跑结果，CI 校验 |
| 🔄 上游 | **冻结** | 六个源全部落盘在 `upstream/`，构建不联网 |
| 📌 上游快照 | 冻结于 `3.2.3` · `2026-10-18` | 不再跟随上游滚动 |

🔬 不是「抄一份列表」，是**同一批域名换个写法的镜像**。灰产靠「归属域成簇或名称含语义」的准入判据在构建阶段被结构性排除，不靠人工逐条挑选。

## 📖 文档

| <div align="center">文档</div> | <div align="center">内容</div> |
|:-----|:-----|
| 📘 [`DetailsReadme/DetailsReadme.md`](DetailsReadme/DetailsReadme.md) | 三支路来源与取舍 · 缓存与生效判据 · 转换原理 · OpenClash 细节 · 一致性保证 |
| 🧪 [`skill/SKILL.md`](skill/SKILL.md) | 匹配语义判定 · 通配映射 · 加新源的方法 · 断言口径 · 七条不要越的线 |
| 🧰 [`skill/scripts/`](skill/scripts/) | `freeze_upstream.py` / `build_ads.py` / `convert_ruleset.py` / `regen.sh` |
| 🧷 [`OVERLAP.md`](OVERLAP.md) | 白名单 × 拦截集重叠清单（构建生成 · CI 校验） |
| 📄 [`WHITELIST-SLIM.md`](WHITELIST-SLIM.md) | 白名单瘦身留痕（保留/裁掉的逐条依据，CI 校验） |
| 📄 [`NOTICE.md`](NOTICE.md) | 来源与使用条件（数据 vs 脚本分开授权） |
| 📅 [`CHANGELOG.md`](CHANGELOG.md) | 规则变动记录 |

🧷 六份文件同一次生成、内容等价，由 CI 每次提交自动校验（三格式逐条比对 + 条数声明 + 产物可复现 + 上游快照完整性），读数不符会直接标红。

## 📚 来源与许可

| <div align="center">项</div> | <div align="center">说明</div> |
|:--|:--|
| 📄 上游 | [`VME98/jinx-rules`](https://github.com/VME98/jinx-rules) · 数据 `3.2.3` · `2026-10-18` |
| 🧩 其余来源 | `217heidai/adblockfilters` · AdGuard Chinese · 秋风 AWAvenue · CJX · xinggsf · jiekouAD（合计六个上游来源，落盘为 `upstream/` 下 3 组 12 个文件） |
| 📜 许可 | 各上游均未声明，本仓亦不主张；`skill/` 脚本与文档以 MIT 提供 |
| 🧬 规则数据 | 版权归各上游及其原始来源，任一上游作者如有异议，开 issue 即下架对应来源 |

📮 上游已自 3.2.4 起转为加密发布，本仓以 3.2.3 明文快照为基线、**不再跟随**，也**不监测上游发版**（冻结仓的取舍：CI 不联网，绿灯只由本仓自己的完整性决定）。`python skill/scripts/freeze_upstream.py --check` 只校验仓内快照；要拉新版得显式跑一次同目录下的 `freeze_upstream.py`，改动会留在 diff 里。详见 [`NOTICE.md`](NOTICE.md)。

---

<div align="center">

📊 上游数据来自 VME98/jinx-rules 与 217heidai/adblockfilters

</div>
