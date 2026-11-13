@echo off
chcp 65001 >nul
title CRMEB 用户分组自动化测试
cd /d "%~dp0"

echo ============================================================
echo   CRMEB 用户分组 增删改查 自动化测试（API + UI）
echo ============================================================

rem ---- 1) 环境自检：无虚拟环境则自动创建并安装依赖 ----
if not exist ".venv\Scripts\python.exe" (
    echo [run] 首次运行：正在创建虚拟环境并安装依赖，请耐心等待...
    python setup_env.py
)

rem ---- 2) 跑测试（conftest 会在结束时自动生成三份报告） ----
echo [run] 开始执行测试...
".venv\Scripts\python.exe" -m pytest %*

rem ---- 3) 打开可发送报告（双击即看的那份） ----
if exist "allure-report-single\index_sendable.html" (
    echo [run] 正在打开可发送报告...
    start "" "allure-report-single\index_sendable.html"
)

echo.
echo ============================================================
echo   测试执行完毕。报告位置：
echo     1. 可发送单文件报告: allure-report-single\index_sendable.html
echo        （把这个文件发给别人，对方双击即可查看）
echo     2. 本机完整报告目录: allure-report\
echo ============================================================
pause
