# 📄 NOTICE · 来源与使用条件

本仓混合了两类内容，**适用条件不同，请分别看待**。缺少 LICENSE 文件不等于「无条件可用」，
这份 NOTICE 就是把条件写明的那一步。

## 一、规则数据：`upstream/` 与仓库根的六份产物

| 来源 | 上游仓库 | 许可状态（2026-10-27 经 GitHub API 逐仓核实） |
|:--|:--|:--|
| Jinx（明文快照 3.2.3） | `VME98/jinx-rules` | 未声明 |
| 217heidai（聚合仓，本仓 5 个中文源的直接取用点） | `217heidai/adblockfilters` | **GPL-3.0** |
| 秋风 AWAvenue | `TG-Twilight/AWAvenue-Ads-Rule` | **GPL-3.0** |
| CJX Annoyance | `cjx82630/cjxlist` | **LGPL-3.0** |
| AdGuard 系 / xinggsf / jiekouAD | 对应上游仓 | xinggsf / jiekouAD 未声明；AdGuard 系（`AdguardTeam/*`）为 GPL-3.0 |

- 🚫 **本仓不主张对规则数据的任何权利**，也不对其准确性、完整性、时效性作任何担保。
- ⚖️ **许可事实（v11 审查 3.5 修正）**：多数上游数据为 **GPL-3.0 / LGPL-3.0**，
  并非此前误记的「均未声明」。域名清单作为数据受何种程度的 GPL 约束属于灰色地带
  （同生态的 blackmatrix7 / hagezi 等仓均以类似方式再分发）；本仓做的是**格式转换与
  合并再分发**，该行为在上游条款下的合法性**未获逐一确认**。个人订阅使用风险极低；
  **二次分发或商用前，请自行核实各上游条款**（尤其 GPL-3.0 系），必要时联系上游作者。
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
