# 商业/开源可发布桌面翻译 Agent 设计

日期：2026-06-18
状态：已确认设计方向，待实施计划与落地

## 1. 目标

在不重写现有 Agent 后端的前提下，把当前项目交付为可安装、可卸载、可诊断、可扩展的 Windows 桌面翻译软件。软件面向中英日长文本、小说和游戏文本场景，默认离线可运行，并预留 OpenAI-compatible 远端 provider；本轮只验证远端 provider 的代码、配置、预检和前端契约，不使用真实 API key 发起请求。

最终发布物必须满足：

- 用户可在安装向导中选择安装目录。
- 可选创建桌面快捷方式，并创建开始菜单入口与卸载入口。
- Tesseract、COMET sidecar、模型和运行数据均位于安装根目录或用户明确选择的同根数据目录；本次开发和下载只使用 E 盘。
- 软件内提供快速开始、可搜索帮助、诊断说明和外部工具接洽指引。
- 能与 Textractor、LunaTranslator、GalTransl 类工作流通过受控文本、文件或本地 IPC 边界接洽，不在本轮实现未审计的进程注入。
- 发布包具备明确的软件许可证、第三方声明、模型许可证边界和隐私说明，可作为开源产品发布，也能生成排除非商业模型的商业安全构建。

## 2. 方案选择

采用“PySide6 现代桌面壳 + 现有 Python Agent 服务层 + Inno Setup 安装器”。

原因：

- PySide6 提供成熟的原生 Windows 控件、导航、对话框、无障碍基础和后续界面扩展能力，比继续扩张单文件 Tkinter 界面更适合正式桌面产品。
- 现有 `DesktopAgentController`、SQLite store、provider adapter、上下文续译、artifact、OCR 和诊断模块继续复用；迁移仅替换桌面表现层，不重写 Agent 核心。
- Inno Setup 原生支持选择安装目录、桌面/开始菜单快捷方式、按用户安装、卸载、版本升级和签名命令接入，适合生成用户熟悉的 Windows 安装体验。
- Tkinter 入口在迁移期保留为开发和回退入口，但 PySide6 成为正式发布入口。

不采用 Tauri/React 全量迁移，因为它会同时引入前端、IPC、Node/Tauri 构建和后端进程管理重构，超出“无需完全重构”的约束。

## 3. 产品信息架构与主要流程

正式桌面端采用左侧导航与主工作区：

1. **首页 / 快速开始**：显示新建项目、打开项目、最近项目、运行时状态和首次使用清单。
2. **翻译工作台**：选择输入来源、源/目标语言、主题、运行模式、训练/验证数据；显示候选、裁决理由、质量信号、人工确认和导出。
3. **项目与任务**：展示批量任务、进度、失败重试、暂停/继续、历史 run 与 artifact。
4. **词库与风格**：编辑 `terms`、`phrases`、`style_rules`，审核 Agent 提案，执行导入、导出和旧词库迁移。
5. **输入连接器**：配置普通文件、OCR 图片、剪贴板/Hook 文本、外部文件夹监听和本地 IPC 接入。
6. **Provider 与评估器**：配置本地引擎、OpenAI-compatible provider、COMET 和 evaluator；真实远端调用始终经过预检与一次性确认。
7. **诊断与运行时**：显示应用、Tesseract 语言包、COMET、模型、数据目录、provider 契约和 GUI 状态，并提供修复动作。
8. **帮助中心**：提供可搜索的快速开始、模式解释、隐私边界、常见错误、Textractor/LunaTranslator/GalTransl 接洽步骤、许可证和版本信息。

首次启动向导只收集必要信息：安装/数据位置确认、源/目标语言、输入来源、离线运行时状态和是否稍后配置远端 provider。所有步骤可跳过并在设置中重新进入。

## 4. 软件架构

### 4.1 分层

- `consensus_translation` 现有模块继续承担领域契约、候选生成、裁决、上下文续译、词库、SQLite、provider、OCR、artifact 和诊断。
- 新增 `desktop_qt` 包，按 `application`、`views`、`viewmodels`、`widgets`、`resources` 拆分；UI 只通过 controller/application service 调用后端，不直接操作 SQLite 或模型。
- 新增 release/runtime service，统一解析安装根目录、运行时根目录、数据根目录、模型缓存和日志目录。
- Tkinter 入口使用相同 application service，迁移期不再新增独有业务逻辑。

### 4.2 运行时位置

开发环境固定使用：

- `E:\Cn-Jp Translate\.runtime\Tesseract-OCR`
- `E:\Cn-Jp Translate\.runtime\comet-env`
- `E:\Cn-Jp Translate\.runtime\comet-models`

正式安装后默认使用：

- `{安装目录}\runtime\Tesseract-OCR`
- `{安装目录}\runtime\comet-env`
- `{安装目录}\runtime\comet-models`
- `{安装目录}\data`（默认按用户安装，确保可写）

若用户选择受保护目录，安装器必须请求相应权限；应用不得静默回退到 C 盘。所有下载任务先写入同根 `runtime\downloads`，校验 SHA256 后原子解包。

### 4.3 诊断分离

诊断拆成两种明确模式：

- **开发/构建诊断**：检查源码、PyInstaller、spec、构建脚本、dist 和 release。
- **用户安装诊断**：只检查已安装 exe、可写目录、runtime、语言包、COMET、模型、配置、帮助资源和 GUI 启动，不要求源码、PyInstaller 或 `dist`。

`--project-root`、`--install-root`、`--runtime-root` 和 `--data-dir` 必须贯穿同一解析对象，不能由不同模块各自推断。

## 5. 翻译引擎与许可证边界

正式发布引入 engine registry 和 release profile：

- `commercial-safe` 为默认发布配置，只启用允许商业使用的代码和模型。
- `research` 可显示 NLLB，但必须由用户确认 CC-BY-NC-4.0 边界后单独下载，不得捆绑进商业构建。
- OPUS-MT 模型逐个记录模型 ID、语言方向、许可证和归属；中文、英文、日文方向优先使用许可明确的直接或英文枢轴路线。
- COMET 代码与 `Unbabel/wmt22-comet-da` 按 Apache-2.0 使用并记录归属。
- Tesseract 及官方语言数据按其许可证记录归属。

当前 `facebook/nllb-200-distilled-600M` 为 CC-BY-NC-4.0，因此从默认商业安全 profile 移除。商业安全离线模式至少提供一条可用 OPUS-MT 翻译链；当存在直接与枢轴路线时可形成两个候选，否则退化为单候选并在 UI 中明确说明。远端 provider 配置后可作为新增候选，但本轮只做模拟与契约测试。

项目自身采用 Apache-2.0，并增加：

- `LICENSE`
- `NOTICE`
- `THIRD_PARTY_NOTICES.md`
- `MODEL_LICENSES.md`
- `PRIVACY.md`

发布前仍需由发布方对最终捆绑版本执行一次许可证复核；本设计不构成法律意见。

## 6. 外部工具接洽

输入连接器统一产出结构化 `CapturedInput`：来源类型、文本、编码、时间、外部会话 ID、文件路径和元数据。首批稳定边界为：

- 文件导入：`txt`、`md`、`docx`，并逐步扩展常用字幕/JSON 格式。
- OCR：图片文件进入 Tesseract CLI，语言包缺失时给出可执行修复动作。
- 剪贴板/Hook 文本：接收用户粘贴或外部工具复制的文本。
- 文件夹监听：外部工具将 UTF-8 文本或 JSON 写入约定目录，应用去重后进入翻译队列。
- 本地 IPC：采用仅监听 loopback 的受控 HTTP/命名管道适配器，使用随机会话令牌并限制 payload；本轮不执行目标进程注入。

帮助中心分别说明：Textractor 的文本输出/扩展路线、LunaTranslator 的文本捕获路线、GalTransl 的文件项目路线，以及本软件可接收和输出的数据格式。

## 7. 安装、升级与发布物

Inno Setup 生成按用户安装器，默认目录为用户本地程序目录，允许用户修改。安装向导提供：

- 主程序（必选）
- Tesseract 与 `eng/jpn/chi_sim/chi_tra` 语言包
- COMET sidecar 与模型（可选的大体积组件；完整离线安装包可预置）
- 桌面快捷方式（默认勾选、可取消）
- 开始菜单快捷方式、帮助和卸载入口

至少生成：

- portable ZIP
- 标准安装器
- 包含已下载本地运行时的完整离线安装器（在磁盘和许可证条件允许时）
- release manifest、SHA256 文件、第三方声明和安装验证报告

安装器脚本预留代码签名命令和 CI 参数；没有证书时明确标记为 unsigned，不伪报签名完成。升级沿用固定 AppId，保留项目数据，并允许用户选择删除数据。

## 8. 安全、隐私与错误处理

- 默认不上传训练集、验证集、词库或原文。
- API key 继续使用 Windows DPAPI，本地配置只保存 credential ID。
- 远端调用前显示 provider、模型、数据范围、估算 token/成本和预算风险，并要求一次性确认。
- loopback IPC 默认关闭，只能在设置中启用；记录端口、会话和来源，不记录凭据。
- 下载器校验来源、状态码、文件大小和 SHA256；失败时保留可重试信息，不把半成品标记为可用。
- 所有用户可见错误包含“发生了什么、影响什么、如何修复”，并可复制诊断摘要。

## 9. 验证门

完成声明必须同时具备以下新鲜证据：

1. 隔离用户目录的全量自动测试通过，直接运行测试不访问真实 `%LOCALAPPDATA%`。
2. PySide6 主流程可完成项目创建、文本/文件输入、离线翻译、人工确认、词库写回、历史查看和 artifact 导出。
3. provider 设置、预检、确认和模拟 provider smoke 通过；不使用真实 key。
4. E 盘 Tesseract 可列出并实际使用 `eng/jpn/chi_sim/chi_tra`；OCR 样例通过。
5. E 盘 COMET CLI、模型加载和小样本评分通过。
6. portable 解压根目录诊断无开发工具误报，本地 smoke 通过。
7. 安装器可选择非默认路径、创建桌面快捷方式、启动应用、运行诊断和完整卸载。
8. 安装后所有组件位于用户选择的安装根目录；除 Windows 必需的快捷方式/卸载注册信息外，不在其他盘静默创建运行时副本。
9. 内置帮助可搜索并覆盖快速开始、模式、输入连接器、provider、运行时、隐私、故障排查和许可证。
10. 发布 manifest、ZIP、安装器和核心 exe 的哈希一致；第三方和模型许可证清单与实际包内容一致。

## 10. 明确非目标

- 不使用真实远端 API key 做在线调用或质量验收。
- 不在本轮实现对游戏进程的注入、hook code 搜索或绕过保护机制。
- 不承诺机器翻译结果无需人工校对即可直接发布。
- 没有发布方代码签名证书时，不把 unsigned 安装器描述为已签名。
