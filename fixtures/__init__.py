# -*- coding: utf-8 -*-
"""
业务 fixture 包。

根目录 conftest.py 会尝试 `from fixtures import login`，
把这里定义的 fixture 注册给全部用例使用。
"""
from fixtures.login import admin_logged_in, api, group_page

__all__ = ["admin_logged_in", "api", "group_page", "login"]

# conftest 里的历史挂载点（保持名称可用）
login = admin_logged_in
