# -*- coding: utf-8 -*-
"""
=============================================================================
 通用模板 setup_env.py（可复用到任意 pytest 项目）
 ----------------------------------------------------------------------------
 使用方式：拷贝本文件到目标 pytest 项目根目录即可用，无需改虚拟环境目录名。
          虚拟环境定位基于"当前 Python 解释器"自动完成（sys.executable）。
 ----------------------------------------------------------------------------
 用途：检查项目跑自动化测试需要的关键依赖是否齐全，缺什么自动装什么，
      并检查 Allure 报告命令是否可用，最后给你一份"体检报告"汇总。
 ----------------------------------------------------------------------------
 用法（在项目根目录下任选一种）：
   python setup_env.py                 # 用系统 Python 检查/安装
   .venv\\Scripts\\python setup_env.py # 用项目虚拟环境 Python 检查/安装（推荐）
   附加参数：
   --check-only                        # 只检测不安装，先看体检结果
 ----------------------------------------------------------------------------
 说明：
   - 用"检测 -> 缺了就装 -> 汇总"三步走，全程中文提示，无需编程基础。
   - Python 依赖缺失时，会自动调用当前 Python 执行 `pip install 包名` 安装。
   - Allure 命令行工具无法用 pip 直接安装（见下文提示），脚本只负责检测
     并给出解决方法，不会擅自下载。
=============================================================================
"""

import importlib.util
import re
import shutil
import subprocess
import sys
from pathlib import Path

# ============================= 依赖清单 ==================================
# 依赖包清单统一由项目根目录 requirements.txt 管理（每行一个 pip 包名，
# 支持空行与 # 注释，也兼容带版本号写法）。
# 本脚本启动时自动读取该文件，想增删依赖只需编辑 requirements.txt，
# 本文件无需再改动。

# ============================= 一般不用改 ==================================
# 项目根目录：脚本所在目录，后续查找 allure 入口都在这里找
PROJECT_ROOT = Path(__file__).resolve().parent

# 依赖清单文件：项目根目录的 requirements.txt（唯一依赖清单）
_REQUIREMENTS_FILE = PROJECT_ROOT / "requirements.txt"

# pip 安装名 -> Python 导入名 别名表（pip 名与 import 名不一致的包）。
# 不在表里的包按通用规则处理：pip 名中的连字符换成下划线即为导入名。
_IMPORT_ALIAS = {
    "allure-pytest": "allure_pytest",
    "webdriver-manager": "webdriver_manager",
    "pytest-result-log": "pytest_result_log",
    "pytest-rerunfailures": "pytest_rerunfailures",
    "pytest-xdist": "xdist",
    "pytest-selenium": "pytest_selenium",
}


def load_required_packages():
    """从项目根目录 requirements.txt 读取唯一依赖清单。

    逐行解析：跳过空行与 # 注释行；用正则剥离 == / >= / <= / < / > / ! 等
    版本符号只取纯包名；导入名 = _IMPORT_ALIAS.get(pip名, pip名.replace('-', '_'))。
    返回 [(pip 名, 导入名), ...] 列表；requirements.txt 不存在时给出清晰
    中文提示并退出（退出码 1）。
    """
    if not _REQUIREMENTS_FILE.is_file():
        print(
            f"[setup_env] ❌ 未找到依赖清单文件：{_REQUIREMENTS_FILE}\n"
            "     请先在项目根目录创建 requirements.txt（每行一个 pip 包名），"
            "再重新运行本脚本。"
        )
        sys.exit(1)

    packages = []
    for raw in _REQUIREMENTS_FILE.read_text(encoding="utf-8").splitlines():
        # 先剥离环境标记（";" 之后的部分，如 "foo>=1 ; python_version<'3.10'"）
        line = raw.split(";", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        # 只取版本符号前的纯包名，并剥离 [extras] 附加项，
        # 如 "requests[socks]==2.34.2" -> "requests"
        pip_name = re.split(r"[<>=!\[]", line, maxsplit=1)[0].strip()
        if not pip_name:
            continue
        import_name = _IMPORT_ALIAS.get(pip_name, pip_name.replace("-", "_"))
        packages.append((pip_name, import_name))
    return packages


# 常见虚拟环境目录名候选（用于按目录名兜底探测，顺序可自行调整）
VENV_DIR_CANDIDATES = (".venv", "venv", "env", ".env")


def check_package(import_name):
    """检测单个 Python 包是否已安装。已安装返回 True，未安装返回 False。

    参数 import_name 是包的"导入名"（import 时用的名字，如 allure_pytest、
    webdriver_manager），不是 pip 安装名（带连字符的名字 find_spec 查不到）。
    """
    # importlib.util.find_spec 是 Python 官方"查包是否装好"的标准方法
    return importlib.util.find_spec(import_name) is not None


def install_package(pkg_name):
    """用当前 Python 自动安装缺失的包，安装成功返回 True，失败返回 False。

    使用 sys.executable（正在运行的 Python 解释器）而不是写死 python，
    这样无论用系统 Python 还是虚拟环境 Python 运行本脚本，都装进同一个环境。
    """
    print(f"    正在安装 {pkg_name}（可能需要一两分钟，请耐心等待）...")
    try:
        # capture_output=True 把安装过程输出收起来，避免刷屏；
        # text=True 让输出以文本形式返回，方便下面打印
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", pkg_name],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"    ✅ {pkg_name} 安装成功！")
            return True
        else:
            # 安装失败时打印 pip 的最后几行报错，方便排查
            tail = (result.stderr or result.stdout or "").strip().splitlines()[-5:]
            print(f"    ❌ {pkg_name} 安装失败，报错如下（最后几行）：")
            for line in tail:
                print(f"      {line}")
            return False
    except Exception as exc:  # noqa: BLE001 - 任何异常都转成提示，不中断脚本
        print(f"    ❌ {pkg_name} 安装过程出错：{exc}")
        return False


def check_allure_command():
    """检查 Allure 命令行工具是否可用。

    查找顺序（和 conftest.py 的 _find_allure 保持一致，不依赖固定目录名）：
      1) 系统 PATH 里的 allure（shutil.which 自动找）
      2) 当前 Python 解释器所在目录（sys.executable 的父目录，即正在使用的
         虚拟环境 Scripts 目录）下的 allure.bat / allure.cmd / allure.exe
      3) 按候选目录名列表 VENV_DIR_CANDIDATES 依次探测项目根目录下
         对应虚拟环境目录的 Scripts（兜底）
    找到返回入口路径，都没找到返回 None。
    """
    # 1) 先看 PATH 里有没有
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

    return None


def main():
    # 支持 python setup_env.py --check-only：只检测不安装，方便先看体检结果
    check_only = "--check-only" in sys.argv[1:]

    # 画个开场横线，方便在控制台里找到输出起点
    print("=" * 60)
    if check_only:
        print("环境预检开始（setup_env.py --check-only，只检测不安装）")
    else:
        print("环境自检开始（setup_env.py）")
    print("=" * 60)

    # ---------- 第 1 步：检查 Python 依赖包 ----------
    print("\n【第 1 步】检查 Python 依赖包 ...")
    already = []   # 已安装的包
    newly = []     # 本次新装的包
    missing = []   # 想装但没装成功的包

    packages = load_required_packages()

    for pip_name, import_name in packages:
        # 检测用"导入名"（find_spec 认这个），展示/安装用"pip 安装名"
        if check_package(import_name):
            print(f"  ✅ {pip_name} 已安装")
            already.append(pip_name)
        elif check_only:
            print(f"  ⚠️  {pip_name} 未安装（预检模式，跳过安装）")
            missing.append(pip_name)
        else:
            print(f"  ⚠️  {pip_name} 未安装，开始自动安装 ...")
            if install_package(pip_name):
                newly.append(pip_name)
            else:
                missing.append(pip_name)

    # ---------- 第 2 步：检查 Allure 命令行工具 ----------
    print("\n【第 2 步】检查 Allure 命令行工具 ...")
    allure_cmd = check_allure_command()
    if allure_cmd:
        print(f"  ✅ 找到 allure 命令：{allure_cmd}")
    else:
        print("  ⚠️  未找到 allure 命令。")
        print("     注意：allure-commandline 已从 PyPI（pip 仓库）下架，")
        print("     pip install allure-commandline 会失败，请按下面任一方式解决：")
        print("     方式一（推荐）：GitHub 官方发布页下载")
        print("            https://github.com/allure-framework/allure2/releases")
        print("            可直接下载 zip 示例（以最新版 2.30.0 为例）：")
        print("            https://github.com/allure-framework/allure2/releases/download/2.30.0/allure-2.30.0.zip")
        print("     方式二：去 Maven Central 下载 allure zip 压缩包")
        print("            （搜索 allure-commandline，选最新版下载 zip），")
        print("             解压后把 bin 目录加入系统 PATH；")
        print("     方式三：把解压出来的 allure.bat 直接复制到当前 Python 所在")
        print("             的 Scripts 目录（即虚拟环境 Scripts，如 .venv\\Scripts），")
        print("             本脚本会自动找到它。")
        print("     部署指引：下载 zip → 解压到非中文路径 → 将解压目录下 bin 加入")
        print("     PATH → 重新打开终端运行 allure --version 验证。")

    # ---------- 第 3 步：打印汇总 ----------
    print("\n" + "=" * 60)
    print("环境自检汇总")
    print("=" * 60)
    print(f"  ✅ 已安装：{len(already)} 个  ->  {'、'.join(already) if already else '无'}")
    print(f"  🆕 新安装：{len(newly)} 个  ->  {'、'.join(newly) if newly else '无'}")
    print(f"  ❌ 缺失未解决：{len(missing)} 个  ->  {'、'.join(missing) if missing else '无'}")
    if allure_cmd:
        print("  ✅ Allure 命令：可用")
    else:
        print("  ⚠️  Allure 命令：缺失，请按上方提示手动解决（无法自动安装）")

    if missing:
        if check_only:
            print("\n提示：以上 ⚠️ 包缺失。运行 `.venv\\Scripts\\python setup_env.py`（去掉 --check-only）即可自动安装。")
        else:
            print("\n提示：仍有依赖未装成功，请把上面 ❌ 的报错信息发给我，我帮你排查。")
    else:
        print("\n一切就绪，可以开始跑测试啦！运行 `pytest` 即可，报告会自动生成。")
    print("=" * 60)


def _venv_python_works(python_path):
    """探测虚拟环境解释器是否仍能正常启动（返回 True / False）。

    Windows 下 .venv 里的 python.exe 只是"跳板"，依赖 pyvenv.cfg 指向的
    基础解释器；基础 Python 升级/迁移后跳板会失效，报晦涩的英文错误
    "did not find executable at ..."。这里实际启动一次以提前发现该问题。
    """
    try:
        result = subprocess.run(
            [str(python_path), "-c", "import sys"],
            capture_output=True,
            text=True,
        )
        return result.returncode == 0
    except OSError:
        return False


def _ensure_venv_and_rerun():
    """引导段：确保本脚本在项目虚拟环境中运行（自动创建 + 自举重跑）。

    流程：
      1) 按候选目录名（.venv / venv / env / .env）探测项目根目录下是否已有
         可用虚拟环境，判定标准为对应目录存在 Scripts\\python.exe；
      2) 均不存在时，用当前解释器（sys.executable）执行
         `python -m venv .venv` 自动创建；创建失败打印中文提示并退出；
      3) 若当前运行本脚本的解释器不是该虚拟环境的 python.exe，则用虚拟
         环境的 python.exe 重新运行本脚本并透传原有命令行参数
         （如 --check-only），运行完成后以同样的退出码退出；
         若已经是虚拟环境解释器，则直接返回，继续执行下方业务逻辑。
    不硬编码项目特定路径，拷到任意项目均可零适配使用。
    """
    # 1) 探测已有虚拟环境
    venv_python = None
    venv_name = None
    for name in VENV_DIR_CANDIDATES:
        candidate_py = PROJECT_ROOT / name / "Scripts" / "python.exe"
        if candidate_py.is_file():
            venv_python = candidate_py
            venv_name = name
            break

    # 1.5) 探测到的虚拟环境可能已失效（目录在、跳板坏）：基础 Python 升级
    #      或迁移后 pyvenv.cfg 仍指向旧路径，直接重跑只会得到晦涩英文报错，
    #      这里提前拦截并给出中文修复指引
    if venv_python is not None and not _venv_python_works(venv_python):
        print(f"[setup_env] ❌ 虚拟环境 {venv_name} 已失效（其基础 Python 解释器可能已升级或被卸载）。")
        print("     修复方式任选其一：")
        print(f"       方式一（简单）：删除整个 {PROJECT_ROOT / venv_name} 目录，"
              "重新运行本脚本自动重建并安装依赖；")
        print(f"       方式二（保留已装包）：编辑 {PROJECT_ROOT / venv_name / 'pyvenv.cfg'}，")
        print("            把 home / executable 两行改为新版 Python 的实际安装路径。")
        sys.exit(1)

    # 2) 均不存在 -> 自动创建 .venv
    if venv_python is None:
        print("[setup_env] 未检测到虚拟环境，正在创建 .venv ...", flush=True)
        try:
            result = subprocess.run(
                [sys.executable, "-m", "venv", str(PROJECT_ROOT / ".venv")],
                capture_output=True,
                text=True,
            )
        except Exception as exc:  # noqa: BLE001 - 任何异常都转成中文提示
            print(f"[setup_env] ❌ 虚拟环境创建失败：{exc}")
            sys.exit(1)
        if result.returncode != 0:
            tail = (result.stderr or result.stdout or "").strip().splitlines()[-5:]
            print("[setup_env] ❌ 虚拟环境创建失败，报错如下（最后几行）：")
            for line in tail:
                print(f"    {line}")
            sys.exit(1)
        venv_python = PROJECT_ROOT / ".venv" / "Scripts" / "python.exe"
        venv_name = ".venv"
        print("[setup_env] ✅ 虚拟环境创建成功：.venv", flush=True)

    # 3) 当前解释器不是虚拟环境解释器 -> 用虚拟环境 python 重跑本脚本
    if Path(sys.executable).resolve() != Path(venv_python).resolve():
        print(f"[setup_env] 切换到虚拟环境 {venv_name} 的解释器重新运行 ...", flush=True)
        try:
            result = subprocess.run(
                [str(venv_python), str(Path(__file__).resolve())] + sys.argv[1:],
                cwd=str(PROJECT_ROOT),
            )
        except Exception as exc:  # noqa: BLE001
            print(f"[setup_env] ❌ 使用虚拟环境解释器运行失败：{exc}")
            sys.exit(1)
        # 以子进程同样的退出码退出（0 成功、1 失败）
        sys.exit(result.returncode)


if __name__ == "__main__":
    _ensure_venv_and_rerun()
    main()
