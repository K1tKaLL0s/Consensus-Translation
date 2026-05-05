# 工作日志（Task12）

## 任务范围

- 补齐项目对外文档包。
- 创建浏览器插件 MVP 脚手架（输入文本+来源，调用 `/tasks/translate`）。

## 已完成项

1. 新增 `README.md`，覆盖环境准备、启动方式、API 说明、PyQt/Streamlit 运行。
2. 新增文档：
   - `docs/cost_strategy.md`
   - `docs/user_manual_zh.md`
   - `docs/presentation_script_zh.md`
3. 新增插件脚手架：
   - `extensions/browser/manifest.json`
   - `extensions/browser/popup.html`
   - `extensions/browser/popup.js`
4. 新增测试 `tests/test_task12_docs_and_plugin_scaffold.py`，用于校验关键文档与插件入口要求。

## 关键约束记录

- 翻译入口必须包含**来源声明**字段。
- 词库能力在文档中明确为**词库分类下载**。
- 训练能力在文档中明确为**训练无上限分段**策略。

## 后续建议

- 增加插件配置项（API Base URL 可配置）。
- 为文档补充 API 错误码表和截图。
