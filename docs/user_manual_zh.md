# 用户手册（中文）

## 1. 项目用途

本系统是「多智能体共识翻译 + 动态术语管理」的可运行 MVP，提供：

- 翻译任务（必须声明来源/主题）。
- 训练任务（无硬上限，按分段处理）。
- 词库导出（支持分类场景）。
- 桌面端（PyQt）与网页端（Streamlit）双入口。

## 2. 最简启动方式（推荐）

请在项目根目录 PowerShell 执行：

```powershell
.\run.ps1 -Init
```

该命令会自动完成：

1. 创建虚拟环境（若不存在）。
2. 安装依赖（若未跳过）。
3. 执行 MySQL 引导（探测 -> 建库 -> 建表）。

日常启动：

```powershell
.\run.ps1
```

桌面模式：

```powershell
.\run.ps1 -Mode desktop
```

## 3. run.ps1 参数说明

- `-Init`：执行初始化流程（venv/依赖/数据库）。
- `-Mode web|desktop|all`：
  - `web`：API + Streamlit
  - `desktop`：API + PyQt
  - `all`：全部启动
- `-SkipInstall`：初始化时跳过依赖安装。
- `-SkipDB`：初始化时跳过数据库步骤。

## 4. MySQL 引导逻辑

系统会自动读取 `.env` 中数据库配置：

- `DB_HOST`
- `DB_PORT`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`

引导行为：

1. 能连接 MySQL：自动执行 `CREATE DATABASE IF NOT EXISTS` 与 ORM 建表。
2. 不能连接：输出可读诊断（服务未启动/未安装/配置错误），并给出可执行建议。

常见提示示例：

- 服务未启动：`Start-Service MySQL80`
- 未安装：`winget install Oracle.MySQL` 或 `choco install mysql`

## 5. LLM 使用与配置

当前项目支持以下 6 种模型提供商（可在 Web UI 配置）：

- `gpt`
- `qwen`
- `kimi`
- `deepseek`
- `gemini`
- `watsonx`

### 5.1 全局配置方式（Web UI）

Web 页面支持全局 `provider + model + api_key` 配置，并持久化到本地配置文件。

配置监控窗口可执行：

1. 新增/更新配置。
2. 删除配置。
3. 刷新状态（provider、model、api_key 是否已配置、更新时间）。

### 5.2 环境变量兼容

仍兼容原有环境变量方式；当本地配置缺失时，回退环境变量读取。

原有可用 provider 包含：

- `deepseek`
- `kimi`
- `qwen`（千问）

对应环境变量：

- `DEEPSEEK_API_KEY`
- `KIMI_API_KEY`
- `QWEN_API_KEY`

若未配置 key，系统允许 Mock 回退（用于本地开发与演示）。

## 6. 业务使用流程

### 6.0 Web 文件任务（新增）

支持上传 `txt/md/docx`，并先选择用途：

1. `translate`：文件翻译（输出保持原格式）。
2. `glossary`：词库导入（自动解析 `=` `,` `tab`，失败按整行术语入库）。

`source_declaration`（来源/主题）为必填。

翻译成功后可通过下载接口获取同格式结果文件。

### 6.1 翻译流程

1. 输入待翻译文本。
2. 输入来源声明（必填，例如作品名、章节、主题）。
3. 提交 `/tasks/translate`。
4. 查看任务回执与结果。

### 6.2 训练流程

1. 提供训练文本。
2. 可选设置 `chunk_size`（默认 4000）。
3. 提交 `/tasks/train`。
4. 系统自动分段并返回分段结果。

说明：训练文本总量不设硬上限，依赖分段机制避免单次过载。

### 6.3 词库导出

- 接口：`/glossary/export?fmt=json|csv|xlsx`
- 用途：按来源/主题做分类下载与离线复核。
- 说明：该能力对应项目约束中的“词库分类下载”。

## 7. 开发逻辑（给开发者）

### 7.1 核心链路

系统核心由多智能体与编排器驱动：

1. `Agent-TEx`：术语抽取。
2. `Agent-Etym`：语境溯源分析。
3. `Agent-Gen`：多路候选生成。
4. `Agent-Arb`：仲裁评分与退避策略。
5. `MAATCSOrchestrator`：整体状态图编排。

### 7.2 持久化逻辑

- ORM 定义在 `src/models/entities.py`。
- 初始化入口 `python -m src.models.init_db`。
- 启动脚本在 `-Init` 阶段自动触发 DB 引导。

### 7.3 启动入口职责分层

- `run.ps1`：用户入口与流程编排。
- `src/tools/bootstrap_mysql.py`：数据库探测与建表执行。
- `src/core/llm_router.py`：模型提供商路由与 key 检查。

## 8. 故障排查

### 8.1 `ModuleNotFoundError: No module named 'PyQt6'`

原因：当前 Python 环境未安装 `PyQt6`。

处理：

1. 激活项目虚拟环境后安装依赖：`pip install -r requirements.txt`
2. 或直接执行 `\.\run.ps1 -Init`

### 8.2 MySQL 连接失败

排查顺序：

1. 检查 `.env` 的主机、端口、账号密码。
2. 检查 MySQL 服务是否启动。
3. 使用引导命令进行安装或启动后重试 `\.\run.ps1 -Init`。

### 8.3 端口冲突

- API 默认 `8000`
- Streamlit 默认 `8501`

若冲突，请先结束占用进程或调整启动参数（开发时可手动方式启动）。

### 8.4 文件上传类型报错

若出现 `unsupported file type`：

- 确认文件扩展名是 `txt/md/docx`。
- 避免将其他格式重命名后上传。

### 8.5 Web 进程手动启动

如需手动启动 Web：

```powershell
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
streamlit run src/ui/web_app/streamlit_app.py
```
