#!/usr/bin/env bash
# regen.sh —— 一条命令重跑全部六份产物（离线，只读 upstream/）
#
# 顺序不可交换：
#   ① direct 先生成 —— build_ads.py 要读 surge-direct.list 做「顺序保护重叠」报告；
#   ② ads 再由三支路合成 —— 只读 upstream/，不联网；
#   ③ 闸门最后跑 —— 两层都要（verify 判对错，selftest 证明闸门本身能抓错）。
#
# 用法：
#   bash skill/scripts/regen.sh            # 重跑 + 校验
#   bash skill/scripts/regen.sh --build    # 只重跑，不校验
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || PY=python

SK=skill/scripts/convert_ruleset.py

echo "== 0/4 校验上游快照未被手改 =="
"$PY" skill/scripts/freeze_upstream.py --check

echo
echo "== 1/4 direct 放行清单（上游白名单 → 瘦身 → 三平台）=="
"$PY" "$SK" --src upstream/jinx-3.2.3 --out . \
    --fixed whitelist.txt --wild whitelist_wildcard.txt \
    --tag direct --mode exact --naming repo \
    --guard-against-fixed blacklist.txt \
    --guard-against-wild blacklist_wildcard.txt \
    --slim-report WHITELIST-SLIM.md \
    --extra-white custom-direct.list

echo
echo "== 2/4 ads 域名集（三支路合成）+ 重叠清单 =="
# --overlap 让「白名单×拦截集」的重叠清单落盘成仓库根的 OVERLAP.md。
# 此前它只在 build/ 里（被 gitignore），订阅者看不到、CI 也不校验 ——
# 而它恰恰是本仓最该被看见的风险（42 条域名只能靠规则顺序存活）。
"$PY" skill/scripts/build_ads.py --overlap OVERLAP.md

echo
echo "== 3/4 ads 产物（→ mihomo / Surge / sing-box）=="
# --label 决定产物表头 `# source:` 的文案。别让内部中间目录（build/ads）
# 出现在用户会下载的文件里 —— 那对读者毫无意义。
"$PY" "$SK" --src build/ads --out . \
    --fixed ads-src.txt \
    --tag ads --mode suffix --naming repo \
    --label "$(cat build/ads/label.txt)" \
    --extra custom-ads.list

echo
if [ "${1:-}" = "--build" ]; then
  echo "== 只构建，跳过校验 =="
  echo "⚠️ 本次产物未经双闸门校验 —— 提交前请补跑 bash skill/scripts/regen.sh（不带 --build）"
  exit 0
fi

echo "== 4/4 闸门（两层）=="
"$PY" skill/tests/verify_products.py
"$PY" skill/tests/selftest_negative.py

echo
echo "✅ 全部通过。产物：mihomo-ads.yaml / surge-ads.list / sing-box-ads.json"
echo "                  mihomo-direct.yaml / surge-direct.list / sing-box-direct.json"
