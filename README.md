# Cn-Jp Translate

中英日专项翻译工具（面向游戏文本与流行小说），当前已完成第二阶段落地：本地模式可投入使用，前后端契约字段对齐并通过自动化核验。

## 当前状态

- 分支：`main`
- 运行形态：Streamlit 本地应用
- 翻译引擎：
  - Engine A: Marian（Opus-MT）
  - Engine B: Meta NLLB-200
- 阶段结论：
  - 第二阶段已完成（M1/M2/M3/M4 + Gate-L + UI-Backend Contract Gate）
  - 第三阶段目标为 AI 辅助模式（当前不实现）

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

## 文档入口

- 工作日志：`docs/worklog_zh.md`
- 用户手册：`docs/user_manual_zh.md`
- 阶段规格：`docs/superpowers/specs/2026-05-07-phase2-realignment-and-local-go-live-design.md`
- 实施计划：`docs/superpowers/plans/2026-05-07-phase2-local-go-live-implementation-plan.md`
