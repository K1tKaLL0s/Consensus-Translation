# 桌面翻译 Agent 发布核验清单

日期：2026-06-18

## 自动化证据

- Qt one-folder 构建：`powershell -ExecutionPolicy Bypass -File .\build_desktop_qt.ps1`
- 标准安装包：`powershell -ExecutionPolicy Bypass -File .\build_installer.ps1 -Channel standard`
- 完整安装包：`powershell -ExecutionPolicy Bypass -File .\build_installer.ps1 -Channel full -RuntimePayload 'E:\Cn-Jp Translate\.runtime'`
- E 盘 runtime 验证：`E:\Ana\python.exe scripts\verify_optional_runtimes.py --runtime-root 'E:\Cn-Jp Translate\.runtime'`
- 安装后验收：`powershell -ExecutionPolicy Bypass -File .\scripts\verify_installed_release.ps1 -InstallerPath <installer> -InstallDir <E:\path>`

## 当前自动化通过项

- Tesseract 5.5.0 与 `eng/jpn/chi_sim/chi_tra` OCR fixture。
- COMET CLI、`Unbabel/wmt22-comet-da` 模型加载与本地样例评分。
- Qt packaged diagnostics 与 local smoke。
- Inno Setup 安装器支持用户选择安装目录和 desktop shortcut task。
- 标准安装包为单 exe；完整安装包因内置 COMET runtime 使用 Inno 分卷。

## 仍不包含或需目标机确认

- 代码签名。
- 自动更新。
- 真实远端 provider/API key 联调。
- 目标用户桌面的可视 GUI 手工 smoke。
- Microsoft SmartScreen 或企业杀软策略验证。

## 发布判断

若自动化测试、安装后验收、release manifest hash、安装路径选择、桌面快捷方式和卸载均通过，则当前产物具备开源发布或未签名商业试发布能力。正式商业分发前应补代码签名、干净构建机复核和真实 provider 联调。
