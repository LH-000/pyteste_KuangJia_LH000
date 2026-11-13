# -*- coding: utf-8 -*-
"""
=============================================================================
 通用模板 conftest.py（可复用到任意 pytest 项目）
 ----------------------------------------------------------------------------
 使用方式：拷贝本文件到目标 pytest 项目根目录（与 pytest.ini 同级），
          按下方【适配点】核对修改后即可生效。
 ----------------------------------------------------------------------------
 使用前提：
   1. 目标项目已安装 allure-pytest（pip install allure-pytest）
   2. 目标项目已安装 allure 命令行工具，且满足以下任一条件：
      a) allure 已加入系统 PATH；或
      b) 虚拟环境 Scripts 目录内存在 allure.bat / allure.cmd / allure.exe
         （如通过 `pip install allure-pytest` 的附加入口，或手动放置）
      均未满足时，报告生成会自动跳过并打印提示，不影响用例执行。
   3. pytest.ini（或 pyproject.toml）的 addopts 已配置
      --alluredir=allure-results --clean-alluredir（见随附 pytest.ini 模板）。
 ----------------------------------------------------------------------------
 适配点（按需修改）：
   1. 无需配置虚拟环境目录名：本模板基于"当前 Python 解释器"自动定位
      虚拟环境 Scripts 目录（sys.executable 所在目录），不依赖固定目录名
      .venv / venv / env，直接拷贝即可用。
   2. PROJECT_ROOT 自动取本文件所在目录，无需修改；
      请勿把 conftest.py 拷贝进子目录，否则报告输出位置会随之变化。
   3. 默认不自动打开报告；如需自动打开，可在生成成功后
      追加 os.startfile(PROJECT_ROOT / "allure-report" / "index.html")。
 =============================================================================
"""

import importlib.util
import os
import shutil
import subprocess
import sys
import time
from os import name
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

# =============================================================================
# 业务适配区（可选）：挂载项目专用 fixture / 配置
# 说明：通用模板只负责 driver 与 Allure 报告；项目私有的业务 fixture
#       （如 login）应放在项目内 fixtures 包（fixtures/__init__.py），
#       此处自动导入并注册到本 conftest 作用域，测试用例即可直接以参数名
#       注入（如 def test_xxx(self, driver, login)）。
#       拷贝模板到无业务 fixture 的项目时，此区域自动跳过，不影响其余能力。
# =============================================================================
try:
    # 业务 fixture，供用例参数注入（api / admin_logged_in / group_page / login）
    from fixtures import (  # noqa: F401
        admin_logged_in,
        api,
        group_page,
        login,
    )
except ImportError:
    login = None


# 项目根目录（conftest.py 所在目录），保证 allure 命令始终在项目根目录执行
PROJECT_ROOT = Path(__file__).resolve().parent

# =============================================================================
# 启动时依赖快速检测（仅打印提示，不拦截用例）
# 说明：pytest_configure 在用例收集前执行，逐个检查关键运行依赖是否可导入；
#       缺失时仅打印中文提示，不抛出异常、不影响任何用例执行。
# =============================================================================
# (pip 安装名, import 导入名) 元组列表；注意 pytest-xdist 的导入名是 xdist
_REQUIRED_RUNTIME_PACKAGES = (
    ("pytest", "pytest"),
    ("allure-pytest", "allure_pytest"),
    ("selenium", "selenium"),
    ("requests", "requests"),
    ("webdriver-manager", "webdriver_manager"),
    ("pytest-result-log", "pytest_result_log"),
    ("pytest-rerunfailures", "pytest_rerunfailures"),
    ("pytest-xdist", "xdist"),
)


def pytest_addoption(parser):
    """注册模板自定义 ini 配置项：browser / browser_driver。

    供 driver fixture 读取本地 Chrome 与 chromedriver 绝对路径；
    注册后可消除 pytest 对未知 ini 键的 Unknown config option 警告。
    拷贝模板时无需修改本函数，只需在 pytest.ini 中按机器填写路径。
    """
    parser.addini("browser", "Chrome 浏览器可执行文件绝对路径", type="string", default="")
    parser.addini("browser_driver", "chromedriver 可执行文件绝对路径", type="string", default="")


def pytest_configure(config):
    """pytest 启动钩子：快速检测关键运行依赖，缺失仅打印提示。

    使用 importlib.util.find_spec 检测 import 名（不实际导入包），
    汇总所有缺失依赖的 pip 名；若存在缺失则打印中文提示，建议先运行
    python setup_env.py 自动安装。本钩子不抛出异常，不拦截用例执行。
    """
    missing = [
        pip_name
        for pip_name, import_name in _REQUIRED_RUNTIME_PACKAGES
        if importlib.util.find_spec(import_name) is None
    ]
    if missing:
        print(
            "[环境提示] 以下依赖缺失：" + "、".join(missing)
            + "，请先运行 python setup_env.py 自动安装后再跑测试"
        )


# 常见虚拟环境目录名候选（用于按目录名兜底探测，顺序可自行调整）
VENV_DIR_CANDIDATES = (".venv", "venv", "env", ".env")


def _find_allure():
    """查找可用的 allure 可执行文件，返回其路径；均未找到时返回 None。

    查找顺序（不再依赖固定目录名，基于当前解释器自我定位）：
    1) PATH 环境变量中的 allure（shutil.which）
    2) 当前 Python 解释器所在目录（sys.executable 的父目录，即正在使用的
       虚拟环境 Scripts 目录）下的 allure.bat / allure.cmd / allure.exe
    3) 按候选目录名列表 VENV_DIR_CANDIDATES 依次探测项目根目录下
       对应虚拟环境目录的 Scripts（兜底，兼容 .venv / venv / env / .env）
    """
    # 1) 优先使用 PATH 中的 allure
    found = shutil.which("allure")
    if found:
        return found

    # 2) 当前解释器所在目录（虚拟环境 Scripts），最可靠的一层
    current_scripts = Path(sys.executable).parent
    for name in ("allure.bat", "allure.cmd", "allure.exe"):
        candidate = current_scripts / name
        if candidate.is_file():
            return str(candidate)

    # 3) 按候选目录名兜底探测项目根目录下的常见虚拟环境
    for venv_name in VENV_DIR_CANDIDATES:
        scripts_dir = PROJECT_ROOT / venv_name / "Scripts"
        for name in ("allure.bat", "allure.cmd", "allure.exe"):
            candidate = scripts_dir / name
            if candidate.is_file():
                return str(candidate)

    # 4) 最终未找到
    return None


def _resolve_java_home():
    """从 PATH 中解析真实 JDK 根目录（含 bin/java.exe 的目录的上级）。

    用于绕过 PyCharm 运行配置中误填的 A_HOME/JAVA_HOME 等环境变量污染，
    确保 allure.bat 能定位到可用的 java.exe。找不到时返回 None。
    """
    java = shutil.which("java")
    if not java:
        return None
    java = Path(java).resolve()
    # 期望 .../bin/java.exe，取上级的上级作为 JAVA_HOME
    if java.name.lower() == "java.exe" and java.parent.name.lower() == "bin":
        return str(java.parent.parent)
    return None


def _wait_for_allure_results(expected, timeout=60.0, poll_interval=0.5):
    """等待 allure-results 目录中 result.json 数量达到预期用例数。

    轮询 allure-results 目录下 *-result.json 文件数量，直到达到 expected
    （即 len(session.items)，每个收集用例对应一个 result.json）。
    说明：allure-pytest 的 result.json 为异步延迟落盘，需按预期数量等待写齐，
    实测最后一个用例的 result.json 约延迟 5 秒才写盘，60 秒超时足以覆盖。
    间隔 poll_interval 秒（默认 0.5）轮询一次；达到数量后返回 (True, count)，
    超过 timeout 秒（默认 60）仍未写齐时返回 (False, count)，由调用方决定
    继续执行并提示。
    """
    results_dir = PROJECT_ROOT / "allure-results"
    started = time.monotonic()

    while True:
        count = 0
        if results_dir.is_dir():
            count = len(list(results_dir.glob("*-result.json")))

        if count >= expected:
            return True, count

        if time.monotonic() - started >= timeout:
            return False, count

        time.sleep(poll_interval)


def pytest_sessionfinish(session, exitstatus):
    """pytest 会话结束钩子：全部用例执行完毕后自动生成 Allure HTML 报告。

    生成前按预期用例数 expected = len(session.items) 轮询等待
    allure-results/*-result.json 数量达到该值（间隔 0.5 秒、总超时 60 秒），
    达到后再额外等待 1 秒 flush，之后才执行 allure generate，避免漏扫用例；
    超时则打印警告并继续生成。整个钩子不抛出未捕获异常（异常仅打印提示），
    不影响 pytest 正常退出码。
    """
    try:
        # --collect-only 模式不执行用例，无需生成报告
        if session.config.option.collectonly:
            return

        allure_cmd = _find_allure()
        if allure_cmd is None:
            print("\n[conftest] 提示: 未检测到 allure 命令，跳过 HTML 报告生成。")
            return

        expected = len(session.items)
        print(f"\n[conftest] 会话结束，预期 {expected} 个用例结果，等待 result.json 写齐 ...")
        ok, result_count = _wait_for_allure_results(expected)
        if not ok:
            print(
                f"\n[conftest] 警告: 等待 60 秒后 allure-results 仅 {result_count} 个 result.json"
                f"（预期 {expected} 个），继续生成报告，可能漏统计用例。"
            )
        else:
            # 数量达标后再额外等待 1 秒，确保最后一批文件完全 flush 到磁盘
            time.sleep(1.0)

        print("\n[conftest] 正在生成 Allure HTML 报告 ...")
        # Windows 下 .bat/.cmd 无法被 CreateProcess 直接启动，需经 shell 执行
        use_shell = allure_cmd.lower().endswith((".bat", ".cmd"))
        # 显式注入真实 JAVA_HOME，规避 PyCharm 运行配置环境变量污染
        run_env = os.environ.copy()
        java_home = _resolve_java_home()
        if java_home:
            run_env["JAVA_HOME"] = java_home

        def _allure_generate(out_dir: str, single_file: bool):
            """执行一次 allure generate（目录版或单文件版）。"""
            cmd = [allure_cmd, "generate", "allure-results", "-o", out_dir,
                   "--clean", "--lang", "zh"]
            if single_file:
                cmd.append("--single-file")
            cmd += ["--name", "CRMEB 用户分组 CRUD 测试报告"]
            subprocess.run(cmd, cwd=str(PROJECT_ROOT), shell=use_shell,
                           check=False, env=run_env)

        # 1) 目录版报告（本机 allure open 查看）
        _allure_generate("allure-report", single_file=False)
        print(
            "[conftest] 报告已生成（项目根目录 allure-report 文件夹），"
            "可执行 `allure open allure-report` 或直接打开 allure-report/index.html 查看。"
        )
        # 2) 单文件版 + 可发送版（双击即看、可发给别人）
        _allure_generate("allure-report-single", single_file=True)
        try:
            from make_report_sendable import make_sendable

            out = make_sendable(PROJECT_ROOT / "allure-report-single")
            print(
                f"[conftest] ✅ 可发送报告: {out}\n"
                "     把这一个 html 文件发给对方，双击即可查看（无需本地服务）。"
            )
        except Exception as exc:  # noqa: BLE001 - 发送版失败不影响主流程
            print(f"[conftest] 提示: 生成可发送报告失败（不影响其余产物）: {exc}")
    except Exception as exc:  # noqa: BLE001 - 钩子内不允许抛出未捕获异常
        print(f"\n[conftest] 错误: 生成 Allure 报告失败，已跳过（不影响用例结果）。原因: {exc}")


@pytest.fixture(scope="session")
def driver(request):
    """配置 Chrome 浏览器，并指定 Chrome 浏览器路径与 chromedriver 路径。

    浏览器与驱动路径从 pytest.ini 的 browser / browser_driver 配置项读取，
    模板本身不含任何项目私货路径，拷贝到任意项目仅需修改 pytest.ini。
    """
    browser = request.config.getini("browser")
    browser_driver = request.config.getini("browser_driver")
    if not browser or not browser_driver:
        raise pytest.UsageError(
            "[conftest] 未配置 browser / browser_driver："
            "请在 pytest.ini 的 [pytest] 段填写 Chrome 浏览器与 chromedriver 的绝对路径"
        )
    options = Options()
    options.binary_location = browser
    # 窗口过小时后台侧边栏会折叠成图标，菜单定位不到，启动即最大化
    options.add_argument("--start-maximized")
    d = webdriver.Chrome(
        service=Service(browser_driver),
        options=options,
    )
    d.maximize_window()
    yield d
    d.quit()


# =============================================================================
# UI 用例失败自动截图：失败瞬间把浏览器现场贴进 Allure 报告
# =============================================================================
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        _driver = item.funcargs.get("driver")
        if _driver is None:
            return
        try:
            import allure

            allure.attach(
                _driver.get_screenshot_as_png(),
                name="失败现场截图",
                attachment_type=allure.attachment_type.PNG,
            )
        except Exception:  # noqa: BLE001 - 截图失败不影响用例结果上报
            pass

