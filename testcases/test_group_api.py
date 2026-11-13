# -*- coding: utf-8 -*-
"""
用户分组 API 增删改查用例（requests 直连后台接口）。

接口契约（探测自真实前端流量）：
  查  GET    /adminapi/user/user_group/list?page=&limit=
  增  POST   /adminapi/user/user_group/save.html      {"group_name"}
  改  POST   /adminapi/user/user_group/save.html      {"id", "group_name"}
  删  DELETE /adminapi/user/user_group/del/{id}
"""
import allure
import pytest

from common.api_client import CrmebAdminApi
from common.config import ADMIN_ACCOUNT, ADMIN_PWD, BASE_ORIGIN
from common.data import group_name

pytestmark = [pytest.mark.api, pytest.mark.regression]


@allure.epic("CRMEB 后台")
@allure.feature("用户管理-用户分组")
class TestGroupApi:
    """用户分组接口 CRUD。"""

    # ---------------- 查 ----------------
    @allure.story("查")
    @allure.title("查-列表: 正常返回结构与字段")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p0
    def test_list_groups_success(self, api):
        data = api.list_groups(page=1, limit=15)
        assert isinstance(data["list"], list), "list 应为列表"
        assert data["count"] >= len(data["list"]), "count 不应小于当前页行数"
        for row in data["list"]:
            assert set(row) >= {"id", "group_name"}, f"行字段缺失: {row}"
            assert row["group_name"], f"分组名不应为空: {row}"

    @allure.story("查")
    @allure.title("查-分页: limit 生效且翻页数据递进")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.p2
    def test_list_groups_pagination(self, api):
        first = api.list_groups(page=1, limit=2)
        assert len(first["list"]) <= 2, "limit=2 时单页不应超过 2 行"
        if first["count"] > 2:
            second = api.list_groups(page=2, limit=2)
            ids1 = {r["id"] for r in first["list"]}
            ids2 = {r["id"] for r in second["list"]}
            assert not (ids1 & ids2), "第1页与第2页不应出现重复数据"

    @allure.story("查")
    @allure.title("查-鉴权: 缺少 token 应返回 401")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.p1
    def test_list_without_token(self):
        anon = CrmebAdminApi()  # 不 login，直接裸查
        resp = anon._request("GET", "/user/user_group/list?page=1&limit=15")
        body = resp.json()
        assert body["status"] == 401, f"预期 401，实际 {body['status']}"
        assert "登录已过期" in body["msg"], f"msg 应提示登录过期: {body['msg']}"

    # ---------------- 增 ----------------
    @allure.story("增")
    @allure.title("增-正常: 新建分组后可在列表查到")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p0
    def test_create_group_success(self, api):
        name = group_name()
        try:
            body = api.create_group(name)
            assert body["status"] == 200, f"创建失败: {body}"
            gid = api.find_group_id_by_name(name)
            assert gid is not None, f"新建分组 {name} 未出现在列表中"
        finally:
            if (gid := api.find_group_id_by_name(name)) is not None:
                api.delete_group(gid)

    @allure.story("增")
    @allure.title("增-异常: 空分组名应被拒绝(400)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.p1
    def test_create_group_empty_name(self, api):
        body = api.create_group("")
        assert body["status"] == 400, f"预期 400，实际 {body['status']}"
        assert body["msg"] == "请输入分组名称", f"msg 不符: {body['msg']}"

    # ---------------- 改 ----------------
    @allure.story("改")
    @allure.title("改-正常: 修改分组名后列表同步更新")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p0
    def test_update_group_success(self, api):
        old_name, new_name = group_name(), group_name()
        gid = None
        try:
            api.create_group(old_name)
            gid = api.find_group_id_by_name(old_name)
            assert gid is not None, "前置失败：新建分组未查到"
            body = api.update_group(gid, new_name)
            assert body["status"] == 200, f"修改失败: {body}"
            assert api.find_group_id_by_name(new_name) == gid, "新名应挂在原 id 上"
            assert api.find_group_id_by_name(old_name) is None, "旧名应已不存在"
        finally:
            if gid is not None:
                api.delete_group(gid)

    @allure.story("改")
    @allure.title("改-异常: 修改不存在的分组应报错(400 数据不存在)")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.p1
    def test_update_group_not_exist(self, api):
        body = api.update_group(99999999, group_name())
        assert body["status"] == 400, f"预期 400，实际 {body['status']}"
        assert body["msg"] == "数据不存在", f"msg 不符: {body['msg']}"

    # ---------------- 删 ----------------
    @allure.story("删")
    @allure.title("删-正常: 删除分组后列表查无此组")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p0
    def test_delete_group_success(self, api):
        name = group_name()
        api.create_group(name)
        gid = api.find_group_id_by_name(name)
        assert gid is not None, "前置失败：新建分组未查到"
        body = api.delete_group(gid)
        assert body["status"] == 200, f"删除失败: {body}"
        assert api.find_group_id_by_name(name) is None, "删除后仍能查到该分组"

    @allure.story("删")
    @allure.title("删-异常: 删除不存在的分组返回幂等成功(200)")
    @allure.severity(allure.severity_level.MINOR)
    @pytest.mark.p2
    def test_delete_group_not_exist(self, api):
        body = api.delete_group(99999999)
        assert body["status"] == 200, f"预期幂等 200，实际 {body['status']}"
