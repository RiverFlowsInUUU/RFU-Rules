<div align="center">

# 🛑 RFU 去广告规则

**一份名单，四种格式**

拦广告 · 统计 · 隐私采集 · PCDN —— 不误杀推送登录，不拦 IP，不碰灰产

[![Frozen](https://img.shields.io/badge/Frozen-Jinx%203.2.3-8250df?style=flat-square)](https://github.com/VME98/jinx-rules)
[![CI](https://github.com/RiverFlowsInUUU/RFU-Rules/actions/workflows/ci.yml/badge.svg)](https://github.com/RiverFlowsInUUU/RFU-Rules/actions/workflows/ci.yml)
[![Ads](https://img.shields.io/badge/%E6%8B%A6%E6%88%AA-9534%20%E6%9D%A1-0969da?style=flat-square)](#-订阅)
[![White](https://img.shields.io/badge/%E6%94%BE%E8%A1%8C-49%20%E6%9D%A1-2da44e?style=flat-square)](#-订阅)

[![mihomo](https://img.shields.io/badge/mihomo-OpenClash-1f6feb?style=flat-square)](#-接入)
[![Surge](https://img.shields.io/badge/Surge-RULE--SET-orange?style=flat-square)](#-接入)
[![Egern](https://img.shields.io/badge/Egern-%E5%A4%8D%E7%94%A8%20Surge%20%E6%A0%BC%E5%BC%8F-8957e5?style=flat-square)](#-接入)
[![sing-box](https://img.shields.io/badge/sing--box-source%20JSON-blue?style=flat-square)](#-接入)

</div>

> 给自建网关（软路由 / 代理内核）准备的去广告域名规则集：约 9500 个域名，纯域名后缀、无通配无正则，路由器和手机都跑得动。四端内容逐条一致，不是四份各自维护的列表。

> 🤖 AI agent 维护入口 → [`skill/SKILL.md`](skill/SKILL.md)

## 📥 订阅

| <div align="center">客户端</div> | <div align="center">🚫 拦截规则集</div> | <div align="center">✅ 放行规则集</div> |
|:--|:--|:--|
| **mihomo** / OpenClash | [`mihomo-ads.yaml`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/mihomo-ads.yaml) `9534` | [`mihomo-direct.yaml`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/mihomo-direct.yaml) `49` |
| **Surge** / **Egern** | [`surge-ads.list`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-ads.list) `9534` | [`surge-direct.list`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-direct.list) `49` |
| **sing-box** | [`sing-box-ads.json`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/sing-box-ads.json) `9534` | [`sing-box-direct.json`](https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/sing-box-direct.json) `49` |

📌 链接即地址，右键复制即可；备用镜像把前缀换成 `https://cdn.jsdelivr.net/gh/RiverFlowsInUUU/RFU-Rules@main/`。

<details>
<summary>🍂 想再叠加 <b>AWAvenue 秋风规则</b>？（可选 —— 本仓已含其 969 条中的 912 条）</summary>

| <div align="center">客户端</div> | <div align="center">🚫 拦截规则集</div> |
|:--|:--|
| **mihomo** / OpenClash | [`AWAvenue-Ads-Rule-Clash-Classical.yaml`](https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Clash-Classical.yaml) `965` |
| **Surge** | [`AWAvenue-Ads-Rule-Surge-RULE-SET.list`](https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Surge-RULE-SET.list) `965` |
| **sing-box** | [`AWAvenue-Ads-Rule-Singbox.json`](https://raw.githubusercontent.com/TG-Twilight/AWAvenue-Ads-Rule/main/Filters/AWAvenue-Ads-Rule-Singbox.json) `965` |

重复规则对结果无副作用，只是体积多几百条。第三方规则由对方托管，只给官方地址。

</details>

## 🔌 接入

⚡ 只记一条：**放行在前，拦截在后，其余分流接在后面。**

```text
1. 放行规则集  →  DIRECT     ← 必须最前，见下方说明
2. 拦截规则集  →  REJECT
3. 常规分流（GEOSITE,cn / GEOIP,cn ...）→ 按你原有的走
```

> [!IMPORTANT]
> **放行清单不许删，哪怕拦截集里也有同样的域。** 拦截集收了 `umeng.com`、`tanx.com`、`getui.net` 这类平台主域，而放行清单保的是同族里的推送、登录功能子域——更具体的规则先命中，各得其所。两者的重叠当前是 **42 条**，逐条列在 [`OVERLAP.md`](OVERLAP.md)。删掉放行行，推送和微信登录立刻失效。

> [!WARNING]
> Surge 用户：拦截行**不要加 `pre-matching`**。它会抢先于一切规则生效，放行清单整份作废——症状就是推送收不到、微信登录转圈。用 `extended-matching` 即可。

各端的更多细节（Egern 的 DNS 层拒答、sing-box 参数坑、OpenClash 必关的开关）：

<details>
<summary>🔷 <b>mihomo / OpenClash</b></summary>

```yaml
rule-providers:
  rfu-ads:
    type: http
    behavior: classical
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

> [!IMPORTANT]
> OpenClash 需关闭 `绕过中国大陆 IP`（`china_ip_route`）：大陆 IP 直接放行、不进内核，规则会整体失效。

```bash
uci set openclash.config.china_ip_route='0' && uci commit openclash
/etc/init.d/openclash restart
```

</details>

<details>
<summary>🔶 <b>Surge</b></summary>

```
[Rule]
RULE-SET,https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-direct.list,DIRECT,extended-matching
RULE-SET,https://raw.githubusercontent.com/RiverFlowsInUUU/RFU-Rules/main/surge-ads.list,REJECT,extended-matching
```

`extended-matching` 让域名规则在 App 直连 IP 时按 TLS SNI / HTTP Host 兜底，缺了它拦截会大批失效。

</details>

<details>
<summary>🟣 <b>Egern</b>（直接复用 Surge 那份）</summary>

```yaml
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
```

DNS 层拒答（可选）与组名改法等细节见[详情](DetailsReadme/DetailsReadme.md)。

</details>

<details>
<summary>🔷 <b>sing-box</b>（1.14.2 实测）</summary>

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

</details>

## ✨ 这份规则集的特点

| | | |
|:--|:--|:--|
| 🚫 拦截 | **9534 条** | 广告、统计、隐私采集、PCDN；赌博色情灰产在构建时就被排除，不进名单 |
| ✅ 放行 | **49 条** | 43 条精确 + 6 条后缀（含 5 条手工补充） |
| 🧩 四端同源 | 同一批域名、四种格式，逐条等价 | 换客户端不用换名单 |
| 🪶 轻 | 纯域名后缀，无通配、无正则、无 IP | 软路由与手机都无匹配负担 |
| 📌 上游快照 | 冻结于 `3.2.3` · `2026-10-18` | 固定基线，更新由本仓统一发布，不随上游滚动 |

放行那 49 条，全是被拦截规则误伤的推送、登录功能域——名单很短，但少了它日常使用寸步难行。

## 📖 想深入了解

| 文档 | 内容 |
|:--|:--|
| 📘 [`DetailsReadme`](DetailsReadme/DetailsReadme.md) | 数据从哪来、为什么这么取舍、转换原理、一致性如何保证 |
| 🧪 [`skill/SKILL.md`](skill/SKILL.md) | 维护者手册：构建链、断言、加新源的完整流程 |
| 🧷 [`OVERLAP.md`](OVERLAP.md) | 放行 × 拦截重叠清单（构建生成，CI 校验） |
| 📄 [`WHITELIST-SLIM.md`](WHITELIST-SLIM.md) | 白名单瘦身留痕（构建生成，CI 校验） |
| 📄 [`NOTICE.md`](NOTICE.md) | 来源与使用条件（数据 vs 脚本分开授权） |
| 📅 [`CHANGELOG.md`](CHANGELOG.md) | 变动记录 |

## 📚 数据来源

| <div align="center">来源</div> | <div align="center">说明</div> |
|:--|:--|
| 📄 上游 | [`VME98/jinx-rules`](https://github.com/VME98/jinx-rules) · 数据 `3.2.3` · `2026-10-18` |
| 🧩 其余 | `217heidai/adblockfilters` · AdGuard Chinese · 秋风 AWAvenue · CJX · xinggsf · jiekouAD（共六个来源，快照落盘于 `upstream/`） |
| 📜 许可 | 规则数据版权归各上游，本仓不主张、有异议即下架；脚本与文档以 MIT 提供 |

---

<div align="center">

📊 上游数据来自 VME98/jinx-rules 与 217heidai/adblockfilters

</div>
