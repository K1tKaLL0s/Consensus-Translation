# 共识翻译 V1 用户手册（中文）

## E 盘可选运行时与训练/验证集（2026-06-18）

1. 在项目根目录运行：

```powershell
powershell -ExecutionPolicy Bypass -File .\install_optional_runtimes.ps1
```

脚本会拒绝非 E 盘路径，并在 `.runtime` 下安装 Tesseract、Python 3.11 COMET sidecar 与 COMET 模型缓存。可分别使用 `-SkipTesseract`、`-SkipComet`、`-SkipCometModel` 跳过组件。

2. 桌面端运行设置：

- `Training Set`：选择 `txt/md/docx` 训练样例或风格上下文。
- `Validation Set`：选择自迭代模式使用的参考译文。
- `Evaluator`：`deterministic` 或 `comet`。
- `Tesseract` / `OCR Lang`：OCR 可执行文件与语言组合，例如 `jpn+eng`。
- `COMET Command` / `COMET Model` / `COMET Cache`：外部 `comet-score.exe`、模型名和 E 盘缓存目录。

3. 数据上传边界：

- `Upload Training` 默认关闭。关闭时，本地 provider 可以使用训练集，远端 provider 只收到 source。
- 开启后，训练集才会加入远端 provider prompt；每次调用前仍必须通过 `Confirm Remote Calls`。
- 预检列表中的 `scopes` 明确显示本次远端调用涉及 source、training、candidate 或 validation。

当前机器已通过 E 盘 Tesseract 5.5.0 的真实英文 OCR smoke。日文/中文语言模型与 COMET 安装需在下载权限可用时重新运行脚本。

目标机无窗口诊断命令：

```powershell
ConsensusTranslationAgent.exe --diagnostics --project-root <项目或解压根目录> --data-dir <E:\桌面数据目录> --report-json <报告.json>
```

`--data-dir` 会把 SQLite 与凭据文件位置切换到指定目录，适合 `%LOCALAPPDATA%` 不可写或要求所有运行数据位于 E 盘的环境。诊断只有出现 `error` 才返回非零；缺少可选 provider/COMET 或人工 GUI smoke 会保留为 warning。

## Local Acceptance Smoke 本地验收（2026-06-17）
- 桌面原型新增 `Run Local Smoke` 按钮，用于在没有远端 API、OCR、COMET 的情况下验证核心 agent 闭环。
- 该 smoke 会使用本地 echo provider 运行一次强制分段任务，覆盖上下文估算、当前片段、待续片段、续译 brief、拼接核验和 artifact 导出。
- 结果会显示在预检列表中，并把验收 artifact 写入本机桌面数据目录下的 `acceptance` 文件夹。
- 源码环境可运行 `powershell -ExecutionPolicy Bypass -File .\run_desktop_acceptance.ps1`，默认输出 `.acceptance/local-acceptance-report.json`。
- 发布包入口可运行 `ConsensusTranslationAgent.exe --local-smoke --acceptance-dir <dir> --report-json <file>`，用于不打开 GUI 的目标机器验收。
- 该 smoke 只能证明核心 workflow 可运行；真实翻译质量、真实远端模型和 GUI 手工体验仍需单独验收。OCR 另有 E 盘 Tesseract 真实 smoke 记录。

## Delivery Diagnostics 交付诊断（2026-06-17）
- 桌面原型新增 `Run Diagnostics` 按钮，用于在软件内检查当前交付环境。
- 诊断内容包括：桌面入口与打包文件、release exe、Tesseract OCR、COMET runtime、已启用 provider 配置与本机凭据、GUI 手工启动 smoke。
- 缺少打包或 release 产物会显示为 `error`；Tesseract、COMET、远端 provider 凭据和 GUI 手工启动属于外部/可选条件，缺失时显示为 `warning`。
- 该诊断不替代真实翻译质量验收，也不会调用远端 provider；远端可用性仍需在保存并加载 provider 后点击 `Smoke Providers` 单独探活。

## Portable Release 包说明（2026-06-17）

- 可运行 `powershell -ExecutionPolicy Bypass -File .\build_desktop_release.ps1` 生成桌面 portable zip。
- 输出位于 `release/ConsensusTranslationAgent-<version>-portable.zip`，同时生成 `release-manifest.json`。
- manifest 记录 exe 和 zip 的 SHA256、文件大小、包含文档、OCR/API/COMET 等可选外部依赖，以及当前未包含的代码签名、安装器、自动更新。
- 当前交付形态是 portable 包：解压后运行 `ConsensusTranslationAgent.exe`。正式安装器和签名仍属于后续发布工作。

## HOOK/OCR 输入插件说明（2026-06-17）

- 桌面原型新增 `Open OCR Image`：选择 `png/jpg/jpeg/bmp/webp/tif/tiff` 后，系统调用 OCR 插件提取文字并填入源文本框，随后可按普通文本运行 Agent。
- OCR 默认调用本机 `tesseract` 命令行；如果系统未安装 Tesseract，会在预检列表中显示错误，不影响 `txt/md/docx` 输入。
- 桌面原型新增 `Import Hook Text`：当前实现从剪贴板导入文本，经 `hook-buffer` 插件进入源文本框；它是受控缓冲入口，不做进程注入。
- 外部 HOOK 工具（例如 Textractor 类工具）后续可以把捕获文本写入该缓冲入口，再交给同一套术语记忆、候选翻译、裁决和续译 workflow。

## Provider Smoke 探活说明（2026-06-17）

- 桌面原型的 provider 配置区新增 `Smoke Providers` 按钮。
- 使用流程：填写并保存 Provider ID、Base URL、Model、API Key 后，点击 `Load Providers`，再点击 `Smoke Providers`。
- 若顶部 `API` 开关未开启，远端 provider smoke 会显示 `api disabled`，不会发起远端请求。
- Smoke 会对当前已加载 provider 发送一个很短的样例翻译请求，并在远端预检列表中显示 `OK` 或 `FAIL`、延迟、token、成本和译文预览。
- Smoke 不会创建正式 agent run，不会写入词库，也不会替代完整翻译质量评估；它只用于确认 endpoint、模型名和本机凭据是否能完成一次最小调用。

## 1. 软件定位

本软件是面向游戏文本与流行小说场景的中英日翻译工具，强调：

- 专有名词场景可解释性
- 多引擎候选比对
- 词库可持续进化
- 可视化流程观测

当前 V1 采用双本地引擎：

- Engine A: Marian（Opus-MT）
- Engine B: Meta NLLB-200

## 2. 理论基础与算法逻辑

### 2.1 MDWC（多维加权共识）

系统通过多维评分对候选译文进行裁决，核心维度包括：

- `token_score`：词级稳定度（术语层）
- `sentence_score`：句义与可读性
- `segment_score`：段落风格一致性
- `user_prior`：用户偏好与历史修订趋势

综合公式由权重配置驱动，输出 `final_score` 与 `decision_reason`。

### 2.2 三级粒度结构

输入在内部按词/句/段组织（Token/Sentence/Segment），便于在复杂文本中定位“仅局部词项异常”的场景。

### 2.3 契约驱动

每次任务生成统一 `TranslationJobContract`，用于承载：

- 任务身份信息
- 阶段状态（current/progress/retry/error）
- 流程追踪字段

UI 仅渲染契约与工作流输出字段，确保前后端一致。

## 3. 软件工作流

### 3.1 本地模式（local）

`ingest -> segment -> engine -> cross_check -> mdwc -> review -> finalize`

产出：

- 最终译文与分数
- 双候选比对信息
- MDWC 决策理由
- 契约快照

本版本新增运行字段：

- `domain_tags` / `domain_hits`：神话/历史/科学要素识别结果
- `decision_trace`：分值联动追踪
- `minimum_log_level`：当前有效日志级别
- `audit_exported`：是否导出审计
- `checkpoint_used` / `resume_from_stage`：恢复执行标记

### 3.2 预训练模式（pretrain）

在本地模式基础上进行词库校准和输出增强：

- 词库更新
- 验证指标字段
- 提升率字段
- 冲突与未分类项字段

本版本的 `validation_metrics` 包含：

- `term_consistency`
- `length_ratio`
- `edit_similarity`
- `overall`

并输出 `evaluation_version` 以标识评估逻辑版本。

## 4. 安装与启动

### 4.1 推荐环境

- Windows + Python 3.13（当前验证环境）
- 可访问 HuggingFace 模型下载网络

### 4.2 依赖安装

在项目根目录执行：

```powershell
E:\Ana\python.exe -m pip install -r requirements.txt
```

### 4.3 启动方式

```powershell
powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1
```

启动成功后，终端应显示：

- `deps-ok`
- `Local URL: http://localhost:8501`

## 5. 使用方法

### 5.1 打开界面

浏览器访问 `http://localhost:8501`。

### 5.2 侧栏参数

- `源语言`：下拉选择，固定为 `zh/en/ja`
- `目标语言`：下拉选择，固定为 `zh/en/ja`
- `主题（预设）`：主题下拉（`general/travel/greeting/history/science`）
- `主题（手动覆盖）`：手动输入优先级高于预设主题；为空时回退到预设主题

### 5.2.1 中文 UI 文案与契约键名

- 中文 UI 文案用于界面展示与操作引导，优先保证中文可读性。
- 契约字段键名保持英文，用于接口协议、日志与测试断言，不随界面文案翻译。
- 例如结果页显示中文说明时，底层字段仍为 `final_text`、`decision_reason`、`final_score`。

### 5.3 执行任务

- 点击 `运行本地任务`：执行本地模式
- 点击 `运行预训练任务`：执行预训练模式

### 5.3.1 三路输入融合（手动输入 + 上传覆盖）

当前 UI 在侧栏维护三组独立输入，每组都遵循“上传优先，失败回退手动”的融合策略：

1. 本地任务输入：`本地文本` + `上传本地文本（txt/md/docx）`
2. 预训练任务输入：`预训练文本` + `上传预训练文本（txt/md/docx）`
3. 预训练验证输入：`验证文本` + `上传验证文本（txt/md/docx）`

执行规则：

1. 上传成功且解析为非空文本时，执行时使用上传内容。
2. 未上传、上传为空、解析失败或依赖缺失时，自动回退到对应手动输入框。
3. 侧栏会分别显示三组“输入来源”（`upload` 或 `manual`），用于核对本次任务真实输入。

### 5.4 结果区与详情区

- 主区域只保留 `翻译结果` 面板，集中显示关键结果字段。
- 页面级明细不再占用主区域，而是放入侧栏折叠区 `页面详情与状态`（默认收起）。
- 侧栏详情中可通过 `页面` 选择查看：`config`、`monitor`、`compare`、`mdwc`、`revision`、`pretrain_report`。

### 5.5 输出面板说明（当前行为）

- 主区域固定显示 `翻译结果`，用于快速确认最终输出。
- 预训练模式下，结果面板同时展示预训练摘要字段与本地基线字段。
- 若需排障或审计，请展开侧栏 `页面详情与状态` 查看完整契约数据。

### 5.6 Confirm/Revise 复核门与词库写回

- 本地模式在产出候选后进入 `confirm/revise` 复核门：
  - `confirm`：接受当前候选并完成流程，不触发词库写回。
  - `revise`：进入修订分支，允许在最终确认前调整译文与术语。
- 词库 `lexicon` 的 writeback 仅在 revise 路径发生，即“仅在 revise 写回”；`confirm` 路径不会写入词库。
- 输入来源仍遵循上传优先与手动回退融合规则；复核门决策只影响是否进入修订与是否执行 writeback，不改变输入回退策略。

## 6. 文件与数据说明

- 词库默认路径：`%LOCALAPPDATA%\ConsensusTranslation\lexicon.json`
- 词库结构（V2）：`terms` / `phrases` / `style_rules`
- 模型缓存路径：HuggingFace 默认缓存目录（首次运行会自动下载）

## 7. 阶段边界说明

当前版本完成到第二阶段，本地模式可投入使用。

第三阶段目标（当前 UI 未开放）：

- AI 辅助模式（最多 3 模型）
- 多模型交火/投票/多轮迭代

当前 Streamlit UI 不提供第三阶段 AI 入口，属预期行为。代码层已提供 Phase-3 Agent Core 原型，用于后续桌面端优先路线：

- `learning`：学习模式，人工确认门控；未确认的词库提案不会写入正式词库。
- `self_iterative`：自迭代模式，要求训练集与验证集，最多三轮；每轮使用验证集评分，低于阈值继续，三轮后仍失败则进入人工复核。
- `self_decision`：自决策模式，由 `MetaPolicyAgent` 根据训练/验证覆盖、API 开关和预算选择学习门控或自迭代，并在 trace 中记录原因。

该原型当前服务于批量 `txt/md/docx` 文本、上下文预算续译、SQLite 词库记忆、远端调用预检、人工确认控制层与 provider adapter 验证。代码层已有 OpenAI-compatible provider 边界、本机凭据 store、provider 配置持久化、项目配置持久化、OCR 图片输入、Hook 文本缓冲输入、provider smoke 和交付诊断；真实进程注入式 hook、真实用户密钥下的远端 API 联调、安装器/签名/自动更新仍为后续任务。

桌面端原型可通过以下命令启动：

```powershell
powershell -ExecutionPolicy Bypass -File .\run_desktop_agent.ps1
```

长文本处理遵循“当前片段 + 待续片段 + 拼接核验”链路：系统先估算上下文长度，超过用户设置限制时自动切分；若单段文本本身超过限制，会继续二次切分；所有仍能放入当前上下文的片段会合并进入初始任务；当前片段完成后总结写作结构、翻译要点和前序摘要；待续片段沿用这些要点继续翻译；最后单开拼接核验任务检查段数、空段和顺序。

Agent 运行时会按 topic 从 SQLite 词库查询当前文本命中的 `terms`、`phrases`、`style_rules`，并把命中内容传给 provider。旧版 JSON 词库可导入 SQLite，后续桌面端 UI 会在此基础上提供人工确认和词库维护界面。

桌面控制器已提供审计与确认接口：可以列出历史 agent run，读取单个 run 的状态，列出待确认词库提案，确认某个 run 的正式输出状态，并按事件 ID 将词库提案写回 SQLite 正式词库表。

远端模型调用前会生成 preflight：列出将调用的远端 provider、对应上下文片段、轮次、估算输入 token、预估成本和预算风险。`require_remote_confirmation=True` 时，桌面控制器必须先确认该 preflight，随后才能执行一次实际远端调用；确认 ID 与输入文本、provider、上下文预算和模式绑定，使用后即失效。

Provider 配置保存在 SQLite `provider_configs` 表中，包含 provider id、类型、base URL、模型、credential id、估算成本和启用状态。API key 不写入该表，只通过本机加密凭据 store 按 `credential_id` 读取；桌面控制器可从 store 加载所有启用 provider。

桌面项目配置保存在 SQLite `project_profile` 表中，包含 source/target/topic/mode、上下文预算、API 开关、预算限制、远端确认开关和最近文件。默认桌面数据库路径为 `%LOCALAPPDATA%\ConsensusTranslation\agent.sqlite3`。基础 Tkinter 壳已经支持打开 `txt/md/docx` 文件、载入首个文件文本、记录最近文件和保存当前项目配置。

旧版 JSON 词库可迁移到桌面 SQLite store：

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate_legacy_lexicon.ps1
```

如需指定路径：

```powershell
powershell -ExecutionPolicy Bypass -File .\migrate_legacy_lexicon.ps1 --source .\data\lexicon.json --db "$env:LOCALAPPDATA\ConsensusTranslation\agent.sqlite3"
```

## 8. 使用须知

1. 首次运行模型下载较慢，属于正常现象。
2. 若网络受限，模型下载会失败，请先确保可访问 HuggingFace。
3. 引擎输出质量受模型覆盖方向影响，部分语对会走中转逻辑。
4. 当前 V1 重点是“可运行 + 可观察 + 可迭代”，非最终质量版本。
5. 预训练指标已从占位逻辑替换为可复现计算，但仍建议后续升级更强验证集评估体系。

## 9. 常见问题

### Q1: 终端有 `sacremoses` 提示怎么办？

这是 Marian 的建议依赖提示，可安装以提升分词兼容性：

```powershell
E:\Ana\python.exe -m pip install sacremoses
```

### Q2: 看到 HuggingFace symlink 警告是否失败？

不是失败，属于 Windows 缓存策略提示，通常不影响翻译功能。

### Q3: 为什么有时翻译速度变慢？

可能是首次加载模型或首次触发某语对模型下载。二次运行通常更快。

## 10. Phase-3 Agent 评估器说明（原型）

- 自迭代模式的验证评分现在通过可插拔 evaluator 完成。默认 evaluator 为本地 deterministic 指标，不需要联网。
- 后续可选择 COMET evaluator 或 OpenAI-compatible LLM judge evaluator；其中 LLM judge 属于远端调用，必须开启 API，并会进入远端调用 preflight。
- 远端 preflight 会把翻译 provider 和远端 evaluator 一并列出，包含上下文片段、轮次、估算 token、估算成本和预算风险。
- 当 `require_remote_confirmation=True` 时，桌面控制器必须先确认 preflight，随后才允许执行一次实际远端调用。

## 11. 长文本续译与拼接核验说明（原型）

- 长文本超过用户设置的上下文限制时，系统会先生成当前片段和待续片段。
- 当前片段完成后会形成 `translation_brief`，其中包含写作结构、翻译要点、待续策略和前序摘要。
- 待续片段会把该 brief 传给 provider，要求沿用前序术语、叙事视角、语气和段落结构。
- 全部片段完成后会创建 `stitch_and_verify` 任务，并输出结构化核验结果：分段数、空段、顺序、上下文限制和来源任务 id。

## 12. 桌面导出包说明（原型）

- 在桌面原型中运行一次 Agent 后，可点击 `Export Artifacts`。
- 导出目录会生成五类文件：最终译文 txt、续译 brief、拼接核验 JSON、分段审计 JSON、manifest JSON。
- manifest 用于复核本次任务的上下文估算、切片数量、待续片段数量、任务 id、run id、配置摘要和核验状态。
- 该导出包适合作为人工复核、后续修订和问题定位的交付材料。

## 13. Windows 桌面包构建说明（原型）

- 桌面打包依赖保存在 `requirements-desktop.txt`。
- 构建前可运行 `python -m consensus_translation.agent_packaging` 做预检。
- 构建命令：

```powershell
E:\Ana\python.exe -m pip install -r requirements-desktop.txt
powershell -ExecutionPolicy Bypass -File .\build_desktop_agent.ps1
```

- 构建成功后，桌面程序位于 `dist\ConsensusTranslationAgent\ConsensusTranslationAgent.exe`。
- 当前产物是 one-folder 桌面包；安装器、签名、自动更新仍属于后续发布工作。

## 14. Provider 设置说明（原型）

- 桌面原型顶部提供 Provider ID、Base URL、Model、API Key、Cost、Enabled 控件。
- 点击 `Save Provider` 会保存 OpenAI-compatible provider 配置。
- 点击 `Load Providers` 会加载所有已启用 provider，后续 `Run Agent` 和 `Preview Remote Calls` 会使用这些 provider。
- API key 不保存到 SQLite provider 配置表；SQLite 只保存 `credential_id`，真实密钥存入本机 credential store。
