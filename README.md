# Cn-Jp Translate

## Release license profile

- Project source: Apache-2.0; see `LICENSE` and `NOTICE`.
- Default local release profile: `commercial-safe`, using commercial-compatible OPUS-MT routes.
- `facebook/nllb-200-distilled-600M` is CC-BY-NC-4.0 and is excluded from commercial bundles; it remains an explicit research-only option.
- Model and dependency boundaries are recorded in `MODEL_LICENSES.md`, `THIRD_PARTY_NOTICES.md`, and `PRIVACY.md`.

## Desktop Runtime Integration（2026-06-18）

- 新增 `agent_runtime.py`：运行时路径按显式项目配置、C 盘常见位置、E 盘常见位置依次解析；`install_optional_runtimes.ps1` 生成的 `.runtime/runtime-settings.json` 具有最高优先级。
- 新增 `install_optional_runtimes.ps1`：强制所有下载、Tesseract、COMET Python 3.11 环境和 COMET 模型缓存位于 E 盘。Tesseract 使用 7-Zip 解包，不运行可能忽略安装目录的 Windows 安装器。
- 桌面端新增 `Training Set`、`Validation Set`、`Evaluator`、`Upload Training`、`Tesseract`、`OCR Lang`、`COMET Command`、`COMET Model` 与 `COMET Cache` 设置，并写入项目 profile。
- 桌面入口支持无窗口诊断：`ConsensusTranslationAgent.exe --diagnostics --project-root <root> --data-dir <E:\data> --report-json <file>`，便于在目标机器核验 packaged runtime。
- 新增 `ExternalCometTranslationEvaluator`，portable exe 通过 E 盘 `comet-score.exe` sidecar 使用 COMET，不把 PyTorch/Transformers 打进基础桌面包。
- 训练集默认不会发送给远端 provider；只有勾选 `Upload Training` 后才会加入远端 prompt。远端 preflight 会显示 `scopes=source`、`scopes=source,training` 或 evaluator 的 `source,candidate,validation` 范围。
- 当前已验证 E 盘 Tesseract 5.5.0 CLI 和真实英文图片 OCR；日文/中文语言包与 COMET 依赖/模型下载需在网络权限可用时运行安装脚本完成。

## Phase-3 Local Acceptance Smoke（2026-06-17）
- 新增 `agent_acceptance.py`，提供不依赖远端 API、OCR 或 COMET 的离线验收 smoke。
- PySide6 桌面端提供 `Run Local Smoke` 入口；它会运行一次强制分段的本地 agent workflow，覆盖上下文估算、当前/待续切片、续译 brief、拼接核验和 artifact 导出。
- 默认 artifact 会写入本机桌面数据目录下的 `acceptance` 文件夹，用于确认目标机器至少能完成核心 agent 闭环。
- 也可运行 `powershell -ExecutionPolicy Bypass -File .\run_desktop_acceptance.ps1`，在不打开 GUI 的情况下生成 `.acceptance/local-acceptance-report.json`。
- 发布后的桌面入口支持 `ConsensusTranslationAgent.exe --local-smoke --acceptance-dir <dir> --report-json <file>`，用于目标机器上的无窗口验收。

## Phase-3 Delivery Diagnostics（2026-06-17）
- 新增 `agent_diagnostics.py`，把桌面打包文件、release exe、Tesseract OCR、COMET runtime、provider 配置/凭据和 GUI 手工 smoke 统一成可展示的诊断报告。
- `DesktopAgentController.run_diagnostics` 已接入该报告；PySide6 桌面端提供 `Run Diagnostics` 页面，诊断结果显示在应用内。
- 诊断报告会把缺少打包/release 产物标为 `error`，把可选外部能力（Tesseract、COMET、provider 凭据、GUI 手工启动）标为 `warning`，避免把外部环境缺口误判为核心 workflow 失败。

## Phase-3 Portable Release 包（2026-06-17）

- 新增 `agent_release.py` 与 `build_desktop_release.ps1`，可在构建 one-folder exe 后生成 `release/ConsensusTranslationAgent-<version>-portable.zip`。
- Release manifest 会记录版本、渠道、入口 exe、exe/zip SHA256、包含文档、可选外部依赖和未包含事项。
- 当前 release 同时支持 portable zip、标准 Inno Setup 安装包和内置 OCR/COMET runtime 的 full 分卷安装包；代码签名和自动更新仍未包含。

## Phase-3 HOOK/OCR 输入插件（2026-06-17）

- 新增 `agent_input_plugins.py`，提供统一输入插件契约、OCR 图片插件和 HOOK 文本缓冲插件。
- PySide6 桌面端保留 OCR、文件夹 inbox 和 hook/剪贴板输入入口；这些输入都会进入同一个 agent translation workflow。
- OCR 默认通过本机 `tesseract` 命令行执行，也支持测试或后续插件注入自定义 OCR 函数；未安装 Tesseract 时会返回明确错误，不影响普通文本/docx 输入。
- 当前 HOOK 是安全的文本缓冲入口，不做进程注入；后续可接 Textractor/LunaTranslator 类外部 hook 工具输出。

## Phase-3 Provider Smoke 探活（2026-06-17）

- 新增 `agent_provider_smoke.py`，用于对当前 provider 列表执行最小样例翻译探活。
- PySide6 桌面端提供 provider 配置和 `Smoke Providers` 入口；它会使用当前源语、目标语和 topic，发送最小样例文本，并在远端预检列表中显示成功/失败、延迟、token、成本和译文预览。
- `api_enabled=False` 时，远端 provider smoke 会返回 `api disabled`，不会发起远端请求。
- Smoke 探活不写入正式 agent run、不写入词库，也不替代完整翻译质量验收；它只用于确认已保存并加载的 provider 端点、模型名和凭据是否可用。

中英日专项翻译工具（面向游戏文本与流行小说），当前已完成第二阶段落地：本地模式可投入使用，前后端契约字段对齐并通过自动化核验。

## 当前状态

- 分支：`codex/desktop-agent-core`
- 运行形态：Streamlit 验证台 + PySide6 可安装桌面 Agent
- 翻译引擎：
  - Engine A: Marian（Opus-MT）
  - Engine B: Meta NLLB-200
- 阶段结论：
  - 第二阶段已完成（M1/M2/M3/M4 + Gate-L + UI-Backend Contract Gate）
  - 第三阶段 Agent 核心原型已落地：契约、provider adapter、三种运行模式策略、SQLite 审计与确认门控
  - Streamlit UI 仍作为验证台；桌面端 PySide6 Agent、训练/验证集入口、HOOK/OCR/文件夹 inbox、provider 配置、COMET sidecar、诊断、portable release 和 Inno Setup 安装器已落地；真实外部 API 联调按用户要求延期，真实进程 hook、签名和自动更新仍属后续发布工程

## 快速开始

1) 安装依赖

```powershell
E:\Ana\python.exe -m pip install -r requirements.txt
```

2) 启动应用

```powershell
powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1
```

3) 打开地址

- `http://localhost:8501`

## 核心能力（第二阶段）

- 本地模式：双引擎候选 + MDWC 裁决 + 可解释输出
- 预训练模式：可复现评估指标输出与提升率计算
- 词库：三层结构（`terms` / `phrases` / `style_rules`）与兼容迁移
- 要素识别：神话/历史/科学标签识别与分值联动追踪
- 工程化：初始化脚本、日志级别控制、审计导出、恢复标记

## Phase-3 Agent Core（原型）

- 运行模式：`learning`、`self_iterative`、`self_decision`
- 自迭代：验证集评分驱动最多三轮重试，低于阈值会转人工复核
- 自决策：`MetaPolicyAgent` 根据训练/验证覆盖、API 开关和预算选择 learning 或 self_iterative
- Provider：支持静态测试 provider、现有本地工作流 provider、OpenAI-compatible HTTP provider
- Provider 配置：SQLite 保存 provider id、类型、base URL、模型、credential id、估算成本和启用状态；API key 只保存在本机凭据 store
- 输入：agent 层支持 `txt` / `md` / `docx` 批量文本入口
- 项目配置：桌面端保存 source/target/topic/mode/context/budget/API 开关和最近文件；默认 SQLite 路径为 `%LOCALAPPDATA%\ConsensusTranslation\agent.sqlite3`
- 安全：学习模式默认人工确认门控，未确认的词库提案只进入 SQLite `revision_events`，不会写入 `terms`
- 存储：SQLite schema 已覆盖 `terms` / `phrases` / `style_rules` / `project_profile` / `agent_runs` / `revision_events`，并支持从 JSON 词库导入三层数据
- 术语记忆：agent 运行前会按 topic 查询当前文本命中的术语、短语和风格规则，并注入 provider request
- 远端预检：API provider 调用前生成 provider、文本片段、上下文 token、预估成本和预算风险；桌面控制器要求一次性确认后才允许实际远端调用
- 长文本：任务开始前估算上下文，按用户设置的上下文限制切分为当前片段与待续片段；所有可放入当前上下文的片段会合并进入初始任务，续译任务继承写作结构与翻译要点，最后单独执行拼接核验
- 凭据：provider 配置只引用 credential id；本机凭据 store 在 Windows 下使用 DPAPI 保护密钥

## 桌面端原型入口

当前正式桌面端入口采用 PySide6；源码环境可直接运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_desktop_qt.ps1
```

该入口用于验证桌面软件形态；controller 已支持文本、单文件、多文件任务、项目配置保存、最近文件、远端调用预检、候选列表、审计 run 列表、待确认词库提案、人工确认写回、provider 配置/探活、OCR/Hook/文件夹 inbox 文本输入、artifact 导出和交付诊断。安装器已支持用户选择安装目录和桌面快捷方式；代码签名、自动更新、真实进程 hook 和带用户密钥的远端 API 联调仍按后续路线推进。

## 旧词库迁移

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate_legacy_lexicon.ps1
```

可显式指定路径：

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate_legacy_lexicon.ps1 --source .\data\lexicon.json --db "$env:LOCALAPPDATA\ConsensusTranslation\agent.sqlite3"
```

## 文档入口

- 工作日志：`docs/worklog_zh.md`
- 用户手册：`docs/user_manual_zh.md`
- 阶段规格：`docs/superpowers/specs/2026-05-07-phase2-realignment-and-local-go-live-design.md`
- 实施计划：`docs/superpowers/plans/2026-05-07-phase2-local-go-live-implementation-plan.md`
- Agent 核心说明：`docs/desktop_agent_core_zh.md`
- Agent 调研记录：`docs/desktop_agent_research_zh.md`

## Phase-3 评估器补充（2026-06-16）

- 新增可插拔 `TranslationEvaluator` 层：默认 `deterministic` 评估器继续复用现有 `evaluate_translation`，自迭代流程不再写死单一验证指标。
- 新增 `CometTranslationEvaluator` 适配器：支持注入已加载模型，运行环境安装可选 COMET runtime 后可加载 COMET 模型做译文质量估计。
- 新增 `OpenAICompatibleJudgeEvaluator`：用 OpenAI-compatible `/chat/completions` 接口作为 LLM-as-evaluator，要求返回 JSON 分数与简短理由。
- 远端 evaluator 已纳入 preflight：`self_iterative` 需要远端 LLM 评审时，会在执行前列出 evaluator、上下文片段、轮次、估算 token 与成本，并复用桌面端一次性确认门。

## Phase-3 续译链路补充（2026-06-16）

- 待续片段现在会把 `translation_brief` 写入 `ProviderRequest.continuation_brief`，真实 provider 能直接看到前序写作结构、翻译要点、待续策略和前序摘要。
- `stitch_and_verify` 不再只是任务占位；该任务会携带结构化 `verification` 报告，用于检查分段数、空段、拼接顺序、上下文限制和来源任务 id。

## Phase-3 桌面导出包补充（2026-06-17）

- 新增 `agent_artifacts.py`，可把一次上下文托管翻译导出为桌面可交付 artifact 包。
- 导出内容包括 `*.translation.txt`、`*.brief.md`、`*.verification.json`、`*.segments.json`、`*.manifest.json`。
- PySide6 桌面端提供 artifact 导出入口，运行一次 Agent 后可把最终译文、续译 brief、拼接核验和分段审计写入用户选择的目录。

## Phase-3 Windows 打包入口（2026-06-17）

- 新增 `requirements-desktop.txt`，将 PyInstaller 作为桌面打包可选依赖。
- 新增 `agent_packaging.py`，提供桌面打包预检，检查入口文件、spec、构建脚本、桌面依赖和 PyInstaller 是否可用。
- 新增 `packaging/desktop_agent_qt.spec` 与 `build_desktop_qt.ps1`，用于构建 `ConsensusTranslationAgent` PySide6 桌面应用。

```powershell
E:\Ana\python.exe -m pip install -r requirements-desktop.txt
powershell -ExecutionPolicy Bypass -File .\build_desktop_qt.ps1
```

该入口依据 PyInstaller 官方 spec 文件工作流组织，当前用于生成 Windows one-folder 桌面包；`build_installer.ps1` 可生成标准安装包和带 OCR/COMET runtime 的 full 分卷安装包。

## Phase-3 Provider 设置入口（2026-06-17）

- PySide6 桌面端新增 Provider ID、Base URL、Model、API Key、Cost、Enabled 控件。
- 新增 `Save Provider` 与 `Load Providers` 按钮，可把 OpenAI-compatible provider 配置保存到 SQLite，并从本机 credential store 加载启用 provider。
- API key 不写入 `provider_configs`，只保存到本机凭据文件；SQLite 中只保存 `credential_id`。
