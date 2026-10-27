# 📄 NOTICE · 来源与使用条件

本仓混合了两类内容，**适用条件不同，请分别看待**。缺少 LICENSE 文件不等于「无条件可用」，
这份 NOTICE 就是把条件写明的那一步。

## 一、规则数据：`upstream/` 与仓库根的六份产物

| 来源 | 上游仓库 | 许可状态 |
|:--|:--|:--|
| Jinx（明文快照 3.2.3） | `VME98/jinx-rules` | 未声明 |
| 217heidai | `217heidai/adblockfilters` | 未声明（该仓 README 自称聚合） |
| AdGuard Chinese / EasyList China | 对应上游仓 | 未声明 |
| 秋风 AWAvenue | `TG-Twilight/AWAvenue-Ads-Rule` | GPL-3.0 |
| CJX Annoyance / xinggsf / jiekouAD | 对应上游仓 | 未声明 |

- 🚫 **本仓不主张对规则数据的任何权利**，也不对其准确性、完整性、时效性作任何担保。
- ⚖️ 各上游均未声明开源许可（`license: null`）。本仓做的是**格式转换与合并再分发**，
  这一行为在各上游条款下的合法性**未获确认**；如需商用或再分发，请自行逐一核实上游条款。
- 📮 任一上游的权利人提出异议，**开 issue 即下架对应来源**，无需解释、不设前置条件。

## 二、非数据部分：`skill/` 下的脚本与仓库内文档

- ✅ `skill/scripts/*.py`、`skill/tests/*.py`、`skill/scripts/regen.sh`、`skill/SKILL.md`
  与本仓的说明性文档（README / DetailsReadme / OVERLAP.md / 本文件），
  **以 MIT 许可提供**（SPDX：`MIT`），可自由使用、修改、再分发，保留出处即可。
- 这部分**不含规则数据**，因此可以单独授权。

## 三、本仓不提供的东西

- 🚫 不提供法律意见。上面第 1 节的风险判断只是维护者的理解，不构成对合规性的保证。
- 🚫 不提供任何 SLA。规则集是「按现状」交付，漏拦与误拦都可能存在，且不做赔偿承诺。
- 🚫 不代任何上游发声。本仓与 `VME98/jinx-rules`、`217heidai/adblockfilters`
  等上游**没有隶属或授权关系**，只是它们的消费者。

---

📌 这份文件解决的是「**能不能用、用到什么程度**」；「**怎么用**」看 [README](README.md)，
「**怎么改**」看 [skill/SKILL.md](skill/SKILL.md)。
