# Privacy and data handling

## Local-first defaults

- Source text, training/validation data, project files, lexicons, audit runs, OCR input, and exported artifacts remain local by default.
- Remote API use is disabled by default.
- The application does not include analytics or telemetry in the current release design.
- Local SQLite, credential, runtime, cache, and model paths are shown in diagnostics.

## Remote provider boundary

When a user enables an OpenAI-compatible provider, every request must pass a preflight that identifies the provider, model, text segments, data scopes, estimated tokens/cost, and budget risk. A one-time confirmation is bound to that exact preflight. Training data is excluded unless the user explicitly enables training upload.

No real remote API calls or API keys are used in the automated release tests.

## Credentials

Provider configuration stores only a credential identifier in SQLite. On Windows, secret values are protected by DPAPI through the local credential store. Secrets must not appear in logs, diagnostics, exports, screenshots, or provider previews.

## External connectors

Clipboard, folder, OCR, and future loopback connectors are opt-in. The application records source type and operational diagnostics but must not record credentials. Process injection and hook-code search are outside the current release scope.

## Deletion and uninstall

Users can remove project data and cached artifacts independently of the application. The installer must explain whether uninstall keeps or removes the selected data directory and must never delete files outside paths that it created and verified.
