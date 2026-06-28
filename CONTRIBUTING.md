# Contributing

## Development Setup

Install only the dependencies needed for the area you are changing. For Windows UI work, include `requirements-qt.txt`.

## Test Expectations

Run the narrowest relevant tests first, then the safe release subset before opening a pull request:

```powershell
python -m pytest -p no:cacheprovider tests/capability
python -m pytest -p no:cacheprovider tests/test_agent_workflows.py
python -m pytest -p no:cacheprovider tests/test_agent_preflight.py
python -m pytest -p no:cacheprovider tests/test_agent_provider_config.py
python -m pytest -p no:cacheprovider tests/test_desktop_qt_workflows.py
python -m pytest -p no:cacheprovider tests/test_react_desktop_integration.py
```

If React UI files change, build to a temporary output directory:

```powershell
npm run build -- --outDir $env:TEMP\consensus-react-build --emptyOutDir
```

## Release Safety

- Do not commit `.runtime/`, `data/`, `dist/`, `build/`, `release/`, `node_modules/`, or pytest cache output.
- Do not commit API keys, tokens, credentials, private source text, or local user data.
- Do not mark partial, placeholder, or mock-only capabilities as production-ready.
- Keep user-facing Windows flows behind explicit contract and capability checks.
