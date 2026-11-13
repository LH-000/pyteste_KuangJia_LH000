# -*- coding: utf-8 -*-
"""
业务 fixture：

api             session 级，已登录的 API 客户端（API 用例 + UI 用例的造数/清理）
admin_logged_in session 级，Selenium 已登录后台的 driver
group_page      function 级，每个用例重新进入「用户分组」页面，互不污染
"""
import pytest

from common.api_client import CrmebAdminApi
from common.config import ADMIN_ACCOUNT, ADMIN_PWD, LOGIN_URL
from pages.group_page import GroupPage
from pages.login_page import LoginPage


@pytest.fixture(scope="session")
def api():
    """已登录的后台 API 会话（整个测试会话共用一个 token）。"""
    client = CrmebAdminApi()
    client.login()
    yield client


@pytest.fixture(scope="session")
def admin_logged_in(driver):
    """Selenium 登录后台一次，整个会话复用（driver 本身是 session 级）。"""
    LoginPage(driver, LOGIN_URL).open().login(ADMIN_ACCOUNT, ADMIN_PWD)
    return driver


@pytest.fixture()
def group_page(admin_logged_in):
    """每个用例都从干净的「用户分组」页面开始。"""
    page = GroupPage(admin_logged_in)
    page.open()
    yield page
    # 收尾截图：失败用例也能在报告里看到最终现场（conftest 另有失败即时截图）
    page.screenshot("用例结束现场")
    # 关闭用例可能遗留的弹窗（如空名校验拦截、失败时的弹窗），
    # 否则遮罩会挡住下一个用例的菜单点击
    page.dismiss_any_message_box()
