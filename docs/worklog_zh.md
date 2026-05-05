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

## 六、Web 文件工作流与 LLM 配置（本次新增）

- 新增全局 LLM 配置服务：支持 `gpt/qwen/kimi/deepseek/gemini/watsonx` 六种 provider。
- 新增配置接口：`POST/GET/DELETE /config/llm`，支持本地配置文件持久化与状态查询。
- 新增文件任务接口：`POST /tasks/file`、`GET /tasks/file/{task_id}`、`GET /downloads/{task_id}`。
- 新增文件能力：支持 `txt/md/docx` 上传，翻译输出保持原格式。
- 新增词库自动解析：支持 `术语=译文`、`术语,译文`、`术语\t译文`，失败回退整行术语。
- Streamlit 页面新增 LLM 配置面板、配置监控窗口、文件任务面板。
- 新增 PNG profile 修复工具：`python -m src.tools.fix_png_profiles --root .`，用于根因处理 `libpng iCCP` 警告源头。

## 七、Windows EXE 打包与图片资源文档（本次新增）

- 新增桌面 EXE 打包脚本：`scripts/build_exe.ps1`（PyInstaller `--onefile`，目标入口为 PyQt）。
- 新增 EXE 冒烟脚本：`scripts/smoke_test_exe.ps1`（检查进程拉起并给出结果）。
- 新增占位图标：`assets/icons/app_placeholder.ico`，支持后续替换为正式图标。
- 预留图片资源目录：`assets/images/`（当前版本不强依赖业务图片资源）。
- PyQt 启动新增离线提醒：未联网时提示“当前未联网，部分功能受限”，但不阻断运行。
- 保持现有运行基础不变：`run.ps1`、Web/API 启动路径继续可用。
