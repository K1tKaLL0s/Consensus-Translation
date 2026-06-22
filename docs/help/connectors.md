# 连接器

本软件不注入第三方进程，也不复制第三方 GPL 项目代码。推荐通过安全的文本边界对接现有工具。

## Textractor

Textractor 可把游戏或应用中的 hook 文本输出到剪贴板、扩展、管道或文件。推荐做法是让 Textractor 或其扩展把文本写入一个 UTF-8 文件夹收件箱，本软件的“输入连接器”页面读取该目录中的 `.txt`、`.md` 或 `.json` 文件。

JSON 文件可使用如下结构：

```json
{"text": "待翻译文本", "source": "Textractor"}
```

读取后文件会移动到 `archive` 目录；无法解析的文件会进入 `error` 目录。

## LunaTranslator

LunaTranslator 用户可通过剪贴板或文件输出对接。剪贴板方式适合少量文本，文件夹收件箱适合长文本、日志式文本或需要审计的输入。

## GalTransl

GalTransl 项目建议通过项目文件交换：导出待翻译文本为 UTF-8 文本或 JSON，放入收件箱；翻译完成后从工作台导出结果和 manifest，再由用户或脚本导回原项目。

## OCR 与图片

OCR 连接器默认依赖安装目录或 E 盘开发运行时中的 Tesseract。日文、简体中文、繁体中文和英文语言包缺失时，诊断页会提示需要补齐的语言。
