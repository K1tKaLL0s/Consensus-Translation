# 工作日志（2026-05-07 第二阶段推进与本地可投用验证）
## 三十二、商业/开源桌面版最终发布验证（2026-06-19）
1. 最终构建产物
   - Qt one-folder：`dist\ConsensusTranslationAgent\ConsensusTranslationAgent.exe`，大小 `7363035` 字节，SHA256 `f87c17d501ce6d0fd1867c22c1811b5043d4e6457d82b55f90923c3c1f933024`。
   - Portable zip：`release\ConsensusTranslationAgent-2026.06.19-portable.zip`，大小 `61342853` 字节，SHA256 `00c7230a2376a141028dfb12f7679b99783f98377a9a93c3dd4a078b93cb4778`。
   - 标准安装包：`release\ConsensusTranslationAgent-Setup-standard.exe`，大小 `44050887` 字节，SHA256 `f1a7bcd35d17175a36be1fd92c9e01e1edbb24246246ef72e0beff5468ddfad9`。
   - Full runtime 安装包：`release\ConsensusTranslationAgent-Setup-full.exe`，大小 `5906539` 字节，SHA256 `ef677563f67e627ed1325c012f486e517f78af989e6b05f056312ed950aada2d`。
   - Full runtime 分卷：`release\ConsensusTranslationAgent-Setup-full-1.bin`，大小 `1916638828` 字节，SHA256 `a429496fcc62fbc8fbab3915680fc4c7d61d334fd985c52cfd46f61bb7dd992a`。
   - Release manifest：`release\ConsensusTranslationAgent-2026.06.19-portable\release-manifest.json`，已记录 commercial-safe profile、exe、zip、standard installer、full installer 和 full 分卷 hash；runtime verification 状态为 `ok`。
2. 最终自动化验证
   - 全量测试：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp .pytest_tmp_runtime\final-release-after-review-fixes`，结果 `240 passed, 2 warnings in 201.07s`；warning 仍为既有 SWIG `SwigPyPacked/SwigPyObject` deprecation。
   - E 盘 runtime：`E:\Ana\python.exe scripts\verify_optional_runtimes.py --runtime-root 'E:\Cn-Jp Translate\.runtime'`，结果 `runtime verification: ok`。
   - Source acceptance：`powershell -ExecutionPolicy Bypass -File .\run_desktop_acceptance.ps1 -OutputDir '.acceptance\source-final'`，结果 `local acceptance: ok`、`verification: passed`。
   - Portable packaged diagnostics：最新 `dist\ConsensusTranslationAgent\ConsensusTranslationAgent.exe --diagnostics --diagnostics-mode installed ...`，退出码 `0`。
   - Portable packaged local smoke：最新 `dist\ConsensusTranslationAgent\ConsensusTranslationAgent.exe --local-smoke ...`，退出码 `0`。
   - Full installer acceptance：`scripts\verify_installed_release.ps1 -InstallerPath release\ConsensusTranslationAgent-Setup-full.exe -InstallDir E:\Cn-Jp Translate\.acceptance\installed-final-full`，结果 `installed-release-verification=ok`，并已静默卸载。
   - Full installed diagnostics：`desktop_install=ok`、`ocr_tesseract=ok`、`comet_runtime=ok`、`provider_configs=warning`、`gui_smoke=warning`；warning 均为未配置真实远端 provider 与人工 GUI 状态，不是功能缺失。
   - 可见 GUI smoke：启动最新 packaged exe，进程保持运行 8 秒，`CloseMainWindow=True` 后关闭。
3. 设计验证门逐项审计
   - 门 1：隔离用户目录的全量测试通过；测试 basetemp 位于 `.pytest_tmp_runtime\final-release-after-review-fixes`，不依赖真实 `%LOCALAPPDATA%`。
   - 门 2：PySide6 主流程由 `tests/test_desktop_qt_workflows.py`、`tests/test_desktop_qt_shell.py`、`tests/test_desktop_qt_help.py` 覆盖，并通过 source/packaged smoke 验证离线翻译和 artifact 输出。
   - 门 3：provider 设置、预检、确认和模拟 smoke 由 `tests/test_desktop_agent_app.py`、`tests/test_agent_provider_smoke.py`、`tests/test_desktop_qt_workflows.py` 覆盖；默认 provider smoke 不会触发真实远端调用，需显式 `allow_live_remote=True` 才允许使用 API key 联调。
   - 门 4：Tesseract `eng/jpn/chi_sim/chi_tra` 语言包和生成图片 OCR fixture 由 `scripts/verify_optional_runtimes.py` 验证通过。
   - 门 5：COMET CLI、`Unbabel/wmt22-comet-da` 模型加载和小样本评分由同一 runtime verifier 验证通过；安装包使用可搬迁的 `runtime\comet-score.cmd` 包装器调用 `python -m comet.cli.score`。
   - 门 6：portable packaged diagnostics 和 local smoke 均退出码 `0`；diagnostics 不要求开发工具链。
   - 门 7：安装器支持非默认 E 盘路径、desktop shortcut task、启动应用、运行 diagnostics/local smoke 和完整卸载；`installed-release-verification.json` 记录快捷方式与 `UninstallString`。
   - 门 8：Full 安装后 runtime 位于用户选择的安装根目录 `...\installed-final-full\runtime`；已验证安装后存在可搬迁 `runtime\comet-score.cmd`，且不会安装绑定开发机绝对路径的 `runtime\comet-env\Scripts\comet-score.exe`；除桌面/开始菜单快捷方式和卸载注册信息外，未静默创建其他运行时副本。
   - 门 9：内置帮助由 `docs/help/*.md` 与 PySide6 Help 页面提供，覆盖快速开始、输入连接器、provider、runtime troubleshooting、隐私和许可证。
   - 门 10：release manifest 记录 exe、zip、standard installer、full installer 和分卷 hash；许可证边界见 `LICENSE`、`MODEL_LICENSES.md`、`THIRD_PARTY_NOTICES.md`、`PRIVACY.md` 和 `docs/release_checklist_zh.md`。
4. 发布边界
   - 真实远端 provider/API key 未运行，符合本轮约束；代码层和前端层已完成配置、预检、确认、禁用保护和 smoke 测试路径。
   - 代码审查硬化项已落地：COMET runtime 可搬迁、Qt 安装态 diagnostics 默认使用 `installed` 模式、provider smoke 默认禁止真实远端调用、发布脚本按 C→E 顺序查找 Python，并自动记录 standard/full installer。
   - 当前安装包未签名；正式商业分发前需补代码签名、干净构建机复核和真实 provider 联调。

## 三十一、E 盘外部运行时与真实数据安全闭环（2026-06-18）

1. 代码与 UI
   - 新增 `agent_runtime.py`，支持项目 runtime settings、C→E 工具发现和 COMET 模型缓存解析。
   - 新增 `ExternalCometTranslationEvaluator`，通过 `comet-score.exe` sidecar 调用 COMET，基础桌面包继续排除 PyTorch/Transformers。
   - 训练/验证集已从桌面 profile 贯通至 context workflow、agent workflow 与 provider request。
   - 桌面 UI 新增训练/验证集、evaluator、Tesseract、OCR language、COMET command/model/cache 设置。
   - 新增 `Upload Training` 安全门；默认不向远端 provider 上传训练集，preflight 显示 data scopes，并将训练/验证摘要绑定到一次性 confirmation ID。
   - 新增 packaged `--diagnostics` CLI 与 JSON report；`--data-dir` 支持把桌面数据库和凭据位置显式放到 E 盘。
2. E 盘运行时
   - 新增 `install_optional_runtimes.ps1`，强制下载、环境和模型缓存位于 E 盘。
   - Tesseract 5.5.0 安装包已下载至 `E:\Cn-Jp Translate\.runtime\downloads`，并通过 `E:\7-Zip\7z.exe` 解包至项目 `.runtime\Tesseract-OCR`。
   - `eng/jpn/chi_sim/chi_tra` 语言包已下载至 E 盘 `.runtime\Tesseract-OCR\tessdata`，生成图片 OCR fixture 已通过。
   - 真实 CLI 与 `OcrImageInputPlugin` 均识别测试图片为 `HELLO 123`，无 warning。
   - COMET Python 3.11 sidecar、`Unbabel/wmt22-comet-da` 模型和底层 Hugging Face/Transformers/Torch 缓存均固定在 E 盘 `.runtime\comet-*` 下；样例评分验证通过。
   - Windows 安装器曾忽略目标路径并在 C 盘生成副本；因高权限用量限制，官方卸载器清理仍待权限恢复后完成。项目 runtime settings 已显式固定使用 E 盘副本。
   - 新增 `scripts/verify_optional_runtimes.py`，当前完整验证结果为 `runtime verification: ok`，报告写入 `.runtime/runtime-verification.json`。
3. TDD 记录
   - 新增运行时发现、外部 COMET CLI、训练/验证传递、项目持久化、UI 控件、数据上传门和安装脚本测试。
   - 当前相关聚焦回归：`50 passed`、`45 passed` 等批次均通过。
   - 全量回归：`193 passed, 2 warnings in 62.72s`；warning 仍为既有 SWIG deprecation warning。

## 三十、桌面 Agent 本地验收 Smoke（2026-06-17）
1. 能力补充
   - 新增 `agent_acceptance.py`，提供无远端 API、无 OCR、无 COMET 的离线本地验收。
   - 验收任务使用本地 echo provider，强制触发上下文切分，覆盖初始翻译、待续翻译、续译 brief、拼接核验和 artifact 导出。
   - `DesktopAgentController` 新增 `run_local_acceptance`。
   - Tkinter 原型新增 `Run Local Smoke` 按钮，结果显示在预检列表中。
   - `agent_acceptance.py` 新增 CLI，支持输出机器可读 JSON report。
   - `desktop_agent_app.py` 支持 `--local-smoke`，可在 packaged exe 中不打开 GUI 执行本地验收。
   - 新增 `run_desktop_acceptance.ps1`，源码环境可一键运行本地验收并写出 report。
   - `packaging/desktop_agent.spec` 增加 `consensus_translation.agent_acceptance` hidden import。
2. TDD 验证记录
   - 先新增 `tests/test_agent_acceptance.py` 和桌面控制器/UI 断言，首次聚焦运行得到预期红灯：`ModuleNotFoundError: No module named 'consensus_translation.agent_acceptance'`。
   - 实现后聚焦回归：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime' tests\test_agent_acceptance.py tests\test_desktop_agent_app.py tests\test_desktop_packaging.py`
   - 当前结果：`24 passed in 1.51s`。
   - 补充 CLI 与脚本后，聚焦回归：`34 passed in 2.20s`。
   - 全量回归：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime'`
   - 当前结果：`178 passed, 2 warnings in 137.96s`；警告为既有 SWIG deprecation warning。
   - 打包预检：`desktop-packaging-preflight-ok`。
   - Release 脚本重新生成 portable zip，当前 `exe_sha256`: `f0f4eb9ece5be916f9dbfe2777085c9442c6290e2a7533c69f99fdc01f9d1cec`。
   - 当前 `zip_sha256`: `692b331c0d2cada510fcab6bdc8f54b1e595b09b6dd596c68847f12c1314da93`。
   - 手动运行本地验收 smoke：`local acceptance: ok`，`verification: passed`，`slices=3`，`pending=1`，任务包含 `initial_translation`、`continuation_translation`、`stitch_and_verify`。
   - 打包产物运行 `ConsensusTranslationAgent.exe --local-smoke`：`EXITCODE=0`，report 写出且 `ok=true`，`verification.status=passed`。
3. 边界说明
   - 本地验收 smoke 证明核心 agent workflow 能离线跑通，不证明真实远端 provider、真实 OCR runtime、COMET 评分或 GUI 手工体验已经验收。

## 二十九、桌面 Agent 交付诊断与前后端匹配核验（2026-06-17）
1. 能力补充
   - 新增 `agent_diagnostics.py`，定义桌面交付诊断报告，覆盖打包 preflight、release exe、Tesseract OCR、COMET runtime、provider 配置/凭据和 GUI 手工 smoke。
   - `DesktopAgentController` 新增 `run_diagnostics`，复用同一套后端诊断。
   - Tkinter 原型新增 `Run Diagnostics` 按钮，诊断结果显示在预检列表中。
   - `packaging/desktop_agent.spec` 增加 `consensus_translation.agent_diagnostics` hidden import，保证桌面 exe 能携带诊断模块。
2. 边界说明
   - 打包/release 缺失属于 `error`。
   - Tesseract、COMET、远端 provider 凭据、GUI 手工启动属于外部或可选环境条件，缺失时记为 `warning`。
   - 该诊断不替代真实 API 联调、真实 OCR 运行时验收、真实 GUI 手工 smoke 或翻译质量验收。
3. TDD 验证记录
   - 先新增 `tests/test_agent_diagnostics.py`、桌面控制器断言和 PyInstaller hidden import 断言，首次聚焦运行得到预期红灯：`ModuleNotFoundError: No module named 'consensus_translation.agent_diagnostics'`。
   - 实现后聚焦回归：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime' tests\test_agent_diagnostics.py tests\test_desktop_agent_app.py tests\test_desktop_packaging.py`
   - 当前结果：`25 passed in 1.53s`。
   - 全量回归：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime'`
   - 当前结果：`172 passed, 2 warnings in 72.20s`；警告为既有 SWIG deprecation warning。
   - 打包预检：设置 `PYTHONPATH=src` 后运行 `E:\Ana\python.exe -m consensus_translation.agent_packaging`，结果为 `desktop-packaging-preflight-ok`。
   - Release 脚本：`powershell -ExecutionPolicy Bypass -File .\build_desktop_release.ps1`，生成 `release\ConsensusTranslationAgent-2026.06.17-portable.zip`。
   - 当前 `exe_sha256`: `891e2ba7a237d319d25e520cf6b45f8cdebd5240732ae5a8b6555a7d96629ac9`。
   - 当前 `zip_sha256`: `0c31f2bcadd2672d83ec3a72c4e15453069c69330b2713371bddbfa1271fab14`。
   - zip 内 `release-manifest.json` 不记录自身 zip hash；外部 sidecar manifest 记录最终 zip hash，避免自引用 hash 不一致。
   - 当前真实环境诊断：`diagnostics: warning | ok=2 | warning=4 | error=0`；warning 来源为未安装 Tesseract、未安装 COMET、未附加 provider store、GUI 仍需手工 smoke。

## 二十八、Portable Release 包与校验清单（2026-06-17）

1. 能力补充
   - 新增 `agent_release.py`，提供桌面 release preflight、manifest 生成、exe/zip SHA256 计算和 portable zip 打包。
   - 新增 `build_desktop_release.ps1`，先构建 PyInstaller one-folder 产物，再生成 portable release 包。
   - `.gitignore` 增加 `release/`，避免 release 产物进入版本控制。

2. Manifest 内容
   - 记录 app 名称、版本、渠道、创建时间、入口 exe。
   - 记录 `ConsensusTranslationAgent.exe` 和 release zip 的 SHA256 与文件大小。
   - 记录包含的 README、用户手册、桌面 agent core 说明。
   - 记录可选外部依赖：Tesseract OCR、OpenAI-compatible provider、COMET runtime。
   - 明确未包含项：代码签名、安装器、自动更新。

3. TDD 验证记录
   - 先新增 `tests/test_agent_release.py`，运行得到预期红灯：`ModuleNotFoundError: No module named 'consensus_translation.agent_release'`。
   - 实现后运行：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime' tests/test_agent_release.py`
   - 结果：`3 passed in 0.58s`。
   - 聚焦回归：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime' tests/test_agent_release.py tests/test_desktop_packaging.py tests/test_desktop_agent_app.py tests/test_agent_input_plugins.py tests/test_agent_provider_smoke.py`
   - 结果：`32 passed in 1.21s`。
   - 全量回归：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime'`
   - 结果：`167 passed, 2 warnings in 70.90s`；警告仍为既有 SWIG deprecation warning。
   - Release 脚本：`powershell -ExecutionPolicy Bypass -File .\build_desktop_release.ps1`
   - 结果：生成 `release\ConsensusTranslationAgent-2026.06.17-portable.zip`，大小 `27056964` 字节。
   - `exe_sha256`: `973f468c4b5c77078c3d1599340561d9894e57f356a5619793dd5af3c6691548`。
   - `zip_sha256`: `202ccbe46b142f33d3c3a3d3bd1bed3cf3f778963fe94915b2146b18de294af2`。
   - zip 条目核验确认包含 `ConsensusTranslationAgent/ConsensusTranslationAgent.exe`、`README.md`、`docs/user_manual_zh.md`、`docs/desktop_agent_core_zh.md` 和 `release-manifest.json`。

## 二十七、桌面 HOOK/OCR 输入插件入口（2026-06-17）

1. 能力补充
   - 新增 `agent_input_plugins.py`，提供 `CapturedInput`、`InputPluginRegistry`、`OcrImageInputPlugin` 和 `HookTextBufferPlugin`。
   - OCR 插件支持 `png/jpg/jpeg/bmp/webp/tif/tiff`，默认调用本机 Tesseract CLI，也支持注入自定义 OCR 函数。
   - Hook 插件当前是安全文本缓冲入口，不执行进程注入；外部 hook 工具或剪贴板文本可进入同一 agent workflow。

2. 桌面入口
   - `DesktopAgentController` 新增 `capture_plugin_input`、`translate_plugin_input` 和 `capture_hook_text`。
   - Tkinter 原型新增 `Open OCR Image` 与 `Import Hook Text` 按钮。
   - OCR/HOOK 输入会进入现有上下文估算、术语记忆、候选翻译、裁决、续译和审计链路。

3. 调研依据
   - Textractor 证明游戏/视觉小说文本 hook 是独立桌面输入能力，且涉及进程注入、pipe 和 shared memory，必须与 agent core 解耦。
   - LunaTranslator 证明“桌面壳 + 文本捕获 + 翻译后端”的产品形态可行。
   - manga-image-translator 和 pytesseract/Tesseract 证明 OCR/图片翻译适合作为可选输入插件，不应硬绑进基础桌面包。

4. TDD 验证记录
   - 先新增 `tests/test_agent_input_plugins.py`、桌面控制器用例和打包 spec 断言，运行聚焦测试得到预期红灯：`ModuleNotFoundError: No module named 'consensus_translation.agent_input_plugins'`。
   - 实现后运行：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime' tests/test_agent_input_plugins.py tests/test_desktop_agent_app.py tests/test_desktop_packaging.py`
   - 结果：`25 passed in 1.09s`。
   - 扩展聚焦回归：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime' tests/test_agent_input_plugins.py tests/test_agent_inputs.py tests/test_desktop_agent_app.py tests/test_desktop_packaging.py tests/test_agent_continuation.py tests/test_agent_workflows.py`
   - 结果：`43 passed in 2.68s`。
   - 全量回归：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime'`
   - 结果：`164 passed, 2 warnings in 125.49s`；警告仍为既有 SWIG deprecation warning。
   - 打包预检：`E:\Ana\python.exe -m consensus_translation.agent_packaging` -> `desktop-packaging-preflight-ok`。
   - 桌面构建：`powershell -ExecutionPolicy Bypass -File .\build_desktop_agent.ps1` 成功，当前 exe 时间戳为 `2026-06-17 17:36:08`，大小 `7316207` 字节。
   - PyInstaller xref 已包含 `consensus_translation.agent_input_plugins`。

## 二十六、桌面 Provider Smoke 探活入口（2026-06-17）

1. 能力补充
   - 新增 `agent_provider_smoke.py`，定义 `ProviderSmokeResult`、`smoke_test_provider` 和 `format_provider_smoke_lines`。
   - Smoke 使用 `ProviderRequest` 发送最小样例翻译请求，返回 provider id、成功状态、译文预览、延迟、成本、token、warning 和错误信息。
   - provider 失败时不向上抛出异常，而是返回 `ok=False` 与错误说明，便于桌面端展示和联调排障。
   - 当 `api_enabled=False` 且 provider 标记为远端 API 时，Smoke 返回 `api disabled`，不会调用 provider。

2. 桌面入口
   - `DesktopAgentController` 新增 `smoke_test_providers`，按当前 source/target/topic 对已加载 provider 逐个探活。
   - Tkinter 原型新增 `Smoke Providers` 按钮，结果显示在远端预检列表中。
   - Smoke 不创建正式 agent run，不写入词库，也不替代完整翻译质量验收。

3. TDD 验证记录
   - 先新增 `tests/test_agent_provider_smoke.py` 与桌面控制器断言，运行聚焦测试得到预期红灯：`ModuleNotFoundError: No module named 'consensus_translation.agent_provider_smoke'`。
   - 实现后运行：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime' tests/test_agent_provider_smoke.py tests/test_desktop_agent_app.py`
   - 补充 API 关闭保护后，结果更新为：`17 passed in 1.02s`。

4. 本轮回归与打包记录
   - 聚焦回归：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime' tests/test_agent_provider_smoke.py tests/test_agent_providers.py tests/test_agent_provider_config.py tests/test_desktop_agent_app.py tests/test_desktop_packaging.py`
   - 结果：`29 passed in 1.77s`。
   - 全量回归：`E:\Ana\python.exe -m pytest -q -p no:cacheprovider --basetemp '.pytest_tmp_runtime'`
   - 结果：`157 passed, 2 warnings in 109.22s`；警告为既有 SWIG deprecation warning。
   - 打包预检：`E:\Ana\python.exe -m consensus_translation.agent_packaging` -> `desktop-packaging-preflight-ok`。
   - 桌面构建：`powershell -ExecutionPolicy Bypass -File .\build_desktop_agent.ps1` 成功，刷新产物 `dist\ConsensusTranslationAgent\ConsensusTranslationAgent.exe`，当前 exe 时间戳为 `2026-06-17 14:42:05`，大小 `7310787` 字节。
   - PyInstaller xref 已包含 `consensus_translation.agent_provider_smoke`。
   - 本轮 GUI 启动 smoke 因提权启动被系统拒绝，未作为完成证据；当前只记录构建成功与产物刷新。

## 一、本轮目标

本轮目标是把项目推进到第二阶段可交付状态：

- 本地模式达到可投入使用（Gate-L 通过）
- 前端 UI 与后端运行态字段严格匹配（UI-Backend Contract Gate 通过）
- AI 辅助模式明确后移至第三阶段目标，当前不实现

## 二、本轮落地内容

### 1) 预训练指标真实化（M1）

- 新增可复现评估模块，替换预训练占位指标
- `validation_metrics` 由固定键集合组成：
  - `term_consistency`
  - `length_ratio`
  - `edit_similarity`
  - `overall`
- `improvement_rate` 改为基于 `overall - pretrain_baseline_overall` 计算
- 输出新增 `evaluation_version`

### 2) 词库三层结构化（M2）

- 词库存储升级为三层：`terms` / `phrases` / `style_rules`
- 保留旧数据兼容：支持从平铺旧结构迁移到新结构
- 增加主题导出接口，便于验证层级写入结果

### 3) 神话/历史/科学要素识别与联动（M3）

- 新增要素识别模块，输出：
  - `domain_tags`
  - `domain_hits`
- 本地流程中加入可追踪的分值联动（有界增益）
- 决策追踪字段 `decision_trace` 显式记录联动值

### 4) 工程化完善（M4）

- 新增环境初始化脚本：`scripts/init_env.ps1`
- 新增运维工具模块，支持：
  - 运行最小日志级别控制（环境变量）
  - 审计 JSON 导出
- 本地流程新增运维字段：
  - `minimum_log_level`
  - `audit_exported`
  - `checkpoint_used`
  - `resume_from_stage`

### 5) UI 与后端契约一致性

- `PAGE_FIELD_MAP` 继续作为页面字段契约
- `extract_page_data` 保持“缺失字段回退到 `contract.<field>`”
- 明确“显式 `None` 不覆盖”为规则，避免误回退
- 增加测试确保 UI 不暴露第三阶段 AI 控件字段

## 三、核验结果（本轮最终）

1. UI/后端匹配核验
   - 命令：`pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py`
   - 结果：`21 passed`

2. 全量测试与覆盖率（Gate-L）
   - 命令：`pytest -v --cov=src/consensus_translation --cov-report=term-missing`
   - 结果：`47 passed`
   - 覆盖率：`92%`

3. Gate-L 关键断言
   - 本地 payload 必含：`final_text/final_score/needs_review/decision_reason/contract/audit_exported`
   - Engine A / Engine B 异常路径均验证写入结构化：`error_code/error_message`

## 四、阶段结论

- 第二阶段目标已完成并通过核验：M1/M2/M3/M4 + Gate-L + UI-Backend Contract Gate
- 本地模式达到“可投入使用”标准
- AI 辅助模式继续保持第三阶段目标，不在当前代码中实现

## 四点五、预发布一致性与中文 UI 说明

- 本轮作为预发布收口，重点补充一致性说明，确保文档、测试与界面描述一致。
- UI 面向中文用户，界面文案采用中文 UI 表述，避免中英混用引起误读。
- 与此同时，运行态契约字段仍保持英文键名，以保证后端协议与测试断言稳定。

## 五、第三阶段目标（暂不推进）

1. AI 辅助模式（最多 3 模型）
   - 交火、投票、多轮迭代

2. 第二阶段后续增强（非阻塞）
   - 将预训练评估从启发式指标升级到更强验证集评估体系
   - 将断点续跑从“状态标记”扩展到“真实阶段恢复执行”

## 六、运行注意事项

- NLLB 首次运行会下载模型，首次耗时较长属正常
- Windows 下 HuggingFace 缓存可能出现 symlink 警告，不影响基本运行
- Marian tokenizer 可能提示安装 `sacremoses`，属于建议项
- 词库默认写入 `%LOCALAPPDATA%\ConsensusTranslation\lexicon.json`，部署时注意权限与路径策略

## 七、Task 3 预发布核验补录（2026-05-07）

1. 指定契约与流程用例核验
   - 命令：`pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py`
   - 结果：`25 passed, 3 warnings in 50.93s`
   - 说明：UI 契约映射、中文 UI 显示约束、本地流程 Gate-L 与异常结构化字段均通过。

2. 全量回归核验
   - 命令：`pytest -q`
   - 结果：`53 passed, 3 warnings in 57.04s`
   - 说明：当前仓库全部测试通过，未出现失败或跳过导致的阻断项。

3. 启动检查（Streamlit）
   - 命令：`powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1`
   - 启动证据：输出 `deps-ok`，并显示
     - `Local URL: http://localhost:8502`
     - `Network URL: http://192.168.5.4:8502`
   - 进程处置：验证到服务进入运行态（`JOB_STATE=Running`）后，已安全停止后台 Job，避免占用端口。

## 八、Task 3 文档与核验落盘（2026-05-07）

1. 指定测试命令核验
   - 命令：`E:\Ana\python.exe -m pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py`
   - 结果：`35 passed, 3 warnings in 40.16s`
   - 结论：UI 契约映射、上传输入解析/回退、结果面板构建、工作流关键路径全部通过。

2. 全量测试命令核验
   - 命令：`E:\Ana\python.exe -m pytest -q`
   - 结果：`63 passed, 3 warnings in 45.16s`
   - 结论：当前仓库全量用例全部通过，无失败项。

3. 启动与手工烟测（安全启动/停止）
   - 启动命令：`powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1`
   - 探活结果：`Local URL: http://localhost:8502`，HTTP `200`
   - 可见性核验：
     - 使用 Streamlit AppTest 解析元素树，侧栏检测到 `file_uploader` 元素（`UnknownElement(type='file_uploader')`），确认上传控件存在。
     - 页面检测到 `翻译结果` 子标题对应输出面板，确认输出面板存在。
   - 进程处置：核验完成后已停止后台 Job 并移除 Job 记录，未遗留占用进程。

4. 用户文档更新
   - `docs/user_manual_zh.md` 已补充“上传文件工作流（5.3.1）”与“输出面板说明（5.5）”。
   - 核心说明：上传成功时优先使用上传文本，异常或空内容时自动回退手动输入；输出面板固定可见。

## 九、Task 3 核验数据差异说明与可追溯证据（2026-05-07）

1. 同日通过数变化（Delta）说明
   - 同日块内出现 `21/47`、`25/53`、`35/63` 三组通过数，属于阶段内增量测试后的自然变化，并非回归不稳定。
   - 变化原因：Task 3 在“上传输入解析/回退”和“输出面板可见性”方向新增并细化了相关测试，用例总数随提交演进增加，因此后续块的通过总数更高。
   - 结论：通过数变化反映的是测试覆盖面扩展，不是质量下降；同日各块均保持 `0 failed`。

2. 本次补录的证据落盘位置与时间戳
   - 补录时间：`2026-05-07 08:05:51 +08:00`。
   - 证据载体：本文件第七节与第八节已记录原始命令与结果；本节提供可追溯汇总，作为本次文档修订的核验索引。
   - 追溯方式：按“命令 -> 结果 -> 事实”可回查对应条目，无需依赖外部独立日志文件。

3. 可追溯命令转录摘要（含通过数/告警数/启动事实）
   - 命令：`pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py` -> 结果：`25 passed, 3 warnings in 50.93s` -> 事实：UI 契约映射、中文 UI 显示约束、本地流程 Gate-L 与异常结构化字段核验通过（见第七节第 1 条）。
   - 命令：`pytest -q` -> 结果：`53 passed, 3 warnings in 57.04s` -> 事实：该轮全量回归无失败（见第七节第 2 条）。
   - 命令：`E:\Ana\python.exe -m pytest -v tests/test_ui_contract_mapping.py tests/test_workflows.py` -> 结果：`35 passed, 3 warnings in 40.16s` -> 事实：上传输入解析/回退与输出面板相关路径在增强后通过（见第八节第 1 条）。
   - 命令：`E:\Ana\python.exe -m pytest -q` -> 结果：`63 passed, 3 warnings in 45.16s` -> 事实：增强后全量回归仍保持无失败（见第八节第 2 条）。
    - 命令：`powershell -ExecutionPolicy Bypass -File .\run_streamlit.ps1` -> 启动事实：`deps-ok`、`Local URL: http://localhost:8502`、`Network URL: http://192.168.5.4:8502`、探活 `HTTP 200`、检测到 `file_uploader` 与 `翻译结果` 面板 -> 进程处置：验证后安全停止后台 Job（见第七节第 3 条与第八节第 3 条）。

## 十、最终收口与合并状态（2026-05-07）

- 说明：本节仅记录当日历史节点（对应先前任务的合并结果），不代表当前 `ui-restructure` 分支已合并到 `main`。
- 历史节点：文件上传功能（`txt/md/docx`）与固定输出面板在当时已完成合并。
- 历史节点核验：`pytest -q` -> `63 passed, 3 warnings`。
- 历史节点中文 UI 对齐：按钮文案与实际行为一致（`运行本地任务` / `运行预训练任务`）。

## 十一、UI 重构轮（Task 3）文档同步与回归证据（2026-05-07）

1. 用户手册行为同步
   - `docs/user_manual_zh.md` 已同步 UI 重构后的交互：
     - 语言选择改为 `zh/en/ja` 下拉
     - 主题改为“预设选择 + 手动覆盖（手动优先）”
     - 三路输入融合（本地/训练/验证），均支持“上传优先、异常回退手动”
     - 主区域仅保留 `翻译结果`，详细字段收敛到侧栏折叠区 `页面详情与状态`

2. 全量回归核验（本轮要求命令）
   - 命令：`E:\Ana\python.exe -m pytest -q`
   - 结果：`67 passed, 3 warnings in 41.64s`
   - Delta 说明：相对上一轮文档记录的 `63 passed`，本轮增加到 `67 passed`，净增 `+4`。
   - 增量来源：本轮新增/细化了 UI 重构相关测试（语言/主题交互、三路输入融合、主区与侧栏信息分层展示等），因此用例总数上升。
   - 结论补充：`63 -> 67` 反映覆盖面扩展，不是回归波动；两轮均为 `0 failed`。
   - 结论：UI 重构相关功能与既有流程在本轮全量回归中均通过，无失败项。

3. 告警说明（非阻断）
   - 两条 `SwigPyPacked/SwigPyObject` 的 `DeprecationWarning`
   - 一条 Marian tokenizer 的 `sacremoses` 建议安装提示
   - 当前均未阻断测试通过，后续按依赖升级节奏处理。

## 十二、Task 4 本地模式行为补录（2026-05-07）

1. 行为与文档对齐项
   - 补录本地模式复核门为 `confirm/revise`：
     - `confirm` 只确认输出，不执行词库写回。
     - `revise` 进入修订路径，且仅该路径触发词库 writeback。
   - 用户手册已同步“仅在 revise 写回”的约束，避免将确认路径误解为会写库。

2. 关键行为核验（fallback merge + confirm/revise + revise writeback）
   - 命令：`E:\Ana\python.exe -m pytest -q tests/test_merging.py tests/test_ui_contract_mapping.py`
   - 结果：`35 passed in 1.59s`
   - 结论：
     - fallback merge 路径通过（低重叠回退决策相关用例通过）。
     - confirm/revise 复核门行为通过（确认不写回、修订可写回、空修订不写回）。
     - revise 写回失败路径的错误传播断言通过（保持可观测性）。

3. 全量回归核验（本轮要求命令）
   - 命令：`E:\Ana\python.exe -m pytest -q`
   - 结果：`82 passed, 3 warnings in 40.44s`
   - 结论：本轮文档与断言补录后，全量测试保持 `0 failed`。

## 十三、Phase-3 Agent Core 原型落地（2026-06-16）

1. 落地范围
   - 新增 agent 契约与模式策略：`learning`、`self_iterative`、`self_decision`。
   - 新增 provider adapter 边界：静态测试 provider、现有本地工作流 provider、OpenAI-compatible HTTP provider。
   - 新增批量输入抽取：支持 `txt/md/docx`，供后续桌面端壳复用。
   - 新增长文本上下文预算续译链路：估算上下文、当前/待续切分、续译任务、拼接核验任务。
   - 增强长文本切割：单段超长时继续二次切分，避免待续任务再次超上下文。
   - 增加本机凭据 store 与 provider config，避免 API key 写入 provider 配置。
   - 新增 Tkinter 桌面端原型入口与 `run_desktop_agent.ps1`。
   - 新增 SQLite 审计与确认门控：`agent_runs`、`revision_events`、`terms`、`phrases`、`style_rules`、`project_profile`。

2. 明确边界
   - 当前 Streamlit UI 仍不暴露第三阶段入口。
   - 完整桌面交互、HOOK/OCR 仍为后续任务。
   - 学习模式下词库更新先进入待确认事件，未确认不得写入正式 `terms`。
   - 长文本续译当前使用启发式 token 估算，后续真实 LLM provider 接入后需替换为 provider-specific token counter。

3. 验证记录
   - 新增 agent 测试：`12 passed`。
   - 全量回归：使用隔离 `LOCALAPPDATA` 与 pytest basetemp 运行，避免 Windows 用户目录权限干扰。

## 十四、Agent 词库数据层与续译调度补强（2026-06-16）

1. 数据层补强
   - `AgentRunStore` 新增 JSON 词库导入能力，支持旧版平铺结构与三层 `terms` / `phrases` / `style_rules`。
   - SQLite 词库新增 topic 导出、单项查询、命中文本查询与受控 upsert。
   - agent 运行前按 topic 将当前文本命中的术语、短语和风格规则注入 `ProviderRequest`，并在 trace 中记录命中数量。

2. 长文本调度补强
   - 多个仍能放入当前上下文的切片会合并进入初始翻译任务。
   - 无法放入当前任务的切片继续作为待续任务，并继承同一 `translation_brief`。

3. 验证记录
   - Agent 集中测试：`31 passed`。
   - 全量回归：`113 passed, 2 warnings in 59.48s`。

## 十五、桌面端人工确认与审计控制层补强（2026-06-16）

1. 数据与控制层
   - `AgentRunStore` 新增待确认 `revision_events` 列表、按事件 ID 确认写回、按 run_id 读取审计详情、确认 run 状态等接口。
   - `DesktopAgentController` 新增审计 run 列表、单 run 查询、确认输出、列出待确认词库提案、确认词库写回、导出 topic 词库等方法。

2. 桌面壳
   - `create_desktop_app` 新增候选列表、审计列表、待确认词库提案列表。
   - 增加 `Confirm Run` 与 `Confirm Lexicon Update` 按钮，使学习模式的人工确认门控具备桌面端操作入口。

3. 验证记录
   - Store 与桌面 controller 集中测试：`10 passed`。

## 十六、远端 Provider 调用预检与确认门（2026-06-16）

1. 预检能力
   - 新增 `agent_preflight.py`，根据上下文切片、运行模式和 provider 列表生成远端调用预览。
   - 预检内容包括远端 provider、上下文任务引用、轮次、估算输入 token、预估成本、预算限制与风险提示。

2. 桌面安全门
   - `DesktopAgentController` 新增 `preview_remote_calls` 与 `confirm_remote_preflight`。
   - `require_remote_confirmation=True` 时，远端 provider 实际调用前必须先确认 preflight；确认 ID 与输入文本、provider、上下文预算、运行模式和成本估算绑定，并且使用后失效。
   - Tkinter 壳新增远端调用预检列表、`Preview Remote Calls` 与 `Confirm Remote Calls` 按钮。

3. 验证记录
   - 预检与桌面 controller 集中测试：`9 passed`。

## 十七、Provider 配置持久化（2026-06-16）

1. 配置存储
   - SQLite schema 新增 `provider_configs` 表，保存 provider id、类型、base URL、模型、credential id、估算成本和启用状态。
   - 配置表不保存 API key 明文；真实密钥继续由 `LocalCredentialStore` 管理。

2. 构建与加载
   - `ProviderConfig` 增加 `enabled` 字段。
   - 新增 `build_enabled_providers`，只从启用配置构建 provider，并按 `credential_id` 读取本机凭据。
   - `DesktopAgentController` 新增 `load_enabled_provider_configs`，用于后续 provider 设置页和项目加载。

3. 验证记录
   - Provider 配置与相关集中测试：`21 passed`。

## 十八、桌面项目配置与最近文件持久化（2026-06-16）

1. 项目配置
   - 新增 `agent_project.py`，定义 `DesktopProjectProfile`。
   - 复用 SQLite `project_profile` 表保存项目 JSON：语言、主题、模式、上下文预算、API 开关、预算限制、远端确认开关和最近文件。
   - 默认桌面数据库路径为 `%LOCALAPPDATA%\ConsensusTranslation\agent.sqlite3`。

2. 桌面控制器与入口
   - `DesktopAgentController` 新增项目 profile 加载、保存和最近文件记录。
   - `translate_file` 完成后会记录最近文件。
   - Tkinter 壳新增基础项目配置控件、`Open Files` 和 `Save Project` 按钮；打开 `txt/md/docx` 后载入首个文件文本并更新最近文件。

3. 验证记录
   - 项目 profile、桌面 controller 与 store 集中测试：`16 passed`。

## 十九、旧 JSON 词库迁移命令（2026-06-16）

1. 迁移模块
   - 新增 `agent_lexicon_migration.py`，提供 `migrate_legacy_json_lexicon` 和命令行入口。
   - 迁移逻辑复用 `AgentRunStore.import_json_lexicon`，兼容旧版平铺 JSON 和三层 `terms` / `phrases` / `style_rules`。
   - 命令输出 JSON 摘要：源路径、目标 SQLite DB、各层导入计数。

2. Windows 包装脚本
   - 新增 `migrate_legacy_lexicon.ps1`。
   - 默认迁移现有 `LexiconRepo` 路径到桌面 SQLite store。
   - 支持 `--source` 与 `--db` 显式指定路径。

3. 验证记录
   - 迁移、store、词库和桌面相关集中测试：`25 passed`。

## 二十、自迭代验证评分与 MetaPolicyAgent（2026-06-16）

1. 自迭代
   - `self_iterative` 不再只按候选置信度提前停止。
   - 每轮裁决后使用现有 deterministic `evaluate_translation` 计算验证集分数。
   - 分数达到阈值则通过并结束；三轮后仍失败则标记 `needs_review`，进入人工复核。
   - trace 新增 `validation_score:*`、`validation_passed:*`、`validation_failed:max_rounds`。

2. 自决策
   - 新增 `agent_meta_policy.py`。
   - `MetaPolicyAgent` 根据训练/验证是否存在、API 开关、预算和验证覆盖率选择 `learning` 或 `self_iterative`。
   - trace 新增 `meta_policy:reason=*` 和 `meta_policy:validation_coverage=*`。

3. 验证记录
   - Workflow/contract/preflight 集中测试：`14 passed`。

## 二十一、可插拔评估器与远端 evaluator 预检（2026-06-16）

1. 评估器抽象
   - 新增 `agent_evaluators.py`，定义 `TranslationEvaluator`、`EvaluationRequest`、`EvaluationResult`。
   - 新增 `DeterministicTranslationEvaluator`，保留现有离线 deterministic 验证指标。
   - 新增 `CometTranslationEvaluator`，支持注入已加载 COMET 模型或在安装可选 runtime 后加载模型。
   - 新增 `OpenAICompatibleJudgeEvaluator`，通过 OpenAI-compatible `/chat/completions` 执行 LLM-as-evaluator，并解析 JSON 分数与理由。

2. 工作流接入
   - `run_agent_translation` 新增可选 `evaluator` 参数。
   - `self_iterative` 每轮裁决后使用 evaluator 评分，trace 记录 `validation_evaluator:*`、`validation_score:*` 与必要的人工复核提示。
   - `run_context_managed_translation` 与桌面控制器透传 evaluator，使长文本切片任务沿用同一评估策略。

3. 远端安全边界
   - `agent_preflight.py` 将远端 evaluator 纳入预检成本估算。
   - 桌面 preflight 列表现在可显示 `evaluator:<id>`、上下文片段、轮次、估算 token 与估算成本。
   - LLM-as-evaluator 在 `api_enabled=False` 时不会被调用；若预算不足，会按预算超限路径停止。

4. 当前验证记录
   - 评估器与工作流集中测试：`15 passed`。
   - preflight 与桌面控制器集中测试：`12 passed`。

## 二十二、续译 brief 透传与拼接核验任务补强（2026-06-16）

1. 待续任务上下文传递
   - `ProviderRequest` 新增 `continuation_brief` 字段。
   - `run_agent_translation` 与 `run_context_managed_translation` 透传该字段。
   - 初始任务不带 brief；每个 `continuation_translation` 任务把同一份 `translation_brief` 传给 provider。
   - OpenAI-compatible provider 会把 continuation brief 放入提示词，便于真实远端模型沿用前序结构、术语和语气。

2. brief 结构补强
   - `translation_brief` 明确拆成写作结构、翻译要点、待续策略、前序摘要四段。
   - 待续策略明确要求沿用前序术语、叙事视角、语气和段落结构，并避免重译已完成片段。

3. 拼接核验任务
   - `ManagedTranslationTask` 新增 `verification` 字段。
   - `stitch_and_verify` 任务现在携带结构化核验报告。
   - 报告包含 `status`、分段数、预期分段数、空段数、顺序是否保持、上下文限制是否遵守和来源任务 id。

4. 当前验证记录
   - 续译集中测试：`4 passed`。

## 二十三、桌面 Agent 导出包（2026-06-17）

1. 导出服务
   - 新增 `agent_artifacts.py`。
   - `export_translation_artifacts` 可将 `ContextManagedTranslationResult` 导出为可交付 artifact 包。
   - 导出文件包括最终译文、续译 brief、拼接核验 JSON、分段审计 JSON 和 manifest JSON。

2. 桌面控制器与 UI
   - `DesktopAgentController` 新增 `export_translation_artifacts` 方法。
   - Tkinter 原型新增 `Export Artifacts` 按钮，使用最近一次 Agent 运行结果导出文件。
   - manifest 记录项目 id、配置摘要、上下文 token 估算、切片数量、待续切片数量、任务 id、run id 和核验状态。

3. 当前验证记录
   - 导出服务与桌面控制器集中测试：`11 passed`。

## 二十四、Windows 桌面包构建与 smoke 验证（2026-06-17）

1. 打包入口
   - 新增 `agent_packaging.py`，提供桌面打包预检。
   - 新增 `requirements-desktop.txt`，将 PyInstaller 作为桌面打包可选依赖。
   - 新增 `packaging/desktop_agent.spec`，以 `desktop_agent_app.py` 为入口生成 `ConsensusTranslationAgent`。
   - 新增 `build_desktop_agent.ps1`，先执行预检，再运行 PyInstaller spec。

2. 构建修正
   - 修正 spec 中 `SPECPATH` 推导导致入口被解析为 `E:\src\...` 的路径问题。
   - 在 spec 中排除 `IPython`、`matplotlib`、`numpy`、`torch`、`transformers` 等桌面入口不需要的重型包，降低分析面。
   - `.gitignore` 增加 `build/` 与 `dist/`，避免构建产物进入版本控制。

3. 当前验证记录
   - PyInstaller 安装成功：`PyInstaller-6.21.0`。
   - 打包预检通过：`desktop-packaging-preflight-ok`。
   - 构建成功：`dist\ConsensusTranslationAgent\ConsensusTranslationAgent.exe`。
   - GUI smoke：隐藏窗口启动 5 秒未退出，随后手动停止进程。

## 二十五、桌面 Provider 设置入口（2026-06-17）

1. 控制器能力
   - `DesktopAgentController` 新增 `save_provider_settings`。
   - `default_desktop_credentials_path` 默认指向 `%LOCALAPPDATA%\ConsensusTranslation\credentials.json`。
   - 保存 provider 时 SQLite `provider_configs` 只写入 provider id、base URL、model、credential id、估算成本和启用状态。
   - API key 写入 `LocalCredentialStore`，不会明文进入 SQLite provider 配置。

2. Tkinter 桌面入口
   - 新增 Provider ID、Base URL、Model、API Key、Cost、Enabled 控件。
   - 新增 `Save Provider` 和 `Load Providers` 按钮。
   - `Load Providers` 会把启用 provider 载入 `controller.providers`，供 `Run Agent` 与 `Preview Remote Calls` 使用。

3. 当前验证记录
   - Provider 设置和桌面 UI 契约集中测试：`17 passed`。
