# 用户手册（中文）

## 1. 产品概览

本系统提供中文到日文任务处理的 MVP 能力：

- 翻译任务提交（必须填写来源声明）。
- 训练任务分段提交（训练无上限分段）。
- 词库导出（词库分类下载场景）。

## 2. 环境与启动

1. 创建虚拟环境：`python -m venv venv`
2. 安装依赖：`pip install -r requirements.txt`
3. 启动 API：`uvicorn src.api.main:app --reload`

可选客户端：

- PyQt：`python -c "from src.ui.pyqt_app.main_window import run; run()"`
- Streamlit：`streamlit run src/ui/web_app/streamlit_app.py`

## 3. 翻译流程

1. 输入待翻译文本。
2. 输入来源声明（例如教材名、章节、网站主题）。
3. 提交到 `/tasks/translate`。
4. 系统返回任务受理状态与文本长度信息。

## 4. 训练流程

1. 提供训练文本。
2. 设置可选 `chunk_size`（默认 4000）。
3. 提交到 `/tasks/train`。
4. 系统按分段处理并返回 `chunk_count`。

说明：训练文本总量不设硬上限，采用分段机制平滑处理。

## 5. 词库导出

- 导出接口：`/glossary/export?fmt=json|csv|xlsx`
- 词库分类下载：可按来源/主题分类后进行下载与离线管理。

## 6. 浏览器插件（MVP）

插件路径：`extensions/browser/`

- 输入框 1：文本
- 输入框 2：来源声明
- 点击提交后调用 `/tasks/translate`

如无法提交，请确认 API 服务地址与端口可访问。
