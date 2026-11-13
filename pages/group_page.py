# -*- coding: utf-8 -*-
"""
CRMEB 后台「用户 -> 用户分组」页 PoM。

页面结构（element-ui，实测）：
  - 左侧一级菜单: li.layout-columns[title="用户"]，子菜单项文本「用户分组」
  - 列表主体表:   .el-table__body-wrapper tr.el-table__row  第2列是分组名
  - 操作列(固定): .el-table__fixed-body-wrapper tr.el-table__row 内有 修改/删除
    主表第 i 行与固定列第 i 行一一对应
  - 分页: .el-pagination .el-pager li.number（列表按 id 升序，新建项在最后一页）
  - 新增/编辑弹窗: 标题「添加分组/修改分组」，输入框 placeholder=请输入分组名称，
    底部 取消/确定
  - 删除确认: 弹窗标题「提示」，正文「确定要删除分组吗？」，底部 取消/确定
"""
import time

import allure
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

# 主表行 / 固定操作列行（索引对齐）
_ROW_BODY = (By.CSS_SELECTOR, ".el-table__body-wrapper tr.el-table__row")
_ROW_FIXED = (By.CSS_SELECTOR, ".el-table__fixed-body-wrapper tr.el-table__row")
# 右上角「温馨提示」等通知弹窗的关闭按钮（会遮挡表格操作列）
_NOTIF_CLOSE = (By.CSS_SELECTOR, ".el-notification .el-notification__closeBtn")
_NOTIF = (By.CSS_SELECTOR, ".el-notification")


class GroupPage:
    """用户分组页面对象：增/删/改/查操作的封装。"""

    MENU_USER = (By.CSS_SELECTOR, 'li.layout-columns[title="用户"]')
    MENU_GROUP = (By.XPATH, '//span[text()="用户分组"]')

    BTN_ADD = (By.XPATH, '//button[.//span[text()="添加分组"] or text()="添加分组"]')
    # 注意：添加/修改分组弹窗是 el-message-box（form-create 表单），不是 el-dialog！
    # 「确定」按钮用输入框向上锚定到本弹窗，避免误中页面其他 message-box
    INPUT_NAME = (By.CSS_SELECTOR, 'input[placeholder="请输入分组名称"]')
    BTN_DIALOG_CONFIRM = (
        By.XPATH,
        '//input[@placeholder="请输入分组名称"]'
        '/ancestor::div[contains(@class,"el-message-box")]'
        '//button[.//span[normalize-space(text())="确定"] or normalize-space(text())="确定"]',
    )
    # 删除确认框：以正文文案锚定（标题「提示」太通用）；正文非固定标签
    DELETE_BOX = (
        By.XPATH,
        '//div[contains(@class,"el-message-box")]'
        '[.//*[contains(normalize-space(.),"确定要删除分组吗")]]',
    )
    FORM_ERROR = (By.CSS_SELECTOR, ".el-form-item__error")

    BTN_PAGER_LAST = (
        By.CSS_SELECTOR,
        ".el-pagination .el-pager li.number:last-child",
    )
    PAGER_TOTAL = (By.CSS_SELECTOR, ".el-pagination__total")

    def __init__(self, driver, timeout: int = 15):
        self.driver = driver
        self.timeout = timeout

    # ---- 导航 -------------------------------------------------------------
    GROUP_URL_PART = "/admin/user/group"

    @allure.step("导航到 用户 -> 用户分组 页面")
    def open(self):
        wait = WebDriverWait(self.driver, self.timeout)
        # 菜单点击走 JS 兜底：即便有遗留弹窗遮罩也能触发路由切换
        self._click(
            wait.until(EC.element_to_be_clickable(self.MENU_USER))
        )
        self._click(
            wait.until(EC.element_to_be_clickable(self.MENU_GROUP))
        )
        # 关键：等路由切到分组页本身。若只等表格行，会被上一个页面
        # （用户管理等）尚未移走的同款表格满足，导致后续操作全部落空
        wait.until(EC.url_contains(self.GROUP_URL_PART))
        # 「添加分组」按钮是分组页特有元素，出现才算页面就绪
        wait.until(EC.presence_of_element_located(self.BTN_ADD))
        wait.until(EC.presence_of_element_located(_ROW_BODY))
        self.close_notifications()
        return self

    @allure.step("持续关闭右上角陆续弹出的「温馨提示」通知")
    def close_notifications(self, quiet: float = 3.0, max_wait: float = 12.0):
        """通知弹窗是间隔数秒陆续出现的，不能只关一波。

        循环检测并 JS 点击关闭按钮：每发现新弹窗就刷新计时，
        连续 quiet 秒没有新弹窗（或总时长到 max_wait）才返回。
        """
        start = time.monotonic()
        last_seen = time.monotonic()
        while (
            time.monotonic() - start < max_wait
            and time.monotonic() - last_seen < quiet
        ):
            btns = self.driver.find_elements(*_NOTIF_CLOSE)
            if btns:
                last_seen = time.monotonic()
                for btn in btns:
                    try:
                        self.driver.execute_script("arguments[0].click();", btn)
                    except Exception:  # noqa: BLE001 - 单个关不掉不影响后续
                        pass
            time.sleep(0.4)
        return self

    def _click(self, element):
        """点击：被遮挡时（通知弹窗等）退避为 JS 强点。"""
        try:
            element.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", element)

    # ---- 查 ----------------------------------------------------------------
    def row_count(self) -> int:
        return len(self.driver.find_elements(*_ROW_BODY))

    def row_names(self) -> list:
        """当前页主表所有分组名（第 2 列）。"""
        names = []
        for row in self.driver.find_elements(*_ROW_BODY):
            cells = row.find_elements(By.CSS_SELECTOR, "td .cell span")
            if len(cells) >= 2:
                names.append(cells[1].text.strip())
        return names

    @allure.step("跳到最后一页（列表按 id 升序，新建分组在末尾）")
    def goto_last_page(self):
        wait = WebDriverWait(self.driver, self.timeout)
        last_li = wait.until(
            EC.presence_of_element_located(self.BTN_PAGER_LAST)
        )
        target = last_li.text.strip()
        assert target.isdigit(), f"末页页码异常: {last_li.text!r}"

        def on_last_page(_driver):
            actives = _driver.find_elements(
                By.CSS_SELECTOR, ".el-pager li.number.active"
            )
            return bool(actives) and actives[0].text.strip() == target

        if not on_last_page(self.driver):
            self._click(last_li)
            try:
                wait.until(on_last_page)
            except TimeoutException:
                # 兜底：页码点击无效时，用「前往 N 页」输入框直接跳页
                jump = wait.until(
                    EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, ".el-pagination__jump .el-input__inner")
                    )
                )
                jump.clear()
                jump.send_keys(str(target))
                jump.send_keys(Keys.ENTER)
                wait.until(on_last_page)
        # 翻页生效后等表格 loading 结束（数据已是末页内容）
        wait.until(
            EC.invisibility_of_element_located(
                (By.CSS_SELECTOR, ".el-table__body-wrapper .el-loading-mask")
            )
        )
        wait.until(EC.presence_of_element_located(_ROW_BODY))
        return self

    def find_row_index_by_name(self, name: str) -> "int | None":
        """在当前页按分组名找行号（主表索引）；找不到返回 None。"""
        for idx, row_name in enumerate(self.row_names()):
            if row_name == name:
                return idx
        return None

    # ---- 增 ----------------------------------------------------------------
    @allure.step("点击「添加分组」打开弹窗")
    def open_add_dialog(self):
        WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(self.BTN_ADD)
        ).click()
        WebDriverWait(self.driver, self.timeout).until(
            EC.visibility_of_element_located(self.INPUT_NAME)
        )
        return self

    @allure.step("弹窗中填入分组名称: {name}")
    def fill_group_name(self, name: str):
        inp = WebDriverWait(self.driver, self.timeout).until(
            EC.visibility_of_element_located(self.INPUT_NAME)
        )
        inp.clear()
        inp.send_keys(name)
        return self

    @allure.step("点击弹窗「确定」提交")
    def confirm_dialog(self):
        WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(self.BTN_DIALOG_CONFIRM)
        ).click()
        # 等弹窗关闭（隐藏）才算提交完成
        WebDriverWait(self.driver, self.timeout).until(
            EC.invisibility_of_element_located(self.INPUT_NAME)
        )
        return self

    def submit_dialog_expect_stay(self):
        """提交但预期被前端校验拦截：弹窗仍在（用于空名称异常用例）。"""
        WebDriverWait(self.driver, self.timeout).until(
            EC.element_to_be_clickable(self.BTN_DIALOG_CONFIRM)
        ).click()
        WebDriverWait(self.driver, self.timeout).until(
            EC.visibility_of_element_located(self.FORM_ERROR)
        )
        return self

    def form_error_text(self) -> str:
        return self.driver.find_element(*self.FORM_ERROR).text.strip()

    # ---- 改 / 删（固定操作列，与主表行索引对齐）----------------------------
    def _op_link(self, row_index: int, text: str):
        """取固定操作列第 row_index 行的 修改/删除 链接。

        操作列文本不是固定标签（非 span），故用标签无关的精确文本匹配。
        """
        rows = self.driver.find_elements(*_ROW_FIXED)
        assert row_index < len(rows), (
            f"固定操作列只有 {len(rows)} 行，找不到第 {row_index} 行"
        )
        return rows[row_index].find_element(
            By.XPATH, f'.//*[normalize-space(text())="{text}"]'
        )

    @allure.step("点击第 {row_index} 行的「修改」")
    def open_edit_dialog(self, row_index: int):
        self._click(self._op_link(row_index, "修改"))
        WebDriverWait(self.driver, self.timeout).until(
            EC.visibility_of_element_located(self.INPUT_NAME)
        )
        return self

    @allure.step("点击第 {row_index} 行的「删除」")
    def click_delete(self, row_index: int):
        self._click(self._op_link(row_index, "删除"))
        WebDriverWait(self.driver, self.timeout).until(
            EC.visibility_of_element_located(self.DELETE_BOX)
        )
        return self

    @allure.step("确认删除（提示框点「确定」）")
    def confirm_delete(self):
        box = self.driver.find_element(*self.DELETE_BOX)
        box.find_element(
            By.XPATH,
            './/button[.//span[normalize-space(text())="确定"]'
            ' or normalize-space(text())="确定"]',
        ).click()
        # 提示框消失即提交完成
        WebDriverWait(self.driver, self.timeout).until(
            EC.invisibility_of_element_located(self.DELETE_BOX)
        )
        return self

    # ---- 通用 ---------------------------------------------------------------
    @allure.step("等待分组行消失: {name}")
    def wait_name_disappear(self, name: str):
        """等待分组名 name 从当前页表格消失（删除生效）。"""

        def gone(_driver):
            return name not in self.row_names()

        WebDriverWait(self.driver, self.timeout).until(gone)

    def screenshot(self, name: str):
        """关键步骤截图进 Allure 报告。"""
        try:
            allure.attach(
                self.driver.get_screenshot_as_png(),
                name=name,
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:  # noqa: BLE001 - 截图失败不影响用例
            pass

    @allure.step("清理用例遗留的 message-box 弹窗")
    def dismiss_any_message_box(self):
        """关闭可能遗留的「添加/修改/删除确认」弹窗，避免污染下个用例。

        用例失败或空名校验拦截时弹窗会留在页面上，遮罩会挡住下一个
        用例的菜单点击。优先点「取消」；点不掉用 ESC（element-ui
        message-box 默认支持 ESC 关闭）。不强删 DOM——强删会让 Vue
        组件树与真实 DOM 失配，后续弹窗渲染不出来。
        """
        for _ in range(3):
            wrappers = [
                w
                for w in self.driver.find_elements(
                    By.CSS_SELECTOR, ".el-message-box__wrapper"
                )
                if w.is_displayed()
            ]
            if not wrappers:
                break
            try:
                cancel = wrappers[0].find_element(
                    By.XPATH,
                    './/button[.//span[normalize-space(text())="取消"]'
                    " or normalize-space(text())=\"取消\"]",
                )
                self.driver.execute_script("arguments[0].click();", cancel)
            except Exception:  # noqa: BLE001 - 点不掉走 ESC
                pass
            time.sleep(0.5)
            if not any(
                w.is_displayed()
                for w in self.driver.find_elements(
                    By.CSS_SELECTOR, ".el-message-box__wrapper"
                )
            ):
                break
            self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            time.sleep(0.5)
        return self
