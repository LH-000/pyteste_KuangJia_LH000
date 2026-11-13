# -*- coding: utf-8 -*-
"""
用户分组 UI 增删改查用例（Selenium 驱动真实后台页面）。

套路：UI 操作 -> UI 断言；造数/清理优先走 API（快且稳），
保证用例失败时也尽量清掉自己造的数据。
"""
import allure
import pytest

from common.data import group_name

pytestmark = [pytest.mark.ui, pytest.mark.regression]


@allure.epic("CRMEB 后台")
@allure.feature("用户管理-用户分组")
class TestGroupUi:
    """用户分组页面 CRUD。"""

    # ---------------- 查 ----------------
    @allure.story("查")
    @allure.title("查-页面: 用户分组列表正常加载")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p0
    def test_ui_group_page_loaded(self, group_page):
        names = group_page.row_names()
        assert names, "分组列表应至少有一行数据"
        assert all(names), "每行分组名不应为空"
        group_page.screenshot("用户分组列表")

    # ---------------- 增 ----------------
    @allure.story("增")
    @allure.title("增-正常: 弹窗新建分组，列表末页可见")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p0
    def test_ui_create_group(self, group_page, api):
        name = group_name()
        gid = None
        try:
            group_page.open_add_dialog()
            group_page.fill_group_name(name)
            group_page.confirm_dialog()
            # 新建分组 id 最大，列表升序 -> 跳最后一页验证
            group_page.goto_last_page()
            group_page.screenshot(f"新建后最后一页(含 {name})")
            assert name in group_page.row_names(), "最后一页应出现新建的分组"
            gid = api.find_group_id_by_name(name)
            assert gid is not None, "API 侧也应能查到新建分组"
        finally:
            if gid is None:
                gid = api.find_group_id_by_name(name)
            if gid is not None:
                api.delete_group(gid)

    @allure.story("增")
    @allure.title("增-异常: 弹窗空名提交被前端校验拦截")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.p1
    def test_ui_create_empty_name(self, group_page):
        group_page.open_add_dialog()
        group_page.submit_dialog_expect_stay()
        group_page.screenshot("空名提交被拦截")
        err = group_page.form_error_text()
        assert err, "应出现表单校验错误提示"
        assert "分组名称" in err, f"校验提示应指向分组名称: {err}"

    # ---------------- 改 ----------------
    @allure.story("改")
    @allure.title("改-正常: 行内修改分组名后列表同步更新")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p0
    def test_ui_edit_group(self, group_page, api):
        old_name, new_name = group_name(), group_name()
        api.create_group(old_name)
        gid = api.find_group_id_by_name(old_name)
        assert gid is not None, "前置失败：API 造数未查到"
        try:
            group_page.goto_last_page()
            idx = group_page.find_row_index_by_name(old_name)
            assert idx is not None, f"最后一页应能找到 {old_name}"
            group_page.open_edit_dialog(idx)
            group_page.fill_group_name(new_name)
            group_page.confirm_dialog()
            group_page.screenshot("修改提交后")
            # 提交后表格原地刷新，同行应变为新名字
            assert group_page.find_row_index_by_name(new_name) is not None, (
                f"行内应显示新名字 {new_name}"
            )
            assert group_page.find_row_index_by_name(old_name) is None, (
                f"旧名字 {old_name} 应消失"
            )
        finally:
            api.delete_group(gid)

    # ---------------- 删 ----------------
    @allure.story("删")
    @allure.title("删-正常: 行内删除分组并确认后行消失")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.p0
    def test_ui_delete_group(self, group_page, api):
        name = group_name()
        api.create_group(name)
        gid = api.find_group_id_by_name(name)
        assert gid is not None, "前置失败：API 造数未查到"
        try:
            group_page.goto_last_page()
            idx = group_page.find_row_index_by_name(name)
            assert idx is not None, f"最后一页应能找到 {name}"
            group_page.screenshot("删除前")
            group_page.click_delete(idx)
            group_page.confirm_delete()
            group_page.wait_name_disappear(name)
            group_page.screenshot("删除确认后")
            assert name not in group_page.row_names(), "该行应已从表格消失"
        finally:
            api.delete_group(gid)  # 幂等兜底清理
