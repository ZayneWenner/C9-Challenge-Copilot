#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""命令行入口包装：python copilot.py check --repo . --deliverables "*proposal*"

不写安装步骤也能跑：只要 Python 3.9+，在仓库根目录执行即可。
"""

import sys

from challenge_copilot.cli import main

if __name__ == "__main__":
    sys.exit(main())
