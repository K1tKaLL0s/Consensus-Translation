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
- 首次使用建议执行：`.\run.ps1 -Init`。
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

## 八、PyQt 交互式一期（Task 7）

- 主窗口改为 **PyQt 交互式面板**：采用 `QTabWidget` 承载翻译面板、训练面板与结果面板，替代静态分屏。
- 翻译工作流增加 **修订/确认** 双动作：先修订再确认，只有确认后才允许持久化确认状态。
- 结果区执行 **复制按钮解锁** 规则：初始禁用，翻译修订阶段保持禁用，仅在确认完成后解锁复制。
- 训练工作流补充兜底行为：未上传参考文本时，可回退读取 `references/{source_declaration}.txt`。
- 离线提示策略更新：保留“当前未联网，部分功能受限”提醒，且 **离线提醒为非阻塞**，不使用阻塞式模态框，不影响界面继续操作。

### Task 7 规格复核验证记录

- `pytest -q`：`175 passed in 9.3s`，状态：通过。
- `./scripts/build_exe.ps1 -Clean`：PyInstaller 输出 `Build complete!`，并生成 `dist/CnJpTranslateDesktop.exe`，状态：通过。
- `./scripts/smoke_test_exe.ps1`：输出 `Smoke test passed`，状态：通过。

### 文档断言测试（红-绿）补充说明

- 本次为 Task 7 规格复核新增文档断言测试 `test_worklog_contains_task7_spec_review_verification_record`。
- 在补充验证记录内容前，断言预期失败（红）；补充 `docs/worklog_zh.md` 后重新执行转为通过（绿），完成 fail-then-fix 验证闭环。

## 九、Task 7 网络状态可见性与启动提示补充（本次新增）

- 文档补充网络状态接口：统一标注后端端点 `/system/network`，供桌面端与网页端共享。
- PyQt 与 Streamlit 均补充网络状态可视化说明，并明确支持“手动刷新”操作。
- 启动模式一致性补充：`web/desktop/all` 共享后端启动约定，`all` 为组合模式。
- 多提供商候选与 provider 分解高亮同步入册：
  - `DeepSeek`：`TEx + Gen-A`
  - `Gemini`：`Etym + Gen-B`
  - `watsonx.ai`：`Gen-C + Arb`
  - 兼容入口：`GPT / 千问 / Kimi`
- `run.ps1` 启动输出补充网络提示：
  - API 输出网络状态接口提示：`http://127.0.0.1:8000/system/network`
  - Streamlit/PyQt 输出“支持手动刷新网络状态”提示。

### Task 7 文档网络状态断言（红-绿）

- 新增断言测试：`test_docs_cover_network_status_visibility_and_manual_refresh_mentions`。
- 红：先运行该测试，因文档未包含 `/system/network` 与“手动刷新”而失败。
- 绿：补充 `docs/worklog_zh.md` 与 `docs/user_manual_zh.md` 后，测试转为通过。

### Task 7 启动语义对齐修复（本次补充）

- 对齐 `run.ps1` 与文档语义：`desktop` 模式改为 **API + PyQt**（不启动 Streamlit）。
- 保持 `web` 语义不变：`API + Streamlit`。
- 保持 `all` 语义不变：同时覆盖 Web 与 Desktop（`API + Streamlit + PyQt`）。
- 明确网络状态可用性：`/system/network` 在 `web/desktop/all` 三种模式均由 API 提供，PyQt 与 Streamlit 均可读取并支持手动刷新。
