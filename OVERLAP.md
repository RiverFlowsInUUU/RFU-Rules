# ⚠️ 白名单 × 拦截集 重叠清单

> 本文件由 `skill/scripts/build_ads.py` 生成，**勿手改**。
> 生成依据：upstream/(A+B+C) · jinx 3.2.3 (2026-10-18)
> CI 会独立复算并与此文件比对（verify_products.py 第 12 段 · 共 16 段），数字或清单不符即判负。

**共 42 条**：21 条同域同名 + 21 条上层后缀覆盖（白名单共 49 条，其余 7 条与拦截集无关）。

## 这是什么

`surge-direct.list`（放行）与 `surge-ads.list`（拦截）**不是互斥的两个集合**。
拦截集收了平台主域（`umeng.com`、`umeng` 系、`tanx.com`、`getui.net`、`jpush.cn` …），
而放行集要保的是同族里的功能子域（推送建连、微信登录、一键登录）。
域名规则只能整棵树一起拦或一起放，所以两者必然重叠 —— 重叠本身不是 bug。

## 所以：放行必须排在拦截之前

重叠域名的处置完全依赖**规则顺序**：更具体的那条先命中。

| 客户端 | 靠什么保证 |
|:--|:--|
| mihomo / OpenClash | `rules` 列表顺序，`rfu-direct` 那条写在 `rfu-ads` 之前 |
| Surge / Egern | `[Rule]` 顺序同上；**拦截行不得加 `pre-matching`**（见下） |
| sing-box | `rules` 数组顺序，`rfu-direct` 的元素排在 `rfu-ads` 之前 |

⚠️ **Surge 的 `pre-matching` 会破坏这个顺序。** 官方文档：
「Rules tagged with `pre-matching` are extracted and checked before everything else」
「Pre-matched rules have the highest priority」，且该参数**只支持 REJECT 系策略** ——
放行行无法用同一参数自救。给拦截行加上它，下面这 42 条会全部失效，
表现出来就是推送收不到、微信登录转圈。

## 一、同域同名（21 条）

拦截集里就有这一条，靠放行行先命中救回。

| 域名 | 备注 |
|:--|:--|
| `apd-pcdnwxlogin.teg.tencent-cloud.net` | 同名 |
| `apd-pcdnwxnat.teg.tencent-cloud.net` | 同名 |
| `apd-pcdnwxstat.teg.tencent-cloud.net` | 同名 |
| `appcfg.v.qq.com` | 同名 |
| `cactus.jd.com` | 同名 |
| `cl-m.i4.cn` | 同名 |
| `dypnsapi.aliyuncs.com` | 同名 |
| `effect.snssdk.com` | 同名 |
| `httpdns.meituan.com` | 同名 |
| `jpush.cn` | 同名 |
| `license.vodglcdn.com` | 同名 |
| `list-app-m.i4.cn` | 同名 |
| `m-cloud.zhihu.com` | 同名 |
| `mssdk.bytedance.com` | 同名 |
| `mssdk.volces.com.queniusz.com` | 同名 |
| `nbfriend-mtop.cainiao.com` | 同名 |
| `pitaya.bytedance.com` | 同名 |
| `pub-conf-m.i4.cn` | 同名 |
| `tnc3-aliec2.snssdk.com` | 同名 |
| `tnc3-alisc1.snssdk.com` | 同名 |
| `tnc3-bjlgy.snssdk.com` | 同名 |

## 二、上层后缀覆盖（21 条）

拦截集只有父域，子域被连带；同样靠放行行先命中。

| 放行条目 | 覆盖它的拦截规则 |
|:--|:--|
| `aspect-upush.umeng.com` | `umeng.com` |
| `gm.mmstat.com` | `mmstat.com` |
| `iuni.telecome.cn` | `telecome.cn` |
| `oneid.gepush.com` | `gepush.com` |
| `oneid.getui.net` | `getui.net` |
| `praisewindow.ugsdk.cn` | `ugsdk.cn` |
| `s.jpush.cn` | `jpush.cn` |
| `sdk.open.talk.gepush.com` | `gepush.com` |
| `sdk.open.talk.getui.net` | `getui.net` |
| `sdkapi.cloooud.com` | `cloooud.com` |
| `seeds-sina.xycdn.com` | `xycdn.com` |
| `sis-ipv6.jpush.cn` | `jpush.cn` |
| `sis.jpush.io` | `jpush.io` |
| `status-ipv6.jpush.cn` | `jpush.cn` |
| `tsis-ipv6.jpush.cn` | `jpush.cn` |
| `tsis.jpush.cn` | `jpush.cn` |
| `user-ipv6.jpush.cn` | `jpush.cn` |
| `user.jpush.cn` | `jpush.cn` |
| `wagbridge.alsc-prd.tanx.com` | `tanx.com` |
| `wgo.mmstat.com` | `mmstat.com` |
| `zlink.ugsdk.cn` | `ugsdk.cn` |

## 改判据时注意

- 想让这份清单变短，只能从拦截集里剔除对应**上层域** —— 但那会连带放过整个平台，
  历史上试过（删 `tanx.com` 保一个子域），结果漏拦面积远大于收益，已回退。
  `build_ads.py` 因此**只报告、不删除**。
- 新增放行条目时，先看它是否落在这里：若是，说明它已经在靠顺序保护，
  不需要额外动作；若不是，才需要考虑是否要改拦截集。
