# -*- coding: utf-8 -*-
"""
框架统一配置：读取 env_config.py 的环境信息，并支持环境变量覆盖。

优先级：环境变量  >  env_config.py 中的默认值
    CRMEB_BASE_URL  覆盖 env_config.URL    （后台登录页完整地址）
    CRMEB_ADMIN     覆盖 env_config.admin
    CRMEB_PWD       覆盖 env_config.passwd
"""
import os
from urllib.parse import urlparse

import env_config

# 允许的 URL 协议白名单：框架只对 http/https 的被测地址发请求
_ALLOWED_SCHEMES = ("http", "https")


def _origin_of(url: str) -> str:
    """从完整页面地址提取协议+主机+端口，例如
    http://192.168.149.128:8899/admin/login -> http://192.168.149.128:8899
    """
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"被测地址协议不合法：{url!r}（仅允许 http/https）"
        )
    if not parsed.hostname:
        raise ValueError(f"被测地址缺少主机名：{url!r}")
    netloc = parsed.netloc
    return f"{parsed.scheme}://{netloc}"


def _login_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise ValueError(
            f"被测地址协议不合法：{url!r}（仅允许 http/https）"
        )
    return url


# ---- 对外配置项 ------------------------------------------------------------
# 后台登录页（UI 用例从这里进入）
LOGIN_URL = _login_url(os.getenv("CRMEB_BASE_URL", env_config.URL))
# 服务根地址（API 客户端用它拼 /adminapi 前缀）
BASE_ORIGIN = _origin_of(LOGIN_URL)

ADMIN_ACCOUNT = os.getenv("CRMEB_ADMIN", env_config.admin)
ADMIN_PWD = os.getenv("CRMEB_PWD", env_config.passwd)
