# 工作日志（2026-05-07 第二阶段推进与本地可投用验证）

## 一、本轮目标

本轮目标是把项目推进到第二阶段可交付状态：

- 本地模式达到可投入使用（Gate-L 通过）
- 前端 UI 与后端运行态字段严格匹配（UI-Backend Contract Gate 通过）
- AI 辅助模式明确后移至第三阶段目标，当前不实现

## 二、本轮落地内容

### 1) 预训练指标真实化（M1）

- 新增可复现评估模块，替换预训练占位指标
- `validation_metrics` 由固定键集合组成：
  - `term_consistency`
  - `length_ratio`
  - `edit_similarity`
  - `overall`
- `improvement_rate` 改为基于 `overall - pretrain_baseline_overall` 计算
- 输出新增 `evaluation_version`

### 2) 词库三层结构化（M2）

- 词库存储升级为三层：`terms` / `phrases` / `style_rules`
- 保留旧数据兼容：支持从平铺旧结构迁移到新结构
- 增加主题导出接口，便于验证层级写入结果

### 3) 神话/历史/科学要素识别与联动（M3）

- 新增要素识别模块，输出：
  - `domain_tags`
  - `domain_hits`
- 本地流程中加入可追踪的分值联动（有界增益）
- 决策追踪字段 `decision_trace` 显式记录联动值

### 4) 工程化完善（M4）

- 新增环境初始化脚本：`scripts/init_env.ps1`
- 新增运维工具模块，支持：
  - 运行最小日志级别控制（环境变量）
  - 审计 JSON 导出
- 本地流程新增运维字段：
  - `minimum_log_level`
  - `audit_exported`
  - `checkpoint_used`
  - `resume_from_stage`

### 5) UI 与后端契约一致性

- `PAGE_FIELD_MAP` 继续作为页面字段契约
- `extract_page_data` 保持“缺失字段回退到 `contract.<field>`”
- 明确“显式 `None` 不覆盖”为规则，避免误回退
- 增加测试确保 UI 不暴露第三阶段 AI 控件字段

## 三、核验结果（本轮最终）

1. UI/后端匹配核验
   - 命令：`pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py`
   - 结果：`21 passed`

2. 全量测试与覆盖率（Gate-L）
   - 命令：`pytest -v --cov=src/consensus_translation --cov-report=term-missing`
   - 结果：`47 passed`
   - 覆盖率：`92%`

3. Gate-L 关键断言
   - 本地 payload 必含：`final_text/final_score/needs_review/decision_reason/contract/audit_exported`
   - Engine A / Engine B 异常路径均验证写入结构化：`error_code/error_message`

## 四、阶段结论

- 第二阶段目标已完成并通过核验：M1/M2/M3/M4 + Gate-L + UI-Backend Contract Gate
- 本地模式达到“可投入使用”标准
- AI 辅助模式继续保持第三阶段目标，不在当前代码中实现

## 四点五、预发布一致性与中文 UI 说明

- 本轮作为预发布收口，重点补充一致性说明，确保文档、测试与界面描述一致。
- UI 面向中文用户，界面文案采用中文 UI 表述，避免中英混用引起误读。
- 与此同时，运行态契约字段仍保持英文键名，以保证后端协议与测试断言稳定。

## 五、第三阶段目标（暂不推进）

1. AI 辅助模式（最多 3 模型）
   - 交火、投票、多轮迭代

2. 第二阶段后续增强（非阻塞）
   - 将预训练评估从启发式指标升级到更强验证集评估体系
   - 将断点续跑从“状态标记”扩展到“真实阶段恢复执行”

## 六、运行注意事项

- NLLB 首次运行会下载模型，首次耗时较长属正常
- Windows 下 HuggingFace 缓存可能出现 symlink 警告，不影响基本运行
- Marian tokenizer 可能提示安装 `sacremoses`，属于建议项
- 词库默认写入 `%LOCALAPPDATA%\ConsensusTranslation\lexicon.json`，部署时注意权限与路径策略

## 七、Task 3 预发布核验补录（2026-05-07）

1. 指定契约与流程用例核验
   - 命令：`pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py`
   - 结果：`25 passed, 3 warnings in 50.93s`
   - 说明：UI 契约映射、中文 UI 显示约束、本地流程 Gate-L 与异常结构化字段均通过。

2. 全量回归核验
   - 命令：`pytest -q`
   - 结果：`53 passed, 3 warnings in 57.04s`
   - 说明：当前仓库全部测试通过，未出现失败或跳过导致的阻断项。

3. 启动检查（Streamlit）
   - 命令：`powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1`
   - 启动证据：输出 `deps-ok`，并显示
     - `Local URL: http://localhost:8502`
     - `Network URL: http://192.168.5.4:8502`
   - 进程处置：验证到服务进入运行态（`JOB_STATE=Running`）后，已安全停止后台 Job，避免占用端口。

## 八、Task 3 文档与核验落盘（2026-05-07）

1. 指定测试命令核验
   - 命令：`E:\Ana\python.exe -m pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py`
   - 结果：`35 passed, 3 warnings in 40.16s`
   - 结论：UI 契约映射、上传输入解析/回退、结果面板构建、工作流关键路径全部通过。

2. 全量测试命令核验
   - 命令：`E:\Ana\python.exe -m pytest -q`
   - 结果：`63 passed, 3 warnings in 45.16s`
   - 结论：当前仓库全量用例全部通过，无失败项。

3. 启动与手工烟测（安全启动/停止）
   - 启动命令：`powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1`
   - 探活结果：`Local URL: http://localhost:8502`，HTTP `200`
   - 可见性核验：
     - 使用 Streamlit AppTest 解析元素树，侧栏检测到 `file_uploader` 元素（`UnknownElement(type='file_uploader')`），确认上传控件存在。
     - 页面检测到 `翻译结果` 子标题对应输出面板，确认输出面板存在。
   - 进程处置：核验完成后已停止后台 Job 并移除 Job 记录，未遗留占用进程。

4. 用户文档更新
   - `docs/user_manual_zh.md` 已补充“上传文件工作流（5.3.1）”与“输出面板说明（5.5）”。
   - 核心说明：上传成功时优先使用上传文本，异常或空内容时自动回退手动输入；输出面板固定可见。

## 九、Task 3 核验数据差异说明与可追溯证据（2026-05-07）

1. 同日通过数变化（Delta）说明
   - 同日块内出现 `21/47`、`25/53`、`35/63` 三组通过数，属于阶段内增量测试后的自然变化，并非回归不稳定。
   - 变化原因：Task 3 在“上传输入解析/回退”和“输出面板可见性”方向新增并细化了相关测试，用例总数随提交演进增加，因此后续块的通过总数更高。
   - 结论：通过数变化反映的是测试覆盖面扩展，不是质量下降；同日各块均保持 `0 failed`。

2. 本次补录的证据落盘位置与时间戳
   - 补录时间：`2026-05-07 08:05:51 +08:00`。
   - 证据载体：本文件第七节与第八节已记录原始命令与结果；本节提供可追溯汇总，作为本次文档修订的核验索引。
   - 追溯方式：按“命令 -> 结果 -> 事实”可回查对应条目，无需依赖外部独立日志文件。

3. 可追溯命令转录摘要（含通过数/告警数/启动事实）
   - 命令：`pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py` -> 结果：`25 passed, 3 warnings in 50.93s` -> 事实：UI 契约映射、中文 UI 显示约束、本地流程 Gate-L 与异常结构化字段核验通过（见第七节第 1 条）。
   - 命令：`pytest -q` -> 结果：`53 passed, 3 warnings in 57.04s` -> 事实：该轮全量回归无失败（见第七节第 2 条）。
   - 命令：`E:\Ana\python.exe -m pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py` -> 结果：`35 passed, 3 warnings in 40.16s` -> 事实：上传输入解析/回退与输出面板相关路径在增强后通过（见第八节第 1 条）。
   - 命令：`E:\Ana\python.exe -m pytest -q` -> 结果：`63 passed, 3 warnings in 45.16s` -> 事实：增强后全量回归仍保持无失败（见第八节第 2 条）。
    - 命令：`powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1` -> 启动事实：`deps-ok`、`Local URL: http://localhost:8502`、`Network URL: http://192.168.5.4:8502`、探活 `HTTP 200`、检测到 `file_uploader` 与 `翻译结果` 面板 -> 进程处置：验证后安全停止后台 Job（见第七节第 3 条与第八节第 3 条）。

## 十、最终收口与合并状态（2026-05-07）

- 说明：本节仅记录当日历史节点（对应先前任务的合并结果），不代表当前 `ui-restructure` 分支已合并到 `main`。
- 历史节点：文件上传功能（`txt/md/docx`）与固定输出面板在当时已完成合并。
- 历史节点核验：`pytest -q` -> `63 passed, 3 warnings`。
- 历史节点中文 UI 对齐：按钮文案与实际行为一致（`运行本地任务` / `运行预训练任务`）。

## 十一、UI 重构轮（Task 3）文档同步与回归证据（2026-05-07）

1. 用户手册行为同步
   - `docs/user_manual_zh.md` 已同步 UI 重构后的交互：
     - 语言选择改为 `zh/en/ja` 下拉
     - 主题改为“预设选择 + 手动覆盖（手动优先）”
     - 三路输入融合（本地/训练/验证），均支持“上传优先、异常回退手动”
     - 主区域仅保留 `翻译结果`，详细字段收敛到侧栏折叠区 `页面详情与状态`

2. 全量回归核验（本轮要求命令）
   - 命令：`E:\Ana\python.exe -m pytest -q`
   - 结果：`67 passed, 3 warnings in 41.64s`
   - Delta 说明：相对上一轮文档记录的 `63 passed`，本轮增加到 `67 passed`，净增 `+4`。
   - 增量来源：本轮新增/细化了 UI 重构相关测试（语言/主题交互、三路输入融合、主区与侧栏信息分层展示等），因此用例总数上升。
   - 结论补充：`63 -> 67` 反映覆盖面扩展，不是回归波动；两轮均为 `0 failed`。
   - 结论：UI 重构相关功能与既有流程在本轮全量回归中均通过，无失败项。

3. 告警说明（非阻断）
   - 两条 `SwigPyPacked/SwigPyObject` 的 `DeprecationWarning`
   - 一条 Marian tokenizer 的 `sacremoses` 建议安装提示
   - 当前均未阻断测试通过，后续按依赖升级节奏处理。
