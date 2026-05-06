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
