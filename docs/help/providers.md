# Provider 与评估器

Provider 页面保存的是 provider 配置和凭据引用。API key 写入本地凭据存储，界面不会回显原文密钥。

默认测试和本地冒烟不会执行真实远端请求。保存远端 provider 后，只有在用户启用 API、预算允许、并在工作台完成远端预检确认时，翻译流程才会调用真实远端 provider。

COMET 评估器通过外部 sidecar 命令运行。缺少 COMET 时，诊断应显示 warning，而不是阻止本地翻译。
