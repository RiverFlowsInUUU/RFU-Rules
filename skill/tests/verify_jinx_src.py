#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""兼容垫片 —— 本脚本已更名，实际判据在 verify_products.py。

为什么保留这个文件：仓库的 CI 工作流（`.github/workflows/ci.yml`）里写的是
旧文件名，而更新 workflow 文件需要 token 具备 `workflow` 权限 —— 当前授权没有，
推送会被 GitHub 拒绝（`refusing to allow an OAuth App to create or update
workflow .github/workflows/ci.yml without workflow scope`）。

所以先用这个 3 行的转发垫片让 CI 保持绿色，待 `gh auth refresh -s workflow`
之后一次性换成新工作流并删掉本文件。**不要在这里加任何判据** —— 判据只有一份，
在 verify_products.py。
"""
import runpy
import sys
from pathlib import Path

sys.argv[0] = str(Path(__file__).with_name('verify_products.py'))
runpy.run_path(sys.argv[0], run_name='__main__')
