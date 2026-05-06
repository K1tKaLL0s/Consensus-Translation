# 工作日志（2026-05-07 本轮重构与引擎落地）

## 一、本轮目标

本轮目标是将项目从“流程可运行但翻译引擎占位”升级为“本地双引擎可用、UI 与后端契约对齐、可验证可观测”的初步可运行状态。

本轮完成的核心方向：

- 统一并强化本地双引擎方案（Engine A: Marian / Engine B: Meta NLLB-200）
- 强化流程契约化（TranslationJobContract 全程贯穿）
- 强化 UI 动态映射（按运行态 payload 展示，不再仅显示静态字段）
- 强化健康检查与预训练输出
- 增补测试与启动可用性验证

## 二、实现内容与编程逻辑

### 1) 双本地引擎方案

- Engine A 使用 Marian（Opus-MT）
  - 引擎名：`marian-opus-mt`
  - 支持 `zh/en/ja` 归一化
  - 先尝试直连模型对（例如 `zh-en`）
  - 若无直连模型且不涉及英文直连，采用 `pivot(en)` 中转
- Engine B 使用 Meta NLLB-200
  - 引擎名：`meta-nllb-200`
  - 模型：`facebook/nllb-200-distilled-600M`
  - 通过 NLLB 语言代码映射执行翻译（`zho_Hans` / `eng_Latn` / `jpn_Jpan`）

### 2) 本地模式工作流（run_local_job）

- 流程分阶段推进：`ingest -> segment -> engine -> cross_check -> mdwc -> review -> finalize`
- 每阶段更新 `stage_status.current` 与 `stage_status.progress`
- 产出内容同时包含：
  - 最终翻译结果（`final_text` / `final_score` / `needs_review`）
  - 候选对比数据（`cand_a` / `cand_b` 等）
  - MDWC 可解释字段（`weights` / `token_score` / `decision_reason` 等）
  - `contract` 快照（用于 UI 与审计）

### 3) 预训练模式（run_pretrain_job）

- 调用本地模式生成基础结果
- 应用用户修订写入词库
- 输出校准字段：
  - `validation_metrics`
  - `improvement_rate`
  - `conflict_terms`
  - `uncategorized_terms`
- 同样输出 `contract`（结束于 `finalize`）

### 4) 词库持久化

- 词库仓储改为可落盘 JSON
- 默认路径优先使用 `%LOCALAPPDATA%\ConsensusTranslation\lexicon.json`
- 支持注入 `store_path`（便于测试与迁移）
- `apply_revision` 执行写回并返回反馈事件（`special_flag` / `user_prior_delta`）

### 5) UI 与契约一致性

- `PAGE_FIELD_MAP` 继续作为页面字段契约
- 增加 dot-path 解析和回退逻辑：
  - 先查 payload 根层
  - 根层缺失时查 `contract.<field>`
- 增加侧栏执行入口：可在 UI 内触发 local/pretrain 任务并展示对应页面数据

### 6) 健康检查

- `l1_process`: 检查 Streamlit 可导入状态
- `l2_service`: 检查工作流执行能力（异常时返回失败详情）
- `l3_task`: 端到端最小任务冒烟并回报结果详情

## 三、验证结果（本轮最新）

执行命令与结果如下：

1. 全量测试 + 覆盖率（Gate-L 验证）
   - 命令：`pytest -v --cov=src/consensus_translation --cov-report=term-missing`
   - 结果：`46 passed`
   - 总覆盖率：`92%`
   - Gate-L 关键断言：本地 payload 必含 `final_text/final_score/needs_review/decision_reason/contract/audit_exported`，并验证错误路径写入结构化 `error_code/error_message`

2. 启动冒烟
   - 命令：`powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1`
   - 结果：输出 `deps-ok`，并给出本地访问地址（`http://localhost:8501`）

3. 双引擎翻译冒烟
   - Marian：`Hello, world.`
   - NLLB：`Hello, world.`

## 四、阶段推进（2026-05-07）

- 第二阶段目标重排完成，AI 辅助模式保持第三阶段范围，不在本阶段推进实现。
- UI-Backend Contract Gate 通过：UI 页面字段映射与后端 payload/contract 回退链路对齐（含 `stage_status.*` 监控字段）。
- Local Go-Live Gate（Gate-L）通过：本地模式必需字段与结构化错误处理均由自动化测试覆盖并通过。

## 五、待完成项目（下一阶段）

1. 预训练指标真实化
   - 当前 `validation_metrics` 为占位逻辑，需替换为基于验证集的真实计算

2. 主题词库进化增强
   - 当前为基础词条写入，尚未形成“短语/固定句式/写作逻辑”三层结构化索引

3. 神话/历史/科学要素识别器
   - 当前仅预留域标签，需补充实体识别与权重联动机制

4. AI 辅助模式（最多 3 模型）
   - 当前仅保留架构接口，尚未实现真实交火、投票与多轮迭代

5. 工程化完善
   - 增加环境初始化脚本
   - 增加日志分级与任务审计导出
   - 增加错误恢复与断点续跑能力

## 六、运行注意事项

- NLLB 首次运行会下载模型，首次耗时较长属正常
- Windows 下 HuggingFace 缓存可能提示 symlink 警告，不影响基本运行
- Marian tokenizer 可能提示安装 `sacremoses`，属于建议项
- 词库默认写入 `%LOCALAPPDATA%`，部署时注意账户权限与路径策略
