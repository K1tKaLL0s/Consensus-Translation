# 共识翻译 V1 用户手册（中文）

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

- `Source Lang`：源语言（建议 `zh/en/ja`）
- `Target Lang`：目标语言（建议 `zh/en/ja`）
- `Topic`：主题标签（如 `myth`、`history`、`science`）

### 5.2.1 中文 UI 文案与契约键名

- 中文 UI 文案用于界面展示与操作引导，优先保证中文可读性。
- 契约字段键名保持英文，用于接口协议、日志与测试断言，不随界面文案翻译。
- 例如结果页显示中文说明时，底层字段仍为 `final_text`、`decision_reason`、`final_score`。

### 5.3 执行任务

- 点击 `运行本地任务`：执行本地模式
- 点击 `运行预训练任务`：执行预训练模式

### 5.3.1 上传文件工作流（新增）

1. 在侧栏使用 `上传文本文件（txt/md/docx）` 选择文件。
2. 上传成功且文件内容非空时，系统提示“文件加载成功，运行时优先使用上传文本”。
3. 若未上传文件，或上传内容为空/解析失败，系统自动回退到手动输入框文本。
4. 本地任务与预训练任务都会显示“输入来源”（`upload` 或 `manual`），便于确认实际执行文本来源。

### 5.4 查看结果

在 `Page` 下拉中选择：

- `config`：任务配置字段
- `monitor`：阶段状态与错误字段
- `compare`：候选对比字段
- `mdwc`：加权裁决字段
- `revision`：修订相关字段
- `pretrain_report`：预训练报告字段

### 5.5 输出面板说明（修复说明）

- 页面底部固定显示 `翻译结果` 输出面板。
- 无论当前选择的 `Page` 页签为何值，输出面板均可见，用于统一查看关键结果字段。
- 预训练模式下，输出面板会同时显示预训练摘要字段与本地基线结果字段。

## 6. 文件与数据说明

- 词库默认路径：`%LOCALAPPDATA%\ConsensusTranslation\lexicon.json`
- 词库结构（V2）：`terms` / `phrases` / `style_rules`
- 模型缓存路径：HuggingFace 默认缓存目录（首次运行会自动下载）

## 7. 阶段边界说明

当前版本完成到第二阶段，本地模式可投入使用。

第三阶段目标（当前未实现）：

- AI 辅助模式（最多 3 模型）
- 多模型交火/投票/多轮迭代

当前 UI 不提供第三阶段 AI 入口，属预期行为。

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
