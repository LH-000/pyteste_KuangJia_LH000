# -*- coding: utf-8 -*-
"""
CRMEB 后台 API 客户端（requests 封装）。

覆盖用户分组模块的增/删/改/查四个接口（探测自真实前端流量）：
  查  GET    /adminapi/user/user_group/list?page=&limit=
  增  POST   /adminapi/user/user_group/save.html      body {"group_name": "..."}
  改  POST   /adminapi/user/user_group/save.html      body {"id": N, "group_name": "..."}
  删  DELETE /adminapi/user/user_group/del/{id}
登录：POST /adminapi/login，鉴权头为 Authori-zation: Bearer <token>。
"""
import secrets
import string

import allure
import requests

from common.config import ADMIN_ACCOUNT, ADMIN_PWD, BASE_ORIGIN


def _rand_key(length: int = 13) -> str:
    """登录参数里的 key：前端生成的一段随机串，服务端不校验内容。"""
    return "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(length))


class CrmebAdminApi:
    """带登录态的后台 API 会话。

    用法：
        api = CrmebAdminApi()
        api.login()
        api.list_groups()
    每个请求/响应都会自动以附件形式写入 Allure 报告，方便排错。
    """

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        self.session = requests.Session()
        self.token = None

    # ---- 基础 -------------------------------------------------------------
    def _url(self, path: str) -> str:
        return f"{BASE_ORIGIN}/adminapi{path}"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = self._url(path)
        resp = self.session.request(
            method, url, timeout=self.timeout, **kwargs
        )
        # 请求/响应摘要进报告（截断避免刷屏）
        req_body = kwargs.get("json") or kwargs.get("params") or ""
        allure.attach(
            f"{method} {url}\n请求: {str(req_body)[:300]}\n"
            f"响应: {resp.status_code} {resp.text[:500]}",
            name=f"[API] {method} {path}",
            attachment_type=allure.attachment_type.TEXT,
        )
        return resp

    # ---- 登录 -------------------------------------------------------------
    def login(self) -> str:
        """管理员登录，成功后 Session 自动携带 Authori-zation 头，返回 token。"""
        resp = self._request(
            "POST",
            "/login",
            json={
                "account": ADMIN_ACCOUNT,
                "pwd": ADMIN_PWD,
                "key": _rand_key(),
                "captchaType": "blockPuzzle",
                "captchaVerification": "",
            },
        )
        body = resp.json()
        assert body.get("status") == 200, f"登录失败: {body.get('msg')}"
        self.token = body["data"]["token"]
        self.session.headers["Authori-zation"] = f"Bearer {self.token}"
        return self.token

    # ---- 用户分组 CRUD ----------------------------------------------------
    def list_groups(self, page: int = 1, limit: int = 15) -> dict:
        """查：分组列表，返回 {"list": [{"id":..,"group_name":..}], "count": 总数}。"""
        resp = self._request(
            "GET", "/user/user_group/list", params={"page": page, "limit": limit}
        )
        body = resp.json()
        assert body.get("status") == 200, f"查询分组列表失败: {body.get('msg')}"
        return body["data"]

    def find_group_id_by_name(self, name: str) -> "int | None":
        """按分组名全量翻页查找，返回第一个匹配的 id；找不到返回 None。"""
        limit = 100
        page = 1
        while True:
            data = self.list_groups(page=page, limit=limit)
            rows = data.get("list", [])
            for row in rows:
                if row.get("group_name") == name:
                    return row["id"]
            if page * limit >= data.get("count", 0) or not rows:
                return None
            page += 1

    def create_group(self, name: str) -> dict:
        """增：新建分组，返回接口原始响应体。"""
        return self._request(
            "POST", "/user/user_group/save.html", json={"group_name": name}
        ).json()

    def update_group(self, group_id: int, name: str) -> dict:
        """改：修改分组名，返回接口原始响应体。"""
        return self._request(
            "POST",
            "/user/user_group/save.html",
            json={"id": group_id, "group_name": name},
        ).json()

    def delete_group(self, group_id: int) -> dict:
        """删：删除分组，返回接口原始响应体。"""
        return self._request(
            "DELETE", f"/user/user_group/del/{group_id}"
        ).json()
