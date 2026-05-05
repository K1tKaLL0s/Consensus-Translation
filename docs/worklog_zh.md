# 工作日志（中文）

## 一、项目完整性核验记录

- 代码分支已合并至 `main` 并推送远程，当前仓库状态干净（`main...origin/main`）。
- 全量测试已通过：`pytest -q` -> `91 passed`。
- 关键入口已核验：
  - 一键启动脚本：`run.ps1`
  - 后端入口：`src/api/main.py`
  - 桌面入口：`src/ui/pyqt_app/main_window.py`
  - Web 入口：`src/ui/web_app/streamlit_app.py`
  - MySQL 引导：`src/tools/bootstrap_mysql.py`

## 二、阶段性交付记录

### 1) 核心系统交付（MAATCS MVP）

- 完成多智能体核心链路：TEx/Etym/Gen/Arb + orchestrator。
- 完成 MySQL ORM 建模与初始化脚本。
- 完成 API 合约：翻译、训练、反馈确认、事件流、词库导出。
- 完成 PyQt 三联屏与 Streamlit 上传界面。
- 完成端到端与契约测试体系。

### 2) 文档与插件交付（Task12）

- 补齐文档包：
  - `README.md`
  - `docs/cost_strategy.md`
  - `docs/user_manual_zh.md`
  - `docs/presentation_script_zh.md`
- 新增浏览器插件 MVP 脚手架：
  - `extensions/browser/manifest.json`
  - `extensions/browser/popup.html`
  - `extensions/browser/popup.js`
- 文档与插件回归测试：`tests/test_task12_docs_and_plugin_scaffold.py`。

### 3) 启动体验与数据库自动化（新增）

- 新增一键启动脚本：`run.ps1`
  - `-Init`：初始化环境（venv/依赖/数据库引导）
  - `-Mode web|desktop|all`：启动模式切换
  - `-SkipInstall` / `-SkipDB`：初始化跳过项
- 新增 MySQL 引导模块：`src/tools/bootstrap_mysql.py`
  - 探测 MySQL 可连接性
  - 自动执行 `CREATE DATABASE IF NOT EXISTS`
  - 自动执行 `Base.metadata.create_all`
  - 异常统一返回可读诊断（安装/服务/端口配置）
- 新增测试：
  - `tests/test_bootstrap_mysql.py`
  - `tests/test_run_ps1.py`

## 三、关键约束落实情况

- 翻译入口必须携带来源声明（source declaration）。
- 训练模式采用无硬上限 + 分段处理策略。
- 词库能力支持分类管理与导出。
- LLM 路由可识别 `deepseek` / `kimi` / `qwen`，并支持无 key 时 Mock 回退。

## 四、已知注意事项

- 桌面模式依赖 `PyQt6`，需在项目虚拟环境安装依赖后运行。
- 首次使用建议执行：`\.\run.ps1 -Init`。
- 如 MySQL 未安装或服务未启动，系统会输出可执行引导命令。

## 五、后续建议

- 为插件增加 API Base URL 图形化配置。
- 在用户手册补充常见故障 FAQ（端口占用、MySQL 服务名差异、权限问题）。
