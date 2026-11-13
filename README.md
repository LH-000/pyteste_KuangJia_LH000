# CRMEB 用户分组自动化测试框架

一套 **pytest + Selenium + requests + Allure** 的分层自动化测试框架，并以
CRMEB 后台 **用户 → 用户分组** 模块的增 / 删 / 改 / 查作为完整示例落地：

- 一套用例同时覆盖 **API（requests）** 与 **UI（Selenium）** 两条路径；
- 测试数据用 **faker** 随机生成，用例自清理，不残留脏数据；
- 运行结束自动生成 **Allure 报告**（目录版 + 单文件可发送版）与运行日志；
- 核心文件（`conftest.py` / `pytest.ini` / `setup_env.py` / `make_report_sendable.py`）
  按 **通用模板** 设计，拷贝到任意 pytest 项目即可复用。

## 框架分层

```
┌─────────────────────────────────────────────────────────┐
│ 用例层  testcases/        只写业务步骤与断言，不碰实现细节      │
├─────────────────────────────────────────────────────────┤
│ 夹具层  fixtures/         登录态、页面对象等夹具的统一出口        │
├─────────────────────────────────────────────────────────┤
│ 页面对象层 pages/         PoM：元素定位 + 页面操作，用例不可见     │
├─────────────────────────────────────────────────────────┤
│ 公共层  common/           配置读取、API 封装、测试数据工厂        │
├─────────────────────────────────────────────────────────┤
│ 配置层  env_config.py     被测环境单一配置源（URL/账号/密码）      │
│         pytest.ini        pytest 运行参数、浏览器/驱动路径        │
└─────────────────────────────────────────────────────────┘
        运行支撑：conftest.py（driver fixture + 报告生成）
                  run.bat（一键入口）  setup_env.py（环境自检/装依赖）
```

依赖方向自上而下：用例层只依赖夹具层与公共层，任何一层的实现变化都不影响
上层用例的可读性。**配置优先级：环境变量 > `env_config.py` 默认值**。

## 快速开始

环境要求：

- Python 3.10+（本项目在 3.13 验证）
- Chrome 浏览器 + 对应版本 chromedriver（路径配置在 `pytest.ini`）
- Allure 命令行工具（`setup_env.py` 会检测并给出安装指引）

### 一键运行（推荐）

双击项目根目录的 **`run.bat`**，它会：

1. 首次运行自动创建 `.venv` 并安装依赖（`setup_env.py`）；
2. 执行全部用例（API + UI，会弹出 Chrome 窗口）；
3. 自动生成三份报告并打开「可发送版」：
   - `allure-report-single\index_sendable.html` ← **把这一个文件发给别人，对方双击即看**
   - `allure-report\`（目录版，本机 `allure open allure-report` 查看）
   - `pytest.log`（运行日志）

### 手动运行

在 PyCharm 终端执行 `.venv\Scripts\python -m pytest`，
或右键 `testcases/` → Run pytest（报告生成逻辑在 `conftest.py`，与入口无关）。

环境自检（只检测不安装）：`python setup_env.py --check-only`。

## 目录结构与职责

```
test_kuangjia/
├── run.bat                  # 一键运行入口（建环境 → 跑用例 → 开报告）
├── env_config.py            # 被测环境配置（URL/账号/密码，唯一配置源）
├── conftest.py              # driver fixture + 会话结束自动生成 Allure 报告
├── pytest.ini               # pytest 配置（含 Chrome/chromedriver 路径）
├── requirements.txt         # 依赖清单（唯一依赖来源，setup_env.py 自动读取）
├── setup_env.py             # 环境自检 / 缺依赖自动安装 / Allure 检测
├── make_report_sendable.py  # 把单文件报告处理成"双击即看、可发人"
├── common/                  # 公共层
│   ├── config.py            # 环境变量覆盖 + URL 协议校验
│   ├── api_client.py        # requests 封装（登录 + 分组 CRUD，请求自动进报告）
│   └── data.py              # faker 分组名工厂（"自动化_" 前缀）
├── pages/                   # 页面对象层（PoM）
│   ├── login_page.py        # 登录页 PoM
│   └── group_page.py        # 用户分组页 PoM（增删改查 + 分页 + 确认弹窗）
├── fixtures/                # 夹具层
│   └── login.py             # api / admin_logged_in / group_page fixtures
└── testcases/               # 用例层
    ├── test_group_api.py    # API 用例 9 条
    └── test_group_ui.py     # UI 用例 5 条
```

## 用例设计（用户分组 CRUD）

### API（test_group_api.py）

| # | 用例 | 级别 | 断言要点 |
|---|------|------|---------|
| 查 | 列表正常返回结构与字段 | P0 | status=200；list/count 关系；字段含 id、group_name |
| 查 | 分页 limit 生效且翻页不重复 | P2 | limit=2 单页 ≤2 行；两页 id 无交集 |
| 查 | 缺少 token 返回 401 | P1 | status=401；msg 提示登录过期 |
| 增 | 新建分组后列表可查到 | P0 | 创建 200；按名能查到 id |
| 增 | 空分组名被拒绝 | P1 | status=400；msg=请输入分组名称 |
| 改 | 改名后列表同步更新 | P0 | 修改 200；新名挂原 id；旧名消失 |
| 改 | 修改不存在的分组报错 | P1 | status=400；msg=数据不存在 |
| 删 | 删除后列表查无此组 | P0 | 删除 200；按名查不到 |
| 删 | 删除不存在的分组幂等成功 | P2 | status=200 |

### UI（test_group_ui.py）

| # | 用例 | 级别 | 验证点 |
|---|------|------|-------|
| 查 | 分组列表正常加载 | P0 | 行数>0 且分组名非空 |
| 增 | 弹窗新建分组，末页可见 | P0 | faker 名录入；翻末页出现该行；API 侧同步可查 |
| 增 | 空名提交被前端校验拦截 | P1 | 弹窗不关；出现「请输入分组名称」红字 |
| 改 | 行内修改分组名 | P0 | 同行文本变为新名，旧名消失 |
| 删 | 行内删除并确认 | P0 | 确认弹窗 → 行消失 |

> 用例自清理：造数优先走 API，用例结束（含失败）都会删除自己创建的分组；
> 万一中断残留，分组名带「自动化_」前缀便于识别清理。

## 接口契约（探测自真实前端流量）

| 操作 | 方法 & 路径 | 请求体 |
|------|------------|--------|
| 登录 | POST `/adminapi/login` | `{account, pwd, key, captchaType, captchaVerification}` |
| 查 | GET `/adminapi/user/user_group/list?page=&limit=` | - |
| 增 | POST `/adminapi/user/user_group/save.html` | `{"group_name": "..."}` |
| 改 | POST `/adminapi/user/user_group/save.html` | `{"id": N, "group_name": "..."}` |
| 删 | DELETE `/adminapi/user/user_group/del/{id}` | - |

鉴权头：`Authori-zation: Bearer <token>`（CRMEB 特有拼写）。

## 换环境 / 改账号

优先用环境变量覆盖（不改代码）：

```
set CRMEB_BASE_URL=http://<新主机>:<端口>/admin/login
set CRMEB_ADMIN=<账号>
set CRMEB_PWD=<密码>
```

或直接改 `env_config.py`。浏览器/驱动路径在 `pytest.ini` 的
`browser` / `browser_driver` 中修改。

## 复用到新项目

本框架的运行支撑文件均按通用模板设计，迁移步骤：

1. 拷贝 `conftest.py`、`pytest.ini`、`setup_env.py`、
   `make_report_sendable.py`、`run.bat`、`requirements.txt` 到新项目根目录
   （`conftest.py` 与 `pytest.ini` 必须同级）；
2. 按 `pytest.ini` 内【必改项】注释修改：`testpaths`（用例目录）、
   `browser` / `browser_driver`（本机 Chrome 与 chromedriver 绝对路径）；
3. 依赖增删只改 `requirements.txt`，`setup_env.py` 自动读取，无需改代码；
4. `common/`、`pages/`、`fixtures/` 按新被测系统填充：配置类放 `common/`，
   页面封装放 `pages/`，登录态等夹具放 `fixtures/` 并在 `conftest.py`
   通过 `pytest_plugins` 或 `fixtures/__init__.py` 暴露；
5. 运行 `run.bat` 完成建环境 → 跑用例 → 出报告全流程。

## 常见问题

- **报告没有生成**：确认 allure 命令行可用（`allure --version`）；
  不可用时 `conftest.py` 会跳过报告生成并打印提示，不影响用例执行。
- **收集用例报 PermissionError**：多为 `.pytest_cache` 被占用；
  `pytest.ini` 的 `norecursedirs` 已排除点目录与产物目录，勿随意删改 `.*` 通配。
- **改了依赖不生效**：删除 `.venv` 后重跑 `run.bat`，或直接
  `.venv\Scripts\python setup_env.py` 补装。

## 依赖

见 `requirements.txt`：pytest、allure-pytest、selenium、requests、faker、
webdriver-manager、pytest-rerunfailures、pytest-xdist、pytest-result-log。
另需 allure 命令行工具（`setup_env.py` 会检测并给出指引）。
