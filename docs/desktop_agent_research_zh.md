# 桌面端 Agent 与长文本翻译工作流调研记录

## 可选运行时官方依据（2026-06-18）

- Tesseract 官方安装文档说明 Windows 版本可使用 UB Mannheim 构建，OCR engine 与语言 `traineddata` 是两部分；本项目因此把二进制和 `eng/jpn/chi_sim/chi_tra` 数据都放在 E 盘独立 runtime。来源：https://tesseract-ocr.github.io/tessdoc/Installation.html
- UB Mannheim 当前公开的 Windows 64 位构建为 Tesseract 5.5.0；本项目固定下载该版本，并使用 E 盘 7-Zip 解包，避免安装器写入默认 C 盘。来源：https://github.com/UB-Mannheim/tesseract/wiki
- Unbabel COMET 官方 README 要求 Python 3.8+，支持 `pip install unbabel-comet`、`comet-score --to_json` 以及 `download_model/load_from_checkpoint`。本项目采用 Python 3.11 sidecar 与 `Unbabel/wmt22-comet-da`，保持桌面基础包轻量。来源：https://github.com/Unbabel/COMET
- COMET 官方说明该模型覆盖简体中文、繁体中文和日文；分数适合排序与质量控制，不应被解释为绝对人工质量结论。

## HOOK/OCR 插件路线补充（2026-06-17）

- Textractor 的 README 明确其定位为 Windows 7+ / Wine 的视觉小说与游戏文本 hook 工具，并说明 host 注入 texthook、通过 pipe 和 shared memory 传回文本。这支持本项目把 HOOK 设计成桌面输入插件，而不是塞进 agent core。来源：https://github.com/Artikash/Textractor
- LunaTranslator 是视觉小说翻译器形态，说明“桌面壳 + 文本捕获 + 翻译后端”的产品路径可行。来源：https://github.com/HIllya51/LunaTranslator
- manga-image-translator 采用图片内文字识别、翻译和图像处理链路，支持把 OCR/图片翻译作为独立多模态输入插件接入。来源：https://github.com/zyddnys/manga-image-translator
- pytesseract 是 Python wrapper for Google Tesseract；Tesseract 本身也提供命令行 OCR 能力。因此本项目当前优先采用 Tesseract CLI 作为可选 OCR runtime，避免把 Pillow/pytesseract 等重型依赖硬绑到桌面基础包。来源：https://github.com/madmaze/pytesseract

设计结论：当前实现只落地受控输入插件和桌面入口。真实进程注入、游戏兼容 hook code 搜索、OCR 模型安装和图像回填仍应保持为可选外部能力，经过用户确认后接入。

## 结论

当前项目路线与已有研究和开源实践一致：桌面端负责本地输入、隐私边界和人工确认；agent core 负责候选生成、冲突裁决、记忆写回和长文本续译；多模型交火应作为受控工作流，而不是完全自治聊天。

## 相似项目

- Textractor：视觉小说文本 HOOK 工具，证明游戏文本提取可作为桌面端插件接入。
  https://github.com/Artikash/Textractor
- LunaTranslator：桌面端视觉小说翻译器，证明“桌面壳 + 文本提取 + 翻译后端”是可落地产品形态。
  https://github.com/HIllya51/LunaTranslator
- GalTransl：面向 Galgame 的自动化翻译项目，证明批量文本/项目化翻译流程有现实需求。
  https://github.com/GalTransl/GalTransl
- manga-image-translator：证明 OCR、翻译、图像回填可作为后续多模态插件路线。
  https://github.com/zyddnys/manga-image-translator

## 理论与工程依据

- NLLB：说明大规模多语机器翻译底座适合承担本地或基础候选层。
  https://arxiv.org/abs/2207.04672
- ALMA：说明 LLM 可通过翻译任务微调/提示获得强翻译能力，适合作为远端候选或审校层。
  https://arxiv.org/abs/2309.11674
- COMET：说明机器翻译质量评估应引入独立评估信号，后续可用于自迭代停止条件。
  https://aclanthology.org/2020.emnlp-main.213/
- GEMBA：说明 LLM-as-evaluator 可作为补充评估方式，但应受控使用并保留人工门控。
  https://arxiv.org/abs/2302.14520
- Multiagent Debate：说明多 agent 互评/辩论可提升复杂任务推理，但翻译场景需要成本与一致性约束。
  https://arxiv.org/abs/2305.14325
- LangGraph：其持久执行、人机协同和长任务编排思路适合本项目的续译与审计链路。
  https://docs.langchain.com/oss/python/langgraph/overview
- OpenAI Agents：其工具调用、handoff、trace 思路适合作为 provider adapter 与 agent trace 的设计参考。
  https://platform.openai.com/docs/guides/agents

## 对本项目的设计约束

1. 桌面端优先：本地文件、隐私边界、人工确认和任务审计必须在本机可运行。
2. Provider 可插拔：远端模型统一走 adapter，平台差异不进入核心工作流。
3. 上下文预算先行：长文本任务必须先估算上下文并切分，不允许一次性把全文塞入模型。
4. 续译必须继承结构：待续片段要继承前序摘要、写作结构和翻译要点。
5. 最终拼接单独核验：拼接不是字符串相加，要验证段数、空段、顺序和后续术语一致性。

## 评估器实现补充（2026-06-16）

- COMET 路线：用于机器翻译质量估计，适合作为自迭代模式中的可选强评估器；当前代码以 `CometTranslationEvaluator` 适配，避免把重型依赖写死进基础运行环境。参考：[COMET](https://aclanthology.org/2020.emnlp-main.213/)、[Unbabel COMET](https://github.com/Unbabel/COMET)。
- LLM-as-evaluator 路线：GEMBA 等研究说明可用 GPT/LLM 评估译文质量，但必须受控使用、记录理由并保留人工复核边界。当前代码以 `OpenAICompatibleJudgeEvaluator` 接入，并要求 JSON 分数与理由。参考：[GEMBA](https://arxiv.org/abs/2302.14520)。
- 工程边界：评估器被设计为可插拔模块，默认 deterministic 离线可用；COMET 与 LLM judge 都是增强链路，不作为基础桌面端启动前置条件。
