# Cn-Jp Translate MVP

一个面向中文到日文场景的翻译与训练 MVP，包含 API、PyQt 桌面端、Streamlit Web 端，以及浏览器插件脚手架。

## 环境准备

1. 使用 Python 3.11+。
2. 创建并激活虚拟环境：

```bash
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 配置环境变量：

```bash
cp .env.example .env
```

## Quick Start

```bash
python -m venv venv
pip install -r requirements.txt
# 配置 .env
python -m src.models.init_db
uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
streamlit run src/ui/web_app/streamlit_app.py
```

## 启动方式

推荐使用一键启动脚本（PowerShell）：

```powershell
./run.ps1 -Init
./run.ps1
./run.ps1 -Mode desktop
```

- `./run.ps1 -Init`：首次初始化（创建虚拟环境、安装依赖、初始化数据库）。
- `./run.ps1`：默认启动 API + Web（Streamlit）。
- `./run.ps1 -Mode desktop`：启动 API + PyQt 桌面端。

### 备用方式（手动启动）

如需手动排查，可分别启动：`uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload`、`streamlit run src/ui/web_app/streamlit_app.py` 或 `python -c "from src.ui.pyqt_app.main_window import run; run()"`。

## API 说明

### POST `/tasks/translate`

- 请求体
  - `text: string` 翻译文本
  - `source_declaration: string` 来源声明（必填）
- 返回体（示例）

```json
{
  "task": "translate",
  "accepted": true,
  "text_length": 12,
  "source_declaration": "教材A-第3章"
}
```

### POST `/tasks/train`

- 请求体
  - `text: string` 训练文本
  - `chunk_size: int` 分段大小，默认 4000
- 语义：训练数据采用无上限分段策略，按 `chunk_size` 切块处理。

### GET `/glossary/export?fmt=json|csv|xlsx`

- 用于词库导出，支持 `json/csv/xlsx`。

## 浏览器插件 MVP

插件位于 `extensions/browser/`，实现最小能力：

- 输入文本
- 输入来源声明
- 调用后端 `/tasks/translate`
- 展示请求结果

开发测试时请先确保 API 已在 `127.0.0.1:8000` 启动。

## 测试

```bash
pytest -q
```
