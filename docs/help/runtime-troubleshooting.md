# 运行时排障

开发运行时固定在 E 盘项目目录 `.runtime` 下。正式安装包运行时位于用户选择的安装目录下的 `runtime` 子目录。

诊断页会检查：

- 安装根目录和数据目录是否可写。
- Tesseract 命令是否存在、版本是否可读取。
- OCR 语言包是否包含 `eng`、`jpn`、`chi_sim`、`chi_tra`。
- COMET CLI 和模型缓存是否可用。
- Provider 配置是否完整。

如果 Tesseract 或 COMET 缺失，本地基础翻译仍可运行；OCR 和 COMET 评估功能会降级并提示修复动作。
