# 📌 上游快照清单

> [!IMPORTANT]
> 本目录是**构建输入**，不是产物。**不要手改这里的任何文件** ——
> 手改会破坏「产物 == 源头重跑」的可复现断言（`verify_products.py` 会判负）。
> 要更新上游，跑 `python skill/scripts/freeze_upstream.py`，让改动留在 git diff 里可审计。

## 源策略

jinx 上游自 `3.2.4` 起改为加密发布（`new-rules/*.enc`，需接收方 P-256 私钥），
明文 `rules/` 停在 `3.2.3` —— 用 commit 钉住，任何情况下不动；
其余中文源为活源，由每周定时工作流（`.github/workflows/update.yml`）刷新，
任一源抓取失败即不落盘、不提交，仓内不出现半新半旧的快照。

构建只读本目录、**不联网**。

## 快照信息

| 项 | 值 |
|---|---|
| 取用时间（UTC） | `2026-10-27T12:05:13+00:00` |
| Jinx 明文通道锚点 | `VME98/jinx-rules@c85751d`（对应版本见 `jinx-3.2.3/version.json`） |
| 源文件数 | 12 |

## 文件明细

| 分组 | 文件 | 字节（LF 归一化） | 非注释行 | sha256 前 12 位 | 用途 |
|---|---|---|---|---|---|
| jinx-3.2.3 | `blacklist.txt` | 71283 | 3726 | `adcf99b214dd` | 上游黑名单（后缀语义） |
| jinx-3.2.3 | `blacklist_wildcard.txt` | 4582 | 264 | `63d63c644e56` | 上游黑名单通配 |
| jinx-3.2.3 | `whitelist.txt` | 5244 | 283 | `6d13c59c5bb8` | 上游白名单（精确语义） |
| jinx-3.2.3 | `whitelist_wildcard.txt` | 661 | 41 | `4b7c55399782` | 上游白名单通配 |
| jinx-3.2.3 | `version.json` | 898 | 30 | `d9c20f057a4c` | 上游版本自述 |
| 217heidai | `adblocksurgelite.list` | 162652 | 8480 | `e689b39dd3e8` | 16 源聚合后 ∩ china.txt 的 lite 档（DOMAIN-SET 格式） |
| 217heidai | `china.txt` | 208868 | 12205 | `168c85896ccd` | 中国域名清单（判定「中国生态」的基准） |
| cn | `AdGuard_Chinese_filter.txt` | 732762 | 21099 | `452f9412e6fa` | AdGuard 官方中文过滤器 |
| cn | `AWAvenue_Ads_Rule.txt` | 23470 | 984 | `fdf930d67659` | 秋风广告规则 |
| cn | `jiekouAD.txt` | 129174 | 5378 | `9590b2f34bf3` | 接口广告源（灰产长尾多，靠准入规则滤） |
| cn | `CJX_Annoyance_List.txt` | 57229 | 1840 | `f5afcf694eb6` | CJX 中文骚扰+广告 |
| cn | `xinggsf_mv.txt` | 6533 | 160 | `1165b91dd489` | xinggsf（优酷等） |

## 取用方式

构建产物（不联网，只读本目录）：

```bash
bash skill/scripts/regen.sh           # 一条命令：快照校验 → direct → ads → 六份产物 → 双闸门
bash skill/scripts/regen.sh --build   # 只重建，不跑闸门
```

更新上游（唯一允许联网的入口）：

```bash
python skill/scripts/freeze_upstream.py --check   # 先确认当前快照未被手改
python skill/scripts/freeze_upstream.py           # 抓取新版并更新本清单
```

## 来源与许可

- **217heidai**：<https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules>
- **cn**：<https://raw.githubusercontent.com/217heidai/adblockfilters/main/rules>
- **jinx-3.2.3**：<https://raw.githubusercontent.com/VME98/jinx-rules/c85751d/rules>

上游均未声明开源许可。本仓只做格式转换与合并，不主张对规则数据的任何权利；
任一上游作者提出异议即删除相关来源。
