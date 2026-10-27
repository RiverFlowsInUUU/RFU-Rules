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
    --extra-white custom-direct.list

echo
echo "== 2/4 ads 域名集（三支路合成）=="
"$PY" skill/scripts/build_ads.py

echo
echo "== 3/4 ads 产物（→ mihomo / Surge / sing-box）=="
"$PY" "$SK" --src build/ads --out . \
    --fixed ads-src.txt \
    --tag ads --mode suffix --naming repo \
    --extra custom-ads.list

echo
if [ "${1:-}" = "--build" ]; then
  echo "== 只构建，跳过校验 =="
  exit 0
fi

echo "== 4/4 闸门（两层）=="
"$PY" skill/tests/verify_products.py
"$PY" skill/tests/selftest_negative.py

echo
echo "✅ 全部通过。产物：mihomo-ads.yaml / surge-ads.list / sing-box-ads.json"
echo "                  mihomo-direct.yaml / surge-direct.list / sing-box-direct.json"
