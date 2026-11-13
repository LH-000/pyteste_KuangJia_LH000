# -*- coding: utf-8 -*-
"""CRMEB 后台登录页 PoM（选择器沿用自原 CRMEB.py，已实测可用）。"""
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait


class LoginPage:
    """后台登录页：输入账号密码回车登录，等待跳转离开 /admin/login。"""

    URL_SUFFIX = "/admin/login"

    # 元素定位（实测自 CRMEB 后台 v1.0.0）
    _ACCOUNT = (By.CSS_SELECTOR, 'input[type="text"]')
    _PASSWORD = (By.CSS_SELECTOR, 'input[type="password"]')

    def __init__(self, driver, login_url: str, timeout: int = 15):
        self.driver = driver
        self.login_url = login_url
        self.timeout = timeout

    def open(self):
        self.driver.get(self.login_url)
        WebDriverWait(self.driver, self.timeout).until(
            EC.presence_of_element_located(self._ACCOUNT)
        )
        return self

    def login(self, account: str, password: str):
        """登录并等待离开登录页（跳转到后台首页）。"""
        wait = WebDriverWait(self.driver, self.timeout)
        wait.until(EC.presence_of_element_located(self._ACCOUNT)).send_keys(account)
        pwd = wait.until(EC.presence_of_element_located(self._PASSWORD))
        pwd.send_keys(password)
        pwd.send_keys("\n")  # 回车提交
        # 登录成功标志：URL 不再是 /admin/login
        WebDriverWait(self.driver, self.timeout).until_not(
            EC.url_contains(self.URL_SUFFIX)
        )
        return self
