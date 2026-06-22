# 桌面端 Agent Core 原型说明

## E 盘运行时、COMET Sidecar 与数据集入口（2026-06-18）

- `agent_runtime.py` 负责解析 Tesseract、COMET CLI 和 COMET 模型缓存。项目 `.runtime/runtime-settings.json` 属于显式配置，优先于全局 C→E 搜索。
- `install_optional_runtimes.ps1` 强制 runtime root 位于 E 盘；Tesseract 通过 7-Zip 解包，COMET 安装在隔离 Python 3.11 环境，避免污染桌面打包 Python。
- `ExternalCometTranslationEvaluator` 通过临时 UTF-8 source/translation/reference 文件调用 `comet-score --to_json`，解析 segment COMET 分数后进入现有自迭代停止条件。
- `DesktopProjectProfile` 持久化训练/验证集路径、evaluator 类型、OCR 和 COMET 运行时设置；旧 profile 缺少字段时使用安全默认值。
- `desktop_agent_app.py --diagnostics` 可在 packaged exe 中无窗口运行同一诊断链路，并用 `--data-dir` 指定 E 盘 SQLite/凭据目录、`--report-json` 输出机器可读报告。
- `run_context_managed_translation` 已把训练/验证数据传入每个 agent slice；`ProviderRequest.training_text` 让训练样例真正进入 provider 边界。
- 远端训练集上传默认关闭；`allow_training_upload` 只有在 UI 勾选 `Upload Training` 后生效。preflight confirmation ID 绑定训练/验证内容摘要与 data scopes。

## Local Acceptance Smoke 本地验收（2026-06-17）
- `agent_acceptance.py` 提供 `run_local_acceptance` 与 `format_acceptance_lines`。
- 该验收链路使用本地 echo provider，不依赖 API、OCR 或 COMET，用于验证桌面 agent 核心闭环。
- 验收任务会强制触发上下文切分，覆盖 `initial_translation`、`continuation_translation`、`stitch_and_verify` 和 artifact 导出。
- `DesktopAgentController.run_local_acceptance` 已接入该能力；Tkinter 入口新增 `Run Local Smoke`，结果显示在预检列表中。
- `agent_acceptance.py` 也提供 CLI，可由 `run_desktop_acceptance.ps1` 调用；`desktop_agent_app.py` 支持 `--local-smoke`，用于 packaged exe 的无窗口验收。

## Delivery Diagnostics 交付诊断（2026-06-17）
- `agent_diagnostics.py` 定义 `DiagnosticCheck`、`DiagnosticReport`、`run_desktop_diagnostics` 和 `format_diagnostic_lines`。
- 诊断链路覆盖桌面打包 preflight、release exe、Tesseract OCR、COMET runtime、provider 配置/凭据，以及 GUI 手工启动 smoke。
- `DesktopAgentController.run_diagnostics` 复用同一套后端诊断；Tkinter 入口新增 `Run Diagnostics`，结果显示在预检列表中。
- 该能力用于核验“前端 UI 与后端代码是否匹配”和“桌面软件 agent 是否具备可交付产物”，但真实 provider API、真实 OCR runtime、真实 GUI 交互仍需要目标机器上的手工或联调验证。

## Portable Release 包（2026-06-17）

- `agent_release.py` 提供 `check_desktop_release_ready` 与 `build_desktop_release_package`，在已有 PyInstaller one-folder 产物基础上生成 portable zip。
- `build_desktop_release.ps1` 会先调用 `build_desktop_agent.ps1`，再写入 release manifest 和 zip。
- manifest 包含版本、渠道、入口 exe、exe/zip SHA256、包含文档、可选外部依赖和未包含发布项。
- 该能力用于可交付包归档和校验，不替代安装器、代码签名或自动更新。

## HOOK/OCR 输入插件（2026-06-17）

- `agent_input_plugins.py` 定义 `CapturedInput`、`InputPluginRegistry` 和输入插件协议。
- `OcrImageInputPlugin` 支持图片路径输入，默认调用本机 `tesseract <image> stdout -l <lang>`，也支持注入自定义 OCR 函数，避免把重型 OCR runtime 写死进核心。
- `HookTextBufferPlugin` 提供安全的 hook 文本缓冲入口，当前不执行进程注入；外部 hook 工具或桌面剪贴板导入可把文本追加到缓冲区，再由 agent workflow 消费。
- `DesktopAgentController.capture_plugin_input` 与 `translate_plugin_input` 让 OCR/HOOK 输入进入和普通文本相同的上下文估算、术语记忆、候选翻译、裁决、续译和审计链路。
- Tkinter 入口新增 `Open OCR Image` 与 `Import Hook Text`，用于验证桌面软件形态下的插件输入闭环。

## Provider Smoke 探活（2026-06-17）

- `agent_provider_smoke.py` 提供 `smoke_test_provider` 与 `ProviderSmokeResult`，用于对当前 provider 执行最小样例翻译探活。
- `DesktopAgentController.smoke_test_providers` 会使用当前 source/target/topic 配置，对已加载 provider 逐个探活，并返回成功/失败、延迟、token、成本、警告和错误信息。
- Tkinter 桌面入口新增 `Smoke Providers` 按钮，结果复用远端预检列表展示。
- Smoke 探活是联调工具，不进入正式 agent run，不写入 `agent_runs`、`revision_events` 或正式词库。

## 定位

Phase-3 Agent Core 是后续桌面端优先路线的服务层原型。它不替代当前 Streamlit 验证台，而是落地可测试的 agent 契约、运行模式、provider adapter、批量文本输入、上下文预算续译、SQLite 审计、provider 配置、HOOK/OCR 输入插件、桌面入口和交付诊断。真实多云 API、真实进程 hook、安装器、签名和自动更新仍属于目标环境联调与发布工程。

## 运行模式

- `learning`：学习模式。生成候选译文、裁决结果和词库更新提案，但正式输出与词库写回需要人工确认。
- `self_iterative`：自迭代模式。要求训练集与验证集，使用 deterministic 验证集评分驱动最多三轮自动交火/再裁决；三轮后仍低于阈值则进入人工复核。
- `self_decision`：自决策模式。`MetaPolicyAgent` 根据训练/验证覆盖、API 开关和预算选择学习门控或自迭代，并将原因写入 trace。

## 核心模块

- `agent_acceptance.py`：离线本地验收 smoke，验证上下文切分、续译、拼接核验和 artifact 导出闭环。
- `agent_contracts.py`：`AgentRunContract`、`TranslationCandidate`、`ConsensusDecision`、`LexiconUpdateProposal`、`ModePolicy`。
- `agent_providers.py`：provider adapter 协议、静态测试 provider、现有本地工作流 provider、OpenAI-compatible HTTP provider。
- `agent_workflows.py`：单任务与批量任务 agent 编排。
- `agent_inputs.py`：`txt/md/docx` 文本抽取。
- `agent_context.py`：上下文长度估算、当前片段/待续片段切分。
- `agent_continuation.py`：初始翻译、续译任务、拼接核验任务编排。
- `agent_project.py`：桌面项目配置契约，保存语言、主题、模式、训练/验证集、evaluator、OCR/COMET 运行时、上下文预算、API 开关和最近文件。
- `agent_meta_policy.py`：自决策策略层，判断是否满足进入自迭代的验证覆盖、API 和预算条件。
- `agent_preflight.py`：远端调用前预检，生成 provider、文本片段、上下文 token、预估成本和预算风险。
- `agent_runtime.py`：C→E 工具发现、项目 runtime settings 与 COMET 模型缓存解析。
- `agent_store.py`：SQLite 审计、确认门控、三层词库存储、JSON 词库导入与 topic 查询。
- `agent_credentials.py`：本机凭据存储；Windows 下使用 DPAPI，避免密钥明文写入配置。
- `agent_provider_config.py`：provider 配置到 provider 实例的构建边界，支持只构建启用 provider。
- `agent_diagnostics.py`：桌面交付诊断，检查打包/release 产物、可选 OCR/COMET runtime、provider 配置/凭据和 GUI 手工 smoke 项。
- `desktop_agent_app.py`：Tkinter 桌面端原型入口与桌面控制器，支持翻译、审计 run、待确认词库提案、人工确认输出、词库写回、provider 配置/探活、OCR/Hook 输入、artifact 导出和交付诊断。

## 安全边界

- API 调用由 provider adapter 控制，`api_enabled=False` 时远端 provider 会被跳过。
- 训练集默认只供本地 provider 使用；远端上传必须显式开启，并在 preflight 中显示数据范围。
- provider 配置持久化在 SQLite `provider_configs` 中，只保存 `credential_id`，不保存 API key 明文；真实密钥由 `LocalCredentialStore` 管理。
- 桌面项目配置持久化在 SQLite `project_profile` 中；默认桌面数据库路径为 `%LOCALAPPDATA%\ConsensusTranslation\agent.sqlite3`。
- 预算在 provider 调用前检查，超预算会停止并写入 trace。
- 桌面控制器在远端 provider 实际调用前要求一次性 preflight 确认；预检 ID 与输入文本、provider、上下文预算、运行模式和成本估算绑定。
- 学习模式默认人工确认门控，未确认的词库提案只写入 `revision_events`，不会进入正式词库表。
- agent 运行前按 topic 查询当前文本命中的 `terms` / `phrases` / `style_rules`，并传入 `ProviderRequest`，trace 中记录命中数量。
- 桌面控制器可以按事件 ID 确认词库提案，也可以将 agent run 从 `awaiting_human_confirmation` 标记为 `finalized`。
- 长文本任务会先估算上下文长度，并保留 `pending_text`。续译任务继承前序译文总结、写作结构与翻译要点。
- 初始翻译、续译、拼接核验都带独立 `task_id`，可被桌面端和审计层追踪。

## 长文本续译链路

1. 任务开始前使用 `ContextBudget` 估算输入 token，并预留输出 token。
2. 若输入超过限制，`ContextSlicePlan` 将可处理片段放入当前 workflow，将其余片段标记为待续；多个仍能放入当前上下文的片段会合并为同一个初始翻译任务，避免漏译。
3. 初始片段翻译完成后生成 `translation_brief`，记录写作结构、翻译要点和前序摘要。
4. 每个待续片段单独生成 `continuation_translation` 任务，并继承同一 `translation_brief`。
5. 全部片段完成后生成 `stitch_and_verify` 任务，按任务 ID 顺序拼接译文并核验空段、段数和顺序。

## 桌面入口

```powershell
powershell -ExecutionPolicy Bypass -File .\run_desktop_agent.ps1
```

该入口当前提供桌面软件外壳验证，已经包含基础文件选择、项目配置保存、最近文件、远端调用预检、候选列表、人工确认和任务审计基础控件；后续会继续接入 provider 设置页和更完整的项目管理界面。

## 词库迁移

旧版 JSON 词库可迁移到桌面 SQLite store：

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate_legacy_lexicon.ps1
```

也可以显式指定输入和输出：

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate_legacy_lexicon.ps1 --source .\data\lexicon.json --db "$env:LOCALAPPDATA\ConsensusTranslation\agent.sqlite3"
```

底层模块为 `consensus_translation.agent_lexicon_migration`，输出 JSON 摘要，包含源路径、目标 DB 与 `terms` / `phrases` / `style_rules` 导入计数。

## 后续路线

1. 使用用户真实 API key/base URL/model 做远端 provider smoke 和小样本翻译验收。
2. 在目标机器安装或配置 Tesseract/COMET 后执行 OCR 与质量评估联调。
3. 将 Hook 文本缓冲扩展为可对接 Textractor/LunaTranslator 等外部捕获工具的适配器；暂不做未审计的进程注入。
4. 打磨桌面 UI 的候选对比、批量任务队列和审计浏览体验。
5. 补充安装器、代码签名、自动更新和正式发布流程。

## 评估器扩展（2026-06-16）

- `agent_evaluators.py` 新增 `TranslationEvaluator` 协议、`EvaluationRequest` 与 `EvaluationResult`，自迭代验证从固定 deterministic 指标改为可插拔评估器。
- 默认 `DeterministicTranslationEvaluator` 继续复用本地 `evaluate_translation`，保证离线与测试环境不依赖外部模型。
- `CometTranslationEvaluator` 作为可选 COMET 适配层，支持注入模型或在安装可选 runtime 后加载 COMET 模型；用于后续更强译文质量估计。
- `OpenAICompatibleJudgeEvaluator` 支持 OpenAI-compatible LLM-as-evaluator，要求评审模型返回 JSON `score` 与 `rationale`，并将 token 用量写入 metrics。
- `agent_workflows.py` 在 `self_iterative` 每轮裁决后调用 evaluator，trace 记录 `validation_evaluator:*`、`validation_score:*`、`validation_review_required:*`。
- `agent_preflight.py` 已把远端 evaluator 纳入远端调用预估，桌面端确认门会显示 evaluator、上下文片段、轮次、成本和预算风险。

## 续译 brief 与拼接核验补强（2026-06-16）

- `translation_brief` 现在明确包含四段：写作结构、翻译要点、待续策略、前序摘要。
- `ProviderRequest` 新增 `continuation_brief`，待续片段进入 provider 前会收到同一份前序 brief；OpenAI-compatible provider 会把该 brief 放入提示词。
- `ManagedTranslationTask` 新增 `verification` 字段，`stitch_and_verify` 任务会保存拼接核验结果，而不只是保留一个占位 task id。
- 拼接核验报告包含 `status`、`segment_count`、`expected_segment_count`、`empty_segment_count`、`order_preserved`、`context_limit_respected` 与 `source_task_ids`。

## 桌面导出包（2026-06-17）

- `agent_artifacts.py` 提供 `export_translation_artifacts`，用于把一次 `ContextManagedTranslationResult` 落盘为可交付文件。
- 导出文件包括最终译文、续译 brief、拼接核验 JSON、分段审计 JSON 和 manifest。
- manifest 记录 artifact 版本、项目 id、配置摘要、上下文 token 估算、切片数量、待续切片数量、任务 id、run id 与最终核验状态。
- `DesktopAgentController.export_translation_artifacts` 已接入该服务；Tkinter 原型提供 `Export Artifacts` 按钮。

## Windows 打包入口（2026-06-17）

- `agent_packaging.py` 提供桌面打包预检，检查桌面入口、PyInstaller spec、构建脚本、桌面依赖文件和 PyInstaller runtime。
- `requirements-desktop.txt` 保存桌面打包可选依赖，避免把 PyInstaller 加入基础运行依赖。
- `packaging/desktop_agent.spec` 以 `desktop_agent_app.py` 为入口，生成 `ConsensusTranslationAgent` one-folder 桌面包。
- `build_desktop_agent.ps1` 先执行预检，再调用 `python -m PyInstaller packaging\desktop_agent.spec --noconfirm --clean`。
- 当前打包入口是发布前置能力，不替代后续安装器、签名和自动更新流程。

## 桌面 Provider 设置入口（2026-06-17）

- `DesktopAgentController.save_provider_settings` 可保存 OpenAI-compatible provider 配置，并把 API key 写入 `LocalCredentialStore`。
- `default_desktop_credentials_path` 默认定位到 `%LOCALAPPDATA%\ConsensusTranslation\credentials.json`。
- Tkinter 原型新增 Provider ID、Base URL、Model、API Key、Cost、Enabled 控件，以及 `Save Provider` 和 `Load Providers` 按钮。
- `Load Providers` 会调用 `load_enabled_provider_configs`，把 SQLite 中启用的 provider 转换为当前运行时 provider 列表。
